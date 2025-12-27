"""
Automatic file monitoring service
Intelligent file processing component of IoT device monitoring system
"""

import asyncio
import logging
import sys
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Callable
import json
import time

# Add configuration path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
config_path = project_root / "config"

# Add to Python path
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(config_path) not in sys.path:
    sys.path.insert(0, str(config_path))

# Import unified configuration manager
from config.unified_config_manager import UnifiedConfigManager, get_config, get_log_message

# Import processing engine and database
from backend.pcap_process.core.engine import PcapProcessingEngine
from backend.pcap_process.core.config import ProcessingConfig
from database.connection import PostgreSQLDatabaseManager

# Initialize the file_monitor logger and reconfigure it during the initialization of the FileMonitorService
logger = logging.getLogger('file_monitor')

# Create configuration manager instance
config_manager = UnifiedConfigManager()

class ScheduledPCAPScanner:
    """Configuration-based scheduled PCAP file scanner"""
    
    def __init__(self, processor_callback: Callable, file_monitor_config: Dict):
        """
        Initialize scheduled scanner
        
        Args:
            processor_callback: Callback function to process PCAP files
            file_monitor_config: File monitoring configuration
        """
        self.processor_callback = processor_callback
        self.config = file_monitor_config
        self.processed_files = set()
        
        # Configuration-based queue initialization
        self.processing_queue = asyncio.Queue()
        if get_config('file_monitor.logging.log_queue_operations', False, 'file_monitor.logging'):
            logger.info(get_log_message('file_monitor', 'queue_reset', component='file_monitor.queue'))
        
        # Configuration-based file extension support
        self.supported_extensions = set(
            get_config('file_monitoring.supported_extensions', 
                      ['.pcap', '.pcapng', '.cap'], 
                      'file_monitor.file_handling')
        )
        
        # Configuration-based processing statistics
        self.processing_stats = {
            'files_detected': 0,
            'files_processed': 0,
            'files_failed': 0,
            'last_processed': None,
            'last_scan': None
        }
        
        # Get scan schedule configuration
        # Try both config keys for compatibility
        self.schedule_enabled = get_config('file_monitoring.schedule.enabled', 
                                         get_config('file_monitor.schedule.enabled', True, 'file_monitor.schedule'), 
                                         'file_monitoring.schedule')
        self.scan_times = get_config('file_monitoring.schedule.scan_times', 
                                   get_config('file_monitor.schedule.scan_times', 
                                            ['06:00', '12:00', '18:00', '23:59'], 
                                            'file_monitor.schedule'),
                                   'file_monitoring.schedule')
        self.timezone_str = get_config('file_monitoring.schedule.timezone', 
                                     get_config('file_monitor.schedule.timezone', 'local', 'file_monitor.schedule'),
                                     'file_monitoring.schedule')
        
        # Setup timezone
        import pytz
        if self.timezone_str == 'local':
            import tzlocal
            local_tz = tzlocal.get_localzone()
            # Convert to pytz timezone for consistent API
            self.timezone = pytz.timezone(str(local_tz))
        else:
            self.timezone = pytz.timezone(self.timezone_str)
        
        logger.info(get_log_message('file_monitor', 'scanner_initialized', 
                                   component='file_monitor.scanner',
                                   extensions=list(self.supported_extensions),
                                   scan_times=self.scan_times,
                                   timezone=str(self.timezone)))

    def _parse_scan_time(self, time_str: str) -> tuple:
        """Parse scan time string to hour and minute"""
        try:
            hour, minute = map(int, time_str.split(':'))
            return hour, minute
        except ValueError:
            logger.warning(f"Invalid scan time format: {time_str}, using 00:00")
            return 0, 0

    def _get_next_scan_time(self) -> datetime:
        """Calculate next scan time based on configuration - fixed to support all scan times"""
        now = datetime.now(self.timezone)
        today = now.date()
        
        # Create all possible scan times for today and tomorrow, then find the earliest one after now
        all_scan_times = []
        
        # Add today's scan times
        for time_str in self.scan_times:
            hour, minute = self._parse_scan_time(time_str)
            scan_time = datetime.combine(today, datetime.min.time().replace(hour=hour, minute=minute))
            scan_time = self.timezone.localize(scan_time)
            if scan_time > now:
                all_scan_times.append(scan_time)
        
        # Add tomorrow's scan times (all of them)
        tomorrow = today + timedelta(days=1)
        for time_str in self.scan_times:
            hour, minute = self._parse_scan_time(time_str)
            scan_time = datetime.combine(tomorrow, datetime.min.time().replace(hour=hour, minute=minute))
            scan_time = self.timezone.localize(scan_time)
            all_scan_times.append(scan_time)
        
        # Sort all scan times and return the earliest one
        if all_scan_times:
            all_scan_times.sort()
            return all_scan_times[0]
        else:
            # Fallback: tomorrow's first scan time
            hour, minute = self._parse_scan_time(self.scan_times[0])
            next_scan = datetime.combine(tomorrow, datetime.min.time().replace(hour=hour, minute=minute))
            next_scan = self.timezone.localize(next_scan)
            return next_scan

    async def schedule_scanner(self, monitor_directories: List[Path]):
        """Main scheduled scanner loop"""
        if not self.schedule_enabled:
            logger.info("Scheduled scanning is disabled, skipping scanner")
            return
        
        logger.info(f"Starting scheduled scanner with scan times: {self.scan_times}")
        
        while True:
            try:
                next_scan = self._get_next_scan_time()
                now = datetime.now(self.timezone)
                wait_seconds = (next_scan - now).total_seconds()
                
                logger.info(f"Next scan scheduled at: {next_scan.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                logger.info(f"Waiting {wait_seconds:.0f} seconds until next scan")
                
                # Wait until next scan time
                await asyncio.sleep(wait_seconds)
                
                # Perform scan
                await self._perform_scheduled_scan(monitor_directories)
                
                # Small delay to prevent double-scanning
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                logger.info("Scheduled scanner cancelled")
                break
            except Exception as e:
                logger.error(f"Error in scheduled scanner: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retry

    async def _perform_scheduled_scan(self, monitor_directories: List[Path]):
        """Perform a scheduled scan of all monitored directories"""
        scan_start = datetime.now(self.timezone)
        logger.info(f"Starting scheduled scan at {scan_start.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        total_files = 0
        new_files = 0
        already_processed = 0
        
        # Configuration-based scanning settings
        ignore_hidden = get_config('file_monitor.scanning.ignore_hidden_files', 
                                 True, 'file_monitor.scanning')
        ignore_temp = get_config('file_monitor.scanning.ignore_temp_files', 
                               True, 'file_monitor.scanning')
        
        for monitor_dir in monitor_directories:
            logger.info(f"Scanning directory: {monitor_dir}")
            
            if not monitor_dir.exists():
                logger.warning(f"Directory not exists: {monitor_dir}")
                continue
            
            # Recursive scan of all subdirectories
            for file_path in monitor_dir.rglob("*"):
                if not file_path.is_file():
                    continue
                
                # Check file extension
                if file_path.suffix.lower() not in self.supported_extensions:
                    continue
                
                # Configuration-based file filtering
                if ignore_hidden and file_path.name.startswith('.'):
                    continue
                
                if ignore_temp and (file_path.name.endswith('.tmp') or file_path.name.endswith('.temp')):
                    continue
                
                total_files += 1
                
                # Check if file was already processed
                if str(file_path) in self.processed_files:
                    already_processed += 1
                    continue
                
                # Queue file for processing
                new_files += 1
                await self._queue_file_for_processing(file_path)
        
        self.processing_stats['last_scan'] = scan_start
        
        logger.info(f"Scheduled scan completed: total={total_files}, new={new_files}, processed={already_processed}")

    async def _queue_file_for_processing(self, file_path: Path):
        """Add file to processing queue"""
        try:
            await self.processing_queue.put({
                'file_path': file_path,
                'detected_time': datetime.now(timezone.utc),
                'retry_count': 0
            })
            
            if get_config('file_monitor.logging.log_file_detection', True, 'file_monitor.logging'):
                logger.info(f"Queued file for processing: {file_path}")
                
        except Exception as e:
            logger.error(f"Failed to queue file {file_path}: {e}")

    async def process_queue(self):
        """Configuration-based queue processing"""
        logger.info(get_log_message('file_monitor', 'queue_started', component='file_monitor.queue'))
        
        queue_check_interval = get_config('file_monitor.processing.queue_check_interval', 1, 'file_monitor.processing')
        max_retries = get_config('file_monitor.processing.max_retries', 3, 'file_monitor.processing')
        retry_delay = get_config('file_monitor.processing.retry_delay', 30, 'file_monitor.processing')
        
        while True:
            try:
                if get_config('file_monitor.logging.log_queue_operations', False, 'file_monitor.logging'):
                    logger.debug(f"Queue waiting, size: {self.processing_queue.qsize()}")
                
                # Get file from queue
                file_info = await self.processing_queue.get()
                file_path = file_info['file_path']
                
                if get_config('file_monitor.logging.log_queue_operations', False, 'file_monitor.logging'):
                    logger.info(f"Processing file from queue: {file_path}")
                
                # Check if file still exists
                if not file_path.exists():
                    logger.warning(f"File no longer exists: {file_path}")
                    self.processing_queue.task_done()
                    continue
                
                if get_config('file_monitor.logging.log_file_processing', True, 'file_monitor.logging'):
                    logger.info(f"Starting file processing: {file_path}")
                
                # Mark as being processed
                self.processed_files.add(str(file_path))
                
                # Call processing callback
                success = await self.processor_callback(file_path, file_info)
                
                if success:
                    self.processing_stats['files_processed'] += 1
                    self.processing_stats['last_processed'] = datetime.now(timezone.utc)
                    
                    if get_config('file_monitor.logging.log_file_processing', True, 'file_monitor.logging'):
                        logger.info(f"File processing successful: {file_path}")
                    
                    # Delete processed file after successful processing
                    if file_path.exists():
                        file_path.unlink()
                        logger.info(f"Deleted processed file: {file_path}")
                else:
                    self.processing_stats['files_failed'] += 1
                    
                    if get_config('file_monitor.logging.log_file_processing', True, 'file_monitor.logging'):
                        logger.error(f"File processing failed: {file_path}")
                    
                    # Handle retry logic
                    retry_count = file_info.get('retry_count', 0)
                    if retry_count < max_retries:
                        file_info['retry_count'] = retry_count + 1
                        logger.info(f"Retrying file processing ({retry_count + 1}/{max_retries}): {file_path}")
                        await asyncio.sleep(retry_delay)
                        await self.processing_queue.put(file_info)
                    else:
                        logger.error(f"Max retries exceeded for file: {file_path}")
                        # Keep failed files for debugging
                        keep_failed = get_config('file_monitoring.keep_failed_files', True, 'file_monitor.file_handling')
                        if not keep_failed and file_path.exists():
                            file_path.unlink()
                            logger.info(f"Deleted failed file: {file_path}")
                
                self.processing_queue.task_done()
                
                # Brief pause between processing
                await asyncio.sleep(queue_check_interval)
                
            except asyncio.CancelledError:
                logger.info("Queue processing cancelled")
                break
            except Exception as e:
                logger.error(f"Error in queue processing: {e}")
                await asyncio.sleep(retry_delay)

class WebSocketBroadcastProtection:
    """WebSocket broadcast protection layer"""
    
    def __init__(self):
        self.websocket_manager = None
        self.database_service = None
        self.connection_checked = False
        self.last_check_time = 0
        self.check_interval = 10  # Check connection status every 10 seconds
        self.debounce_interval = 2  # Debounce for 2 seconds
        
    async def safe_broadcast(self, experiment_id: str, device_id: str = None, 
                           semaphore: asyncio.Semaphore = None, 
                           last_broadcast_time: Dict = None):
        """
        WebSocket broadcast
        
        Args:
            experiment_id: Experiment ID
            device_id: Device ID
            semaphore: Concurrency control semaphore
            last_broadcast_time: Debounce time record
        """
        # 1. Concurrency control
        if semaphore:
            async with semaphore:
                await self._protected_broadcast(experiment_id, device_id, last_broadcast_time)
        else:
            await self._protected_broadcast(experiment_id, device_id, last_broadcast_time)
    
    async def _protected_broadcast(self, experiment_id: str, device_id: str = None, 
                                 last_broadcast_time: Dict = None):
        """Broadcast execution"""
        try:
            # 1. Debounce mechanism
            if not self._should_broadcast(experiment_id, last_broadcast_time):
                return
            
            # 2. Connection status check
            if not await self._ensure_websocket_ready():
                logger.warning(get_log_message('file_monitor', 'websocket_not_ready', 
                                             component='file_monitor.websocket_protection'))
                return
            
            # 3. Database service check
            if not await self._ensure_database_ready():
                # Fallback - send simple update message
                await self._fallback_broadcast(experiment_id)
                return
            
            # 4. Execute full broadcast
            await self._execute_full_broadcast(experiment_id, device_id)
            
            # 5. Update debounce time
            if last_broadcast_time is not None:
                last_broadcast_time[experiment_id] = datetime.now().timestamp()
                
        except Exception as e:
            # 6. Error isolation - record but do not throw
            logger.error(get_log_message('file_monitor', 'protected_broadcast_error', 
                                       component='file_monitor.websocket_protection',
                                       experiment_id=experiment_id, error=str(e)))
    
    def _should_broadcast(self, experiment_id: str, last_broadcast_time: Dict = None) -> bool:
        """Debounce check"""
        if last_broadcast_time is None:
            return True
            
        current_time = datetime.now().timestamp()
        last_time = last_broadcast_time.get(experiment_id, 0)
        
        return (current_time - last_time) >= self.debounce_interval
    
    async def _ensure_websocket_ready(self) -> bool:
        """Ensure WebSocket manager is ready"""
        current_time = datetime.now().timestamp()
        
        # Periodically check connection status
        if (current_time - self.last_check_time) >= self.check_interval:
            self.connection_checked = False
            self.last_check_time = current_time
        
        if self.connection_checked and self.websocket_manager:
            return True
        
        try:
            # Get WebSocket manager
            from ..api.websocket.manager_singleton import get_websocket_manager
            self.websocket_manager = get_websocket_manager()
            
            # Check manager status
            if not self.websocket_manager or not self.websocket_manager.is_running():
                logger.warning(get_log_message('file_monitor', 'websocket_manager_not_running', 
                                             component='file_monitor.websocket_protection'))
                return False
            
            # Check if there are active connections
            connection_count = self.websocket_manager.get_connection_count()
            if connection_count == 0:
                # No connections, no broadcast, but not an error
                logger.debug(get_log_message('file_monitor', 'no_websocket_connections', 
                                           component='file_monitor.websocket_protection'))
                return False
            
            self.connection_checked = True
            return True
            
        except ImportError:
            logger.debug(get_log_message('file_monitor', 'websocket_manager_unavailable', 
                                       component='file_monitor.websocket_protection'))
            return False
        except Exception as e:
            logger.warning(get_log_message('file_monitor', 'websocket_check_failed', 
                                         component='file_monitor.websocket_protection',
                                         error=str(e)))
            return False
    
    async def _ensure_database_ready(self) -> bool:
        """Ensure database service is ready"""
        if self.database_service:
            return True
        
        try:
            # Try to get database service instance
            try:
                from ..api.api_config import get_database_service
                self.database_service = get_database_service()
            except ImportError:
                try:
                    from backend.api.api_config import get_database_service
                    self.database_service = get_database_service()
                except ImportError:
                    pass
            
            # Create temporary instance (if necessary)
            if not self.database_service:
                from database.services.database_service import DatabaseService
                # This requires a valid database manager instance
                # If not, return False to enable fallback mode
                return False
            
            return True
            
        except Exception as e:
            logger.warning(get_log_message('file_monitor', 'database_service_check_failed', 
                                         component='file_monitor.websocket_protection',
                                         error=str(e)))
            return False
    
    async def _fallback_broadcast(self, experiment_id: str):
        """Fallback - send simple update message"""
        try:
            simple_message = {
                "type": "experiment_data_update",
                "experiment_id": experiment_id,
                "timestamp": datetime.now().isoformat(),
                "message": "New data available"
            }
            
            await self.websocket_manager.broadcast_to_topic(
                f"experiments.{experiment_id}",
                simple_message
            )
            
            logger.info(get_log_message('file_monitor', 'fallback_broadcast_success', 
                                      component='file_monitor.websocket_protection',
                                      experiment_id=experiment_id))
                                      
        except Exception as e:
            logger.debug(get_log_message('file_monitor', 'fallback_broadcast_failed', 
                                       component='file_monitor.websocket_protection',
                                       experiment_id=experiment_id, error=str(e)))
    
    async def _execute_full_broadcast(self, experiment_id: str, device_id: str = None):
        """Execute full data broadcast"""
        try:
            # Broadcast experiment detail update
            await self._safe_broadcast_experiment_detail(experiment_id)
            
            # Broadcast experiment overview update
            await self._safe_broadcast_experiments_overview()
            
            # Broadcast device updates (if device ID is provided)
            if device_id:
                await self._safe_broadcast_device_updates(device_id, experiment_id)
                
        except Exception as e:
            logger.warning(get_log_message('file_monitor', 'full_broadcast_partial_failure', 
                                         component='file_monitor.websocket_protection',
                                         experiment_id=experiment_id, error=str(e)))
            # Do not throw exception, allow partial success
    
    async def _safe_broadcast_experiment_detail(self, experiment_id: str):
        """Safe broadcast experiment detail"""
        try:
            experiment_data = await self.database_service.get_experiment_detail(experiment_id)
            if experiment_data:
                await self.websocket_manager.broadcast_to_topic(
                    f"experiments.{experiment_id}",
                    experiment_data
                )
        except Exception as e:
            logger.debug(f"Experiment detail broadcast failed: {e}")
    
    async def _safe_broadcast_experiments_overview(self):
        """Safe broadcast experiment overview"""
        try:
            experiments_data = await self.database_service.get_experiments_overview()
            if experiments_data:
                await self.websocket_manager.broadcast_to_topic(
                    "experiments.overview",
                    experiments_data
                )
        except Exception as e:
            logger.debug(f"Experiments overview broadcast failed: {e}")
    
    async def _safe_broadcast_device_updates(self, device_id: str, experiment_id: str):
        """Safe broadcast device updates - all analysis data"""
        try:
            # Use default time window for analysis data
            time_window = "48h"  # Default time window for device analysis
            
            # 1. Device detail
            device_detail = await self.database_service.get_device_detail(device_id, experiment_id, time_window)
            if device_detail:
                serializable_data = self._serialize_datetime_objects(device_detail)
                await self.websocket_manager.broadcast_to_topic(
                    f"devices.{device_id}.detail",
                    serializable_data
                )
            
            # 2. Port analysis
            port_analysis = await self.database_service.get_device_port_analysis(device_id, time_window, experiment_id)
            if port_analysis:
                serializable_data = self._serialize_datetime_objects(port_analysis)
                await self.websocket_manager.broadcast_to_topic(
                    f"devices.{device_id}.port-analysis",
                    serializable_data
                )
            
            # 3. Protocol distribution
            protocol_distribution = await self.database_service.get_device_protocol_distribution(device_id, time_window, experiment_id)
            if protocol_distribution:
                serializable_data = self._serialize_datetime_objects(protocol_distribution)
                await self.websocket_manager.broadcast_to_topic(
                    f"devices.{device_id}.protocol-distribution",
                    serializable_data
                )
            
            # 4. Traffic trend
            traffic_trend = await self.database_service.get_device_traffic_trend(device_id, time_window, experiment_id)
            if traffic_trend:
                serializable_data = self._serialize_datetime_objects(traffic_trend)
                await self.websocket_manager.broadcast_to_topic(
                    f"devices.{device_id}.traffic-trend",
                    serializable_data
                )
            
            # 5. Network topology
            network_topology = await self.database_service.get_device_network_topology(device_id, time_window, experiment_id)
            if network_topology:
                serializable_data = self._serialize_datetime_objects(network_topology)
                await self.websocket_manager.broadcast_to_topic(
                    f"devices.{device_id}.network-topology",
                    serializable_data
                )
            
            # 6. Activity timeline
            activity_timeline = await self.database_service.get_device_activity_timeline(device_id, time_window, experiment_id)
            if activity_timeline:
                serializable_data = self._serialize_datetime_objects(activity_timeline)
                await self.websocket_manager.broadcast_to_topic(
                    f"devices.{device_id}.activity-timeline",
                    serializable_data
                )
                
        except Exception as e:
            logger.debug(f"Device analysis broadcast failed for device {device_id}: {e}")
    
    def _serialize_datetime_objects(self, data):
        """Recursive serialization of datetime objects"""
        if isinstance(data, dict):
            return {key: self._serialize_datetime_objects(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._serialize_datetime_objects(item) for item in data]
        elif hasattr(data, 'isoformat'):  # datetime object
            return data.isoformat()
        else:
            return data


class FileMonitorService:
    """File Monitor Service with WebSocket Protection"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize file monitoring service
        
        Args:
            config_path: External configuration file path (optional)
        """
        # Load configuration
        self.config = self._load_external_config(config_path)
        
        # Service components
        self.observer = None
        self.file_handler = None
        self.db_manager = None
        self.pcap_engine = None
        self.queue_task = None
        self.is_running = False
        self.event_loop = None
        
        # Configure logging for file monitor service
        self._setup_file_monitor_logging()
        
        # Setup scheduler configuration
        self._setup_scheduler_config()
        
        # WebSocket broadcast protection layer
        self._websocket_protection = WebSocketBroadcastProtection()
        self._concurrent_broadcast_semaphore = asyncio.Semaphore(5)  # Limit concurrent broadcast count
        self._last_broadcast_time = {}  # Debounce mechanism
        self._broadcast_queue = asyncio.Queue(maxsize=100)  # Broadcast queue
        self._broadcast_worker_task = None
        
        # Configuration-based monitoring directories
        project_root = Path(__file__).parent.parent.parent
        pcap_input_dir = get_config('file_monitor.directories.pcap_input_dir', 'pcap_input', 'file_monitor.directories')
        self.monitor_directories = [project_root / pcap_input_dir]
        
        # Configuration-based file handling settings
        self.supported_extensions = set(
            get_config('file_monitoring.supported_extensions',
                     ['.pcap', '.pcapng', '.cap'], 
                     'file_monitor.file_handling')
        )
        
        # Configuration-based processing queue and statistics
        self.processing_queue = asyncio.Queue()
        self.processed_files = set()
        
        # WebSocket broadcast statistics
        self.websocket_stats = {
            'broadcasts_sent': 0,
            'broadcasts_failed': 0,
            'last_broadcast': None
        }
        
        # Processing statistics
        self.processing_stats = {
            'files_detected': 0,
            'files_processed': 0,
            'files_failed': 0,
            'last_processed': None,
            'last_scan': None
        }
        
        # Get timezone configuration  
        self.timezone = timezone.utc
        timezone_str = get_config('file_monitor.timezone', 'UTC', 'file_monitor')
        if timezone_str.lower() == 'local':
            try:
                import tzlocal
                self.timezone = tzlocal.get_localzone()
            except ImportError:
                logger.warning("tzlocal not available, using UTC")
                self.timezone = timezone.utc
        
        # Display configuration summary
        directory_list = [str(d) for d in self.monitor_directories]
        
        logger.info(get_log_message('file_monitor', 'service_initialized', 
                                   component='file_monitor.service',
                                   directories=directory_list))
    
    def _setup_file_monitor_logging(self):
        """Setup file monitor specific logging"""
        # Logging settings
        log_level_str = get_config('file_monitor.logging.log_level', 'INFO', 'file_monitor.logging')
        log_level = getattr(logging, log_level_str.upper(), logging.INFO)
        
        log_dir = get_config('file_monitor.directories.log_dir', 'log', 'file_monitor.directories')
        project_root = Path(__file__).parent.parent.parent
        log_dir_path = project_root / log_dir
        log_dir_path.mkdir(parents=True, exist_ok=True)
        
        log_file_path = log_dir_path / 'file_monitor.log'
        
        # Get the global file monitor logger
        file_monitor_logger = logging.getLogger('file_monitor')
        file_monitor_logger.setLevel(log_level)
        
        # Prevent logging from propagating to parent logger to avoid writing to API logs
        file_monitor_logger.propagate = False
        
        # Remove existing handlers to avoid duplicates
        for handler in file_monitor_logger.handlers[:]:
            file_monitor_logger.removeHandler(handler)
        
        # Add file handler
        file_handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
        file_handler.setLevel(log_level)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        file_monitor_logger.addHandler(file_handler)
        
        # Store log file path for cleanup
        self.log_file_path = log_file_path
        
        # Test log message to verify configuration
        file_monitor_logger.info(f"File monitor logging configured: {log_file_path}")
        
        # Update the global logger reference to ensure it uses the configured handler
        global logger
        logger = file_monitor_logger
    
    def _setup_scheduler_config(self):
        """Setup scheduler configuration"""
        # Get scan schedule configuration
        # Try both config keys for compatibility
        self.schedule_enabled = get_config('file_monitoring.schedule.enabled', 
                                         get_config('file_monitor.schedule.enabled', True, 'file_monitor.schedule'), 
                                         'file_monitoring.schedule')
        self.scan_times = get_config('file_monitoring.schedule.scan_times', 
                                   get_config('file_monitor.schedule.scan_times', 
                                            ['06:00', '12:00', '18:00', '23:59'], 
                                            'file_monitor.schedule'),
                                   'file_monitoring.schedule')
        self.timezone_str = get_config('file_monitoring.schedule.timezone', 
                                     get_config('file_monitor.schedule.timezone', 'local', 'file_monitor.schedule'),
                                     'file_monitoring.schedule')
        
        # Setup timezone for scheduler
        import pytz
        if self.timezone_str == 'local':
            import tzlocal
            local_tz = tzlocal.get_localzone()
            # Convert to pytz timezone for consistent API
            self.timezone = pytz.timezone(str(local_tz))
        else:
            self.timezone = pytz.timezone(self.timezone_str)
        
        # Configuration-based deletion statistics
        if get_config('file_monitor.performance.enable_deletion_stats', True, 'file_monitor.performance'):
            self.deletion_stats = {'files_deleted': 0, 'files_backed_up': 0}
    
    def _load_external_config(self, config_path: Optional[str]) -> Dict:
        """Load external configuration file"""
        external_config = {}
        
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    external_config = json.load(f)
                logger.debug(f"Loaded external config from {config_path}")
            except Exception as e:
                logger.warning(get_log_message('file_monitor', 'config_load_failed', 
                                              component='file_monitor.config',
                                              config_path=config_path, error=str(e)))
        
        # External configuration
        return external_config
    
    async def initialize(self) -> bool:
        """Service initialization"""
        try:
            logger.info(get_log_message('file_monitor', 'service_initializing', 
                                       component='file_monitor.service'))
            
            # Initialize database connection
            self.db_manager = PostgreSQLDatabaseManager()
            if not await self.db_manager.initialize():
                raise Exception("Database connection failed")
            
            # Initialize PCAP processing engine
            processing_config = ProcessingConfig()
            self.pcap_engine = PcapProcessingEngine(self.db_manager, processing_config)
            await self.pcap_engine.initialize()
            
            # Initialize file handler
            self.file_handler = ScheduledPCAPScanner(
                self._process_pcap_file,
                self.config
            )
            
            # Replace ScheduledPCAPScanner's queue with FileMonitorService's queue
            self.file_handler.processing_queue = self.processing_queue
            
            # Set event loop reference
            self.event_loop = asyncio.get_event_loop()
            
            # Start processing queue
            self.queue_task = asyncio.create_task(self._process_queue())
            
            # Start scheduled scanner instead of observer
            self.scanner_task = asyncio.create_task(self._schedule_scanner(self.monitor_directories))
            
            logger.info(get_log_message('file_monitor', 'service_initialized', 
                                       component='file_monitor.service',
                                       directories=[str(d) for d in self.monitor_directories]))
            return True
            
        except Exception as e:
            logger.error(get_log_message('file_monitor', 'service_initialization_failed', 
                                       component='file_monitor.service',
                                       error=str(e)))
            return False
    
    async def _process_pcap_file(self, file_path: Path, file_info: Dict) -> bool:
        """
        PCAP file processing
        
        Args:
            file_path: PCAP file path
            file_info: File information
            
        Returns:
            Whether processing was successful
        """
        try:
            # Infer experiment information from file path
            experiment_info = self._extract_experiment_info(file_path)
            
            # Process file using PCAP engine
            result = await self.pcap_engine.process_single_file(
                pcap_file=file_path,
                experiment_id=experiment_info['experiment_id'],
                device_mac=experiment_info['device_mac']
            )
            
            if result and result.get('success'):
                packets_processed = result.get('packets_processed', 0)
                
                if get_config('file_monitor.logging.log_file_processing', True, 'file_monitor.logging'):
                    logger.info(get_log_message('file_monitor', 'file_processing_info', 
                                              component='file_monitor.processor',
                                              experiment_id=experiment_info['experiment_id'],
                                              device_mac=experiment_info['device_mac'],
                                              packets=packets_processed))
                
                # File deletion processing
                # Consider file successfully processed even if packets_processed == 0 (duplicates)
                # as long as result.get('success') is True
                await self._handle_processed_file_deletion(file_path, True)
                
                # WebSocket broadcast
                device_id = self._extract_device_id_from_result(result, experiment_info)
                await self._trigger_realtime_updates(experiment_info['experiment_id'], device_id)
                
                return True
            else:
                error_msg = result.get('error', 'Unknown error') if result else 'Processing returned empty result'
                
                if get_config('file_monitor.logging.log_file_processing', True, 'file_monitor.logging'):
                    logger.error(get_log_message('file_monitor', 'file_processing_failed', 
                                               component='file_monitor.processor',
                                               file_path=str(file_path), error=error_msg))
                
                await self._handle_processed_file_deletion(file_path, False)
                return False
                
        except Exception as e:
            if get_config('file_monitor.logging.log_file_processing', True, 'file_monitor.logging'):
                logger.error(get_log_message('file_monitor', 'file_processing_failed', 
                                           component='file_monitor.processor',
                                           file_path=str(file_path), error=str(e)))
            
            await self._handle_processed_file_deletion(file_path, False)
            return False
    
    def _extract_device_id_from_result(self, result: Dict, experiment_info: Dict) -> Optional[str]:
        """Extract device ID from processing result"""
        device_id = None
        
        # Get device ID from storage_result
        if result.get('storage_result') and isinstance(result['storage_result'], dict):
            device_id = result['storage_result'].get('device_id')
        
        # If device ID is not found, try to find it by MAC address
        if not device_id and experiment_info.get('device_mac'):
            # Here you can add logic to find device ID by MAC address
            pass
        
        return device_id
    
    async def _handle_processed_file_deletion(self, file_path: Path, success: bool):
        """
        Processed file deletion processing
        
        Args:
            file_path: File path
            success: Whether processing was successful
        """
        try:
            # Check if automatic deletion is enabled
            auto_delete = get_config('file_monitoring.auto_delete_after_processing', 
                                   False, 'file_monitor.file_handling')
            if not auto_delete:
                return
            
            # If processing fails and configuration preserves failed files, do not delete
            keep_failed = get_config('file_monitoring.keep_failed_files', 
                                   True, 'file_monitor.file_handling')
            if not success and keep_failed:
                logger.info(get_log_message('file_monitor', 'file_kept_failed', 
                                          component='file_monitor.deletion',
                                          file_path=str(file_path)))
                return
            
            # Deletion delay
            delete_delay = get_config('file_monitoring.delete_delay_seconds', 
                                    5, 'file_monitor.file_handling')
            if delete_delay > 0:
                await asyncio.sleep(delete_delay)
            
            # Check if file still exists
            if not file_path.exists():
                logger.info(get_log_message('file_monitor', 'file_delete_skipped', 
                                          component='file_monitor.deletion',
                                          file_path=str(file_path)))
                return
            
            # Backup functionality has been removed
            
            # Delete file
            file_path.unlink()
            logger.info(get_log_message('file_monitor', 'file_deleted', 
                                      component='file_monitor.deletion',
                                      file_path=str(file_path)))
            
            # Update deletion statistics
            if hasattr(self, 'deletion_stats'):
                self.deletion_stats['files_deleted'] += 1
            
        except Exception as e:
            logger.error(get_log_message('file_monitor', 'file_delete_failed', 
                                       component='file_monitor.deletion',
                                       file_path=str(file_path), error=str(e)))
    
    async def _trigger_realtime_updates(self, experiment_id: str, device_id: str = None):
        """
        Enhanced real-time updates with protection layer
        
        Args:
            experiment_id: Experiment ID
            device_id: Device ID (optional)
        """
        # Check if real-time updates are enabled
        if not get_config('file_monitor.websocket_broadcast.enable_realtime_updates', 
                         True, 'file_monitor.websocket_broadcast'):
            return
        
        try:
            # Use protection layer for safe broadcast
            await self._websocket_protection.safe_broadcast(
                experiment_id=experiment_id,
                device_id=device_id,
                semaphore=self._concurrent_broadcast_semaphore,
                last_broadcast_time=self._last_broadcast_time
            )
            
        except Exception as e:
            # WebSocket errors should not affect file processing
            if get_config('file_monitor.logging.log_websocket_broadcasts', True, 'file_monitor.logging'):
                logger.warning(get_log_message('file_monitor', 'websocket_broadcast_failed_gracefully', 
                                             component='file_monitor.websocket',
                                             experiment_id=experiment_id, error=str(e)))
            # Continue execution, do not throw exception
    
    def _get_database_service(self):
        """Get database service instance"""
        database_service = None
        
        try:
            # Try to get database service instance from API application
            from ..api.api_config import get_database_service
            database_service = get_database_service()
        except ImportError:
            try:
                from backend.api.api_config import get_database_service
                database_service = get_database_service()
            except ImportError:
                pass
        
        # Create temporary instance
        if not database_service:
            try:
                from database.services.database_service import DatabaseService
                database_service = DatabaseService(self.db_manager)
                if get_config('file_monitor.logging.log_websocket_broadcasts', True, 'file_monitor.logging'):
                    logger.info(get_log_message('file_monitor', 'database_service_created', 
                                              component='file_monitor.websocket'))
            except Exception as e:
                logger.error(get_log_message('file_monitor', 'database_service_creation_failed', 
                                           component='file_monitor.websocket',
                                           error=str(e)))
        
        return database_service
    
    async def _broadcast_experiment_detail(self, websocket_manager, database_service, experiment_id):
        """Broadcast experiment detail update"""
        try:
            experiment_data = await database_service.get_experiment_detail(experiment_id)
            await websocket_manager.broadcast_to_topic(
                f"experiments.{experiment_id}",
                experiment_data
            )
        
            if get_config('file_monitor.logging.log_websocket_broadcasts', True, 'file_monitor.logging'):
                logger.info(get_log_message('file_monitor', 'websocket_broadcast_success', 
                                          component='file_monitor.websocket',
                                          topic=f"experiments.{experiment_id}"))
        except Exception as e:
            if get_config('file_monitor.logging.log_websocket_broadcasts', True, 'file_monitor.logging'):
                logger.warning(get_log_message('file_monitor', 'websocket_broadcast_failed', 
                                             component='file_monitor.websocket',
                                             topic=f"experiments.{experiment_id}", error=str(e)))
            
    async def _broadcast_experiments_overview(self, websocket_manager, database_service):
        """Broadcast experiment overview update"""
        try:
            experiments_data = await database_service.get_experiments_overview()
            await websocket_manager.broadcast_to_topic(
                "experiments.overview",
                experiments_data
            )
        
            if get_config('file_monitor.logging.log_websocket_broadcasts', True, 'file_monitor.logging'):
                logger.info(get_log_message('file_monitor', 'websocket_broadcast_success', 
                                          component='file_monitor.websocket',
                                          topic="experiments.overview"))
        except Exception as e:
            if get_config('file_monitor.logging.log_websocket_broadcasts', True, 'file_monitor.logging'):
                logger.warning(get_log_message('file_monitor', 'websocket_broadcast_failed', 
                                             component='file_monitor.websocket',
                                             topic="experiments.overview", error=str(e)))
            
    async def _broadcast_devices_overview(self, websocket_manager, database_service):
        """Broadcast device overview update"""
        try:
            devices_data = await database_service.get_all_devices()
            await websocket_manager.broadcast_to_topic(
                "devices.overview",
                devices_data
            )
        
            if get_config('file_monitor.logging.log_websocket_broadcasts', True, 'file_monitor.logging'):
                logger.info(get_log_message('file_monitor', 'websocket_broadcast_success', 
                                          component='file_monitor.websocket',
                                          topic="devices.overview"))
        except Exception as e:
            if get_config('file_monitor.logging.log_websocket_broadcasts', True, 'file_monitor.logging'):
                logger.warning(get_log_message('file_monitor', 'websocket_broadcast_failed', 
                                             component='file_monitor.websocket',
                                             topic="devices.overview", error=str(e)))
            
    async def _broadcast_device_detail(self, websocket_manager, database_service, device_id, experiment_id):
        """Broadcast device detail update"""
        try:
            device_detail_data = await database_service.get_device_detail(device_id, experiment_id)
            
            if device_detail_data:
                # Serialize datetime objects
                serializable_data = self._serialize_datetime_objects(device_detail_data)
                
                await websocket_manager.broadcast_to_topic(
                    f"devices.{device_id}.detail",
                    serializable_data
                )
            
            if get_config('file_monitor.logging.log_websocket_broadcasts', True, 'file_monitor.logging'):
                logger.info(get_log_message('file_monitor', 'websocket_broadcast_success', 
                                          component='file_monitor.websocket',
                                          topic=f"devices.{device_id}.detail"))
        except Exception as e:
            if get_config('file_monitor.logging.log_websocket_broadcasts', True, 'file_monitor.logging'):
                logger.warning(get_log_message('file_monitor', 'websocket_broadcast_failed', 
                                             component='file_monitor.websocket',
                                             topic=f"devices.{device_id}.detail", error=str(e)))
    
    async def _broadcast_device_analysis(self, websocket_manager, database_service, device_id, experiment_id):
        """Broadcast device analysis update"""
        time_windows = get_config('file_monitor.websocket_broadcast.analysis_time_windows', 
                                {}, 'file_monitor.websocket_broadcast')
        
        # Port analysis
        try:
            port_time_window = time_windows.get('port_analysis', '24h')
            port_analysis_data = await database_service.get_device_port_analysis(device_id, port_time_window, experiment_id)
            serializable_port_data = self._serialize_datetime_objects(port_analysis_data)
            await websocket_manager.broadcast_to_topic(
                f"devices.{device_id}.port-analysis",
                serializable_port_data
            )
        
            if get_config('file_monitor.logging.log_websocket_broadcasts', True, 'file_monitor.logging'):
                logger.info(get_log_message('file_monitor', 'websocket_broadcast_success', 
                                          component='file_monitor.websocket',
                                          topic=f"devices.{device_id}.port-analysis"))
        except Exception as e:
            if get_config('file_monitor.logging.log_websocket_broadcasts', True, 'file_monitor.logging'):
                logger.warning(get_log_message('file_monitor', 'websocket_broadcast_failed', 
                                             component='file_monitor.websocket',
                                             topic=f"devices.{device_id}.port-analysis", error=str(e)))
                        
        # Protocol distribution
        try:
            protocol_time_window = time_windows.get('protocol_distribution', '1h')
            protocol_data = await database_service.get_device_protocol_distribution(device_id, protocol_time_window, experiment_id)
            serializable_protocol_data = self._serialize_datetime_objects(protocol_data)
            await websocket_manager.broadcast_to_topic(
                f"devices.{device_id}.protocol-distribution",
                serializable_protocol_data
            )
        
            if get_config('file_monitor.logging.log_websocket_broadcasts', True, 'file_monitor.logging'):
                logger.info(get_log_message('file_monitor', 'websocket_broadcast_success', 
                                          component='file_monitor.websocket',
                                          topic=f"devices.{device_id}.protocol-distribution"))
        except Exception as e:
            if get_config('file_monitor.logging.log_websocket_broadcasts', True, 'file_monitor.logging'):
                logger.warning(get_log_message('file_monitor', 'websocket_broadcast_failed', 
                                             component='file_monitor.websocket',
                                             topic=f"devices.{device_id}.protocol-distribution", error=str(e)))
                        
        # Network topology
        try:
            topology_time_window = time_windows.get('network_topology', '24h')
            topology_data = await database_service.get_device_network_topology(device_id, topology_time_window, experiment_id)
            serializable_topology_data = self._serialize_datetime_objects(topology_data)
            await websocket_manager.broadcast_to_topic(
                f"devices.{device_id}.network-topology",
                serializable_topology_data
            )
        
            if get_config('file_monitor.logging.log_websocket_broadcasts', True, 'file_monitor.logging'):
                logger.info(get_log_message('file_monitor', 'websocket_broadcast_success', 
                                          component='file_monitor.websocket',
                                          topic=f"devices.{device_id}.network-topology"))
        except Exception as e:
            if get_config('file_monitor.logging.log_websocket_broadcasts', True, 'file_monitor.logging'):
                logger.warning(get_log_message('file_monitor', 'websocket_broadcast_failed', 
                                             component='file_monitor.websocket',
                                             topic=f"devices.{device_id}.network-topology", error=str(e)))
                        
        # Activity timeline
        try:
            timeline_time_window = time_windows.get('activity_timeline', '24h')
            timeline_data = await database_service.get_device_activity_timeline(device_id, timeline_time_window, experiment_id)
            serializable_timeline_data = self._serialize_datetime_objects(timeline_data)
            await websocket_manager.broadcast_to_topic(
                f"devices.{device_id}.activity-timeline",
                serializable_timeline_data
            )
        
            if get_config('file_monitor.logging.log_websocket_broadcasts', True, 'file_monitor.logging'):
                logger.info(get_log_message('file_monitor', 'websocket_broadcast_success', 
                                          component='file_monitor.websocket',
                                          topic=f"devices.{device_id}.activity-timeline"))
        except Exception as e:
            if get_config('file_monitor.logging.log_websocket_broadcasts', True, 'file_monitor.logging'):
                logger.warning(get_log_message('file_monitor', 'websocket_broadcast_failed', 
                                             component='file_monitor.websocket',
                                             topic=f"devices.{device_id}.activity-timeline", error=str(e)))
                        
        # Traffic trend
        try:
            traffic_time_window = time_windows.get('traffic_trend', '24h')
            traffic_data = await database_service.get_device_traffic_trend(device_id, traffic_time_window, experiment_id)
            serializable_traffic_data = self._serialize_datetime_objects(traffic_data)
            await websocket_manager.broadcast_to_topic(
                f"devices.{device_id}.traffic-trend",
                serializable_traffic_data
            )
        
            if get_config('file_monitor.logging.log_websocket_broadcasts', True, 'file_monitor.logging'):
                logger.info(get_log_message('file_monitor', 'websocket_broadcast_success', 
                                          component='file_monitor.websocket',
                                          topic=f"devices.{device_id}.traffic-trend"))
        except Exception as e:
            if get_config('file_monitor.logging.log_websocket_broadcasts', True, 'file_monitor.logging'):
                logger.warning(get_log_message('file_monitor', 'websocket_broadcast_failed', 
                                             component='file_monitor.websocket',
                                             topic=f"devices.{device_id}.traffic-trend", error=str(e)))
    

    
    def _extract_experiment_info(self, file_path: Path) -> Dict:
        """
        Experiment information extraction
        
        Args:
            file_path: PCAP file path
            
        Returns:
            Experiment information dictionary
        """
        try:

            # Experiment information extraction
            extract_from_path = get_config('file_monitoring.extract_experiment_from_path', 
                                         True, 'file_monitoring')
            
            if extract_from_path:
                # Use actual monitoring directory and ensure it's an absolute path
                monitor_dir = self.monitor_directories[0].resolve()
                file_path = file_path.resolve()
 
                try:
                    relative_path = file_path.relative_to(monitor_dir)
                    path_parts = relative_path.parts
               
                    if len(path_parts) >= 2:
                        # Format: pcap_input/experiment_name/file.pcap
                        experiment_id = path_parts[0]
                        # logger.info(f"[DEBUG] Using first path part as experiment ID: {experiment_id}")
                    else:
                        # Format: pcap_input/file.pcap - using configuration-based default prefix
                        default_prefix = get_config('file_monitoring.default_experiment_prefix', 
                                                  'auto_', 'file_monitoring')
                        experiment_id = f"{default_prefix}{datetime.now().strftime('%Y%m%d')}"
                        # logger.warning(f"[DEBUG] Path parts less than 2, using default experiment ID: {experiment_id}")
                    
                except ValueError as ve:
                    # Path not in monitoring directory, using default experiment ID
                    # logger.error(f"[ERROR] File path not in monitoring directory: {ve}")
                    default_prefix = get_config('file_monitoring.default_experiment_prefix', 
                                              'auto_', 'file_monitoring')
                    experiment_id = f"{default_prefix}{datetime.now().strftime('%Y%m%d')}"
                    # logger.warning(f"[ERROR] Using default experiment ID: {experiment_id}")
            else:
                # Not from path extraction, using default experiment ID
                default_prefix = get_config('file_monitoring.default_experiment_prefix', 
                                          'auto_', 'file_monitoring')
                experiment_id = f"{default_prefix}{datetime.now().strftime('%Y%m%d')}"
                # logger.info(f"[DEBUG] Configuration disabled path extraction, using default experiment ID: {experiment_id}")
            
            # MAC address extraction
            extract_mac = get_config('file_monitoring.extract_mac_from_filename', 
                                   True, 'file_monitoring')
            if extract_mac:
                device_mac = self._extract_mac_from_filename(file_path.name)
            else:
                device_mac = "00:00:00:00:00:00"  # Default MAC address
            
            # logger.info(f"[DEBUG] Final extraction result: experiment_id={experiment_id}, device_mac={device_mac}")
            
            return {
                'experiment_id': experiment_id,
                'device_mac': device_mac,
                'file_name': file_path.name
            }
            
        except Exception as e:
            # Add generic exception handling
            # logger.error(f"[CRITICAL] Unexpected error in experiment information extraction: {e}")
            # logger.error(f"[CRITICAL] File path: {file_path}")
            
            default_prefix = get_config('file_monitoring.default_experiment_prefix', 
                                      'auto_', 'file_monitoring')
            experiment_id = f"{default_prefix}{datetime.now().strftime('%Y%m%d')}"
            device_mac = self._extract_mac_from_filename(file_path.name)
            
            return {
                'experiment_id': experiment_id,
                'device_mac': device_mac,
                'file_name': file_path.name
            }
    
    def _extract_mac_from_filename(self, filename: str) -> str:
        """Extract MAC address from filename"""
        import re
        
        # Common MAC address formats
        mac_patterns = [
            r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})',  # Standard format
            r'([0-9A-Fa-f]{2}){6}',  # No separator format
        ]
        
        for pattern in mac_patterns:
            match = re.search(pattern, filename)
            if match:
                mac = match.group(0)
                # Standardize to colon-separated format
                if ':' not in mac and '-' not in mac:
                    mac = ':'.join([mac[i:i+2] for i in range(0, 12, 2)])
                return mac.upper()
        
        # If MAC address cannot be extracted, generate a default value
        return "00:00:00:00:00:00"
    
    def _serialize_datetime_objects(self, data):
        """Recursively serialize datetime objects in data structure to ISO string"""
        if isinstance(data, dict):
            return {key: self._serialize_datetime_objects(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._serialize_datetime_objects(item) for item in data]
        elif hasattr(data, 'isoformat'):  # datetime object
            return data.isoformat()
        else:
            return data
    
    async def start_monitoring(self, block=True):
        """Monitoring start"""
        try:
            if self.is_running:
                logger.warning(get_log_message('file_monitor', 'service_already_running', 
                                             component='file_monitor.service'))
                return
            
            logger.info(get_log_message('file_monitor', 'monitor_starting', 
                                       component='file_monitor.service'))
            
            # Set observer
            self.observer = None # No longer using Observer
            
            # Configuration-based monitoring directory setting
            # No longer scheduling scans, so this is no longer relevant for the main service
            
            # Set event loop reference
            self.event_loop = asyncio.get_event_loop()
            
            # Start processing queue
            self.queue_task = asyncio.create_task(self._process_queue())
            
            # Start scheduled scanner instead of observer
            self.scanner_task = asyncio.create_task(self._schedule_scanner(self.monitor_directories))
            
            self.is_running = True
            logger.info(get_log_message('file_monitor', 'monitor_started', 
                                       component='file_monitor.service'))
            
            # Log scheduled scanning configuration
            logger.info(f"Scheduled scanning enabled with times: {self.file_handler.scan_times}")
            logger.info(f"Monitoring directories: {[str(d) for d in self.monitor_directories]}")
            
            # Determine if blocking based on parameter
            if block:
                # Keep service running (for standalone operation)
                try:
                    while self.is_running:
                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    logger.info(get_log_message('file_monitor', 'interrupt_signal_received', 
                                              component='file_monitor.service'))
                finally:
                    await self.stop_monitoring()
            else:
                # Non-blocking mode (for API background tasks)
                logger.info(get_log_message('file_monitor', 'monitor_running_non_blocking', 
                                          component='file_monitor.service'))
                
        except Exception as e:
            logger.error(get_log_message('file_monitor', 'service_start_failed', 
                                       component='file_monitor.service',
                                       error=str(e)))
            raise
    
    async def start_monitoring_non_blocking(self):
        """Non-blocking monitoring start"""
        await self.start_monitoring(block=False)
    
    async def _scan_existing_files(self):
        """Existing file scanning"""
        try:
            logger.info(get_log_message('file_monitor', 'scanning_start', 
                                       component='file_monitor.scanner'))
            
            total_files = 0
            new_files = 0
            already_processed = 0
            
            # Scanning settings
            recursive_scan = get_config('file_monitor.scanning.recursive_scan', 
                                      True, 'file_monitor.scanning')
            ignore_hidden = get_config('file_monitor.scanning.ignore_hidden_files', 
                                     True, 'file_monitor.scanning')
            ignore_temp = get_config('file_monitor.scanning.ignore_temp_files', 
                                   True, 'file_monitor.scanning')
            
            for monitor_dir in self.monitor_directories:
                logger.info(get_log_message('file_monitor', 'scanning_directory', 
                                          component='file_monitor.scanner',
                                          directory=str(monitor_dir.resolve())))
                
                if not monitor_dir.exists():
                    logger.warning(get_log_message('file_monitor', 'directory_not_exists', 
                                                 component='file_monitor.scanner',
                                                 directory=str(monitor_dir.resolve())))
                    continue
                
                # File search
                file_iterator = monitor_dir.rglob("*") if recursive_scan else monitor_dir.glob("*")
                
                for file_path in file_iterator:
                    if not file_path.is_file():
                        continue
                    
                    # Check file extension
                    if file_path.suffix.lower() not in self.file_handler.supported_extensions:
                        continue
                    
                    # File filtering
                    if ignore_hidden and file_path.name.startswith('.'):
                        continue
                    
                    if ignore_temp and (file_path.name.endswith('.tmp') or file_path.name.endswith('.temp')):
                        continue
                    
                    total_files += 1
                    
                    # Check if file is processed in database
                    is_processed = await self._check_file_processed_in_database(file_path)
                    
                    if is_processed:
                        already_processed += 1
                        logger.debug(get_log_message('file_monitor', 'file_already_processed', 
                                                   component='file_monitor.scanner',
                                                   file_path=str(file_path)))
                        # Add to memory cache to avoid duplicate processing
                        self.file_handler.processed_files.add(str(file_path))
                    else:
                        new_files += 1
                        logger.info(get_log_message('file_monitor', 'file_unprocessed', 
                                                  component='file_monitor.scanner',
                                                  file_path=str(file_path)))
                        await self.file_handler._queue_file_for_processing(file_path)
            
            logger.info(get_log_message('file_monitor', 'scanning_complete', 
                                       component='file_monitor.scanner',
                                       total=total_files, new=new_files, processed=already_processed))
            
        except Exception as e:
            logger.error(get_log_message('file_monitor', 'scanning_error', 
                                       component='file_monitor.scanner',
                                       error=str(e)))
            import traceback
            if get_config('file_monitor.logging.log_error_details', True, 'file_monitor.logging'):
                logger.error(get_log_message('file_monitor', 'error_details', 
                                           component='file_monitor.scanner',
                                           details=traceback.format_exc()))
    
    async def _check_file_processed_in_database(self, file_path: Path) -> bool:
        """Check if file is processed in database"""
        try:
            # Extract experiment information from filename
            experiment_info = self._extract_experiment_info(file_path)
            experiment_id = experiment_info.get('experiment_id')
            device_mac = experiment_info.get('device_mac')
            
            if not experiment_id or not device_mac:
                logger.debug(f"Cannot extract experiment information, regarded as unprocessed: {file_path}")
                return False
            
            # Check if there are corresponding packet_flows records in the database
            check_query = """
            SELECT COUNT(*) as count 
            FROM packet_flows pf
            JOIN devices d ON pf.device_id = d.device_id
            WHERE d.mac_address = $1 AND pf.experiment_id = $2
            """
            
            result = await self.db_manager.execute_query(check_query, (device_mac, experiment_id))
            
            if result and result[0]['count'] > 0:
                logger.debug(f"File processed ({result[0]['count']} records): {file_path}")
                return True
            else:
                logger.debug(f"File not processed: {file_path}")
                return False
                
        except Exception as e:
            logger.warning(get_log_message('file_monitor', 'file_status_check_failed', 
                                         component='file_monitor.database',
                                         file_path=str(file_path), error=str(e)))
            return False
    
    async def stop_monitoring(self):
        """Monitoring stop"""
        if not self.is_running:
            logger.warning(get_log_message('file_monitor', 'service_not_running', 
                                         component='file_monitor.service'))
            return
        
        logger.info(get_log_message('file_monitor', 'monitor_stopping', 
                                   component='file_monitor.service'))
        
        self.is_running = False
        
        # Stop WebSocket broadcast worker
        if hasattr(self, '_broadcast_worker_task') and self._broadcast_worker_task:
            self._broadcast_worker_task.cancel()
            try:
                await self._broadcast_worker_task
            except asyncio.CancelledError:
                pass
        
        # Stop queue task
        if self.queue_task:
            self.queue_task.cancel()
            try:
                await self.queue_task
            except asyncio.CancelledError:
                pass
        
        # Stop scanner task
        if hasattr(self, 'scanner_task') and self.scanner_task:
            self.scanner_task.cancel()
            try:
                await self.scanner_task
            except asyncio.CancelledError:
                pass
        
        # Stop observer (not used in current implementation)
        if self.observer:
            self.observer.stop()
            self.observer.join()
        
        # Clean up log file handlers
        self._cleanup_log_handlers()
        
        logger.info(get_log_message('file_monitor', 'monitor_stopped', 
                                   component='file_monitor.service'))
    
    def _cleanup_log_handlers(self):
        """Clean up file monitor log handlers"""
        try:
            # Use the same logger instance
            # Remove all handlers
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
            
            # Use the API logger for cleanup messages since file_monitor logger may be cleaned up
            import logging
            api_logger = logging.getLogger(__name__)
            api_logger.info("File monitor log handlers cleaned up")
        except Exception as e:
            import logging
            api_logger = logging.getLogger(__name__)
            api_logger.warning(f"Failed to clean up log handlers: {e}")
    
    def cleanup_log_file(self):
        """Clean up the file monitor log file (called from stop scripts)"""
        try:
            if hasattr(self, 'log_file_path') and self.log_file_path.exists():
                self.log_file_path.unlink()
                logger.info(f"Cleaned up file monitor log: {self.log_file_path}")
        except Exception as e:
            logger.warning(f"Failed to clean up log file: {e}")
    
    def get_stats(self) -> Dict:
        """Get monitoring statistics"""
        if self.file_handler:
            return {
                'service_status': 'running' if self.is_running else 'stopped',
                'monitor_directories': [str(d) for d in self.monitor_directories],
                'processing_stats': self.file_handler.processing_stats.copy(),
                'queue_size': self.file_handler.processing_queue.qsize(),
                'processed_files_count': len(self.file_handler.processed_files)
            }
        else:
            return {'service_status': 'not_initialized'}

    def get_statistics(self) -> Dict:
        """Get statistics (compatible with API)"""
        stats = self.get_stats()
        processing_stats = stats.get('processing_stats', {})
        
        result = {
            'files_detected': processing_stats.get('files_detected', 0),
            'files_processed': processing_stats.get('files_processed', 0),
            'files_failed': processing_stats.get('files_failed', 0),
            'queue_size': stats.get('queue_size', 0),
            'processed_files_count': stats.get('processed_files_count', 0),
            'service_status': stats.get('service_status', 'unknown')
        }
        
        # Add deletion statistics
        if hasattr(self, 'deletion_stats'):
            result.update({
                'files_deleted': self.deletion_stats.get('files_deleted', 0),
                'files_backed_up': self.deletion_stats.get('files_backed_up', 0)
            })
        else:
            result.update({
                'files_deleted': 0,
                'files_backed_up': 0
            })
        
        return result
    
    def get_status(self) -> Dict:
        """Get service status"""
        return {
            'is_running': self.is_running,
            'observer_alive': self.observer.is_alive() if self.observer else False,
            'handler_initialized': self.file_handler is not None,
            'queue_task_running': self.queue_task and not self.queue_task.done() if hasattr(self, 'queue_task') else False,
            'monitor_directories': [str(d) for d in self.monitor_directories]
        }
    
    async def start(self):
        """Start service (including initialization)"""
        if not await self.initialize():
            raise Exception("Service initialization failed")
        await self.start_monitoring_non_blocking()
    
    async def trigger_manual_scan(self):
        """Manually trigger a scan of all monitored directories"""
        if not hasattr(self, 'monitor_directories') or not self.monitor_directories:
            # Fallback to default pcap_input directory
            from pathlib import Path
            pcap_input_dir = get_config('file_monitor.directories.pcap_input_dir', 'pcap_input', 'file_monitor.directories')
            project_root = Path(__file__).parent.parent.parent  # Go up to project root
            monitor_directories = [project_root / pcap_input_dir]
        else:
            monitor_directories = self.monitor_directories
        
        logger.info("Manual scan triggered")
        
        scan_start = datetime.now(self.timezone)
        total_files = 0
        new_files = 0
        already_processed = 0
        
        # Scanning settings
        ignore_hidden = get_config('file_monitor.scanning.ignore_hidden_files', 
                                 True, 'file_monitor.scanning')
        ignore_temp = get_config('file_monitor.scanning.ignore_temp_files', 
                               True, 'file_monitor.scanning')
        
        for monitor_dir in monitor_directories:
            logger.info(f"Manual scanning directory: {monitor_dir}")
            
            if not monitor_dir.exists():
                logger.warning(f"Directory not exists: {monitor_dir}")
                continue
            
            # Recursive scan of all subdirectories
            for file_path in monitor_dir.rglob("*"):
                if not file_path.is_file():
                    continue
                
                # Check file extension
                if file_path.suffix.lower() not in self.supported_extensions:
                    continue
                
                # File filtering
                if ignore_hidden and file_path.name.startswith('.'):
                    continue
                
                if ignore_temp and (file_path.name.endswith('.tmp') or file_path.name.endswith('.temp')):
                    continue
                
                total_files += 1
                
                # Check if file was already processed
                if str(file_path) in self.processed_files:
                    already_processed += 1
                    continue
                
                # Queue file for processing
                new_files += 1
                await self._queue_file_for_processing(file_path)
        
        scan_result = {
            'scan_time': scan_start.isoformat(),
            'total_files': total_files,
            'new_files': new_files,
            'already_processed': already_processed,
            'directories_scanned': [str(d) for d in monitor_directories]
        }
        
        logger.info(f"Manual scan completed: total={total_files}, new={new_files}, processed={already_processed}")
        return scan_result

    async def _queue_file_for_processing(self, file_path: Path):
        """Add file to processing queue"""
        try:
            await self.processing_queue.put({
                'file_path': file_path,
                'detected_time': datetime.now(self.timezone),
                'retry_count': 0
            })
            
            if get_config('file_monitor.logging.log_file_detection', True, 'file_monitor.logging'):
                logger.info(f"Queued file for processing: {file_path}")
                
        except Exception as e:
            logger.error(f"Failed to queue file {file_path}: {e}")
    
    async def _process_queue(self):
        """Process files from the queue"""
        logger.info("File processing queue started")
        
        while self.is_running:
            try:
                # Get file from queue with timeout
                file_info = await asyncio.wait_for(self.processing_queue.get(), timeout=1.0)
                file_path = file_info['file_path']
                
                logger.info(f"Processing file from queue: {file_path}")
                
                # Check if file still exists
                if not file_path.exists():
                    logger.warning(f"File no longer exists: {file_path}")
                    self.processing_queue.task_done()
                    continue
                
                # Process the file
                success = await self._process_pcap_file(file_path, file_info)
                
                if success:
                    self.processing_stats['files_processed'] += 1
                    self.processing_stats['last_processed'] = datetime.now(timezone.utc)
                    logger.info(f"File processing successful: {file_path}")
                else:
                    self.processing_stats['files_failed'] += 1
                    logger.error(f"File processing failed: {file_path}")
                
                self.processing_queue.task_done()
                
            except asyncio.TimeoutError:
                # No files in queue, continue waiting
                continue
            except Exception as e:
                logger.error(f"Queue processing error: {e}")
                continue
        
        logger.info("File processing queue stopped")
    
    async def _schedule_scanner(self, directories):
        """Start the scheduled scanner using the ScheduledPCAPScanner implementation"""
        logger.info("Starting automatic scheduled scanner...")
        
        if not self.file_handler:
            logger.error("File handler not initialized, cannot start scheduled scanner")
            return
        
        try:
            # Use the ScheduledPCAPScanner's proper scheduler implementation
            await self.file_handler.schedule_scanner(directories)
        except asyncio.CancelledError:
            logger.info("Scheduled scanner cancelled")
        except Exception as e:
            logger.error(f"Scheduled scanner error: {e}")
        finally:
            logger.info("Scheduled scanner stopped")
    
    async def stop(self):
        """Stop service"""
        await self.stop_monitoring()


async def main():
    """Main function for standalone monitoring service"""
    # Logging settings
    log_level_str = get_config('file_monitor.logging.log_level', 'INFO', 'file_monitor.logging')
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    
    log_dir = get_config('file_monitor.directories.log_dir', 'log', 'file_monitor.directories')
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    log_file_path = Path(log_dir) / 'file_monitor.log'
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file_path)
        ]
    )
    
    # Create and start monitoring service
    monitor_service = FileMonitorService()
    
    try:
        if await monitor_service.initialize():
            logger.info(get_log_message('file_monitor', 'standalone_service_starting', 
                                       component='file_monitor.main'))
            await monitor_service.start_monitoring()
        else:
            logger.error(get_log_message('file_monitor', 'standalone_init_failed', 
                                       component='file_monitor.main'))
            
    except KeyboardInterrupt:
        logger.info(get_log_message('file_monitor', 'user_interrupted', 
                                   component='file_monitor.main'))
    except Exception as e:
        logger.error(get_log_message('file_monitor', 'standalone_service_error', 
                                   component='file_monitor.main',
                                   error=str(e)))
    finally:
        await monitor_service.stop_monitoring()


if __name__ == "__main__":
    asyncio.run(main()) 
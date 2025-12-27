"""
Core PCAP Processing Engine
"""

import asyncio
import logging
import sys
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path for database imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from database.connection import PostgreSQLDatabaseManager

# Import unified manager
from config.unified_config_manager import UnifiedConfigManager

# Use absolute imports for internal modules
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

from pcap_process.core.config import ProcessingConfig
from pcap_process.core.coordinator import ConfigurableProcessingCoordinator
from pcap_process.parsers.packet_parser import PacketParser
from pcap_process.storage.packet_storage import PacketStorage
from pcap_process.analyzers.modular_data_analyzer import ModularDataAnalyzer

# Initialize manager
config_manager = UnifiedConfigManager()

logger = logging.getLogger(__name__)


class ConfigurablePcapProcessingEngine:
    """
    Core engine for PCAP file processing with complete data analysis
    
    Responsibilities:
    - Orchestrate processing pipeline
    - Manage resources and connections
    - Generate all required database tables
    - Provide simple API for processing operations
    """
    
    def __init__(self, db_manager: PostgreSQLDatabaseManager, config: Optional[ProcessingConfig] = None):
        """Initialize processing engine with configuration"""
        self.db_manager = db_manager
        self.config = config or ProcessingConfig()
        
        # Load unified configuration
        self.unified_config = config_manager.get_config()
        self.log_templates = config_manager.get_log_templates()
        
        # Get service-specific configuration
        self.pcap_config = self.unified_config.get('pcap_processing', {})
        self.processing_params = self.pcap_config.get('processing_parameters', {})
        self.feature_flags = self.pcap_config.get('feature_flags', {})
        self.parser_config = self.pcap_config.get('parser_config', {})
        self.storage_config = self.pcap_config.get('storage_config', {})
        self.timezone_config = self.pcap_config.get('timezone_config', {})
        self.error_handling = self.pcap_config.get('error_handling', {})
        self.logging_config = self.pcap_config.get('logging', {})
        self.performance_config = self.pcap_config.get('performance', {})
        
        # Update processing config with unified settings
        self._update_processing_config()
        
        # Core components
        self.coordinator = ConfigurableProcessingCoordinator(self.config)
        self.packet_parser = PacketParser()
        self.storage = PacketStorage(db_manager)
        self.data_analyzer = ModularDataAnalyzer(db_manager)
        
        # State
        self.is_initialized = False
        self.stats = {
            'experiments_processed': 0,
            'files_processed': 0,
            'packets_processed': 0,
            'start_time': None,
            'end_time': None
        }
        
        # UTC timezone for consistent time handling
        self.utc_timezone = timezone.utc
        
        if self._should_log_engine_operations():
            logger.info(self._get_log_message('engine_initialized'))
    
    def _get_log_message(self, template_key: str, **kwargs) -> str:
        """Get formatted log message from templates"""
        try:
            template = self.log_templates.get('pcap_processing', {}).get(template_key)
            if isinstance(template, str):
                return template.format(**kwargs)
            elif isinstance(template, dict):
                message_format = template.get('emoji', template_key)
                return message_format.format(**kwargs)
            else:
                return template_key
        except Exception:
            return f"[Missing log message: pcap_processing.{template_key}]"
    
    def _update_processing_config(self):
        """Update processing config with unified configuration values"""
        # Update batch sizes
        self.config.batch_size = self.processing_params.get('batch_size', self.config.batch_size)
        self.config.max_workers = self.processing_params.get('max_workers', self.config.max_workers)
        self.config.timeout_seconds = self.processing_params.get('timeout_seconds', self.config.timeout_seconds)
        self.config.db_batch_size = self.processing_params.get('db_batch_size', self.config.db_batch_size)
        
        # Update feature flags
        self.config.enable_real_time = self.feature_flags.get('enable_real_time', self.config.enable_real_time)
        self.config.enable_packet_flows = self.feature_flags.get('enable_packet_flows', self.config.enable_packet_flows)
        self.config.enable_device_analysis = self.feature_flags.get('enable_device_analysis', self.config.enable_device_analysis)
        self.config.enable_topology_analysis = self.feature_flags.get('enable_topology_analysis', self.config.enable_topology_analysis)
        self.config.enable_transaction_batching = self.feature_flags.get('enable_transaction_batching', self.config.enable_transaction_batching)
    
    def _should_log_engine_operations(self) -> bool:
        """Check if engine operations logging is enabled"""
        return self.logging_config.get('log_engine_operations', True)
    
    def _should_log_file_processing(self) -> bool:
        """Check if file processing logging is enabled"""
        return self.logging_config.get('log_file_processing', True)
    
    def _should_log_error_details(self) -> bool:
        """Check if error details logging is enabled"""
        return self.logging_config.get('log_error_details', True)
    
    def _should_enable_performance_logging(self) -> bool:
        """Check if performance logging is enabled"""
        return self.logging_config.get('enable_performance_logging', True)
    
    def _should_continue_on_parse_error(self) -> bool:
        """Check if processing should continue on parse errors"""
        return self.error_handling.get('continue_on_parse_error', True)
    
    def _get_max_retry_attempts(self) -> int:
        """Get maximum retry attempts for failed operations"""
        return self.error_handling.get('max_retry_attempts', 3)
    
    def _should_skip_corrupted_files(self) -> bool:
        """Check if corrupted files should be skipped"""
        return self.error_handling.get('skip_corrupted_files', True)
    
    async def initialize(self) -> bool:
        """Initialize engine components"""
        try:
            await self.storage.initialize()
            self.is_initialized = True
            if self._should_log_engine_operations():
                logger.info(self._get_log_message('engine_init_success'))
            return True
        except Exception as e:
            if self._should_log_error_details():
                logger.error(self._get_log_message('engine_init_failed', error=str(e)))
            return False
    
    async def process_experiment(self, experiment_path: Path, experiment_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a single experiment directory with complete analysis
        
        Args:
            experiment_path: Path to experiment directory
            experiment_id: Optional experiment identifier
            
        Returns:
            Processing results
        """
        if not self.is_initialized:
            raise RuntimeError("Engine not initialized")
        
        experiment_id = experiment_id or experiment_path.name
        if self._should_log_engine_operations():
            logger.info(self._get_log_message('experiment_processing_start', experiment_id=experiment_id))
        
        self.stats['start_time'] = datetime.now(self.utc_timezone)
        
        try:
            # Use coordinator to manage the processing workflow
            result = await self.coordinator.process_experiment_directory(
                experiment_path, experiment_id, self.packet_parser, self.storage
            )
            
            # If packet flows were successfully stored, run complete data analysis
            if result.get('success') and result.get('packets_processed', 0) > 0:
                if self.feature_flags.get('enable_device_analysis', True):
                    if self._should_log_engine_operations():
                        logger.info(self._get_log_message('analysis_start', experiment_id=experiment_id))
                
                analysis_result = await self.data_analyzer.analyze_experiment_data(experiment_id)
                result['analysis_result'] = analysis_result
                
                if self._should_log_engine_operations():
                    devices_count = analysis_result.get('devices_analyzed', 0)
                    logger.info(self._get_log_message('analysis_complete', devices_analyzed=devices_count))
            
            self.stats['experiments_processed'] += 1
            self.stats['files_processed'] += result.get('files_processed', 0)
            self.stats['packets_processed'] += result.get('packets_processed', 0)
            
            return result
            
        except Exception as e:
            if self._should_log_error_details():
                logger.error(self._get_log_message('experiment_processing_error', 
                                                 experiment_id=experiment_id, error=str(e)))
            return {'error': str(e), 'experiment_id': experiment_id}
        finally:
            self.stats['end_time'] = datetime.now(self.utc_timezone)
    
    async def process_all_experiments(self, pcap_input_path: Path) -> Dict[str, Any]:
        """
        Process all experiments in directory with complete analysis
        
        Args:
            pcap_input_path: Base directory containing experiment folders
            
        Returns:
            Overall processing results
        """
        if not self.is_initialized:
            raise RuntimeError("Engine not initialized")
        
        if not pcap_input_path.exists():
            return {'error': f'Directory not found: {pcap_input_path}'}
        
        # Find experiment directories
        experiment_dirs = [
            d for d in pcap_input_path.iterdir() 
            if d.is_dir() and d.name.startswith('experiment_')
        ]
        
        if not experiment_dirs:
            return {'error': 'No experiment directories found'}
        
        if self._should_log_engine_operations():
            logger.info(self._get_log_message('experiments_discovery', count=len(experiment_dirs)))
        
        results = []
        successful = 0
        failed = 0
        total_devices_analyzed = 0
        
        for exp_dir in sorted(experiment_dirs):
            result = await self.process_experiment(exp_dir)
            results.append(result)
            
            if result.get('success'):
                successful += 1
                analysis_result = result.get('analysis_result', {})
                total_devices_analyzed += analysis_result.get('devices_analyzed', 0)
            else:
                failed += 1
        
        return {
            'success': True,
            'total_experiments': len(experiment_dirs),
            'successful': successful,
            'failed': failed,
            'total_devices_analyzed': total_devices_analyzed,
            'experiment_results': results,
            'overall_stats': self.get_stats()
        }
    
    async def process_single_file(self, pcap_file: Path, experiment_id: str, device_mac: str) -> Dict[str, Any]:
        """
        Process a single PCAP file with analysis
        
        Args:
            pcap_file: Path to PCAP file
            experiment_id: Experiment identifier
            device_mac: Device MAC address
            
        Returns:
            Processing results
        """
        if not self.is_initialized:
            raise RuntimeError("Engine not initialized")
        
        if self._should_log_file_processing():
            logger.info(self._get_log_message('file_processing_start', 
                                            filename=pcap_file.name, device_mac=device_mac))
        
        try:
            result = await self.coordinator.process_single_pcap(
                pcap_file, experiment_id, device_mac, self.packet_parser, self.storage
            )
            
            # Run analysis if packets were processed
            if result.get('success') and result.get('packets_processed', 0) > 0:
                if self.feature_flags.get('enable_device_analysis', True):
                    if self._should_log_engine_operations():
                        logger.info(self._get_log_message('single_file_analysis'))
                analysis_result = await self.data_analyzer.analyze_experiment_data(experiment_id)
                result['analysis_result'] = analysis_result
            
            self.stats['files_processed'] += 1
            self.stats['packets_processed'] += result.get('packets_processed', 0)
            
            return result
            
        except Exception as e:
            if self._should_log_error_details():
                logger.error(self._get_log_message('file_processing_error', 
                                                 filename=pcap_file.name, error=str(e)))
            return {'error': str(e), 'file': str(pcap_file)}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        stats = self.stats.copy()
        
        if stats['start_time'] and stats['end_time']:
            stats['duration_seconds'] = (stats['end_time'] - stats['start_time']).total_seconds()
        
        return stats
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            await self.storage.cleanup()
            self.is_initialized = False
            if self._should_log_engine_operations():
                logger.info(self._get_log_message('engine_cleanup'))
        except Exception as e:
            if self._should_log_error_details():
                logger.error(self._get_log_message('cleanup_error', error=str(e)))
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup() 


# Backward compatibility alias
PcapProcessingEngine = ConfigurablePcapProcessingEngine
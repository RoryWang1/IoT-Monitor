"""
Device Detail API Endpoint - Fully Configurable Version
Handles individual device detail retrieval with comprehensive data aggregation
"""

import logging
import sys
import os
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Depends

# Setup unified path configuration
from ...common.path_config import setup_project_paths
setup_project_paths()

# Import the unified config manager
from config.unified_config_manager import get_config, get_log_message

logger = logging.getLogger(__name__)

class ConfigurableDeviceDetailAPI:
    """Fully configurable Device Detail API with zero hardcoded values"""
    
    def __init__(self):
        """Initialize with unified configuration"""
        self.config_component = "api_endpoints.device_detail"
        self._load_configuration()
    
    def _load_configuration(self):
        """Load all configuration for device detail API"""
        # Default values configuration
        self.defaults = get_config(f'{self.config_component}.defaults', {
            'time_window': '48h',
            'device_type': 'unknown',
            'manufacturer': 'Unknown',
            'status': 'unknown',
            'device_name_prefix': 'Device_',
            'device_id_suffix_length': 8,
            'unknown_device_name': 'Unknown Device',
            'unknown_manufacturer': 'Unknown',
            'unknown_device_type': 'unknown'
        }, self.config_component)
        
        # Query limits configuration
        self.query_limits = get_config(f'{self.config_component}.query_limits', {
            'max_packets_threshold': 1000000,
            'max_bytes_threshold': 1073741824,  # 1GB
            'max_sessions_threshold': 10000
        }, self.config_component)
        
        # Data formatting configuration
        self.formatting = get_config(f'{self.config_component}.formatting', {
            'bytes_unit_gb_threshold': 1073741824,  # 1GB
            'bytes_unit_mb_threshold': 1048576,     # 1MB
            'bytes_unit_kb_threshold': 1024,        # 1KB
            'time_format_hour_threshold': 3600,     # 1 hour
            'time_format_minute_threshold': 60,     # 1 minute
            'decimal_places': 2,
            'enable_traffic_formatting': True,
            'enable_duration_formatting': True
        }, self.config_component)
        
        # Response field configuration
        self.response_fields = get_config(f'{self.config_component}.response_fields', {
            'device_id_field': 'deviceId',
            'device_name_field': 'deviceName',
            'device_type_field': 'deviceType',
            'mac_address_field': 'macAddress',
            'ip_address_field': 'ipAddress',
            'manufacturer_field': 'manufacturer',
            'status_field': 'status',
            'experiment_id_field': 'experimentId',
            'total_packets_field': 'totalPackets',
            'total_bytes_field': 'totalBytes',
            'total_sessions_field': 'totalSessions',
            'total_traffic_field': 'totalTraffic',
            'active_duration_field': 'activeDuration',
            'first_seen_field': 'firstSeen',
            'last_seen_field': 'lastSeen',
            'time_window_field': 'timeWindow',
            'resolved_name_field': 'resolvedName',
            'resolved_vendor_field': 'resolvedVendor',
            'resolved_type_field': 'resolvedType',
            'resolution_source_field': 'resolutionSource',
            'source_mapping_field': 'sourceMapping'
        }, self.config_component)
        
        # Error messages configuration
        self.error_messages = get_config(f'{self.config_component}.error_messages', {
            'device_not_found': "Device '{device_id}' not found in experiment '{experiment_id}'",
            'device_not_found_no_experiment': "Device '{device_id}' not found",
            'invalid_device_id': "Invalid device ID format: {device_id}",
            'invalid_time_window': "Invalid time window: {time_window}",
            'database_query_failed': "Database query failed: {error}",
            'enhancement_failed': "Failed to enhance device info: {error}",
            'timezone_conversion_failed': "Timezone conversion failed: {error}"
        }, self.config_component)
        
        # Query configuration
        self.queries = get_config(f'{self.config_component}.queries', {
            'device_base_query': "SELECT * FROM devices WHERE device_id = $1",
            'device_with_experiment_condition': " AND experiment_id = $2",
            'stats_base_query': """
                SELECT 
                    COUNT(*) as total_packets,
                    SUM(packet_size) as total_bytes,
                    COUNT(DISTINCT flow_hash) as total_sessions,
                    MIN(packet_timestamp) as first_seen,
                    MAX(packet_timestamp) as last_seen
                FROM packet_flows 
                WHERE device_id = $1 
                AND packet_timestamp >= $2 
                AND packet_timestamp <= $3
            """,
            'stats_with_experiment_condition': " AND experiment_id = $4"
        }, self.config_component)
        
        # Feature flags configuration
        self.features = get_config(f'{self.config_component}.features', {
            'enable_device_enhancement': True,
            'enable_timezone_conversion': True,
            'enable_traffic_formatting': True,
            'enable_duration_formatting': True,
            'enable_resolution_metadata': True,
            'enable_query_logging': True,
            'enable_performance_logging': True,
            'enable_result_caching': False
        }, self.config_component)
        
        # Logging configuration
        self.logging_config = get_config(f'{self.config_component}.logging', {
            'log_api_calls': True,
            'log_database_queries': True,
            'log_query_results': True,
            'log_enhancement_operations': True,
            'log_formatting_operations': False,
            'log_performance_metrics': True,
            'log_error_details': True
        }, self.config_component)
    
    def _get_log_message(self, template_key: str, **kwargs) -> str:
        """Get formatted log message from templates"""
        return get_log_message('api_endpoints.device_detail', template_key, **kwargs)
    
    def _format_traffic_size(self, bytes_value: int) -> str:
        """Format traffic size with configurable units"""
        if not self.formatting.get('enable_traffic_formatting', True):
            return str(bytes_value)
        
        decimal_places = self.formatting.get('decimal_places', 2)
        
        if bytes_value >= self.formatting.get('bytes_unit_gb_threshold', 1073741824):
            gb_value = bytes_value / self.formatting.get('bytes_unit_gb_threshold', 1073741824)
            return f"{gb_value:.{decimal_places}f} GB"
        elif bytes_value >= self.formatting.get('bytes_unit_mb_threshold', 1048576):
            mb_value = bytes_value / self.formatting.get('bytes_unit_mb_threshold', 1048576)
            return f"{mb_value:.{decimal_places}f} MB"
        elif bytes_value >= self.formatting.get('bytes_unit_kb_threshold', 1024):
            kb_value = bytes_value / self.formatting.get('bytes_unit_kb_threshold', 1024)
            return f"{kb_value:.{decimal_places}f} KB"
        else:
            return f"{bytes_value} B"
    
    def _format_duration(self, duration_seconds: float) -> str:
        """Format duration with configurable thresholds"""
        if not self.formatting.get('enable_duration_formatting', True):
            return f"{int(duration_seconds)}s"
        
        hour_threshold = self.formatting.get('time_format_hour_threshold', 3600)
        minute_threshold = self.formatting.get('time_format_minute_threshold', 60)
        
        if duration_seconds >= hour_threshold:
            hours = int(duration_seconds // hour_threshold)
            minutes = int((duration_seconds % hour_threshold) // minute_threshold)
            return f"{hours}h {minutes}m"
        elif duration_seconds >= minute_threshold:
            minutes = int(duration_seconds // minute_threshold)
            seconds = int(duration_seconds % minute_threshold)
            return f"{minutes}m {seconds}s"
        else:
            return f"{int(duration_seconds)}s"
    
    def _get_fallback_device_name(self, device_id: str) -> str:
        """Generate fallback device name with configuration"""
        prefix = self.defaults.get('device_name_prefix', 'Device_')
        suffix_length = self.defaults.get('device_id_suffix_length', 8)
        return f"{prefix}{device_id[:suffix_length]}"
    
    def _build_device_query(self, device_id: str, experiment_id: Optional[str]) -> tuple:
        """Build device query with configurable structure"""
        base_query = self.queries.get('device_base_query', 
                                    "SELECT * FROM devices WHERE device_id = $1")
        params = [device_id]
        
        if experiment_id:
            condition = self.queries.get('device_with_experiment_condition', 
                                       " AND experiment_id = $2")
            base_query += condition
            params.append(experiment_id)
        
        return base_query, params
    
    def _build_stats_query(self, device_id: str, start_time, end_time, 
                          experiment_id: Optional[str]) -> tuple:
        """Build statistics query with configurable structure"""
        base_query = self.queries.get('stats_base_query', """
            SELECT 
                COUNT(*) as total_packets,
                SUM(packet_size) as total_bytes,
                COUNT(DISTINCT flow_hash) as total_sessions,
                MIN(packet_timestamp) as first_seen,
                MAX(packet_timestamp) as last_seen
            FROM packet_flows 
            WHERE device_id = $1 
            AND packet_timestamp >= $2 
            AND packet_timestamp <= $3
        """)
        
        params = [device_id, start_time, end_time]
        
        if experiment_id:
            condition = self.queries.get('stats_with_experiment_condition', 
                                       " AND experiment_id = $4")
            base_query += condition
            params.append(experiment_id)
        
        return base_query, params
    
    def _build_response(self, device: Dict, stats: Dict, enhanced_info: Dict, 
                       experiment_id: str, time_window: str, 
                       converted_first_seen, converted_last_seen, 
                       traffic_formatted: str, duration_formatted: str) -> Dict[str, Any]:
        """Build response with configurable field structure"""
        # Get enhanced values or fallback to device values or defaults
        device_name = (enhanced_info.get('resolvedName') or 
                      device.get('device_name') or 
                      self._get_fallback_device_name(device['device_id']))
        
        device_type = (enhanced_info.get('resolvedType') or 
                      device.get('device_type') or 
                      self.defaults.get('device_type', 'unknown'))
        
        manufacturer = (enhanced_info.get('resolvedVendor') or 
                       device.get('manufacturer') or 
                       self.defaults.get('manufacturer', 'Unknown'))
        
        # Build response using configured field names
        response = {
            self.response_fields.get('device_id_field', 'deviceId'): device['device_id'],
            self.response_fields.get('device_name_field', 'deviceName'): device_name,
            self.response_fields.get('device_type_field', 'deviceType'): device_type,
            self.response_fields.get('mac_address_field', 'macAddress'): device.get('mac_address'),
            self.response_fields.get('ip_address_field', 'ipAddress'): device.get('ip_address'),
            self.response_fields.get('manufacturer_field', 'manufacturer'): manufacturer,
            self.response_fields.get('status_field', 'status'): device.get('status', self.defaults.get('status', 'unknown')),
            self.response_fields.get('experiment_id_field', 'experimentId'): device.get('experiment_id'),
            self.response_fields.get('total_packets_field', 'totalPackets'): stats.get('total_packets', 0) or 0,
            self.response_fields.get('total_bytes_field', 'totalBytes'): stats.get('total_bytes', 0) or 0,
            self.response_fields.get('total_sessions_field', 'totalSessions'): stats.get('total_sessions', 0) or 0,
            self.response_fields.get('total_traffic_field', 'totalTraffic'): traffic_formatted,
            self.response_fields.get('active_duration_field', 'activeDuration'): duration_formatted,
            self.response_fields.get('first_seen_field', 'firstSeen'): converted_first_seen,
            self.response_fields.get('last_seen_field', 'lastSeen'): converted_last_seen,
            self.response_fields.get('time_window_field', 'timeWindow'): time_window,
        }
        
        # Add resolution metadata if enabled
        if self.features.get('enable_resolution_metadata', True):
            response.update({
                self.response_fields.get('resolved_name_field', 'resolvedName'): enhanced_info.get('resolvedName'),
                self.response_fields.get('resolved_vendor_field', 'resolvedVendor'): enhanced_info.get('resolvedVendor'),
                self.response_fields.get('resolved_type_field', 'resolvedType'): enhanced_info.get('resolvedType'),
                self.response_fields.get('resolution_source_field', 'resolutionSource'): enhanced_info.get('resolutionSource', 'none'),
                self.response_fields.get('source_mapping_field', 'sourceMapping'): enhanced_info.get('sourceMapping', {})
            })
        
        return response

# Create global configurable API instance
configurable_device_detail_api = ConfigurableDeviceDetailAPI()

router = APIRouter()

# Use the unified dependency injection
from ...common.dependencies import get_database_service_instance

@router.get("/{device_id}/detail", response_model=Dict[str, Any])
async def get_device_detail(
    device_id: str, 
    background_tasks: BackgroundTasks,
    experiment_id: str = Query(default=None, description="Experiment ID for data isolation"),
    time_window: str = Query(default=None, description="Time window: 1h, 6h, 12h, 24h, 48h, auto"),
    database_service = Depends(get_database_service_instance)
):
    """
    Retrieve comprehensive device detail information with full configuration support
    
    Args:
        device_id: Device identifier (MAC address or UUID)
        experiment_id: Experiment ID for data isolation
        time_window: Time window for data filtering
    
    Returns:
        Comprehensive device detail data
    """
    api = configurable_device_detail_api
    
    # Use configured default time window if not provided
    if time_window is None:
        time_window = api.defaults.get('time_window', '48h')
    
    try:
        if api.logging_config.get('log_api_calls', True):
            logger.info(api._get_log_message('api_called', 
                                           device_id=device_id, 
                                           experiment_id=experiment_id, 
                                           time_window=time_window))
        
        # Get database manager
        db_manager = database_service.db_manager
        
        # Build and execute device query using configuration
        device_query, device_params = api._build_device_query(device_id, experiment_id)
        
        if api.logging_config.get('log_database_queries', True):
            logger.info(api._get_log_message('executing_query', 
                                           query=device_query, 
                                           params=device_params))
        
        device_result = await db_manager.execute_query(device_query, device_params)
        
        if api.logging_config.get('log_query_results', True):
            logger.info(api._get_log_message('query_result', 
                                           result_count=len(device_result) if device_result else 0))
        
        if not device_result:
            if api.logging_config.get('log_error_details', True):
                logger.warning(api._get_log_message('device_not_found', device_id=device_id))
            
            error_message = api.error_messages.get('device_not_found' if experiment_id else 'device_not_found_no_experiment', 
                                                  "Device not found")
            raise HTTPException(
                status_code=404,
                detail=error_message.format(device_id=device_id, experiment_id=experiment_id)
            )
        
        device = device_result[0]
        
        if api.logging_config.get('log_query_results', True):
            logger.info(api._get_log_message('device_found', device_id=device_id))
        
        # Get timezone-aware time bounds using unified service
        from database.services.timezone_time_window_service import timezone_time_window_service
        start_time, end_time = await timezone_time_window_service.get_timezone_aware_time_bounds(
            experiment_id, time_window, db_manager
        )
        
        # Build and execute statistics query using configuration
        stats_query, stats_params = api._build_stats_query(device_id, start_time, end_time, experiment_id)
        stats_result = await db_manager.execute_query(stats_query, stats_params)
        stats = stats_result[0] if stats_result else {}
        
        # Format duration and traffic using configurable formatting
        first_seen = stats.get('first_seen')
        last_seen = stats.get('last_seen')
        active_duration = 0
        duration_formatted = api._format_duration(0)
        
        if first_seen and last_seen:
            duration_seconds = (last_seen - first_seen).total_seconds()
            active_duration = int(duration_seconds)
            duration_formatted = api._format_duration(duration_seconds)
        
        # Format traffic using configurable formatting
        total_bytes = stats.get('total_bytes', 0) or 0
        traffic_formatted = api._format_traffic_size(total_bytes)
        
        # Apply timezone conversion if enabled
        converted_first_seen = None
        converted_last_seen = None
        
        if api.features.get('enable_timezone_conversion', True):
            try:
                from database.services.timezone_manager import TimezoneManager
                timezone_manager = TimezoneManager()
                
                if first_seen:
                    converted_first_seen = timezone_manager.convert_to_experiment_timezone(
                        first_seen, experiment_id
                    )
                
                if last_seen:
                    converted_last_seen = timezone_manager.convert_to_experiment_timezone(
                        last_seen, experiment_id
                    )
            except Exception as e:
                if api.logging_config.get('log_error_details', True):
                    logger.warning(api._get_log_message('timezone_conversion_failed', error=str(e)))
                converted_first_seen = first_seen
                converted_last_seen = last_seen
        else:
            converted_first_seen = first_seen
            converted_last_seen = last_seen
        
        # Get enhanced device information if enabled
        enhanced_device_info = {}
        if api.features.get('enable_device_enhancement', True):
            mac_address = device.get('mac_address')
            if mac_address:
                try:
                    if api.logging_config.get('log_enhancement_operations', True):
                        logger.info(api._get_log_message('enhancing_device_info', mac_address=mac_address))
                    
                    resolution_info = await database_service.resolve_device_info(mac_address, use_cache=True)
                    enhanced_device_info = {
                        'resolvedName': resolution_info.get('resolvedName'),
                        'resolvedVendor': resolution_info.get('resolvedVendor'),
                        'resolvedType': resolution_info.get('resolvedType'),
                        'resolutionSource': resolution_info.get('source', 'none'),
                        'sourceMapping': resolution_info.get('sourceMapping', {})
                    }
                    
                    if api.logging_config.get('log_enhancement_operations', True):
                        logger.info(api._get_log_message('device_info_enhanced', 
                                                       source=enhanced_device_info.get('resolutionSource', 'none')))
                
                except Exception as e:
                    if api.logging_config.get('log_error_details', True):
                        logger.warning(api._get_log_message('enhancement_failed', error=str(e)))
                    enhanced_device_info = {
                        'resolvedName': None,
                        'resolvedVendor': None,
                        'resolvedType': None,
                        'resolutionSource': 'none',
                        'sourceMapping': {}
                    }
        
        # Calculate real-time device status
        device_status = device.get('status', api.defaults.get('status', 'unknown'))
        try:
            # Use the same real-time status calculation as the experiment detail API
            from backend.pcap_process.analyzers.device.device_status_service import DeviceStatusService
            status_service = DeviceStatusService(db_manager)
            device_status = await status_service.calculate_realtime_status(device_id, experiment_id)
        except Exception as e:
            if api.logging_config.get('log_error_details', True):
                logger.warning(f"Failed to calculate real-time status for device {device_id}: {e}")
            # Fall back to database status
            device_status = device.get('status', api.defaults.get('status', 'unknown'))
        
        # Temporarily store real-time status in device dict for _build_response
        device['status'] = device_status
        
        # Build response using configurable structure
        response = api._build_response(
            device, stats, enhanced_device_info, experiment_id, time_window,
            converted_first_seen, converted_last_seen, 
            traffic_formatted, duration_formatted
        )
        
        if api.logging_config.get('log_api_calls', True):
            logger.info(api._get_log_message('api_completed', 
                                           device_id=device_id,
                                           packets=response.get(api.response_fields.get('total_packets_field', 'totalPackets'), 0),
                                           sessions=response.get(api.response_fields.get('total_sessions_field', 'totalSessions'), 0)))
        
        # Broadcast removed to prevent infinite loop with frontend re-fetching
        # background_tasks.add_task(_trigger_device_detail_broadcast, device_id, experiment_id, response)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = api.error_messages.get('database_query_failed', 'Database query failed: {error}')
        if api.logging_config.get('log_error_details', True):
            logger.error(api._get_log_message('api_error', device_id=device_id, error=str(e)))
        raise HTTPException(
            status_code=500,
            detail=error_msg.format(error=str(e))
        )

# Background task for WebSocket broadcast
async def _trigger_device_detail_broadcast(device_id: str, experiment_id: str, response_data: dict):
    """Trigger WebSocket broadcast when device detail is accessed"""
    try:
        # Import broadcast service
        from ...services.broadcast_service import broadcast_service
        
        # Trigger broadcast for device detail update
        await broadcast_service.emit_event(f"devices.{device_id}.detail", response_data)
        
        # Also trigger a general device data change broadcast
        await broadcast_service.broadcast_device_data_change(device_id, experiment_id, "api_access")
        
    except Exception as e:
        # Silent error handling for broadcast - don't affect API response
        logger.debug(f"Failed to trigger device detail broadcast for {device_id}: {e}") 
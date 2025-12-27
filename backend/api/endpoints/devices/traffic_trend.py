"""
Device Traffic Trend API Endpoint
Handles device traffic trend data retrieval with enhanced time-series analysis
"""

import logging
import sys
import os
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Depends

# Setup unified path configuration
from ...common.path_config import setup_project_paths
setup_project_paths()

# Import the unified configuration manager
from config.unified_config_manager import get_config, get_log_message

logger = logging.getLogger(__name__)

class ConfigurableDeviceTrafficTrendAPI:
    """Fully configurable Device Traffic Trend API with zero hardcoded values"""
    
    def __init__(self):
        """Initialize with unified configuration"""
        self.config_component = "api_endpoints.traffic_trend"
        self._load_configuration()
    
    def _load_configuration(self):
        """Load all configuration for traffic trend API"""
        # Default values configuration for traffic trend API
        self.defaults = get_config(f'{self.config_component}.defaults', {
            'time_window': '48h',
            'interval_fallback_minutes': 240,
            'min_data_points': 1,
            'max_data_points': 100,
            'unknown_protocol': 'Unknown',
            'tcp_fallback': 'TCP-Other',
            'udp_fallback': 'UDP-Other'
        }, self.config_component)
        
        # Time interval configuration for traffic trend API
        self.time_intervals = get_config(f'{self.config_component}.time_intervals', {
            'hour_1_minutes': 10,
            'hour_6_minutes': 30,
            'hour_24_minutes': 120,
            'hour_48_minutes': 240,
            'hour_long_minutes': 360,
            'hour_1_threshold': 1,
            'hour_6_threshold': 6,
            'hour_24_threshold': 24,
            'hour_48_threshold': 48,
            'minute_to_hour_threshold': 60
        }, self.config_component)
        
        # Protocol mapping configuration for traffic trend API
        self.protocol_mapping = get_config(f'{self.config_component}.protocol_mapping', {
            'http_ports': [80],
            'https_ports': [443],
            'dns_ports': [53],
            'dhcp_ports': [67, 68],
            'upnp_ports': [1900],
            'http_alt_port_ranges': [[8000, 8999]],
            'http_keywords': ['http'],
            'https_keywords': ['http'],
            'dns_keywords': ['dns'],
            'dhcp_keywords': ['dhcp'],
            'upnp_keywords': ['ssdp', 'upnp']
        }, self.config_component)
        
        # Protocol names configuration for traffic trend API
        self.protocol_names = get_config(f'{self.config_component}.protocol_names', {
            'http_name': 'HTTP',
            'https_name': 'HTTPS',
            'dns_name': 'DNS',
            'dhcp_name': 'DHCP',
            'upnp_name': 'UPnP/SSDP',
            'http_alt_name': 'HTTP-Alt',
            'tcp_other_name': 'TCP-Other',
            'udp_other_name': 'UDP-Other',
            'unknown_name': 'Unknown'
        }, self.config_component)
        
        # Time formatting configuration for traffic trend API
        self.time_formatting = get_config(f'{self.config_component}.time_formatting', {
            'display_format': '%m/%d %H:%M',
            'short_format': '%H:%M',
            'full_format': '%Y/%m/%d %H:%M',
            'iso_format': 'isoformat',
            'enable_timezone_formatting': True,
            'enable_fallback_formatting': True
        }, self.config_component)
        
        # Response field configuration for traffic trend API
        self.response_fields = get_config(f'{self.config_component}.response_fields', {
            'timestamp_field': 'timestamp',
            'display_timestamp_field': 'display_timestamp',
            'short_timestamp_field': 'short_timestamp',
            'full_timestamp_field': 'full_timestamp',
            'protocols_field': 'protocols',
            'packets_field': 'packets',
            'bytes_field': 'bytes',
            'sessions_field': 'sessions'
        }, self.config_component)
        
        # Query configuration for traffic trend API
        self.queries = get_config(f'{self.config_component}.queries', {
            'base_select': """
                SELECT 
                    {time_group_expr} as time_period,
                    {protocol_case_expr} as protocol,
                    COUNT(*) as packets,
                    SUM(packet_size) as bytes,
                    COUNT(DISTINCT flow_hash) as sessions
                FROM packet_flows 
                WHERE device_id = $1
                AND packet_timestamp >= $2 
                AND packet_timestamp <= $3
            """,
            'experiment_condition': " AND experiment_id = $4",
            'group_by_clause': " GROUP BY 1, 2",
            'order_by_clause': " ORDER BY 1, SUM(packet_size) DESC",
            'minute_group_template': """
                DATE_TRUNC('minute', packet_timestamp) +
                INTERVAL '{interval} minutes' * 
                FLOOR(EXTRACT(minute FROM packet_timestamp) / {interval})
            """,
            'hour_group_template': """
                DATE_TRUNC('hour', packet_timestamp) +
                INTERVAL '{interval} hours' * 
                FLOOR(EXTRACT(hour FROM packet_timestamp) / {interval})
            """
        }, self.config_component)
        
        # Error messages configuration
        self.error_messages = get_config(f'{self.config_component}.error_messages', {
            'no_trend_data': "No trend data found for device: {device_id}",
            'query_execution_failed': "Traffic trend query execution failed: {error}",
            'timezone_formatting_failed': "Timezone formatting failed: {error}, using fallback",
            'timezone_manager_unavailable': "Timezone manager not available, using fallback formatting",
            'invalid_time_window': "Invalid time window: {time_window}",
            'device_not_found': "Device {device_id} not found",
            'api_error': "Error in traffic trend API: {error}"
        }, self.config_component)
        
        # Features configuration for traffic trend API
        self.features = get_config(f'{self.config_component}.features', {
            'enable_timezone_support': True,
            'enable_protocol_detection': True,
            'enable_smart_intervals': True,
            'enable_session_counting': True,
            'enable_protocol_aggregation': True,
            'enable_fallback_formatting': True,
            'enable_query_optimization': True,
            'enable_data_validation': True
        }, self.config_component)
        
        # Logging configuration for traffic trend API
        self.logging_config = get_config(f'{self.config_component}.logging', {
            'log_api_calls': True,
            'log_query_execution': True,
            'log_query_results': True,
            'log_timezone_operations': True,
            'log_data_aggregation': False,
            'log_protocol_detection': False,
            'log_performance_metrics': True,
            'log_error_details': True
        }, self.config_component)
    
    def _get_log_message(self, template_key: str, **kwargs) -> str:
        """Get formatted log message from templates"""
        return get_log_message('api_endpoints.traffic_trend', template_key, **kwargs)
    
    def _determine_time_interval(self, hours: float) -> int:
        """Determine time interval based on configurable thresholds"""
        if hours <= self.time_intervals.get('hour_1_threshold', 1):
            return self.time_intervals.get('hour_1_minutes', 10)
        elif hours <= self.time_intervals.get('hour_6_threshold', 6):
            return self.time_intervals.get('hour_6_minutes', 30)
        elif hours <= self.time_intervals.get('hour_24_threshold', 24):
            return self.time_intervals.get('hour_24_minutes', 120)
        elif hours <= self.time_intervals.get('hour_48_threshold', 48):
            return self.time_intervals.get('hour_48_minutes', 240)
        else:
            return self.time_intervals.get('hour_long_minutes', 360)
    
    def _build_time_group_expression(self, interval_minutes: int) -> str:
        """Build time grouping SQL expression"""
        minute_threshold = self.time_intervals.get('minute_to_hour_threshold', 60)
        
        if interval_minutes < minute_threshold:
            # Minute-level grouping
            template = self.queries.get('minute_group_template', '')
            return template.format(interval=interval_minutes)
        else:
            # Hour-level grouping
            hour_interval = interval_minutes // minute_threshold
            template = self.queries.get('hour_group_template', '')
            return template.format(interval=hour_interval)
    
    def _build_protocol_case_expression(self) -> str:
        """Build protocol detection CASE expression"""
        http_ports = self.protocol_mapping.get('http_ports', [80])
        https_ports = self.protocol_mapping.get('https_ports', [443])
        dns_ports = self.protocol_mapping.get('dns_ports', [53])
        dhcp_ports = self.protocol_mapping.get('dhcp_ports', [67, 68])
        upnp_ports = self.protocol_mapping.get('upnp_ports', [1900])
        http_alt_ranges = self.protocol_mapping.get('http_alt_port_ranges', [[8000, 8999]])
        
        # Get protocol names
        http_name = self.protocol_names.get('http_name', 'HTTP')
        https_name = self.protocol_names.get('https_name', 'HTTPS')
        dns_name = self.protocol_names.get('dns_name', 'DNS')
        dhcp_name = self.protocol_names.get('dhcp_name', 'DHCP')
        upnp_name = self.protocol_names.get('upnp_name', 'UPnP/SSDP')
        http_alt_name = self.protocol_names.get('http_alt_name', 'HTTP-Alt')
        tcp_other_name = self.protocol_names.get('tcp_other_name', 'TCP-Other')
        udp_other_name = self.protocol_names.get('udp_other_name', 'UDP-Other')
        unknown_name = self.protocol_names.get('unknown_name', 'Unknown')
        
        # Build port conditions
        http_port_condition = ' OR '.join([f'dst_port = {port} OR src_port = {port}' for port in http_ports])
        https_port_condition = ' OR '.join([f'dst_port = {port} OR src_port = {port}' for port in https_ports])
        dns_port_condition = ' OR '.join([f'dst_port = {port} OR src_port = {port}' for port in dns_ports])
        dhcp_port_condition = ' OR '.join([f'dst_port IN ({", ".join(map(str, dhcp_ports))}) OR src_port IN ({", ".join(map(str, dhcp_ports))})'])
        upnp_port_condition = ' OR '.join([f'dst_port = {port} OR src_port = {port}' for port in upnp_ports])
        
        # Build HTTP-Alt range condition
        http_alt_conditions = []
        for start, end in http_alt_ranges:
            http_alt_conditions.append(f'(dst_port BETWEEN {start} AND {end}) OR (src_port BETWEEN {start} AND {end})')
        http_alt_condition = ' OR '.join(http_alt_conditions)
        
        # Build keyword conditions
        http_keywords = self.protocol_mapping.get('http_keywords', ['http'])
        https_keywords = self.protocol_mapping.get('https_keywords', ['http'])
        dns_keywords = self.protocol_mapping.get('dns_keywords', ['dns'])
        dhcp_keywords = self.protocol_mapping.get('dhcp_keywords', ['dhcp'])
        upnp_keywords = self.protocol_mapping.get('upnp_keywords', ['ssdp', 'upnp'])
        
        http_keyword_condition = ' OR '.join([f"app_protocol ILIKE '%{kw}%'" for kw in http_keywords])
        dns_keyword_condition = ' OR '.join([f"app_protocol ILIKE '%{kw}%'" for kw in dns_keywords])
        dhcp_keyword_condition = ' OR '.join([f"app_protocol ILIKE '%{kw}%'" for kw in dhcp_keywords])
        upnp_keyword_condition = ' OR '.join([f"app_protocol ILIKE '%{kw}%'" for kw in upnp_keywords])
        
        case_expression = f"""
            CASE 
                WHEN app_protocol IS NOT NULL AND app_protocol != '' THEN
                    CASE 
                        WHEN ({http_keyword_condition}) AND ({https_port_condition}) THEN '{https_name}'
                        WHEN ({http_keyword_condition}) THEN '{http_name}'
                        WHEN ({dns_keyword_condition}) THEN '{dns_name}'
                        WHEN ({dhcp_keyword_condition}) THEN '{dhcp_name}'
                        WHEN ({upnp_keyword_condition}) THEN '{upnp_name}'
                        ELSE UPPER(app_protocol)
                    END
                WHEN {http_port_condition} THEN '{http_name}'
                WHEN {https_port_condition} THEN '{https_name}'
                WHEN {dns_port_condition} THEN '{dns_name}'
                WHEN {dhcp_port_condition} THEN '{dhcp_name}'
                WHEN {upnp_port_condition} THEN '{upnp_name}'
                WHEN {http_alt_condition} THEN '{http_alt_name}'
                WHEN protocol = 'TCP' THEN '{tcp_other_name}'
                WHEN protocol = 'UDP' THEN '{udp_other_name}'
                ELSE COALESCE(protocol, '{unknown_name}')
            END
        """
        
        return case_expression
    
    def _build_query(self, device_id: str, start_time, end_time, experiment_id: str, 
                    time_group_expr: str, protocol_case_expr: str) -> tuple:
        """Build complete SQL query with configurable components"""
        base_query = self.queries.get('base_select', '')
        query = base_query.format(
            time_group_expr=time_group_expr,
            protocol_case_expr=protocol_case_expr
        )
        
        params = [device_id, start_time, end_time]
        if experiment_id:
            query += self.queries.get('experiment_condition', '')
            params.append(experiment_id)
        
        query += self.queries.get('group_by_clause', '')
        query += self.queries.get('order_by_clause', '')
        
        return query, params
    
    def _format_timestamp(self, timestamp, experiment_id: str = None) -> Dict[str, str]:
        """Format timestamp with configurable formats"""
        if self.features.get('enable_timezone_support', True) and experiment_id:
            try:
                from database.services.timezone_manager import timezone_manager
                return timezone_manager.format_timestamp_for_api(timestamp, experiment_id)
            except Exception as e:
                if self.logging_config.get('log_timezone_operations', True):
                    logger.warning(self._get_log_message('timezone_formatting_failed', error=str(e)))
        
        # Fallback formatting using configuration
        if self.features.get('enable_fallback_formatting', True):
            iso_format = self.time_formatting.get('iso_format', 'isoformat')
            timestamp_str = timestamp.isoformat() if iso_format == 'isoformat' else timestamp.strftime(iso_format)
            
            return {
                self.response_fields.get('timestamp_field', 'timestamp'): timestamp_str,
                self.response_fields.get('display_timestamp_field', 'display_timestamp'): 
                    timestamp.strftime(self.time_formatting.get('display_format', '%m/%d %H:%M')),
                self.response_fields.get('short_timestamp_field', 'short_timestamp'): 
                    timestamp.strftime(self.time_formatting.get('short_format', '%H:%M')),
                self.response_fields.get('full_timestamp_field', 'full_timestamp'): 
                    timestamp.strftime(self.time_formatting.get('full_format', '%Y/%m/%d %H:%M'))
            }
        
        # Minimal fallback
        return {self.response_fields.get('timestamp_field', 'timestamp'): timestamp.isoformat()}
    
    def _aggregate_traffic_data(self, result: List[Dict]) -> Dict:
        """Aggregate traffic data by time with configurable logic"""
        traffic_by_time = {}
        
        for row in result:
            timestamp = row['time_period']
            protocol = row['protocol']
            packets = row['packets'] or 0
            bytes_count = row['bytes'] or 0
            sessions = row.get('sessions', 0) or 0
            
            if timestamp not in traffic_by_time:
                traffic_by_time[timestamp] = {
                    'protocols': {},
                    'total_packets': 0,
                    'total_bytes': 0,
                    'total_sessions': sessions  # Only set sessions on the first occurrence to avoid duplication
                }
            
            traffic_by_time[timestamp]['protocols'][protocol] = bytes_count
            traffic_by_time[timestamp]['total_packets'] += packets
            traffic_by_time[timestamp]['total_bytes'] += bytes_count
            # No longer accumulate sessions, as the query returns the total number of sessions for that time period (duplicates)
        
        return traffic_by_time
    
    def _build_response(self, traffic_by_time: Dict, experiment_id: str = None) -> List[Dict[str, Any]]:
        """Build response with configurable field structure"""
        traffic_trend = []
        
        for timestamp, data in sorted(traffic_by_time.items()):
            # Format timestamp using configuration
            formatted_time = self._format_timestamp(timestamp, experiment_id)
            
            # Build trend entry using configured field names
            trend_entry = {
                **formatted_time,
                self.response_fields.get('protocols_field', 'protocols'): data['protocols'],
                self.response_fields.get('packets_field', 'packets'): data['total_packets'],
                self.response_fields.get('bytes_field', 'bytes'): data['total_bytes']
            }
            
            # Add session count if enabled
            if self.features.get('enable_session_counting', True):
                sessions_count = data.get('total_sessions', 0)
                trend_entry[self.response_fields.get('sessions_field', 'sessions')] = sessions_count
            
            traffic_trend.append(trend_entry)
        
        return traffic_trend

# Create global configurable API instance  
configurable_traffic_trend_api = ConfigurableDeviceTrafficTrendAPI()

router = APIRouter()

# Use the unified dependency injection
from ...common.dependencies import get_database_service_instance

@router.get("/{device_id}/traffic-trend", response_model=List[Dict[str, Any]])
async def get_device_traffic_trend(
    device_id: str, 
    background_tasks: BackgroundTasks,
    time_window: str = Query(default=None, alias="time_window", description="Time window: 1h, 6h, 12h, 24h, 48h, auto"),
    experiment_id: str = Query(default=None, alias="experiment_id", description="Experiment ID for data isolation"),
    database_service = Depends(get_database_service_instance)
):
    """
    Retrieve traffic trend for a specific device with full configuration support
    Returns time series data with protocol breakdown
    """
    api = configurable_traffic_trend_api
    
    # Use configured default time window if not provided
    if time_window is None:
        time_window = api.defaults.get('time_window', '48h')
    
    try:
        if api.logging_config.get('log_api_calls', True):
            logger.info(api._get_log_message('api_called', 
                                           device_id=device_id,
                                           time_window=time_window, 
                                           experiment_id=experiment_id))
        
        db_manager = database_service.db_manager
        
        # Get time window boundaries using unified service
        from database.services.timezone_time_window_service import timezone_time_window_service
        start_time, end_time = await timezone_time_window_service.get_timezone_aware_time_bounds(
            experiment_id, time_window, db_manager
        )
        
        # Determine time interval using configuration
        time_diff = end_time - start_time
        hours = time_diff.total_seconds() / 3600
        interval_minutes = api._determine_time_interval(hours)
        
        if api.logging_config.get('log_query_execution', True):
            logger.info(api._get_log_message('interval_determined', 
                                           hours=hours, 
                                           interval_minutes=interval_minutes))
        
        # Build time grouping expression
        time_group_expr = api._build_time_group_expression(interval_minutes)
        
        # Build protocol detection expression
        protocol_case_expr = api._build_protocol_case_expression()
        
        # Build complete query
        trend_query, params = api._build_query(device_id, start_time, end_time, 
                                              experiment_id, time_group_expr, protocol_case_expr)
        
        if api.logging_config.get('log_query_execution', True):
            logger.info(api._get_log_message('executing_query', params=params))
        
        result = await db_manager.execute_query(trend_query, params)
        
        if api.logging_config.get('log_query_results', True):
            logger.info(api._get_log_message('query_result', 
                                           result_count=len(result) if result else 0))
        
        if not result:
            if api.logging_config.get('log_error_details', True):
                logger.warning(api._get_log_message('no_trend_data', device_id=device_id))
            return []
        
        # Check timezone manager availability
        if api.features.get('enable_timezone_support', True):
            try:
                from database.services.timezone_manager import timezone_manager
                has_timezone_support = True
            except ImportError:
                has_timezone_support = False
                if api.logging_config.get('log_timezone_operations', True):
                    logger.warning(api._get_log_message('timezone_manager_unavailable'))
        
        # Aggregate traffic data using configurable logic
        traffic_by_time = api._aggregate_traffic_data(result)
        
        # Build response using configurable structure
        traffic_trend = api._build_response(traffic_by_time, experiment_id)
        
        if api.logging_config.get('log_api_calls', True):
            logger.info(api._get_log_message('api_completed', 
                                           device_id=device_id,
                                           data_points=len(traffic_trend)))
        
        # Broadcast removed to prevent infinite loop with frontend re-fetching
        # background_tasks.add_task(_trigger_traffic_trend_broadcast, device_id, experiment_id, traffic_trend)
        
        return traffic_trend
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = api.error_messages.get('api_error', 'Error in traffic trend API: {error}')
        if api.logging_config.get('log_error_details', True):
            logger.error(api._get_log_message('api_error', device_id=device_id, error=str(e)))
        raise HTTPException(
            status_code=500,
            detail=error_msg.format(error=str(e))
        )

# Background task for WebSocket broadcast
async def _trigger_traffic_trend_broadcast(device_id: str, experiment_id: str, response_data: list):
    """Trigger WebSocket broadcast when traffic trend is accessed"""
    try:
        # Import broadcast service
        from ...services.broadcast_service import broadcast_service
        
        # Trigger broadcast for traffic trend update
        await broadcast_service.emit_event(f"devices.{device_id}.traffic-trend", response_data)
        
    except Exception as e:
        # Silent error handling for broadcast - don't affect API response
        logger.debug(f"Failed to trigger traffic trend broadcast for {device_id}: {e}")

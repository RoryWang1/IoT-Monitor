"""
Device Protocol Distribution API Endpoint
IoT device monitoring system's intelligent protocol distribution analysis component
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Depends

logger = logging.getLogger(__name__)

# Setup unified path configuration
from ...common.path_config import setup_project_paths
setup_project_paths()

# Import the unified configuration manager
from config.unified_config_manager import get_config, get_log_message

class ConfigurableDeviceProtocolDistributionAPI:
    """Configurable device protocol distribution analysis API class"""
    
    def __init__(self):
        """Initialize the configurable protocol distribution API"""
        self.config_namespace = 'device_protocol_distribution'
        
        # Configurable component initialization log
        if get_config(f'{self.config_namespace}.logging.log_component_initialization', True, f'{self.config_namespace}.logging'):
            logger.info(get_log_message('device_protocol_distribution', 'component_initialized', 
                                       component='device_protocol_distribution.api'))
    
    def _get_default_time_window(self) -> str:
        """Get the configurable default time window"""
        return get_config(f'{self.config_namespace}.defaults.time_window', '48h', f'{self.config_namespace}.defaults')
    
    def _get_query_limits(self) -> Dict[str, Any]:
        """Get the configurable query limits"""
        return {
            'max_protocol_results': get_config(f'{self.config_namespace}.query_limits.max_protocol_results', 20, f'{self.config_namespace}.query_limits'),
            'min_packets_threshold': get_config(f'{self.config_namespace}.query_limits.min_packets_threshold', 1, f'{self.config_namespace}.query_limits'),
            'max_query_timeout': get_config(f'{self.config_namespace}.query_limits.max_query_timeout', 30, f'{self.config_namespace}.query_limits')
        }
    
    def _get_protocol_classification_rules(self) -> Dict[str, Any]:
        """Get the configurable protocol classification rules"""
        return {
            'app_protocol_patterns': get_config(f'{self.config_namespace}.protocol_classification.app_protocol_patterns', {
                'http_patterns': ['http'],
                'https_patterns': ['http'],
                'dns_patterns': ['dns'],
                'dhcp_patterns': ['dhcp'],
                'upnp_patterns': ['ssdp', 'upnp'],
                'case_handling': 'UPPER'
            }, f'{self.config_namespace}.protocol_classification'),
            'port_mappings': get_config(f'{self.config_namespace}.protocol_classification.port_mappings', {
                '80': 'HTTP',
                '443': 'HTTPS',
                '53': 'DNS',
                '67': 'DHCP',
                '68': 'DHCP',
                '1900': 'UPnP/SSDP',
                '123': 'NTP',
                '22': 'SSH',
                '21': 'FTP',
                '25': 'SMTP',
                '110': 'POP3',
                '143': 'IMAP'
            }, f'{self.config_namespace}.protocol_classification'),
            'port_ranges': get_config(f'{self.config_namespace}.protocol_classification.port_ranges', {
                '8000-8999': 'HTTP-Alt',
                '8443-8543': 'HTTPS-Alt'
            }, f'{self.config_namespace}.protocol_classification'),
            'transport_layer_fallbacks': get_config(f'{self.config_namespace}.protocol_classification.transport_layer_fallbacks', {
                'TCP': 'TCP-Other',
                'UDP': 'UDP-Other',
                'unknown': 'Unknown'
            }, f'{self.config_namespace}.protocol_classification')
        }
    
    def _get_statistics_configuration(self) -> Dict[str, Any]:
        """Get the configurable statistics configuration"""
        return {
            'enable_packet_counting': get_config(f'{self.config_namespace}.statistics.enable_packet_counting', True, f'{self.config_namespace}.statistics'),
            'enable_byte_counting': get_config(f'{self.config_namespace}.statistics.enable_byte_counting', True, f'{self.config_namespace}.statistics'),
            'enable_session_counting': get_config(f'{self.config_namespace}.statistics.enable_session_counting', True, f'{self.config_namespace}.statistics'),
            'enable_avg_packet_size': get_config(f'{self.config_namespace}.statistics.enable_avg_packet_size', True, f'{self.config_namespace}.statistics'),
            'enable_time_range_tracking': get_config(f'{self.config_namespace}.statistics.enable_time_range_tracking', True, f'{self.config_namespace}.statistics'),
            'percentage_decimal_places': get_config(f'{self.config_namespace}.statistics.percentage_decimal_places', 2, f'{self.config_namespace}.statistics'),
            'avg_size_decimal_places': get_config(f'{self.config_namespace}.statistics.avg_size_decimal_places', 2, f'{self.config_namespace}.statistics')
        }
    
    def _get_response_field_mapping(self) -> Dict[str, str]:
        """Get the configurable response field mapping"""
        return {
            'protocol_field': get_config(f'{self.config_namespace}.response_fields.protocol_field', 'protocol', f'{self.config_namespace}.response_fields'),
            'packet_count_field': get_config(f'{self.config_namespace}.response_fields.packet_count_field', 'packet_count', f'{self.config_namespace}.response_fields'),
            'byte_count_field': get_config(f'{self.config_namespace}.response_fields.byte_count_field', 'byte_count', f'{self.config_namespace}.response_fields'),
            'percentage_field': get_config(f'{self.config_namespace}.response_fields.percentage_field', 'percentage', f'{self.config_namespace}.response_fields'),
            'session_count_field': get_config(f'{self.config_namespace}.response_fields.session_count_field', 'session_count', f'{self.config_namespace}.response_fields'),
            'avg_packet_size_field': get_config(f'{self.config_namespace}.response_fields.avg_packet_size_field', 'avg_packet_size', f'{self.config_namespace}.response_fields'),
            'formatted_bytes_field': get_config(f'{self.config_namespace}.response_fields.formatted_bytes_field', 'formatted_bytes', f'{self.config_namespace}.response_fields'),
            'experiment_id_field': get_config(f'{self.config_namespace}.response_fields.experiment_id_field', 'experiment_id', f'{self.config_namespace}.response_fields')
        }
    
    def _get_data_formatting_config(self) -> Dict[str, Any]:
        """Get the configurable data formatting configuration"""
        return {
            'string_conversion_fields': get_config(f'{self.config_namespace}.data_formatting.string_conversion_fields', 
                                                  ['packet_count', 'byte_count', 'avg_packet_size'], 
                                                  f'{self.config_namespace}.data_formatting'),
            'byte_formatting_pattern': get_config(f'{self.config_namespace}.data_formatting.byte_formatting_pattern', '{bytes} B', f'{self.config_namespace}.data_formatting'),
            'percentage_formatting_pattern': get_config(f'{self.config_namespace}.data_formatting.percentage_formatting_pattern', '{percentage:.2f}', f'{self.config_namespace}.data_formatting'),
            'avg_size_formatting_pattern': get_config(f'{self.config_namespace}.data_formatting.avg_size_formatting_pattern', '{size:.2f}', f'{self.config_namespace}.data_formatting'),
            'null_value_replacement': get_config(f'{self.config_namespace}.data_formatting.null_value_replacement', '0', f'{self.config_namespace}.data_formatting'),
            'empty_experiment_id_replacement': get_config(f'{self.config_namespace}.data_formatting.empty_experiment_id_replacement', '', f'{self.config_namespace}.data_formatting')
        }
    
    def _build_protocol_classification_sql(self, classification_rules: Dict[str, Any]) -> str:
        """Build the configurable protocol classification SQL CASE expression"""
        app_patterns = classification_rules['app_protocol_patterns']
        port_mappings = classification_rules['port_mappings']
        port_ranges = classification_rules['port_ranges']
        fallbacks = classification_rules['transport_layer_fallbacks']
        
        # Build the app_protocol branch
        app_protocol_cases = []
        for pattern in app_patterns.get('http_patterns', []):
            app_protocol_cases.append(f"WHEN app_protocol ILIKE '%{pattern}%' AND (dst_port = 443 OR src_port = 443) THEN 'HTTPS'")
            app_protocol_cases.append(f"WHEN app_protocol ILIKE '%{pattern}%' THEN 'HTTP'")
        
        for pattern in app_patterns.get('dns_patterns', []):
            app_protocol_cases.append(f"WHEN app_protocol ILIKE '%{pattern}%' THEN 'DNS'")
        
        for pattern in app_patterns.get('dhcp_patterns', []):
            app_protocol_cases.append(f"WHEN app_protocol ILIKE '%{pattern}%' THEN 'DHCP'")
        
        for pattern in app_patterns.get('upnp_patterns', []):
            app_protocol_cases.append(f"WHEN app_protocol ILIKE '%{pattern}%' THEN 'UPnP/SSDP'")
        
        # Build the port mapping branch
        port_cases = []
        for port, protocol in port_mappings.items():
            port_cases.append(f"WHEN dst_port = {port} OR src_port = {port} THEN '{protocol}'")
        
        # Build the port range branch
        range_cases = []
        for port_range, protocol in port_ranges.items():
            start_port, end_port = port_range.split('-')
            range_cases.append(f"WHEN (dst_port BETWEEN {start_port} AND {end_port}) OR (src_port BETWEEN {start_port} AND {end_port}) THEN '{protocol}'")
        
        # Build the transport layer fallback branch
        transport_cases = []
        for transport, fallback in fallbacks.items():
            if transport != 'unknown':
                transport_cases.append(f"WHEN protocol = '{transport}' THEN '{fallback}'")
        
        unknown_fallback = fallbacks['unknown']
        case_handling = app_patterns.get('case_handling', 'UPPER')
        
        # Assemble the complete CASE expression
        case_sql = f"""
        CASE 
            -- Intelligent protocol classification: prioritize app_protocol, merge similar protocols to avoid over-distribution
            WHEN app_protocol IS NOT NULL AND app_protocol != '' THEN
                CASE 
                    {chr(10).join('                    ' + case for case in app_protocol_cases)}
                    ELSE {case_handling}(app_protocol)
                END
            -- Port fallback recognition
            {chr(10).join('            ' + case for case in port_cases)}
            -- Port range classification
            {chr(10).join('            ' + case for case in range_cases)}
            -- Transport layer protocol
            {chr(10).join('            ' + case for case in transport_cases)}
            ELSE COALESCE(protocol, '{unknown_fallback}')
        END"""
        
        return case_sql
    
    def _build_protocol_distribution_query(self, classification_rules: Dict[str, Any], 
                                         stats_config: Dict[str, Any], limits: Dict[str, Any]) -> str:
        """Build the configurable protocol distribution query"""
        
        # Build the protocol classification expression
        protocol_case_expr = self._build_protocol_classification_sql(classification_rules)
        
        # Build the SELECT fields
        select_fields = [f"({protocol_case_expr}) as protocol"]
        
        if stats_config['enable_packet_counting']:
            select_fields.append("COUNT(*) as packets")
        
        if stats_config['enable_byte_counting']:
            select_fields.append("SUM(packet_size) as bytes")
        
        if stats_config['enable_session_counting']:
            select_fields.append("COUNT(DISTINCT flow_hash) as sessions")
        
        if stats_config['enable_avg_packet_size']:
            select_fields.append("AVG(packet_size) as avg_packet_size")
        
        if stats_config['enable_time_range_tracking']:
            select_fields.extend([
                "MIN(packet_timestamp) as first_seen",
                "MAX(packet_timestamp) as last_seen"
            ])
        
        # Get the query template
        query_template = get_config(f'{self.config_namespace}.query_configuration.protocol_distribution_query_template', 
        """
        SELECT {select_fields}
        FROM packet_flows 
        WHERE device_id = $1
        AND packet_timestamp >= $2 
        AND packet_timestamp <= $3
        {experiment_filter}
        GROUP BY 1
        ORDER BY {order_by_clause}
        LIMIT {max_results}
        """, f'{self.config_namespace}.query_configuration')
        
        # Configurable sorting clause
        order_by_clause = get_config(f'{self.config_namespace}.query_configuration.order_by_clause', 
                                   'SUM(packet_size) DESC', f'{self.config_namespace}.query_configuration')
        
        return query_template.format(
            select_fields=", ".join(select_fields),
            experiment_filter="{experiment_filter}",  # Keep placeholder for runtime replacement
            order_by_clause=order_by_clause,
            max_results=limits['max_protocol_results']
        )
    
    def _format_response_data(self, raw_data: List[Dict], stats_config: Dict[str, Any],
                             field_mapping: Dict[str, str], formatting_config: Dict[str, Any],
                             experiment_id: Optional[str]) -> List[Dict[str, Any]]:
        """Configurable response data formatting"""
        
        # Calculate total traffic for percentage
        total_bytes = sum(row.get('bytes', 0) or 0 for row in raw_data)
        
        formatted_data = []
        for row in raw_data:
            protocol = row.get('protocol') or formatting_config['null_value_replacement']
            packets = row.get('packets', 0) or 0
            bytes_count = row.get('bytes', 0) or 0
            sessions = row.get('sessions', 0) or 0
            
            # Calculate percentage
            percentage = (bytes_count / total_bytes * 100) if total_bytes > 0 else 0
            
            # Build the response object
            protocol_entry = {}
            
            # Core fields
            protocol_entry[field_mapping['protocol_field']] = protocol
            
            # String conversion based on configuration
            string_fields = formatting_config['string_conversion_fields']
            
            if 'packet_count' in string_fields:
                protocol_entry[field_mapping['packet_count_field']] = str(packets)
            else:
                protocol_entry[field_mapping['packet_count_field']] = packets
            
            if 'byte_count' in string_fields:
                protocol_entry[field_mapping['byte_count_field']] = str(bytes_count)
            else:
                protocol_entry[field_mapping['byte_count_field']] = bytes_count
            
            # Format percentage
            protocol_entry[field_mapping['percentage_field']] = formatting_config['percentage_formatting_pattern'].format(percentage=percentage)
            
            # Session count
            protocol_entry[field_mapping['session_count_field']] = sessions
            
            # Average packet size
            if packets > 0:
                avg_size = bytes_count / packets
                if 'avg_packet_size' in string_fields:
                    protocol_entry[field_mapping['avg_packet_size_field']] = formatting_config['avg_size_formatting_pattern'].format(size=avg_size)
                else:
                    protocol_entry[field_mapping['avg_packet_size_field']] = round(avg_size, stats_config['avg_size_decimal_places'])
            else:
                protocol_entry[field_mapping['avg_packet_size_field']] = formatting_config['null_value_replacement']
            
            # Format bytes
            protocol_entry[field_mapping['formatted_bytes_field']] = formatting_config['byte_formatting_pattern'].format(bytes=bytes_count)
            
            # Experiment ID
            protocol_entry[field_mapping['experiment_id_field']] = experiment_id or formatting_config['empty_experiment_id_replacement']
            
            formatted_data.append(protocol_entry)
        
        return formatted_data
    
    async def get_device_protocol_distribution(self, device_id: str, time_window: str, 
                                             experiment_id: Optional[str], database_service) -> List[Dict[str, Any]]:
        """Configurable device protocol distribution main method"""
        try:
            # Configurable API call log
            if get_config(f'{self.config_namespace}.logging.log_api_calls', True, f'{self.config_namespace}.logging'):
                logger.info(get_log_message('device_protocol_distribution', 'api_call_started', 
                                           component='device_protocol_distribution.api',
                                           device_id=device_id, time_window=time_window, 
                                           experiment_id=experiment_id))
            
            db_manager = database_service.db_manager
            
            # Get the time window boundaries
            from database.services.timezone_time_window_service import timezone_time_window_service
            start_time, end_time = await timezone_time_window_service.get_timezone_aware_time_bounds(
                experiment_id, time_window, db_manager
            )
            
            # Get the configurable limits
            limits = self._get_query_limits()
            classification_rules = self._get_protocol_classification_rules()
            stats_config = self._get_statistics_configuration()
            field_mapping = self._get_response_field_mapping()
            formatting_config = self._get_data_formatting_config()
            
            # Build the protocol distribution query
            base_query = self._build_protocol_distribution_query(classification_rules, stats_config, limits)
            
            # Process the experiment ID filter
            params = [device_id, start_time, end_time]
            if experiment_id:
                final_query = base_query.replace('{experiment_filter}', 'AND experiment_id = $4')
                params.append(experiment_id)
            else:
                final_query = base_query.replace('{experiment_filter}', '')
            
            # Configurable query execution log
            if get_config(f'{self.config_namespace}.logging.log_query_execution', True, f'{self.config_namespace}.logging'):
                logger.info(get_log_message('device_protocol_distribution', 'query_execution_started', 
                                           component='device_protocol_distribution.database',
                                           params=str(params)))
            
            result = await db_manager.execute_query(final_query, params)
            
            if not result:
                if get_config(f'{self.config_namespace}.logging.log_empty_results', True, f'{self.config_namespace}.logging'):
                    logger.warning(get_log_message('device_protocol_distribution', 'no_data_found', 
                                                  component='device_protocol_distribution.api',
                                                  device_id=device_id))
                return []
            
            # Format the response data
            formatted_result = self._format_response_data(
                result, stats_config, field_mapping, formatting_config, experiment_id
            )
            
            # Configurable success log
            if get_config(f'{self.config_namespace}.logging.log_api_success', True, f'{self.config_namespace}.logging'):
                logger.info(get_log_message('device_protocol_distribution', 'api_call_completed', 
                                           component='device_protocol_distribution.api',
                                           device_id=device_id, results_count=len(formatted_result)))
            
            return formatted_result
            
        except Exception as e:
            # Configurable error log
            if get_config(f'{self.config_namespace}.logging.log_api_errors', True, f'{self.config_namespace}.logging'):
                logger.error(get_log_message('device_protocol_distribution', 'api_call_failed', 
                                            component='device_protocol_distribution.api',
                                            device_id=device_id, error=str(e)))
            raise

# Create the configurable API instance
configurable_api = ConfigurableDeviceProtocolDistributionAPI()

router = APIRouter()

# Use the unified dependency injection
from ...common.dependencies import get_database_service_instance

@router.get("/{device_id}/protocol-distribution", response_model=List[Dict[str, Any]])
async def get_device_protocol_distribution(
    device_id: str, 
    background_tasks: BackgroundTasks,
    time_window: str = Query(default=None, alias="time_window", description="Time window: 1h, 6h, 12h, 24h, 48h, auto"),
    experiment_id: str = Query(default=None, alias="experiment_id", description="Experiment ID for data isolation"),
    database_service = Depends(get_database_service_instance)
):
    """
    Configurable device protocol distribution API endpoint
    Returns configurable protocol distribution with intelligent classification and aggregation
    """
    try:
        # Use the configurable defaults
        if time_window is None:
            time_window = configurable_api._get_default_time_window()
        
        # Call the configurable API method
        result = await configurable_api.get_device_protocol_distribution(
            device_id=device_id,
            time_window=time_window, 
            experiment_id=experiment_id,
            database_service=database_service
        )
        
        # Broadcast removed to prevent infinite loop with frontend re-fetching
        # background_tasks.add_task(_trigger_protocol_distribution_broadcast, device_id, experiment_id, result)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        error_message = get_config('device_protocol_distribution.error_messages.general_error', 
                                 f"Failed to retrieve protocol distribution for device '{device_id}': {{error}}", 
                                 'device_protocol_distribution.error_messages')
        raise HTTPException(
            status_code=500,
            detail=error_message.format(device_id=device_id, error=str(e))
        )

# Background task for WebSocket broadcast
async def _trigger_protocol_distribution_broadcast(device_id: str, experiment_id: str, response_data: list):
    """Trigger WebSocket broadcast when protocol distribution is accessed"""
    try:
        # Import broadcast service
        from ...services.broadcast_service import broadcast_service
        
        # Trigger broadcast for protocol distribution update
        await broadcast_service.emit_event(f"devices.{device_id}.protocol-distribution", response_data)
        
    except Exception as e:
        # Silent error handling for broadcast - don't affect API response
        logger.debug(f"Failed to trigger protocol distribution broadcast for {device_id}: {e}") 
"""
Device Port Analysis API Endpoint
Smart port analysis component for IoT device monitoring systems
"""

import logging
import sys
import os
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Depends

# Setup unified path configuration
from ...common.path_config import setup_project_paths
setup_project_paths()

# Simplified imports - use try/except for robust config loading
logger = logging.getLogger(__name__)

# Simple config getter with fallbacks
def get_config_safe(key: str, default_value, namespace: str = None):
    """Safe config getter with fallbacks"""
    try:
        from config.unified_config_manager import get_config
        return get_config(key, default_value, namespace)
    except ImportError:
        logger.warning(f"Config manager not available, using default for {key}")
        return default_value

def get_log_message_safe(category: str, message_key: str, **kwargs):
    """Safe log message getter with fallbacks"""
    try:
        from config.unified_config_manager import get_log_message
        return get_log_message(category, message_key, **kwargs)
    except ImportError:
        # Create a simple fallback message
        component = kwargs.get('component', 'unknown')
        return f"{category}.{message_key}: {component}"
    except Exception as e:
        # Handle other errors like missing message templates
        return f"[Log message error: {e}] {category}.{message_key}"

class ConfigurableDevicePortAnalysisAPI:
    """Fully configurable device port analysis API class"""
    
    def __init__(self):
        """Initialize the configurable port analysis API"""
        self.config_namespace = 'device_port_analysis'
        
        # Configurable component initialization log
        if get_config_safe(f'{self.config_namespace}.logging.log_component_initialization', True, f'{self.config_namespace}.logging'):
            logger.info(get_log_message_safe('device_port_analysis', 'component_initialized', 
                                       component='device_port_analysis.api'))
    
    def _get_default_time_window(self) -> str:
        """Get the configurable default time window"""
        return get_config_safe(f'{self.config_namespace}.defaults.time_window', '48h', f'{self.config_namespace}.defaults')
    
    def _get_query_limits(self) -> Dict[str, int]:
        """Get the configurable query limits"""
        return {
            'max_port_results': get_config_safe(f'{self.config_namespace}.query_limits.max_port_results', 50, f'{self.config_namespace}.query_limits'),
            'min_packets_threshold': get_config_safe(f'{self.config_namespace}.query_limits.min_packets_threshold', 1, f'{self.config_namespace}.query_limits'),
            'max_query_timeout': get_config_safe(f'{self.config_namespace}.query_limits.max_query_timeout', 30, f'{self.config_namespace}.query_limits')
        }
    
    def _get_protocol_mappings(self) -> Dict[str, Any]:
        """Get the configurable protocol mappings"""
        return {
            'app_protocol_mapping': get_config_safe(f'{self.config_namespace}.protocol_mapping.app_protocol_rules', {
                'http_patterns': ['http'],
                'https_patterns': ['http'],
                'dns_patterns': ['dns'],
                'dhcp_patterns': ['dhcp'],
                'ssdp_patterns': ['ssdp'],
                'default_transform': 'UPPER'
            }, f'{self.config_namespace}.protocol_mapping'),
            
            'port_service_mapping': get_config_safe(f'{self.config_namespace}.protocol_mapping.port_services', {
                '80': 'HTTP',
                '443': 'HTTPS',
                '53': 'DNS',
                '67': 'DHCP',
                '68': 'DHCP',
                '1900': 'UPnP/SSDP',
                '123': 'NTP',
                '22': 'SSH',
                '21': 'FTP',
                '25': 'SMTP'
            }, f'{self.config_namespace}.protocol_mapping'),
            
            'port_ranges': get_config_safe(f'{self.config_namespace}.protocol_mapping.port_ranges', {
                '8000-8999': 'HTTP-Alt',
                '8443-8543': 'HTTPS-Alt'
            }, f'{self.config_namespace}.protocol_mapping'),
            
            'fallback_protocol': get_config_safe(f'{self.config_namespace}.protocol_mapping.fallback_protocol', 'TCP', f'{self.config_namespace}.protocol_mapping')
        }
    
    def _get_status_thresholds(self) -> Dict[str, int]:
        """Get the configurable status thresholds"""
        return {
            'very_active_threshold': get_config_safe(f'{self.config_namespace}.status_thresholds.very_active_threshold', 100, f'{self.config_namespace}.status_thresholds'),
            'active_threshold': get_config_safe(f'{self.config_namespace}.status_thresholds.active_threshold', 50, f'{self.config_namespace}.status_thresholds'),
            'moderate_threshold': get_config_safe(f'{self.config_namespace}.status_thresholds.moderate_threshold', 10, f'{self.config_namespace}.status_thresholds'),
            'inactive_threshold': get_config_safe(f'{self.config_namespace}.status_thresholds.inactive_threshold', 0, f'{self.config_namespace}.status_thresholds')
        }
    
    def _get_response_field_mapping(self) -> Dict[str, str]:
        """Get the configurable response field mapping"""
        return {
            'port_field': get_config_safe(f'{self.config_namespace}.response_fields.port_field', 'port', f'{self.config_namespace}.response_fields'),
            'protocol_field': get_config_safe(f'{self.config_namespace}.response_fields.protocol_field', 'protocol', f'{self.config_namespace}.response_fields'),
            'service_field': get_config_safe(f'{self.config_namespace}.response_fields.service_field', 'service', f'{self.config_namespace}.response_fields'),
            'packets_field': get_config_safe(f'{self.config_namespace}.response_fields.packets_field', 'packets', f'{self.config_namespace}.response_fields'),
            'bytes_field': get_config_safe(f'{self.config_namespace}.response_fields.bytes_field', 'bytes', f'{self.config_namespace}.response_fields'),
            'percentage_field': get_config_safe(f'{self.config_namespace}.response_fields.percentage_field', 'percentage', f'{self.config_namespace}.response_fields'),
            'status_field': get_config_safe(f'{self.config_namespace}.response_fields.status_field', 'status', f'{self.config_namespace}.response_fields'),
            'sessions_field': get_config_safe(f'{self.config_namespace}.response_fields.sessions_field', 'sessions', f'{self.config_namespace}.response_fields'),
            'outbound_packets_field': get_config_safe(f'{self.config_namespace}.response_fields.outbound_packets_field', 'outbound_packets', f'{self.config_namespace}.response_fields'),
            'inbound_packets_field': get_config_safe(f'{self.config_namespace}.response_fields.inbound_packets_field', 'inbound_packets', f'{self.config_namespace}.response_fields'),
            'avg_packet_size_field': get_config_safe(f'{self.config_namespace}.response_fields.avg_packet_size_field', 'avg_packet_size', f'{self.config_namespace}.response_fields')
        }
    
    def _get_data_formatting_config(self) -> Dict[str, Any]:
        """Get the configurable data formatting configuration"""
        return {
            'percentage_decimal_places': get_config_safe(f'{self.config_namespace}.data_formatting.percentage_decimal_places', 2, f'{self.config_namespace}.data_formatting'),
            'avg_packet_size_decimal_places': get_config_safe(f'{self.config_namespace}.data_formatting.avg_packet_size_decimal_places', 2, f'{self.config_namespace}.data_formatting'),
            'force_integer_conversion': get_config_safe(f'{self.config_namespace}.data_formatting.force_integer_conversion', True, f'{self.config_namespace}.data_formatting'),
            'handle_null_values': get_config_safe(f'{self.config_namespace}.data_formatting.handle_null_values', True, f'{self.config_namespace}.data_formatting')
        }
    
    def _build_protocol_detection_sql(self, mappings: Dict[str, Any]) -> str:
        """Build the configurable protocol detection SQL"""
        app_mapping = mappings['app_protocol_mapping']
        port_mapping = mappings['port_service_mapping']
        port_ranges = mappings['port_ranges']
        fallback = mappings['fallback_protocol']
        
        # Build the app_protocol branch
        app_protocol_cases = []
        for pattern_type, patterns in app_mapping.items():
            if pattern_type == 'default_transform':
                continue
            if pattern_type == 'http_patterns':
                for pattern in patterns:
                    app_protocol_cases.append(f"WHEN app_protocol ILIKE '%{pattern}%' AND COALESCE(src_port, dst_port) = 443 THEN 'HTTPS'")
                    app_protocol_cases.append(f"WHEN app_protocol ILIKE '%{pattern}%' THEN 'HTTP'")
            else:
                service_name = pattern_type.replace('_patterns', '').upper()
                for pattern in patterns:
                    app_protocol_cases.append(f"WHEN app_protocol ILIKE '%{pattern}%' THEN '{service_name}'")
        
        # Add default transformation
        if app_mapping.get('default_transform') == 'UPPER':
            app_protocol_cases.append("ELSE UPPER(app_protocol)")
        
        # Build the port mapping branch
        port_cases = []
        for port, service in port_mapping.items():
            port_cases.append(f"WHEN COALESCE(src_port, dst_port) = {port} THEN '{service}'")
        
        # Build the port range branch
        range_cases = []
        for port_range, service in port_ranges.items():
            start, end = port_range.split('-')
            range_cases.append(f"WHEN COALESCE(src_port, dst_port) BETWEEN {start} AND {end} THEN '{service}'")
        
        # Combine the complete CASE expression
        protocol_sql = f"""
        CASE 
            -- Smart protocol recognition: prioritize app_protocol
            WHEN app_protocol IS NOT NULL AND app_protocol != '' THEN
                CASE 
                    {chr(10).join('                    ' + case for case in app_protocol_cases)}
                END
            -- Port service recognition
            {chr(10).join('            ' + case for case in port_cases)}
            -- Port range recognition
            {chr(10).join('            ' + case for case in range_cases)}
            ELSE COALESCE(protocol, '{fallback}')
        END"""
        
        return protocol_sql
    
    def _build_query_template(self, protocol_sql: str, limits: Dict[str, int]) -> str:
        """Build the configurable query template"""
        query_template = get_config_safe(f'{self.config_namespace}.query_configuration.port_analysis_query_template', 
        """
        SELECT 
            COALESCE(src_port, dst_port) as port,
            {protocol_detection} as service_protocol,
            COUNT(*) as packets,
            SUM(packet_size) as bytes,
            COUNT(DISTINCT flow_hash) as sessions,
            -- Accurate bidirectional traffic statistics
            SUM(CASE WHEN src_port IS NOT NULL THEN 1 ELSE 0 END) as outbound_packets,
            SUM(CASE WHEN dst_port IS NOT NULL THEN 1 ELSE 0 END) as inbound_packets,
            AVG(packet_size) as avg_packet_size
        FROM packet_flows 
        WHERE device_id = $1
        AND packet_timestamp >= $2 
        AND packet_timestamp <= $3
        {experiment_filter}
        GROUP BY 1, 2
        HAVING COALESCE(src_port, dst_port) IS NOT NULL 
            AND COALESCE(src_port, dst_port) != 0
        ORDER BY SUM(packet_size) DESC
        LIMIT {max_results}
        """, f'{self.config_namespace}.query_configuration')
        
        return query_template.format(
            protocol_detection=protocol_sql,
            experiment_filter="{experiment_filter}",  # Keep placeholder for runtime replacement
            max_results=limits['max_port_results']
        )
    
    def _calculate_dynamic_activity_scores(self, raw_data: List[Dict]) -> Dict[str, Any]:
        """
        Dynamic port activity scoring based on statistical analysis and relative activity
        Returns the comprehensive activity score and dynamic thresholds for each port
        """
        if not raw_data:
            return {
                'scores': {},
                'thresholds': {'very_active': 0.9, 'active': 0.7, 'moderate': 0.4, 'low': 0.1},
                'statistics': {}
            }
        
        # Extract the metrics data
        packets_data = [row['packets'] or 0 for row in raw_data]
        bytes_data = [row['bytes'] or 0 for row in raw_data]
        sessions_data = [row['sessions'] or 0 for row in raw_data]
        avg_packet_size_data = [row['avg_packet_size'] or 0 for row in raw_data]
        
        # Calculate the statistical distribution
        import numpy as np
        
        def safe_percentile(data, percentile):
            """Safe calculation of percentiles, handling empty data cases"""
            if not data or all(x == 0 for x in data):
                return 0
            filtered_data = [x for x in data if x > 0]
            if not filtered_data:
                return 0
            return np.percentile(filtered_data, percentile)
        
        def optimize_log_normalize_metric(value, data_list):
            """
            Log normalization to handle the heavy-tailed distribution of network traffic
            """
            if not data_list or max(data_list) == 0:
                return 0
            
            # Use log1p to avoid log(0) problem, handle heavy-tailed distribution
            log_value = np.log1p(value)
            log_max = np.log1p(max(data_list))
            
            # Normalize to 0-1 range
            normalized = log_value / log_max if log_max > 0 else 0
            return min(1.0, normalized)
        
        def calculate_port_activity_score(packets, bytes_count, sessions, port_type, 
                                        outbound, inbound, all_packets_data, all_bytes_data, all_sessions_data):
            """
            Port activity scoring algorithm
            Implements comprehensive scoring with log normalization, port type weights, and bidirectional bonus
            """
            # 1. Log normalized scoring
            packets_score = optimize_log_normalize_metric(packets, all_packets_data)
            bytes_score = optimize_log_normalize_metric(bytes_count, all_bytes_data) 
            sessions_score = optimize_log_normalize_metric(sessions, all_sessions_data)
            
            # 2. Port type weights from document
            port_weights = {
                'system': 1.5,      # System ports highest weight
                'well_known': 1.2,  # Well-known ports higher weight
                'registered': 1.0,  # Registered ports standard weight
                'dynamic': 0.8      # Dynamic ports lower weight
            }
            
            # 3. Bidirectional communication bonus
            bidirectional_bonus = 0.15 if (outbound > 0 and inbound > 0) else 0
            
            # Add traffic balance bonus for more balanced bidirectional communication
            if outbound > 0 and inbound > 0:
                balance_ratio = min(outbound, inbound) / max(outbound, inbound)
                bidirectional_bonus += balance_ratio * 0.1
            
            # 4. Comprehensive scoring with document weights
            base_score = (
                packets_score * 0.4 +    # Packet weight (0.4)
                bytes_score * 0.4 +      # Byte weight (0.4) 
                sessions_score * 0.2     # Session weight (0.2)
            )
            
            # 5. Apply port type weight and bonuses
            port_weight = port_weights.get(port_type, 1.0)
            final_score = (base_score + bidirectional_bonus) * port_weight
            
            return min(1.0, max(0.0, final_score))
        
        # Calculate the percentiles for each dimension
        packets_stats = {
            'p95': safe_percentile(packets_data, 95),
            'p75': safe_percentile(packets_data, 75),
            'p50': safe_percentile(packets_data, 50),
            'p25': safe_percentile(packets_data, 25),
            'mean': np.mean(packets_data) if packets_data else 0,
            'std': np.std(packets_data) if packets_data else 0
        }
        
        bytes_stats = {
            'p95': safe_percentile(bytes_data, 95),
            'p75': safe_percentile(bytes_data, 75),
            'p50': safe_percentile(bytes_data, 50),
            'p25': safe_percentile(bytes_data, 25),
            'mean': np.mean(bytes_data) if bytes_data else 0,
            'std': np.std(bytes_data) if bytes_data else 0
        }
        
        sessions_stats = {
            'p95': safe_percentile(sessions_data, 95),
            'p75': safe_percentile(sessions_data, 75),
            'p50': safe_percentile(sessions_data, 50),
            'p25': safe_percentile(sessions_data, 25),
            'mean': np.mean(sessions_data) if sessions_data else 0,
            'std': np.std(sessions_data) if sessions_data else 0
        }
        
        # Port type weight configuration
        port_type_weights = get_config_safe(f'{self.config_namespace}.dynamic_scoring.port_type_weights', {
            'well_known': 1.2,    # 1-1023: Well-known port weight higher
            'registered': 1.0,     # 1024-49151: Registered port standard weight
            'dynamic': 0.8,        # 49152-65535: Dynamic port weight lower
            'system': 1.5          # System critical port special weight
        }, f'{self.config_namespace}.dynamic_scoring')
        
        # Critical port list
        critical_ports = get_config_safe(f'{self.config_namespace}.dynamic_scoring.critical_ports', [
            22, 23, 25, 53, 80, 110, 143, 443, 993, 995, 3389, 5432, 3306
        ], f'{self.config_namespace}.dynamic_scoring')
        
        # Calculate the comprehensive activity score for each port
        port_scores = {}
        
        for i, row in enumerate(raw_data):
            port = row['port'] or 0
            packets = row['packets'] or 0
            bytes_count = row['bytes'] or 0
            sessions = row['sessions'] or 0
            outbound = row['outbound_packets'] or 0
            inbound = row['inbound_packets'] or 0
            avg_packet_size = row['avg_packet_size'] or 0
            
            # Determine port type for scoring
            port_type = 'registered'  # Default type
            if port in critical_ports:
                port_type = 'system'
            elif 1 <= port <= 1023:
                port_type = 'well_known'
            elif 49152 <= port <= 65535:
                port_type = 'dynamic'
            
            # Use the port activity scoring algorithm
            final_score = calculate_port_activity_score(
                packets, bytes_count, sessions, port_type, 
                outbound, inbound, packets_data, bytes_data, sessions_data
            )
            
            # Calculate individual component scores for debugging/analytics
            packets_score = optimize_log_normalize_metric(packets, packets_data)
            bytes_score = optimize_log_normalize_metric(bytes_count, bytes_data)
            sessions_score = optimize_log_normalize_metric(sessions, sessions_data)
            bidirectional_bonus = 0.15 if (outbound > 0 and inbound > 0) else 0
            if outbound > 0 and inbound > 0:
                balance_ratio = min(outbound, inbound) / max(outbound, inbound)
                bidirectional_bonus += balance_ratio * 0.1
            
            port_scores[port] = {
                'score': final_score,
                'packets_score': packets_score,
                'bytes_score': bytes_score,
                'sessions_score': sessions_score,
                'bidirectional_bonus': bidirectional_bonus,
                'port_type': port_type,
                'algorithm_source': 'document_design_optimized'
            }
        
        # Determine the dynamic thresholds based on the mathematical expectation
        all_scores = [info['score'] for info in port_scores.values()]
        dynamic_thresholds = {}
        
        if all_scores:
            score_mean = np.mean(all_scores)
            score_std = np.std(all_scores)
            # Use the safe_percentile function to ensure safe handling of empty arrays
            score_p95 = safe_percentile(all_scores, 95)
            score_p75 = safe_percentile(all_scores, 75)
            score_p50 = safe_percentile(all_scores, 50)
            score_p25 = safe_percentile(all_scores, 25)
            
            # Adaptive thresholds based on statistical distribution
            dynamic_thresholds = {
                'very_active': max(0.8, min(score_mean + 2 * score_std, score_p95 * 0.95)),
                'active': max(0.6, min(score_mean + score_std, score_p75 * 0.9)),
                'moderate': max(0.3, min(score_mean, score_p50 * 0.8)),
                'low': max(0.1, min(score_mean - score_std, score_p25 * 0.8))
            }
        else:
            dynamic_thresholds = {'very_active': 0.8, 'active': 0.6, 'moderate': 0.3, 'low': 0.1}
        
        return {
            'scores': port_scores,
            'thresholds': dynamic_thresholds,
            'statistics': {
                'packets': packets_stats,
                'bytes': bytes_stats,
                'sessions': sessions_stats,
                'total_ports': len(raw_data),
                'score_distribution': {
                    'min': min(all_scores) if all_scores else 0,
                    'max': max(all_scores) if all_scores else 0,
                    'mean': np.mean(all_scores) if all_scores else 0,
                    'std': np.std(all_scores) if all_scores else 0
                }
            }
        }

    def _determine_port_status_dynamic(self, port_num: int, packets: int, bytes_count: int, 
                                     outbound: int, inbound: int, activity_analysis: Dict[str, Any]) -> str:
        """Determine the intelligent port status based on dynamic analysis"""
        
        status_mapping = get_config_safe(f'{self.config_namespace}.status_mapping', {
            'very_active': 'very_active',
            'active': 'active',
            'bidirectional': 'bidirectional',
            'moderate': 'moderate',
            'low_activity': 'low_activity',
            'inactive': 'inactive'
        }, f'{self.config_namespace}.status_mapping')
        
        # Get the scoring information for the port
        port_score_info = activity_analysis['scores'].get(port_num, {'score': 0})
        score = port_score_info['score']
        thresholds = activity_analysis['thresholds']
        
        # Special case: completely no activity
        if packets <= 0:
            return status_mapping['inactive']
        
        # Determine the activity status based on dynamic scoring
        activity_status = status_mapping['inactive']  # Default status
        
        if score >= thresholds['very_active']:
            activity_status = status_mapping['very_active']
        elif score >= thresholds['active']:
            activity_status = status_mapping['active']
        elif score >= thresholds['moderate']:
            activity_status = status_mapping['moderate']
        elif score >= thresholds['low']:
            activity_status = status_mapping['low_activity']
        else:
            activity_status = status_mapping['inactive']
        
        # Check if it is bidirectional communication
        is_bidirectional = (outbound > 0 and inbound > 0)
        
        # If it is bidirectional communication and has enough activity, you can choose to display the bidirectional status
        # But only when the activity is low, it is displayed first
        if (is_bidirectional and 
            activity_status in [status_mapping['low_activity'], status_mapping['inactive']] and
            get_config_safe(f'{self.config_namespace}.dynamic_scoring.prioritize_bidirectional', False, f'{self.config_namespace}.dynamic_scoring')):
            return status_mapping['bidirectional']
        
        # Otherwise, return the status based on activity
        return activity_status
    
    def _format_response_data(self, raw_data: List[Dict], field_mapping: Dict[str, str], 
                             formatting_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Configurable response data formatting with dynamic activity scoring"""
        # Calculate total bytes for percentage  
        total_bytes = sum(row['bytes'] or 0 for row in raw_data)
        
        # Calculate the dynamic activity score and thresholds
        activity_analysis = self._calculate_dynamic_activity_scores(raw_data)
        
        formatted_data = []
        
        for row in raw_data:
            port = row['port'] or 0
            service_protocol = row['service_protocol'] or 'unknown'
            packets = row['packets'] or 0
            bytes_count = row['bytes'] or 0
            sessions = row['sessions'] or 0
            outbound_packets = row['outbound_packets'] or 0
            inbound_packets = row['inbound_packets'] or 0
            percentage = (bytes_count / total_bytes * 100) if total_bytes > 0 else 0
            
            # Use the new dynamic status determination
            status = self._determine_port_status_dynamic(port, packets, bytes_count, 
                                                       outbound_packets, inbound_packets, activity_analysis)
            
            # Get the detailed scoring information for the port
            port_score_info = activity_analysis['scores'].get(port, {
                'score': 0,
                'packets_score': 0,
                'bytes_score': 0,
                'sessions_score': 0,
                'bidirectional_bonus': 0,
                'port_weight': 1.0
            })
            
            # Build the dynamic response object
            port_entry = {}
            
            # Core field mapping
            if formatting_config['force_integer_conversion']:
                port_entry[field_mapping['port_field']] = int(port)
                port_entry[field_mapping['packets_field']] = int(packets)
                port_entry[field_mapping['bytes_field']] = int(bytes_count)
                port_entry[field_mapping['sessions_field']] = int(sessions)
                port_entry[field_mapping['outbound_packets_field']] = int(outbound_packets)
                port_entry[field_mapping['inbound_packets_field']] = int(inbound_packets)
            else:
                port_entry[field_mapping['port_field']] = port
                port_entry[field_mapping['packets_field']] = packets
                port_entry[field_mapping['bytes_field']] = bytes_count
                port_entry[field_mapping['sessions_field']] = sessions
                port_entry[field_mapping['outbound_packets_field']] = outbound_packets
                port_entry[field_mapping['inbound_packets_field']] = inbound_packets
            
            port_entry[field_mapping['protocol_field']] = service_protocol
            port_entry[field_mapping['service_field']] = service_protocol  # Frontend compatibility
            port_entry[field_mapping['status_field']] = status
            port_entry[field_mapping['percentage_field']] = round(
                float(percentage), formatting_config['percentage_decimal_places']
            )
            port_entry[field_mapping['avg_packet_size_field']] = round(
                float(row['avg_packet_size'] or 0), formatting_config['avg_packet_size_decimal_places']
            )
            
            # Add dynamic scoring information, for debugging and advanced analysis
            include_scoring_details = get_config_safe(f'{self.config_namespace}.response.include_scoring_details', False, f'{self.config_namespace}.response')
            if include_scoring_details:
                port_entry['activity_score'] = round(port_score_info['score'], 3)
                port_entry['scoring_details'] = {
                    'packets_score': round(port_score_info.get('packets_score', 0), 3),
                    'bytes_score': round(port_score_info.get('bytes_score', 0), 3),
                    'sessions_score': round(port_score_info.get('sessions_score', 0), 3),
                    'bidirectional_bonus': round(port_score_info.get('bidirectional_bonus', 0), 3),
                    'port_weight': round(port_score_info.get('port_weight', 1.0), 2)
                }
            
            formatted_data.append(port_entry)
        
        # Add statistics to the response header
        include_statistics = get_config_safe(f'{self.config_namespace}.response.include_statistics', False, f'{self.config_namespace}.response')
        if include_statistics and formatted_data:
            statistics_entry = {
                field_mapping['port_field']: 'STATISTICS',
                field_mapping['protocol_field']: 'system_info',
                field_mapping['status_field']: 'statistics',
                'dynamic_thresholds': activity_analysis['thresholds'],
                'port_count': activity_analysis['statistics']['total_ports'],
                'score_distribution': activity_analysis['statistics']['score_distribution']
            }
            formatted_data.insert(0, statistics_entry)
        
        return formatted_data
    
    async def get_device_port_analysis(self, device_id: str, time_window: str, 
                                     experiment_id: Optional[str], database_service) -> List[Dict[str, Any]]:
        """Configurable device port analysis main method"""
        try:
            # Configurable API call log
            if get_config_safe(f'{self.config_namespace}.logging.log_api_calls', True, f'{self.config_namespace}.logging'):
                logger.info(get_log_message_safe('device_port_analysis', 'api_call_started', 
                                           component='device_port_analysis.api',
                                           device_id=device_id, time_window=time_window, 
                                           experiment_id=experiment_id))
            
            db_manager = database_service.db_manager
            
            # Get the time window boundaries
            from database.services.timezone_time_window_service import timezone_time_window_service
            start_time, end_time = await timezone_time_window_service.get_timezone_aware_time_bounds(
                experiment_id, time_window, db_manager
            )
            
            # Get the configuration
            protocol_mappings = self._get_protocol_mappings()
            query_limits = self._get_query_limits()
            field_mapping = self._get_response_field_mapping()
            formatting_config = self._get_data_formatting_config()
            
            # Build the protocol detection SQL
            protocol_sql = self._build_protocol_detection_sql(protocol_mappings)
            
            # Build the query
            base_query = self._build_query_template(protocol_sql, query_limits)
            
            # Handle experiment ID filtering
            if experiment_id:
                params = [device_id, start_time, end_time, experiment_id]
                final_query = base_query.replace('{experiment_filter}', 'AND experiment_id = $4')
            else:
                params = [device_id, start_time, end_time]
                final_query = base_query.replace('{experiment_filter}', '')
            
            # Configurable query execution log
            if get_config_safe(f'{self.config_namespace}.logging.log_query_execution', True, f'{self.config_namespace}.logging'):
                logger.info(get_log_message_safe('device_port_analysis', 'query_execution_started', 
                                           component='device_port_analysis.database',
                                           params=str(params)))
            
            result = await db_manager.execute_query(final_query, params)
            
            if not result:
                if get_config_safe(f'{self.config_namespace}.logging.log_empty_results', True, f'{self.config_namespace}.logging'):
                    logger.warning(get_log_message_safe('device_port_analysis', 'no_data_found', 
                                                  component='device_port_analysis.api',
                                                  device_id=device_id))
                return []
            
            # Format the response data
            formatted_result = self._format_response_data(result, field_mapping, formatting_config)
            
            # Configurable success log
            if get_config_safe(f'{self.config_namespace}.logging.log_api_success', True, f'{self.config_namespace}.logging'):
                logger.info(get_log_message_safe('device_port_analysis', 'api_call_completed', 
                                           component='device_port_analysis.api',
                                           device_id=device_id, results_count=len(formatted_result)))
            
            return formatted_result
            
        except Exception as e:
            # Configurable error log
            if get_config_safe(f'{self.config_namespace}.logging.log_api_errors', True, f'{self.config_namespace}.logging'):
                logger.error(get_log_message_safe('device_port_analysis', 'api_call_failed', 
                                            component='device_port_analysis.api',
                                            device_id=device_id, error=str(e)))
            raise

# Create the configurable API instance
configurable_api = ConfigurableDevicePortAnalysisAPI()

router = APIRouter()

# Use the unified dependency injection
from ...common.dependencies import get_database_service_instance

@router.get("/{device_id}/port-analysis", response_model=List[Dict[str, Any]])
async def get_device_port_analysis(
    device_id: str, 
    background_tasks: BackgroundTasks,
    time_window: str = Query(default=None, alias="time_window", description="Time window: 1h, 6h, 12h, 24h, 48h, auto"),
    experiment_id: str = Query(default=None, alias="experiment_id", description="Experiment ID for data isolation"),
    database_service = Depends(get_database_service_instance)
):
    """
    Configurable device port analysis API endpoint
    Returns comprehensive port analysis with configurable protocol detection and status determination
    """
    try:
        # Use the configurable default values
        if time_window is None:
            time_window = configurable_api._get_default_time_window()
        
        # Call the configurable API method
        result = await configurable_api.get_device_port_analysis(
            device_id=device_id,
            time_window=time_window, 
            experiment_id=experiment_id,
            database_service=database_service
        )
        
        # Broadcast removed to prevent infinite loop with frontend re-fetching
        # background_tasks.add_task(_trigger_port_analysis_broadcast, device_id, experiment_id, result)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        # Log the detailed error for debugging
        logger.error(f"Port analysis error for device {device_id}: {type(e).__name__}: {str(e)}")
        import traceback
        logger.error(f"Port analysis error traceback: {traceback.format_exc()}")
        
        error_message = get_config_safe('device_port_analysis.error_messages.general_error', 
                                 "Failed to retrieve port analysis for device '{device_id}': {error}", 
                                 'device_port_analysis.error_messages')
        raise HTTPException(
            status_code=500,
            detail=error_message.format(device_id=device_id, error=str(e))
        )

# Background task for WebSocket broadcast
async def _trigger_port_analysis_broadcast(device_id: str, experiment_id: str, response_data: list):
    """Trigger WebSocket broadcast when port analysis is accessed"""
    try:
        # Import broadcast service
        from ...services.broadcast_service import broadcast_service
        
        # Trigger broadcast for port analysis update
        await broadcast_service.emit_event(f"devices.{device_id}.port-analysis", response_data)
        
    except Exception as e:
        # Silent error handling for broadcast - don't affect API response
        logger.debug(f"Failed to trigger port analysis broadcast for {device_id}: {e}") 
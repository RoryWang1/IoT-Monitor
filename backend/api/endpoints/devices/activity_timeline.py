"""
Device Activity Timeline API Endpoint
IoT device monitoring system's intelligent activity timeline component
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Depends

# Setup unified path configuration
from ...common.path_config import setup_project_paths
setup_project_paths()

# Import the unified config manager
from config.unified_config_manager import get_config, get_log_message

logger = logging.getLogger(__name__)

class ConfigurableDeviceActivityTimelineAPI:
    """Fully configurable device activity timeline API class"""
    
    def __init__(self):
        """Initialize the configurable activity timeline API"""
        self.config_namespace = 'device_activity_timeline'
        
        # Configurable component initialization log
        if get_config(f'{self.config_namespace}.logging.log_component_initialization', True, f'{self.config_namespace}.logging'):
            logger.info(get_log_message('device_activity_timeline', 'component_initialized', 
                                       component='device_activity_timeline.api'))
    
    def _get_default_time_window(self) -> str:
        """Get the configurable default time window"""
        return get_config(f'{self.config_namespace}.defaults.time_window', '48h', f'{self.config_namespace}.defaults')
    
    def _get_aggregation_config(self) -> Dict[str, Any]:
        """Get the configurable aggregation configuration"""
        return {
            'time_unit': get_config(f'{self.config_namespace}.aggregation.time_unit', 'hour', f'{self.config_namespace}.aggregation'),
            'enable_session_counting': get_config(f'{self.config_namespace}.aggregation.enable_session_counting', True, f'{self.config_namespace}.aggregation'),
            'enable_byte_counting': get_config(f'{self.config_namespace}.aggregation.enable_byte_counting', True, f'{self.config_namespace}.aggregation'),
            'enable_packet_counting': get_config(f'{self.config_namespace}.aggregation.enable_packet_counting', True, f'{self.config_namespace}.aggregation')
        }
    
    def _get_intensity_calculation_config(self) -> Dict[str, Any]:
        """Get the configurable intensity calculation configuration"""
        return {
            'calculation_method': get_config(f'{self.config_namespace}.intensity_calculation.method', 'packet_based', f'{self.config_namespace}.intensity_calculation'),
            'packet_scale_factor': get_config(f'{self.config_namespace}.intensity_calculation.packet_scale_factor', 10.0, f'{self.config_namespace}.intensity_calculation'),
            'max_intensity': get_config(f'{self.config_namespace}.intensity_calculation.max_intensity', 100, f'{self.config_namespace}.intensity_calculation'),
            'min_intensity': get_config(f'{self.config_namespace}.intensity_calculation.min_intensity', 0, f'{self.config_namespace}.intensity_calculation'),
            'decimal_places': get_config(f'{self.config_namespace}.intensity_calculation.decimal_places', 1, f'{self.config_namespace}.intensity_calculation')
        }
    
    def _get_pattern_classification_config(self) -> Dict[str, Any]:
        """Get the configurable pattern classification configuration"""
        return {
            'thresholds': {
                'high_activity': get_config(f'{self.config_namespace}.pattern_classification.high_activity_threshold', 50, f'{self.config_namespace}.pattern_classification'),
                'normal_activity': get_config(f'{self.config_namespace}.pattern_classification.normal_activity_threshold', 10, f'{self.config_namespace}.pattern_classification'),
                'low_activity': get_config(f'{self.config_namespace}.pattern_classification.low_activity_threshold', 1, f'{self.config_namespace}.pattern_classification')
            },
            'pattern_labels': {
                'high': get_config(f'{self.config_namespace}.pattern_classification.high_pattern_label', 'high', f'{self.config_namespace}.pattern_classification'),
                'normal': get_config(f'{self.config_namespace}.pattern_classification.normal_pattern_label', 'normal', f'{self.config_namespace}.pattern_classification'),
                'low': get_config(f'{self.config_namespace}.pattern_classification.low_pattern_label', 'low', f'{self.config_namespace}.pattern_classification'),
                'inactive': get_config(f'{self.config_namespace}.pattern_classification.inactive_pattern_label', 'inactive', f'{self.config_namespace}.pattern_classification')
            }
        }
    
    def _get_response_field_mapping(self) -> Dict[str, str]:
        """Get the configurable response field mapping"""
        return {
            'timestamp_field': get_config(f'{self.config_namespace}.response_fields.timestamp_field', 'timestamp', f'{self.config_namespace}.response_fields'),
            'hour_field': get_config(f'{self.config_namespace}.response_fields.hour_field', 'hour', f'{self.config_namespace}.response_fields'),
            'minute_field': get_config(f'{self.config_namespace}.response_fields.minute_field', 'minute', f'{self.config_namespace}.response_fields'),
            'packets_field': get_config(f'{self.config_namespace}.response_fields.packets_field', 'packets', f'{self.config_namespace}.response_fields'),
            'bytes_field': get_config(f'{self.config_namespace}.response_fields.bytes_field', 'bytes', f'{self.config_namespace}.response_fields'),
            'sessions_field': get_config(f'{self.config_namespace}.response_fields.sessions_field', 'sessions', f'{self.config_namespace}.response_fields'),
            'intensity_field': get_config(f'{self.config_namespace}.response_fields.intensity_field', 'intensity', f'{self.config_namespace}.response_fields'),
            'pattern_field': get_config(f'{self.config_namespace}.response_fields.pattern_field', 'pattern', f'{self.config_namespace}.response_fields')
        }
    
    def _build_aggregation_query(self, aggregation_config: Dict[str, Any]) -> str:
        """Build the configurable aggregation query"""
        time_unit = aggregation_config['time_unit']
        
        # Configurable time aggregation function
        time_truncate_function = get_config(f'{self.config_namespace}.query_configuration.time_truncate_functions.{time_unit}', 
                                          f"DATE_TRUNC('{time_unit}', packet_timestamp)", 
                                          f'{self.config_namespace}.query_configuration')
        
        # Build the SELECT clause
        select_fields = [f"{time_truncate_function} as {time_unit}_timestamp"]
        
        if aggregation_config['enable_packet_counting']:
            select_fields.append("COUNT(*) as packet_count")
        
        if aggregation_config['enable_byte_counting']:
            select_fields.append("SUM(packet_size) as byte_count")
        
        if aggregation_config['enable_session_counting']:
            select_fields.append("COUNT(DISTINCT flow_hash) as session_count")
        
        # Configurable query template
        query_template = get_config(f'{self.config_namespace}.query_configuration.timeline_query_template', 
        """
        SELECT {select_fields}
        FROM packet_flows 
        WHERE device_id = $1
        AND packet_timestamp >= $2 
        AND packet_timestamp <= $3
        {experiment_filter}
        GROUP BY {time_truncate}
        ORDER BY {time_truncate}
        """, f'{self.config_namespace}.query_configuration')
        
        return query_template.format(
            select_fields=", ".join(select_fields),
            time_truncate=time_truncate_function,
            experiment_filter="{experiment_filter}"  # Keep placeholder for runtime replacement
        )
    
    def _calculate_intensity(self, packets: int, bytes_count: int, sessions: int, 
                           intensity_config: Dict[str, Any]) -> float:
        """
        Strength calculation algorithm
        Optimize using mathematical expectations and time decay
        """
        method = intensity_config['calculation_method']
        
        # Dynamic threshold based on mathematical expectations
        import numpy as np
        
        if method == 'packet_based':
            intensity = packets / intensity_config['packet_scale_factor'] if packets > 0 else 0
        elif method == 'byte_based':
            byte_scale = get_config(f'{self.config_namespace}.intensity_calculation.byte_scale_factor', 1024, f'{self.config_namespace}.intensity_calculation')
            intensity = bytes_count / byte_scale if bytes_count > 0 else 0
        elif method == 'session_based':
            session_scale = get_config(f'{self.config_namespace}.intensity_calculation.session_scale_factor', 5, f'{self.config_namespace}.intensity_calculation')
            intensity = sessions / session_scale if sessions > 0 else 0
        elif method == 'combined':
            # Combined calculation
            weights = get_config(f'{self.config_namespace}.intensity_calculation.combined_weights', {
                'packet_weight': 0.4,   # Increase packet weight
                'byte_weight': 0.4,     # Increase byte weight  
                'session_weight': 0.2   # Decrease session weight
            }, f'{self.config_namespace}.intensity_calculation')
            
            # Treat packets, bytes, and sessions as different "energy" measures
            packet_energy = np.log1p(packets) if packets > 0 else 0.1  # Log normalization to avoid extreme values
            byte_energy = np.log1p(bytes_count) if bytes_count > 0 else 0.1
            session_energy = np.log1p(sessions) if sessions > 0 else 0.1
            
            # Calculate distance factor (distance of data flow)
            distance_factor = 1.0  # Base distance
            
            # Apply weight formula: W = d^m * (1/E1 + 1/E2 + 1/E3)
            m = 2  # Distance index
            energy_inverse_sum = (1/packet_energy) + (1/byte_energy) + (1/session_energy)
            weight_factor = (distance_factor ** m) * energy_inverse_sum
            
            # Standardize weights and apply to each component
            packet_component = (packets / intensity_config['packet_scale_factor']) * weights['packet_weight']
            byte_component = (bytes_count / 1024) * weights['byte_weight']  
            session_component = (sessions / 5) * weights['session_weight']
            
            # Apply weight factor
            intensity = (packet_component + byte_component + session_component) * (1 / weight_factor)
            
            # Time decay factor
            from datetime import datetime
            current_hour = datetime.now().hour
            time_decay_factor = self._calculate_time_decay_factor(current_hour)
            intensity *= time_decay_factor
            
        elif method == 'adaptive':
            # Dynamic strength calculation based on mathematical expectations
            # Calculate statistical features of data
            total_activity = packets + bytes_count + sessions
            if total_activity > 0:
                # Strength calculation based on expected values
                activity_components = [packets, bytes_count, sessions]
                mean_activity = np.mean(activity_components)
                std_activity = np.std(activity_components) if len(activity_components) > 1 else 0
                
                # Standard score calculation (Z-score)
                z_score = (total_activity - mean_activity) / (std_activity + 1) if std_activity > 0 else 0
                
                # Map to intensity values (sigmoid function ensures 0-1 range)
                intensity = 1 / (1 + np.exp(-z_score))
            else:
                intensity = 0
        else:
            intensity = 0  # Default to 0 for unknown methods
        
        # Apply maximum and minimum value limits
        intensity = max(intensity_config['min_intensity'], 
                       min(intensity_config['max_intensity'], intensity))
        
        return round(intensity, intensity_config['decimal_places'])
    
    def _calculate_time_decay_factor(self, hour: int) -> float:
        """
        Calculate time decay factor
        Different time periods have different activity importance
        """
        # Define weights for different time periods
        time_weights = {
            'business_hours': (9, 17, 1.2),    # Business hours have higher weight
            'evening_peak': (18, 22, 1.1),     # Evening peak has higher weight
            'night_low': (23, 6, 0.8),         # Night activity has lower weight
            'morning_prep': (7, 8, 1.0)        # Morning preparation has normal weight
        }
        
        for period, (start, end, weight) in time_weights.items():
            if start <= end:  # Same day
                if start <= hour <= end:
                    return weight
            else:  # Cross day
                if hour >= start or hour <= end:
                    return weight
        
        return 1.0  # Default weight
    
    def _classify_pattern(self, packets: int, intensity: float, 
                         classification_config: Dict[str, Any], db_manager=None,
                         device_id: str = None, experiment_id: str = None, 
                         time_period: datetime = None) -> str:
        """Advanced multi-dimensional pattern classification using real data"""
        # Import pattern analyzer for advanced classification
        from backend.pcap_process.analyzers.utils.pattern_analyzer import PatternAnalyzer
        
        if packets == 0:
            return classification_config['pattern_labels']['inactive']
        
        # Use advanced multi-dimensional classification from document design
        if db_manager and device_id:
            try:
                pattern_analyzer = PatternAnalyzer(db_manager)
                
                # Get REAL data instead of estimates from packet_flows table
                real_bytes, real_sessions = self._get_real_traffic_data(
                    db_manager, device_id, experiment_id, time_period
                )
                
                current_hour = datetime.now().hour
                
                # Use new multi-dimensional classification with REAL data
                advanced_pattern = pattern_analyzer.classify_multidimensional_traffic_pattern(
                    packets, real_bytes, real_sessions, current_hour, intensity
                )
                
                # Map advanced patterns to configuration labels for backward compatibility
                pattern_mapping = {
                    'peak': classification_config['pattern_labels']['high'],
                    'burst': classification_config['pattern_labels']['high'], 
                    'active': classification_config['pattern_labels']['normal'],
                    'business_active': classification_config['pattern_labels']['normal'],
                    'evening_active': classification_config['pattern_labels']['normal'],
                    'evening': classification_config['pattern_labels']['normal'],
                    'business': classification_config['pattern_labels']['normal'],
                    'night': classification_config['pattern_labels']['low'],
                    'night_idle': classification_config['pattern_labels']['inactive'],
                    'idle': classification_config['pattern_labels']['low'],
                    'normal': classification_config['pattern_labels']['normal']
                }
                
                return pattern_mapping.get(advanced_pattern, classification_config['pattern_labels']['normal'])
            except Exception as e:
                logger.warning(f"Failed to use advanced pattern analysis: {e}, falling back to simple classification")
        
        # Fallback to simple classification when PatternAnalyzer is not available
        thresholds = classification_config['thresholds']
        
        if intensity >= thresholds['high_activity']:
            return classification_config['pattern_labels']['high']
        elif intensity >= thresholds['normal_activity']:
            return classification_config['pattern_labels']['normal']
        elif intensity >= thresholds['low_activity']:
            return classification_config['pattern_labels']['low']
        else:
            return classification_config['pattern_labels']['inactive']
    
    async def _get_real_traffic_data(self, db_manager, device_id: str, 
                                   experiment_id: str = None, 
                                   time_period: datetime = None) -> tuple:
        """Get real traffic data from database instead of estimates"""
        try:
            # Build time window around the specific time period
            if time_period:
                # Get data for the specific hour window
                start_time = time_period.replace(minute=0, second=0, microsecond=0)
                end_time = start_time.replace(hour=start_time.hour + 1)
            else:
                # Get recent data (last hour as fallback)
                from datetime import timedelta
                end_time = datetime.now()
                start_time = end_time - timedelta(hours=1)
            
            # Query real data from packet_flows
            if experiment_id:
                query = """
                SELECT 
                    COALESCE(SUM(packet_size), 0) as total_bytes,
                    COUNT(DISTINCT flow_hash) as total_sessions
                FROM packet_flows
                WHERE device_id = $1 
                    AND experiment_id = $2
                    AND packet_timestamp >= $3 
                    AND packet_timestamp <= $4
                """
                params = (device_id, experiment_id, start_time, end_time)
            else:
                query = """
                SELECT 
                    COALESCE(SUM(packet_size), 0) as total_bytes,
                    COUNT(DISTINCT flow_hash) as total_sessions
                FROM packet_flows
                WHERE device_id = $1 
                    AND packet_timestamp >= $2 
                    AND packet_timestamp <= $3
                """
                params = (device_id, start_time, end_time)
            
            result = await db_manager.execute_query(query, params)
            
            if result and len(result) > 0:
                real_bytes = int(result[0]['total_bytes'] or 0)
                real_sessions = int(result[0]['total_sessions'] or 0)
                logger.debug(f"Retrieved real data for device {device_id}: {real_bytes} bytes, {real_sessions} sessions")
                return real_bytes, real_sessions
            else:
                logger.warning(f"No real data found for device {device_id}, using minimal defaults")
                return 0, 0
                
        except Exception as e:
            logger.error(f"Failed to get real traffic data for device {device_id}: {e}")
            return 0, 0
    
    def _format_response_data(self, raw_data: List[Dict], aggregation_config: Dict[str, Any],
                              intensity_config: Dict[str, Any], classification_config: Dict[str, Any],
                              field_mapping: Dict[str, Any], db_manager=None, 
                              device_id: str = None, experiment_id: str = None) -> List[Dict[str, Any]]:
        """Format the aggregated data for the response"""
        formatted_data = []
        time_unit = aggregation_config['time_unit']
        
        for row in raw_data:
            timestamp_key = f'{time_unit}_timestamp'
            timestamp_obj = row.get(timestamp_key)
            
            packets = row.get('packet_count', 0) or 0
            bytes_count = row.get('byte_count', 0) or 0
            sessions = row.get('session_count', 0) or 0
            
            # Configurable intensity calculation
            intensity = self._calculate_intensity(packets, bytes_count, sessions, intensity_config)
            
            # Configurable pattern classification with real data support
            pattern = self._classify_pattern(
                packets, intensity, classification_config, db_manager,
                device_id=device_id, experiment_id=experiment_id, 
                time_period=timestamp_obj
            )
            
            # Build dynamic response object
            timeline_entry = {}
            
            # Timestamp field
            timeline_entry[field_mapping['timestamp_field']] = timestamp_obj.isoformat() if timestamp_obj else None
            timeline_entry[field_mapping['hour_field']] = timestamp_obj.hour if timestamp_obj else 0
            timeline_entry[field_mapping['minute_field']] = (
                timestamp_obj.minute if (timestamp_obj and time_unit == 'minute') else 0
            )
            
            # Statistics fields
            timeline_entry[field_mapping['packets_field']] = packets
            timeline_entry[field_mapping['bytes_field']] = bytes_count
            timeline_entry[field_mapping['sessions_field']] = sessions
            timeline_entry[field_mapping['intensity_field']] = intensity
            timeline_entry[field_mapping['pattern_field']] = pattern
            
            formatted_data.append(timeline_entry)
        
        return formatted_data
    
    async def get_device_activity_timeline(self, device_id: str, time_window: str, 
                                         experiment_id: Optional[str], database_service) -> List[Dict[str, Any]]:
        """Configurable device activity timeline main method"""
        try:
           
            if get_config(f'{self.config_namespace}.logging.log_api_calls', True, f'{self.config_namespace}.logging'):
                logger.info(get_log_message('device_activity_timeline', 'api_call_started', 
                                           component='device_activity_timeline.api',
                                           device_id=device_id, time_window=time_window, 
                                           experiment_id=experiment_id))
            
            db_manager = database_service.db_manager
            
            # Get the time window boundaries
            from database.services.timezone_time_window_service import timezone_time_window_service
            start_time, end_time = await timezone_time_window_service.get_timezone_aware_time_bounds(
                experiment_id, time_window, db_manager
            )
            
            # Get the configuration
            aggregation_config = self._get_aggregation_config()
            intensity_config = self._get_intensity_calculation_config()
            classification_config = self._get_pattern_classification_config()
            field_mapping = self._get_response_field_mapping()
            
            # Build the aggregation query
            base_query = self._build_aggregation_query(aggregation_config)
            
            # Handle experiment ID filtering
            if experiment_id:
                params = [device_id, start_time, end_time, experiment_id]
                final_query = base_query.replace('{experiment_filter}', 'AND experiment_id = $4')
            else:
                params = [device_id, start_time, end_time]
                final_query = base_query.replace('{experiment_filter}', '')
            
            # Configurable query execution log
            if get_config(f'{self.config_namespace}.logging.log_query_execution', True, f'{self.config_namespace}.logging'):
                logger.info(get_log_message('device_activity_timeline', 'query_execution_started', 
                                           component='device_activity_timeline.database',
                                           params=str(params)))
            
            result = await db_manager.execute_query(final_query, params)
            
            if not result:
                if get_config(f'{self.config_namespace}.logging.log_empty_results', True, f'{self.config_namespace}.logging'):
                    logger.warning(get_log_message('device_activity_timeline', 'no_data_found', 
                                                  component='device_activity_timeline.api',
                                                  device_id=device_id))
                return []
            
            # Format the response data
            formatted_result = self._format_response_data(
                result, aggregation_config, intensity_config, 
                classification_config, field_mapping, db_manager,
                device_id=device_id, experiment_id=experiment_id
            )
            
            # Configurable success log
            if get_config(f'{self.config_namespace}.logging.log_api_success', True, f'{self.config_namespace}.logging'):
                logger.info(get_log_message('device_activity_timeline', 'api_call_completed', 
                                           component='device_activity_timeline.api',
                                           device_id=device_id, results_count=len(formatted_result)))
            
            return formatted_result
            
        except Exception as e:
            # Configurable error log
            if get_config(f'{self.config_namespace}.logging.log_api_errors', True, f'{self.config_namespace}.logging'):
                logger.error(get_log_message('device_activity_timeline', 'api_call_failed', 
                                            component='device_activity_timeline.api',
                                            device_id=device_id, error=str(e)))
            raise

# Create the configurable API instance
configurable_api = ConfigurableDeviceActivityTimelineAPI()

router = APIRouter()

# Use the unified dependency injection
from ...common.dependencies import get_database_service_instance

@router.get("/{device_id}/activity-timeline", response_model=List[Dict[str, Any]])
async def get_device_activity_timeline(
    device_id: str, 
    background_tasks: BackgroundTasks,
    time_window: str = Query(default=None, alias="time_window", description="Time window: 1h, 6h, 12h, 24h, 48h, auto"),
    experiment_id: str = Query(default=None, alias="experiment_id", description="Experiment ID for data isolation"),
    database_service = Depends(get_database_service_instance)
):
    """
    Configurable device activity timeline API endpoint
    Returns configurable activity timeline with intensity calculation and pattern classification
    """
    try:
        # Use the configurable defaults
        if time_window is None:
            time_window = configurable_api._get_default_time_window()
        
        # Call the configurable API method
        result = await configurable_api.get_device_activity_timeline(
            device_id=device_id,
            time_window=time_window, 
            experiment_id=experiment_id,
            database_service=database_service
        )
        
        # Broadcast removed to prevent infinite loop with frontend re-fetching
        # background_tasks.add_task(_trigger_activity_timeline_broadcast, device_id, experiment_id, result)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        error_message = get_config('device_activity_timeline.error_messages.general_error', 
                                 f"Failed to retrieve activity timeline for device '{device_id}': {{error}}", 
                                 'device_activity_timeline.error_messages')
        raise HTTPException(
            status_code=500,
            detail=error_message.format(device_id=device_id, error=str(e))
        )

# Background task for WebSocket broadcast
async def _trigger_activity_timeline_broadcast(device_id: str, experiment_id: str, response_data: list):
    """Trigger WebSocket broadcast when activity timeline is accessed"""
    try:
        # Import broadcast service
        from ...services.broadcast_service import broadcast_service
        
        # Trigger broadcast for activity timeline update
        await broadcast_service.emit_event(f"devices.{device_id}.activity-timeline", response_data)
        
    except Exception as e:
        # Silent error handling for broadcast - don't affect API response
        logger.debug(f"Failed to trigger activity timeline broadcast for {device_id}: {e}")
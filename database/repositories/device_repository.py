"""
Device Repository Module
Handles all device-related database operations
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone
from database.services.database_service import PostgreSQLDatabaseManager

# Import new utility functions
# Define utility functions to avoid import issues   
def calculate_percentage(value: int, total: int) -> float:
    """Calculate percentage"""
    if total == 0:
        return 0.0
    return round((value / total) * 100, 2)
from database.decorators.error_handling import handle_database_errors, log_execution_time

logger = logging.getLogger(__name__)


class DeviceRepository:
    def __init__(self, db_manager: PostgreSQLDatabaseManager):
        self.db_manager = db_manager

    async def get_all_devices(self) -> List[Dict[str, Any]]:
        """Get all devices from database"""
        try:
            query = "SELECT device_id, device_name, device_type, mac_address, status FROM devices ORDER BY device_name"
            result = await self.db_manager.execute_query(query, ())
            return result or []
        except Exception as e:
            logger.error(f"Error getting all devices: {e}")
            return []
    
    async def get_device_by_mac(self, mac_address: str, experiment_id: str = None) -> Optional[Dict[str, Any]]:
        """Get device by MAC address from database"""
        try:
            if experiment_id:
                query = """
                SELECT device_id, device_name, device_type, mac_address, ip_address, 
                       status, manufacturer, experiment_id, created_at, updated_at
                FROM devices 
                WHERE UPPER(mac_address) = UPPER($1) AND experiment_id = $2
                LIMIT 1
                """
                params = (mac_address, experiment_id)
            else:
                query = """
                SELECT device_id, device_name, device_type, mac_address, ip_address, 
                       status, manufacturer, experiment_id, created_at, updated_at
                FROM devices 
                WHERE UPPER(mac_address) = UPPER($1)
                LIMIT 1
                """
                params = (mac_address,)
            
            logger.info(f"Getting device by MAC: {mac_address} in experiment: {experiment_id}")
            result = await self.db_manager.execute_query(query, params)
            
            if result:
                device = result[0]
                logger.info(f"Found device by MAC {mac_address}: {device['device_id']}")
                return device
            else:
                logger.warning(f"No device found for MAC {mac_address} in experiment {experiment_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting device by MAC {mac_address}: {e}")
            return None
    
    async def get_devices_list(self, limit: int = 100, offset: int = 0, experiment_id: str = None) -> List[Dict[str, Any]]:
        """Get devices list with pagination and experiment filtering"""
        try:
            if experiment_id:
                query = """
                SELECT 
                    device_id, 
                    device_name, 
                    device_type, 
                    mac_address, 
                    ip_address,
                    status, 
                    manufacturer,
                    experiment_id,
                    created_at,
                    updated_at
                FROM devices 
                WHERE experiment_id = $1
                ORDER BY device_name
                LIMIT $2 OFFSET $3
                """
                params = (experiment_id, limit, offset)
            else:
                query = """
                SELECT 
                    device_id, 
                    device_name, 
                    device_type, 
                    mac_address, 
                    ip_address,
                    status, 
                    manufacturer,
                    experiment_id,
                    created_at,
                    updated_at
                FROM devices 
                ORDER BY device_name
                LIMIT $1 OFFSET $2
                """
                params = (limit, offset)
            
            logger.info(f"Getting devices list with query: {query}, params: {params}")
            result = await self.db_manager.execute_query(query, params)
            
            # Format result for frontend compatibility
            formatted_result = []
            for device in result or []:
                formatted_device = {
                    'deviceId': device['device_id'],
                    'deviceName': device['device_name'] or f"Device_{device['mac_address'][-8:] if device['mac_address'] else 'Unknown'}",
                    'deviceType': device['device_type'] or 'unknown',
                    'macAddress': device['mac_address'],
                    'ipAddress': device['ip_address'],
                    'status': device['status'],
                    'manufacturer': device['manufacturer'],
                    'experimentId': device['experiment_id'],
                    'createdAt': device['created_at'],
                    'updatedAt': device['updated_at']
                }
                formatted_result.append(formatted_device)
            
            logger.info(f"Successfully retrieved {len(formatted_result)} devices")
            return formatted_result
            
        except Exception as e:
            logger.error(f"Error getting devices list: {e}")
            return []
    
    async def get_devices_count(self, experiment_id: str = None) -> int:
        """Get total devices count with optional experiment filtering"""
        try:
            if experiment_id:
                query = "SELECT COUNT(*) FROM devices WHERE experiment_id = $1"
                params = (experiment_id,)
            else:
                query = "SELECT COUNT(*) FROM devices"
                params = ()
            
            result = await self.db_manager.execute_scalar(query, params)
            return result or 0
            
        except Exception as e:
            logger.error(f"Error getting devices count: {e}")
            return 0

    # @handle_database_errors(default_return=None, log_prefix="Device detail query")  # Temporarily disable error handling decorator to debug
    @log_execution_time(log_prefix="DeviceRepository")
    async def get_device_detail(self, device_id: str, experiment_id: str = None, time_window: str = "24h") -> Optional[Dict[str, Any]]:
        """Get complete device detail with real-time time-window filtering"""
        try:
            logger.info(f"🔍 Getting device detail for device_id={device_id}, experiment_id={experiment_id}, time_window={time_window}")
            
            # Use unified timezone time window service
            from database.services.timezone_time_window_service import timezone_time_window_service
            
            # Get timezone-aware time bounds using unified service
            start_time, end_time = await timezone_time_window_service.get_timezone_aware_time_bounds(
                experiment_id, time_window, self.db_manager
            )
            
            logger.info(f"🔍 Time window calculated: {start_time} to {end_time}")
            
            # Get device basic info
            device_query = "SELECT * FROM devices WHERE device_id = $1"
            params = [device_id]
            if experiment_id:
                device_query += " AND experiment_id = $2"
                params.append(experiment_id)
            
            logger.info(f"🔍 Device query: {device_query} with params: {params}")
            device_result = await self.db_manager.execute_query(device_query, params)
            logger.info(f"🔍 Device query result: {device_result}")
            
            if not device_result:
                logger.warning(f"🔍 Device not found: device_id={device_id}, experiment_id={experiment_id}")
                return None

            device = device_result[0]
            logger.info(f"🔍 Device found: {device}")

            # Get REAL-TIME statistics from packet_flows within time window
            if experiment_id is not None:
                realtime_stats_query = """
                SELECT 
                    COUNT(DISTINCT flow_hash) as total_sessions,
                    SUM(packet_size) as total_bytes,
                    MIN(packet_timestamp) as first_seen,
                    MAX(packet_timestamp) as last_seen
                FROM packet_flows 
                WHERE device_id = $1 
                    AND experiment_id = $2
                    AND packet_timestamp >= $3 
                    AND packet_timestamp <= $4
                """
                stats_params = [device_id, experiment_id, start_time, end_time]
            else:
                realtime_stats_query = """
                SELECT 
                    COUNT(DISTINCT flow_hash) as total_sessions,
                    SUM(packet_size) as total_bytes,
                    MIN(packet_timestamp) as first_seen,
                    MAX(packet_timestamp) as last_seen
                FROM packet_flows 
                WHERE device_id = $1 
                    AND packet_timestamp >= $2 
                    AND packet_timestamp <= $3
                """
                stats_params = [device_id, start_time, end_time]
            
            logger.info(f"Stats query: {realtime_stats_query} with params: {stats_params}")
            stats_result = await self.db_manager.execute_query(realtime_stats_query, stats_params)
            logger.info(f"Stats query result: {stats_result}")
            
            stats = stats_result[0] if stats_result else {}
            logger.info(f"Processed stats: {stats}")

            # Try to get reference data for device
            mac_address = device.get('mac_address')
            resolved_name = device.get('device_name')
            resolved_vendor = device.get('manufacturer', 'Unknown')
            resolved_type = device.get('device_type', 'unknown')
            resolution_source = 'known_device' if resolved_name else 'none'

            # Format traffic value
            total_traffic = stats.get('total_bytes', 0) or 0
            if isinstance(total_traffic, (int, float)) and total_traffic > 0:
                if total_traffic >= 1024**3:
                    traffic_str = f"{total_traffic / (1024**3):.1f} GB"
                elif total_traffic >= 1024**2:
                    traffic_str = f"{total_traffic / (1024**2):.1f} MB"
                elif total_traffic >= 1024:
                    traffic_str = f"{total_traffic / 1024:.1f} KB"
                else:
                    traffic_str = f"{total_traffic} B"
            else:
                traffic_str = "0 B"

            # Return frontend-compatible format with camelCase field names
            result = {
                # Core device info
                'deviceId': device['device_id'],
                'deviceName': resolved_name or f"Device_{mac_address[-8:] if mac_address else device_id[:8]}",
                'deviceType': resolved_type,
                'macAddress': mac_address,
                'ipAddress': device.get('ip_address'),
                'manufacturer': resolved_vendor,
                'status': device.get('status', 'unknown'),
                'experimentId': device.get('experiment_id'),
                
                # Reference resolution info
                'resolvedName': resolved_name,
                'resolvedVendor': resolved_vendor,
                'resolvedType': resolved_type,
                'resolutionSource': resolution_source,
                
                # Statistics
                'firstSeen': stats.get('first_seen'),
                'lastSeen': stats.get('last_seen'),
                'totalSessions': stats.get('total_sessions', 0) or 0,
                'totalTraffic': traffic_str,
                'activeDuration': self._calculate_duration(stats.get('first_seen'), stats.get('last_seen')),
                
                # Additional metadata
                'timeWindow': time_window
            }
            
            logger.info(f"Returning device detail result for {device_id}: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error getting device detail for {device_id}: {e}", exc_info=True)
            return None
    
    def _calculate_duration(self, first_seen, last_seen):
        """Calculate duration between first_seen and last_seen"""
        if not first_seen or not last_seen:
            return 'N/A'
        
        try:
            if isinstance(first_seen, str):
                from datetime import datetime
                first_seen = datetime.fromisoformat(first_seen.replace('Z', '+00:00'))
            if isinstance(last_seen, str):
                from datetime import datetime
                last_seen = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
            
            duration = last_seen - first_seen
            total_seconds = int(duration.total_seconds())
            
            if total_seconds < 60:
                return f"{total_seconds}s"
            elif total_seconds < 3600:
                minutes = total_seconds // 60
                return f"{minutes}m"
            elif total_seconds < 86400:
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                return f"{hours}h {minutes}m"
            else:
                days = total_seconds // 86400
                hours = (total_seconds % 86400) // 3600
                return f"{days}d {hours}h"
        except Exception:
            return 'N/A'

    async def get_device_protocol_distribution(self, device_id: str, time_window: str = "1h", experiment_id: str = None) -> List[Dict[str, Any]]:
        """Get device protocol distribution with unified timezone-aware analysis"""
        try:
            # Use unified timezone time window service
            from database.services.timezone_time_window_service import timezone_time_window_service
            
            # Get timezone-aware time bounds using unified service
            start_time, end_time = await timezone_time_window_service.get_timezone_aware_time_bounds(
                experiment_id, time_window, self.db_manager
            )

            # Query for protocol distribution from packet_flows with application layer protocols
            if experiment_id is not None:
                query = """
                SELECT 
                    COALESCE(app_protocol, protocol) as protocol,
                    COUNT(*) as packet_count,
                    SUM(packet_size) as byte_count,
                    COUNT(DISTINCT flow_hash) as session_count
                FROM packet_flows
                WHERE device_id = $1 
                    AND experiment_id = $2
                    AND packet_timestamp >= $3 
                    AND packet_timestamp <= $4
                GROUP BY COALESCE(app_protocol, protocol)
                ORDER BY SUM(packet_size) DESC
                """
                params = (device_id, experiment_id, start_time, end_time)
            else:
                query = """
                SELECT 
                    COALESCE(app_protocol, protocol) as protocol,
                    COUNT(*) as packet_count,
                    SUM(packet_size) as byte_count,
                    COUNT(DISTINCT flow_hash) as session_count
                FROM packet_flows
                WHERE device_id = $1 
                    AND packet_timestamp >= $2 
                    AND packet_timestamp <= $3
                GROUP BY COALESCE(app_protocol, protocol)
                ORDER BY SUM(packet_size) DESC
                """
                params = (device_id, start_time, end_time)
            
            result = await self.db_manager.execute_query(query, params)
            
            if not result:
                # Return empty result when no data in time window
                return []
            
            # Calculate total for percentages
            total_bytes = sum(row['byte_count'] or 0 for row in result)
            
            # Format results for frontend compatibility
            protocol_distribution = []
            for row in result:
                packet_count = row['packet_count'] or 0
                byte_count = row['byte_count'] or 0
                percentage = (byte_count / total_bytes * 100) if total_bytes > 0 else 0
                
                protocol_distribution.append({
                    'protocol': row['protocol'],
                    'packet_count': str(packet_count),  # Frontend expects string
                    'byte_count': str(byte_count),      # Frontend expects string
                    'percentage': f"{percentage:.2f}",   # Frontend expects string with 2 decimals
                    'sessions': row['session_count'] or 0
                })
            
            return protocol_distribution
            
        except Exception as e:
            logger.error(f"Error getting protocol distribution: {e}")
            # Return empty result on error
            return []

    async def get_device_traffic_trend(self, device_id: str, time_window: str = "24h", experiment_id: str = None) -> List[Dict[str, Any]]:
        """Get device traffic trend with timezone-aware analysis"""
        try:
            # Import timezone manager
            from database.services.timezone_manager import timezone_manager
            
            # Always define current_time for fallback responses
            if experiment_id:
                experiment_tz_str = timezone_manager.get_experiment_timezone(experiment_id)
                import pytz
                experiment_tz = pytz.timezone(experiment_tz_str)
                current_time = datetime.now(experiment_tz)
            else:
                import pytz
                current_time = datetime.now(pytz.UTC)
            
            # Use timezone-aware time bounds
            if time_window == "auto":
                # AUTO mode: query all data, no time filtering
                # Get data time range first
                time_range_query = "SELECT MIN(packet_timestamp) as min_time, MAX(packet_timestamp) as max_time FROM packet_flows WHERE device_id = $1"
                time_params = [device_id]
                if experiment_id:
                    time_range_query += " AND experiment_id = $2"
                    time_params.append(experiment_id)
                
                time_range_result = await self.db_manager.execute_query(time_range_query, time_params)
                if time_range_result and time_range_result[0]['min_time']:
                    start_time = time_range_result[0]['min_time'] 
                    end_time = time_range_result[0]['max_time']
                else:
                    start_time = current_time - timedelta(hours=24)
                    end_time = current_time
            else:
                # Traditional real-time time window - time filtering
                time_deltas = {
                    "1h": timedelta(hours=1),
                    "2h": timedelta(hours=2),
                    "6h": timedelta(hours=6), 
                    "12h": timedelta(hours=12),
                    "24h": timedelta(hours=24),
                    "48h": timedelta(hours=48)
                }
                delta = time_deltas.get(time_window, timedelta(hours=24))
                start_time = current_time - delta
                end_time = current_time
            
            # Define period_interval for AUTO mode queries
            period_mapping = {
                "1h": ("10 minutes", 6),    # 6 periods of 10 minutes
                "2h": ("20 minutes", 6),    # 6 periods of 20 minutes
                "6h": ("1 hour", 6),        # 6 periods of 1 hour
                "12h": ("2 hours", 6),      # 6 periods of 2 hours
                "24h": ("4 hours", 6),      # 6 periods of 4 hours
                "48h": ("8 hours", 6)       # 6 periods of 8 hours
            }
            period_interval, num_periods = period_mapping.get(time_window, ("4 hours", 6))

            # Check if time window is "auto" or traditional time window
            if time_window == "auto":
                # AUTO mode: query all data, no time filtering
                # Get data time range first
                time_range_query = "SELECT MIN(packet_timestamp) as min_time, MAX(packet_timestamp) as max_time FROM packet_flows WHERE device_id = $1"
                time_params = [device_id]
                if experiment_id:
                    time_range_query += " AND experiment_id = $2"
                    time_params.append(experiment_id)
                
                time_range_result = await self.db_manager.execute_query(time_range_query, time_params)
                if time_range_result and time_range_result[0]['min_time']:
                    start_time = time_range_result[0]['min_time'] 
                    end_time = time_range_result[0]['max_time']
                else:
                    start_time = current_time - timedelta(hours=24)
                    end_time = current_time
            else:
                # Traditional real-time time window - time filtering
                time_deltas = {
                    "1h": timedelta(hours=1),
                    "2h": timedelta(hours=2),
                    "6h": timedelta(hours=6), 
                    "12h": timedelta(hours=12),
                    "24h": timedelta(hours=24),
                    "48h": timedelta(hours=48)
                }
                delta = time_deltas.get(time_window, timedelta(hours=24))
                start_time = current_time - delta
                end_time = current_time
            
            # Select time grouping granularity based on time window and data range
            if time_window == "auto":
                # Calculate data time span, select appropriate grouping granularity
                data_duration = (end_time - start_time).total_seconds() / 3600  # hours
                logger.info(f"🔍 AUTO MODE: start_time={start_time}, end_time={end_time}, duration={data_duration:.2f}h")
                if data_duration <= 2:  # 2 hours, group by 10 minutes
                    time_trunc = "DATE_TRUNC('hour', packet_timestamp) + INTERVAL '10 minutes' * FLOOR(EXTRACT(MINUTE FROM packet_timestamp) / 10)"
                    logger.info("🔍 Using 10-minute grouping")
                elif data_duration <= 6:  # 6 hours, group by 30 minutes
                    time_trunc = "DATE_TRUNC('hour', packet_timestamp) + INTERVAL '30 minutes' * FLOOR(EXTRACT(MINUTE FROM packet_timestamp) / 30)"
                    logger.info("🔍 Using 30-minute grouping")
                else:  # More than 6 hours, group by hour
                    time_trunc = "DATE_TRUNC('hour', packet_timestamp)"
                    logger.info("🔍 Using hour grouping")
            else:
                # Traditional time window grouping strategy
                if time_window in ["1h", "2h"]:
                    time_trunc = "DATE_TRUNC('hour', packet_timestamp) + INTERVAL '10 minutes' * FLOOR(EXTRACT(MINUTE FROM packet_timestamp) / 10)"
                elif time_window in ["6h"]:
                    time_trunc = "DATE_TRUNC('hour', packet_timestamp) + INTERVAL '30 minutes' * FLOOR(EXTRACT(MINUTE FROM packet_timestamp) / 30)"
                else:  # 12h, 24h, 48h
                    time_trunc = "DATE_TRUNC('hour', packet_timestamp)"
            
            # Query for traffic trend from packet_flows with application layer protocols
            # Use positional reference instead of repeated complex expressions
            # Use CTE to calculate sessions (period-level deduplication) and protocol distribution
            if experiment_id is not None:
                query = f"""
                WITH session_counts AS (
                    SELECT 
                        {time_trunc} as time_period,
                        COUNT(DISTINCT flow_hash) as total_sessions_for_period
                    FROM packet_flows
                    WHERE device_id = $1 
                        AND experiment_id = $2
                        AND packet_timestamp >= $3 
                        AND packet_timestamp <= $4
                    GROUP BY 1
                ),
                protocol_stats AS (
                    SELECT 
                        {time_trunc} as time_period,
                        COALESCE(app_protocol, protocol) as protocol,
                        COUNT(*) as packets,
                        SUM(packet_size) as bytes
                    FROM packet_flows
                    WHERE device_id = $1 
                        AND experiment_id = $2
                        AND packet_timestamp >= $3 
                        AND packet_timestamp <= $4
                    GROUP BY 1, COALESCE(app_protocol, protocol)
                )
                SELECT 
                    ps.time_period,
                    ps.protocol,
                    ps.packets,
                    ps.bytes,
                    COALESCE(sc.total_sessions_for_period, 0) as sessions
                FROM protocol_stats ps
                LEFT JOIN session_counts sc ON ps.time_period = sc.time_period
                ORDER BY ps.time_period, ps.protocol
                """
                params = (device_id, experiment_id, start_time, end_time)
            else:
                query = f"""
                WITH session_counts AS (
                    SELECT 
                        {time_trunc} as time_period,
                        COUNT(DISTINCT flow_hash) as total_sessions_for_period
                    FROM packet_flows
                    WHERE device_id = $1 
                        AND packet_timestamp >= $2 
                        AND packet_timestamp <= $3
                    GROUP BY 1
                ),
                protocol_stats AS (
                    SELECT 
                        {time_trunc} as time_period,
                        COALESCE(app_protocol, protocol) as protocol,
                        COUNT(*) as packets,
                        SUM(packet_size) as bytes
                    FROM packet_flows
                    WHERE device_id = $1 
                        AND packet_timestamp >= $2 
                        AND packet_timestamp <= $3
                    GROUP BY 1, COALESCE(app_protocol, protocol)
                )
                SELECT 
                    ps.time_period,
                    ps.protocol,
                    ps.packets,
                    ps.bytes,
                    COALESCE(sc.total_sessions_for_period, 0) as sessions
                FROM protocol_stats ps
                LEFT JOIN session_counts sc ON ps.time_period = sc.time_period
                ORDER BY ps.time_period, ps.protocol
                """
                params = (device_id, start_time, end_time)
            
            result = await self.db_manager.execute_query(query, params)
            logger.info(f"TRAFFIC TREND SQL RESULT: {len(result) if result else 0} rows returned")
            if result:
                logger.info(f"First few results: {result[:5]}")
            
            if not result:
                # Return empty array when no real data exists - do not generate fake data points
                logger.info(f"No traffic data found for device {device_id} in time window {time_window}")
                return []
            
            # Group by timestamp and aggregate protocols
            traffic_by_period = {}
            for row in result:
                timestamp = row['time_period']
                protocol = row['protocol']
                packets = row['packets'] or 0
                bytes_count = row['bytes'] or 0
                
                if timestamp not in traffic_by_period:
                    traffic_by_period[timestamp] = {
                        'protocols': {},
                        'total_packets': 0,
                        'total_bytes': 0
                    }
                
                traffic_by_period[timestamp]['protocols'][protocol] = {
                    'packets': packets,
                    'bytes': bytes_count
                }
                traffic_by_period[timestamp]['total_packets'] += packets
                traffic_by_period[timestamp]['total_bytes'] += bytes_count
            
            # Format results for frontend with timezone-aware timestamps
            traffic_trend = []
            for timestamp, data in sorted(traffic_by_period.items()):
                # Use timezone manager for consistent timestamp formatting
                if experiment_id:
                    formatted_time = timezone_manager.format_timestamp_for_api(timestamp, experiment_id)
                else:
                    # Fallback formatting for legacy support
                    formatted_time = {
                        'timestamp': timestamp.isoformat(),
                        'display_timestamp': timestamp.strftime('%m/%d %H:%M'),
                        'short_timestamp': timestamp.strftime('%H:%M'),
                        'full_timestamp': timestamp.strftime('%Y/%m/%d %H:%M')
                    }
                
                traffic_trend.append({
                    **formatted_time,
                    'protocols': data['protocols'],
                    'total_packets': data['total_packets'],
                    'total_bytes': data['total_bytes'],
                    # Backward compatibility fields
                    'packets': data['total_packets'],
                    'bytes': data['total_bytes']
                })
            
            return traffic_trend
            
        except Exception as e:
            logger.error(f"Error getting traffic trend: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            # Fallback to single data point with timezone awareness
            try:
                from database.services.timezone_manager import timezone_manager
                if experiment_id:
                    experiment_tz_str = timezone_manager.get_experiment_timezone(experiment_id)
                    import pytz
                    experiment_tz = pytz.timezone(experiment_tz_str)
                    current_time = datetime.now(experiment_tz)
                    formatted_time = timezone_manager.format_timestamp_for_api(current_time, experiment_id)
                else:
                    # Fallback to UTC
                    import pytz
                    current_time = datetime.now(pytz.UTC)
                    formatted_time = {
                        'timestamp': current_time.isoformat(),
                        'display_timestamp': current_time.strftime('%m/%d %H:%M'),
                        'short_timestamp': current_time.strftime('%H:%M'),
                        'full_timestamp': current_time.strftime('%Y/%m/%d %H:%M')
                    }
                
                # Return empty array instead of fake data during error conditions
                return []
            except Exception as fallback_error:
                logger.error(f"Error in fallback: {fallback_error}")
                return []

    async def get_device_activity_timeline(self, device_id: str, time_window: str = "24h", experiment_id: str = None) -> List[Dict[str, Any]]:
        """Get device activity timeline with timezone-aware analysis"""
        try:
            # Import timezone manager
            from database.services.timezone_manager import timezone_manager
            
            # Always define current_time for fallback responses
            if experiment_id:
                experiment_tz_str = timezone_manager.get_experiment_timezone(experiment_id)
                import pytz
                experiment_tz = pytz.timezone(experiment_tz_str)
                current_time = datetime.now(experiment_tz)
            else:
                import pytz
                current_time = datetime.now(pytz.UTC)
            
            # Use timezone-aware time bounds
            if experiment_id:
                start_time, end_time = timezone_manager.get_timezone_aware_time_bounds(experiment_id, time_window)
            else:
                # Fallback to UTC for legacy support
                delta = timedelta(hours=24)
                start_time = current_time - delta
                end_time = current_time
            
            # If auto mode, based on actual data range
            if time_window == "auto":
                # AUTO mode: query all data, no time filtering
                if experiment_id is not None:
                    query = f"""
                    SELECT 
                        DATE_TRUNC('hour', packet_timestamp) + 
                        INTERVAL '{period_interval}' * 
                        FLOOR(EXTRACT(EPOCH FROM (packet_timestamp - DATE_TRUNC('hour', packet_timestamp))) / 
                              EXTRACT(EPOCH FROM INTERVAL '{period_interval}')) as period_start,
                        COUNT(*) as packets,
                        SUM(packet_size) as bytes,
                        COUNT(DISTINCT flow_hash) as sessions
                    FROM packet_flows
                    WHERE device_id = $1 
                        AND experiment_id = $2
                    GROUP BY period_start
                    ORDER BY period_start
                    """
                    params = (device_id, experiment_id)
                else:
                    query = f"""
                    SELECT 
                        DATE_TRUNC('hour', packet_timestamp) + 
                        INTERVAL '{period_interval}' * 
                        FLOOR(EXTRACT(EPOCH FROM (packet_timestamp - DATE_TRUNC('hour', packet_timestamp))) / 
                              EXTRACT(EPOCH FROM INTERVAL '{period_interval}')) as period_start,
                        COUNT(*) as packets,
                        SUM(packet_size) as bytes,
                        COUNT(DISTINCT flow_hash) as sessions
                    FROM packet_flows
                    WHERE device_id = $1 
                    GROUP BY period_start
                    ORDER BY period_start
                    """
                    params = (device_id,)
            else:
                # Traditional real-time time window - time filtering
                time_deltas = {
                    "1h": timedelta(hours=1),
                    "2h": timedelta(hours=2),
                    "6h": timedelta(hours=6), 
                    "12h": timedelta(hours=12),
                    "24h": timedelta(hours=24),
                    "48h": timedelta(hours=48)
                }
                delta = time_deltas.get(time_window, timedelta(hours=24))
                start_time = current_time - delta
                end_time = current_time
            
            # Determine time period based on window
            period_mapping = {
                "1h": ("5 minutes", 12),    # 12 periods of 5 minutes
                "2h": ("10 minutes", 12),   # 12 periods of 10 minutes  
                "6h": ("30 minutes", 12),   # 12 periods of 30 minutes
                "12h": ("1 hour", 12),      # 12 periods of 1 hour
                "24h": ("2 hours", 12),     # 12 periods of 2 hours
                "48h": ("4 hours", 12)      # 12 periods of 4 hours
            }
            period_interval, num_periods = period_mapping.get(time_window, ("2 hours", 12))
            
            # Query for activity timeline from packet_flows with time filtering
            if experiment_id is not None:
                query = f"""
                SELECT 
                    DATE_TRUNC('hour', packet_timestamp) + 
                    INTERVAL '{period_interval}' * 
                    FLOOR(EXTRACT(EPOCH FROM (packet_timestamp - DATE_TRUNC('hour', packet_timestamp))) / 
                          EXTRACT(EPOCH FROM INTERVAL '{period_interval}')) as period_start,
                    COUNT(*) as packets,
                    SUM(packet_size) as bytes,
                    COUNT(DISTINCT flow_hash) as sessions
                FROM packet_flows
                WHERE device_id = $1 
                    AND experiment_id = $2
                    AND packet_timestamp >= $3 
                    AND packet_timestamp <= $4
                GROUP BY period_start
                ORDER BY period_start
                """
                params = (device_id, experiment_id, start_time, end_time)
            else:
                query = f"""
                SELECT 
                    DATE_TRUNC('hour', packet_timestamp) + 
                    INTERVAL '{period_interval}' * 
                    FLOOR(EXTRACT(EPOCH FROM (packet_timestamp - DATE_TRUNC('hour', packet_timestamp))) / 
                          EXTRACT(EPOCH FROM INTERVAL '{period_interval}')) as period_start,
                    COUNT(*) as packets,
                    SUM(packet_size) as bytes,
                    COUNT(DISTINCT flow_hash) as sessions
                FROM packet_flows
                WHERE device_id = $1 
                    AND packet_timestamp >= $2 
                    AND packet_timestamp <= $3
                GROUP BY period_start
                ORDER BY period_start
                """
                params = (device_id, start_time, end_time)
            
            result = await self.db_manager.execute_query(query, params)
            
            # Return empty result when no data found - like other APIs
            if not result:
                logger.warning(f"NO PACKET_FLOWS DATA FOUND in time window {time_window} - returning empty result")
                return []
            
            # Process results into timeline format - only when we have actual data
            activity_timeline = []
            
            # Collect all data for advanced intensity calculation
            all_packets_data = [row['packets'] or 0 for row in result]
            all_bytes_data = [row['bytes'] or 0 for row in result] 
            all_sessions_data = [row['sessions'] or 0 for row in result]
            
            # Convert SQL results to timeline format with optimized intensity calculation
            for row in result:
                period_start = row['period_start']
                packets = row['packets'] or 0
                bytes_count = row['bytes'] or 0
                sessions = row['sessions'] or 0
                
                # Apply advanced intensity calculation algorithm from document
                intensity = self._calculate_adaptive_intensity(
                    packets, bytes_count, sessions, period_start.hour,
                    all_packets_data, all_bytes_data, all_sessions_data
                )
                
                activity_timeline.append({
                    'timestamp': period_start.isoformat(),
                    'hour': period_start.hour,
                    'packets': packets,
                    'sessions': sessions,
                    'bytes': bytes_count,
                    'intensity': round(intensity, 1)
                })
            
            logger.info(f"REAL-TIME ACTIVITY TIMELINE: {len(activity_timeline)} periods with actual data for {time_window} window")
            return activity_timeline
            
        except Exception as e:
            logger.error(f"Error getting activity timeline: {e}")
            return []

    async def get_device_network_topology(self, device_id: str, time_window: str = "24h", experiment_id: str = None) -> Optional[Dict[str, Any]]:
        """Get device network topology with timezone-aware analysis"""
        try:
            # Import timezone manager
            from database.services.timezone_manager import timezone_manager
            
            # Always define current_time for fallback responses
            if experiment_id:
                experiment_tz_str = timezone_manager.get_experiment_timezone(experiment_id)
                import pytz
                experiment_tz = pytz.timezone(experiment_tz_str)
                current_time = datetime.now(experiment_tz)
            else:
                import pytz
                current_time = datetime.now(pytz.UTC)
            
            # Use timezone-aware time bounds
            if experiment_id:
                start_time, end_time = timezone_manager.get_timezone_aware_time_bounds(experiment_id, time_window)
            else:
                # Fallback to UTC for legacy support
                delta = timedelta(hours=24)
                start_time = current_time - delta
                end_time = current_time
            
            # If auto mode, based on actual data range
            if time_window == "auto":
                # Get data time range
                time_range_query = "SELECT MIN(packet_timestamp) as min_time, MAX(packet_timestamp) as max_time FROM packet_flows WHERE device_id = $1"
                time_params = [device_id]
                if experiment_id:
                    time_range_query += " AND experiment_id = $2"
                    time_params.append(experiment_id)
                
                time_range_result = await self.db_manager.execute_query(time_range_query, time_params)
                if time_range_result and time_range_result[0]['min_time']:
                    start_time = time_range_result[0]['min_time'] 
                    end_time = time_range_result[0]['max_time']
                else:
                    start_time = current_time - timedelta(hours=24)
                    end_time = current_time
            else:
                # Traditional real-time time window
                time_deltas = {
                    "1h": timedelta(hours=1),
                    "2h": timedelta(hours=2),
                    "6h": timedelta(hours=6), 
                    "12h": timedelta(hours=12),
                    "24h": timedelta(hours=24),
                    "48h": timedelta(hours=48)
                }
                delta = time_deltas.get(time_window, timedelta(hours=24))
                start_time = current_time - delta
                end_time = current_time
            
            # HIGH-PRECISION Network Topology Query with experiment_id isolation and data filtering
            if experiment_id is not None:
                query = """
                WITH flow_connections AS (
                    SELECT 
                        pf.src_ip,
                        pf.dst_ip,
                        pf.flow_hash,
                        pf.protocol,
                        pf.app_protocol,
                        COUNT(*) as packets,
                        SUM(pf.packet_size) as bytes,
                        MIN(pf.packet_timestamp) as first_seen,
                        MAX(pf.packet_timestamp) as last_seen
                    FROM packet_flows pf
                    WHERE pf.device_id = $1 
                        AND pf.experiment_id = $2
                        AND pf.packet_timestamp >= $3 
                        AND pf.packet_timestamp <= $4
                        AND (pf.src_ip IS NOT NULL OR pf.dst_ip IS NOT NULL)
                        AND pf.src_ip != '0.0.0.0'
                        AND pf.dst_ip != '0.0.0.0'
                    GROUP BY pf.src_ip, pf.dst_ip, pf.flow_hash, pf.protocol, pf.app_protocol
                )
                SELECT 
                    src_ip,
                    dst_ip,
                    '' as src_mac,
                    '' as dst_mac,
                    protocol,
                    app_protocol,
                    SUM(packets) as packets,
                    SUM(bytes) as bytes,
                    COUNT(DISTINCT flow_hash) as sessions,
                    MIN(first_seen) as first_seen,
                    MAX(last_seen) as last_seen
                FROM flow_connections
                GROUP BY src_ip, dst_ip, protocol, app_protocol
                ORDER BY SUM(bytes) DESC
                LIMIT 100
                """
                params = (device_id, experiment_id, start_time, end_time)
            else:
                query = """
                WITH flow_connections AS (
                    SELECT 
                        pf.src_ip,
                        pf.dst_ip,
                        pf.flow_hash,
                        pf.protocol,
                        pf.app_protocol,
                        COUNT(*) as packets,
                        SUM(pf.packet_size) as bytes,
                        MIN(pf.packet_timestamp) as first_seen,
                        MAX(pf.packet_timestamp) as last_seen
                    FROM packet_flows pf
                    WHERE pf.device_id = $1 
                        AND pf.packet_timestamp >= $2 
                        AND pf.packet_timestamp <= $3
                        AND (pf.src_ip IS NOT NULL OR pf.dst_ip IS NOT NULL)
                        AND pf.src_ip != '0.0.0.0'
                        AND pf.dst_ip != '0.0.0.0'
                    GROUP BY pf.src_ip, pf.dst_ip, pf.flow_hash, pf.protocol, pf.app_protocol
                )
                SELECT 
                    src_ip,
                    dst_ip,
                    '' as src_mac,
                    '' as dst_mac,
                    protocol,
                    app_protocol,
                    SUM(packets) as packets,
                    SUM(bytes) as bytes,
                    COUNT(DISTINCT flow_hash) as sessions,
                    MIN(first_seen) as first_seen,
                    MAX(last_seen) as last_seen
                FROM flow_connections
                GROUP BY src_ip, dst_ip, protocol, app_protocol
                ORDER BY SUM(bytes) DESC
                LIMIT 100
                """
                params = (device_id, start_time, end_time)
            
            result = await self.db_manager.execute_query(query, params)
            
            # Get device info for the main device with MAC address
            device_info_query = "SELECT device_name, device_type, ip_address, mac_address FROM devices WHERE device_id = $1"
            device_info_result = await self.db_manager.execute_query(device_info_query, (device_id,))
            device_info = device_info_result[0] if device_info_result else {}
            
            device_ip = device_info.get('ip_address')
            device_mac = device_info.get('mac_address')
            device_name = device_info.get('device_name', f'Device {device_id[:8]}')
            device_type = device_info.get('device_type', 'device')
            
            # Create IP to MAC address mapping (from all devices and packet_flows in the same experiment)
            mac_mapping = {}
            
            # First get known IP-MAC mapping from devices table
            if experiment_id:
                device_mac_query = "SELECT ip_address, mac_address FROM devices WHERE experiment_id = $1 AND ip_address IS NOT NULL"
                device_mac_result = await self.db_manager.execute_query(device_mac_query, (experiment_id,))
                for row in device_mac_result:
                    if row['ip_address'] and row['mac_address']:
                        mac_mapping[str(row['ip_address'])] = row['mac_address']
            
            # Supplement IP-MAC mapping from packet_flows (using recent data)
            flows_mac_query = """
            SELECT DISTINCT 
                src_ip, src_mac,
                dst_ip, dst_mac
            FROM packet_flows 
            WHERE device_id = $1 
                AND packet_timestamp >= $2 
                AND packet_timestamp <= $3
                AND (src_mac IS NOT NULL OR dst_mac IS NOT NULL)
            """
            flows_params = (device_id, start_time, end_time)
            if experiment_id:
                flows_mac_query += " AND experiment_id = $4"
                flows_params = (*flows_params, experiment_id)
            
            flows_mac_result = await self.db_manager.execute_query(flows_mac_query, flows_params)
            for row in flows_mac_result:
                # Add src_ip -> src_mac mapping
                if row['src_ip'] and row['src_mac'] and str(row['src_ip']) not in mac_mapping:
                    mac_mapping[str(row['src_ip'])] = row['src_mac']
                # Add dst_ip -> dst_mac mapping  
                if row['dst_ip'] and row['dst_mac'] and str(row['dst_ip']) not in mac_mapping:
                    mac_mapping[str(row['dst_ip'])] = row['dst_mac']
            
            # Initialize unified device resolution service
            from database.services.device_resolution_service import DeviceResolutionService
            resolution_service = DeviceResolutionService(self.db_manager)
            
            # Collect all MAC addresses that need resolution
            mac_addresses_to_resolve = []
            if device_mac:
                mac_addresses_to_resolve.append(device_mac)
            
            # Add MAC addresses from flow data
            if result:
                for row in result:
                    src_mac = row['src_mac'] or mac_mapping.get(str(row['src_ip']), None)
                    dst_mac = row['dst_mac'] or mac_mapping.get(str(row['dst_ip']), None)
                    if src_mac and src_mac not in mac_addresses_to_resolve:
                        mac_addresses_to_resolve.append(src_mac)
                    if dst_mac and dst_mac not in mac_addresses_to_resolve:
                        mac_addresses_to_resolve.append(dst_mac)
            
            # Bulk resolve all MAC addresses for better performance
            resolution_cache = {}
            if mac_addresses_to_resolve:
                resolution_cache = await resolution_service.bulk_resolve_devices(mac_addresses_to_resolve)
            
            # Helper function to get vendor from MAC address using cached resolutions
            def get_vendor_from_mac(mac_addr):
                """Get vendor information from pre-resolved cache"""
                if not mac_addr or mac_addr == 'Unknown':
                    return 'Unknown'
                
                if mac_addr in resolution_cache:
                    return resolution_cache[mac_addr].get('resolved_vendor', 'Unknown')
                else:
                    return 'Unknown'
            
            # Build nodes and edges
            nodes = {}
            edges = []
            
            # Helper function to classify external devices
            def classify_external_device(ip_addr, mac_addr=None):
                """Classify external devices based on IP address and other information"""
                # Check if it is a local network
                if (ip_addr.startswith('192.168.') or ip_addr.startswith('10.') or 
                    ip_addr.startswith('172.16.') or ip_addr.startswith('172.17.') or
                    ip_addr.startswith('172.18.') or ip_addr.startswith('172.19.') or
                    ip_addr.startswith('172.20.') or ip_addr.startswith('172.21.') or
                    ip_addr.startswith('172.22.') or ip_addr.startswith('172.23.') or
                    ip_addr.startswith('172.24.') or ip_addr.startswith('172.25.') or
                    ip_addr.startswith('172.26.') or ip_addr.startswith('172.27.') or
                    ip_addr.startswith('172.28.') or ip_addr.startswith('172.29.') or
                    ip_addr.startswith('172.30.') or ip_addr.startswith('172.31.')):
                    
                    # Check if it is a gateway
                    if ip_addr.endswith('.1') or ip_addr.endswith('.254'):
                        return 'gateway', 'Gateway/Router', '#FF6B6B'
                    else:
                        return 'local', f'Local Device {ip_addr.split(".")[-1]}', '#96CEB4'
                
                # External internet address
                if (ip_addr.startswith('23.') or ip_addr.startswith('107.') or 
                    ip_addr.startswith('50.') or ip_addr.startswith('52.') or
                    ip_addr.startswith('54.') or ip_addr.startswith('35.')):
                    return 'cloud', f'Cloud Service {ip_addr.split(".")[-1]}', '#FFEAA7'
                
                # Other external addresses
                return 'external', f'External {ip_addr.split(".")[-1]}', '#DDA0DD'
            
            # Add main device node with MAC address and vendor info
            if device_ip:
                main_vendor = get_vendor_from_mac(device_mac)
                main_label = f"{device_name}" if main_vendor == 'Unknown' else f"{device_name} ({main_vendor})"
                
                nodes[device_ip] = {
                    'id': device_ip,
                    'label': main_label,
                    'resolved_label': main_label,
                    'resolved_vendor': main_vendor,
                    'resolved_type': device_type,
                    'resolution_source': 'known_device',
                    'type': device_type,
                    'ip': device_ip,
                    'macAddress': device_mac or 'Unknown',
                    'size': 35,  # Main device is larger
                    'color': '#4ECDC4'
                }
            
            if not result:
                # When no data in time window, return only the device node without connections
                pass
            else:
                # Process connections with enhanced node information
                max_bytes = max([row['bytes'] or 0 for row in result]) if result else 1
                for row in result:
                    src_ip = row['src_ip']
                    dst_ip = row['dst_ip']
                    src_mac = row['src_mac'] or mac_mapping.get(str(src_ip), 'Unknown')
                    dst_mac = row['dst_mac'] or mac_mapping.get(str(dst_ip), 'Unknown')
                    protocol = row['protocol']
                    app_protocol = row['app_protocol'] or protocol
                    packets = row['packets'] or 0
                    bytes_count = row['bytes'] or 0
                    first_seen = row['first_seen']
                    last_seen = row['last_seen']
                    
                    # Add source node with vendor resolution
                    if src_ip not in nodes:
                        if str(src_ip) == str(device_ip):
                            node_vendor = get_vendor_from_mac(device_mac)
                            node_label = f"{device_name}" if node_vendor == 'Unknown' else f"{device_name} ({node_vendor})"
                            node_type = device_type
                            node_color = '#4ECDC4'
                            node_size = 35
                            node_mac = device_mac or 'Unknown'
                            resolution_source = 'known_device'
                        else:
                            node_type, base_label, node_color = classify_external_device(str(src_ip), src_mac)
                            node_size = 25
                            node_mac = src_mac
                            node_vendor = get_vendor_from_mac(src_mac)
                            
                            # Enhanced labeling with vendor info
                            if node_vendor != 'Unknown':
                                node_label = f"{base_label} ({node_vendor})"
                                resolution_source = 'vendor_pattern'
                            else:
                                node_label = base_label
                                resolution_source = 'none'
                        
                        nodes[src_ip] = {
                            'id': str(src_ip),
                            'label': node_label,
                            'resolved_label': node_label,
                            'resolved_vendor': node_vendor if 'node_vendor' in locals() else 'Unknown',
                            'resolved_type': node_type,
                            'resolution_source': resolution_source if 'resolution_source' in locals() else 'none',
                            'type': node_type,
                            'ip': str(src_ip),
                            'macAddress': node_mac,
                            'size': node_size,
                            'color': node_color
                        }
                    
                    # Add destination node with vendor resolution
                    if dst_ip not in nodes:
                        if str(dst_ip) == str(device_ip):
                            node_vendor = get_vendor_from_mac(device_mac)
                            node_label = f"{device_name}" if node_vendor == 'Unknown' else f"{device_name} ({node_vendor})"
                            node_type = device_type
                            node_color = '#4ECDC4'
                            node_size = 35
                            node_mac = device_mac or 'Unknown'
                            resolution_source = 'known_device'
                        else:
                            node_type, base_label, node_color = classify_external_device(str(dst_ip), dst_mac)
                            node_size = 25
                            node_mac = dst_mac
                            node_vendor = get_vendor_from_mac(dst_mac)
                            
                            # Enhanced labeling with vendor info
                            if node_vendor != 'Unknown':
                                node_label = f"{base_label} ({node_vendor})"
                                resolution_source = 'vendor_pattern'
                            else:
                                node_label = base_label
                                resolution_source = 'none'
                        
                        nodes[dst_ip] = {
                            'id': str(dst_ip),
                            'label': node_label,
                            'resolved_label': node_label,
                            'resolved_vendor': node_vendor if 'node_vendor' in locals() else 'Unknown',
                            'resolved_type': node_type,
                            'resolution_source': resolution_source if 'resolution_source' in locals() else 'none',
                            'type': node_type,
                            'ip': str(dst_ip),
                            'macAddress': node_mac,
                            'size': node_size,
                            'color': node_color
                        }
                    
                    # Calculate dynamic edge weight based on traffic volume
                    traffic_ratio = bytes_count / max_bytes if max_bytes > 0 else 0.1
                    edge_weight = max(1, min(10, int(traffic_ratio * 10)))  # 1-10 range
                    
                    # Add edge with enhanced information
                    edges.append({
                        'source': str(src_ip),
                        'target': str(dst_ip),
                        'weight': edge_weight,
                        'packets': packets,
                        'bytes': bytes_count,
                        'protocol': protocol,
                        'app_protocol': app_protocol,
                        'first_seen': first_seen.isoformat() if first_seen else None,
                        'last_seen': last_seen.isoformat() if last_seen else None,
                        'duration': str(last_seen - first_seen) if first_seen and last_seen else 'Unknown',
                        'src_mac': src_mac,
                        'dst_mac': dst_mac
                    })
            
            topology = {
                'nodes': list(nodes.values()),
                'edges': edges,
                'deviceInfo': {
                    'deviceId': device_id,
                    'ip': device_ip,
                    'connections': len(edges)
                }
            }
            
            return topology
            
        except Exception as e:
            logger.error(f"Error getting network topology: {e}")
            # Return empty topology on error
            return {
                'nodes': [],
                'edges': [],
                'deviceInfo': {
                    'deviceId': device_id,
                    'ip': 'Unknown',
                    'connections': 0
                }
            }

    @handle_database_errors(default_return=[], log_prefix="Port analysis query")
    @log_execution_time(log_prefix="DeviceRepository")
    async def get_device_port_analysis(self, device_id: str, time_window: str = "24h", experiment_id: str = None) -> List[Dict[str, Any]]:
        """HIGH-PRECISION Port Analysis - Fixed experiment_id handling and deduplication"""
        logger.info(f"HIGH-PRECISION PORT ANALYSIS: device={device_id}, window={time_window}, experiment={experiment_id}")
        
        # Resolve device ID
        resolved_device_id = device_id
        if not resolved_device_id:
            logger.warning(f"Could not resolve device identifier: {device_id}")
            return []

        # Use unified timezone time window service  
        from database.services.timezone_time_window_service import timezone_time_window_service
        
        # Get timezone-aware time bounds using unified service
        start_time, end_time = await timezone_time_window_service.get_timezone_aware_time_bounds(
            experiment_id, time_window, self.db_manager
        )

        # Only select fields used by frontend (removed 5 unused fields)
        if experiment_id is not None:
            precision_query = """
            SELECT 
                COALESCE(dst_port, src_port) as port,
                COUNT(*) as total_packets,
                SUM(packet_size) as total_bytes,
                STRING_AGG(DISTINCT protocol, '/' ORDER BY protocol) as protocols
            FROM packet_flows
            WHERE device_id = $1 
                AND experiment_id = $2
                AND packet_timestamp >= $3 
                AND packet_timestamp <= $4
                AND (dst_port IS NOT NULL OR src_port IS NOT NULL)
            GROUP BY COALESCE(dst_port, src_port)
            HAVING COUNT(*) > 0
            ORDER BY SUM(packet_size) DESC
            LIMIT 100
            """
            query_params = (resolved_device_id, experiment_id, start_time, end_time)
        else:
            # Only select fields used by frontend (removed 5 unused fields)
            precision_query = """
            SELECT 
                COALESCE(dst_port, src_port) as port,
                COUNT(*) as total_packets,
                SUM(packet_size) as total_bytes,
                STRING_AGG(DISTINCT protocol, '/' ORDER BY protocol) as protocols
            FROM packet_flows
            WHERE device_id = $1 
                AND packet_timestamp >= $2 
                AND packet_timestamp <= $3
                AND (dst_port IS NOT NULL OR src_port IS NOT NULL)
            GROUP BY COALESCE(dst_port, src_port)
            HAVING COUNT(*) > 0
            ORDER BY SUM(packet_size) DESC
            LIMIT 100
            """
            query_params = (resolved_device_id, start_time, end_time)

        logger.info(f"EXECUTING HIGH-PRECISION QUERY with params: {query_params}")
        result = await self.db_manager.execute_query(precision_query, query_params)
        logger.info(f"HIGH-PRECISION QUERY RESULT: {len(result) if result else 0} ports found")

        if not result:
            logger.warning(f"NO PACKET_FLOWS DATA FOUND in time window {time_window} - returning empty result")
            return []

        # Process results with deduplication
        total_packets = sum(row['total_packets'] for row in result)
        port_data = []
        seen_ports = set()  # Track unique port-protocol combinations

        for row in result:
            port_num = int(row['port']) if row['port'] else 0
            protocols = row['protocols'] or 'Unknown'
            
            # Create unique identifier
            port_key = f"{port_num}-{protocols}"
            
            if port_key in seen_ports:
                logger.warning(f"SKIPPING DUPLICATE PORT: {port_key}")
                continue
            
            seen_ports.add(port_key)
            
            packets = int(row['total_packets'])
            bytes_val = int(row['total_bytes'] or 0)
            # sessions field is no longer returned by optimized query, set to 0
            sessions = 0
            
            packet_percentage = calculate_percentage(packets, total_packets)
            service_name = self._get_service_name(port_num)
            
            port_entry = {
                'port': port_num,
                'protocol': protocols,
                'service': service_name,
                'packets': packets,
                'bytes': bytes_val,
                'sessions': sessions,
                'percentage': packet_percentage,
                'status': 'active',
                'analytics': {
                    'service_confidence': 'high',
                    'traffic_direction': 'bidirectional',
                    'data_source': 'packet_flows_real_time',
                    'time_window': time_window,
                    'analysis_accuracy': 'high_precision_real_time'
                }
            }
            port_data.append(port_entry)

        logger.info(f"HIGH-PRECISION SUCCESS: {len(port_data)} unique ports processed")
        return port_data

    async def _fallback_to_port_analysis(self, device_id: str, time_window: str) -> List[Dict[str, Any]]:
        """Fallback to port_analysis table with deduplication and enhanced structure"""
        try:
            # Use GROUP BY to deduplicate and aggregate duplicate entries
            fallback_query = """
            SELECT 
                port_number as port,
                protocol,
                SUM(packet_count) as packet_count,
                SUM(byte_count) as byte_count,
                SUM(session_count) as session_count,
                AVG(usage_percentage) as percentage,
                MIN(status) as status
            FROM port_analysis
            WHERE device_id = $1
            GROUP BY port_number, protocol
            ORDER BY SUM(packet_count) DESC
            LIMIT 50
            """
            
            fallback_result = await self.db_manager.execute_query(fallback_query, (device_id,))
            
            if not fallback_result:
                return [{
                    'port': 0,
                    'protocol': 'No Data Available',
                    'service': 'No Service',
                    'packets': 0,
                    'bytes': 0,
                    'sessions': 0,
                    'percentage': 0.0,
                    'status': 'no_data',
                    'analytics': {
                        'service_confidence': 'none',
                        'analysis_accuracy': 'no_data_available'
                    }
                }]

            port_data = []
            seen_ports = set()  # Extra deduplication check
            
            for row in fallback_result:
                port_num = int(row['port']) if row['port'] else 0
                protocol = row['protocol'] or 'Unknown'
                
                # Create unique identifier
                port_key = f"{port_num}-{protocol}"
                
                if port_key in seen_ports:
                    logger.warning(f"FALLBACK SKIPPING DUPLICATE: {port_key}")
                    continue
                
                seen_ports.add(port_key)
                
                packets = int(row['packet_count']) if row['packet_count'] else 0
                bytes_val = int(row['byte_count']) if row['byte_count'] else 0
                sessions = int(row['session_count']) if row['session_count'] else 0
                
                port_entry = {
                    'port': port_num,
                    'protocol': protocol,
                    'service': self._get_service_name(port_num),
                    'packets': packets,
                    'bytes': bytes_val,
                    'sessions': sessions,
                    'percentage': float(row['percentage']) if row['percentage'] else 0.0,
                    'status': row['status'] or 'unknown',
                    'analytics': {
                        'service_confidence': 'medium',
                        'data_source': 'port_analysis_deduped',
                        'time_window': time_window,
                        'analysis_accuracy': 'enhanced_precomputed_deduped'
                    }
                }
                port_data.append(port_entry)

            logger.info(f"FALLBACK SUCCESS: {len(port_data)} unique ports from port_analysis table")
            return port_data
            
        except Exception as e:
            logger.error(f"Error in port_analysis fallback: {e}")
            return []

    def _get_service_name(self, port: int) -> str:
        """Get service name for port"""
        service_map = {
            22: 'SSH', 23: 'Telnet', 25: 'SMTP', 53: 'DNS',
            80: 'HTTP', 110: 'POP3', 143: 'IMAP', 443: 'HTTPS',
            993: 'IMAPS', 995: 'POP3S', 8080: 'HTTP-Alt', 8443: 'HTTPS-Alt'
        }
        return service_map.get(port, f'Port-{port}')

    def _calculate_adaptive_intensity(self, packets: int, bytes_count: int, sessions: int, 
                                    hour: int, all_packets_data: list, all_bytes_data: list, 
                                    all_sessions_data: list) -> float:
        """
        Advanced activity intensity calculation algorithm based on document design
        Implements log normalization, energy weight factors, and time decay factors
        """
        import numpy as np
        
        # Edge case handling
        if packets == 0 and bytes_count == 0 and sessions == 0:
            return 0.0
        
        # Log standardization to avoid extreme values [3]
        packet_energy = np.log1p(packets) if packets > 0 else 0.1
        byte_energy = np.log1p(bytes_count) if bytes_count > 0 else 0.1
        session_energy = np.log1p(sessions) if sessions > 0 else 0.1
        
        # Weight configuration from document
        weights = {
            'packet_weight': 0.4,   # Packet weight
            'byte_weight': 0.4,     # Byte weight  
            'session_weight': 0.2   # Session weight
        }
        
        # Calculate component scores with improved normalization
        max_packets = max(all_packets_data) if all_packets_data and max(all_packets_data) > 0 else 1
        max_bytes = max(all_bytes_data) if all_bytes_data and max(all_bytes_data) > 0 else 1
        max_sessions = max(all_sessions_data) if all_sessions_data and max(all_sessions_data) > 0 else 1
        
        packet_component = (packets / max_packets) * weights['packet_weight']
        byte_component = (bytes_count / max_bytes) * weights['byte_weight']
        session_component = (sessions / max_sessions) * weights['session_weight']
        
        # Apply energy weight factor: W = d^m * (1/E1 + 1/E2 + 1/E3)
        distance_factor = 1.0  # Base distance
        m = 2  # Distance exponent
        energy_inverse_sum = (1/packet_energy) + (1/byte_energy) + (1/session_energy)
        weight_factor = (distance_factor ** m) * energy_inverse_sum
        
        # Calculate base intensity
        base_intensity = (packet_component + byte_component + session_component) * (1 / weight_factor)
        
        # Time decay factor calculation
        time_decay = self._calculate_time_decay_factor(hour)
        
        # Final intensity calculation (scale to 0-100 range)
        final_intensity = base_intensity * time_decay * 100
        
        return round(min(100.0, max(0.0, final_intensity)), 1)
    
    def _calculate_time_decay_factor(self, hour: int) -> float:
        """
        Calculate time decay factor for different time periods
        Different time periods have different activity importance weights
        """
        # Time weight configuration from document
        time_weights = {
            'business_hours': (9, 17, 1.2),    # Business hours weight higher
            'evening_peak': (18, 22, 1.1),     # Evening peak
            'night_low': (23, 6, 0.8),         # Night activity weight lower
            'morning_prep': (7, 8, 1.0)        # Morning preparation
        }
        
        for period, (start, end, weight) in time_weights.items():
            if start <= end:  # Same day
                if start <= hour <= end:
                    return weight
            else:  # Cross day (night period)
                if hour >= start or hour <= end:
                    return weight
        
        return 1.0  # Default weight
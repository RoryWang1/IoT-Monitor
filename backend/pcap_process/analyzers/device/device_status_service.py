"""
Device Status Service
Handles real-time device status calculation based on last activity time
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class DeviceStatusService:
    """Device real-time status calculation service"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def _get_threshold_hours(self) -> float:
        """Get the device online threshold hours from configuration"""
        # Always read from config to ensure we get the latest value
        try:
            from config.unified_config_manager import get_config
            threshold_hours = get_config("device_status.online_detection.threshold_hours", 24.0)
            logger.debug(f"Device status threshold loaded from config: {threshold_hours} hours")
            return threshold_hours
        except Exception as e:
            logger.warning(f"Failed to load device status threshold from config: {e}, using default 24.0 hours")
            return 24.0
    
    async def calculate_realtime_status(self, device_id: str, experiment_id: str) -> str:
        """
        Calculate device status based on last activity time
        
        Status logic:
        - Last activity within configured threshold hours: online
        - Last activity older than threshold hours: offline
        - No data: offline
        """
        try:
            # Get latest packet timestamp for this device
            query = """
            SELECT 
                MAX(packet_timestamp) as last_activity_time,
                COUNT(*) as total_packets
            FROM packet_flows 
            WHERE device_id = $1 AND experiment_id = $2
            """
            result = await self.db_manager.execute_query(query, (device_id, experiment_id))
            
            if not result or not result[0]['last_activity_time']:
                logger.debug(f"No packet data found for device {device_id}")
                return 'offline'
            
            last_activity = result[0]['last_activity_time']
            total_packets = result[0]['total_packets']
            
            # Calculate time difference from current time
            current_time = datetime.now(timezone.utc)
            
            # Ensure last_activity is timezone-aware
            if last_activity.tzinfo is None:
                # If no timezone info, assume UTC
                last_activity = last_activity.replace(tzinfo=timezone.utc)
            elif last_activity.tzinfo != timezone.utc:
                # Convert to UTC for comparison
                last_activity = last_activity.astimezone(timezone.utc)
            
            time_diff = current_time - last_activity
            time_diff_hours = time_diff.total_seconds() / 3600
            
            # Get configurable threshold
            threshold_hours = self._get_threshold_hours()
            
            logger.debug(f"Device {device_id}: last_activity={last_activity}, "
                        f"current_time={current_time}, time_diff={time_diff_hours:.1f}h, threshold={threshold_hours}h, packets={total_packets}")
            
            # Handle negative time differences (future timestamps)
            # Use absolute value to handle timezone issues or clock drift
            abs_time_diff_hours = abs(time_diff_hours)
            
            if time_diff_hours < 0:
                logger.debug(f"Device {device_id} has future timestamp {last_activity}, using absolute time difference: {abs_time_diff_hours:.1f}h")
            
            # Configurable binary status determination using absolute time difference
            if abs_time_diff_hours <= threshold_hours:
                return 'online'
            else:
                return 'offline'
                
        except Exception as e:
            logger.error(f"Error calculating device status for {device_id}: {e}")
            return 'offline'
    
    async def calculate_experiment_device_statuses(self, experiment_id: str) -> Dict[str, str]:
        """
        Calculate real-time status for all devices in an experiment
        Returns dict mapping device_id -> status
        """
        try:
            # Get all devices in the experiment with their latest packet timestamps
            query = """
            SELECT 
                d.device_id,
                MAX(pf.packet_timestamp) as last_packet_time
            FROM devices d
            LEFT JOIN packet_flows pf ON d.device_id = pf.device_id AND d.experiment_id = pf.experiment_id
            WHERE d.experiment_id = $1
            GROUP BY d.device_id
            """
            
            result = await self.db_manager.execute_query(query, (experiment_id,))
            
            if not result:
                logger.warning(f"No devices found for experiment {experiment_id}")
                return {}
            
            current_time = datetime.now(timezone.utc)
            device_statuses = {}
            threshold_hours = self._get_threshold_hours()
            
            for row in result:
                device_id = row['device_id']
                last_packet_time = row['last_packet_time']
                
                if not last_packet_time:
                    device_statuses[device_id] = 'offline'
                    continue
                
                # Calculate time difference
                time_diff = current_time - last_packet_time
                time_diff_hours = time_diff.total_seconds() / 3600
                
                # Configurable binary status determination
                if time_diff_hours <= threshold_hours:
                    device_statuses[device_id] = 'online'
                else:
                    device_statuses[device_id] = 'offline'
            
            logger.info(f"Calculated status for {len(device_statuses)} devices in experiment {experiment_id} with threshold {threshold_hours}h")
            return device_statuses
            
        except Exception as e:
            logger.error(f"Error calculating experiment device statuses for {experiment_id}: {e}")
            return {}
    
    async def get_device_status_summary(self, experiment_id: str) -> Dict[str, int]:
        """
        Get summary of device status counts for an experiment
        Returns dict with online/offline counts (no warning state)
        """
        try:
            device_statuses = await self.calculate_experiment_device_statuses(experiment_id)
            
            summary = {
                'online': 0,
                'offline': 0
            }
            
            for status in device_statuses.values():
                if status == 'online':
                    summary['online'] += 1
                else:
                    summary['offline'] += 1
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting device status summary for {experiment_id}: {e}")
            return {'online': 0, 'offline': 0} 
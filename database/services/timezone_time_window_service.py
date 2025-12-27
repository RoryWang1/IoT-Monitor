"""
Unified Timezone-Aware Time Window Service
Provides centralized time window calculation for all API endpoints
"""

import logging
from datetime import datetime, timedelta
from typing import Tuple, Optional, Dict, Any
import pytz
from database.services.timezone_manager import timezone_manager

logger = logging.getLogger(__name__)


class TimezoneTimeWindowService:
    """
    Centralized timezone-aware time window calculation service
    All API endpoints should use this service for consistent time filtering
    """
    
    def __init__(self):
        self.default_timezone = 'Europe/London'  # Fallback timezone
        
    async def get_timezone_aware_time_bounds(
        self, 
        experiment_id: Optional[str], 
        time_window: str,
        db_manager=None
    ) -> Tuple[datetime, datetime]:
        """
        Get timezone-aware time bounds for data filtering
        
        Args:
            experiment_id: Experiment ID for timezone lookup
            time_window: Time window (1h, 2h, 6h, 12h, 24h, 48h, auto)
            db_manager: Database manager for auto mode queries
            
        Returns:
            Tuple of (start_time, end_time) in experiment timezone
        """
        try:
            # Get experiment timezone or fallback
            if experiment_id:
                experiment_tz_str = timezone_manager.get_experiment_timezone(experiment_id)
                experiment_tz = pytz.timezone(experiment_tz_str)
                logger.info(f"Using experiment timezone: {experiment_tz_str}")
            else:
                experiment_tz = pytz.timezone(self.default_timezone)
                logger.warning(f"Using fallback timezone: {self.default_timezone} (no experiment_id)")
            
            # Get current time in experiment timezone
            current_time = datetime.now(experiment_tz)
            
            # Handle auto mode - query actual data range
            if time_window == "auto":
                if db_manager and experiment_id:
                    start_time, end_time = await self._get_auto_time_range(
                        db_manager, experiment_id, current_time
                    )
                else:
                    # Fallback to 24h if no DB manager
                    start_time = current_time - timedelta(hours=24)
                    end_time = current_time
                    logger.warning("Auto mode fallback to 24h (no DB manager)")
            else:
                # Calculate standard time windows
                start_time, end_time = self._calculate_standard_time_window(
                    current_time, time_window
                )
            
            logger.info(f"Time bounds calculated: {start_time} to {end_time} ({experiment_tz_str if experiment_id else self.default_timezone})")
            return start_time, end_time
            
        except Exception as e:
            logger.error(f"Error calculating timezone-aware time bounds: {e}")
            # Emergency fallback to UTC
            utc_now = datetime.now(pytz.UTC)
            delta = timedelta(hours=24)
            return utc_now - delta, utc_now
    
    async def _get_auto_time_range(
        self, 
        db_manager, 
        experiment_id: str, 
        current_time: datetime
    ) -> Tuple[datetime, datetime]:
        """Get actual data time range for auto mode"""
        try:
            time_range_query = """
            SELECT MIN(packet_timestamp) as min_time, MAX(packet_timestamp) as max_time 
            FROM packet_flows 
            WHERE experiment_id = $1
            """
            
            result = await db_manager.execute_query(time_range_query, [experiment_id])
            
            if result and result[0]['min_time']:
                start_time = result[0]['min_time']
                end_time = result[0]['max_time']
                logger.info(f"Auto mode: Using actual data range {start_time} to {end_time}")
                return start_time, end_time
            else:
                # No data found, fallback to 24h
                start_time = current_time - timedelta(hours=24)
                end_time = current_time
                logger.warning("Auto mode: No data found, using 24h fallback")
                return start_time, end_time
                
        except Exception as e:
            logger.error(f"Error in auto time range calculation: {e}")
            # Fallback to 24h
            start_time = current_time - timedelta(hours=24)
            end_time = current_time
            return start_time, end_time
    
    def _calculate_standard_time_window(
        self, 
        current_time: datetime, 
        time_window: str
    ) -> Tuple[datetime, datetime]:
        """Calculate standard time window bounds"""
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
        
        return start_time, end_time
    
    def get_query_params_with_time_filter(
        self,
        base_params: list,
        device_id: str,
        start_time: datetime,
        end_time: datetime,
        experiment_id: Optional[str] = None
    ) -> Tuple[str, list]:
        """
        Generate SQL WHERE clause and parameters with time filtering
        
        Args:
            base_params: Base parameters list
            device_id: Device ID for filtering
            start_time: Start time for filtering
            end_time: End time for filtering  
            experiment_id: Optional experiment ID
            
        Returns:
            Tuple of (where_clause, parameters)
        """
        params = base_params.copy()
        where_conditions = ["device_id = ${}".format(len(params) + 1)]
        params.append(device_id)
        
        # Add time window filtering
        where_conditions.append("packet_timestamp >= ${}".format(len(params) + 1))
        params.append(start_time)
        
        where_conditions.append("packet_timestamp <= ${}".format(len(params) + 1))
        params.append(end_time)
        
        # Add experiment isolation if provided
        if experiment_id:
            where_conditions.append("experiment_id = ${}".format(len(params) + 1))
            params.append(experiment_id)
        
        where_clause = " AND ".join(where_conditions)
        return where_clause, params
    
    async def format_response_timestamps(
        self, 
        data: Any, 
        experiment_id: Optional[str]
    ) -> Any:
        """
        Format timestamps in API response using experiment timezone
        
        Args:
            data: Response data (dict, list, or primitive)
            experiment_id: Experiment ID for timezone lookup
            
        Returns:
            Data with formatted timestamps
        """
        if not experiment_id:
            return data
            
        try:
            # Use timezone manager for consistent formatting
            if isinstance(data, dict) and 'timestamp' in data:
                timestamp = data.get('timestamp')
                if timestamp:
                    formatted = timezone_manager.format_timestamp_for_api(timestamp, experiment_id)
                    data.update(formatted)
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and 'timestamp' in item:
                        timestamp = item.get('timestamp')
                        if timestamp:
                            formatted = timezone_manager.format_timestamp_for_api(timestamp, experiment_id)
                            item.update(formatted)
            
            return data
            
        except Exception as e:
            logger.error(f"Error formatting response timestamps: {e}")
            return data


# Global singleton instance
timezone_time_window_service = TimezoneTimeWindowService() 
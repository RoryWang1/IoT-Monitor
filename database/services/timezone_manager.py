"""
Backend Timezone Management Service
Provides timezone-aware time filtering and conversion for IoT Device Monitor system
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
import pytz
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)

class TimezoneManager:
    """
    Central timezone management for IoT Device Monitor system
    Handles timezone-aware time calculations for API filtering
    """
    
    def __init__(self):
        self.supported_timezones = {
            'UTC': 'UTC',
            'Europe/London': 'Europe/London', 
            'America/New_York': 'America/New_York',
            'Asia/Shanghai': 'Asia/Shanghai',
            'Europe/Paris': 'Europe/Paris'
        }
        # File-based storage for timezone settings to persist across restarts
        self._timezone_file = '/tmp/experiment_timezones.json'
        self._experiment_timezones = self._load_timezone_settings()
        
    def _load_timezone_settings(self) -> Dict[str, str]:
        """Load timezone settings from file"""
        try:
            import json
            import os
            if os.path.exists(self._timezone_file):
                with open(self._timezone_file, 'r') as f:
                    settings = json.load(f)
                    logger.info(f"Loaded timezone settings: {settings}")
                    return settings
        except Exception as e:
            logger.warning(f"Failed to load timezone settings: {e}")
        return {}
    
    def _save_timezone_settings(self):
        """Save timezone settings to file"""
        try:
            import json
            import os
            os.makedirs(os.path.dirname(self._timezone_file), exist_ok=True)
            with open(self._timezone_file, 'w') as f:
                json.dump(self._experiment_timezones, f)
                logger.info(f"Saved timezone settings: {self._experiment_timezones}")
        except Exception as e:
            logger.error(f"Failed to save timezone settings: {e}")
        
    def get_experiment_timezone(self, experiment_id: str) -> str:
        """
        Get the configured timezone for an experiment
        Returns stored timezone or defaults to London timezone
        """
        # Always reload from file to get latest timezone settings
        self._experiment_timezones = self._load_timezone_settings()
        return self._experiment_timezones.get(experiment_id, 'Europe/London')
    
    def set_experiment_timezone(self, experiment_id: str, timezone_str: str) -> bool:
        """
        Set timezone for an experiment
        Returns True if successful
        """
        if timezone_str not in self.supported_timezones:
            return False
        
        self._experiment_timezones[experiment_id] = timezone_str
        self._save_timezone_settings()  # Persist to file
        logger.info(f"Set timezone for experiment {experiment_id} to {timezone_str}")
        return True
    
    def get_timezone_info(self, timezone_str: str) -> Dict[str, Any]:
        """Get detailed timezone information"""
        try:
            tz = pytz.timezone(timezone_str)
            now = datetime.now(tz)
            
            return {
                'timezone': timezone_str,
                'timezone_display': self._format_timezone_display(timezone_str, now),
                'utc_offset': now.strftime('%z'),
                'is_dst': bool(now.dst()),
                'current_time': now.isoformat()
            }
        except Exception as e:
            logger.warning(f"Error getting timezone info for {timezone_str}: {e}")
            # Fallback to UTC
            utc_now = datetime.now(pytz.UTC)
            return {
                'timezone': 'UTC',
                'timezone_display': 'UTC | UTC | +0000',
                'utc_offset': '+0000',
                'is_dst': False,
                'current_time': utc_now.isoformat()
            }
    
    def _format_timezone_display(self, timezone_str: str, dt: datetime) -> str:
        """Format timezone display string: Region | Abbreviation | UTC Offset"""
        try:
            # Extract region from timezone string
            region = timezone_str.split('/')[-1].replace('_', ' ')
            
            # Get timezone abbreviation
            abbrev = dt.strftime('%Z')
            
            # Get UTC offset
            offset = dt.strftime('%z')
            # Format offset as +HHMM
            if len(offset) == 5:
                offset = f"{offset[:3]}:{offset[3:]}"
            
            return f"{region} | {abbrev} | {offset}"
        except Exception:
            return f"{timezone_str} | UTC | +0000"
    
    def get_timezone_aware_time_bounds(self, experiment_id: str, time_window: str) -> Tuple[datetime, datetime]:
        """
        Calculate timezone-aware time bounds for filtering
        Returns (start_time, end_time) in experiment timezone
        """
        try:
            # Get experiment timezone
            experiment_tz_str = self.get_experiment_timezone(experiment_id)
            experiment_tz = pytz.timezone(experiment_tz_str)
            
            # Get current time in experiment timezone
            current_time = datetime.now(experiment_tz)
            
            # Handle auto mode - return full data range placeholder
            if time_window == "auto":
                # For auto mode, we'll let the repository handle the actual data range
                return current_time, current_time
            
            # Calculate time delta for regular windows
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
            
            logger.info(f"Timezone-aware time bounds for {experiment_id} ({experiment_tz_str}): {start_time} to {end_time}")
            
            return start_time, end_time
            
        except Exception as e:
            logger.error(f"Error calculating timezone-aware time bounds: {e}")
            # Fallback to UTC
            utc_now = datetime.now(pytz.UTC)
            delta = timedelta(hours=24)
            return utc_now - delta, utc_now
    
    def convert_to_experiment_timezone(self, timestamp: datetime, experiment_id: str) -> datetime:
        """Convert a timestamp to experiment timezone"""
        try:
            experiment_tz_str = self.get_experiment_timezone(experiment_id)
            experiment_tz = pytz.timezone(experiment_tz_str)
            
            # If timestamp is naive, assume it's UTC
            if timestamp.tzinfo is None:
                timestamp = pytz.UTC.localize(timestamp)
            
            # Convert to experiment timezone
            return timestamp.astimezone(experiment_tz)
            
        except Exception as e:
            logger.error(f"Error converting timestamp to experiment timezone: {e}")
            return timestamp
    
    def format_timestamp_for_api(self, timestamp: datetime, experiment_id: str) -> Dict[str, str]:
        """
        Format timestamp for API response with multiple formats
        All in experiment timezone
        """
        try:
            # Convert to experiment timezone
            tz_timestamp = self.convert_to_experiment_timezone(timestamp, experiment_id)
            
            return {
                'timestamp': tz_timestamp.isoformat(),
                'display_timestamp': tz_timestamp.strftime('%m/%d %H:%M'),  # Chart format
                'short_timestamp': tz_timestamp.strftime('%H:%M'),          # Short format  
                'full_timestamp': tz_timestamp.strftime('%Y/%m/%d %H:%M')   # Full format
            }
            
        except Exception as e:
            logger.error(f"Error formatting timestamp for API: {e}")
            # Fallback to original timestamp
            return {
                'timestamp': timestamp.isoformat(),
                'display_timestamp': timestamp.strftime('%m/%d %H:%M'),
                'short_timestamp': timestamp.strftime('%H:%M'), 
                'full_timestamp': timestamp.strftime('%Y/%m/%d %H:%M')
            }

    @asynccontextmanager
    async def timezone_context(self, experiment_id: str):
        """
        Context manager for timezone-aware operations
        Sets the timezone context for database operations
        """
        try:
            experiment_tz_str = self.get_experiment_timezone(experiment_id)
            logger.debug(f"Entering timezone context for experiment {experiment_id}: {experiment_tz_str}")
            
            # Store original timezone (if any)
            original_tz = getattr(self, '_current_timezone', None)
            self._current_timezone = experiment_tz_str
            
            yield experiment_tz_str
            
        finally:
            # Restore original timezone
            if original_tz:
                self._current_timezone = original_tz
            else:
                delattr(self, '_current_timezone')
                
            logger.debug(f"Exiting timezone context for experiment {experiment_id}")

# Global timezone manager instance
timezone_manager = TimezoneManager() 
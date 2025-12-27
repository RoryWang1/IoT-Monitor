"""
Unified Timezone Management System
Supports per-experiment timezone configuration for federated functionality
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Any, List
try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Fallback for Python < 3.9
    try:
        from backports.zoneinfo import ZoneInfo
    except ImportError:
        # Use pytz as fallback
        import pytz
        
        class ZoneInfo:
            def __init__(self, key):
                self.key = key
                self.tz = pytz.timezone(key)
            
            def __str__(self):
                return self.key

import asyncio
from functools import lru_cache

logger = logging.getLogger(__name__)


class TimezoneManager:
    """
    Centralized timezone management for IoT monitoring system
    Supports per-experiment timezone configuration
    """
    
    def __init__(self):
        self._experiment_timezones: Dict[str, str] = {}
        self._default_timezone = 'UTC'
        self._cache_size = 1000
        
    async def get_experiment_timezone(self, experiment_id: str) -> str:
        """Get timezone for specific experiment"""
        if experiment_id in self._experiment_timezones:
            return self._experiment_timezones[experiment_id]
        
        # Try to load from database
        timezone_config = await self._load_experiment_timezone_from_db(experiment_id)
        if timezone_config:
            self._experiment_timezones[experiment_id] = timezone_config
            return timezone_config
            
        # Use default timezone
        return self._default_timezone
    
    async def set_experiment_timezone(self, experiment_id: str, timezone_name: str) -> bool:
        """Set timezone for specific experiment"""
        try:
            # Validate timezone
            if not self._validate_timezone(timezone_name):
                logger.error(f"Invalid timezone: {timezone_name}")
                return False
            
            # Update in-memory cache
            self._experiment_timezones[experiment_id] = timezone_name
            
            # Persist to database
            success = await self._save_experiment_timezone_to_db(experiment_id, timezone_name)
            if not success:
                # Rollback in-memory change if database save failed
                self._experiment_timezones.pop(experiment_id, None)
                return False
                
            logger.info(f"Set timezone for experiment {experiment_id}: {timezone_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set timezone for experiment {experiment_id}: {e}")
            return False
    
    def convert_timestamp(self, dt: datetime, target_timezone: str, source_timezone: str = 'UTC') -> datetime:
        """Convert timestamp between timezones"""
        try:
            # Handle timezone-naive datetime 
            if dt.tzinfo is None:
                source_tz = ZoneInfo(source_timezone)
                dt = dt.replace(tzinfo=source_tz)
            
            # Convert to target timezone
            target_tz = ZoneInfo(target_timezone)
            return dt.astimezone(target_tz)
            
        except Exception as e:
            logger.error(f"Timezone conversion failed: {e}")
            return dt  # Return original on failure
    
    async def convert_experiment_data(self, data: Any, experiment_id: str, 
                                    timestamp_fields: List[str] = None) -> Any:
        """Convert timestamp fields in data to experiment's timezone"""
        if timestamp_fields is None:
            timestamp_fields = ['timestamp', 'created_at', 'updated_at', 'last_seen', 
                              'first_seen', 'packet_timestamp', 'time_period']
        
        experiment_tz = await self.get_experiment_timezone(experiment_id)
        
        # Handle different data types
        if isinstance(data, dict):
            return await self._convert_dict_timestamps(data, experiment_tz, timestamp_fields)
        elif isinstance(data, list):
            return await self._convert_list_timestamps(data, experiment_tz, timestamp_fields)
        else:
            return data
    
    async def _convert_dict_timestamps(self, data: Dict, target_tz: str, 
                                     timestamp_fields: List[str]) -> Dict:
        """Convert timestamp fields in dictionary"""
        converted_data = data.copy()
        
        for field in timestamp_fields:
            if field in converted_data and converted_data[field]:
                original_value = converted_data[field]
                
                # Handle datetime objects
                if isinstance(original_value, datetime):
                    converted_data[field] = self.convert_timestamp(original_value, target_tz)
                    
                # Handle ISO strings
                elif isinstance(original_value, str):
                    try:
                        dt = datetime.fromisoformat(original_value.replace('Z', '+00:00'))
                        converted_dt = self.convert_timestamp(dt, target_tz)
                        converted_data[field] = converted_dt.isoformat()
                    except ValueError:
                        # Not a valid ISO datetime string, skip
                        pass
        
        return converted_data
    
    async def _convert_list_timestamps(self, data: List, target_tz: str, 
                                     timestamp_fields: List[str]) -> List:
        """Convert timestamp fields in list of dictionaries"""
        converted_list = []
        
        for item in data:
            if isinstance(item, dict):
                converted_item = await self._convert_dict_timestamps(item, target_tz, timestamp_fields)
                converted_list.append(converted_item)
            else:
                converted_list.append(item)
        
        return converted_list
    
    def format_timestamp(self, dt: datetime, format_type: str = 'iso') -> str:
        """Format timestamp for display with enhanced date/time formats"""
        try:
            if format_type == 'iso':
                return dt.isoformat()
            elif format_type == 'display':
                return dt.strftime('%Y-%m-%d %H:%M:%S %Z')
            elif format_type == 'short':
                return dt.strftime('%m-%d %H:%M')
            elif format_type == 'time_only':
                return dt.strftime('%H:%M:%S')
            elif format_type == 'chart_display':
                return dt.strftime('%m/%d %H:%M')
            elif format_type == 'full_chart':
                return dt.strftime('%Y/%m/%d %H:%M')
            elif format_type == 'compact':
                return dt.strftime('%m%d %H:%M')
            else:
                return dt.isoformat()
        except Exception as e:
            logger.error(f"Timestamp formatting failed: {e}")
            return str(dt)
    
    @lru_cache(maxsize=100)
    def _validate_timezone(self, timezone_name: str) -> bool:
        """Validate timezone name"""
        try:
            ZoneInfo(timezone_name)
            return True
        except Exception:
            return False
    
    def get_supported_timezones(self) -> List[Dict[str, str]]:
        """Get list of supported timezones - simplified to 4 main regions with automatic DST handling"""
        common_timezones = [
            {'name': 'UTC', 'display': 'UTC - Coordinated Universal Time'},
            {'name': 'Europe/London', 'display': 'United Kingdom (GMT/BST with automatic DST)'},
            {'name': 'America/New_York', 'display': 'United States (EST/EDT with automatic DST)'},
            {'name': 'Asia/Shanghai', 'display': 'China (CST - China Standard Time)'},
            {'name': 'Europe/Paris', 'display': 'Europe (CET/CEST with automatic DST)'},
        ]
        return common_timezones
    
    async def _load_experiment_timezone_from_db(self, experiment_id: str) -> Optional[str]:
        """Load experiment timezone from database"""
        try:
            # Get database connection 
            db_manager = None
            try:
                from database.connection import get_database_connection
                db_manager = await get_database_connection()
            except ImportError:
                try:
                    # Alternative import path
                    import sys
                    import os
                    # Add project root to path
                    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                    if project_root not in sys.path:
                        sys.path.insert(0, project_root)
                    from database.connection import get_database_connection
                    db_manager = await get_database_connection()
                except ImportError as e:
                    logger.warning(f"Could not import database connection: {e}")
                    return None
            
            if not db_manager:
                logger.warning("Database connection not available")
                return None
                
            # Check if timezone column exists first
            check_column_query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'experiments' AND column_name = 'timezone'
            """
            
            column_result = await db_manager.execute_query(check_column_query)
            
            if not column_result:
                logger.info(f"Timezone column does not exist in experiments table - will add it")
                # Add timezone column if it doesn't exist
                try:
                    add_column_query = """
                    ALTER TABLE experiments 
                    ADD COLUMN IF NOT EXISTS timezone VARCHAR(50) DEFAULT 'UTC'
                    """
                    await db_manager.execute_command(add_column_query)
                    logger.info("Added timezone column to experiments table")
                except Exception as add_error:
                    logger.error(f"Failed to add timezone column: {add_error}")
                    return None
                
            # Query experiments table for timezone configuration
            query = """
            SELECT timezone FROM experiments 
            WHERE experiment_id = $1 AND timezone IS NOT NULL
            """
            result = await db_manager.execute_query(query, (experiment_id,))
            
            if result and len(result) > 0:
                timezone_name = result[0]['timezone']
                logger.info(f"Loaded timezone for experiment {experiment_id}: {timezone_name}")
                return timezone_name
            else:
                logger.info(f"No timezone found for experiment {experiment_id}, will use default")
                return None
                
        except Exception as e:
            logger.error(f"Failed to load timezone for experiment {experiment_id}: {e}")
            import traceback
            logger.error(f"Timezone load traceback: {traceback.format_exc()}")
            return None
    
    async def _save_experiment_timezone_to_db(self, experiment_id: str, timezone_name: str) -> bool:
        """Save experiment timezone to database"""
        try:
            # Get database connection 
            db_manager = None
            try:
                from database.connection import get_database_connection
                db_manager = await get_database_connection()
            except ImportError:
                try:
                    # Alternative import path
                    import sys
                    import os
                    # Add project root to path
                    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                    if project_root not in sys.path:
                        sys.path.insert(0, project_root)
                    from database.connection import get_database_connection
                    db_manager = await get_database_connection()
                except ImportError as e:
                    logger.warning(f"Could not import database connection: {e}")
                    return False
            
            if not db_manager:
                logger.warning("Database connection not available")
                return False
                
            # Check if timezone column exists first
            check_column_query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'experiments' AND column_name = 'timezone'
            """
            
            column_result = await db_manager.execute_query(check_column_query)
            
            if not column_result:
                logger.info(f"Timezone column does not exist in experiments table - will add it")
                # Add timezone column if it doesn't exist
                try:
                    add_column_query = """
                    ALTER TABLE experiments 
                    ADD COLUMN IF NOT EXISTS timezone VARCHAR(50) DEFAULT 'UTC'
                    """
                    await db_manager.execute_command(add_column_query)
                    logger.info("Added timezone column to experiments table")
                except Exception as add_error:
                    logger.error(f"Failed to add timezone column: {add_error}")
                    return False
                
            # Update experiments table with timezone configuration
            query = """
            UPDATE experiments 
            SET timezone = $1, updated_at = CURRENT_TIMESTAMP
            WHERE experiment_id = $2
            """
            
            affected_rows = await db_manager.execute_command(query, (timezone_name, experiment_id))
            
            if affected_rows > 0:
                logger.info(f"Saved timezone for experiment {experiment_id}: {timezone_name}")
                return True
            else:
                logger.warning(f"No experiment found with ID {experiment_id} to update timezone")
                return False
                
        except Exception as e:
            logger.error(f"Failed to save timezone for experiment {experiment_id}: {e}")
            import traceback
            logger.error(f"Timezone save traceback: {traceback.format_exc()}")
            return False
    
    def get_current_time_in_experiment_timezone(self, experiment_id: str) -> datetime:
        """Get current time in experiment's timezone"""
        experiment_tz = self._experiment_timezones.get(experiment_id, self._default_timezone)
        now_utc = datetime.now(timezone.utc)
        return self.convert_timestamp(now_utc, experiment_tz)
    
    async def get_timezone_info(self, experiment_id: str) -> Dict[str, Any]:
        """Get timezone information for experiment with enhanced display"""
        experiment_tz = await self.get_experiment_timezone(experiment_id)
        current_time = self.get_current_time_in_experiment_timezone(experiment_id)
        
        # Get timezone display name from supported list
        supported_timezones = self.get_supported_timezones()
        timezone_display = next(
            (tz['display'] for tz in supported_timezones if tz['name'] == experiment_tz),
            experiment_tz
        )
        
        # Extract timezone abbreviation
        timezone_abbr = current_time.strftime('%Z')
        
        return {
            'timezone': experiment_tz,
            'timezone_display': timezone_display,
            'timezone_abbr': timezone_abbr,
            'current_time': current_time.isoformat(),
            'current_time_display': self.format_timestamp(current_time, 'display'),
            'current_time_chart': self.format_timestamp(current_time, 'chart_display'),
            'utc_offset': current_time.strftime('%z'),
            'utc_offset_display': current_time.strftime('%z')[:-2] + ':' + current_time.strftime('%z')[-2:],
            'is_dst': current_time.dst() is not None and current_time.dst().total_seconds() != 0
        }


# Global timezone manager instance
timezone_manager = TimezoneManager() 
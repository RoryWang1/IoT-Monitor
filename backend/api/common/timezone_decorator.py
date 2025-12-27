"""
Timezone Conversion Decorator
Automatically converts timestamps in API responses to experiment timezone
"""

import asyncio
import logging
from functools import wraps
from typing import Any, Callable, Dict, Optional
from inspect import iscoroutinefunction

from api.common.timezone_manager import timezone_manager

logger = logging.getLogger(__name__)


def timezone_aware(
    experiment_id_param: str = 'experiment_id',
    timestamp_fields: Optional[list] = None
):
    """
    Decorator to automatically convert timestamps to experiment timezone
    
    Args:
        experiment_id_param: Name of the parameter containing experiment_id
        timestamp_fields: List of timestamp field names to convert
    """
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Call the original function
            result = await func(*args, **kwargs)
            
            # Get experiment_id from kwargs
            experiment_id = kwargs.get(experiment_id_param)
            if not experiment_id:
                # Try to get from positional args (if it's a method call)
                if hasattr(func, '__self__') and args:
                    # Look for experiment_id in function signature
                    import inspect
                    sig = inspect.signature(func)
                    param_names = list(sig.parameters.keys())
                    if experiment_id_param in param_names:
                        param_index = param_names.index(experiment_id_param)
                        if param_index < len(args):
                            experiment_id = args[param_index]
            
            # If no experiment_id found, return original result
            if not experiment_id:
                return result
            
            # Convert timestamps
            try:
                converted_result = await timezone_manager.convert_experiment_data(
                    result, experiment_id, timestamp_fields
                )
                return converted_result
            except Exception as e:
                logger.warning(f"Timezone conversion failed: {e}")
                return result
        
        def sync_wrapper(*args, **kwargs):
            # For sync functions, we can't do async timezone conversion
            # Return original result with a warning
            logger.warning(f"Timezone conversion not supported for sync function {func.__name__}")
            return func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        if iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class TimezoneAwareResponse:
    """
    Context manager for timezone-aware API responses
    """
    
    def __init__(self, experiment_id: str, timestamp_fields: Optional[list] = None):
        self.experiment_id = experiment_id
        self.timestamp_fields = timestamp_fields
    
    async def convert(self, data: Any) -> Any:
        """Convert data timestamps to experiment timezone"""
        if not self.experiment_id:
            return data
        
        try:
            return await timezone_manager.convert_experiment_data(
                data, self.experiment_id, self.timestamp_fields
            )
        except Exception as e:
            logger.warning(f"Timezone conversion failed: {e}")
            return data


def add_timezone_info(data: Dict[str, Any], experiment_id: str) -> Dict[str, Any]:
    """
    Add timezone information to API response
    """
    try:
        # Get timezone info asynchronously
        loop = asyncio.get_event_loop()
        timezone_info = loop.run_until_complete(
            timezone_manager.get_timezone_info(experiment_id)
        )
        
        # Add timezone metadata
        if isinstance(data, dict):
            data['timezone_info'] = {
                'timezone': timezone_info['timezone'],
                'current_time': timezone_info['current_time'],
                'utc_offset': timezone_info['utc_offset']
            }
    except Exception as e:
        logger.warning(f"Failed to add timezone info: {e}")
    
    return data 
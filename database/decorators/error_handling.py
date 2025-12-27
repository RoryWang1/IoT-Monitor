"""
Error handling decorator
Unified error handling logic for database operations and API calls
"""

import logging
import time
from functools import wraps
from typing import Any, Callable, Optional, Union

logger = logging.getLogger(__name__)


def handle_database_errors(
    default_return: Any = None,
    log_prefix: str = "Database operation",
    reraise: bool = False
):
    """
    Database error handling decorator
    
    Args:
        default_return: Default return value on error
        log_prefix: Log prefix
        reraise: Whether to re-raise the exception
    
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_msg = f"{log_prefix} failed in {func.__name__}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                
                if reraise:
                    raise
                return default_return
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_msg = f"{log_prefix} failed in {func.__name__}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                
                if reraise:
                    raise
                return default_return
        
        # Return the appropriate wrapper based on function type
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # CO_COROUTINE
            return async_wrapper
        else:
            # Check if it is an asynchronous function
            import inspect
            if inspect.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
    
    return decorator


def handle_api_errors(
    status_code: int = 500,
    error_message: str = "Internal server error",
    log_prefix: str = "API operation"
):
    """
    API error handling decorator
    
    Args:
        status_code: HTTP status code
        error_message: Error message
        log_prefix: Log prefix
    
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_msg = f"{log_prefix} failed in {func.__name__}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                
                # Return API error response format
                return {
                    "success": False,
                    "error": error_message,
                    "details": str(e) if logger.level <= logging.DEBUG else None,
                    "status_code": status_code
                }
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_msg = f"{log_prefix} failed in {func.__name__}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                
                # Return API error response format
                return {
                    "success": False,
                    "error": error_message,
                    "details": str(e) if logger.level <= logging.DEBUG else None,
                    "status_code": status_code
                }
        
        # Return the appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def log_execution_time(
    log_level: int = logging.INFO,
    log_prefix: str = "Operation"
):
    """
    Execution time recording decorator
    
    Args:
        log_level: Log level
        log_prefix: Log prefix
    
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.log(
                    log_level,
                    f"{log_prefix} {func.__name__} completed in {execution_time:.3f}s"
                )
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.log(
                    log_level,
                    f"{log_prefix} {func.__name__} failed after {execution_time:.3f}s: {str(e)}"
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.log(
                    log_level,
                    f"{log_prefix} {func.__name__} completed in {execution_time:.3f}s"
                )
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.log(
                    log_level,
                    f"{log_prefix} {func.__name__} failed after {execution_time:.3f}s: {str(e)}"
                )
                raise
        
        # Return the appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def validate_parameters(**validators):
    """
    Parameter validation decorator
    
    Args:
        **validators: Parameter validation dictionary, key is parameter name, value is validation function
    
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Get function parameter names
            import inspect
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Validate parameters
            for param_name, validator in validators.items():
                if param_name in bound_args.arguments:
                    value = bound_args.arguments[param_name]
                    if not validator(value):
                        raise ValueError(f"Invalid parameter {param_name}: {value}")
            
            return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Get function parameter names
            import inspect
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Validate parameters
            for param_name, validator in validators.items():
                if param_name in bound_args.arguments:
                    value = bound_args.arguments[param_name]
                    if not validator(value):
                        raise ValueError(f"Invalid parameter {param_name}: {value}")
            
            return func(*args, **kwargs)
        
        # Return the appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Common validators
def is_valid_uuid(value: str) -> bool:
    """Validate UUID format"""
    import uuid
    try:
        uuid.UUID(value)
        return True
    except (ValueError, TypeError):
        return False


def is_valid_time_window(value: str) -> bool:
    """Validate time window format"""
    valid_windows = {"1h", "2h", "6h", "12h", "24h", "48h"}
    return value in valid_windows


def is_positive_integer(value: int) -> bool:
    """Validate positive integer"""
    return isinstance(value, int) and value > 0


def is_non_empty_string(value: str) -> bool:
    """Validate non-empty string"""
    return isinstance(value, str) and len(value.strip()) > 0
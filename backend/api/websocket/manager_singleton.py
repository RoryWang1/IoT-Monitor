"""
WebSocket manager singleton
Provides a centralized way to get the WebSocket manager instance
"""

import logging
import threading
import sys
from typing import Optional, Any
from pathlib import Path

# Add configuration path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent
config_path = project_root / "config"

# Add to Python path
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(config_path) not in sys.path:
    sys.path.insert(0, str(config_path))

# Import unified config manager
from unified_config_manager import config_manager, get_config, get_log_message

logger = logging.getLogger(__name__)

class ConfigurableWebSocketManagerSingleton:
    """WebSocket manager singleton class"""
    
    def __init__(self):
        self._instance = None
        self._lock = threading.Lock()
        self._access_count = 0
        self._creation_time = None
        self._load_configuration()
    
    def _load_configuration(self):
        """Load singleton configuration"""
        # Singleton behavior configuration
        self.enable_singleton_mode = get_config('manager_singleton.singleton_behavior.enable_singleton_mode',
                                               True, 'manager_singleton.singleton_behavior')
        self.allow_external_override = get_config('manager_singleton.singleton_behavior.allow_external_override',
                                                 True, 'manager_singleton.singleton_behavior')
        self.enable_instance_reset = get_config('manager_singleton.singleton_behavior.enable_instance_reset',
                                               True, 'manager_singleton.singleton_behavior')
        self.thread_safe = get_config('manager_singleton.singleton_behavior.thread_safe',
                                    True, 'manager_singleton.singleton_behavior')
        
        # Instance management configuration
        self.lazy_initialization = get_config('manager_singleton.instance_management.lazy_initialization',
                                             True, 'manager_singleton.instance_management')
        self.enable_instance_validation = get_config('manager_singleton.instance_management.enable_instance_validation',
                                                    True, 'manager_singleton.instance_management')
        self.enable_instance_caching = get_config('manager_singleton.instance_management.enable_instance_caching',
                                                 True, 'manager_singleton.instance_management')
        self.auto_cleanup_on_error = get_config('manager_singleton.instance_management.auto_cleanup_on_error',
                                               False, 'manager_singleton.instance_management')
        
        # Logging configuration
        self.log_instance_creation = get_config('manager_singleton.logging.log_instance_creation',
                                               True, 'manager_singleton.logging')
        self.log_external_setting = get_config('manager_singleton.logging.log_external_setting',
                                              True, 'manager_singleton.logging')
        self.log_instance_status = get_config('manager_singleton.logging.log_instance_status',
                                             False, 'manager_singleton.logging')
        self.log_access_attempts = get_config('manager_singleton.logging.log_access_attempts',
                                             False, 'manager_singleton.logging')
        self.detailed_logging = get_config('manager_singleton.logging.detailed_logging',
                                         True, 'manager_singleton.logging')
        
        # Error handling configuration
        self.fail_on_creation_error = get_config('manager_singleton.error_handling.fail_on_creation_error',
                                                True, 'manager_singleton.error_handling')
        self.enable_fallback_creation = get_config('manager_singleton.error_handling.enable_fallback_creation',
                                                  False, 'manager_singleton.error_handling')
        self.log_creation_errors = get_config('manager_singleton.error_handling.log_creation_errors',
                                             True, 'manager_singleton.error_handling')
        self.retry_on_failure = get_config('manager_singleton.error_handling.retry_on_failure',
                                         False, 'manager_singleton.error_handling')
        
        # Validation configuration
        self.validate_instance_type = get_config('manager_singleton.validation.validate_instance_type',
                                                True, 'manager_singleton.validation')
        self.check_instance_methods = get_config('manager_singleton.validation.check_instance_methods',
                                                True, 'manager_singleton.validation')
        self.verify_singleton_contract = get_config('manager_singleton.validation.verify_singleton_contract',
                                                   True, 'manager_singleton.validation')
        
        # Feature configuration
        self.enable_instance_monitoring = get_config('manager_singleton.features.enable_instance_monitoring',
                                                    False, 'manager_singleton.features')
        self.enable_usage_tracking = get_config('manager_singleton.features.enable_usage_tracking',
                                               False, 'manager_singleton.features')
        self.enable_performance_metrics = get_config('manager_singleton.features.enable_performance_metrics',
                                                    False, 'manager_singleton.features')
    
    def get_instance(self):
        """Get instance"""
        if self.log_access_attempts:
            logger.debug(f"WebSocket manager access attempt #{self._access_count + 1}")
        
        # If singleton mode is not enabled, create a new instance each time
        if not self.enable_singleton_mode:
            return self._create_new_instance()
        
        # Thread safety check
        if self.thread_safe:
            with self._lock:
                return self._get_or_create_instance()
        else:
            return self._get_or_create_instance()
    
    def _get_or_create_instance(self):
        """Get or create instance"""
        if self._instance is None:
            if self.lazy_initialization:
                self._instance = self._create_new_instance()
            else:
                # Instance creation in non-lazy mode
                self._instance = self._create_new_instance()
        
        # Instance validation
        if self.enable_instance_validation and not self._validate_instance(self._instance):
            if self.auto_cleanup_on_error:
                self._instance = None
                self._instance = self._create_new_instance()
        
        # Usage tracking
        if self.enable_usage_tracking:
            self._access_count += 1
        
        return self._instance
    
    def _create_new_instance(self):
        """Create new instance"""
        try:
            # Import and create instance
            from .websocket_manager import WebSocketManager
            instance = WebSocketManager()
            
            # Record creation time
            if self.enable_performance_metrics:
                import time
                self._creation_time = time.time()
            
            if self.log_instance_creation:
                logger.info(get_log_message('manager_singleton', 'instance_created',
                                          component='manager_singleton.create'))
            
            # Instance validation
            if self.enable_instance_validation and not self._validate_instance(instance):
                raise ValueError("Created instance failed validation")
            
            return instance
            
        except Exception as e:
            if self.log_creation_errors:
                logger.error(get_log_message('manager_singleton', 'instance_creation_failed',
                                           component='manager_singleton.create',
                                           error=str(e)))
            
            if self.enable_fallback_creation:
                # Try to create a simplified instance
                try:
                    from .websocket_manager import WebSocketManager
                    return WebSocketManager()
                except Exception as fallback_error:
                    if self.detailed_logging:
                        logger.error(f"Fallback creation also failed: {fallback_error}")
            
            if self.fail_on_creation_error:
                raise
            else:
                return None
    
    def _validate_instance(self, instance) -> bool:
        """Validate instance"""
        if not self.enable_instance_validation:
            return True
        
        try:
            # Type validation
            if self.validate_instance_type:
                from .websocket_manager import WebSocketManager
                if not isinstance(instance, WebSocketManager):
                    return False
            
            # Method check
            if self.check_instance_methods:
                required_methods = ['connect_client', 'disconnect_client', 'subscribe_client', 'unsubscribe_client']
                for method in required_methods:
                    if not hasattr(instance, method) or not callable(getattr(instance, method)):
                        return False
            
            # Singleton contract validation
            if self.verify_singleton_contract and hasattr(instance, 'is_singleton'):
                if not instance.is_singleton():
                    return False
            
            return True
            
        except Exception as e:
            if self.detailed_logging:
                logger.error(f"Instance validation error: {e}")
            return False
    
    def set_instance(self, manager):
        """Set external instance"""
        if not self.allow_external_override and self._instance is not None:
            if self.log_external_setting:
                logger.warning(get_log_message('manager_singleton', 'instance_already_exists',
                                             component='manager_singleton.set'))
            return False
        
        # Instance validation
        if self.enable_instance_validation and not self._validate_instance(manager):
            if self.log_creation_errors:
                logger.error("External instance failed validation")
            return False
        
        if self.thread_safe:
            with self._lock:
                self._instance = manager
        else:
            self._instance = manager
        
        if self.log_external_setting:
            logger.info(get_log_message('manager_singleton', 'instance_set_externally',
                                       component='manager_singleton.set'))
        
        return True
    
    def reset_instance(self):
        """Reset instance"""
        if not self.enable_instance_reset:
            if self.detailed_logging:
                logger.warning("Instance reset is disabled in configuration")
            return False
        
        if self.thread_safe:
            with self._lock:
                self._instance = None
                self._access_count = 0
                self._creation_time = None
        else:
            self._instance = None
            self._access_count = 0
            self._creation_time = None
        
        if self.log_instance_status:
            logger.info(get_log_message('manager_singleton', 'instance_reset',
                                       component='manager_singleton.reset'))
        
        return True
    
    def get_instance_status(self) -> dict:
        """Get instance status information"""
        status = {
            "has_instance": self._instance is not None,
            "access_count": self._access_count if self.enable_usage_tracking else None,
            "creation_time": self._creation_time if self.enable_performance_metrics else None,
            "singleton_mode": self.enable_singleton_mode,
            "thread_safe": self.thread_safe
        }
        
        if self.log_instance_status:
            logger.info(get_log_message('manager_singleton', 'instance_status',
                                       component='manager_singleton.status',
                                       status=str(status)))
        
        return status

# Create singleton manager
_singleton_manager = ConfigurableWebSocketManagerSingleton()

def get_websocket_manager():
    """
    WebSocket manager getter function
    Ensures all parts of the application use the same instance (if singleton mode is enabled)
    """
    return _singleton_manager.get_instance()

def set_websocket_manager(manager):
    """
    WebSocket manager setter function
    Used by application startup to ensure consistency
    """
    return _singleton_manager.set_instance(manager)

def reset_websocket_manager():
    """
    WebSocket manager reset function
    Used for testing and development environments
    """
    return _singleton_manager.reset_instance()

def get_manager_status():
    """
    Get WebSocket manager singleton status
    Used for monitoring and debugging
    """
    return _singleton_manager.get_instance_status() 
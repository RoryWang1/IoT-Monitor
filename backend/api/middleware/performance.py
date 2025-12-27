"""
Configurable Performance Monitoring Middleware
Tracks API response times and performance metrics with configurable thresholds
"""

import time
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Setup unified path configuration
import sys
from pathlib import Path
config_path = Path(__file__).parent.parent.parent.parent / "config"
sys.path.insert(0, str(config_path))

from config.unified_config_manager import get_config, get_log_message

logger = logging.getLogger(__name__)

class ConfigurablePerformanceMiddleware(BaseHTTPMiddleware):
    """Configurable performance monitoring middleware"""
    
    def __init__(self, app):
        super().__init__(app)
        self.config_namespace = 'performance_middleware'
        
    def _get_thresholds(self) -> dict:
        """Get performance threshold configuration"""
        return {
            'slow_request_threshold': get_config(f'{self.config_namespace}.thresholds.slow_request_seconds', 1.0, f'{self.config_namespace}.thresholds'),
            'very_slow_threshold': get_config(f'{self.config_namespace}.thresholds.very_slow_seconds', 5.0, f'{self.config_namespace}.thresholds'),
            'critical_threshold': get_config(f'{self.config_namespace}.thresholds.critical_seconds', 10.0, f'{self.config_namespace}.thresholds')
        }
    
    def _get_logging_config(self) -> dict:
        """Get logging configuration"""
        return {
            'log_all_requests': get_config(f'{self.config_namespace}.logging.log_all_requests', False, f'{self.config_namespace}.logging'),
            'log_slow_requests': get_config(f'{self.config_namespace}.logging.log_slow_requests', True, f'{self.config_namespace}.logging'),
            'log_very_slow_requests': get_config(f'{self.config_namespace}.logging.log_very_slow_requests', True, f'{self.config_namespace}.logging'),
            'log_critical_requests': get_config(f'{self.config_namespace}.logging.log_critical_requests', True, f'{self.config_namespace}.logging'),
            'include_response_headers': get_config(f'{self.config_namespace}.logging.include_response_headers', True, f'{self.config_namespace}.logging')
        }
    
    def _get_features(self) -> dict:
        """Get feature switch configuration"""
        return {
            'enable_performance_headers': get_config(f'{self.config_namespace}.features.enable_performance_headers', True, f'{self.config_namespace}.features'),
            'enable_request_logging': get_config(f'{self.config_namespace}.features.enable_request_logging', True, f'{self.config_namespace}.features'),
            'enable_performance_analytics': get_config(f'{self.config_namespace}.features.enable_performance_analytics', False, f'{self.config_namespace}.features')
        }
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Get configuration
        thresholds = self._get_thresholds()
        logging_config = self._get_logging_config()
        features = self._get_features()
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Add performance headers
        if features['enable_performance_headers']:
            response.headers["X-Process-Time"] = str(process_time)
            if features['include_response_headers']:
                response.headers["X-Performance-Category"] = self._categorize_performance(process_time, thresholds)
        
        # Configurable performance logging
        if features['enable_request_logging']:
            self._log_request_performance(request, response, process_time, thresholds, logging_config)
        
        return response
    
    def _categorize_performance(self, process_time: float, thresholds: dict) -> str:
        """Categorize performance based on configurable thresholds"""
        if process_time >= thresholds['critical_threshold']:
            return "critical"
        elif process_time >= thresholds['very_slow_threshold']:
            return "very_slow"
        elif process_time >= thresholds['slow_request_threshold']:
            return "slow"
        else:
            return "normal"
    
    def _log_request_performance(self, request: Request, response: Response, 
                               process_time: float, thresholds: dict, logging_config: dict):
        """Configurable performance logging"""
        category = self._categorize_performance(process_time, thresholds)
        
        # Build log context
        log_context = {
            'method': request.method,
            'path': request.url.path,
            'status_code': response.status_code,
            'process_time': round(process_time, 3),
            'category': category
        }
        
        # Log different levels of requests based on performance category
        if category == "critical" and logging_config['log_critical_requests']:
            logger.error(get_log_message('performance_middleware', 'critical_request', 
                                       component='performance.middleware', **log_context))
        elif category == "very_slow" and logging_config['log_very_slow_requests']:
            logger.warning(get_log_message('performance_middleware', 'very_slow_request', 
                                         component='performance.middleware', **log_context))
        elif category == "slow" and logging_config['log_slow_requests']:
            logger.warning(get_log_message('performance_middleware', 'slow_request', 
                                         component='performance.middleware', **log_context))
        elif logging_config['log_all_requests']:
            logger.debug(get_log_message('performance_middleware', 'normal_request', 
                                       component='performance.middleware', **log_context))

# Alias for compatibility
PerformanceMiddleware = ConfigurablePerformanceMiddleware 
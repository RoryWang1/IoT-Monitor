#!/usr/bin/env python3
"""
API configuration file
"""

import os
from pathlib import Path
from typing import Dict, List
import sys

# Add project root path to Python path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


from config.unified_config_manager import UnifiedConfigManager, get_config, get_server_config

# Create config manager instance
config_manager = UnifiedConfigManager()

class APIConfig:
    """API configuration class"""
    
    def __init__(self):
        self.config_manager = config_manager
        
    # Server configuration
    
    @property
    def HOST(self) -> str:
        """API server host"""
        return get_config('server.api.host', '0.0.0.0', 'api.server')
    
    @property
    def PORT(self) -> int:
        """API server port"""
        return get_config('server.api.port', 8001, 'api.server')
    
    @property
    def DEBUG(self) -> bool:
        """Debug mode"""
        return get_config('server.api.debug', True, 'api.server')
    
    @property
    def RELOAD(self) -> bool:
        """Hot reload mode"""
        return get_config('server.api.reload', True, 'api.server')
    
    @property
    def LOG_LEVEL(self) -> str:
        """Log level"""
        return get_config('server.api.log_level', 'info', 'api.server')
    
    # 】CORS configuration 】】
    
    @property
    def CORS_ORIGINS(self) -> List[str]:
        """CORS allowed origins"""
        # Get frontend port from config
        from config.unified_config_manager import UnifiedConfigManager
        config_manager = UnifiedConfigManager()
        frontend_port = config_manager.get_frontend_port('api.cors')
        
        return get_config('server.cors.origins', [
            f"http://{config_manager.get_frontend_host('api.cors')}:{frontend_port}", 
            f"http://127.0.0.1:{frontend_port}",
            f"http://localhost:{frontend_port}"
        ], 'api.cors')
    
    # Path configuration
    
    @classmethod
    def get_project_root(cls) -> Path:
        """Get project root directory"""
        return Path(get_config('paths.project_root', 
                             str(Path(__file__).parent.parent.parent), 
                             'api.paths'))
    
    @classmethod
    def get_backend_path(cls) -> Path:
        """Get backend directory path"""
        return Path(get_config('paths.backend_directory', 
                             str(cls.get_project_root() / "backend"), 
                             'api.paths'))
    
    @classmethod
    def get_api_path(cls) -> Path:
        """Get API directory path"""
        return cls.get_backend_path() / "api"
    
    @classmethod
    def get_database_path(cls) -> Path:
        """Get database directory path"""
        return Path(get_config('paths.data_directory',
                             str(cls.get_project_root() / "database"),
                             'api.paths'))
    
    @classmethod
    def get_pcap_input_path(cls) -> Path:
        """Get PCAP input directory path"""
        return Path(get_config('paths.pcap_input',
                             str(cls.get_project_root() / "pcap_input"),
                             'api.paths'))
    
    @classmethod
    def get_log_directory(cls) -> Path:
        """Get log directory path"""
        return Path(get_config('paths.log_directory',
                             str(cls.get_project_root() / "log"),
                             'api.paths'))
    
    # Application configuration
    
    @property
    def APP_NAME(self) -> str:
        """Application name"""
        return get_config('server.api.name', 'IoT Device Monitor API', 'api.app')
    
    @property
    def APP_VERSION(self) -> str:
        """Application version"""
        return get_config('server.api.version', 'dev', 'api.app')
    
    @property
    def APP_DESCRIPTION(self) -> str:
        """Application description"""
        return get_config('server.api.description', 
                         'Database-driven IoT device monitoring and analysis API', 
                         'api.app')
    
    # Logging configuration
    
    @classmethod
    def get_log_file(cls) -> Path:
        """Get log file path"""
        return cls.get_log_directory() / "api.log"
    
    @property
    def LOG_FORMAT(self) -> str:
        """Log format"""
        return get_config('logging.format', 
                         '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                         'api.logging')
    
    @property
    def LOG_FILE_ENABLED(self) -> bool:
        """Enable file logging"""
        return get_config('logging.file_enabled', True, 'api.logging')
    
    @property
    def LOG_CONSOLE_ENABLED(self) -> bool:
        """Enable console logging"""
        return get_config('logging.console_enabled', True, 'api.logging')
    
    # Performance configuration
    
    @property
    def ENABLE_CACHING(self) -> bool:
        """Enable caching"""
        return get_config('performance.enable_caching', True, 'api.performance')
    
    @property
    def CACHE_TTL_SECONDS(self) -> int:
        """Cache TTL (seconds)"""
        return get_config('performance.cache_ttl_seconds', 300, 'api.performance')
    
    @property
    def ENABLE_COMPRESSION(self) -> bool:
        """Enable compression"""
        return get_config('performance.enable_compression', True, 'api.performance')
    
    @property
    def MAX_REQUEST_SIZE_MB(self) -> int:
        """Maximum request size (MB)"""
        return get_config('performance.max_request_size_mb', 50, 'api.performance')
    
    @property
    def RESPONSE_TIMEOUT_SECONDS(self) -> int:
        """Response timeout (seconds)"""
        return get_config('performance.response_timeout_seconds', 30, 'api.performance')
    
    # Security configuration
    
    @property
    def ENABLE_RATE_LIMITING(self) -> bool:
        """Enable rate limiting"""
        return get_config('security.enable_rate_limiting', True, 'api.security')
    
    @property
    def REQUESTS_PER_MINUTE(self) -> int:
        """Requests per minute limit"""
        return get_config('security.requests_per_minute', 100, 'api.security')
    
    @property
    def ENABLE_HTTPS(self) -> bool:
        """Enable HTTPS"""
        return get_config('security.enable_https', False, 'api.security')
    
    # Feature switches
    
    @property
    def ENABLE_REAL_TIME_UPDATES(self) -> bool:
        """Enable real-time updates"""
        return get_config('features.enable_real_time_updates', True, 'api.features')
    
    @property
    def ENABLE_EXPERIMENT_ISOLATION(self) -> bool:
        """Enable experiment isolation"""
        return get_config('features.enable_experiment_isolation', True, 'api.features')
    
    @property
    def ENABLE_TIMEZONE_SUPPORT(self) -> bool:
        """Enable timezone support"""
        return get_config('features.enable_timezone_support', True, 'api.features')
    
    # Convenience methods
    
    def get_full_config(self) -> Dict:
        """Get full API configuration"""
        return {
            'server': {
                'host': self.HOST,
                'port': self.PORT,
                'debug': self.DEBUG,
                'reload': self.RELOAD,
                'log_level': self.LOG_LEVEL
            },
            'app': {
                'name': self.APP_NAME,
                'version': self.APP_VERSION,
                'description': self.APP_DESCRIPTION
            },
            'cors': {
                'origins': self.CORS_ORIGINS
            },
            'logging': {
                'format': self.LOG_FORMAT,
                'file_enabled': self.LOG_FILE_ENABLED,
                'console_enabled': self.LOG_CONSOLE_ENABLED
            },
            'performance': {
                'enable_caching': self.ENABLE_CACHING,
                'cache_ttl_seconds': self.CACHE_TTL_SECONDS,
                'enable_compression': self.ENABLE_COMPRESSION
            },
            'features': {
                'enable_real_time_updates': self.ENABLE_REAL_TIME_UPDATES,
                'enable_experiment_isolation': self.ENABLE_EXPERIMENT_ISOLATION,
                'enable_timezone_support': self.ENABLE_TIMEZONE_SUPPORT
            }
        }
    
    def validate_config(self) -> Dict:
        """Validate configuration"""
        errors = []
        warnings = []
        
        # Validate port
        if not (1 <= self.PORT <= 65535):
            errors.append(f"Invalid port: {self.PORT}")
        
        # Validate paths
        try:
            pcap_path = self.get_pcap_input_path()
            if not pcap_path.exists():
                warnings.append(f"PCAP input directory does not exist: {pcap_path}")
        except Exception as e:
            errors.append(f"Error accessing PCAP input path: {e}")
        
        # Validate logging configuration
        if not self.LOG_FILE_ENABLED and not self.LOG_CONSOLE_ENABLED:
            warnings.append("Both file and console logging are disabled")
        
        return {
            'errors': errors,
            'warnings': warnings,
            'valid': len(errors) == 0
        }

# Export config instance
config = APIConfig()

# Backward-compatible convenience access function
def get_api_config() -> APIConfig:
    """Get API configuration instance"""
    return config

def get_config_dict() -> Dict:
    """Get configuration dictionary"""
    return config.get_full_config() 
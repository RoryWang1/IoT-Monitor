#!/usr/bin/env python3
"""
IoT device monitoring system
"""

import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime
import logging
import hashlib
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configure the use of tracking records
@dataclass
class ConfigUsageRecord:
    """Configuration usage record"""
    key: str
    component: str
    access_time: datetime
    access_count: int = 0

class ConfigFileHandler(FileSystemEventHandler):
    """Configuration file change listener"""
    
    def __init__(self, callback: Callable):
        self.callback = callback
        
    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('.json'):
            self.callback(event.src_path)

class UnifiedConfigManager:
    """Unified configuration manager"""
    
    _instance = None
    _lock = threading.Lock()
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        # Basic configuration
        self._initialized = True
        self._lock = threading.RLock()
        self._config_data = {}
        self._log_messages = {}
        self._usage_records = {}
        self._last_reload_time = None
        self._config_hash = None
        
        # Path configuration
        self.project_root = self._get_project_root()
        self.config_dir = self.project_root / "config"
        self.templates_dir = self.config_dir / "templates"
        
        # Environment detection (simplified)
        self.environment = os.getenv('IOT_ENV', os.getenv('ENVIRONMENT', 'development')).lower()
        
        # Logging settings
        self.logger = self._setup_logger()
        
        # File monitoring
        self._observer = None
        self._file_handlers = {}
        self._monitoring_started = False
        
        # Initialize configuration
        self._load_all_configurations()
        self._start_file_monitoring()
        
        # Record initialization
        self.logger.info(f"Unified configuration manager initialized for {self.environment} environment")
    
    def _get_project_root(self) -> Path:
        """Get project root directory"""
        current_file = Path(__file__).resolve()
        # config/unified_config_manager.py -> config -> project_root
        return current_file.parent.parent
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration that replaces environment files"""
        return {
            "environment": self.environment,
            "description": f"{self.environment.title()} environment configuration for IoT monitoring system",
            "server": {
                "api": {
                    "host": "127.0.0.1",
                    "port": 8002,
                    "debug": True if self.environment == "development" else False,
                    "reload": True if self.environment == "development" else False,
                    "log_level": "info",
                    "name": "IoT Device Monitor API",
                    "description": "IoT device monitoring and analysis API"
                },
                "frontend": {
                    "port": 3001,
                    "host": "localhost"
                },
                "cors": {
                    "origins": [
                                        "http://localhost:3001",
                "http://127.0.0.1:3001"
                    ],
                    "allow_credentials": True
                },
                "startup_timeout_seconds": 30,
                "shutdown_timeout_seconds": 10,
                "environment_type": self.environment
            },
            "database": {
                "connection": {
                    "host": "localhost",
                    "port": 5433,
                    "database": "iot_monitor",
                    "user": "postgres",
                    "password": "postgres"
                },
                "pool": {
                    "min_size": 3,
                    "max_size": 15,
                    "command_timeout": 60,
                    "acquire_timeout": 30,
                    "idle_timeout": 300
                },
                "server_settings": {
                    "jit": "off",
                    "application_name": "IoT_Device_Monitor",
                    "timezone": "UTC",
                    "statement_timeout": "30s"
                },
                "maintenance": {
                    "enable_auto_analyze": True,
                    "enable_auto_vacuum": False,
                    "analyze_threshold": 1000,
                    "vacuum_threshold": 5000,
                    "cleanup_enabled": True,
                    "cleanup_time": "02:00",
                    "cleanup_frequency": "daily",
                    "timezone": "UTC"
                },
                "performance": {
                    "enable_query_logging": True if self.environment == "development" else False,
                    "slow_query_threshold_ms": 1000,
                    "enable_connection_pooling": True,
                    "max_connections_per_host": 50,
                    "query_timeout_seconds": 30,
                    "enable_query_optimization": True
                },
                "health_check": {
                    "include_version": True,
                    "include_pool_stats": True,
                    "include_table_stats": True,
                    "table_stats_timeout": 5
                },
                "tables": {
                    "monitored": [
                        "devices",
                        "device_statistics", 
                        "device_traffic_history",
                        "device_connections",
                        "packet_flows",
                        "experiments",
                        "vendor_patterns",
                        "known_devices"
                    ]
                },
                "logging": {
                    "level": "INFO"
                },
                "retention": {
                    "packet_flows_days": 8,
                    "device_history_days": 8,
                    "experiment_data_days": 8,
                    "logs_days": 8
                },
                "optimization": {
                    "auto_vacuum": True,
                    "analyze_frequency": "weekly",
                    "index_maintenance": True,
                    "enable_auto_analyze": True,
                    "enable_auto_vacuum": False,
                    "analyze_threshold": 1000,
                    "vacuum_threshold": 5000
                },
                "query": {
                    "max_timeout_seconds": 30,
                    "connection_pool_size": 20,
                    "batch_processing_size": 100
                },
                "cleanup_schedule": {
                    "enabled": True,
                    "frequency": "daily",
                    "time": "02:00",
                    "timezone": "UTC"
                },
                "port": 5433,
                "host": "localhost",
                "data_directory": "database/data"
            },
            "paths": {
                "pcap_input": str(self.project_root / "pcap_input"),
                "log_directory": str(self.project_root / "log"),
                "data_directory": str(self.project_root / "database" / "data"),
                "config_directory": str(self.project_root / "config"),
                "frontend_directory": str(self.project_root / "frontend"),
                "backend_directory": str(self.project_root / "backend"),
                "project_root": str(self.project_root),
                "file_monitor_config": str(self.project_root / "config" / "file_monitor_config.json"),
                "logs": str(self.project_root / "log")
            },
            "file_monitoring": {
                "enabled": True,
                "auto_process_enabled": True,
                "supported_extensions": [
                    ".pcap",
                    ".pcapng", 
                    ".cap"
                ],
                "max_retries": 3,
                "retry_delay": 10,
                "processing_timeout": 300,
                "file_size_check_delay": 2,
                "monitor_recursive": True,
                "enable_duplicate_detection": True,
                "cleanup_processed_files": True,
                "auto_delete_after_processing": True,
                "delete_delay_seconds": 5,
                "keep_failed_files": True,
                "default_experiment_prefix": "auto_",
                "notification_enabled": False,
                "queue_processing": {
                    "max_queue_size": 1000,
                    "processing_timeout": 300,
                    "retry_attempts": 3
                },
                "schedule": {
                    "enabled": True,
                    "scan_times": [
                        "06:00",
                        "12:00", 
                        "18:00",
                        "23:10"
                    ],
                    "timezone": "local"
                },
                "processing": {
                    "auto_process_new_files": True,
                    "batch_size": 10,
                    "max_concurrent_files": 3
                },
                "file_types": {
                    "supported_extensions": [
                        ".pcap",
                        ".pcapng",
                        ".cap"
                    ],
                    "ignore_hidden_files": True,
                    "ignore_temp_files": True
                }
            },
            "device_monitoring": {
                "online_threshold_hours": 24,
                "offline_threshold_hours": 48,
                "broadcast_interval_seconds": 30,
                "status_check_interval_seconds": 1800,
                "max_device_age_days": 30
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file_enabled": True,
                "console_enabled": True,
                "rotation": {
                    "max_size_mb": 100,
                    "backup_count": 5,
                    "enabled": True
                },
                "console_level": "INFO",
                "file_level": "INFO"
            },
            "features": {
                "enable_real_time_updates": True,
                "enable_experiment_isolation": True,
                "enable_timezone_support": True,
                "enable_database": True,
                "enable_broadcast_service": True,
                "enable_file_monitoring": True,
                "enable_websocket": True
            },
            "data_retention": {
                "packet_flows_days": 8,
                "device_history_days": 8,
                "experiment_data_days": 8,
                "log_files_days": 8
            },
            "api_endpoints": {
                "network_topology": {
                    "defaults": {
                        "time_window": "48h",
                        "unknown_device_name": "Unknown Device",
                        "fallback_device_type": "unknown",
                        "unknown_vendor": "Unknown",
                        "fallback_mac_address": "00:00:00:00:00:00"
                    },
                    "query_limits": {
                        "max_nodes": 100,
                        "max_edges": 200,
                        "max_connections": 50,
                        "direct_mac_lookup_limit": 10
                    },
                    "features": {
                        "enable_mac_resolution": True,
                        "enable_direct_mac_lookup": True,
                        "enable_ip_filtering": True,
                        "enable_edge_optimization": True,
                        "enable_node_classification": True,
                        "enable_detailed_logging": True,
                        "enable_protocol_detection": True
                    },
                    "query_descriptions": {
                        "time_window_description": "Time window for network topology analysis",
                        "experiment_id_description": "Experiment ID for data isolation"
                    },
                    "ip_filtering": {
                        "exclude_self_connections": True,
                        "exclude_broadcast_ips": ["255.255.255.255", "0.0.0.0"],
                        "exclude_multicast_prefixes": ["224.", "239."]
                    },
                    "node_configuration": {
                        "main_device_size": 40,
                        "gateway_size": 35,
                        "regular_device_size": 25,
                        "external_device_size": 20
                    },
                    "node_colors": {
                        "main_device": "#3B82F6",
                        "gateway": "#10B981",
                        "device": "#6B7280",
                        "external": "#EF4444",
                        "unknown": "#9CA3AF"
                    },
                    "node_labels": {
                        "gateway_suffix_patterns": [".1", ".254"],
                        "gateway_label": "Gateway",
                        "device_label_prefix": "Device",
                        "external_label_prefix": "External"
                    },
                    "edge_configuration": {
                        "use_log_normalization": True,
                        "bidirectional_enhancement": True,
                        "min_weight": 1,
                        "max_weight": 8,
                        "min_strength": 0.1,
                        "max_strength": 1.0
                    },
                    "protocol_mapping": {
                        "http_ports": [80, 8080, 8000],
                        "https_ports": [443, 8443],
                        "dns_ports": [53],
                        "dhcp_ports": [67, 68],
                        "upnp_ports": [1900],
                        "ssh_ports": [22],
                        "ftp_ports": [21, 20],
                        "smtp_ports": [25, 587]
                    },
                    "protocol_names": {
                        "http_protocol": "HTTP",
                        "https_protocol": "HTTPS",
                        "dns_protocol": "DNS",
                        "dhcp_protocol": "DHCP",
                        "upnp_protocol": "UPnP",
                        "ssh_protocol": "SSH",
                        "ftp_protocol": "FTP",
                        "smtp_protocol": "SMTP",
                        "tcp_fallback": "TCP"
                    },
                    "error_messages": {
                        "device_not_found": "Device '{device_id}' not found",
                        "failed_retrieve_topology": "Failed to retrieve network topology"
                    }
                }
            }
        }
    
    def _setup_logger(self) -> logging.Logger:
        """Set logger"""
        logger = logging.getLogger('config.unified_manager')
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def _load_all_configurations(self):
        """Load all configurations"""
        with self._lock:
            # Load default configuration first
            self._config_data = self._get_default_config()
            
            # Load log message templates
            self._load_log_messages()
            
            # Load and apply user configuration (this will override defaults)
            self._load_and_apply_user_config()
            
            # Calculate configuration hash
            self._update_config_hash()
            
            self._last_reload_time = datetime.now()
            
            self.logger.info(f"Configuration reloaded for {self.environment} environment")
    
    def _load_log_messages(self):
        """Load log message templates"""
        log_file = self.templates_dir / "log_messages.json"
        
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    self._log_messages = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                self.logger.error(f"Failed to load log messages: {e}")
                self._log_messages = {}
        else:
            self.logger.warning(f"Log messages file not found: {log_file}")
            self._log_messages = {}
    
    def _load_and_apply_user_config(self):
        """Load and apply user configuration"""
        user_config_file = self.config_dir / "user_config.json"
        
        if not user_config_file.exists():
            self.logger.debug(f"User config file not found: {user_config_file}")
            return
        
        try:
            with open(user_config_file, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
            
            # Apply user configuration to system configuration
            self._apply_user_config_to_system(user_config)
            
            self.logger.info("User configuration loaded and applied")
            
        except (json.JSONDecodeError, IOError) as e:
            self.logger.error(f"Failed to load user config: {e}")
    
    def _apply_user_config_to_system(self, user_config: Dict[str, Any]):
        """Apply user configuration to system configuration"""
        if not user_config:
            return
        
        # Apply logging configuration
        if "logging" in user_config:
            self._apply_logging_config(user_config["logging"])
        
        # Apply file monitoring configuration  
        if "file_monitoring" in user_config:
            self._apply_file_monitoring_config(user_config["file_monitoring"])
        
        # Apply database maintenance configuration
        if "database_maintenance" in user_config:
            self._apply_database_maintenance_config(user_config["database_maintenance"])
        
        # Apply data retention configuration directly
        if "data_retention" in user_config:
            self._apply_data_retention_config(user_config["data_retention"])
        
        # Apply database storage configuration
        if "database_storage" in user_config:
            self._apply_database_storage_config(user_config["database_storage"])
        
        # Apply device status configuration
        if "device_status" in user_config:
            self._apply_device_status_config(user_config["device_status"])
        
        # Apply network topology configuration
        if "network_topology" in user_config:
            self._apply_network_topology_config(user_config["network_topology"])
        
        # Apply port analysis configuration
        if "port_analysis" in user_config:
            self._apply_port_analysis_config(user_config["port_analysis"])
        
        # Apply advanced port analysis configuration
        if "advanced_port_analysis" in user_config:
            self._apply_advanced_port_analysis_config(user_config["advanced_port_analysis"])
        
        # Apply performance tuning configuration
        if "performance_tuning" in user_config:
            self._apply_performance_config(user_config["performance_tuning"])
        
        # Apply alerts configuration
        if "alerts_and_monitoring" in user_config:
            self._apply_alerts_config(user_config["alerts_and_monitoring"])
        
        # Apply security configuration
        if "security_and_monitoring" in user_config:
            self._apply_security_config(user_config["security_and_monitoring"])
        
        # Apply UI preferences configuration
        if "ui_preferences" in user_config:
            self._apply_ui_preferences_config(user_config["ui_preferences"])
        
        # Apply system architecture configuration (ports and paths)
        if "system_architecture" in user_config:
            self._apply_system_architecture_config(user_config["system_architecture"])
        
        # Apply service management configuration
        if "service_management" in user_config:
            self._apply_service_management_config(user_config["service_management"])
        
        # Apply websocket management configuration
        if "websocket_management" in user_config:
            self._apply_websocket_management_config(user_config["websocket_management"])
        
        # Apply system monitoring configuration
        if "system_monitoring" in user_config:
            self._apply_system_monitoring_config(user_config["system_monitoring"])
    
    def _apply_logging_config(self, logging_config: Dict[str, Any]):
        """Apply logging configuration"""
        if "logging" not in self._config_data:
            self._config_data["logging"] = {}
        
        # Log-level configuration
        if "level" in logging_config:
            level_config = logging_config["level"]
            if "current" in level_config:
                current_level = level_config["current"]
                self._config_data["logging"]["level"] = current_level
                self._config_data["logging"]["console_level"] = current_level
                self._config_data["logging"]["file_level"] = current_level
                
                # Dynamic update log level
                self._update_runtime_logging_level(current_level)
        
        # Category log level configuration
        if "categories" in logging_config:
            categories = logging_config["categories"]
            
            # Map user-friendly category names to system paths
            category_mapping = {
                "api_endpoints": "api.logging.level",
                "database": "database.logging.level",
                "websocket": "websocket.logging.level",
                "file_monitor": "file_monitor.logging.level",
                "device_analysis": "device_analysis.logging.level"
            }
            
            for user_category, system_path in category_mapping.items():
                if user_category in categories:
                    level = categories[user_category]
                    self._set_nested_config(self._config_data, system_path, level)
        
        # Log rotation configuration
        if "rotation" in logging_config:
            rotation = logging_config["rotation"]
            if "rotation" not in self._config_data["logging"]:
                self._config_data["logging"]["rotation"] = {}
            
            self._config_data["logging"]["rotation"]["max_size_mb"] = rotation.get("max_size_mb", 100)
            self._config_data["logging"]["rotation"]["backup_count"] = rotation.get("backup_count", 5)
            self._config_data["logging"]["rotation"]["enabled"] = rotation.get("enabled", True)
    
    def _update_runtime_logging_level(self, level: str):
        """Update logging level for all active loggers"""
        try:
            import logging
            
            # Convert string level to logging constant
            log_level = getattr(logging, level.upper(), logging.INFO)
            
            # Update root logger
            logging.getLogger().setLevel(log_level)
            
            # Update all existing loggers
            for logger_name in logging.Logger.manager.loggerDict:
                logger = logging.getLogger(logger_name)
                if logger.handlers:  # Only update loggers that have handlers
                    logger.setLevel(log_level)
            
            self.logger.info(f"Updated runtime logging level to {level}")
            
        except Exception as e:
            self.logger.error(f"Failed to update runtime logging level: {e}")
    
    def _set_nested_config(self, config_dict: dict, path: str, value: Any):
        """Set nested configuration value"""
        keys = path.split('.')
        current = config_dict
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    def _apply_file_monitoring_config(self, file_monitoring_config: Dict[str, Any]):
        """Apply file monitoring configuration"""
        if "file_monitor" not in self._config_data:
            self._config_data["file_monitor"] = {}
        
        # Daily scan scheduling configuration
        if "schedule" in file_monitoring_config:
            scan_schedule = file_monitoring_config["schedule"]
            if "schedule" not in self._config_data["file_monitor"]:
                self._config_data["file_monitor"]["schedule"] = {}
            
            self._config_data["file_monitor"]["schedule"]["enabled"] = scan_schedule.get("enabled", True)
            self._config_data["file_monitor"]["schedule"]["scan_times"] = scan_schedule.get("scan_times", ["06:00", "12:00", "18:00", "23:59"])
            self._config_data["file_monitor"]["schedule"]["timezone"] = scan_schedule.get("timezone", "local")
        
        # Automatic processing configuration
        if "processing" in file_monitoring_config:
            auto_processing = file_monitoring_config["processing"]
            if "processing" not in self._config_data["file_monitor"]:
                self._config_data["file_monitor"]["processing"] = {}
            
            self._config_data["file_monitor"]["processing"]["auto_process_new_files"] = auto_processing.get("auto_process_new_files", True)
            self._config_data["file_monitor"]["processing"]["batch_size"] = auto_processing.get("batch_size", 10)
            self._config_data["file_monitor"]["processing"]["max_concurrent_files"] = auto_processing.get("max_concurrent_files", 3)
        
        # File type configuration
        if "file_types" in file_monitoring_config:
            file_types = file_monitoring_config["file_types"]
            if "files" not in self._config_data["file_monitor"]:
                self._config_data["file_monitor"]["files"] = {}
            
            self._config_data["file_monitor"]["files"]["supported_extensions"] = file_types.get("supported_extensions", [".pcap", ".pcapng", ".cap"])
            self._config_data["file_monitor"]["files"]["ignore_hidden_files"] = file_types.get("ignore_hidden_files", True)
            self._config_data["file_monitor"]["files"]["ignore_temp_files"] = file_types.get("ignore_temp_files", True)
        
        # Also store in file_monitoring for direct access
        if "file_monitoring" not in self._config_data:
            self._config_data["file_monitoring"] = {}
        self._config_data["file_monitoring"].update(file_monitoring_config)
    
    def _apply_network_topology_config(self, network_topology_config: Dict[str, Any]):
        """Apply network topology configuration"""
        if "api_endpoints" not in self._config_data:
            self._config_data["api_endpoints"] = {}
        if "network_topology" not in self._config_data["api_endpoints"]:
            self._config_data["api_endpoints"]["network_topology"] = {}
        
        # Default configuration
        if "defaults" in network_topology_config:
            defaults = network_topology_config["defaults"]
            if "defaults" not in self._config_data["api_endpoints"]["network_topology"]:
                self._config_data["api_endpoints"]["network_topology"]["defaults"] = {}
            
            self._config_data["api_endpoints"]["network_topology"]["defaults"]["time_window"] = defaults.get("time_window", "48h")
            self._config_data["api_endpoints"]["network_topology"]["defaults"]["unknown_device_name"] = "Unknown Device"
            self._config_data["api_endpoints"]["network_topology"]["defaults"]["fallback_device_type"] = "unknown"
            self._config_data["api_endpoints"]["network_topology"]["defaults"]["unknown_vendor"] = "Unknown"
            self._config_data["api_endpoints"]["network_topology"]["defaults"]["fallback_mac_address"] = "00:00:00:00:00:00"
        
        # Query limit configuration
        if "query_limits" in network_topology_config:
            query_limits = network_topology_config["query_limits"]
            if "query_limits" not in self._config_data["api_endpoints"]["network_topology"]:
                self._config_data["api_endpoints"]["network_topology"]["query_limits"] = {}
            
            self._config_data["api_endpoints"]["network_topology"]["query_limits"]["max_nodes"] = query_limits.get("max_nodes", 100)
            self._config_data["api_endpoints"]["network_topology"]["query_limits"]["max_edges"] = query_limits.get("max_edges", 200)
            self._config_data["api_endpoints"]["network_topology"]["query_limits"]["max_connections"] = query_limits.get("max_connections", 50)
            self._config_data["api_endpoints"]["network_topology"]["query_limits"]["direct_mac_lookup_limit"] = 10
        
        # Feature configuration
        if "features" in network_topology_config:
            features = network_topology_config["features"]
            if "features" not in self._config_data["api_endpoints"]["network_topology"]:
                self._config_data["api_endpoints"]["network_topology"]["features"] = {}
            
            self._config_data["api_endpoints"]["network_topology"]["features"]["enable_mac_resolution"] = features.get("enable_mac_resolution", True)
            self._config_data["api_endpoints"]["network_topology"]["features"]["enable_direct_mac_lookup"] = features.get("enable_direct_mac_lookup", True)
            self._config_data["api_endpoints"]["network_topology"]["features"]["enable_ip_filtering"] = features.get("enable_ip_filtering", True)
            self._config_data["api_endpoints"]["network_topology"]["features"]["enable_edge_optimization"] = features.get("enable_edge_optimization", True)
            self._config_data["api_endpoints"]["network_topology"]["features"]["enable_node_classification"] = True
            self._config_data["api_endpoints"]["network_topology"]["features"]["enable_detailed_logging"] = True
        
        # Analysis settings configuration
        if "analysis_settings" in network_topology_config:
            analysis_settings = network_topology_config["analysis_settings"]
            
            # Edge calculation configuration
            if "edge_calculation" in analysis_settings:
                edge_calculation = analysis_settings["edge_calculation"]
                if "edge_configuration" not in self._config_data["api_endpoints"]["network_topology"]:
                    self._config_data["api_endpoints"]["network_topology"]["edge_configuration"] = {}
                
                self._config_data["api_endpoints"]["network_topology"]["edge_configuration"]["use_log_normalization"] = edge_calculation.get("use_log_normalization", True)
                self._config_data["api_endpoints"]["network_topology"]["edge_configuration"]["bidirectional_enhancement"] = edge_calculation.get("bidirectional_enhancement", True)
                self._config_data["api_endpoints"]["network_topology"]["edge_configuration"]["min_weight"] = 1
                self._config_data["api_endpoints"]["network_topology"]["edge_configuration"]["max_weight"] = 8
                self._config_data["api_endpoints"]["network_topology"]["edge_configuration"]["min_strength"] = 0.1
                self._config_data["api_endpoints"]["network_topology"]["edge_configuration"]["max_strength"] = 1.0
        
        # Add default IP filtering, node configuration, color configuration, etc.
        if "ip_filtering" not in self._config_data["api_endpoints"]["network_topology"]:
            self._config_data["api_endpoints"]["network_topology"]["ip_filtering"] = {
                "exclude_self_connections": True,
                "exclude_broadcast_ips": ["255.255.255.255", "0.0.0.0"],
                "exclude_multicast_prefixes": ["224.", "239."]
            }
        
        if "node_configuration" not in self._config_data["api_endpoints"]["network_topology"]:
            self._config_data["api_endpoints"]["network_topology"]["node_configuration"] = {
                "main_device_size": 40,
                "gateway_size": 35,
                "regular_device_size": 25,
                "external_device_size": 20
            }
        
        if "node_colors" not in self._config_data["api_endpoints"]["network_topology"]:
            self._config_data["api_endpoints"]["network_topology"]["node_colors"] = {
                "main_device": "#3B82F6",
                "gateway": "#10B981",
                "device": "#6B7280",
                "external": "#EF4444",
                "unknown": "#9CA3AF"
            }
        
        if "error_messages" not in self._config_data["api_endpoints"]["network_topology"]:
            self._config_data["api_endpoints"]["network_topology"]["error_messages"] = {
                "device_not_found": "Device '{device_id}' not found",
                "failed_retrieve_topology": "Failed to retrieve network topology"
            }
    
    def _apply_port_analysis_config(self, port_analysis_config: Dict[str, Any]):
        """Apply port analysis configuration - complex dynamic scoring system"""
        if "device_port_analysis" not in self._config_data:
            self._config_data["device_port_analysis"] = {}
        
        # Dynamic scoring configuration
        if "dynamic_scoring" in port_analysis_config:
            dynamic_scoring = port_analysis_config["dynamic_scoring"]
            if "dynamic_scoring" not in self._config_data["device_port_analysis"]:
                self._config_data["device_port_analysis"]["dynamic_scoring"] = {}
            
            self._config_data["device_port_analysis"]["dynamic_scoring"]["enabled"] = dynamic_scoring.get("enabled", True)
        
        # Scoring algorithm configuration
        if "scoring_algorithm" in port_analysis_config:
            scoring_algorithm = port_analysis_config["scoring_algorithm"]
            
            # Port type weight configuration
            if "port_type_weights" in scoring_algorithm:
                port_type_weights = scoring_algorithm["port_type_weights"]
                if "dynamic_scoring" not in self._config_data["device_port_analysis"]:
                    self._config_data["device_port_analysis"]["dynamic_scoring"] = {}
                
                weight_config = {}
                weight_config["well_known"] = port_type_weights.get("well_known_ports", 1.2)
                weight_config["registered"] = port_type_weights.get("registered_ports", 1.0)
                weight_config["dynamic"] = port_type_weights.get("dynamic_ports", 0.8)
                weight_config["critical"] = port_type_weights.get("critical_system_ports", 1.5)
                
                self._config_data["device_port_analysis"]["dynamic_scoring"]["port_type_weights"] = weight_config
            
            # Metric weight configuration
            if "metric_weights" in scoring_algorithm:
                metric_weights = scoring_algorithm["metric_weights"]
                if "dynamic_scoring" not in self._config_data["device_port_analysis"]:
                    self._config_data["device_port_analysis"]["dynamic_scoring"] = {}
                
                weights_config = {
                    "packets": metric_weights.get("packet_count_weight", 0.4),
                    "bytes": metric_weights.get("byte_volume_weight", 0.4),
                    "sessions": metric_weights.get("session_count_weight", 0.2),
                    "percentile": metric_weights.get("percentile_ranking_weight", 0.0)
                }
                self._config_data["device_port_analysis"]["dynamic_scoring"]["metric_weights"] = weights_config
            
            # Bidirectional communication configuration
            if "bidirectional_communication" in scoring_algorithm:
                bidirectional_comm = scoring_algorithm["bidirectional_communication"]
                if "dynamic_scoring" not in self._config_data["device_port_analysis"]:
                    self._config_data["device_port_analysis"]["dynamic_scoring"] = {}
                
                self._config_data["device_port_analysis"]["dynamic_scoring"]["bidirectional_base_bonus"] = bidirectional_comm.get("bonus_weight", 0.15)
                self._config_data["device_port_analysis"]["dynamic_scoring"]["bidirectional_balance_bonus"] = bidirectional_comm.get("balance_bonus_weight", 0.1)
                self._config_data["device_port_analysis"]["dynamic_scoring"]["prioritize_bidirectional"] = bidirectional_comm.get("enable_bonus", True)
            
            # Packet size bonus configuration
            if "packet_size_bonuses" in scoring_algorithm:
                packet_size_bonuses = scoring_algorithm["packet_size_bonuses"]
                if "dynamic_scoring" not in self._config_data["device_port_analysis"]:
                    self._config_data["device_port_analysis"]["dynamic_scoring"] = {}
                
                self._config_data["device_port_analysis"]["dynamic_scoring"]["large_packet_threshold"] = packet_size_bonuses.get("large_packet_threshold_bytes", 1000)
                self._config_data["device_port_analysis"]["dynamic_scoring"]["medium_packet_threshold"] = packet_size_bonuses.get("medium_packet_threshold_bytes", 100)
                self._config_data["device_port_analysis"]["dynamic_scoring"]["size_consistency_bonus"] = {
                    "large_packets": packet_size_bonuses.get("large_packet_bonus", 0.1),
                    "medium_packets": packet_size_bonuses.get("medium_packet_bonus", 0.05)
                }
        
        # Threshold calculation configuration
        if "threshold_calculation" in port_analysis_config:
            threshold_calc = port_analysis_config["threshold_calculation"]
            if "dynamic_scoring" not in self._config_data["device_port_analysis"]:
                self._config_data["device_port_analysis"]["dynamic_scoring"] = {}
            
            self._config_data["device_port_analysis"]["dynamic_scoring"]["use_mathematical_expectation_thresholds"] = threshold_calc.get("use_mathematical_expectation", True)
            
            # Percentile factor configuration
            if "percentile_factors" in threshold_calc:
                percentile_factors = threshold_calc["percentile_factors"]
                threshold_config = {}
                threshold_config["very_active_factor"] = percentile_factors.get("very_active", 0.95)
                threshold_config["active_factor"] = percentile_factors.get("active", 0.9)
                threshold_config["moderate_factor"] = percentile_factors.get("moderate", 0.8)
                threshold_config["low_factor"] = percentile_factors.get("low_activity", 0.8)
                
                self._config_data["device_port_analysis"]["dynamic_scoring"]["threshold_calculation"] = threshold_config
            
            # Minimum threshold configuration
            if "minimum_thresholds" in threshold_calc:
                minimum_thresholds = threshold_calc["minimum_thresholds"]
                if "status_thresholds" not in self._config_data["device_port_analysis"]:
                    self._config_data["device_port_analysis"]["status_thresholds"] = {}
                
                self._config_data["device_port_analysis"]["status_thresholds"]["very_active_threshold"] = minimum_thresholds.get("very_active_min", 100)
                self._config_data["device_port_analysis"]["status_thresholds"]["active_threshold"] = minimum_thresholds.get("active_min", 50)
                self._config_data["device_port_analysis"]["status_thresholds"]["moderate_threshold"] = minimum_thresholds.get("moderate_min", 10)
                self._config_data["device_port_analysis"]["status_thresholds"]["inactive_threshold"] = minimum_thresholds.get("inactive_max", 0)
        
        # Analysis settings configuration
        if "analysis_settings" in port_analysis_config:
            analysis_settings = port_analysis_config["analysis_settings"]
            
            # Default configuration
            if "defaults" not in self._config_data["device_port_analysis"]:
                self._config_data["device_port_analysis"]["defaults"] = {}
            
            # Time window configuration
            if "time_windows" in analysis_settings:
                time_windows = analysis_settings["time_windows"]
                self._config_data["device_port_analysis"]["defaults"]["time_window"] = time_windows.get("default", "24h")
            
            # Query limit configuration
            if "query_limits" not in self._config_data["device_port_analysis"]:
                self._config_data["device_port_analysis"]["query_limits"] = {}
            
            self._config_data["device_port_analysis"]["query_limits"]["max_port_results"] = analysis_settings.get("max_ports_analyzed", 50)
            self._config_data["device_port_analysis"]["query_limits"]["min_packets_threshold"] = analysis_settings.get("min_packets_threshold", 1)
            
            # Response configuration
            if "response" not in self._config_data["device_port_analysis"]:
                self._config_data["device_port_analysis"]["response"] = {}
            
            self._config_data["device_port_analysis"]["response"]["include_scoring_details"] = analysis_settings.get("include_scoring_details", False)
            self._config_data["device_port_analysis"]["response"]["include_statistics"] = analysis_settings.get("include_statistics", False)
        
        # Activity timeline configuration
        if "activity_timeline" in port_analysis_config:
            activity_timeline = port_analysis_config["activity_timeline"]
            if "activity_timeline" not in self._config_data["device_port_analysis"]:
                self._config_data["device_port_analysis"]["activity_timeline"] = {}
            
            # Intensity calculation configuration
            if "intensity_calculation" in activity_timeline:
                intensity_calc = activity_timeline["intensity_calculation"]
                self._config_data["device_port_analysis"]["activity_timeline"]["intensity_calculation"] = {
                    "method": intensity_calc.get("method", "adaptive"),
                    "use_time_decay": intensity_calc.get("use_time_decay", True),
                    "mathematical_expectation": intensity_calc.get("mathematical_expectation", True)
                }
            
            # Time decay factor configuration
            if "time_decay_factors" in activity_timeline:
                time_decay_factors = activity_timeline["time_decay_factors"]
                self._config_data["device_port_analysis"]["activity_timeline"]["time_decay_factors"] = time_decay_factors
        
        # DBSCAN clustering configuration
        if "dbscan_clustering" in port_analysis_config:
            dbscan_clustering = port_analysis_config["dbscan_clustering"]
            if "dbscan_clustering" not in self._config_data["device_port_analysis"]:
                self._config_data["device_port_analysis"]["dbscan_clustering"] = {}
            
            # Adaptive parameter configuration
            if "adaptive_parameters" in dbscan_clustering:
                adaptive_params = dbscan_clustering["adaptive_parameters"]
                self._config_data["device_port_analysis"]["dbscan_clustering"]["adaptive_parameters"] = {
                    "enabled": adaptive_params.get("enabled", True),
                    "use_k_distance_graph": adaptive_params.get("use_k_distance_graph", True),
                    "polynomial_degree": adaptive_params.get("polynomial_degree", 15),
                    "noise_reduction_threshold": adaptive_params.get("noise_reduction_threshold", 0.8)
                }
            
            # Fallback parameter configuration
            if "fallback_parameters" in dbscan_clustering:
                fallback_params = dbscan_clustering["fallback_parameters"]
                self._config_data["device_port_analysis"]["dbscan_clustering"]["fallback_parameters"] = {
                    "default_eps": fallback_params.get("default_eps", 0.9),
                    "default_min_samples": fallback_params.get("default_min_samples", 4)
                }
        
        # Add other necessary configurations
        if "use_log_normalization" not in self._config_data["device_port_analysis"].get("dynamic_scoring", {}):
            if "dynamic_scoring" not in self._config_data["device_port_analysis"]:
                self._config_data["device_port_analysis"]["dynamic_scoring"] = {}
            self._config_data["device_port_analysis"]["dynamic_scoring"]["use_log_normalization"] = True
    
    def _apply_database_maintenance_config(self, db_maintenance_config: Dict[str, Any]):
        """Apply database maintenance configuration"""
        if "database" not in self._config_data:
            self._config_data["database"] = {}
        
        # Cleanup scheduling configuration
        if "cleanup_schedule" in db_maintenance_config:
            cleanup_schedule = db_maintenance_config["cleanup_schedule"]
            if "maintenance" not in self._config_data["database"]:
                self._config_data["database"]["maintenance"] = {}
            
            self._config_data["database"]["maintenance"]["cleanup_enabled"] = cleanup_schedule.get("enabled", True)
            self._config_data["database"]["maintenance"]["cleanup_time"] = cleanup_schedule.get("time", "02:00")
            self._config_data["database"]["maintenance"]["cleanup_frequency"] = cleanup_schedule.get("frequency", "daily")
            self._config_data["database"]["maintenance"]["timezone"] = cleanup_schedule.get("timezone", "UTC")
        
        # Data retention configuration
        if "data_retention" in db_maintenance_config:
            data_retention = db_maintenance_config["data_retention"]
            if "retention" not in self._config_data["database"]:
                self._config_data["database"]["retention"] = {}
            
            self._config_data["database"]["retention"]["packet_flows_days"] = data_retention.get("packet_flows_days", 30)
            self._config_data["database"]["retention"]["device_history_days"] = data_retention.get("device_history_days", 90)
            self._config_data["database"]["retention"]["experiment_data_days"] = data_retention.get("experiment_data_days", 180)
            self._config_data["database"]["retention"]["logs_days"] = data_retention.get("logs_days", 30)
        
        # Optimization configuration
        if "optimization" in db_maintenance_config:
            optimization = db_maintenance_config["optimization"]
            if "optimization" not in self._config_data["database"]:
                self._config_data["database"]["optimization"] = {}
            
            self._config_data["database"]["optimization"]["enable_auto_analyze"] = optimization.get("enable_auto_analyze", True)
            self._config_data["database"]["optimization"]["enable_auto_vacuum"] = optimization.get("enable_auto_vacuum", False)
            self._config_data["database"]["optimization"]["analyze_threshold"] = optimization.get("analyze_threshold", 1000)
            self._config_data["database"]["optimization"]["vacuum_threshold"] = optimization.get("vacuum_threshold", 5000)
    
    def _apply_data_retention_config(self, data_retention_config: Dict[str, Any]):
        """Apply data retention configuration directly"""
        if "database" not in self._config_data:
            self._config_data["database"] = {}
        if "retention" not in self._config_data["database"]:
            self._config_data["database"]["retention"] = {}
        
        # Apply to database retention
        self._config_data["database"]["retention"]["packet_flows_days"] = data_retention_config.get("packet_flows_days", 30)
        self._config_data["database"]["retention"]["device_history_days"] = data_retention_config.get("device_history_days", 90)
        self._config_data["database"]["retention"]["experiment_data_days"] = data_retention_config.get("experiment_data_days", 180)
        self._config_data["database"]["retention"]["logs_days"] = data_retention_config.get("log_files_days", 30)
        
        # Also store in data_retention for direct access
        if "data_retention" not in self._config_data:
            self._config_data["data_retention"] = {}
        self._config_data["data_retention"].update(data_retention_config)
    
    def _apply_database_storage_config(self, database_storage_config: Dict[str, Any]):
        """Apply database storage configuration"""
        # Initialize system_architecture if not exists
        if "system_architecture" not in self._config_data:
            self._config_data["system_architecture"] = {}
        if "paths" not in self._config_data["system_architecture"]:
            self._config_data["system_architecture"]["paths"] = {}
        if "database" not in self._config_data["system_architecture"]["paths"]:
            self._config_data["system_architecture"]["paths"]["database"] = {}
        
        # Apply data directory configuration
        data_directory = database_storage_config.get("data_directory", "database/data")
        self._config_data["system_architecture"]["paths"]["database"]["data_directory"] = data_directory
        
        # Also apply to database config for backward compatibility
        if "database" not in self._config_data:
            self._config_data["database"] = {}
        self._config_data["database"]["data_directory"] = data_directory
    
    def _apply_device_status_config(self, device_status_config: Dict[str, Any]):
        """Apply device status configuration - simple last activity time-based detection"""
        if "device_status" not in self._config_data:
            self._config_data["device_status"] = {}
        
        # Device online threshold configuration - based on last packet time
        if "online_detection" in device_status_config:
            online_detection = device_status_config["online_detection"]
            hours = online_detection.get("threshold_hours", 24)
            self._config_data["device_status"]["online_detection"] = {
                "threshold_hours": hours,
                "method": online_detection.get("method", "last_packet_time")
            }
            
            # Also map to device status service
            if "device_monitoring" not in self._config_data:
                self._config_data["device_monitoring"] = {}
            self._config_data["device_monitoring"]["online_threshold_hours"] = hours
        
        # Status check interval configuration
        if "status_updates" in device_status_config:
            status_updates = device_status_config["status_updates"]
            minutes = status_updates.get("check_interval_minutes", 30)
            self._config_data["device_status"]["status_updates"] = {
                "check_interval_minutes": minutes,
                "broadcast_updates": status_updates.get("broadcast_updates", True)
            }
            self._config_data["device_monitoring"]["status_check_interval_seconds"] = minutes * 60
    
    def _apply_advanced_port_analysis_config(self, advanced_port_analysis_config: Dict[str, Any]):
        """Apply advanced port analysis configuration"""
        if "advanced_port_analysis" not in self._config_data:
            self._config_data["advanced_port_analysis"] = {}
        
        # Query optimization configuration
        if "query_optimization" in advanced_port_analysis_config:
            query_optimization = advanced_port_analysis_config["query_optimization"]
            if "query_optimization" not in self._config_data["advanced_port_analysis"]:
                self._config_data["advanced_port_analysis"]["query_optimization"] = {}
            
            self._config_data["advanced_port_analysis"]["query_optimization"]["enable_query_caching"] = query_optimization.get("enable_query_caching", True)
            self._config_data["advanced_port_analysis"]["query_optimization"]["cache_timeout_seconds"] = query_optimization.get("cache_timeout_seconds", 300)
            self._config_data["advanced_port_analysis"]["query_optimization"]["max_query_timeout_seconds"] = query_optimization.get("max_query_timeout_seconds", 30)
        
        # Result formatting configuration
        if "result_formatting" in advanced_port_analysis_config:
            result_formatting = advanced_port_analysis_config["result_formatting"]
            if "result_formatting" not in self._config_data["advanced_port_analysis"]:
                self._config_data["advanced_port_analysis"]["result_formatting"] = {}
            
            self._config_data["advanced_port_analysis"]["result_formatting"]["decimal_precision"] = result_formatting.get("decimal_precision", 2)
            self._config_data["advanced_port_analysis"]["result_formatting"]["force_integer_conversion"] = result_formatting.get("force_integer_conversion", True)
            self._config_data["advanced_port_analysis"]["result_formatting"]["handle_null_values"] = result_formatting.get("handle_null_values", True)
    
    def _apply_service_management_config(self, service_management_config: Dict[str, Any]):
        """Apply service management configuration"""
        if "service_management" not in self._config_data:
            self._config_data["service_management"] = {}
        
        # Database service configuration
        if "database_service" in service_management_config:
            database_service = service_management_config["database_service"]
            if "database_service" not in self._config_data["service_management"]:
                self._config_data["service_management"]["database_service"] = {}
            
            self._config_data["service_management"]["database_service"]["enable_automatic_startup"] = database_service.get("enable_automatic_startup", True)
            self._config_data["service_management"]["database_service"]["startup_retry_attempts"] = database_service.get("startup_retry_attempts", 3)
            self._config_data["service_management"]["database_service"]["health_check_interval_seconds"] = database_service.get("health_check_interval_seconds", 30)
        
        # Broadcast service configuration
        if "broadcast_service" in service_management_config:
            broadcast_service = service_management_config["broadcast_service"]
            if "broadcast_service" not in self._config_data["service_management"]:
                self._config_data["service_management"]["broadcast_service"] = {}
            
            self._config_data["service_management"]["broadcast_service"]["enable_automatic_startup"] = broadcast_service.get("enable_automatic_startup", True)
            self._config_data["service_management"]["broadcast_service"]["broadcast_without_connections"] = broadcast_service.get("broadcast_without_connections", False)
            self._config_data["service_management"]["broadcast_service"]["suppress_connection_warnings"] = broadcast_service.get("suppress_connection_warnings", False)
        
        # File monitoring service configuration
        if "file_monitoring_service" in service_management_config:
            file_monitoring_service = service_management_config["file_monitoring_service"]
            if "file_monitoring_service" not in self._config_data["service_management"]:
                self._config_data["service_management"]["file_monitoring_service"] = {}
            
            self._config_data["service_management"]["file_monitoring_service"]["enable_automatic_startup"] = file_monitoring_service.get("enable_automatic_startup", True)
            self._config_data["service_management"]["file_monitoring_service"]["monitoring_interval_seconds"] = file_monitoring_service.get("monitoring_interval_seconds", 5)
            self._config_data["service_management"]["file_monitoring_service"]["max_concurrent_processing"] = file_monitoring_service.get("max_concurrent_processing", 3)
    
    def _apply_websocket_management_config(self, websocket_management_config: Dict[str, Any]):
        """Apply websocket management configuration"""
        if "websocket_management" not in self._config_data:
            self._config_data["websocket_management"] = {}
        
        # Connection management configuration
        if "connection_management" in websocket_management_config:
            connection_management = websocket_management_config["connection_management"]
            if "connection_management" not in self._config_data["websocket_management"]:
                self._config_data["websocket_management"]["connection_management"] = {}
            
            self._config_data["websocket_management"]["connection_management"]["enable_connection_tracking"] = connection_management.get("enable_connection_tracking", True)
            self._config_data["websocket_management"]["connection_management"]["max_connections_per_ip"] = connection_management.get("max_connections_per_ip", 10)
            self._config_data["websocket_management"]["connection_management"]["connection_timeout_minutes"] = connection_management.get("connection_timeout_minutes", 30)
            self._config_data["websocket_management"]["connection_management"]["enable_heartbeat_monitoring"] = connection_management.get("enable_heartbeat_monitoring", True)
        
        # Message handling configuration
        if "message_handling" in websocket_management_config:
            message_handling = websocket_management_config["message_handling"]
            if "message_handling" not in self._config_data["websocket_management"]:
                self._config_data["websocket_management"]["message_handling"] = {}
            
            self._config_data["websocket_management"]["message_handling"]["enable_message_validation"] = message_handling.get("enable_message_validation", True)
            self._config_data["websocket_management"]["message_handling"]["max_message_size_kb"] = message_handling.get("max_message_size_kb", 1024)
            self._config_data["websocket_management"]["message_handling"]["enable_compression"] = message_handling.get("enable_compression", False)
    
    def _apply_system_monitoring_config(self, system_monitoring_config: Dict[str, Any]):
        """Apply system monitoring configuration"""
        if "system_monitoring" not in self._config_data:
            self._config_data["system_monitoring"] = {}
        
        # Performance monitoring configuration
        if "performance_monitoring" in system_monitoring_config:
            performance_monitoring = system_monitoring_config["performance_monitoring"]
            if "performance_monitoring" not in self._config_data["system_monitoring"]:
                self._config_data["system_monitoring"]["performance_monitoring"] = {}
            
            self._config_data["system_monitoring"]["performance_monitoring"]["enable_performance_tracking"] = performance_monitoring.get("enable_performance_tracking", True)
            self._config_data["system_monitoring"]["performance_monitoring"]["slow_query_threshold_ms"] = performance_monitoring.get("slow_query_threshold_ms", 500)
            self._config_data["system_monitoring"]["performance_monitoring"]["memory_usage_threshold_percent"] = performance_monitoring.get("memory_usage_threshold_percent", 80)
        
        # Error handling configuration
        if "error_handling" in system_monitoring_config:
            error_handling = system_monitoring_config["error_handling"]
            if "error_handling" not in self._config_data["system_monitoring"]:
                self._config_data["system_monitoring"]["error_handling"] = {}
            
            self._config_data["system_monitoring"]["error_handling"]["enable_error_tracking"] = error_handling.get("enable_error_tracking", True)
            self._config_data["system_monitoring"]["error_handling"]["max_error_rate_percent"] = error_handling.get("max_error_rate_percent", 5)
            self._config_data["system_monitoring"]["error_handling"]["error_notification_threshold"] = error_handling.get("error_notification_threshold", 10)
    
    def _apply_performance_config(self, performance_config: Dict[str, Any]):
        """Apply performance configuration"""
        # Caching configuration
        if "caching" in performance_config:
            caching = performance_config["caching"]
            if "caching" not in self._config_data:
                self._config_data["caching"] = {}
            
            self._config_data["caching"]["device_resolution_cache_minutes"] = caching.get("device_resolution_cache_minutes", 60)
            self._config_data["caching"]["timezone_cache_minutes"] = caching.get("timezone_cache_minutes", 30)
            self._config_data["caching"]["config_cache_minutes"] = caching.get("config_cache_minutes", 15)
        
        # Query optimization configuration
        if "query_optimization" in performance_config:
            query_optimization = performance_config["query_optimization"]
            if "database" not in self._config_data:
                self._config_data["database"] = {}
            if "query" not in self._config_data["database"]:
                self._config_data["database"]["query"] = {}
            
            self._config_data["database"]["query"]["max_timeout_seconds"] = query_optimization.get("max_query_timeout_seconds", 30)
            self._config_data["database"]["query"]["connection_pool_size"] = query_optimization.get("connection_pool_size", 20)
            self._config_data["database"]["query"]["batch_processing_size"] = query_optimization.get("batch_processing_size", 100)
        
        # WebSocket broadcasting configuration
        if "websocket_broadcasting" in performance_config:
            websocket_broadcasting = performance_config["websocket_broadcasting"]
            if "device_monitoring" not in self._config_data:
                self._config_data["device_monitoring"] = {}
            
            self._config_data["device_monitoring"]["broadcast_interval_seconds"] = websocket_broadcasting.get("broadcast_interval_seconds", 30)
            
            if "websocket" not in self._config_data:
                self._config_data["websocket"] = {}
            if "broadcasting" not in self._config_data["websocket"]:
                self._config_data["websocket"]["broadcasting"] = {}
            
            self._config_data["websocket"]["broadcasting"]["max_concurrent_broadcasts"] = websocket_broadcasting.get("max_concurrent_broadcasts", 5)
            self._config_data["websocket"]["broadcasting"]["debounce_interval_seconds"] = websocket_broadcasting.get("debounce_interval_seconds", 2)
    
    def _apply_alerts_config(self, alerts_config: Dict[str, Any]):
        """Apply alerts configuration"""
        if "alerts" not in self._config_data:
            self._config_data["alerts"] = {}
        
        # Notification configuration
        if "notifications" in alerts_config:
            notifications = alerts_config["notifications"]
            self._config_data["alerts"]["enabled"] = notifications.get("enabled", True)
            self._config_data["alerts"]["notification_types"] = notifications.get("types", ["console", "log"])
        
        # Threshold configuration
        if "thresholds" in alerts_config:
            thresholds = alerts_config["thresholds"]
            self._config_data["alerts"]["device_offline_hours"] = thresholds.get("device_offline_hours", 6)
            self._config_data["alerts"]["high_traffic_threshold_gb"] = thresholds.get("high_traffic_threshold_gb", 5)
            self._config_data["alerts"]["error_rate_threshold"] = thresholds.get("error_rate_threshold", 0.1)
            self._config_data["alerts"]["port_activity_threshold"] = thresholds.get("port_activity_threshold", 100)
    
    def _apply_security_config(self, security_config: Dict[str, Any]):
        """Apply security configuration"""
        # Connection limit configuration
        if "connection_limits" in security_config:
            connection_limits = security_config["connection_limits"]
            if "websocket" not in self._config_data:
                self._config_data["websocket"] = {}
            if "limits" not in self._config_data["websocket"]:
                self._config_data["websocket"]["limits"] = {}
            
            self._config_data["websocket"]["limits"]["max_connections"] = connection_limits.get("max_websocket_connections", 100)
            self._config_data["websocket"]["limits"]["connection_timeout_minutes"] = connection_limits.get("connection_timeout_minutes", 30)
            self._config_data["websocket"]["limits"]["max_message_size_kb"] = connection_limits.get("max_message_size_kb", 1024)
        
        # Monitoring configuration
        if "monitoring" in security_config:
            monitoring = security_config["monitoring"]
            if "security_monitoring" not in self._config_data:
                self._config_data["security_monitoring"] = {}
            
            self._config_data["security_monitoring"]["failed_requests_threshold"] = monitoring.get("failed_requests_threshold", 10)
            self._config_data["security_monitoring"]["suspicious_activity_detection"] = monitoring.get("suspicious_activity_detection", True)
            self._config_data["security_monitoring"]["rate_limiting"] = monitoring.get("rate_limiting", True)
    
    def _apply_ui_preferences_config(self, ui_preferences_config: Dict[str, Any]):
        """Apply UI preferences configuration"""
        if "ui" not in self._config_data:
            self._config_data["ui"] = {}
        
        # Refresh interval configuration
        if "refresh_intervals" in ui_preferences_config:
            refresh_intervals = ui_preferences_config["refresh_intervals"]
            if "refresh" not in self._config_data["ui"]:
                self._config_data["ui"]["refresh"] = {}
            
            self._config_data["ui"]["refresh"]["device_overview_seconds"] = refresh_intervals.get("device_overview_seconds", 30)
            self._config_data["ui"]["refresh"]["port_analysis_seconds"] = refresh_intervals.get("port_analysis_seconds", 60)
            self._config_data["ui"]["refresh"]["traffic_trend_seconds"] = refresh_intervals.get("traffic_trend_seconds", 120)
            self._config_data["ui"]["refresh"]["system_status_seconds"] = refresh_intervals.get("system_status_seconds", 10)
        
        # Display configuration
        if "display_options" in ui_preferences_config:
            display_options = ui_preferences_config["display_options"]
            if "display" not in self._config_data["ui"]:
                self._config_data["ui"]["display"] = {}
            
            self._config_data["ui"]["display"]["show_inactive_devices"] = display_options.get("show_inactive_devices", True)
            self._config_data["ui"]["display"]["default_time_window"] = display_options.get("default_time_window", "48h")
            self._config_data["ui"]["display"]["max_items_per_page"] = display_options.get("max_items_per_page", 50)
            self._config_data["ui"]["display"]["chart_animation"] = display_options.get("chart_animation", True)
            self._config_data["ui"]["display"]["auto_refresh"] = display_options.get("auto_refresh", True)
        
        # Time window default configuration
        if "time_window_defaults" in ui_preferences_config:
            time_window_defaults = ui_preferences_config["time_window_defaults"]
            if "time_window_defaults" not in self._config_data["ui"]:
                self._config_data["ui"]["time_window_defaults"] = {}
            
            self._config_data["ui"]["time_window_defaults"]["device_detail"] = time_window_defaults.get("device_detail", "48h")
            self._config_data["ui"]["time_window_defaults"]["network_topology"] = time_window_defaults.get("network_topology", "48h")
            self._config_data["ui"]["time_window_defaults"]["port_analysis"] = time_window_defaults.get("port_analysis", "48h")
            self._config_data["ui"]["time_window_defaults"]["protocol_distribution"] = time_window_defaults.get("protocol_distribution", "48h")
            self._config_data["ui"]["time_window_defaults"]["activity_timeline"] = time_window_defaults.get("activity_timeline", "48h")
            self._config_data["ui"]["time_window_defaults"]["traffic_trend"] = time_window_defaults.get("traffic_trend", "48h")
    
    def _apply_system_architecture_config(self, system_architecture_config: Dict[str, Any]):
        """Apply system architecture configuration (ports and paths)"""
        if not system_architecture_config:
            return
        
        # Apply ports configuration
        if "ports" in system_architecture_config:
            ports_config = system_architecture_config["ports"]
            
            # Ensure server config exists
            if "server" not in self._config_data:
                self._config_data["server"] = {}
            
            # Frontend port
            if "frontend" in ports_config:
                frontend_port = ports_config["frontend"]["port"]
                if "frontend" not in self._config_data["server"]:
                    self._config_data["server"]["frontend"] = {}
                self._config_data["server"]["frontend"]["port"] = frontend_port
                
                # Update CORS origins with new port
                self._update_cors_origins_with_port(frontend_port)
            
            # Backend port
            if "backend" in ports_config:
                backend_port = ports_config["backend"]["port"]
                if "api" not in self._config_data["server"]:
                    self._config_data["server"]["api"] = {}
                self._config_data["server"]["api"]["port"] = backend_port
            
            # Database port
            if "database" in ports_config:
                database_port = ports_config["database"]["port"]
                if "database" not in self._config_data:
                    self._config_data["database"] = {}
                self._config_data["database"]["port"] = database_port
        
        # Apply hosts configuration
        if "hosts" in system_architecture_config:
            hosts_config = system_architecture_config["hosts"]
            
            # Ensure server config exists
            if "server" not in self._config_data:
                self._config_data["server"] = {}
            
            # API host
            if "api" in hosts_config:
                api_host = hosts_config["api"]["host"]
                if "api" not in self._config_data["server"]:
                    self._config_data["server"]["api"] = {}
                self._config_data["server"]["api"]["host"] = api_host
            
            # Frontend host  
            if "frontend" in hosts_config:
                frontend_host = hosts_config["frontend"]["host"]
                if "frontend" not in self._config_data["server"]:
                    self._config_data["server"]["frontend"] = {}
                self._config_data["server"]["frontend"]["host"] = frontend_host
                
                # Update CORS origins with new host and port
                frontend_port = self._config_data.get("server", {}).get("frontend", {}).get("port", 3001)
                self._update_cors_origins_with_host_and_port(frontend_host, frontend_port)
            
            # Database host
            if "database" in hosts_config:
                database_host = hosts_config["database"]["host"]
                if "database" not in self._config_data:
                    self._config_data["database"] = {}
                self._config_data["database"]["host"] = database_host
        
        # Apply paths configuration
        if "paths" in system_architecture_config:
            paths_config = system_architecture_config["paths"]
            
            # Ensure paths config exists
            if "paths" not in self._config_data:
                self._config_data["paths"] = {}
            
            # Database data directory
            if "database" in paths_config:
                db_data_dir = paths_config["database"]["data_directory"]
                if "database" not in self._config_data:
                    self._config_data["database"] = {}
                self._config_data["database"]["data_directory"] = db_data_dir
            
            # Logs directory
            if "logs" in paths_config:
                logs_dir = paths_config["logs"]["directory"]
                self._config_data["paths"]["logs"] = logs_dir
            
            # PCAP input directory
            if "pcap_input" in paths_config:
                pcap_dir = paths_config["pcap_input"]["directory"]
                self._config_data["paths"]["pcap_input"] = pcap_dir
    
    def _update_cors_origins_with_port(self, frontend_port: int):
        """Update CORS origins with new frontend port"""
        # Get current frontend host
        frontend_host = self._config_data.get("server", {}).get("frontend", {}).get("host", "localhost")
        self._update_cors_origins_with_host_and_port(frontend_host, frontend_port)
    
    def _update_cors_origins_with_host_and_port(self, frontend_host: str, frontend_port: int):
        """Update CORS origins with new frontend host and port"""
        if "server" not in self._config_data:
            self._config_data["server"] = {}
        if "cors" not in self._config_data["server"]:
            self._config_data["server"]["cors"] = {}
        
        # Get API host for additional CORS origins
        api_host = self._config_data.get("server", {}).get("api", {}).get("host", "127.0.0.1")
        
        cors_origins = [
            f"http://{frontend_host}:{frontend_port}"
        ]
        
        # Add API host variant if different from frontend host
        if api_host != frontend_host:
            cors_origins.append(f"http://{api_host}:{frontend_port}")
        
        # Add localhost variant if host is not localhost
        if frontend_host != "localhost":
            cors_origins.append(f"http://localhost:{frontend_port}")
            
        # Add 127.0.0.1 variant if not already included
        if api_host != "127.0.0.1" and frontend_host != "127.0.0.1":
            cors_origins.append(f"http://127.0.0.1:{frontend_port}")
            
        self._config_data["server"]["cors"]["origins"] = cors_origins
    
    def _update_config_hash(self):
        """Update configuration hash"""
        config_str = json.dumps(self._config_data, sort_keys=True)
        self._config_hash = hashlib.md5(config_str.encode()).hexdigest()
    
    def _start_file_monitoring(self):
        """Start file monitoring"""
        with self._lock:
            # Use class-level monitoring flag to prevent multiple observers across instances
            if hasattr(UnifiedConfigManager, '_global_monitoring_started') and UnifiedConfigManager._global_monitoring_started:
                self.logger.debug("Configuration monitoring already started globally, skipping...")
                return
            
            if self._monitoring_started or self._observer is not None:
                self.logger.debug("Configuration monitoring already started for this instance, skipping...")
                return
            
            try:
                # Clean up any existing observer before creating a new one
                if hasattr(self, '_observer') and self._observer is not None:
                    try:
                        self._observer.stop()
                        self._observer.join()
                    except:
                        pass
                
                self._observer = Observer()
                
                # Use a single handler for all directories to avoid conflicts
                handler = ConfigFileHandler(self._on_config_file_changed)
                
                # Monitor environment configuration directory
                # This directory is no longer used for default configs, but kept for user config
                if self.config_dir.exists():
                    try:
                        self._observer.schedule(handler, str(self.config_dir), recursive=False)
                    except RuntimeError as e:
                        if "already scheduled" in str(e):
                            self.logger.debug(f"Config directory already being monitored: {self.config_dir}")
                        else:
                            raise
                    
                # Monitor template directory  
                if self.templates_dir.exists():
                    try:
                        self._observer.schedule(handler, str(self.templates_dir), recursive=False)
                    except RuntimeError as e:
                        if "already scheduled" in str(e):
                            self.logger.debug(f"Template directory already being monitored: {self.templates_dir}")
                        else:
                            raise
                
                # Monitor user configuration file in config directory
                if self.config_dir.exists():
                    try:
                        self._observer.schedule(handler, str(self.config_dir), recursive=False)
                    except RuntimeError as e:
                        if "already scheduled" in str(e):
                            self.logger.debug(f"Config directory already being monitored: {self.config_dir}")
                        else:
                            raise
                
                self._observer.start()
                self._monitoring_started = True
                UnifiedConfigManager._global_monitoring_started = True
                self.logger.info("Configuration file monitoring started")
                
            except Exception as e:
                # If the observer fails to start, clear the reference to try again
                if "already scheduled" in str(e):
                    self.logger.debug("Configuration monitoring already active, marking as started...")
                    self._monitoring_started = True  # Mark as started to prevent retries
                    UnifiedConfigManager._global_monitoring_started = True
                    
                    # Clean up the observer that failed to start
                    if self._observer:
                        try:
                            self._observer.stop()
                            self._observer.join()
                        except:
                            pass
                        self._observer = None
                    return
                else:
                    self.logger.error(f"Failed to start configuration monitoring: {e}")
                    self._observer = None
                    self._monitoring_started = False
                    # Reset global flag to allow retry
                    UnifiedConfigManager._global_monitoring_started = False
    
    def _on_config_file_changed(self, file_path: str):
        """Configuration file change processing"""
        # Prevent frequent reloading
        time.sleep(0.1)
        
        self.logger.info(f"Configuration file changed: {file_path}")
        
        # Check if it's a user config file change
        if file_path.endswith('user_config.json'):
            # For user config changes, reload all configurations to apply changes
            self._load_all_configurations()
            
            # Save the updated system configuration
            self._save_system_config()
        else:
            # Reload all configurations for other file changes
            self._load_all_configurations()
    
    def _save_system_config(self):
        """Save updated system configuration to environment file"""
        try:
            # This method is no longer relevant as environment files are removed
            # Keeping it for now, but it will not save to a file.
            self.logger.warning("Attempted to save system config, but environment files are removed.")
            # env_file = self.environments_dir / f"{self.environment}.json"
            # with open(env_file, 'w', encoding='utf-8') as f:
            #     json.dump(self._config_data, f, indent=2, ensure_ascii=False)
            # self.logger.info(f"System configuration saved: {env_file}")
        except Exception as e:
            self.logger.error(f"Failed to save system configuration: {e}")
    
    # Configuration access interface
    
    def get(self, key: str, default: Any = None, component: str = "unknown") -> Any:
        """Get configuration value - support dot notation access"""
        with self._lock:
            # Record usage
            self._record_usage(key, component)
            
            # Parse dot notation path
            keys = key.split('.')
            value = self._config_data
            
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            
            return value
    
    def get_server_config(self, component: str = "api") -> Dict[str, Any]:
        """Get server configuration"""
        return self.get(f'server.{component}', {}, f"server.{component}")
    
    def get_database_config(self, component: str = "database") -> Dict[str, Any]:
        """Get database configuration"""
        return self.get('database', {}, component)
    
    def get_path(self, key: str, component: str = "paths") -> str:
        """Get path configuration"""
        return self.get(f'paths.{key}', "", component)
    
    def get_frontend_port(self, component: str = "frontend") -> int:
        """Get frontend port configuration"""
        return self.get('server.frontend.port', 3001, component)
    
    def get_backend_port(self, component: str = "backend") -> int:
        """Get backend port configuration"""
        return self.get('server.api.port', 8001, component)
    
    def get_database_port(self, component: str = "database") -> int:
        """Get database port configuration"""
        return self.get('database.port', 5433, component)
    
    def get_database_data_directory(self, component: str = "database") -> str:
        """Get database data directory configuration"""
        return self.get('database.data_directory', 'database/data', component)
    
    def get_logs_directory(self, component: str = "logs") -> str:
        """Get logs directory configuration"""
        return self.get('paths.logs', 'log', component)
    
    def get_pcap_input_directory(self, component: str = "pcap") -> str:
        """Get PCAP input directory configuration"""
        return self.get('paths.pcap_input', 'pcap_input', component)
    
    def get_api_host(self, component: str = "api") -> str:
        """Get API host configuration"""
        return self.get('server.api.host', '127.0.0.1', component)
    
    def get_frontend_host(self, component: str = "frontend") -> str:
        """Get frontend host configuration"""
        return self.get('server.frontend.host', 'localhost', component)
    
    def get_database_host(self, component: str = "database") -> str:
        """Get database host configuration"""
        return self.get('database.host', 'localhost', component)
    
    def get_feature_flag(self, feature: str, component: str = "features") -> bool:
        """Get feature switch"""
        return self.get(f'features.{feature}', False, component)
    
    # Log message interface
    
    def get_log_message(self, category: str, message_key: str, 
                       style: str = None, component: str = "logging", **kwargs) -> str:
        """Get formatted log message"""
        with self._lock:
            # Record usage
            self._record_usage(f"log.{category}.{message_key}", component)
            
            # Get message template
            message_template = None
            if category in self._log_messages:
                if message_key in self._log_messages[category]:
                    message_data = self._log_messages[category][message_key]
                    # Support two formats: simplified format (direct string) and complex format (style dictionary)
                    if isinstance(message_data, str):
                        # Simplified format: directly use string
                        message_template = message_data
                    elif isinstance(message_data, dict):
                        # Complex format: select based on style
                        if style is None:
                            logging_config = self.get('logging', {}, component)
                            if logging_config.get('include_emoji', True):
                                style = 'emoji'
                            elif logging_config.get('include_chinese', True):
                                style = 'plain'
                            else:
                                style = 'english'
                        message_template = message_data.get(style)
                    else:
                        # Process other data types
                        message_template = str(message_data)
            
            if message_template is None:
                return f"[Missing log message: {category}.{message_key}]"
            
            # Format message
            try:
                return message_template.format(**kwargs)
            except KeyError as e:
                return f"[Log message format error: {e}] {message_template}"
            except Exception as e:
                return f"[Log message processing error: {e}] {message_template}"
    
    # Useful methods
    
    def get_cors_origins(self, component: str = "cors") -> List[str]:
        """Get CORS configuration"""
        return self.get('server.cors.origins', [], component)
    
    def get_monitoring_config(self, component: str = "monitoring") -> Dict[str, Any]:
        """Get monitoring configuration"""
        return {
            'device_monitoring': self.get('device_monitoring', {}, component),
            'file_monitoring': self.get('file_monitoring', {}, component),
            'websocket': self.get('websocket', {}, component)
        }
    
    def is_debug_mode(self, component: str = "debug") -> bool:
        """Is debug mode"""
        return self.get('server.api.debug', False, component)
    
    def get_log_level(self, component: str = "logging") -> str:
        """Get log level"""
        # First try to get from user config
        user_level = self.get('logging.level.current', None, component)
        if user_level:
            return user_level.upper()
        
        # Fallback to system config
        return self.get('logging.level', 'INFO', component).upper()
    
    def get_config(self) -> Dict[str, Any]:
        """Get complete configuration data"""
        with self._lock:
            return self._config_data.copy()
    
    def get_log_templates(self) -> Dict[str, Any]:
        """Get log message templates"""
        with self._lock:
            return self._log_messages.copy()
    
    #  Usage statistics
    
    def _record_usage(self, key: str, component: str):
        """Record configuration usage"""
        usage_key = f"{component}:{key}"
        
        if usage_key not in self._usage_records:
            self._usage_records[usage_key] = ConfigUsageRecord(
                key=key,
                component=component,
                access_time=datetime.now()
            )
        
        record = self._usage_records[usage_key]
        record.access_count += 1
        record.access_time = datetime.now()
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        with self._lock:
            # Calculate component usage statistics
            component_usage = {}
            for record in self._usage_records.values():
                if record.component not in component_usage:
                    component_usage[record.component] = 0
                component_usage[record.component] += record.access_count
            
            stats = {
                'total_accesses': sum(r.access_count for r in self._usage_records.values()),
                'unique_keys': len(self._usage_records),
                'components': len(set(r.component for r in self._usage_records.values())),
                'component_usage': component_usage,
                'most_used_keys': sorted(
                    [(r.key, r.access_count) for r in self._usage_records.values()],
                    key=lambda x: x[1], reverse=True
                )[:10],
                'last_reload': self._last_reload_time,
                'environment': self.environment,
                'config_hash': self._config_hash
            }
            return stats
    
    # Configuration management
    
    def reload_config(self, force: bool = False):
        """Reload configuration"""
        if force or self._config_needs_reload():
            self._load_all_configurations()
            return True
        return False
    
    def _config_needs_reload(self) -> bool:
        """Check if configuration needs to be reloaded"""
        # This method is no longer relevant as environment files are removed
        # Keeping it for now, but it will always return False.
        return False
    
    def validate_config(self) -> Dict[str, List[str]]:
        """Validate configuration completeness"""
        errors = []
        warnings = []
        
        # Check required configuration sections
        required_sections = ['server', 'database', 'paths', 'logging']
        for section in required_sections:
            if section not in self._config_data:
                errors.append(f"Missing required section: {section}")
        
        # Check path configuration
        if 'paths' in self._config_data:
            for key, path in self._config_data['paths'].items():
                path_obj = Path(path)
                if not path_obj.exists() and not path_obj.parent.exists():
                    warnings.append(f"Path may not exist: {key} = {path}")
        
        # Check port configuration
        server_config = self._config_data.get('server', {})
        if 'api' in server_config:
            port = server_config['api'].get('port')
            if port and (not isinstance(port, int) or port < 1 or port > 65535):
                errors.append(f"Invalid port number: {port}")
        
        return {
            'errors': errors,
            'warnings': warnings,
            'valid': len(errors) == 0
        }
    
    def __del__(self):
        """Clean up resources"""
        if hasattr(self, '_observer') and self._observer:
            self._observer.stop()
            self._observer.join()

# Global configuration manager instance
config_manager = UnifiedConfigManager()

# Convenient access function
def get_config(key: str, default: Any = None, component: str = "unknown") -> Any:
    """Convenient configuration access function"""
    return config_manager.get(key, default, component)

def get_log_message(category: str, message_key: str, 
                   style: str = None, component: str = "logging", **kwargs) -> str:
    """Convenient log message access function"""
    return config_manager.get_log_message(category, message_key, style, component, **kwargs)

def get_server_config(component: str = "api") -> Dict[str, Any]:
    """Convenient server configuration access function"""
    return config_manager.get_server_config(component)

def get_database_config() -> Dict[str, Any]:
    """Convenient database configuration access function"""
    return config_manager.get_database_config() 
Configuration Module
====================

Function
--------
System configuration management

Main Files
----------
unified_config_manager.py  Configuration manager
user_config.json           User configuration file

Main Configuration
------------------
System ports:
  frontend: 3001
  backend: 8001
  database: 5433

Log level:
  logging.level.current     Global log level

File monitoring:
  file_monitoring.schedule  Scan time
  file_monitoring.processing  Processing parameters

Data retention:
  data_retention.packet_flows_days: 8

Usage
-----
from config.unified_config_manager import get_config
value = get_config('logging.level', 'INFO', 'component_name') 
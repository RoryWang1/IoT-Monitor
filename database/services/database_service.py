#!/usr/bin/env python3
"""
Database Service Layer
Provides unified interface for all database operations
Only handles experiment-isolated operations without lab concept
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional

# Import unified configuration manager
from config.unified_config_manager import UnifiedConfigManager

# Import repositories using correct paths
from database.repositories.reference_repository import ReferenceRepository
from database.connection import PostgreSQLDatabaseManager

# Initialize configuration manager
config_manager = UnifiedConfigManager()

# Configure logger
logger = logging.getLogger(__name__)

# Import timezone manager for timestamp conversion (lazy import to avoid circular dependencies)
timezone_manager = None


class ConfigurableDatabaseService:
    """
    Unified database service for IoT Device Monitor
    Handles experiment isolation without lab concept
    Fully configurable through JSON configuration files
    """
    
    def __init__(self, db_manager: PostgreSQLDatabaseManager):
        """Initialize service with database manager and configuration"""
        self.db_manager = db_manager
        self.config = config_manager.get_config()
        self.log_templates = config_manager.get_log_templates()
        
        # Get service-specific configuration
        self.service_config = self.config.get('database_service', {})
        self.pagination_config = self.service_config.get('pagination', {})
        self.time_windows_config = self.service_config.get('time_windows', {})
        self.device_defaults_config = self.service_config.get('device_defaults', {})
        self.experiment_defaults_config = self.service_config.get('experiment_defaults', {})
        self.status_values_config = self.service_config.get('status_values', {})
        self.traffic_formatting_config = self.service_config.get('traffic_formatting', {})
        self.resolution_metadata_config = self.service_config.get('resolution_metadata', {})
        self.logging_config = self.service_config.get('logging', {})
        self.features_config = self.service_config.get('features', {})
        self.health_check_config = self.service_config.get('health_check', {})
        self.performance_config = self.service_config.get('performance', {})
        
        # Initialize repositories with lazy loading to avoid circular imports
        self._device_repo = None
        self._status_service = None
        self.reference_repo = ReferenceRepository(db_manager)
        
        # Initialize reference service for API compatibility
        from database.services.reference_service import ReferenceService
        self.reference_service = ReferenceService(db_manager)
        
        # Initialize unified device resolution service
        from database.services.device_resolution_service import DeviceResolutionService
        self.device_resolution_service = DeviceResolutionService(db_manager)
    
    def _get_log_message(self, template_key: str, **kwargs) -> str:
        """Get formatted log message from templates"""
        try:
            template = self.log_templates.get('database_service', {}).get(template_key, {})
            message_format = template.get('emoji', template_key)
            return message_format.format(**kwargs)
        except Exception:
            return f"[Missing log message: database_service.{template_key}]"
    
    def _get_default_limit(self) -> int:
        """Get default pagination limit from configuration"""
        return self.pagination_config.get('default_limit', 100)
    
    def _get_default_offset(self) -> int:
        """Get default pagination offset from configuration"""
        return self.pagination_config.get('default_offset', 0)
    
    def _get_default_time_window(self) -> str:
        """Get default time window from configuration"""
        return self.time_windows_config.get('default_time_window', '24h')
    
    def _get_unknown_device_name(self, mac_address: str) -> str:
        """Generate unknown device name from configuration"""
        prefix = self.device_defaults_config.get('unknown_device_name_prefix', 'Device_')
        suffix_length = self.device_defaults_config.get('unknown_device_id_suffix_length', 8)
        if mac_address and len(mac_address) >= suffix_length:
            return f"{prefix}{mac_address[-suffix_length:]}"
        return f"{prefix}Unknown"
    
    def _get_unknown_device_type(self) -> str:
        """Get unknown device type from configuration"""
        return self.device_defaults_config.get('unknown_device_type', 'unknown')
    
    def _get_unknown_manufacturer(self) -> str:
        """Get unknown manufacturer from configuration"""
        return self.device_defaults_config.get('unknown_manufacturer', 'Unknown')
    
    def _get_experiment_name(self, experiment_id: str) -> str:
        """Generate experiment name from configuration"""
        if self.experiment_defaults_config.get('enable_auto_naming', True):
            prefix = self.experiment_defaults_config.get('default_experiment_name_prefix', 'Experiment ')
            # Extract number from experiment_id and format it properly
            exp_number = experiment_id.replace('experiment_', '')
            return f"{prefix}{exp_number}"
        return experiment_id
    
    def _get_experiment_description(self, experiment_id: str) -> str:
        """Generate experiment description from configuration"""
        prefix = self.experiment_defaults_config.get('default_description_prefix', 'IoT device monitoring experiment ')
        return f"{prefix}{experiment_id}"
    
    def _format_traffic(self, total_bytes: int) -> str:
        """Format traffic bytes according to configuration"""
        if not self.traffic_formatting_config.get('enable_traffic_formatting', True):
            return f"{total_bytes} B"
        
        mb_threshold = self.traffic_formatting_config.get('mb_unit_threshold', 1048576)
        kb_threshold = self.traffic_formatting_config.get('bytes_unit_threshold', 1024)
        decimal_places = self.traffic_formatting_config.get('decimal_places', 1)
        
        if total_bytes >= mb_threshold:
            return f"{total_bytes / mb_threshold:.{decimal_places}f} MB"
        elif total_bytes >= kb_threshold:
            return f"{total_bytes / kb_threshold:.{decimal_places}f} KB"
        else:
            return f"{total_bytes} B"
    
    @property
    def device_repo(self):
        """Lazy load device repository to avoid circular imports"""
        if self._device_repo is None:
            from database.repositories.device_repository import DeviceRepository
            self._device_repo = DeviceRepository(self.db_manager)
        return self._device_repo
    
    @property
    def status_service(self):
        """Lazy load device status service to avoid circular imports"""
        if self._status_service is None:
            from backend.pcap_process.analyzers.device import DeviceStatusService
            self._status_service = DeviceStatusService(self.db_manager)
        return self._status_service
    
    # Device Operations
    async def get_device_by_id(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get device by ID from database"""
        try:
            return await self.device_repo.get_device_by_id(device_id)
        except Exception as e:
            if self.logging_config.get('log_error_details', True):
                logger.error(self._get_log_message('device_get_failed', device_id=device_id, error=str(e)))
            return None
    
    async def get_device_by_mac(self, mac_address: str, experiment_id: str = None) -> Optional[Dict[str, Any]]:
        """Get device by MAC address from database"""
        try:
            return await self.device_repo.get_device_by_mac(mac_address, experiment_id)
        except Exception as e:
            if self.logging_config.get('log_error_details', True):
                logger.error(self._get_log_message('device_by_mac_failed', 
                                                 mac_address=mac_address, 
                                                 experiment_id=experiment_id, 
                                                 error=str(e)))
            return None
    
    async def get_all_devices(self) -> List[Dict[str, Any]]:
        """Get all devices from database"""
        try:
            return await self.device_repo.get_all_devices()
        except Exception as e:
            if self.logging_config.get('log_error_details', True):
                logger.error(self._get_log_message('all_devices_failed', error=str(e)))
            return []
    
    async def get_device_statistics(self, device_id: str, experiment_id: str = None) -> Optional[Dict[str, Any]]:
        """Get device statistics from database"""
        try:
            return await self.device_repo.get_device_statistics(device_id, experiment_id)
        except Exception as e:
            if self.logging_config.get('log_error_details', True):
                logger.error(self._get_log_message('device_statistics_failed', 
                                                 device_id=device_id, 
                                                 experiment_id=experiment_id, 
                                                 error=str(e)))
            return None
    
    async def get_device_traffic_trend(self, device_id: str, time_window: str = None, experiment_id: str = None) -> List[Dict[str, Any]]:
        """Get device traffic trend from database"""
        try:
            time_window = time_window or self._get_default_time_window()
            return await self.device_repo.get_device_traffic_trend(device_id, time_window, experiment_id)
        except Exception as e:
            if self.logging_config.get('log_error_details', True):
                logger.error(self._get_log_message('traffic_trend_failed', 
                                                 device_id=device_id, 
                                                 experiment_id=experiment_id, 
                                                 error=str(e)))
            return []
    
    async def get_device_protocol_distribution(self, device_id: str, time_window: str = None, experiment_id: str = None) -> List[Dict[str, Any]]:
        """Get device protocol distribution from database"""
        try:
            time_window = time_window or self._get_default_time_window()
            return await self.device_repo.get_device_protocol_distribution(device_id, time_window, experiment_id)
        except Exception as e:
            if self.logging_config.get('log_error_details', True):
                logger.error(self._get_log_message('protocol_distribution_failed', 
                                                 device_id=device_id, 
                                                 experiment_id=experiment_id, 
                                                 error=str(e)))
            return []
    
    async def get_device_port_analysis(self, device_id: str, time_window: str = None, experiment_id: str = None) -> List[Dict[str, Any]]:
        """Get device port analysis from database"""
        try:
            time_window = time_window or self._get_default_time_window()
            return await self.device_repo.get_device_port_analysis(device_id, time_window, experiment_id)
        except Exception as e:
            if self.logging_config.get('log_error_details', True):
                logger.error(self._get_log_message('port_analysis_failed', 
                                                 device_id=device_id, 
                                                 experiment_id=experiment_id, 
                                                 error=str(e)))
            return []
    
    async def get_device_activity_timeline(self, device_id: str, time_window: str = None, experiment_id: str = None) -> List[Dict[str, Any]]:
        """Get device activity timeline from database"""
        try:
            time_window = time_window or self._get_default_time_window()
            return await self.device_repo.get_device_activity_timeline(device_id, time_window, experiment_id)
        except Exception as e:
            if self.logging_config.get('log_error_details', True):
                logger.error(self._get_log_message('activity_timeline_failed', 
                                                 device_id=device_id, 
                                                 experiment_id=experiment_id, 
                                                 error=str(e)))
            return []
    
    async def get_device_network_topology(self, device_id: str, time_window: str = None, experiment_id: str = None) -> Optional[Dict[str, Any]]:
        """Get device network topology from database"""
        try:
            time_window = time_window or self._get_default_time_window()
            return await self.device_repo.get_device_network_topology(device_id, time_window, experiment_id)
        except Exception as e:
            if self.logging_config.get('log_error_details', True):
                logger.error(self._get_log_message('network_topology_failed', 
                                                 device_id=device_id, 
                                                 experiment_id=experiment_id, 
                                                 error=str(e)))
            return None
    
    async def get_device_detail(self, device_id: str, experiment_id: str = None, time_window: str = None) -> Optional[Dict[str, Any]]:
        """Get complete device detail from database"""
        try:
            time_window = time_window or self._get_default_time_window()
            return await self.device_repo.get_device_detail(device_id, experiment_id, time_window)
        except Exception as e:
            if self.logging_config.get('log_error_details', True):
                logger.error(self._get_log_message('device_detail_failed', 
                                                 device_id=device_id, 
                                                 experiment_id=experiment_id, 
                                                 error=str(e)))
            return None
    
    async def get_devices_list(self, limit: int = None, offset: int = None, experiment_id: str = None) -> List[Dict[str, Any]]:
        """Get devices list with pagination and experiment filtering"""
        try:
            limit = limit or self._get_default_limit()
            offset = offset or self._get_default_offset()
            
            # Get raw device data from repository
            raw_devices = await self.device_repo.get_devices_list(limit=limit, offset=offset, experiment_id=experiment_id)
            
            if not raw_devices:
                return []
            
            # Convert from frontend format back to enhancement format
            devices_for_enhancement = []
            for device in raw_devices:
                device_dict = {
                    'device_id': device.get('deviceId'),
                    'device_name': device.get('deviceName'),
                    'device_type': device.get('deviceType'),
                    'mac_address': device.get('macAddress'),
                    'ip_address': device.get('ipAddress'),
                    'status': device.get('status'),
                    'manufacturer': device.get('manufacturer'),
                    'experiment_id': device.get('experimentId'),
                    'created_at': device.get('createdAt'),
                    'updated_at': device.get('updatedAt')
                }
                devices_for_enhancement.append(device_dict)
            
            # Enhance devices with reference data if feature is enabled
            if self.features_config.get('enable_device_enhancement', True):
                enhanced_devices = await self.reference_service.enhance_device_list(devices_for_enhancement)
            else:
                enhanced_devices = devices_for_enhancement
            
            # Convert back to frontend format with enhanced data
            enhanced_result = []
            for device in enhanced_devices:
                # Use enhanced data or fallback to original
                device_name = device.get('resolvedName') or device.get('device_name')
                if not device_name and self.device_defaults_config.get('enable_name_fallback', True):
                    device_name = self._get_unknown_device_name(device.get('mac_address'))
                
                enhanced_device = {
                    'deviceId': device.get('device_id'),
                    'deviceName': device_name,
                    'deviceType': device.get('resolvedType') or device.get('device_type') or self._get_unknown_device_type(),
                    'macAddress': device.get('mac_address'),
                    'ipAddress': device.get('ip_address'),
                    'status': device.get('status'),
                    'manufacturer': device.get('resolvedVendor') or device.get('manufacturer') or self._get_unknown_manufacturer(),
                    'experimentId': device.get('experiment_id'),
                    'createdAt': device.get('created_at'),
                    'updatedAt': device.get('updated_at')
                }
                
                # Include resolution metadata if enabled
                if self.resolution_metadata_config.get('include_resolution_metadata', True):
                    enhanced_device.update({
                        'resolvedName': device.get('resolvedName'),
                        'resolvedVendor': device.get('resolvedVendor'),
                        'resolvedType': device.get('resolvedType'),
                        'resolutionSource': device.get('resolutionSource', 
                                                      self.resolution_metadata_config.get('default_resolutionSource', 'none')),
                        'sourceMapping': device.get('sourceMapping', {}) if self.resolution_metadata_config.get('enable_sourceMapping', True) else {}
                    })
                
                enhanced_result.append(enhanced_device)
            
            if self.logging_config.get('log_enhancement_operations', True):
                logger.info(self._get_log_message('devices_list_enhanced', count=len(enhanced_result)))
            
            return enhanced_result
            
        except Exception as e:
            if self.logging_config.get('log_error_details', True):
                logger.error(self._get_log_message('devices_list_failed', error=str(e)))
            return []

    async def get_devices_count(self) -> int:
        """Get total devices count"""
        try:
            return await self.device_repo.get_devices_count()
        except Exception as e:
            if self.logging_config.get('log_error_details', True):
                logger.error(self._get_log_message('devices_count_failed', error=str(e)))
            return 0
    
    async def get_all_devices_with_stats(self, experiment_id: str = None) -> List[Dict[str, Any]]:
        """Get all devices with their statistics"""
        try:
            return await self.device_repo.get_all_devices_with_stats(experiment_id)
        except Exception as e:
            if self.logging_config.get('log_error_details', True):
                logger.error(self._get_log_message('devices_with_stats_failed', error=str(e)))
            return []
    
    # Reference Data Operations - delegated to reference_service
    async def get_known_devices(self, limit: int = 100, offset: int = 0, search: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get known devices with pagination and search"""
        return await self.reference_service.get_known_devices(limit=limit, offset=offset, search=search)
    
    async def get_vendor_patterns(self, limit: int = 100, offset: int = 0, vendor: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get vendor patterns with pagination and filtering"""
        return await self.reference_service.get_vendor_patterns(limit=limit, offset=offset, vendor=vendor)
    
    async def lookup_device_by_mac(self, mac_address: str) -> Optional[Dict[str, Any]]:
        """Lookup device information by MAC address"""
        return await self.reference_service.lookup_device_by_mac(mac_address)
    
    async def lookup_vendor_by_mac(self, mac_address: str) -> Optional[Dict[str, Any]]:
        """Lookup vendor information by MAC address"""
        return await self.reference_service.lookup_vendor_by_mac(mac_address)
    
    async def get_device_types(self) -> List[Dict[str, Any]]:
        """Get all available device types"""
        return await self.reference_service.get_device_types()
    
    # Unified Device Resolution Operations
    async def resolve_device_info(self, mac_address: str, use_cache: bool = True) -> Dict[str, Any]:
        """Resolve device information with intelligent field-level fallback"""
        return await self.device_resolution_service.resolve_device_info(mac_address, use_cache)
    
    async def bulk_resolve_devices(self, mac_addresses: List[str], use_cache: bool = True) -> Dict[str, Dict[str, Any]]:
        """Bulk resolve device information with intelligent field-level fallback"""
        return await self.device_resolution_service.bulk_resolve_devices(mac_addresses, use_cache)
    
    def clear_device_resolution_cache(self):
        """Clear the device resolution cache"""
        self.device_resolution_service.clear_cache()
    
    def get_device_resolution_cache_stats(self) -> Dict[str, Any]:
        """Get device resolution cache statistics"""
        return self.device_resolution_service.get_cache_stats()
    
    # Connection Management
    async def close_connections(self):
        """Close all database connections"""
        try:
            if hasattr(self, 'db_manager') and self.db_manager:
                await self.db_manager.close()
        except Exception as e:
            if self.logging_config.get('log_error_details', True):
                logger.error(self._get_log_message('database_connections_close_failed', error=str(e)))
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close_connections()

    # Experiment Related Methods
    
    async def get_experiments_overview(self, limit: int = None, offset: int = None) -> List[Dict[str, Any]]:
        """Get experiments overview list"""
        try:
            limit = limit or self._get_default_limit()
            offset = offset or self._get_default_offset()
            
            # Get experiments from experiments table, then LEFT JOIN device data, not GROUP BY devices table
            query = """
            SELECT 
                e.experiment_id,
                e.experiment_name,
                e.status as exp_status,
                e.description,
                e.created_at,
                COUNT(d.device_id) as device_count,
                COUNT(CASE WHEN d.status = 'online' THEN 1 END) as online_devices,
                COUNT(CASE WHEN d.status != 'online' THEN 1 END) as offline_devices
            FROM experiments e
            LEFT JOIN devices d ON e.experiment_id = d.experiment_id
            GROUP BY e.experiment_id, e.experiment_name, e.status, e.description, e.created_at
            ORDER BY e.created_at DESC
            LIMIT $1 OFFSET $2
            """
            
            experiments_data = await self.db_manager.execute_query(query, (limit, offset))
            
            experiments = []
            for exp_data in experiments_data:
                experiment_id = exp_data['experiment_id']
                
                # Get device details for this experiment with real data timestamps
                devices_query = """
                SELECT d.device_id, d.device_name, d.device_type, d.mac_address, d.status, d.manufacturer, d.ip_address,
                       pf.first_seen, pf.last_seen
                FROM devices d
                LEFT JOIN (
                    SELECT device_id,
                           MIN(packet_timestamp) as first_seen,
                           MAX(packet_timestamp) as last_seen
                    FROM packet_flows
                    WHERE experiment_id = $1
                    GROUP BY device_id
                ) pf ON d.device_id = pf.device_id
                WHERE d.experiment_id = $1
                ORDER BY d.device_name
                """
                raw_devices = await self.db_manager.execute_query(devices_query, (experiment_id,))
                
                # Convert to dict format for enhancement
                devices_for_enhancement = []
                for device in raw_devices:
                    device_dict = {
                        'device_id': device['device_id'],
                        'device_name': device['device_name'],
                        'device_type': device['device_type'],
                        'mac_address': device['mac_address'],
                        'ip_address': device['ip_address'],
                        'status': device['status'],
                        'manufacturer': device['manufacturer'],
                        'first_seen': device['first_seen'],  # Real data first seen time
                        'last_seen': device['last_seen']     # Real data last seen time
                    }
                    devices_for_enhancement.append(device_dict)
                
                # Enhance devices with reference data if feature is enabled
                if self.features_config.get('enable_device_enhancement', True):
                    enhanced_devices = await self.reference_service.enhance_device_list(devices_for_enhancement) if devices_for_enhancement else []
                else:
                    enhanced_devices = devices_for_enhancement
                
                # Format devices for frontend consistency with REAL-TIME status calculation and ENHANCED data
                devices = []
                real_online_count = 0
                
                for device in enhanced_devices:
                    # Calculate REAL-TIME device status if feature is enabled
                    if self.features_config.get('enable_real_time_status', True):
                        device_status = await self.status_service.calculate_realtime_status(device['device_id'], experiment_id)
                    else:
                        device_status = device['status']
                    
                    if device_status == 'online':
                        real_online_count += 1
                    
                    # Use configuration for unknown values
                    device_name = device.get('resolvedName', device['device_name'])
                    if not device_name and self.device_defaults_config.get('enable_name_fallback', True):
                        device_name = self._get_unknown_device_name(device['mac_address'])
                    
                    formatted_device = {
                        'deviceId': str(device['device_id']),
                        'deviceName': device_name,
                        'deviceType': device.get('resolvedType', device['device_type']) or self._get_unknown_device_type(),
                        'macAddress': device['mac_address'],
                        'ipAddress': device['ip_address'],
                        'manufacturer': device.get('resolvedVendor', device['manufacturer']) or self._get_unknown_manufacturer(),
                        'status': device_status,
                        'firstSeen': device['first_seen'].isoformat() if device['first_seen'] else None,  # Real data first seen time
                        'lastSeen': device['last_seen'].isoformat() if device['last_seen'] else None      # Real data last seen time
                    }
                    devices.append(formatted_device)
                
                # Get traffic total for this experiment - use REAL-TIME data from packet_flows
                traffic_query = """
                SELECT COALESCE(SUM(packet_size), 0) as total_bytes
                FROM packet_flows pf
                WHERE pf.experiment_id = $1
                """
                traffic_result = await self.db_manager.execute_query(traffic_query, (experiment_id,))
                total_bytes = int(traffic_result[0]['total_bytes']) if traffic_result else 0
                
                # Format traffic using configuration
                formatted_traffic = self._format_traffic(total_bytes)
                
                # Count device types if statistics calculation is enabled
                device_types = {}
                if self.features_config.get('enable_statistics_calculation', True):
                    for device in devices:
                        device_type = device['deviceType']
                        device_types[device_type] = device_types.get(device_type, 0) + 1
                
                experiment = {
                    'experimentId': experiment_id,
                    'experimentName': self._get_experiment_name(experiment_id),
                    'deviceCount': exp_data['device_count'],
                    'onlineDevices': real_online_count,  # Use real-time calculated online count
                    'deviceTypes': device_types,
                    'devices': devices,
                    'totalTraffic': formatted_traffic,
                    'status': self.status_values_config.get('completed_status', 'completed'),
                    'description': self._get_experiment_description(experiment_id)
                }
                experiments.append(experiment)
            
            return experiments
            
        except Exception as e:
            if self.logging_config.get('log_error_details', True):
                logger.error(self._get_log_message('experiments_overview_failed', error=str(e)))
            return []
    
    async def get_experiment_detail(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information for a specific experiment"""
        try:
            # First check if experiment exists
            exp_query = """
            SELECT experiment_id, experiment_name, status, created_at, updated_at, start_date
            FROM experiments 
            WHERE experiment_id = $1
            """
            exp_result = await self.db_manager.execute_query(exp_query, (experiment_id,))
            
            if not exp_result:
                return None
            
            experiment_info = exp_result[0]
            
            # Get experiment devices with real data timestamps from packet_flows
            devices_query = """
            SELECT d.device_id, d.device_name, d.device_type, d.mac_address, d.ip_address, d.status, 
                   d.manufacturer, d.created_at, d.updated_at,
                   pf.first_seen, pf.last_seen
            FROM devices d
            LEFT JOIN (
                SELECT device_id,
                       MIN(packet_timestamp) as first_seen,
                       MAX(packet_timestamp) as last_seen
                FROM packet_flows
                WHERE experiment_id = $1
                GROUP BY device_id
            ) pf ON d.device_id = pf.device_id
            WHERE d.experiment_id = $1
            ORDER BY d.device_name
            """
            devices = await self.db_manager.execute_query(devices_query, (experiment_id,))
            
            # Calculate statistics with REAL-TIME status
            total_devices = len(devices) if devices else 0
            real_online_count = 0
            
            # Calculate real-time status for each device in detail view
            for device in devices or []:
                device_status = await self.status_service.calculate_realtime_status(device['device_id'], experiment_id)
                if device_status == 'online':
                    real_online_count += 1
            
            online_devices = real_online_count
            offline_devices = total_devices - online_devices
            
            # Get traffic data - use REAL-TIME data from packet_flows
            # Use packet_flows for REAL-TIME data instead of empty device_traffic_trend table
            if devices:
                traffic_query = """
                SELECT COALESCE(SUM(packet_size), 0) as total_bytes, COALESCE(COUNT(*), 0) as total_packets
                FROM packet_flows pf
                WHERE pf.experiment_id = $1
                """
                traffic_result = await self.db_manager.execute_query(traffic_query, (experiment_id,))
                total_bytes = int(traffic_result[0]['total_bytes']) if traffic_result else 0
                total_packets = int(traffic_result[0]['total_packets']) if traffic_result else 0
            else:
                total_bytes = 0
                total_packets = 0
            
            # Format devices for frontend (convert to camelCase) with REAL-TIME status and ENHANCED reference data
            formatted_devices = []
            if devices:
                # Convert to dict format for enhancement
                devices_for_enhancement = []
                for device in devices:
                    device_dict = {
                        'device_id': device['device_id'],
                        'device_name': device['device_name'],
                        'device_type': device['device_type'],
                        'mac_address': device['mac_address'],
                        'ip_address': device['ip_address'],
                        'status': device['status'],
                        'manufacturer': device['manufacturer'],
                        'first_seen': device['first_seen'],  # Real data first seen time
                        'last_seen': device['last_seen'],    # Real data last seen time
                        'created_at': device['created_at'],
                        'updated_at': device['updated_at']
                    }
                    devices_for_enhancement.append(device_dict)
                
                # Enhance devices with reference data
                enhanced_devices = await self.reference_service.enhance_device_list(devices_for_enhancement)
                
                for device in enhanced_devices:
                    # Calculate real-time status for detail view
                    device_status = await self.status_service.calculate_realtime_status(device['device_id'], experiment_id)
                    
                    # Use configuration for unknown values
                    device_name = device.get('resolvedName', device['device_name'])
                    if not device_name and self.device_defaults_config.get('enable_name_fallback', True):
                        device_name = self._get_unknown_device_name(device['mac_address'])
                    
                    formatted_device = {
                        'deviceId': str(device['device_id']),
                        'deviceName': device_name,
                        'deviceType': device.get('resolvedType', device['device_type']) or self._get_unknown_device_type(),
                        'macAddress': device['mac_address'],
                        'ipAddress': device['ip_address'],
                        'status': device_status,  # Use real-time calculated status
                        'manufacturer': device.get('resolvedVendor', device['manufacturer']) or self._get_unknown_manufacturer(),
                        'firstSeen': device['first_seen'].isoformat() if device['first_seen'] else None,  # Real data first seen time
                        'lastSeen': device['last_seen'].isoformat() if device['last_seen'] else None,      # Real data last seen time
                        'createdAt': device['created_at'].isoformat() if device['created_at'] else None,
                        'updatedAt': device['updated_at'].isoformat() if device['updated_at'] else None
                    }
                    
                    # Include resolution metadata if enabled
                    if self.resolution_metadata_config.get('include_resolution_metadata', True):
                        formatted_device.update({
                        'resolvedName': device.get('resolvedName'),
                        'resolvedVendor': device.get('resolvedVendor'),
                        'resolvedType': device.get('resolvedType'),
                            'resolutionSource': device.get('resolutionSource', 
                                                          self.resolution_metadata_config.get('default_resolutionSource', 'none')),
                            'sourceMapping': device.get('sourceMapping', {}) if self.resolution_metadata_config.get('enable_sourceMapping', True) else {}
                        })
                    formatted_devices.append(formatted_device)
            
            # Device types distribution - use enhanced device data
            device_types = {}
            if formatted_devices:
                for device in formatted_devices:
                    device_type = device['deviceType'] or 'unknown'  # use frontend field name
                    device_types[device_type] = device_types.get(device_type, 0) + 1
            
            experiment_detail = {
                'experimentId': experiment_id,
                'experimentName': self._get_experiment_name(experiment_id),
                'status': experiment_info['status'] or self.experiment_defaults_config.get('default_status', 'active'),
                'description': self._get_experiment_description(experiment_id),
                'statistics': {
                    'totalDevices': total_devices,
                    'onlineDevices': online_devices,
                    'offlineDevices': offline_devices,
                    'totalBytes': total_bytes,
                    'totalPackets': total_packets,
                    'deviceTypes': device_types
                },
                'devices': formatted_devices,
                'metadata': {
                    'createdAt': experiment_info['created_at'].isoformat() if experiment_info['created_at'] else None,
                    'updatedAt': experiment_info['updated_at'].isoformat() if experiment_info['updated_at'] else None,
                    'startDate': experiment_info['start_date'].isoformat() if experiment_info['start_date'] else None,
                    'duration': 'N/A',
                    'dataSource': 'pcap_files'
                }
            }
            
            return experiment_detail
            
        except Exception as e:
            if self.logging_config.get('log_error_details', True):
                logger.error(self._get_log_message('experiment_detail_failed', experiment_id=experiment_id, error=str(e)))
            return None
    
    async def get_experiment_devices(self, experiment_id: str, limit: int = None, offset: int = None) -> List[Dict[str, Any]]:
        """Get devices for a specific experiment with enhanced reference data and pagination"""
        try:
            # use configurable default values
            limit = limit or self._get_default_limit()
            offset = offset or self._get_default_offset()
            
            query = """
            SELECT d.device_id, d.device_name, d.device_type, d.mac_address, d.ip_address, d.status,
                   d.manufacturer, d.created_at, d.updated_at,
                   pf.first_seen, pf.last_seen
            FROM devices d
            LEFT JOIN (
                SELECT device_id,
                       MIN(packet_timestamp) as first_seen,
                       MAX(packet_timestamp) as last_seen
                FROM packet_flows
                WHERE experiment_id = $1
                GROUP BY device_id
            ) pf ON d.device_id = pf.device_id
            WHERE d.experiment_id = $1
            ORDER BY d.device_name
            LIMIT $2 OFFSET $3
            """
            raw_devices = await self.db_manager.execute_query(query, (experiment_id, limit, offset))
            
            if not raw_devices:
                return []
            
            # Convert to dict format for enhancement
            devices_for_enhancement = []
            for device in raw_devices:
                device_dict = {
                    'device_id': device['device_id'],
                    'device_name': device['device_name'],
                    'device_type': device['device_type'],
                    'mac_address': device['mac_address'],
                    'ip_address': device['ip_address'],
                    'status': device['status'],
                    'manufacturer': device['manufacturer'],
                    'first_seen': device['first_seen'],  # Real data first seen time
                    'last_seen': device['last_seen'],    # Real data last seen time
                    'created_at': device['created_at'],
                    'updated_at': device['updated_at']
                }
                devices_for_enhancement.append(device_dict)
            
            # Enhance devices with reference data
            enhanced_devices = await self.reference_service.enhance_device_list(devices_for_enhancement)
            
            # Format for frontend
            formatted_devices = []
            for device in enhanced_devices:
                # Use configuration for unknown values
                device_name = device.get('resolvedName', device['device_name'])
                if not device_name and self.device_defaults_config.get('enable_name_fallback', True):
                    device_name = self._get_unknown_device_name(device['mac_address'])
                
                formatted_device = {
                    'deviceId': str(device['device_id']),
                    'deviceName': device_name,
                    'deviceType': device.get('resolvedType', device['device_type']) or self._get_unknown_device_type(),
                    'macAddress': device['mac_address'],
                    'ipAddress': device['ip_address'],
                    'status': device['status'],
                    'manufacturer': device.get('resolvedVendor', device['manufacturer']) or self._get_unknown_manufacturer(),
                    'firstSeen': device['first_seen'].isoformat() if device['first_seen'] else None,  # Real data first seen time
                    'lastSeen': device['last_seen'].isoformat() if device['last_seen'] else None,      # Real data last seen time
                    'createdAt': device['created_at'].isoformat() if device['created_at'] else None,
                    'updatedAt': device['updated_at'].isoformat() if device['updated_at'] else None
                }
                
                # Include resolution metadata if enabled
                if self.resolution_metadata_config.get('include_resolution_metadata', True):
                    formatted_device.update({
                    'resolvedName': device.get('resolvedName'),
                    'resolvedVendor': device.get('resolvedVendor'),
                    'resolvedType': device.get('resolvedType'),
                        'resolutionSource': device.get('resolutionSource', 
                                                      self.resolution_metadata_config.get('default_resolutionSource', 'none')),
                        'sourceMapping': device.get('sourceMapping', {}) if self.resolution_metadata_config.get('enable_sourceMapping', True) else {}
                    })
                formatted_devices.append(formatted_device)
            
            if self.logging_config.get('log_enhancement_operations', True):
                logger.info(self._get_log_message('devices_enhanced_formatted', 
                                                count=len(formatted_devices), 
                                                experiment_id=experiment_id))
            return formatted_devices
            
        except Exception as e:
            if self.logging_config.get('log_error_details', True):
                logger.error(self._get_log_message('experiment_devices_failed', 
                                                 experiment_id=experiment_id, 
                                                 error=str(e)))
            return []
    
    async def get_experiment_device_count(self, experiment_id: str) -> int:
        """Get total device count for a specific experiment"""
        try:
            query = "SELECT COUNT(*) FROM devices WHERE experiment_id = $1"
            result = await self.db_manager.execute_scalar(query, (experiment_id,))
            return result or 0
        except Exception as e:
            if self.logging_config.get('log_error_details', True):
                logger.error(self._get_log_message('experiment_device_count_failed', 
                                                 experiment_id=experiment_id, 
                                                 error=str(e)))
            return 0
    
    async def get_database_health(self) -> Dict[str, Any]:
        """Check database health status"""
        try:
            # Test database connection using configured query
            query = self.health_check_config.get('test_query', "SELECT 1 as status")
            result = await self.db_manager.execute_query(query, ())
            
            if result:
                health_response = {
                    "status": self.status_values_config.get('healthy_status', 'healthy'),
                    "connection": self.status_values_config.get('active_connection', 'active'),
                    "timestamp": "now()"
                }
                
                # Add detailed response if enabled
                if self.health_check_config.get('enable_detailed_response', True):
                    health_response.update({
                        "query_result": result[0] if result else None,
                        "response_time": "< 1s"  # Could be enhanced with actual timing
                    })
                
                return health_response
            else:
                return {
                    "status": self.status_values_config.get('unhealthy_status', 'unhealthy'), 
                    "connection": self.status_values_config.get('failed_connection', 'failed'),
                    "error": "No result from test query"
                }
                
        except Exception as e:
            if self.logging_config.get('log_database_health', True):
                logger.error(self._get_log_message('database_health_check_failed', error=str(e)))
            return {
                "status": self.status_values_config.get('unhealthy_status', 'unhealthy'),
                "connection": self.status_values_config.get('failed_connection', 'failed'), 
                "error": str(e)
            }
    
    async def close(self):
        """Close database connections"""
        try:
            if self.db_manager:
                await self.db_manager.close()
                if self.logging_config.get('log_database_health', True):
                    logger.info(self._get_log_message('database_service_closed'))
        except Exception as e:
            if self.logging_config.get('log_error_details', True):
                logger.error(self._get_log_message('database_service_close_failed', error=str(e)))


# Backward compatibility alias
DatabaseService = ConfigurableDatabaseService

# Global service instance getter function
def get_database_service() -> ConfigurableDatabaseService:
    """Get database service instance"""
    from database.connection import PostgreSQLDatabaseManager
    db_manager = PostgreSQLDatabaseManager()
    return ConfigurableDatabaseService(db_manager) 
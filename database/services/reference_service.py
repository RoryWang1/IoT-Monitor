"""
Reference Data Service
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

# Import unified configuration manager
from config.unified_config_manager import UnifiedConfigManager

# Import database repositories
from database.repositories.reference_repository import ReferenceRepository

# Initialize configuration manager
config_manager = UnifiedConfigManager()

logger = logging.getLogger(__name__)

class ConfigurableReferenceService:
    """High-level service for reference data operations - fully configurable"""
    
    def __init__(self, db_manager):
        """Initialize service with database manager and configuration"""
        self.db_manager = db_manager
        self.reference_repo = ReferenceRepository(db_manager)
    
        # Load configuration
        self.config = config_manager.get_config()
        self.log_templates = config_manager.get_log_templates()
        
        # Get service-specific configuration
        self.service_config = self.config.get('reference_service', {})
        self.fallback_config = self.service_config.get('fallback_values', {})
        self.response_config = self.service_config.get('response_messages', {})
        self.pagination_config = self.service_config.get('pagination', {})
        self.validation_config = self.service_config.get('validation', {})
        self.features_config = self.service_config.get('features', {})
        self.database_config = self.service_config.get('database_queries', {})
        self.logging_config = self.service_config.get('logging', {})
    
    def _get_log_message(self, template_key: str, **kwargs) -> str:
        """Get formatted log message from templates"""
        try:
            template = self.log_templates.get('reference_service', {}).get(template_key, {})
            message_format = template.get('emoji', template_key)
            return message_format.format(**kwargs)
        except Exception:
            return f"[Missing log message: reference_service.{template_key}]"
    
    def _get_unknown_device_name(self) -> str:
        """Get unknown device name from configuration"""
        return self.fallback_config.get('unknown_device_name', 'Unknown')
    
    def _get_unknown_device_vendor(self) -> str:
        """Get unknown device vendor from configuration"""
        return self.fallback_config.get('unknown_device_vendor', 'Unknown')
    
    def _get_unknown_device_type(self) -> str:
        """Get unknown device type from configuration"""
        return self.fallback_config.get('unknown_device_type', 'unknown')
    
    def _get_fallback_source(self) -> str:
        """Get fallback source from configuration"""
        return self.fallback_config.get('fallback_source', 'fallback')
    
    def _get_success_status(self) -> str:
        """Get success status from configuration"""
        return self.response_config.get('success_status', 'success')
    
    def _get_error_status(self) -> str:
        """Get error status from configuration"""
        return self.response_config.get('error_status', 'error')
    
    def _get_response_message(self, message_key: str, **kwargs) -> str:
        """Get response message from configuration"""
        template = self.response_config.get(message_key, message_key)
        try:
            return template.format(**kwargs)
        except (KeyError, ValueError):
            return template
    
    def _get_default_limit(self) -> int:
        """Get default pagination limit from configuration"""
        return self.pagination_config.get('default_limit', 100)
    
    def _get_default_offset(self) -> int:
        """Get default pagination offset from configuration"""
        return self.pagination_config.get('default_offset', 0)
    
    def _get_max_limit(self) -> int:
        """Get maximum pagination limit from configuration"""
        return self.pagination_config.get('max_limit', 500)
    
    def _should_log_enhancement_operations(self) -> bool:
        """Check if enhancement operations logging is enabled"""
        return self.logging_config.get('log_enhancement_operations', True)
    
    def _should_log_device_operations(self) -> bool:
        """Check if device operations logging is enabled"""
        return self.logging_config.get('log_device_operations', True)
    
    def _should_log_vendor_operations(self) -> bool:
        """Check if vendor operations logging is enabled"""
        return self.logging_config.get('log_vendor_operations', True)
    
    def _should_log_error_details(self) -> bool:
        """Check if error details logging is enabled"""
        return self.logging_config.get('log_error_details', True)
    
    def _should_return_original_on_error(self) -> bool:
        """Check if should return original devices on error"""
        return self.features_config.get('return_original_on_error', True)
    
    async def enhance_device_list(self, devices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enhance a list of devices with resolved names and vendor information
        Now uses the unified device resolution service
        """
        try:
            if not devices:
                return []
            
            # Extract MAC addresses
            mac_addresses = []
            for device in devices:
                mac = device.get('mac_address')
                if mac:
                    mac_addresses.append(mac)
            
            # Use unified device resolution service for better field-level resolution
            from database.services.device_resolution_service import DeviceResolutionService
            resolution_service = DeviceResolutionService(self.db_manager)
            resolution_data = await resolution_service.bulk_resolve_devices(mac_addresses)
            
            # Enhance device data
            enhanced_devices = []
            for device in devices:
                mac = device.get('mac_address')
                enhanced_device = device.copy()
                
                if mac and mac in resolution_data:
                    resolution = resolution_data[mac]
                    enhanced_device.update({
                        'resolvedName': resolution['resolvedName'],
                        'resolvedVendor': resolution['resolvedVendor'],
                        'resolvedType': resolution['resolvedType'],
                        'resolutionSource': resolution['source'],
                        'sourceMapping': resolution.get('sourceMapping', {})
                    })
                else:
                    enhanced_device.update({
                        'resolvedName': self._get_unknown_device_name(),
                        'resolvedVendor': self._get_unknown_device_vendor(),
                        'resolvedType': self._get_unknown_device_type(),
                        'resolutionSource': 'none',
                        'sourceMapping': {
                            'name_source': self._get_fallback_source(),
                            'vendor_source': self._get_fallback_source(),
                            'type_source': self._get_fallback_source()
                        }
                    })
                
                enhanced_devices.append(enhanced_device)
            
            if self._should_log_enhancement_operations():
                logger.info(self._get_log_message('device_list_enhanced', count=len(enhanced_devices)))
            return enhanced_devices
            
        except Exception as e:
            if self._should_log_error_details():
                logger.error(self._get_log_message('enhance_device_list_failed', error=str(e)))
            return devices if self._should_return_original_on_error() else []
    
    async def add_known_device(self, mac_address: str, device_name: str, 
                              device_type: str = None, vendor: str = None, 
                              notes: str = None) -> Dict[str, Any]:
        """
        Add a known device with validation and cache management
        """
        try:
            # Validate MAC address format
            if self.validation_config.get('enable_mac_validation', True) and not self._is_valid_mac_address(mac_address):
                return {
                    self._get_success_status(): False,
                    self._get_error_status(): self._get_response_message('invalid_mac_error'),
                    "mac_address": mac_address
                }
            
            # Validate device name
            if self.validation_config.get('enable_name_validation', True):
                name_to_check = device_name.strip() if self.validation_config.get('trim_whitespace', True) else device_name
                min_length = self.validation_config.get('min_name_length', 1)
                
                if not device_name or len(name_to_check) < min_length:
                    return {
                        self._get_success_status(): False,
                        self._get_error_status(): self._get_response_message('empty_name_error'),
                        "mac_address": mac_address
                    }
            
            # Add to database
            success = await self.reference_repo.add_known_device(
                mac_address, device_name.strip(), device_type, vendor, notes
            )
            
            if success:
                return {
                    self._get_success_status(): True,
                    "message": self._get_response_message('device_added_message', device_name=device_name),
                    "mac_address": mac_address,
                    "device_name": device_name
                }
            else:
                return {
                    self._get_success_status(): False,
                    self._get_error_status(): self._get_response_message('database_error'),
                    "mac_address": mac_address
                }
            
        except Exception as e:
            if self._should_log_error_details():
                logger.error(self._get_log_message('known_device_add_failed', 
                                                 mac_address=mac_address, error=str(e)))
            return {
                self._get_success_status(): False,
                self._get_error_status(): self._get_response_message('internal_error_prefix', error=str(e)),
                "mac_address": mac_address
            }
    
    async def update_known_device(self, mac_address: str, **kwargs) -> Dict[str, Any]:
        """
        Update a known device with cache management
        """
        try:
            success = await self.reference_repo.update_known_device(mac_address, **kwargs)
            
            if success:
                return {
                    self._get_success_status(): True,
                    "message": self._get_response_message('device_updated_message'),
                    "mac_address": mac_address
                }
            else:
                return {
                    self._get_success_status(): False,
                    self._get_error_status(): self._get_response_message('device_not_found_error'),
                    "mac_address": mac_address
                }
            
        except Exception as e:
            if self._should_log_error_details():
                logger.error(self._get_log_message('known_device_update_failed', 
                                                 mac_address=mac_address, error=str(e)))
            return {
                self._get_success_status(): False,
                self._get_error_status(): self._get_response_message('internal_error_prefix', error=str(e)),
                "mac_address": mac_address
            }
    
    async def delete_known_device(self, mac_address: str) -> Dict[str, Any]:
        """
        Delete a known device with cache management
        """
        try:
            success = await self.reference_repo.delete_known_device(mac_address)
            
            if success:
                return {
                    self._get_success_status(): True,
                    "message": self._get_response_message('device_deleted_message'),
                    "mac_address": mac_address
                }
            else:
                return {
                    self._get_success_status(): False,
                    self._get_error_status(): self._get_response_message('device_not_found_delete_error'),
                    "mac_address": mac_address
                }
            
        except Exception as e:
            if self._should_log_error_details():
                logger.error(self._get_log_message('known_device_delete_failed', 
                                                 mac_address=mac_address, error=str(e)))
            return {
                self._get_success_status(): False,
                self._get_error_status(): self._get_response_message('internal_error_prefix', error=str(e)),
                "mac_address": mac_address
            }
    
    async def get_vendor_information(self, mac_address: str) -> Dict[str, Any]:
        """
        Get detailed vendor information for a MAC address
        """
        try:
            # Extract OUI from MAC address
            oui_pattern = mac_address[:8] if len(mac_address) >= 8 else mac_address
            
            vendor_info = await self.reference_repo.get_vendor_by_oui(oui_pattern)
            
            if vendor_info:
                return {
                    self._get_success_status(): True,
                    "mac_address": mac_address,
                    "oui_pattern": vendor_info["oui_pattern"],
                    "vendor_name": vendor_info["vendor_name"],
                    "device_category": vendor_info["device_category"],
                }
            else:
                return {
                    self._get_success_status(): False,
                    "mac_address": mac_address,
                    "oui_pattern": oui_pattern,
                    self._get_error_status(): self._get_response_message('vendor_not_found_error')
                }
            
        except Exception as e:
            if self._should_log_error_details():
                logger.error(self._get_log_message('vendor_info_get_failed', 
                                                 mac_address=mac_address, error=str(e)))
            return {
                self._get_success_status(): False,
                "mac_address": mac_address,
                self._get_error_status(): self._get_response_message('internal_error_prefix', error=str(e))
            }
    
    async def search_vendors(self, search_term: str, limit: int = None) -> List[Dict[str, Any]]:
        """Search vendors using improved MAC prefix and fuzzy matching"""
        try:
            # Use default limit from configuration if not provided
            search_limit = limit if limit is not None else self._get_default_limit()
            return await self.reference_repo.search_vendors(search_term, search_limit)
        except Exception as e:
            if self._should_log_error_details():
                logger.error(self._get_log_message('vendors_search_failed', error=str(e)))
            return []
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get reference database statistics"""
        try:
            # Get basic counts
            known_devices_count = await self.reference_repo.get_known_devices_count()
            vendor_patterns_count = await self.reference_repo.get_vendor_patterns_count()
            
            # Get recent devices (configurable limit)
            statistics_limit = 5  # Could be configurable
            recent_devices = await self.reference_repo.get_recent_known_devices(limit=statistics_limit)
            
            # Get top vendors (configurable limit)
            top_vendors = await self.reference_repo.get_top_vendors(limit=statistics_limit)
            
            result = {
                "known_devices_count": known_devices_count,
                "vendor_patterns_count": vendor_patterns_count,
                "recent_known_devices": recent_devices,
                "top_vendors": top_vendors
            }
            
            # Add feature statistics if enabled
            if self.features_config.get('enable_cache_statistics', False):
                result.update({
                    "cache_enabled": True,
                    "cache_stats_available": True
                })
            
            return result
            
        except Exception as e:
            if self._should_log_error_details():
                logger.error(self._get_log_message('statistics_get_failed', error=str(e)))
            return {
                "known_devices_count": 0,
                "vendor_patterns_count": 0,
                "recent_known_devices": [],
                "top_vendors": []
            }
    
    def _is_valid_mac_address(self, mac: str) -> bool:
        """Validate MAC address format"""
        if not mac:
            return False
        
        # Remove common separators
        clean_mac = mac.replace(':', '').replace('-', '').replace(' ', '')
        
        # Should be exactly 12 hex characters
        if len(clean_mac) != 12:
            return False
        
        # Check if all characters are valid hex
        try:
            int(clean_mac, 16)
            return True
        except ValueError:
            return False
    
    def _get_fallback_device_info(self, mac_address: str) -> Dict[str, Any]:
        """Return fallback device information using configuration"""
        return {
            "mac_address": mac_address,
            "resolvedName": self._get_unknown_device_name(),
            "resolvedVendor": self._get_unknown_device_vendor(), 
            "resolvedType": self._get_unknown_device_type(),
            "source": self._get_fallback_source()
        }
    
    # New API support methods
    
    async def get_known_devices(self, limit: int = None, offset: int = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get known devices with pagination and improved search"""
        try:
            # Use configured defaults if not provided
            query_limit = limit if limit is not None else self._get_default_limit()
            query_offset = offset if offset is not None else self._get_default_offset()
            
            # Validate limit against maximum
            max_limit = self._get_max_limit()
            if self.pagination_config.get('enable_pagination_validation', True) and query_limit > max_limit:
                query_limit = max_limit
            
            if search:
                # Use the new search method for better MAC address and name matching
                search_results = await self.reference_repo.search_known_devices(search, query_limit)
                # Apply offset manually for search results
                return search_results[query_offset:query_offset + query_limit] if len(search_results) > query_offset else []
            else:
                # Direct query for listing without search
                params = [query_limit, query_offset]
                query = """
                SELECT mac_address, device_name, device_type, vendor, notes, created_at
                FROM known_devices 
                ORDER BY device_name
                LIMIT $1 OFFSET $2
                """
                
                results = await self.db_manager.execute_query(query, tuple(params))
                return [dict(row) for row in results] if results else []
            
        except Exception as e:
            if self._should_log_error_details():
                logger.error(self._get_log_message('known_devices_get_failed', error=str(e)))
            return []
    
    async def get_vendor_patterns(self, limit: int = None, offset: int = None, vendor: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get vendor patterns with pagination and filtering"""
        try:
            # Use configured defaults if not provided
            query_limit = limit if limit is not None else self._get_default_limit()
            query_offset = offset if offset is not None else self._get_default_offset()
            
            # Validate limit against maximum
            max_limit = self._get_max_limit()
            if self.pagination_config.get('enable_pagination_validation', True) and query_limit > max_limit:
                query_limit = max_limit
            
            # Build query with optional filtering
            where_clause = ""
            params = []
            
            if vendor:
                where_clause = "WHERE vendor_name ILIKE $1"
                params.append(f"%{vendor}%")
                params.extend([query_limit, query_offset])
                query = f"""
                SELECT oui_pattern, vendor_name, device_category, created_at
                FROM vendor_patterns 
                {where_clause}
                ORDER BY vendor_name
                LIMIT ${len(params)-1} OFFSET ${len(params)}
                """
            else:
                params = [query_limit, query_offset]
                query = """
                SELECT oui_pattern, vendor_name, device_category, created_at
                FROM vendor_patterns 
                ORDER BY vendor_name
                LIMIT $1 OFFSET $2
                """
            
            results = await self.db_manager.execute_query(query, tuple(params))
            return [dict(row) for row in results] if results else []
            
        except Exception as e:
            if self._should_log_error_details():
                logger.error(self._get_log_message('vendor_patterns_get_failed', error=str(e)))
            return []
    
    async def lookup_device_by_mac(self, mac_address: str) -> Optional[Dict[str, Any]]:
        """Lookup device information by MAC address"""
        try:
            return await self.reference_repo.get_known_device(mac_address)
        except Exception as e:
            if self._should_log_error_details():
                logger.error(self._get_log_message('device_lookup_failed', 
                                                 mac_address=mac_address, error=str(e)))
            return None
    
    async def lookup_vendor_by_mac(self, mac_address: str) -> Optional[Dict[str, Any]]:
        """Lookup vendor information by MAC address"""
        try:
            oui_pattern = mac_address[:8]
            return await self.reference_repo.get_vendor_by_oui(oui_pattern)
        except Exception as e:
            if self._should_log_error_details():
                logger.error(self._get_log_message('vendor_lookup_failed', 
                                                 mac_address=mac_address, error=str(e)))
            return None
    
    async def get_device_types(self) -> List[Dict[str, Any]]:
        """Get all available device types"""
        try:
            # Query all distinct device types with configurable filtering
            unknown_type = self.database_config.get('unknown_type_value', 'unknown')
            exclude_unknown = self.database_config.get('exclude_unknown_types', True)
            
            where_clause = "WHERE device_type IS NOT NULL"
            if exclude_unknown:
                where_clause += f" AND device_type != '{unknown_type}'"
            
            query = f"""
            SELECT DISTINCT device_type, COUNT(*) as device_count
            FROM known_devices 
            {where_clause}
            GROUP BY device_type
            ORDER BY device_count DESC, device_type
            """
            results = await self.db_manager.execute_query(query)
            return [{'device_type': row['device_type'], 'count': row['device_count']} for row in results] if results else []
        except Exception as e:
            if self._should_log_error_details():
                logger.error(self._get_log_message('device_types_get_failed', error=str(e)))
            return []
    
    async def get_vendors(self, limit: int = None, offset: int = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get vendor list with pagination and search"""
        try:
            # Use configured defaults if not provided
            query_limit = limit if limit is not None else self._get_default_limit()
            query_offset = offset if offset is not None else self._get_default_offset()
            
            # Validate limit against maximum
            max_limit = self._get_max_limit()
            if self.pagination_config.get('enable_pagination_validation', True) and query_limit > max_limit:
                query_limit = max_limit
            
            # Build query with optional search
            where_clause = ""
            params = []
            
            if search:
                where_clause = "WHERE vendor_name ILIKE $1"
                params.append(f"%{search}%")
                params.extend([query_limit, query_offset])
                query = f"""
                SELECT vendor_name, COUNT(*) as pattern_count, MIN(created_at) as first_seen
                FROM vendor_patterns 
                {where_clause}
                GROUP BY vendor_name
                ORDER BY pattern_count DESC, vendor_name
                LIMIT ${len(params)-1} OFFSET ${len(params)}
                """
            else:
                params = [query_limit, query_offset]
                query = """
                SELECT vendor_name, COUNT(*) as pattern_count, MIN(created_at) as first_seen
                FROM vendor_patterns 
                GROUP BY vendor_name
                ORDER BY pattern_count DESC, vendor_name
                LIMIT $1 OFFSET $2
                """
            
            results = await self.db_manager.execute_query(query, tuple(params))
            return [dict(row) for row in results] if results else []
        except Exception as e:
            if self._should_log_error_details():
                logger.error(self._get_log_message('vendors_get_failed', error=str(e)))
            return []
    
    async def get_reference_stats(self) -> Dict[str, Any]:
        """Get reference database statistics (alias for get_statistics)"""
        return await self.get_statistics() 


# Backward compatibility alias
ReferenceService = ConfigurableReferenceService
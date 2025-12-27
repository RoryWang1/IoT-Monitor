"""
Unified Device Resolution Service   
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

# Import unified configuration manager
from config.unified_config_manager import UnifiedConfigManager

# Initialize configuration manager
config_manager = UnifiedConfigManager()

logger = logging.getLogger(__name__)


class ConfigurableDeviceResolutionService:
    """
    Unified device resolution service with intelligent field-level mapping
    Fully configurable through JSON configuration files
    
    Resolution Priority (configurable):
    1. known_devices table (exact MAC match) - get all available fields
    2. vendor_patterns table (OUI match) - fill missing fields only
    3. Configurable fallback - for any remaining missing fields
    """
    
    def __init__(self, db_manager):
        """Initialize service with database manager and configuration"""
        self.db_manager = db_manager
        self.config = config_manager.get_config()
        self.log_templates = config_manager.get_log_templates()
        
        # Get service-specific configuration
        self.service_config = self.config.get('device_resolution_service', {})
        self.cache_config = self.service_config.get('cache', {})
        self.fallback_config = self.service_config.get('fallback_values', {})
        self.validation_config = self.service_config.get('field_validation', {})
        self.priority_config = self.service_config.get('resolution_priority', {})
        self.batch_config = self.service_config.get('batch_processing', {})
        self.logging_config = self.service_config.get('logging', {})
        self.features_config = self.service_config.get('features', {})
        
        # Initialize cache with configurable settings
        self._resolution_cache = {}
        self._cache_timeout = self.cache_config.get('cache_timeout_seconds', 300)
        self._max_cache_size = self.cache_config.get('max_cache_size', 10000)
        
        if self.logging_config.get('log_resolution_details', True):
            logger.info(self._get_log_message('service_initialized'))
    
    def _get_log_message(self, template_key: str, **kwargs) -> str:
        """Get formatted log message from templates"""
        try:
            template = self.log_templates.get('device_resolution_service', {}).get(template_key, {})
            message_format = template.get('emoji', template_key)
            return message_format.format(**kwargs)
        except Exception:
            return f"[Missing log message: device_resolution_service.{template_key}]"
    
    def _get_unknown_device_name(self) -> str:
        """Get unknown device name from configuration"""
        return self.fallback_config.get('unknown_device_name', 'Unknown')
    
    def _get_unknown_device_vendor(self) -> str:
        """Get unknown device vendor from configuration"""
        return self.fallback_config.get('unknown_device_vendor', 'Unknown')
    
    def _get_unknown_device_type(self) -> str:
        """Get unknown device type from configuration"""
        return self.fallback_config.get('unknown_device_type', 'unknown')
    
    def _get_fallback_source_name(self) -> str:
        """Get fallback source name from configuration"""
        return self.fallback_config.get('fallback_source_name', 'fallback')
    
    def _get_invalid_values(self) -> List[str]:
        """Get list of values considered invalid from configuration"""
        return self.validation_config.get('invalid_values', ['unknown', 'null', '', 'undefined', 'n/a', 'none'])
    
    def _should_cache_hit_log(self) -> bool:
        """Check if cache hit logging is enabled"""
        return self.logging_config.get('log_cache_hits', True)
    
    def _should_cache_miss_log(self) -> bool:
        """Check if cache miss logging is enabled"""  
        return self.logging_config.get('log_cache_misses', True)
    
    def _should_batch_operations_log(self) -> bool:
        """Check if batch operations logging is enabled"""
        return self.logging_config.get('log_batch_operations', True)
    
    def _should_resolution_details_log(self) -> bool:
        """Check if resolution details logging is enabled"""
        return self.logging_config.get('log_resolution_details', True)
    
    def _is_cache_enabled(self) -> bool:
        """Check if caching is enabled"""
        return self.cache_config.get('enable_cache', True)
    
    def _is_debug_mode_enabled(self) -> bool:
        """Check if debug mode is enabled"""
        return self.features_config.get('enable_debug_mode', True)
    
    def _is_detailed_source_mapping_enabled(self) -> bool:
        """Check if detailed source mapping is enabled"""
        return self.features_config.get('enable_detailed_source_mapping', True)
    
    def _cleanup_cache_if_needed(self):
        """Clean up cache if it exceeds maximum size"""
        if len(self._resolution_cache) > self._max_cache_size:
            # Remove oldest entries (simple FIFO)
            items_to_remove = len(self._resolution_cache) - self._max_cache_size + 100  # Remove extra to avoid frequent cleanup
            oldest_keys = list(self._resolution_cache.keys())[:items_to_remove]
            for key in oldest_keys:
                del self._resolution_cache[key]
    
    async def resolve_device_info(self, mac_address: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Resolve complete device information with intelligent field-level fallback
        
        Args:
            mac_address: Device MAC address
            use_cache: Whether to use caching (respects configuration)
            
        Returns:
            Dict containing resolved device information with source tracking
        """
        try:
            # Respect cache configuration
            use_cache = use_cache and self._is_cache_enabled()
            
            # Check cache first
            if use_cache and mac_address in self._resolution_cache:
                cached_data, timestamp = self._resolution_cache[mac_address]
                if (datetime.now() - timestamp).seconds < self._cache_timeout:
                    if self._should_cache_hit_log() and self._is_debug_mode_enabled():
                        logger.debug(self._get_log_message('cache_hit', mac_address=mac_address))
                    return cached_data
            
            # Get fresh resolution
            device_info = await self._resolve_device_with_fallback(mac_address)
            
            # Cache the result
            if use_cache:
                self._cleanup_cache_if_needed()
                self._resolution_cache[mac_address] = (device_info, datetime.now())
                if self._should_cache_miss_log() and self._is_debug_mode_enabled():
                    logger.debug(self._get_log_message('cache_miss', mac_address=mac_address))
            
            return device_info
            
        except Exception as e:
            logger.error(self._get_log_message('resolve_failed', mac_address=mac_address, error=str(e)))
            return self._get_unknown_device_info(mac_address)
    
    async def bulk_resolve_devices(self, mac_addresses: List[str], use_cache: bool = True) -> Dict[str, Dict[str, Any]]:
        """
        Bulk resolve device information with intelligent caching and field-level fallback
        
        Args:
            mac_addresses: List of MAC addresses to resolve
            use_cache: Whether to use caching (respects configuration)
            
        Returns:
            Dict mapping MAC addresses to resolved device information
        """
        try:
            if not mac_addresses:
                return {}
            
            # Respect batch configuration
            max_batch_size = self.batch_config.get('max_batch_size', 100)
            if len(mac_addresses) > max_batch_size:
                mac_addresses = mac_addresses[:max_batch_size]
            
            # Respect cache configuration
            use_cache = use_cache and self._is_cache_enabled()
            
            results = {}
            cache_misses = []
            
            # Check cache for each MAC
            if use_cache:
                for mac in mac_addresses:
                    if mac in self._resolution_cache:
                        cached_data, timestamp = self._resolution_cache[mac]
                        if (datetime.now() - timestamp).seconds < self._cache_timeout:
                            results[mac] = cached_data
                        else:
                            cache_misses.append(mac)
                    else:
                        cache_misses.append(mac)
            else:
                cache_misses = mac_addresses
            
            # Resolve cache misses with batch optimization
            if cache_misses and self.batch_config.get('enable_batch_optimization', True):
                fresh_results = await self._bulk_resolve_with_fallback(cache_misses)
                results.update(fresh_results)
                
                # Update cache
                if use_cache:
                    for mac, info in fresh_results.items():
                        self._cleanup_cache_if_needed()
                        self._resolution_cache[mac] = (info, datetime.now())
            
            if self._should_batch_operations_log():
                logger.info(self._get_log_message('bulk_resolve_success', 
                                                total_count=len(mac_addresses), 
                                                cache_miss_count=len(cache_misses)))
            return results
            
        except Exception as e:
            logger.error(self._get_log_message('bulk_resolve_failed', error=str(e)))
            return {mac: self._get_unknown_device_info(mac) for mac in mac_addresses}
    
    async def _resolve_device_with_fallback(self, mac_address: str) -> Dict[str, Any]:
        """
        Core resolution logic with field-level fallback
        """
        # Initialize result structure
        resolved_info = {
            'mac_address': mac_address,
            'resolvedName': None,
            'resolvedVendor': None,
            'resolvedType': None,
            'sourceMapping': {
                'name_source': 'none',
                'vendor_source': 'none',
                'type_source': 'none'
            }
        }
        
        # Step 1: Try known_devices table (exact MAC match)
        known_device = await self._get_known_device_info(mac_address)
        if known_device:
            # Extract non-empty fields from known_devices
            if self._is_valid_field(known_device.get('device_name')):
                resolved_info['resolvedName'] = known_device['device_name']
                resolved_info['sourceMapping']['name_source'] = 'known_device'
            
            if self._is_valid_field(known_device.get('vendor')):
                resolved_info['resolvedVendor'] = known_device['vendor']
                resolved_info['sourceMapping']['vendor_source'] = 'known_device'
            
            if self._is_valid_field(known_device.get('device_type')):
                resolved_info['resolvedType'] = known_device['device_type']
                resolved_info['sourceMapping']['type_source'] = 'known_device'
            
            if self._should_resolution_details_log() and self._is_debug_mode_enabled():
                logger.debug(self._get_log_message('known_device_found', mac_address=mac_address))
        
        # Step 2: Fill missing fields from vendor_patterns table (OUI match)
        missing_fields = [
            field for field, source in resolved_info['sourceMapping'].items() 
            if source == 'none'
        ]
        
        if missing_fields:
            vendor_pattern = await self._get_vendor_pattern_info(mac_address)
            if vendor_pattern:
                # Fill missing vendor field
                if (resolved_info['sourceMapping']['vendor_source'] == 'none' and 
                    self._is_valid_field(vendor_pattern.get('vendor_name'))):
                    resolved_info['resolvedVendor'] = vendor_pattern['vendor_name']
                    resolved_info['sourceMapping']['vendor_source'] = 'vendor_pattern'
                
                # Fill missing type field
                if (resolved_info['sourceMapping']['type_source'] == 'none' and 
                    self._is_valid_field(vendor_pattern.get('device_category'))):
                    resolved_info['resolvedType'] = vendor_pattern['device_category']
                    resolved_info['sourceMapping']['type_source'] = 'vendor_pattern'
                
                if self._should_resolution_details_log() and self._is_debug_mode_enabled():
                    logger.debug(self._get_log_message('vendor_pattern_found', mac_address=mac_address))
        
        # Step 3: Set configured fallback values for any remaining missing fields
        if not resolved_info['resolvedName']:
            resolved_info['resolvedName'] = self._get_unknown_device_name()
            resolved_info['sourceMapping']['name_source'] = self._get_fallback_source_name()
        
        if not resolved_info['resolvedVendor']:
            resolved_info['resolvedVendor'] = self._get_unknown_device_vendor()
            resolved_info['sourceMapping']['vendor_source'] = self._get_fallback_source_name()
        
        if not resolved_info['resolvedType']:
            resolved_info['resolvedType'] = self._get_unknown_device_type()
            resolved_info['sourceMapping']['type_source'] = self._get_fallback_source_name()
        
        # Determine overall resolution source for backward compatibility
        resolved_info['source'] = self._determine_primary_source(resolved_info['sourceMapping'])
        
        if self._should_resolution_details_log() and self._is_debug_mode_enabled():
            logger.debug(self._get_log_message('resolution_complete', 
                                             mac_address=mac_address, 
                                             source_info=str(resolved_info['sourceMapping'])))
        return resolved_info
    
    async def _bulk_resolve_with_fallback(self, mac_addresses: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Optimized bulk resolution with field-level fallback
        """
        results = {}
        
        # Step 1: Batch query known_devices
        known_devices_map = await self._batch_get_known_devices(mac_addresses)
        
        # Step 2: Batch query vendor_patterns for all MACs (we'll filter usage later)
        vendor_patterns_map = await self._batch_get_vendor_patterns(mac_addresses)
        
        # Step 3: Process each MAC with field-level fallback
        for mac in mac_addresses:
            resolved_info = {
                'mac_address': mac,
                'resolvedName': None,
                'resolvedVendor': None,
                'resolvedType': None,
                'sourceMapping': {
                    'name_source': 'none',
                    'vendor_source': 'none',
                    'type_source': 'none'
                }
            }
            
            # Apply known_devices data
            known_device = known_devices_map.get(mac)
            if known_device:
                if self._is_valid_field(known_device.get('device_name')):
                    resolved_info['resolvedName'] = known_device['device_name']
                    resolved_info['sourceMapping']['name_source'] = 'known_device'
                
                if self._is_valid_field(known_device.get('vendor')):
                    resolved_info['resolvedVendor'] = known_device['vendor']
                    resolved_info['sourceMapping']['vendor_source'] = 'known_device'
                
                if self._is_valid_field(known_device.get('device_type')):
                    resolved_info['resolvedType'] = known_device['device_type']
                    resolved_info['sourceMapping']['type_source'] = 'known_device'
            
            # Apply vendor_patterns data for missing fields only
            vendor_pattern = vendor_patterns_map.get(mac[:8])  # OUI match
            if vendor_pattern:
                if (resolved_info['sourceMapping']['vendor_source'] == 'none' and 
                    self._is_valid_field(vendor_pattern.get('vendor_name'))):
                    resolved_info['resolvedVendor'] = vendor_pattern['vendor_name']
                    resolved_info['sourceMapping']['vendor_source'] = 'vendor_pattern'
                
                if (resolved_info['sourceMapping']['type_source'] == 'none' and 
                    self._is_valid_field(vendor_pattern.get('device_category'))):
                    resolved_info['resolvedType'] = vendor_pattern['device_category']
                    resolved_info['sourceMapping']['type_source'] = 'vendor_pattern'
            
            # Set configured fallback values for remaining missing fields
            if not resolved_info['resolvedName']:
                resolved_info['resolvedName'] = self._get_unknown_device_name()
                resolved_info['sourceMapping']['name_source'] = self._get_fallback_source_name()
            
            if not resolved_info['resolvedVendor']:
                resolved_info['resolvedVendor'] = self._get_unknown_device_vendor()
                resolved_info['sourceMapping']['vendor_source'] = self._get_fallback_source_name()
            
            if not resolved_info['resolvedType']:
                resolved_info['resolvedType'] = self._get_unknown_device_type()
                resolved_info['sourceMapping']['type_source'] = self._get_fallback_source_name()
            
            # Determine primary source for backward compatibility
            resolved_info['source'] = self._determine_primary_source(resolved_info['sourceMapping'])
            
            results[mac] = resolved_info
        
        return results
    
    async def _get_known_device_info(self, mac_address: str) -> Optional[Dict[str, Any]]:
        """Get device info from known_devices table with case-insensitive MAC address matching"""
        try:
            result = await self.db_manager.execute_query(
                "SELECT device_name, device_type, vendor, notes FROM known_devices WHERE UPPER(mac_address) = UPPER($1)",
                (mac_address,)
            )
            return result[0] if result else None
        except Exception as e:
            if self._is_debug_mode_enabled():
                logger.debug(f"No known device found for {mac_address}: {e}")
            return None
    
    async def _get_vendor_pattern_info(self, mac_address: str) -> Optional[Dict[str, Any]]:
        """Get vendor info from vendor_patterns table using OUI"""
        try:
            oui = mac_address[:8]
            result = await self.db_manager.execute_query(
                "SELECT vendor_name, device_category FROM vendor_patterns WHERE oui_pattern = $1",
                (oui,)
            )
            return result[0] if result else None
        except Exception as e:
            if self._is_debug_mode_enabled():
                logger.debug(f"No vendor pattern found for {mac_address}: {e}")
            return None
    
    async def _batch_get_known_devices(self, mac_addresses: List[str]) -> Dict[str, Dict[str, Any]]:
        """Batch query known_devices table with case-insensitive MAC address matching"""
        try:
            if not mac_addresses:
                return {}
            
            # Create case-insensitive matching conditions
            conditions = []
            params = []
            for i, mac in enumerate(mac_addresses):
                conditions.append(f"UPPER(mac_address) = UPPER(${i+1})")
                params.append(mac)
            
            query = f"""
                SELECT mac_address, device_name, device_type, vendor, notes
                FROM known_devices 
                WHERE {' OR '.join(conditions)}
            """
            
            results = await self.db_manager.execute_query(query, tuple(params))
            # Create lookup by uppercase MAC for consistent mapping
            result_map = {}
            for row in results:
                # Map both the original MAC from database and any input MAC that matches
                for input_mac in mac_addresses:
                    if row['mac_address'].upper() == input_mac.upper():
                        result_map[input_mac] = row
                        break
            return result_map
        
        except Exception as e:
            logger.error(self._get_log_message('known_devices_batch_failed', error=str(e)))
            return {}
    
    async def _batch_get_vendor_patterns(self, mac_addresses: List[str]) -> Dict[str, Dict[str, Any]]:
        """Batch query vendor_patterns table"""
        try:
            if not mac_addresses:
                return {}
            
            # Extract unique OUI patterns
            oui_patterns = list(set([mac[:8] for mac in mac_addresses]))
            placeholders = ','.join([f'${i+1}' for i in range(len(oui_patterns))])
            
            query = f"""
                SELECT oui_pattern, vendor_name, device_category
                FROM vendor_patterns 
                WHERE oui_pattern IN ({placeholders})
            """
            
            results = await self.db_manager.execute_query(query, tuple(oui_patterns))
            return {row['oui_pattern']: row for row in results} if results else {}
        
        except Exception as e:
            logger.error(self._get_log_message('vendor_patterns_batch_failed', error=str(e)))
            return {}
    
    def _is_valid_field(self, value: Any) -> bool:
        """Check if a field value is valid (configurable validation)"""
        if value is None:
            return False
        
        if isinstance(value, str):
            cleaned = value.strip() if self.validation_config.get('trim_whitespace', True) else value
            if not cleaned:
                return False
            
            # Use case-sensitive or case-insensitive validation
            invalid_values = self._get_invalid_values()
            if self.validation_config.get('case_sensitive_validation', False):
                return cleaned not in invalid_values
            else:
                return cleaned.lower() not in [v.lower() for v in invalid_values]
        
        return bool(value)
    
    def _determine_primary_source(self, source_mapping: Dict[str, str]) -> str:
        """Determine primary resolution source for backward compatibility"""
        sources = list(source_mapping.values())
        if 'known_device' in sources:
            return 'known_device'
        elif 'vendor_pattern' in sources:
            return 'vendor_pattern'
        else:
            return self._get_fallback_source_name()
    
    def _get_unknown_device_info(self, mac_address: str) -> Dict[str, Any]:
        """Return configured unknown device information"""
        return {
            'mac_address': mac_address,
            'resolvedName': self._get_unknown_device_name(),
            'resolvedVendor': self._get_unknown_device_vendor(),
            'resolvedType': self._get_unknown_device_type(),
            'source': self._get_fallback_source_name(),
            'sourceMapping': {
                'name_source': self._get_fallback_source_name(),
                'vendor_source': self._get_fallback_source_name(),
                'type_source': self._get_fallback_source_name()
            }
        }
    
    def clear_cache(self):
        """Clear the resolution cache"""
        self._resolution_cache.clear()
        if self.logging_config.get('log_resolution_details', True):
            logger.info(self._get_log_message('cache_cleared'))
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        current_time = datetime.now()
        valid_entries = 0
        
        for mac, (data, timestamp) in self._resolution_cache.items():
            if (current_time - timestamp).seconds < self._cache_timeout:
                valid_entries += 1
        
        stats = {
            'total_entries': len(self._resolution_cache),
            'valid_entries': valid_entries,
            'cache_timeout': self._cache_timeout,
            'max_cache_size': self._max_cache_size,
            'cache_enabled': self._is_cache_enabled()
        }
        
        if self.cache_config.get('enable_cache_statistics', True):
            stats.update({
                'hit_rate_estimate': f"{(valid_entries / max(1, len(self._resolution_cache))) * 100:.1f}%"
            })
        
        return stats


# Backward compatibility alias
DeviceResolutionService = ConfigurableDeviceResolutionService


# Global service instance getter function
def get_device_resolution_service(db_manager) -> ConfigurableDeviceResolutionService:
    """Get device resolution service instance"""
    return ConfigurableDeviceResolutionService(db_manager) 
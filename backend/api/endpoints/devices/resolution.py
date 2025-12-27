"""
Configurable Unified Device Resolution API Endpoint
Provides unified device mapping with field-level fallback logic and configurable parameters
"""

import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

# Setup unified path configuration
from ...common.path_config import setup_project_paths
setup_project_paths()

from config.unified_config_manager import get_config, get_log_message
from ...common.dependencies import get_database_service_instance

logger = logging.getLogger(__name__)

class ConfigurableDeviceResolutionAPI:
    """Configured device parsing API"""
    
    def __init__(self):
        self.config_namespace = 'device_resolution_api'
        
    def _get_resolution_config(self) -> Dict[str, Any]:
        """Get the resolution configuration"""
        return {
            'use_cache_default': get_config(f'{self.config_namespace}.resolution.use_cache_default', True, f'{self.config_namespace}.resolution'),
            'enable_bulk_optimization': get_config(f'{self.config_namespace}.resolution.enable_bulk_optimization', True, f'{self.config_namespace}.resolution'),
            'max_bulk_size': get_config(f'{self.config_namespace}.resolution.max_bulk_size', 100, f'{self.config_namespace}.resolution'),
            'cache_statistics_enabled': get_config(f'{self.config_namespace}.resolution.cache_statistics_enabled', True, f'{self.config_namespace}.resolution')
        }
    
    def _get_response_field_mapping(self) -> Dict[str, str]:
        """Get the response field mapping configuration"""
        return get_config(f'{self.config_namespace}.response_fields', {
            'mac_address_field': 'mac_address',
            'resolvedName_field': 'resolvedName',
            'resolvedVendor_field': 'resolvedVendor',
            'resolvedType_field': 'resolvedType',
            'source_field': 'source',
            'sourceMapping_field': 'sourceMapping',
            'devices_field': 'devices',
            'summary_field': 'summary',
            'cache_stats_field': 'cache_stats',
            'cache_health_field': 'cache_health'
        }, f'{self.config_namespace}.response_fields')
    
    def _get_error_messages(self) -> Dict[str, str]:
        """Get the error messages configuration"""
        return get_config(f'{self.config_namespace}.error_messages', {
            'device_not_found': "Could not resolve device information for MAC: {mac_address}",
            'bulk_resolution_failed': "Failed to bulk resolve device information",
            'cache_stats_failed': "Failed to get cache statistics",
            'cache_clear_failed': "Failed to clear cache",
            'invalid_bulk_request': "Invalid bulk resolution request: {error}",
            'resolution_timeout': "Device resolution timeout: {mac_address}"
        }, f'{self.config_namespace}.error_messages')
    
    async def resolve_single_device(self, mac_address: str, use_cache: bool, database_service) -> Dict[str, Any]:
        """Configurable single device resolution"""
        try:
            # Configurable API call log
            if get_config(f'{self.config_namespace}.logging.log_resolution_calls', True, f'{self.config_namespace}.logging'):
                logger.info(get_log_message('device_resolution_api', 'single_resolution_started', 
                                           component='device_resolution.api',
                                           mac_address=mac_address, use_cache=use_cache))
            
            device_info = await database_service.resolve_device_info(mac_address, use_cache=use_cache)
            
            if not device_info:
                error_messages = self._get_error_messages()
                raise HTTPException(
                    status_code=404,
                    detail=error_messages['device_not_found'].format(mac_address=mac_address)
                )
            
            # Configurable success log
            if get_config(f'{self.config_namespace}.logging.log_resolution_success', True, f'{self.config_namespace}.logging'):
                logger.info(get_log_message('device_resolution_api', 'single_resolution_completed', 
                                           component='device_resolution.api',
                                           mac_address=mac_address, source=device_info.get('source', 'unknown')))
            return device_info
            
        except HTTPException:
            raise
        except Exception as e:
            # Configurable error log
            if get_config(f'{self.config_namespace}.logging.log_resolution_errors', True, f'{self.config_namespace}.logging'):
                logger.error(get_log_message('device_resolution_api', 'single_resolution_failed', 
                                            component='device_resolution.api',
                                            mac_address=mac_address, error=str(e)))
            raise
    
    async def resolve_bulk_devices(self, mac_addresses: List[str], use_cache: bool, database_service) -> Dict[str, Any]:
        """Configurable bulk device resolution"""
        try:
            resolution_config = self._get_resolution_config()
            error_messages = self._get_error_messages()
            
            # Configurable bulk resolution log
            if get_config(f'{self.config_namespace}.logging.log_bulk_calls', True, f'{self.config_namespace}.logging'):
                logger.info(get_log_message('device_resolution_api', 'bulk_resolution_started', 
                                           component='device_resolution.api',
                                           device_count=len(mac_addresses), use_cache=use_cache))
            
            if not mac_addresses:
                return {"devices": {}, "summary": {"total": 0, "resolved": 0, "cache_hits": 0}}
            
            # Validate bulk size limit
            if len(mac_addresses) > resolution_config['max_bulk_size']:
                raise HTTPException(
                    status_code=400,
                    detail=error_messages['invalid_bulk_request'].format(
                        error=f"Request size {len(mac_addresses)} exceeds limit {resolution_config['max_bulk_size']}"
                    )
                )
            
            device_resolutions = await database_service.bulk_resolve_devices(mac_addresses, use_cache=use_cache)
            
            # Build the response data
            field_mapping = self._get_response_field_mapping()
            resolved_devices = {}
            for mac, info in device_resolutions.items():
                resolved_devices[mac] = {
                    field_mapping['mac_address_field']: info['mac_address'],
                    field_mapping['resolvedName_field']: info['resolvedName'],
                    field_mapping['resolvedVendor_field']: info['resolvedVendor'],
                    field_mapping['resolvedType_field']: info['resolvedType'],
                    field_mapping['source_field']: info['source'],
                    field_mapping['sourceMapping_field']: info.get('sourceMapping', {})
                }
            
            # Generate statistics
            source_counts = {}
            for info in device_resolutions.values():
                source = info.get('source', 'unknown')
                source_counts[source] = source_counts.get(source, 0) + 1
            
            summary = {
                "total": len(mac_addresses),
                "resolved": len(device_resolutions),
                "source_breakdown": source_counts
            }
            
            # Configurable success log
            if get_config(f'{self.config_namespace}.logging.log_bulk_success', True, f'{self.config_namespace}.logging'):
                logger.info(get_log_message('device_resolution_api', 'bulk_resolution_completed', 
                                           component='device_resolution.api',
                                           total=summary['total'], resolved=summary['resolved']))
            
            return {
                field_mapping['devices_field']: resolved_devices,
                field_mapping['summary_field']: summary
            }
            
        except HTTPException:
            raise
        except Exception as e:
            # Configurable error log
            if get_config(f'{self.config_namespace}.logging.log_bulk_errors', True, f'{self.config_namespace}.logging'):
                logger.error(get_log_message('device_resolution_api', 'bulk_resolution_failed', 
                                            component='device_resolution.api',
                                            error=str(e)))
            raise
    
    async def get_cache_statistics(self, database_service) -> Dict[str, Any]:
        """Configurable cache statistics retrieval"""
        try:
            resolution_config = self._get_resolution_config()
            if not resolution_config['cache_statistics_enabled']:
                return {"message": "Cache statistics disabled"}
            
            # Configurable cache statistics log
            if get_config(f'{self.config_namespace}.logging.log_cache_operations', True, f'{self.config_namespace}.logging'):
                logger.info(get_log_message('device_resolution_api', 'cache_stats_request', 
                                           component='device_resolution.api'))
            
            stats = database_service.get_device_resolution_cache_stats()
            field_mapping = self._get_response_field_mapping()
            
            return {
                field_mapping['cache_stats_field']: stats,
                field_mapping['cache_health_field']: "healthy" if stats['valid_entries'] > 0 else "empty"
            }
            
        except Exception as e:
            # Configurable error log
            if get_config(f'{self.config_namespace}.logging.log_cache_errors', True, f'{self.config_namespace}.logging'):
                logger.error(get_log_message('device_resolution_api', 'cache_stats_failed', 
                                            component='device_resolution.api',
                                            error=str(e)))
            raise
    
    async def clear_cache(self, database_service) -> Dict[str, Any]:
        """Configurable cache clearing"""
        try:
            # Configurable cache clearing log
            if get_config(f'{self.config_namespace}.logging.log_cache_operations', True, f'{self.config_namespace}.logging'):
                logger.info(get_log_message('device_resolution_api', 'cache_clear_request', 
                                           component='device_resolution.api'))
            
            database_service.clear_device_resolution_cache()
            
            return {
                "message": "Device resolution cache cleared successfully",
                "timestamp": "2025-01-27T12:00:00Z"
            }
            
        except Exception as e:
            # Configurable error log
            if get_config(f'{self.config_namespace}.logging.log_cache_errors', True, f'{self.config_namespace}.logging'):
                logger.error(get_log_message('device_resolution_api', 'cache_clear_failed', 
                                            component='device_resolution.api',
                                            error=str(e)))
            raise

# Create the configurable API instance
configurable_api = ConfigurableDeviceResolutionAPI()

router = APIRouter()

# Request/Response models
class DeviceResolutionRequest(BaseModel):
    mac_address: str

class BulkDeviceResolutionRequest(BaseModel):
    mac_addresses: List[str]

class DeviceResolutionResponse(BaseModel):
    mac_address: str
    resolvedName: str
    resolvedVendor: str
    resolvedType: str
    source: str
    sourceMapping: Dict[str, str]

@router.post("/resolve", response_model=DeviceResolutionResponse)
async def resolve_device_info(
    request: DeviceResolutionRequest,
    use_cache: bool = Query(default=None, description="Whether to use caching"),
    database_service = Depends(get_database_service_instance)
):
    """
    Configurable device information resolution API endpoint
    Resolve device information with intelligent field-level fallback and configurable parameters
    
    Resolution Priority:
    1. known_devices table (exact MAC match) - get all available fields
    2. vendor_patterns table (OUI match) - fill missing fields only
    3. Unknown fallback - for any remaining missing fields
    """
    try:
        # Use the configurable defaults
        resolution_config = configurable_api._get_resolution_config()
        if use_cache is None:
            use_cache = resolution_config['use_cache_default']
        
        # Call the configurable API method
        device_info = await configurable_api.resolve_single_device(
            request.mac_address, use_cache, database_service
        )
        
        field_mapping = configurable_api._get_response_field_mapping()
        return DeviceResolutionResponse(
            mac_address=device_info[field_mapping['mac_address_field']],
            resolvedName=device_info[field_mapping['resolvedName_field']],
            resolvedVendor=device_info[field_mapping['resolvedVendor_field']],
            resolvedType=device_info[field_mapping['resolvedType_field']],
            source=device_info[field_mapping['source_field']],
            sourceMapping=device_info.get(field_mapping['sourceMapping_field'], {})
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_messages = configurable_api._get_error_messages()
        raise HTTPException(
            status_code=500,
            detail=error_messages['resolution_timeout'].format(mac_address=request.mac_address)
        )

@router.post("/bulk-resolve")
async def bulk_resolve_devices(
    request: BulkDeviceResolutionRequest,
    use_cache: bool = Query(default=None, description="Whether to use caching"),
    database_service = Depends(get_database_service_instance)
):
    """
    Configurable bulk device resolution API endpoint
    Bulk resolve device information with intelligent field-level fallback and configurable optimization
    
    This endpoint is optimized for resolving multiple devices at once
    and provides better performance than individual resolution calls.
    """
    try:
        # Use the configurable defaults
        resolution_config = configurable_api._get_resolution_config()
        if use_cache is None:
            use_cache = resolution_config['use_cache_default']
        
        # Call the configurable API method
        return await configurable_api.resolve_bulk_devices(
            request.mac_addresses, use_cache, database_service
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_messages = configurable_api._get_error_messages()
        raise HTTPException(
            status_code=500,
            detail=error_messages['bulk_resolution_failed']
        )

@router.get("/cache/stats")
async def get_cache_stats(
    database_service = Depends(get_database_service_instance)
):
    """Configurable device resolution cache statistics API endpoint"""
    try:
        return await configurable_api.get_cache_statistics(database_service)
    except Exception as e:
        error_messages = configurable_api._get_error_messages()
        raise HTTPException(
            status_code=500,
            detail=error_messages['cache_stats_failed']
        )

@router.post("/cache/clear")
async def clear_cache(
    database_service = Depends(get_database_service_instance)
):
    """Configurable device resolution cache clearing API endpoint"""
    try:
        return await configurable_api.clear_cache(database_service)
    except Exception as e:
        error_messages = configurable_api._get_error_messages()
        raise HTTPException(
            status_code=500,
            detail=error_messages['cache_clear_failed']
        )

 
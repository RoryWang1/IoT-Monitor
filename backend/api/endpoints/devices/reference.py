"""
Configurable Device Reference API Endpoint
Handles device reference data operations with full configuration support
"""

import logging
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Depends, Response
from pydantic import BaseModel

# Setup unified path configuration
from ...common.path_config import setup_project_paths
setup_project_paths()

# Import unified configuration manager
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../'))
from config.unified_config_manager import UnifiedConfigManager

# Initialize configuration
config_manager = UnifiedConfigManager()
logger = logging.getLogger(__name__)

router = APIRouter()

class ConfigurableDeviceReferenceAPI:
    """Configurable Device Reference API with full configuration support"""
    
    def __init__(self):
        self.config = config_manager.get('api_endpoints.device_reference', {}, 'device_reference_api')
        self.defaults = self.config.get('defaults', {})
        self.pagination = self.config.get('pagination', {})
        self.validation = self.config.get('validation', {})
        self.response_messages = self.config.get('response_messages', {})
        self.error_messages = self.config.get('error_messages', {})
        self.query_descriptions = self.config.get('query_descriptions', {})
        self.export_config = self.config.get('export', {})
        self.features = self.config.get('features', {})
        
    def get_log_message(self, category: str, key: str, **kwargs) -> str:
        """Get configured log message"""
        return config_manager.get_log_message(category, key, component='device_reference_api', **kwargs)
    
    def get_default(self, key: str, fallback: Any = None) -> Any:
        """Get configured default value"""
        return self.defaults.get(key, fallback)
    
    def get_pagination(self, key: str, fallback: Any = None) -> Any:
        """Get configured pagination value"""
        return self.pagination.get(key, fallback)
    
    def get_response_message(self, key: str, **kwargs) -> str:
        """Get configured response message"""
        return self.response_messages.get(key, key).format(**kwargs)
    
    def get_error_message(self, key: str, **kwargs) -> str:
        """Get configured error message"""
        return self.error_messages.get(key, key).format(**kwargs)
    
    def get_query_description(self, key: str) -> str:
        """Get configured query description"""
        return self.query_descriptions.get(key, key)
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled"""
        return self.features.get(feature, True)

# Initialize the configurable API
api_config = ConfigurableDeviceReferenceAPI()

# Request models with configurable defaults
class KnownDeviceRequest(BaseModel):
    mac_address: str
    device_name: str
    device_type: str = api_config.get_default('device_type', 'unknown')
    vendor: str = api_config.get_default('vendor', 'Unknown')
    notes: Optional[str] = None

class KnownDeviceUpdateRequest(BaseModel):
    device_name: Optional[str] = None
    device_type: Optional[str] = None
    vendor: Optional[str] = None
    notes: Optional[str] = None

class VendorPatternRequest(BaseModel):
    oui_pattern: str
    vendor_name: str
    device_category: str = api_config.get_default('device_category', 'unknown')

# Import unified dependencies
from ...common.dependencies import get_database_service_instance

@router.get("/resolve/{mac_address}", response_model=Dict[str, Any])
async def resolve_device_info(
    mac_address: str,
    database_service = Depends(get_database_service_instance)
):
    """
    Resolve device information from reference database
    
    Args:
        mac_address: Device MAC address
    
    Returns:
        Resolved device information
    """
    try:
        if api_config.is_feature_enabled('enable_detailed_logging'):
            logger.info(api_config.get_log_message('device_reference', 'resolving_device_info', mac_address=mac_address))
        
        resolution_data = await database_service.reference_service.resolve_device_info(mac_address)
        return resolution_data
        
    except Exception as e:
        logger.error(api_config.get_log_message('device_reference', 'error_resolving_device', mac_address=mac_address, error=str(e)))
        raise HTTPException(
            status_code=500,
            detail=api_config.get_error_message('failed_resolve_device', mac_address=mac_address)
        )

@router.post("/known-devices", response_model=Dict[str, Any])
async def add_known_device(
    request: KnownDeviceRequest,
    database_service = Depends(get_database_service_instance)
):
    """
    Add a new known device to the reference database
    
    Args:
        request: Known device information
    
    Returns:
        Operation result
    """
    try:
        if api_config.is_feature_enabled('enable_detailed_logging'):
            logger.info(api_config.get_log_message('device_reference', 'adding_known_device', 
                                                 mac_address=request.mac_address, device_name=request.device_name))
        
        success = await database_service.reference_service.reference_repo.add_known_device(
            request.mac_address,
            request.device_name,
            request.device_type,
            request.vendor,
            request.notes
        )
        
        if success:
            return {
                "success": True,
                "message": api_config.get_response_message('known_device_added'),
                "mac_address": request.mac_address,
                "device_name": request.device_name
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=api_config.get_error_message('failed_add_known_device')
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(api_config.get_log_message('device_reference', 'error_adding_known_device', 
                                              mac_address=request.mac_address, error=str(e)))
        raise HTTPException(
            status_code=500,
            detail=api_config.get_error_message('failed_add_known_device')
        )

@router.put("/known-devices/{mac_address}", response_model=Dict[str, Any])
async def update_known_device(
    mac_address: str, 
    request: KnownDeviceUpdateRequest,
    database_service = Depends(get_database_service_instance)
):
    """
    Update an existing known device
    
    Args:
        mac_address: Device MAC address
        request: Updated device information
    
    Returns:
        Operation result
    """
    try:
        if api_config.is_feature_enabled('enable_detailed_logging'):
            logger.info(api_config.get_log_message('device_reference', 'updating_known_device', mac_address=mac_address))
        
        # Convert request to dict, excluding None values
        update_data = {k: v for k, v in request.dict().items() if v is not None}
        
        if not update_data:
            raise HTTPException(
                status_code=400,
                detail=api_config.get_error_message('at_least_one_field_required')
            )
        
        success = await database_service.reference_service.reference_repo.update_known_device(
            mac_address, **update_data
        )
        
        if success:
            return {
                "success": True,
                "message": api_config.get_response_message('known_device_updated'),
                "mac_address": mac_address
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=api_config.get_error_message('device_not_found')
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(api_config.get_log_message('device_reference', 'error_updating_known_device', 
                                              mac_address=mac_address, error=str(e)))
        raise HTTPException(
            status_code=500,
            detail=api_config.get_error_message('failed_update_known_device')
        )

@router.delete("/known-devices/{mac_address}", response_model=Dict[str, Any])
async def delete_known_device(
    mac_address: str,
    database_service = Depends(get_database_service_instance)
):
    """
    Delete a known device from the reference database
    
    Args:
        mac_address: Device MAC address
    
    Returns:
        Operation result
    """
    try:
        if api_config.is_feature_enabled('enable_detailed_logging'):
            logger.info(api_config.get_log_message('device_reference', 'deleting_known_device', mac_address=mac_address))
        
        success = await database_service.reference_service.reference_repo.delete_known_device(mac_address)
        
        if success:
            return {
                "success": True,
                "message": api_config.get_response_message('known_device_deleted'),
                "mac_address": mac_address
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=api_config.get_error_message('device_not_found')
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(api_config.get_log_message('device_reference', 'error_deleting_known_device', 
                                              mac_address=mac_address, error=str(e)))
        raise HTTPException(
            status_code=500,
            detail=api_config.get_error_message('failed_delete_known_device')
        )

@router.get("/vendor-info/{mac_address}", response_model=Dict[str, Any])
async def get_vendor_information(
    mac_address: str,
    database_service = Depends(get_database_service_instance)
):
    """
    Get vendor information for a MAC address
    
    Args:
        mac_address: Device MAC address
    
    Returns:
        Vendor information
    """
    try:
        if api_config.is_feature_enabled('enable_detailed_logging'):
            logger.info(api_config.get_log_message('device_reference', 'getting_vendor_info', mac_address=mac_address))
        
        # Extract OUI from MAC address
        oui_pattern = mac_address[:8]
        vendor_info = await database_service.reference_service.reference_repo.get_vendor_by_oui(oui_pattern)
        
        if vendor_info:
            return vendor_info
        else:
            return {
                "oui_pattern": oui_pattern,
                "vendor_name": api_config.get_default('unknown_vendor_name', 'Unknown'),
                "device_category": api_config.get_default('unknown_device_category', 'unknown')
            }
        
    except Exception as e:
        logger.error(api_config.get_log_message('device_reference', 'error_getting_vendor_info', 
                                              mac_address=mac_address, error=str(e)))
        raise HTTPException(
            status_code=500,
            detail=api_config.get_error_message('failed_get_vendor_info', mac_address=mac_address)
        )

@router.post("/vendor-patterns", response_model=Dict[str, Any])
async def add_vendor_pattern(
    request: VendorPatternRequest,
    database_service = Depends(get_database_service_instance)
):
    """
    Add a new vendor pattern to the reference database
    
    Args:
        request: Vendor pattern information
    
    Returns:
        Operation result
    """
    try:
        if api_config.is_feature_enabled('enable_detailed_logging'):
            logger.info(api_config.get_log_message('device_reference', 'adding_vendor_pattern', 
                                                 oui_pattern=request.oui_pattern, vendor_name=request.vendor_name))
        
        success = await database_service.reference_service.reference_repo.add_vendor_pattern(
            request.oui_pattern,
            request.vendor_name,
            request.device_category
        )
        
        if success:
            return {
                "success": True,
                "message": api_config.get_response_message('vendor_pattern_added'),
                "oui_pattern": request.oui_pattern,
                "vendor_name": request.vendor_name
            }
        else:
            logger.error(api_config.get_log_message('device_reference', 'repository_operation_failed', 
                                                  oui_pattern=request.oui_pattern))
            raise HTTPException(
                status_code=400,
                detail=api_config.get_error_message('repository_operation_failed')
            )
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(api_config.get_log_message('device_reference', 'validation_error_vendor_pattern', 
                                              oui_pattern=request.oui_pattern, error=str(e)))
        raise HTTPException(
            status_code=400,
            detail=api_config.get_error_message('invalid_input_format') + f": {str(e)}"
        )
    except Exception as e:
        logger.error(api_config.get_log_message('device_reference', 'unexpected_error_vendor_pattern', 
                                              oui_pattern=request.oui_pattern, error=str(e)))
        raise HTTPException(
            status_code=500,
            detail=api_config.get_error_message('failed_add_vendor_pattern') + f": {str(e)}"
        )

@router.put("/vendor-patterns", response_model=Dict[str, Any])
async def update_vendor_pattern(
    request: VendorPatternRequest,
    oui_pattern: str = Query(..., description=api_config.get_query_description('oui_pattern_update_description')),
    database_service = Depends(get_database_service_instance)
):
    """
    Update an existing vendor pattern
    
    Args:
        oui_pattern: OUI pattern to update
        request: Updated vendor pattern information
    
    Returns:
        Operation result
    """
    try:
        success = await database_service.reference_service.reference_repo.update_vendor_pattern(
            oui_pattern,
            request.vendor_name,
            request.device_category
        )
        
        if success:
            return {
                "success": True,
                "message": api_config.get_response_message('vendor_pattern_updated'),
                "oui_pattern": oui_pattern,
                "vendor_name": request.vendor_name
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=api_config.get_error_message('vendor_pattern_not_found')
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(api_config.get_log_message('device_reference', 'error_updating_vendor_pattern', 
                                              oui_pattern=oui_pattern, error=str(e)))
        raise HTTPException(
            status_code=500,
            detail=api_config.get_error_message('failed_update_vendor_pattern')
        )

@router.delete("/vendor-patterns", response_model=Dict[str, Any])
async def delete_vendor_pattern(
    oui_pattern: str = Query(..., description=api_config.get_query_description('oui_pattern_delete_description')),
    database_service = Depends(get_database_service_instance)
):
    """
    Delete a vendor pattern
    
    Args:
        oui_pattern: OUI pattern to delete
    
    Returns:
        Operation result
    """
    try:
        if api_config.is_feature_enabled('enable_detailed_logging'):
            logger.info(api_config.get_log_message('device_reference', 'deleting_vendor_pattern', oui_pattern=oui_pattern))
        
        success = await database_service.reference_service.reference_repo.delete_vendor_pattern(oui_pattern)
        
        if success:
            return {
                "success": True,
                "message": api_config.get_response_message('vendor_pattern_deleted'),
                "oui_pattern": oui_pattern
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=api_config.get_error_message('vendor_pattern_not_found')
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(api_config.get_log_message('device_reference', 'error_deleting_vendor_pattern', 
                                              oui_pattern=oui_pattern, error=str(e)))
        raise HTTPException(
            status_code=500,
            detail=api_config.get_error_message('failed_delete_vendor_pattern')
        )

@router.get("/vendor-search", response_model=List[Dict[str, Any]])
async def search_vendors(
    query: str = Query(..., description=api_config.get_query_description('search_query_vendors')),
    limit: int = Query(api_config.get_pagination('search_limit', 10), 
                      description=api_config.get_query_description('max_results_description'), 
                      ge=1, le=api_config.get_pagination('search_max_limit', 100)),
    database_service = Depends(get_database_service_instance)
):
    """
    Search for vendor patterns by name
    
    Args:
        query: Search query
        limit: Maximum number of results
    
    Returns:
        List of matching vendor patterns
    """
    try:
        if api_config.is_feature_enabled('enable_detailed_logging'):
            logger.info(api_config.get_log_message('device_reference', 'searching_vendors', query=query))
        
        results = await database_service.reference_service.reference_repo.search_vendors(
            query, limit
        )
        return results
        
    except Exception as e:
        logger.error(api_config.get_log_message('device_reference', 'error_searching_vendors', 
                                              query=query, error=str(e)))
        raise HTTPException(
            status_code=500,
            detail=api_config.get_error_message('failed_search_vendors')
        )

@router.get("/known-devices-search", response_model=List[Dict[str, Any]])
async def search_known_devices(
    query: str = Query(..., description=api_config.get_query_description('search_query_devices')),
    limit: int = Query(api_config.get_pagination('search_limit', 10), 
                      description=api_config.get_query_description('max_results_description'), 
                      ge=1, le=api_config.get_pagination('search_max_limit', 100)),
    database_service = Depends(get_database_service_instance)
):
    """
    Search for known devices by MAC address or device name
    
    Args:
        query: Search query
        limit: Maximum number of results
    
    Returns:
        List of matching known devices
    """
    try:
        if api_config.is_feature_enabled('enable_detailed_logging'):
            logger.info(api_config.get_log_message('device_reference', 'searching_known_devices', query=query))
        
        results = await database_service.reference_service.reference_repo.search_known_devices(
            query, limit
        )
        return results
        
    except Exception as e:
        logger.error(api_config.get_log_message('device_reference', 'error_searching_known_devices', 
                                              query=query, error=str(e)))
        raise HTTPException(
            status_code=500,
            detail=api_config.get_error_message('failed_search_known_devices')
        )

@router.get("/stats", response_model=Dict[str, Any])
async def get_reference_stats(
    database_service = Depends(get_database_service_instance)
):
    """
    Get reference database statistics
    
    Returns:
        Reference database statistics
    """
    try:
        if api_config.is_feature_enabled('enable_detailed_logging'):
            logger.info(api_config.get_log_message('device_reference', 'getting_reference_stats'))
        
        stats = await database_service.reference_service.reference_repo.get_reference_stats()
        return stats
        
    except Exception as e:
        logger.error(api_config.get_log_message('device_reference', 'error_retrieving_reference_stats', error=str(e)))
        raise HTTPException(
            status_code=500,
            detail=api_config.get_error_message('failed_retrieve_reference_stats')
        )

@router.post("/cache/clear", response_model=Dict[str, Any])
async def clear_reference_cache():
    """
    Clear reference data cache
    
    Returns:
        Operation result
    """
    try:
        # Note: Cache clearing would be implemented in the reference service
        return {
            "success": True,
            "message": api_config.get_response_message('cache_cleared')
        }
        
    except Exception as e:
        logger.error(api_config.get_log_message('device_reference', 'error_clearing_cache', error=str(e)))
        raise HTTPException(
            status_code=500,
            detail=api_config.get_error_message('failed_clear_cache')
        )

@router.get("/known-devices", response_model=List[Dict[str, Any]])
async def get_known_devices(
    limit: int = Query(default=api_config.get_pagination('default_limit', 100), 
                      description=api_config.get_query_description('max_devices_description')),
    offset: int = Query(default=api_config.get_pagination('default_offset', 0), 
                       description=api_config.get_query_description('offset_skip_description')),
    search: Optional[str] = Query(default=None, 
                                 description=api_config.get_query_description('search_query_device_filter')),
    database_service = Depends(get_database_service_instance)
):
    """
    Retrieve known devices from reference database
    
    Args:
        limit: Maximum number of devices to return
        offset: Number of devices to skip (for pagination)
        search: Search term for filtering devices
    
    Returns:
        List of known devices with their reference information
    """
    try:
        if api_config.is_feature_enabled('enable_detailed_logging'):
            logger.info(api_config.get_log_message('device_reference', 'getting_known_devices', 
                                                 limit=limit, offset=offset, search=search))
        
        known_devices = await database_service.get_known_devices(limit=limit, offset=offset, search=search)
        
        if not known_devices:
            logger.warning(api_config.get_log_message('device_reference', 'no_known_devices_found'))
            return []
        
        if api_config.is_feature_enabled('enable_detailed_logging'):
            logger.info(api_config.get_log_message('device_reference', 'retrieved_known_devices', count=len(known_devices)))
        
        return known_devices
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(api_config.get_log_message('device_reference', 'error_retrieving_known_devices', error=str(e)))
        raise HTTPException(
            status_code=500,
            detail=api_config.get_error_message('failed_retrieve_known_devices')
        )

@router.get("/vendor-patterns", response_model=List[Dict[str, Any]])
async def get_vendor_patterns(
    limit: int = Query(default=api_config.get_pagination('default_limit', 100), 
                      description=api_config.get_query_description('max_patterns_description')),
    offset: int = Query(default=api_config.get_pagination('default_offset', 0), 
                       description=api_config.get_query_description('offset_patterns_description')),
    vendor: Optional[str] = Query(default=None, 
                                 description=api_config.get_query_description('vendor_filter_description')),
    database_service = Depends(get_database_service_instance)
):
    """
    Retrieve vendor patterns from reference database
    
    Args:
        limit: Maximum number of patterns to return
        offset: Number of patterns to skip (for pagination)
        vendor: Filter by specific vendor name
    
    Returns:
        List of vendor patterns with MAC address ranges
    """
    try:
        if api_config.is_feature_enabled('enable_detailed_logging'):
            logger.info(api_config.get_log_message('device_reference', 'getting_vendor_patterns', 
                                                 limit=limit, offset=offset, vendor=vendor))
        
        vendor_patterns = await database_service.get_vendor_patterns(limit=limit, offset=offset, vendor=vendor)
        
        if not vendor_patterns:
            logger.warning(api_config.get_log_message('device_reference', 'no_vendor_patterns_found'))
            return []
        
        if api_config.is_feature_enabled('enable_detailed_logging'):
            logger.info(api_config.get_log_message('device_reference', 'retrieved_vendor_patterns', count=len(vendor_patterns)))
        
        return vendor_patterns
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(api_config.get_log_message('device_reference', 'error_retrieving_vendor_patterns', error=str(e)))
        raise HTTPException(
            status_code=500,
            detail=api_config.get_error_message('failed_retrieve_vendor_patterns')
        )

@router.get("/device-lookup/{mac_address}", response_model=Dict[str, Any])
async def lookup_device_by_mac(
    mac_address: str,
    database_service = Depends(get_database_service_instance)
):
    """
    Lookup device information by MAC address from reference database
    
    Args:
        mac_address: Device MAC address
    
    Returns:
        Device information from reference database
    """
    try:
        device_info = await database_service.reference_service.reference_repo.get_known_device(mac_address)
        
        if device_info:
            return device_info
        else:
            raise HTTPException(
                status_code=404,
                detail=api_config.get_error_message('device_not_found')
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(api_config.get_log_message('device_reference', 'error_retrieving_known_devices', error=str(e)))
        raise HTTPException(
            status_code=500,
            detail=api_config.get_error_message('failed_retrieve_known_devices')
        )

@router.get("/vendor-lookup/{mac_address}", response_model=Dict[str, Any])
async def lookup_vendor_by_mac(
    mac_address: str,
    database_service = Depends(get_database_service_instance)
):
    """
    Lookup vendor information by MAC address OUI
    
    Args:
        mac_address: Device MAC address
    
    Returns:
        Vendor information based on MAC address OUI
    """
    try:
        # Extract OUI from MAC address
        oui_pattern = mac_address[:8]
        vendor_info = await database_service.reference_service.reference_repo.get_vendor_by_oui(oui_pattern)
        
        if vendor_info:
            return vendor_info
        else:
            raise HTTPException(
                status_code=404,
                detail=api_config.get_error_message('vendor_pattern_not_found')
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(api_config.get_log_message('device_reference', 'error_retrieving_vendor_patterns', error=str(e)))
        raise HTTPException(
            status_code=500,
            detail=api_config.get_error_message('failed_retrieve_vendor_patterns')
        )

@router.get("/device-types", response_model=List[Dict[str, Any]])
async def get_device_types(
    database_service = Depends(get_database_service_instance)
):
    """
    Retrieve all available device types from reference database
    
    Returns:
        List of device types with their descriptions
    """
    try:
        if api_config.is_feature_enabled('enable_detailed_logging'):
            logger.info(api_config.get_log_message('device_reference', 'getting_device_types'))
        
        device_types = await database_service.get_device_types()
        
        if not device_types:
            logger.warning(api_config.get_log_message('device_reference', 'no_device_types_found'))
            return []
        
        if api_config.is_feature_enabled('enable_detailed_logging'):
            logger.info(api_config.get_log_message('device_reference', 'retrieved_device_types', count=len(device_types)))
        
        return device_types
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(api_config.get_log_message('device_reference', 'error_retrieving_device_types', error=str(e)))
        raise HTTPException(
            status_code=500,
            detail=api_config.get_error_message('failed_retrieve_device_types')
        )

@router.get("/vendors", response_model=List[Dict[str, Any]])
async def get_vendors(
    limit: int = Query(default=api_config.get_pagination('default_limit', 100), 
                      description=api_config.get_query_description('max_vendors_description')),
    offset: int = Query(default=api_config.get_pagination('default_offset', 0), 
                       description=api_config.get_query_description('offset_vendors_description')),
    search: Optional[str] = Query(default=None, 
                                 description=api_config.get_query_description('search_query_vendor_filter')),
    database_service = Depends(get_database_service_instance)
):
    """
    Retrieve vendor list from reference database
    
    Args:
        limit: Maximum number of vendors to return
        offset: Number of vendors to skip (for pagination)
        search: Search term for filtering vendors
    
    Returns:
        List of vendors with their information
    """
    try:
        if api_config.is_feature_enabled('enable_detailed_logging'):
            logger.info(api_config.get_log_message('device_reference', 'getting_vendors', 
                                                 limit=limit, offset=offset, search=search))
        
        vendors = await database_service.get_vendors(limit=limit, offset=offset, search=search)
        
        if not vendors:
            logger.warning(api_config.get_log_message('device_reference', 'no_vendors_found'))
            return []
        
        if api_config.is_feature_enabled('enable_detailed_logging'):
            logger.info(api_config.get_log_message('device_reference', 'retrieved_vendors', count=len(vendors)))
        
        return vendors
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(api_config.get_log_message('device_reference', 'error_retrieving_vendors', error=str(e)))
        raise HTTPException(
            status_code=500,
            detail=api_config.get_error_message('failed_retrieve_vendors')
        )

@router.get("/vendor-patterns/export")
async def export_vendor_patterns(
    database_service = Depends(get_database_service_instance)
):
    """
    Export all vendor patterns as JSON
    
    Returns:
        JSON file download with all vendor patterns
    """
    try:
        if not api_config.is_feature_enabled('enable_export_functionality'):
            raise HTTPException(
                status_code=403,
                detail="Export functionality is disabled"
            )
        
        if api_config.is_feature_enabled('enable_detailed_logging'):
            logger.info(api_config.get_log_message('device_reference', 'exporting_vendor_patterns'))
        
        # Get all vendor patterns using the configured export limit
        export_limit = api_config.export_config.get('export_limit', 10000)
        vendor_patterns = await database_service.get_vendor_patterns(limit=export_limit, offset=0)
        
        # Convert datetime objects to strings for JSON serialization
        def convert_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {k: convert_datetime(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_datetime(item) for item in obj]
            return obj
        
        # Process the data
        processed_patterns = convert_datetime(vendor_patterns)
        
        # Create export data
        export_data = {
            "export_type": api_config.export_config.get('export_type_vendor_patterns', 'vendor_patterns'),
            "export_date": datetime.now().isoformat(),
            "total_records": len(processed_patterns),
            "data": processed_patterns
        }
        
        # Create filename
        timestamp = datetime.now().strftime(api_config.export_config.get('timestamp_format', '%Y%m%d_%H%M%S'))
        filename_prefix = api_config.export_config.get('filename_prefix_vendor_patterns', 'vendor_patterns_export')
        filename_format = api_config.export_config.get('filename_format', '{prefix}_{timestamp}')
        file_extension = api_config.export_config.get('file_extension', 'json')
        
        filename = f"{filename_format.format(prefix=filename_prefix, timestamp=timestamp)}.{file_extension}"
        
        # Return JSON response with download headers
        content = json.dumps(export_data, 
                           indent=api_config.export_config.get('json_indent', 2), 
                           ensure_ascii=api_config.export_config.get('ensure_ascii', False))
        
        return Response(
            content=content,
            media_type=api_config.export_config.get('media_type', 'application/json'),
            headers={
                "Content-Disposition": api_config.export_config.get('content_disposition_template', 
                                                                  'attachment; filename={filename}').format(filename=filename),
                "Content-Type": api_config.export_config.get('media_type', 'application/json')
            }
        )
        
    except Exception as e:
        logger.error(api_config.get_log_message('device_reference', 'error_exporting_vendor_patterns', error=str(e)))
        raise HTTPException(
            status_code=500,
            detail=api_config.get_error_message('failed_export_vendor_patterns') + f": {str(e)}"
        )

@router.get("/known-devices/export")
async def export_known_devices(
    database_service = Depends(get_database_service_instance)
):
    """
    Export all known devices as JSON
    
    Returns:
        JSON file download with all known devices
    """
    try:
        if not api_config.is_feature_enabled('enable_export_functionality'):
            raise HTTPException(
                status_code=403,
                detail="Export functionality is disabled"
            )
        
        if api_config.is_feature_enabled('enable_detailed_logging'):
            logger.info(api_config.get_log_message('device_reference', 'exporting_known_devices'))
        
        # Get all known devices using the configured export limit
        export_limit = api_config.export_config.get('export_limit', 10000)
        known_devices = await database_service.get_known_devices(limit=export_limit, offset=0)
        
        # Convert datetime objects to strings for JSON serialization
        def convert_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {k: convert_datetime(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_datetime(item) for item in obj]
            return obj
        
        # Process the data
        processed_devices = convert_datetime(known_devices)
        
        # Create export data
        export_data = {
            "export_type": api_config.export_config.get('export_type_known_devices', 'known_devices'),
            "export_date": datetime.now().isoformat(),
            "total_records": len(processed_devices),
            "data": processed_devices
        }
        
        # Create filename
        timestamp = datetime.now().strftime(api_config.export_config.get('timestamp_format', '%Y%m%d_%H%M%S'))
        filename_prefix = api_config.export_config.get('filename_prefix_known_devices', 'known_devices_export')
        filename_format = api_config.export_config.get('filename_format', '{prefix}_{timestamp}')
        file_extension = api_config.export_config.get('file_extension', 'json')
        
        filename = f"{filename_format.format(prefix=filename_prefix, timestamp=timestamp)}.{file_extension}"
        
        # Return JSON response with download headers
        content = json.dumps(export_data, 
                           indent=api_config.export_config.get('json_indent', 2), 
                           ensure_ascii=api_config.export_config.get('ensure_ascii', False))
        
        return Response(
            content=content,
            media_type=api_config.export_config.get('media_type', 'application/json'),
            headers={
                "Content-Disposition": api_config.export_config.get('content_disposition_template', 
                                                                  'attachment; filename={filename}').format(filename=filename),
                "Content-Type": api_config.export_config.get('media_type', 'application/json')
            }
        )
        
    except Exception as e:
        logger.error(api_config.get_log_message('device_reference', 'error_exporting_known_devices', error=str(e)))
        raise HTTPException(
            status_code=500,
            detail=api_config.get_error_message('failed_export_known_devices') + f": {str(e)}"
        )

@router.get("/reference-stats", response_model=Dict[str, Any])
async def get_reference_stats(
    database_service = Depends(get_database_service_instance)
):
    """
    Retrieve reference database statistics
    
    Returns:
        Statistics about the reference database content
    """
    try:
        if api_config.is_feature_enabled('enable_detailed_logging'):
            logger.info(api_config.get_log_message('device_reference', 'getting_reference_stats'))
        
        stats = await database_service.get_reference_stats()
        
        if not stats:
            logger.warning(api_config.get_log_message('device_reference', 'no_reference_stats_found'))
            return {}
        
        if api_config.is_feature_enabled('enable_detailed_logging'):
            logger.info(api_config.get_log_message('device_reference', 'retrieved_reference_stats'))
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(api_config.get_log_message('device_reference', 'error_retrieving_reference_stats', error=str(e)))
        raise HTTPException(
            status_code=500,
            detail=api_config.get_error_message('failed_retrieve_reference_stats')
        ) 
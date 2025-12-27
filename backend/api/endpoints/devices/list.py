#!/usr/bin/env python3
"""
Configurable Device List API Endpoint
Handles device listing with configurable pagination and filtering
"""

import logging
import sys
import os
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
import asyncio
from datetime import datetime
from pathlib import Path

# Setup unified path configuration
config_path = Path(__file__).parent.parent.parent.parent / "config"
sys.path.insert(0, str(config_path))

from config.unified_config_manager import UnifiedConfigManager
from config.unified_config_manager import get_config, get_log_message

logger = logging.getLogger(__name__)

class ConfigurableDeviceListAPI:
    """Configurable device list API"""
    
    def __init__(self):
        self.config_namespace = 'device_list_api'
        
    def _get_default_pagination(self) -> Dict[str, Any]:
        """Get the default pagination configuration"""
        return {
            'default_limit': get_config(f'{self.config_namespace}.pagination.default_limit', 100, f'{self.config_namespace}.pagination'),
            'max_limit': get_config(f'{self.config_namespace}.pagination.max_limit', 1000, f'{self.config_namespace}.pagination'),
            'default_offset': get_config(f'{self.config_namespace}.pagination.default_offset', 0, f'{self.config_namespace}.pagination')
        }
    
    def _get_response_field_mapping(self) -> Dict[str, str]:
        """Get the response field mapping configuration"""
        return get_config(f'{self.config_namespace}.response_fields', {
            'count_field': 'count',
            'devices_field': 'devices',
            'total_field': 'total',
            'limit_field': 'limit',
            'offset_field': 'offset'
        }, f'{self.config_namespace}.response_fields')
    
    async def get_devices_list(self, limit: int, offset: int, experiment_id: Optional[str], database_service) -> List[Dict[str, Any]]:
        """Configurable device list retrieval"""
        try:
            # Configurable API call log
            if get_config(f'{self.config_namespace}.logging.log_api_calls', True, f'{self.config_namespace}.logging'):
                logger.info(get_log_message('device_list_api', 'api_call_started', 
                                           component='device_list.api',
                                           limit=limit, offset=offset, experiment_id=experiment_id))
            
            devices = await database_service.get_devices_list(
                limit=limit,
                offset=offset,
                experiment_id=experiment_id
            )
            
            # Configurable success log
            if get_config(f'{self.config_namespace}.logging.log_api_success', True, f'{self.config_namespace}.logging'):
                logger.info(get_log_message('device_list_api', 'api_call_completed', 
                                           component='device_list.api',
                                           results_count=len(devices)))
            return devices
            
        except Exception as e:
            # Configurable error log
            if get_config(f'{self.config_namespace}.logging.log_api_errors', True, f'{self.config_namespace}.logging'):
                logger.error(get_log_message('device_list_api', 'api_call_failed', 
                                            component='device_list.api',
                                            error=str(e)))
            raise
    
    async def get_devices_count(self, database_service) -> int:
        """Configurable device count retrieval"""
        try:
            # Configurable API call log
            if get_config(f'{self.config_namespace}.logging.log_count_requests', True, f'{self.config_namespace}.logging'):
                logger.info(get_log_message('device_list_api', 'count_request_started', 
                                           component='device_list.api'))
            
            count = await database_service.get_devices_count()
            
            # Configurable success log
            if get_config(f'{self.config_namespace}.logging.log_count_success', True, f'{self.config_namespace}.logging'):
                logger.info(get_log_message('device_list_api', 'count_request_completed', 
                                           component='device_list.api',
                                           count=count))
            return count
            
        except Exception as e:
            # Configurable error log
            if get_config(f'{self.config_namespace}.logging.log_count_errors', True, f'{self.config_namespace}.logging'):
                logger.error(get_log_message('device_list_api', 'count_request_failed', 
                                            component='device_list.api',
                                            error=str(e)))
            raise

# Create the configurable API instance
configurable_api = ConfigurableDeviceListAPI()

router = APIRouter()

# Use the unified dependency injection
from ...common.dependencies import get_database_service_instance

@router.get("/list", 
           response_model=List[Dict[str, Any]], 
           summary="Get devices list",
           description="Get paginated list of devices with configurable parameters")
async def get_devices_list(
    limit: int = Query(default=None, description="Number of devices to return", ge=1, le=1000),
    offset: int = Query(default=None, description="Number of devices to skip", ge=0),
    experiment_id: Optional[str] = Query(default=None, description="Filter devices by experiment ID"),
    database_service = Depends(get_database_service_instance)
):
    """
    Configurable device list API endpoint
    Get paginated list of devices with configurable pagination and filtering
    """
    try:
        # Use the configurable defaults
        pagination_config = configurable_api._get_default_pagination()
        if limit is None:
            limit = pagination_config['default_limit']
        if offset is None:
            offset = pagination_config['default_offset']
        
        # Call the configurable API method
        return await configurable_api.get_devices_list(
            limit=limit,
            offset=offset,
            experiment_id=experiment_id,
            database_service=database_service
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_message = get_config('device_list_api.error_messages.general_error', 
                                 "Failed to get devices list: {error}", 
                                 'device_list_api.error_messages')
        raise HTTPException(
            status_code=500, 
            detail=error_message.format(error=str(e))
        )


@router.get("/count",
           response_model=Dict[str, int],
           summary="Get devices count", 
           description="Get total count of devices with configurable response format")
async def get_devices_count(
    database_service = Depends(get_database_service_instance)
):
    """
    Configurable device count API endpoint
    Get total count of devices with configurable response format
    """
    try:
        # Call the configurable API method
        count = await configurable_api.get_devices_count(database_service)
        
        # Use the configurable response field mapping
        field_mapping = configurable_api._get_response_field_mapping()
        return {field_mapping['count_field']: count}
        
    except HTTPException:
        raise
    except Exception as e:
        error_message = get_config('device_list_api.error_messages.count_error', 
                                 "Failed to get devices count: {error}", 
                                 'device_list_api.error_messages')
        raise HTTPException(
            status_code=500,
            detail=error_message.format(error=str(e))
        ) 
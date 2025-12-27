"""
Configurable Experiment Devices API Endpoint
Handles device data retrieval for specific experiments with configurable parameters
"""

import logging
import sys
import os
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Path, Depends, Query

# Setup unified path configuration
from ...common.path_config import setup_project_paths
setup_project_paths()

from config.unified_config_manager import get_config, get_log_message

logger = logging.getLogger(__name__)

class ConfigurableExperimentDevicesAPI:
    """Configurable experiment devices API"""
    
    def __init__(self):
        self.config_namespace = 'experiment_devices_api'
        
    def _get_pagination_config(self) -> Dict[str, int]:
        """Get pagination configuration"""
        return {
            'default_limit': get_config(f'{self.config_namespace}.pagination.default_limit', 100, f'{self.config_namespace}.pagination'),
            'max_limit': get_config(f'{self.config_namespace}.pagination.max_limit', 1000, f'{self.config_namespace}.pagination'),
            'default_offset': get_config(f'{self.config_namespace}.pagination.default_offset', 0, f'{self.config_namespace}.pagination')
        }
    
    def _get_response_field_mapping(self) -> Dict[str, str]:
        """Get response field mapping configuration"""
        return get_config(f'{self.config_namespace}.response_fields', {
            'devices_field': 'devices',
            'total_field': 'total',
            'limit_field': 'limit',
            'offset_field': 'offset',
            'experiment_id_field': 'experiment_id',
            'device_count_field': 'device_count',
            'summary_field': 'summary'
        }, f'{self.config_namespace}.response_fields')
    
    def _get_error_messages(self) -> Dict[str, str]:
        """Get error messages configuration"""
        return get_config(f'{self.config_namespace}.error_messages', {
            'experiment_not_found': "Experiment '{experiment_id}' not found",
            'invalid_experiment_id': "Invalid experiment ID format: {experiment_id}",
            'invalid_pagination': "Invalid pagination parameters: {error}",
            'database_query_failed': "Database query failed: {error}",
            'devices_retrieval_failed': "Failed to retrieve devices for experiment '{experiment_id}'"
        }, f'{self.config_namespace}.error_messages')
    
    def _get_validation_config(self) -> Dict[str, Any]:
        """Get validation configuration"""
        return {
            'enable_id_validation': get_config(f'{self.config_namespace}.validation.enable_id_validation', True, f'{self.config_namespace}.validation'),
            'max_id_length': get_config(f'{self.config_namespace}.validation.max_id_length', 100, f'{self.config_namespace}.validation'),
            'min_id_length': get_config(f'{self.config_namespace}.validation.min_id_length', 1, f'{self.config_namespace}.validation'),
            'allowed_id_pattern': get_config(f'{self.config_namespace}.validation.allowed_id_pattern', r'^[a-zA-Z0-9_-]+$', f'{self.config_namespace}.validation')
        }
    
    def _validate_experiment_id(self, experiment_id: str) -> bool:
        """Configurable experiment ID validation"""
        validation_config = self._get_validation_config()
        
        if not validation_config['enable_id_validation']:
            return True
        
        # Length validation
        if len(experiment_id) < validation_config['min_id_length'] or len(experiment_id) > validation_config['max_id_length']:
            return False
        
        # Pattern validation
        import re
        pattern = validation_config['allowed_id_pattern']
        if not re.match(pattern, experiment_id):
            return False
        
        return True
    
    def _validate_pagination(self, limit: int, offset: int) -> bool:
        """Configurable pagination validation"""
        pagination_config = self._get_pagination_config()
        
        if limit <= 0 or limit > pagination_config['max_limit']:
            return False
        
        if offset < 0:
            return False
        
        return True
    
    async def get_experiment_devices(self, experiment_id: str, limit: int, offset: int, database_service) -> Dict[str, Any]:
        """Configurable experiment devices retrieval"""
        try:
            error_messages = self._get_error_messages()
            
            # Configurable ID validation
            if not self._validate_experiment_id(experiment_id):
                raise HTTPException(
                    status_code=400,
                    detail=error_messages['invalid_experiment_id'].format(experiment_id=experiment_id)
                )
            
            # Configurable pagination validation
            if not self._validate_pagination(limit, offset):
                raise HTTPException(
                    status_code=400,
                    detail=error_messages['invalid_pagination'].format(
                        error=f"limit={limit}, offset={offset}"
                    )
                )
            
            # Configurable API call log
            if get_config(f'{self.config_namespace}.logging.log_api_calls', True, f'{self.config_namespace}.logging'):
                logger.info(get_log_message('experiment_devices_api', 'devices_request_started', 
                                           component='experiment_devices.api',
                                           experiment_id=experiment_id, limit=limit, offset=offset))
            
            # Get device list
            devices = await database_service.get_experiment_devices(experiment_id, limit=limit, offset=offset)
            total_count = await database_service.get_experiment_device_count(experiment_id)
            
            # Configurable data enhancement
            enhanced_response = self._enhance_devices_response(devices, total_count, limit, offset, experiment_id)
            
            # Configurable success log
            if get_config(f'{self.config_namespace}.logging.log_api_success', True, f'{self.config_namespace}.logging'):
                logger.info(get_log_message('experiment_devices_api', 'devices_request_completed', 
                                           component='experiment_devices.api',
                                           experiment_id=experiment_id, device_count=len(devices), total=total_count))
            
            return enhanced_response
            
        except HTTPException:
            raise
        except Exception as e:
            # Configurable error log
            if get_config(f'{self.config_namespace}.logging.log_api_errors', True, f'{self.config_namespace}.logging'):
                logger.error(get_log_message('experiment_devices_api', 'devices_request_failed', 
                                            component='experiment_devices.api',
                                            experiment_id=experiment_id, error=str(e)))
            raise
    
    def _enhance_devices_response(self, devices: List[Dict[str, Any]], total_count: int, limit: int, offset: int, experiment_id: str) -> Dict[str, Any]:
        """Configurable device response enhancement"""
        field_mapping = self._get_response_field_mapping()
        
        # Build enhanced response
        enhanced_response = {
            field_mapping['devices_field']: devices,
            field_mapping['total_field']: total_count,
            field_mapping['limit_field']: limit,
            field_mapping['offset_field']: offset,
            field_mapping['experiment_id_field']: experiment_id
        }
        
        # Configurable summary enhancement
        if get_config(f'{self.config_namespace}.features.enable_summary_enhancement', True, f'{self.config_namespace}.features'):
            summary = {
                'current_page_count': len(devices),
                'has_more': (offset + len(devices)) < total_count,
                'remaining_count': max(0, total_count - offset - len(devices))
            }
            enhanced_response[field_mapping['summary_field']] = summary
        
        return enhanced_response

# Create configurable API instance
configurable_api = ConfigurableExperimentDevicesAPI()

router = APIRouter()

# Use unified dependency injection
from ...common.dependencies import get_database_service_instance

@router.get("/{experiment_id}/devices", response_model=Dict[str, Any])
async def get_experiment_devices(
    experiment_id: str = Path(..., description="Experiment ID"),
    limit: int = Query(default=None, description="Maximum number of devices to return"),
    offset: int = Query(default=None, description="Number of devices to skip"),
    database_service = Depends(get_database_service_instance)
):
    """
    Configurable experiment devices API endpoint
    Retrieve devices for a specific experiment with configurable pagination and validation
    
    Args:
        experiment_id: Experiment identifier
        limit: Maximum number of devices to return
        offset: Number of devices to skip
    
    Returns:
        List of devices with pagination metadata
    """
    try:
        # Use configurable pagination defaults
        pagination_config = configurable_api._get_pagination_config()
        if limit is None:
            limit = pagination_config['default_limit']
        if offset is None:
            offset = pagination_config['default_offset']
        
        # Call configurable API method
        return await configurable_api.get_experiment_devices(experiment_id, limit, offset, database_service)
        
    except HTTPException:
        raise
    except Exception as e:
        error_messages = configurable_api._get_error_messages()
        raise HTTPException(
            status_code=500,
            detail=error_messages['devices_retrieval_failed'].format(experiment_id=experiment_id)
        ) 
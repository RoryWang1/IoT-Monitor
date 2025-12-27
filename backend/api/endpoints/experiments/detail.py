"""
Configurable Experiment Detail API Endpoint
Handles experiment detail data retrieval with configurable parameters
"""

import logging
import sys
import os
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Path, Depends

# Setup unified path configuration
from ...common.path_config import setup_project_paths
setup_project_paths()

from config.unified_config_manager import get_config, get_log_message

logger = logging.getLogger(__name__)

class ConfigurableExperimentDetailAPI:
    """Configurable experiment detail API"""
    
    def __init__(self):
        self.config_namespace = 'experiment_detail_api'
        
    def _get_response_field_mapping(self) -> Dict[str, str]:
        """Get the response field mapping configuration"""
        return get_config(f'{self.config_namespace}.response_fields', {
            'experiment_id_field': 'experiment_id',
            'experiment_name_field': 'experiment_name',
            'description_field': 'description',
            'status_field': 'status',
            'created_at_field': 'created_at',
            'updated_at_field': 'updated_at',
            'device_count_field': 'device_count',
            'total_packets_field': 'total_packets',
            'total_bytes_field': 'total_bytes',
            'duration_field': 'duration'
        }, f'{self.config_namespace}.response_fields')
    
    def _get_error_messages(self) -> Dict[str, str]:
        """Get the error messages configuration"""
        return get_config(f'{self.config_namespace}.error_messages', {
            'experiment_not_found': "Experiment '{experiment_id}' not found",
            'invalid_experiment_id': "Invalid experiment ID format: {experiment_id}",
            'database_query_failed': "Database query failed: {error}",
            'detail_retrieval_failed': "Failed to retrieve experiment detail for '{experiment_id}'"
        }, f'{self.config_namespace}.error_messages')
    
    def _get_validation_config(self) -> Dict[str, Any]:
        """Get the validation configuration"""
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
    
    async def get_experiment_detail(self, experiment_id: str, database_service) -> Dict[str, Any]:
        """Configurable experiment detail retrieval with timezone support"""
        try:
            error_messages = self._get_error_messages()
            
            # Configurable ID validation
            if not self._validate_experiment_id(experiment_id):
                raise HTTPException(
                    status_code=400,
                    detail=error_messages['invalid_experiment_id'].format(experiment_id=experiment_id)
                )
            
            # Configurable API call log
            if get_config(f'{self.config_namespace}.logging.log_api_calls', True, f'{self.config_namespace}.logging'):
                logger.info(get_log_message('experiment_detail_api', 'detail_request_started', 
                                           component='experiment_detail.api',
                                           experiment_id=experiment_id))
            
            experiment_detail = await database_service.get_experiment_detail(experiment_id)
            
            if not experiment_detail:
                raise HTTPException(
                    status_code=404,
                    detail=error_messages['experiment_not_found'].format(experiment_id=experiment_id)
                )
            
            # Apply timezone conversion to experiment detail
            enhanced_detail = await self._apply_timezone_conversion(experiment_detail, experiment_id)
            
            # Configurable data enhancement
            enhanced_detail = self._enhance_experiment_detail(enhanced_detail)
            
            # Configurable success log
            if get_config(f'{self.config_namespace}.logging.log_api_success', True, f'{self.config_namespace}.logging'):
                logger.info(get_log_message('experiment_detail_api', 'detail_request_completed', 
                                           component='experiment_detail.api',
                                           experiment_id=experiment_id))
            
            return enhanced_detail
            
        except HTTPException:
            raise
        except Exception as e:
            # Configurable error log
            if get_config(f'{self.config_namespace}.logging.log_api_errors', True, f'{self.config_namespace}.logging'):
                logger.error(get_log_message('experiment_detail_api', 'detail_request_failed', 
                                            component='experiment_detail.api',
                                            experiment_id=experiment_id, error=str(e)))
            raise
    
    async def _apply_timezone_conversion(self, experiment_detail: Dict[str, Any], experiment_id: str) -> Dict[str, Any]:
        """Apply timezone conversion to all timestamps in experiment detail"""
        try:
            # Import the correct timezone manager that actually works
            try:
                from database.services.timezone_manager import timezone_manager
                logger.info("Using database.services.timezone_manager")
            except ImportError:
                # Fallback to common timezone manager if database one is not available
                from backend.api.common.timezone_manager import timezone_manager
                logger.warning("Falling back to backend.api.common.timezone_manager")
            
            # Debug: Check what timezone we get - fix await error
            experiment_tz = timezone_manager.get_experiment_timezone(experiment_id)  # Remove await
            logger.info(f"Experiment {experiment_id} timezone: {experiment_tz}")
            
            # If timezone is UTC, we might not have the timezone data saved properly
            if experiment_tz == 'UTC':
                logger.warning(f"Experiment {experiment_id} timezone is UTC - checking if this is intended")
            
            # Create a copy of the data
            converted_detail = experiment_detail.copy()
            
            # Convert experiment-level timestamps
            experiment_timestamp_fields = ['createdAt', 'updatedAt', 'created_at', 'updated_at']
            for field in experiment_timestamp_fields:
                if field in converted_detail and converted_detail[field]:
                    original_timestamp = converted_detail[field]
                    if isinstance(original_timestamp, str):
                        try:
                            from datetime import datetime
                            dt = datetime.fromisoformat(original_timestamp.replace('Z', '+00:00'))
                            converted_dt = timezone_manager.convert_to_experiment_timezone(dt, experiment_id)
                            converted_detail[field] = converted_dt.isoformat()
                            logger.debug(f"Converted {field}: {original_timestamp} -> {converted_detail[field]}")
                        except Exception as e:
                            logger.warning(f"Failed to convert timestamp {field}: {e}")
            
            # Convert device timestamps in devices list
            if 'devices' in converted_detail and isinstance(converted_detail['devices'], list):
                for device in converted_detail['devices']:
                    device_timestamp_fields = ['lastSeen', 'firstSeen', 'last_seen', 'first_seen', 'createdAt', 'updatedAt', 'created_at', 'updated_at']
                    for field in device_timestamp_fields:
                        if field in device and device[field]:
                            original_timestamp = device[field]
                            if isinstance(original_timestamp, str):
                                try:
                                    from datetime import datetime
                                    dt = datetime.fromisoformat(original_timestamp.replace('Z', '+00:00'))
                                    converted_dt = timezone_manager.convert_to_experiment_timezone(dt, experiment_id)
                                    device[field] = converted_dt.isoformat()
                                    logger.debug(f"Converted device {field}: {original_timestamp} -> {device[field]}")
                                except Exception as e:
                                    logger.warning(f"Failed to convert device timestamp {field}: {e}")
            
            # Convert device timestamps in device_list (alternative field name)
            if 'device_list' in converted_detail and isinstance(converted_detail['device_list'], list):
                for device in converted_detail['device_list']:
                    device_timestamp_fields = ['lastSeen', 'firstSeen', 'last_seen', 'first_seen', 'createdAt', 'updatedAt', 'created_at', 'updated_at']
                    for field in device_timestamp_fields:
                        if field in device and device[field]:
                            original_timestamp = device[field]
                            if isinstance(original_timestamp, str):
                                try:
                                    from datetime import datetime
                                    dt = datetime.fromisoformat(original_timestamp.replace('Z', '+00:00'))
                                    converted_dt = timezone_manager.convert_to_experiment_timezone(dt, experiment_id)
                                    device[field] = converted_dt.isoformat()
                                    logger.debug(f"Converted device_list {field}: {original_timestamp} -> {device[field]}")
                                except Exception as e:
                                    logger.warning(f"Failed to convert device_list timestamp {field}: {e}")
            
            # Convert timestamps in traffic timeline if present
            if 'trafficTimeline' in converted_detail and isinstance(converted_detail['trafficTimeline'], list):
                for item in converted_detail['trafficTimeline']:
                    if 'timestamp' in item and item['timestamp']:
                        try:
                            from datetime import datetime
                            dt = datetime.fromisoformat(item['timestamp'].replace('Z', '+00:00'))
                            converted_dt = timezone_manager.convert_to_experiment_timezone(dt, experiment_id)
                            item['timestamp'] = converted_dt.isoformat()
                            logger.debug(f"Converted timeline timestamp: {dt} -> {item['timestamp']}")
                        except Exception as e:
                            logger.warning(f"Failed to convert traffic timeline timestamp: {e}")
            
            return converted_detail
            
        except Exception as e:
            logger.error(f"Error applying timezone conversion: {e}")
            return experiment_detail  # Return original data on error
    
    def _enhance_experiment_detail(self, experiment_detail: Dict[str, Any]) -> Dict[str, Any]:
        """Configurable experiment detail enhancement"""
        # Keep all original fields, do not discard statistics and devices
        enhanced_detail = experiment_detail.copy()  # Keep all original data
        
        field_mapping = self._get_response_field_mapping()
        
        # Apply field mapping (only rename or validate fields defined in the mapping)
        for config_field, actual_field in field_mapping.items():
            if actual_field in experiment_detail:
                # If you need to rename fields, handle it here
                # Currently keeping the original field names
                enhanced_detail[actual_field] = experiment_detail[actual_field]
        
        # Configurable field enhancement
        if get_config(f'{self.config_namespace}.features.enable_field_enhancement', True, f'{self.config_namespace}.features'):
            # Add calculated fields
            if 'created_at' in enhanced_detail and 'updated_at' in enhanced_detail:
                created_at = enhanced_detail['created_at']
                updated_at = enhanced_detail['updated_at']
                if created_at and updated_at:
                    from datetime import datetime
                    if isinstance(created_at, str):
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    if isinstance(updated_at, str):
                        updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                    enhanced_detail['duration_days'] = (updated_at - created_at).days
        
        return enhanced_detail

# Create configurable API instance
configurable_api = ConfigurableExperimentDetailAPI()

router = APIRouter()

# Use unified dependency injection
from ...common.dependencies import get_database_service_instance

@router.get("/{experiment_id}", response_model=Dict[str, Any])
async def get_experiment_detail(
    experiment_id: str = Path(..., description="Experiment ID"),
    database_service = Depends(get_database_service_instance)
):
    """
    Configurable experiment detail API endpoint
    Retrieve detailed information for a specific experiment with configurable validation and enhancement
    
    Args:
        experiment_id: Experiment identifier
    
    Returns:
        Experiment detail data
    """
    try:
        # Call configurable API method
        return await configurable_api.get_experiment_detail(experiment_id, database_service)
        
    except HTTPException:
        raise
    except Exception as e:
        error_messages = configurable_api._get_error_messages()
        raise HTTPException(
            status_code=500,
            detail=error_messages['detail_retrieval_failed'].format(experiment_id=experiment_id)
        ) 
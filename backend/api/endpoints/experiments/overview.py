"""
Configurable Experiments Overview API Endpoint
Handles experiment list and overview data retrieval with configurable parameters
"""

import logging
import sys
import os
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Depends

# Setup unified path configuration
from ...common.path_config import setup_project_paths
setup_project_paths()

from config.unified_config_manager import UnifiedConfigManager
from config.unified_config_manager import get_config, get_log_message

logger = logging.getLogger(__name__)

class ConfigurableExperimentsOverviewAPI:
    """Configurable experiments overview API"""
    
    def __init__(self):
        self.config_namespace = 'experiments_overview_api'
        
    def _get_default_pagination(self) -> Dict[str, Any]:
        """Get default pagination configuration"""
        return {
            'default_limit': get_config(f'{self.config_namespace}.pagination.default_limit', 100, f'{self.config_namespace}.pagination'),
            'max_limit': get_config(f'{self.config_namespace}.pagination.max_limit', 1000, f'{self.config_namespace}.pagination'),
            'default_offset': get_config(f'{self.config_namespace}.pagination.default_offset', 0, f'{self.config_namespace}.pagination')
        }
    
    def _get_response_field_mapping(self) -> Dict[str, str]:
        """Get response field mapping configuration"""
        return get_config(f'{self.config_namespace}.response_fields', {
            'experiments_field': 'experiments',
            'count_field': 'total_count',
            'limit_field': 'limit',
            'offset_field': 'offset'
        }, f'{self.config_namespace}.response_fields')
    
    async def get_experiments_list(self, database_service) -> List[Dict[str, Any]]:
        """Configurable experiment list retrieval"""
        try:
            # Configurable API call log
            if get_config(f'{self.config_namespace}.logging.log_api_calls', True, f'{self.config_namespace}.logging'):
                logger.info(get_log_message('experiments_overview_api', 'list_request_started', 
                                           component='experiments_overview.api'))
            
            experiments = await database_service.get_experiments_overview()
            
            if not experiments:
                # Configurable empty result log
                if get_config(f'{self.config_namespace}.logging.log_empty_results', True, f'{self.config_namespace}.logging'):
                    logger.warning(get_log_message('experiments_overview_api', 'no_experiments_found', 
                                                  component='experiments_overview.api'))
                return []
            
            # Configurable success log
            if get_config(f'{self.config_namespace}.logging.log_api_success', True, f'{self.config_namespace}.logging'):
                logger.info(get_log_message('experiments_overview_api', 'list_request_completed', 
                                           component='experiments_overview.api',
                                           results_count=len(experiments)))
            return experiments
            
        except Exception as e:
            # Configurable error log
            if get_config(f'{self.config_namespace}.logging.log_api_errors', True, f'{self.config_namespace}.logging'):
                logger.error(get_log_message('experiments_overview_api', 'list_request_failed', 
                                            component='experiments_overview.api',
                                            error=str(e)))
            raise
    
    async def get_experiments_overview(self, limit: int, offset: int, database_service) -> List[Dict[str, Any]]:
        """Configurable experiments overview retrieval"""
        try:
            # Configurable API call log
            if get_config(f'{self.config_namespace}.logging.log_overview_calls', True, f'{self.config_namespace}.logging'):
                logger.info(get_log_message('experiments_overview_api', 'overview_request_started', 
                                           component='experiments_overview.api',
                                           limit=limit, offset=offset))
            
            experiments = await database_service.get_experiments_overview(limit=limit, offset=offset)
            
            if not experiments:
                # Configurable empty result log
                if get_config(f'{self.config_namespace}.logging.log_empty_results', True, f'{self.config_namespace}.logging'):
                    logger.warning(get_log_message('experiments_overview_api', 'no_experiments_found', 
                                                  component='experiments_overview.api'))
                return []
            
            # Configurable success log
            if get_config(f'{self.config_namespace}.logging.log_overview_success', True, f'{self.config_namespace}.logging'):
                logger.info(get_log_message('experiments_overview_api', 'overview_request_completed', 
                                           component='experiments_overview.api',
                                           experiment_count=len(experiments)))
            return experiments
            
        except Exception as e:
            # Configurable error log
            if get_config(f'{self.config_namespace}.logging.log_overview_errors', True, f'{self.config_namespace}.logging'):
                logger.error(get_log_message('experiments_overview_api', 'overview_request_failed', 
                                            component='experiments_overview.api',
                                            error=str(e)))
            raise

# Create configurable API instance
configurable_api = ConfigurableExperimentsOverviewAPI()

router = APIRouter()

# Use unified dependency injection
from ...common.dependencies import get_database_service_instance

@router.get("", response_model=List[Dict[str, Any]])
async def get_experiments_list(
    database_service = Depends(get_database_service_instance)
):
    """
    Configurable experiments list API endpoint
    Get all experiments list with configurable response format
    
    Returns:
        List of experiments with basic information
    """
    try:
        # Call configurable API method
        return await configurable_api.get_experiments_list(database_service)
        
    except HTTPException:
        raise
    except Exception as e:
        error_message = get_config('experiments_overview_api.error_messages.list_error', 
                                 "Failed to retrieve experiments list: {error}", 
                                 'experiments_overview_api.error_messages')
        raise HTTPException(
            status_code=500,
            detail=error_message.format(error=str(e))
        )

@router.get("/overview", response_model=List[Dict[str, Any]])
async def get_experiments_overview(
    limit: int = Query(default=None, description="Maximum number of experiments to return"),
    offset: int = Query(default=None, description="Number of experiments to skip"),
    database_service = Depends(get_database_service_instance)
):
    """
    Configurable experiments overview API endpoint
    Retrieve experiments overview list with configurable pagination
    
    Args:
        limit: Maximum number of experiments to return
        offset: Number of experiments to skip (for pagination)
    
    Returns:
        List of experiments with summary information
    """
    try:
        # Use configurable defaults
        pagination_config = configurable_api._get_default_pagination()
        if limit is None:
            limit = pagination_config['default_limit']
        if offset is None:
            offset = pagination_config['default_offset']
        
        # Call configurable API method
        return await configurable_api.get_experiments_overview(
            limit=limit,
            offset=offset,
            database_service=database_service
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_message = get_config('experiments_overview_api.error_messages.overview_error', 
                                 "Failed to retrieve experiments overview: {error}", 
                                 'experiments_overview_api.error_messages')
        raise HTTPException(
            status_code=500,
            detail=error_message.format(error=str(e))
        ) 
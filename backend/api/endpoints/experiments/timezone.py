"""
Configurable Timezone Management API Endpoint
Handles timezone configuration with configurable validation and timezone data
"""

import logging
import sys
import os
import json
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Path, Depends
from pydantic import BaseModel

# Setup unified path configuration
from ...common.path_config import setup_project_paths
setup_project_paths()

from config.unified_config_manager import get_config, get_log_message

logger = logging.getLogger(__name__)

class TimezoneUpdateRequest(BaseModel):
    timezone: str

router = APIRouter()

# Use unified dependency injection
from ...common.dependencies import get_database_service_instance

try:
    from database.services.timezone_manager import timezone_manager
except ImportError:
    from backend.api.common.timezone_manager import timezone_manager

@router.get("/{experiment_id}/timezone")
async def get_experiment_timezone(
    experiment_id: str = Path(..., description="Experiment ID"),
    database_service = Depends(get_database_service_instance)
):
    """
    Get experiment timezone settings
    """
    try:
        # Use global timezone_manager instance
        tz_info = timezone_manager.get_timezone_info(timezone_manager.get_experiment_timezone(experiment_id))
        
        return {
            "experiment_id": experiment_id,
            "timezone": tz_info["timezone"],
            "currentTime": tz_info["current_time"],
            "current_time": tz_info["current_time"],
            "currentTimeDisplay": tz_info.get("timezone_display", tz_info["timezone"]),
            "utcOffset": tz_info["utc_offset"],
            "isDst": tz_info["is_dst"],
            "supported_timezones": list(timezone_manager.supported_timezones.keys())
        }
        
    except Exception as e:
        logger.error(f"Error getting timezone for experiment {experiment_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve timezone for experiment '{experiment_id}'"
        )

@router.put("/{experiment_id}/timezone")
async def update_experiment_timezone(
    experiment_id: str = Path(..., description="Experiment ID"),
    request: TimezoneUpdateRequest = ...,
    database_service = Depends(get_database_service_instance)
):
    """
    Update experiment timezone settings
    """
    try:
        # Use global timezone_manager instance
        success = timezone_manager.set_experiment_timezone(experiment_id, request.timezone)
        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid timezone: {request.timezone}"
            )
        
        # Get updated timezone information
        tz_info = timezone_manager.get_timezone_info(request.timezone)
        
        return {
            "experiment_id": experiment_id,
            "timezone": tz_info["timezone"],
            "currentTime": tz_info["current_time"],  # Use frontend expected field name
            "current_time": tz_info["current_time"], # Keep compatibility
            "currentTimeDisplay": tz_info.get("timezone_display", tz_info["timezone"]),
            "utcOffset": tz_info["utc_offset"],
            "isDst": tz_info["is_dst"],
            "supported_timezones": list(timezone_manager.supported_timezones.keys()),
            "updated": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting timezone for experiment {experiment_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update timezone for experiment '{experiment_id}'"
        )

@router.get("/timezones")
async def get_supported_timezones():
    """
    Get supported timezones list
    """ 
    try:
        # Use global timezone_manager instance to get supported timezones
        supported_timezones = list(timezone_manager.supported_timezones.keys())
        
        return {
            "supported_timezones": supported_timezones
        }
        
    except Exception as e:
        logger.error(f"Error getting supported timezones: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve supported timezones"
        )

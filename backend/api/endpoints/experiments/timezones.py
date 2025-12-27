"""
Timezone Management API Endpoints

Handles timezone settings for experiments and provides timezone information.
Enhanced with PCAP timezone support.
"""

import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List, Any

from ...common.dependencies import get_timezone_manager
from ....pcap_process.utils.timezone_processor import timezone_processor

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{experiment_id}/timezone")
async def get_experiment_timezone(
    experiment_id: str,
    timezone_manager = Depends(get_timezone_manager)
) -> Dict[str, Any]:
    """
    Get current timezone for an experiment
    
    Args:
        experiment_id: Experiment identifier
        
    Returns:
        Dictionary containing timezone information
    """
    try:
        timezone = timezone_manager.get_experiment_timezone(experiment_id)
        current_time = timezone_manager.get_current_time_in_timezone(experiment_id)
        
        return {
            "experiment_id": experiment_id,
            "timezone": timezone,
            "current_time": current_time.isoformat(),
            "utc_offset": timezone_manager.get_timezone_offset(timezone)
        }
        
    except Exception as e:
        logger.error(f"Error getting timezone for experiment {experiment_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting timezone: {str(e)}")


@router.post("/{experiment_id}/timezone")
async def set_experiment_timezone(
    experiment_id: str,
    request: Dict[str, str],
    timezone_manager = Depends(get_timezone_manager)
) -> Dict[str, Any]:
    """
    Set timezone for an experiment
    
    Args:
        experiment_id: Experiment identifier
        request: Dictionary with 'timezone' key
        
    Returns:
        Updated timezone information
    """
    try:
        timezone = request.get('timezone')
        if not timezone:
            raise HTTPException(status_code=400, detail="Timezone is required")
        
        timezone_manager.set_experiment_timezone(experiment_id, timezone)
        current_time = timezone_manager.get_current_time_in_timezone(experiment_id)
        
        return {
            "experiment_id": experiment_id,
            "timezone": timezone,
            "current_time": current_time.isoformat(),
            "utc_offset": timezone_manager.get_timezone_offset(timezone),
            "updated": True
        }
        
    except Exception as e:
        logger.error(f"Error setting timezone for experiment {experiment_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error setting timezone: {str(e)}")


@router.get("/timezones")
async def get_supported_timezones() -> Dict[str, Any]:
    """
    Get all supported timezones for experiments and PCAP processing
    
    Returns:
        Dictionary containing supported timezones from both systems
    """
    try:
        # Get experiment timezones (existing system)
        experiment_timezones = {
            'America/New_York': -4,  # EDT (summer)
            'Europe/London': 1,      # BST (summer)
            'Asia/Shanghai': 8,      # CST
            'Europe/Berlin': 2,      # CEST (summer)
            'America/Los_Angeles': -7, # PDT (summer)
            'Asia/Tokyo': 9,         # JST
            'Australia/Sydney': 10,  # AEST (winter)
        }
        
        # Get PCAP timezones (new system)
        pcap_timezones = timezone_processor.get_supported_timezones()
        
        return {
            "experiment_timezones": {
                "description": "Full timezone names for experiment display",
                "timezones": experiment_timezones
            },
            "pcap_timezones": {
                "description": "Short timezone codes for PCAP filename processing", 
                "timezones": pcap_timezones
            },
            "total_supported": len(experiment_timezones) + len(pcap_timezones)
        }
        
    except Exception as e:
        logger.error(f"Error getting supported timezones: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting timezones: {str(e)}")


@router.get("/pcap-timezones")
async def get_pcap_timezones() -> Dict[str, Any]:
    """
    Get supported timezone codes for PCAP filename processing
    
    Returns:
        Dictionary containing PCAP timezone codes and their UTC offsets
    """
    try:
        pcap_timezones = timezone_processor.get_supported_timezones()
        
        return {
            "supported_codes": pcap_timezones,
            "count": len(pcap_timezones),
            "filename_format": "MAC_YY-MM-DD-HH-MM-SS_TIMEZONE.pcap",
            "examples": [
                "00:17:88:24:76:FF_25-06-23-14-21-48_EDT.pcap",
                "AA:BB:CC:DD:EE:FF_25-12-31-23-59-59_BST.pcap",
                "12:34:56:78:9A:BC_25-06-24-10-57-24_UTC.pcap"
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting PCAP timezones: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting PCAP timezones: {str(e)}")


@router.post("/validate-pcap-filename")
async def validate_pcap_filename(request: Dict[str, str]) -> Dict[str, Any]:
    """
    Validate PCAP filename format and extract metadata
    
    Args:
        request: Dictionary with 'filename' key
        
    Returns:
        Validation result and extracted metadata
    """
    try:
        filename = request.get('filename')
        if not filename:
            raise HTTPException(status_code=400, detail="Filename is required")
        
        # Parse filename using timezone processor
        mac_address, timestamp_str, timezone_code = timezone_processor.parse_pcap_filename(filename)
        
        is_valid = all([mac_address, timestamp_str, timezone_code])
        
        result = {
            "filename": filename,
            "is_valid": is_valid,
            "extracted_data": {
                "mac_address": mac_address,
                "timestamp_str": timestamp_str,
                "timezone_code": timezone_code
            }
        }
        
        if is_valid:
            # Get additional timezone information
            timezone_offset = timezone_processor.get_timezone_offset(timezone_code)
            is_supported_timezone = timezone_processor.validate_timezone_code(timezone_code)
            
            result["timezone_info"] = {
                "utc_offset": timezone_offset,
                "is_supported": is_supported_timezone
            }
        
        return result
        
    except Exception as e:
        logger.error(f"Error validating PCAP filename: {e}")
        raise HTTPException(status_code=500, detail=f"Error validating filename: {str(e)}") 
"""
Experiment with the API endpoint of the network traffic Sankey diagram
Provide traffic analysis apis from devices to geographical locations, between devices, and from protocols to services
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks

# Setup unified path configuration
from ...common.path_config import setup_project_paths
setup_project_paths()

from ...common.dependencies import get_database_service_instance

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/{experiment_id}/network-flow-sankey")
async def get_experiment_network_flow_sankey(
    experiment_id: str,
    background_tasks: BackgroundTasks,
    flow_type: str = Query(
        default="device-to-location",
        description="Traffic analysis type: device-to-location, device-to-device, protocol-to-service"
    ),
    time_window: str = Query(
        default="24h", 
        description="Time window: 1h, 6h, 12h, 24h, 48h"
    ),
    group_by: str = Query(
        default="device_type",
        description="Device grouping method: device_type, manufacturer, device_name (only for device-to-location)"
    ),
    database_service = Depends(get_database_service_instance)
):
    """
    Get the network traffic Sankey diagram data for the experiment
    
    Parameters:
    - experiment_id: Experiment ID
    - flow_type: Traffic analysis type
      - device-to-location: Traffic distribution from devices to geographical locations
      - device-to-device: Device-to-device communication traffic
      - protocol-to-service: Protocol-to-service traffic distribution
    - time_window: Time window
    - group_by: Device grouping method (only for device-to-location)
    
    Returns:
    - Sankey diagram data, including node and connection information
    """
    try:
        logger.info(f"Fetching network flow sankey data for experiment {experiment_id}, type: {flow_type}")
        
        # Validate parameters
        valid_flow_types = ["device-to-location", "device-to-device", "protocol-to-service"]
        if flow_type not in valid_flow_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid flow_type. Must be one of: {', '.join(valid_flow_types)}"
            )
        
        valid_time_windows = ["auto", "1h", "2h", "6h", "12h", "24h", "48h"]
        if time_window not in valid_time_windows:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid time_window. Must be one of: {', '.join(valid_time_windows)}"
            )
        
        if flow_type == "device-to-location":
            valid_group_by = ["device_type", "manufacturer", "device_name"]
            if group_by not in valid_group_by:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid group_by for device-to-location. Must be one of: {', '.join(valid_group_by)}"
                )
        
        # Check if the experiment exists
        db_manager = database_service.db_manager
        experiment_check_query = "SELECT experiment_id FROM experiments WHERE experiment_id = $1"
        experiment_result = await db_manager.execute_query(experiment_check_query, (experiment_id,))
        
        if not experiment_result:
            raise HTTPException(
                status_code=404,
                detail=f"Experiment {experiment_id} not found"
            )
        
        # Import the Sankey flow analyzer
        from backend.pcap_process.analyzers.network.sankey_flow_analyzer import SankeyFlowAnalyzer
        analyzer = SankeyFlowAnalyzer(db_manager)
        
        # Perform the corresponding analysis based on the traffic type
        if flow_type == "device-to-location":
            result = await analyzer.analyze_device_to_location_flow(
                experiment_id, time_window, group_by
            )
        elif flow_type == "device-to-device":
            result = await analyzer.analyze_device_to_device_flow(
                experiment_id, time_window
            )
        elif flow_type == "protocol-to-service":
            result = await analyzer.analyze_protocol_to_service_flow(
                experiment_id, time_window
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported flow_type: {flow_type}"
            )
        
        # Add API call information
        result['api_info'] = {
            'timestamp': logger.handlers[0].formatter.formatTime(
                logger.handlers[0], logger.handlers[0].format(
                    logging.LogRecord(
                        name=logger.name,
                        level=logging.INFO,
                        pathname="",
                        lineno=0,
                        msg="",
                        args=(),
                        exc_info=None
                    )
                )
            ) if logger.handlers else None,
            'request_params': {
                'experiment_id': experiment_id,
                'flow_type': flow_type,
                'time_window': time_window,
                'group_by': group_by if flow_type == "device-to-location" else None
            }
        }
        
        logger.info(f"Successfully generated {flow_type} sankey data for experiment {experiment_id}: "
                   f"{result['metadata']['total_nodes']} nodes, {result['metadata']['total_links']} links")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating network flow sankey data for experiment {experiment_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/{experiment_id}/location-statistics")
async def get_experiment_location_statistics(
    experiment_id: str,
    background_tasks: BackgroundTasks,
    database_service = Depends(get_database_service_instance)
):
    """
    Get the geographical location statistics for the experiment
    
    Parameters:
    - experiment_id: Experiment ID
    
    Returns:
    - Geographical location statistics, including country distribution, city distribution, etc.
    """
    try:
        logger.info(f"Fetching location statistics for experiment {experiment_id}")
        
        # Check if the experiment exists
        db_manager = database_service.db_manager
        experiment_check_query = "SELECT experiment_id FROM experiments WHERE experiment_id = $1"
        experiment_result = await db_manager.execute_query(experiment_check_query, (experiment_id,))
        
        if not experiment_result:
            raise HTTPException(
                status_code=404,
                detail=f"Experiment {experiment_id} not found"
            )
        
        # Use the geographical location service to get the statistics
        from backend.services.ip_geolocation_service import IPGeolocationService
        geolocation_service = IPGeolocationService(db_manager)
        
        stats = await geolocation_service.get_location_statistics(experiment_id)
        
        logger.info(f"Successfully retrieved location statistics for experiment {experiment_id}: "
                   f"{stats['total_unique_ips']} unique IPs, {stats['location_coverage']:.1f}% coverage")
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting location statistics for experiment {experiment_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.post("/{experiment_id}/refresh-location-cache")
async def refresh_experiment_location_cache(
    experiment_id: str,
    background_tasks: BackgroundTasks,
    force_refresh: bool = Query(
        default=False,
        description="Whether to force refresh all IP geographical location cache"
    ),
    database_service = Depends(get_database_service_instance)
):
    """
    Refresh the IP geographical location cache for the experiment
    
    Parameters:
    - experiment_id: Experiment ID
    - force_refresh: Whether to force refresh all cache
    
    Returns:
    - Refresh result statistics
    """
    try:
        logger.info(f"Refreshing location cache for experiment {experiment_id}, force: {force_refresh}")
        
        # Check if the experiment exists
        db_manager = database_service.db_manager
        experiment_check_query = "SELECT experiment_id FROM experiments WHERE experiment_id = $1"
        experiment_result = await db_manager.execute_query(experiment_check_query, (experiment_id,))
        
        if not experiment_result:
            raise HTTPException(
                status_code=404,
                detail=f"Experiment {experiment_id} not found"
            )
        
        # Get all external IPs in the experiment
        query = """
        SELECT DISTINCT dst_ip as ip_address
        FROM packet_flows 
        WHERE experiment_id = $1 
        AND dst_ip IS NOT NULL 
        AND dst_ip != '0.0.0.0'::inet
        AND NOT (HOST(dst_ip) LIKE '192.168.%' OR HOST(dst_ip) LIKE '10.%' OR HOST(dst_ip) LIKE '172.%')
        """
        
        result = await db_manager.execute_query(query, (experiment_id,))
        unique_ips = [row['ip_address'] for row in result]
        
        if not unique_ips:
            return {
                'experiment_id': experiment_id,
                'total_ips': 0,
                'processed_ips': 0,
                'new_locations': 0,
                'updated_locations': 0,
                'failed_lookups': 0,
                'message': 'No external IPs found in experiment'
            }
        
        # Use the geographical location service to refresh the cache
        from backend.services.ip_geolocation_service import IPGeolocationService
        geolocation_service = IPGeolocationService(db_manager)
        
        # If force refresh, delete the existing cache first
        if force_refresh:
            delete_query = """
            DELETE FROM ip_geolocation_cache 
            WHERE ip_address = ANY($1)
            """
            await db_manager.execute_command(delete_query, (unique_ips,))
            logger.info(f"Cleared existing cache for {len(unique_ips)} IPs")
        
        # Batch get geographical location information (this will automatically update the cache)
        def refresh_task():
            """Background task: refresh geographical location cache"""
            import asyncio
            
            async def do_refresh():
                try:
                    locations = await geolocation_service.bulk_get_locations(unique_ips)
                    logger.info(f"Refreshed location cache: {len(locations)} IPs located out of {len(unique_ips)}")
                except Exception as e:
                    logger.error(f"Error in background refresh task: {e}")
            
            # Run the asynchronous task
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(do_refresh())
            loop.close()
        
        # Add background task
        background_tasks.add_task(refresh_task)
        
        # Immediately return the response, without waiting for the background task to complete
        return {
            'experiment_id': experiment_id,
            'total_ips': len(unique_ips),
            'refresh_started': True,
            'force_refresh': force_refresh,
            'message': f'Location cache refresh started for {len(unique_ips)} unique IPs. Check logs for progress.'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing location cache for experiment {experiment_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        ) 
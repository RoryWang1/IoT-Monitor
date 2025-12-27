"""
Broadcast management endpoint
"""

import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/admin/broadcast", tags=["admin", "broadcast"])

@router.post("/test/device-update/{device_id}")
async def test_device_update_broadcast(
    device_id: str,
    experiment_id: str = "experiment_1",
    background_tasks: BackgroundTasks = None
) -> Dict[str, Any]:
    """
    Device data update broadcast
    """
    try:
        # Get broadcast service
        from backend.api.services.broadcast_service import broadcast_service
        
        # Check if broadcast service is running
        if not broadcast_service.is_running():
            raise HTTPException(status_code=503, detail="Broadcast service not running")
        
        # Immediately trigger device data change broadcast
        await broadcast_service.broadcast_device_data_change(device_id, experiment_id, "manual_test")
        
        # Get WebSocket status
        websocket_manager = broadcast_service._get_websocket_manager()
        connection_count = websocket_manager.get_connection_count() if websocket_manager else 0
        
        detail_topic = f"devices.{device_id}.detail"
        subscriber_count = websocket_manager.get_topic_subscriber_count(detail_topic) if websocket_manager else 0
        
        return {
            "status": "success",
            "message": f"Device update broadcast triggered for {device_id}",
            "device_id": device_id,
            "experiment_id": experiment_id,
            "timestamp": datetime.now().isoformat(),
            "websocket_connections": connection_count,
            "topic_subscribers": subscriber_count,
            "topic": detail_topic
        }
        
    except Exception as e:
        logger.error(f"Error in test device update broadcast: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test/immediate-update")
async def test_immediate_broadcast() -> Dict[str, Any]:
    """
    Immediate broadcast update
    """
    try:
        from backend.api.services.broadcast_service import broadcast_service
        
        if not broadcast_service.is_running():
            raise HTTPException(status_code=503, detail="Broadcast service not running")
        
        # Trigger immediate update
        await broadcast_service.trigger_immediate_update()
        
        # Get status information
        websocket_manager = broadcast_service._get_websocket_manager()
        connection_count = websocket_manager.get_connection_count() if websocket_manager else 0
        total_topics = len(websocket_manager.get_all_topics()) if websocket_manager else 0
        
        return {
            "status": "success",
            "message": "Immediate broadcast update triggered",
            "timestamp": datetime.now().isoformat(),
            "websocket_connections": connection_count,
            "total_topics": total_topics
        }
        
    except Exception as e:
        logger.error(f"Error in immediate broadcast test: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_broadcast_status() -> Dict[str, Any]:
    """
    Get broadcast service status
    """
    try:
        from backend.api.services.broadcast_service import broadcast_service
        
        # Get broadcast service status
        is_running = broadcast_service.is_running()
        is_active = broadcast_service.is_active
        task_count = len(broadcast_service.broadcast_tasks)
        
        # Get WebSocket status
        websocket_manager = broadcast_service._get_websocket_manager()
        websocket_status = {
            "available": websocket_manager is not None,
            "connections": websocket_manager.get_connection_count() if websocket_manager else 0,
            "topics": websocket_manager.get_all_topics() if websocket_manager else [],
            "topic_count": len(websocket_manager.get_all_topics()) if websocket_manager else 0
        }
        
        return {
            "broadcast_service": {
                "running": is_running,
                "active": is_active,
                "tasks": task_count
            },
            "websocket_manager": websocket_status,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting broadcast status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/simulate/data-change")
async def simulate_data_change() -> Dict[str, Any]:
    """
    Simulate data change
    
    Simulate new data packets arriving, triggering a complete data update process
    """
    try:
        from backend.api.services.broadcast_service import broadcast_service
        from backend.api.common.dependencies import get_database_service_instance
        
        if not broadcast_service.is_running():
            raise HTTPException(status_code=503, detail="Broadcast service not running")
        
        # Get database service
        database_service = get_database_service_instance()
        if not database_service:
            raise HTTPException(status_code=503, detail="Database service not available")
        
        # Get all devices
        devices_data = await database_service.get_all_devices()
        if not devices_data:
            raise HTTPException(status_code=404, detail="No devices found")
        
        # Trigger data change broadcast for the first 3 devices
        updated_devices = []
        for device in devices_data[:3]:
            device_id = device.get('deviceId') or device.get('device_id')
            experiment_id = device.get('experimentId') or device.get('experiment_id', 'experiment_1')
            
            if device_id:
                await broadcast_service.broadcast_device_data_change(device_id, experiment_id, "simulated")
                updated_devices.append({
                    "device_id": device_id,
                    "experiment_id": experiment_id,
                    "device_name": device.get('deviceName', 'Unknown')
                })
        
        return {
            "status": "success",
            "message": "Data change simulation completed",
            "updated_devices": updated_devices,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in data change simulation: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 
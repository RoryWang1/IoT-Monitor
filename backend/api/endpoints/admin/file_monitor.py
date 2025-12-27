"""
File Monitor Admin Endpoints

Provides API endpoints for managing file monitoring service.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from backend.services.file_monitor_service import FileMonitorService
from config.unified_config_manager import get_log_message
import logging

logger = logging.getLogger(__name__)

# Global file monitor service instance
_monitor_service: Optional[FileMonitorService] = None

# Router for file monitor endpoints
router = APIRouter(prefix="/admin/file-monitor", tags=["admin", "file-monitor"])


@router.get("/status")
async def get_monitor_status():
    """Get file monitor service status"""
    try:
        if _monitor_service is None:
            return JSONResponse({
                "status": "not_initialized",
                "message": "File monitor service not initialized",
                "enabled": False,
                "scanning": False
            })
        
        # Get service status with datetime serialization
        stats = _monitor_service.processing_stats.copy()
        
        # Serialize datetime objects to ISO strings
        def serialize_datetime(obj):
            if hasattr(obj, 'isoformat'):
                return obj.isoformat()
            return obj
        
        serialized_stats = {}
        for key, value in stats.items():
            serialized_stats[key] = serialize_datetime(value)
        
        status = {
            "status": "running" if _monitor_service.is_running else "stopped",
            "enabled": _monitor_service.schedule_enabled,
            "scanning": _monitor_service.is_running,
            "scan_times": _monitor_service.scan_times,
            "timezone": str(_monitor_service.timezone),
            "stats": serialized_stats
        }
        
        return JSONResponse(status)
        
    except Exception as e:
        logger.error(get_log_message('file_monitor', 'status_check_failed', 
                                   component='file_monitor.api', error=str(e)))
        raise HTTPException(status_code=500, detail=f"Failed to get monitor status: {e}")


@router.post("/scan")
async def trigger_manual_scan():
    """Manually trigger a file scan"""
    try:
        if _monitor_service is None:
            raise HTTPException(status_code=503, detail="File monitor service not initialized")
        
        if not _monitor_service.is_running:
            raise HTTPException(status_code=503, detail="File monitor service not running")
        
        # Trigger a manual scan
        result = await _monitor_service.trigger_manual_scan()
        
        return JSONResponse({
            "status": "success",
            "message": "Manual scan triggered",
            "scan_result": result
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(get_log_message('file_monitor', 'manual_scan_failed', 
                                   component='file_monitor.api', error=str(e)))
        raise HTTPException(status_code=500, detail=f"Failed to trigger scan: {e}")


@router.post("/restart")
async def restart_monitor_service():
    """Restart the file monitor service with full configuration reload"""
    try:
        global _monitor_service
        
        if _monitor_service is None:
            raise HTTPException(status_code=503, detail="File monitor service not initialized")
        
        # Stop the current service
        if _monitor_service.is_running:
            await _monitor_service.stop_monitoring()
        
        # Completely recreate the service instance to reload configuration
        from backend.services.file_monitor_service import FileMonitorService
        from pathlib import Path
        from config.unified_config_manager import get_config
        
        # Get project root
        project_root = Path(__file__).parent.parent.parent.parent
        monitor_config_path = get_config('paths.file_monitor_config',
                                       str(project_root / "backend" / "config" / "file_monitor_config.json"),
                                       'app.file_monitor')
        
        # Create new service instance
        _monitor_service = FileMonitorService(monitor_config_path)
        
        # Initialize and start the new service
        if await _monitor_service.initialize():
            import asyncio
            asyncio.create_task(_monitor_service.start_monitoring_non_blocking())
            
            return JSONResponse({
                "status": "success",
                "message": "File monitor service restarted with configuration reload",
                "scan_times": _monitor_service.scan_times if hasattr(_monitor_service, 'scan_times') else [],
                "timezone": str(_monitor_service.timezone) if hasattr(_monitor_service, 'timezone') else "unknown"
            })
        else:
            raise HTTPException(status_code=500, detail="Failed to restart file monitor service")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(get_log_message('file_monitor', 'restart_failed', 
                                   component='file_monitor.api', error=str(e)))
        raise HTTPException(status_code=500, detail=f"Failed to restart service: {e}")


@router.get("/config")
async def get_monitor_config():
    """Get file monitor configuration"""
    try:
        if _monitor_service is None:
            raise HTTPException(status_code=503, detail="File monitor service not initialized")
        
        config = {
            "schedule_enabled": _monitor_service.schedule_enabled,
            "scan_times": _monitor_service.scan_times,
            "timezone": str(_monitor_service.timezone),
            "supported_extensions": list(_monitor_service.supported_extensions),
            "monitor_directories": [str(d) for d in _monitor_service.monitor_directories] if hasattr(_monitor_service, 'monitor_directories') else []
        }
        
        return JSONResponse(config)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(get_log_message('file_monitor', 'config_get_failed', 
                                   component='file_monitor.api', error=str(e)))
        raise HTTPException(status_code=500, detail=f"Failed to get configuration: {e}")


# Broadcast service routes
@router.get("/broadcast/status")
async def get_broadcast_status():
    """Get broadcast service status"""
    try:
        from backend.api.services.broadcast_service import broadcast_service
        
        status = {
            "status": "running" if broadcast_service.is_running else "stopped",
            "device_monitoring_enabled": broadcast_service.device_monitoring_enabled,
            "tasks_active": len(broadcast_service.background_tasks),
            "websocket_manager_ready": broadcast_service.websocket_manager is not None
        }
        
        return JSONResponse(status)
        
    except Exception as e:
        logger.error(f"Failed to get broadcast status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get broadcast status: {e}")


@router.post("/broadcast/start")
async def start_broadcast_service():
    """Start broadcast service"""
    try:
        from backend.api.services.broadcast_service import broadcast_service
        
        await broadcast_service.start_device_monitoring()
        
        return JSONResponse({
            "status": "success",
            "message": "Broadcast service started successfully"
        })
        
    except Exception as e:
        logger.error(f"Failed to start broadcast service: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start broadcast service: {e}")


@router.post("/broadcast/stop")
async def stop_broadcast_service():
    """Stop broadcast service"""
    try:
        from backend.api.services.broadcast_service import broadcast_service
        
        await broadcast_service.stop_device_monitoring()
        
        return JSONResponse({
            "status": "success",
            "message": "Broadcast service stopped successfully"
        })
        
    except Exception as e:
        logger.error(f"Failed to stop broadcast service: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop broadcast service: {e}")


@router.post("/broadcast/force-broadcast")
async def force_broadcast():
    """Force a manual broadcast to test the system"""
    try:
        from backend.api.services.broadcast_service import broadcast_service
        
        # Force an experiments overview broadcast
        await broadcast_service.broadcast_experiments_overview_update()
        
        return JSONResponse({
            "status": "success",
            "message": "Manual broadcast sent successfully"
        })
        
    except Exception as e:
        logger.error(f"Failed to send manual broadcast: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send manual broadcast: {e}")


# Make router available for app registration
__all__ = ["router", "_monitor_service"] 
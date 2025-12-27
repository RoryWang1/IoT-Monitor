#!/usr/bin/env python3
"""
IoT device monitoring API server
"""

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, Any, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Import unified config manager
import sys
from pathlib import Path

current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import unified config manager
from config.unified_config_manager import UnifiedConfigManager, get_config, get_log_message

# Create config manager instance
config_manager = UnifiedConfigManager()

# Import API config
from backend.api.api_config import config

if __name__ == "__main__":
    import multiprocessing
    if hasattr(multiprocessing, 'set_start_method'):
        try:
            multiprocessing.set_start_method('fork', force=True)
        except RuntimeError:
            pass

# Get logging settings from config
log_level = get_config('logging.level', config.LOG_LEVEL, 'app.logging').upper()
log_format = get_config('logging.format', 
                       '%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
                       'app.logging')

# Configure logging
logging.basicConfig(
    level=getattr(logging, log_level),
    format=log_format
)
logger = logging.getLogger(__name__)

# FastAPI imports
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import services
from backend.api.services.broadcast_service import broadcast_service

# Global service instance
database_service = None

# Import routes
from backend.api.endpoints.devices import detail as devices_detail
from backend.api.endpoints.devices import list as devices_list
from backend.api.endpoints.devices import port_analysis as devices_port_analysis
from backend.api.endpoints.devices import protocol_distribution as devices_protocol_distribution
from backend.api.endpoints.devices import network_topology as devices_network_topology
from backend.api.endpoints.devices import activity_timeline as devices_activity_timeline
from backend.api.endpoints.devices import traffic_trend as devices_traffic_trend
from backend.api.endpoints.devices import reference as devices_reference
from backend.api.endpoints.devices import resolution as devices_resolution
from backend.api.endpoints.devices import ingest as devices_ingest

from backend.api.endpoints.experiments import overview as experiments_overview
from backend.api.endpoints.experiments import detail as experiments_detail
from backend.api.endpoints.experiments import devices as experiments_devices
from backend.api.endpoints.experiments import timezone as experiments_timezone
from backend.api.endpoints.experiments import network_flow as experiments_network_flow


# Fix WebSocket routes import
try:
    from backend.api.websocket.websocket_routes import create_websocket_router
    websocket_router = create_websocket_router()
    logger.info(get_log_message('app', 'websocket_routes_loaded', component='app.websocket'))
except Exception as e:
    logger.warning(get_log_message('websocket', 'routes_unavailable', component='app.websocket', error=str(e)))
    # Create empty WebSocket routes as fallback
    from fastapi import APIRouter
    websocket_router = APIRouter()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    
    # Get startup configuration
    app_name = config.APP_NAME
    app_version = config.APP_VERSION
    startup_timeout = get_config('server.startup_timeout_seconds', 30, 'app.startup')
    enable_database = get_config('features.enable_database', True, 'app.features')
    enable_broadcast = get_config('features.enable_broadcast_service', True, 'app.features')
    enable_file_monitor = get_config('features.enable_file_monitoring', True, 'app.features')
    enable_websocket = get_config('features.enable_websocket', True, 'app.features')
    
    logger.info(get_log_message('startup', 'api_starting', component='app.startup',
                               app_name=app_name, version=app_version))
    
    try:
        # Initialize database manager
        if enable_database:
            logger.info(get_log_message('database', 'initializing', component='app.database'))
            from database.connection import PostgreSQLDatabaseManager
            db_manager = PostgreSQLDatabaseManager()
            await db_manager.initialize()
            
            # Initialize database service
            from database.services.database_service import DatabaseService
            global database_service
            database_service = DatabaseService(db_manager)
            
            # Register to dependency injection system immediately
            from backend.api.common.dependencies import register_database_service
            register_database_service(database_service)
            
            # Initialize database lifecycle service for automatic data cleanup
            try:
                logger.info(get_log_message('database', 'lifecycle_initializing', component='app.database'))
                from database.services.automated_data_lifecycle_service import AutomatedDataLifecycleService
                lifecycle_service = AutomatedDataLifecycleService(db_manager)
                
                # Initialize cleanup functions and scheduler
                await lifecycle_service.initialize_automated_lifecycle()
                
                # Get configuration from user_config
                cleanup_enabled = get_config('maintenance.database_cleanup.enabled', True, 'app.maintenance')
                if cleanup_enabled:
                    # Check if initial cleanup is needed
                    retention_days = get_config('data_retention.packet_flows_days', 8, 'app.data_retention')
                    retention_hours = retention_days * 24
                    
                    logger.info(get_log_message('database', 'lifecycle_configured', component='app.database',
                                               retention_days=retention_days, daily_time=get_config('maintenance.database_cleanup.daily_time', '02:00', 'app.maintenance')))
                    
                    # Run initial cleanup if needed (non-blocking)
                    asyncio.create_task(lifecycle_service.run_manual_cleanup(retention_hours))
                else:
                    logger.info(get_log_message('database', 'lifecycle_disabled', component='app.database'))
                
                logger.info(get_log_message('database', 'lifecycle_initialized', component='app.database'))
            except Exception as e:
                logger.warning(get_log_message('database', 'lifecycle_init_failed', component='app.database', error=str(e)))
            
            logger.info(get_log_message('database', 'service_initialized', component='app.database'))
        else:
            logger.info(get_log_message('database', 'service_disabled', component='app.database'))
        
        # Start broadcast service
        if enable_broadcast:
            logger.info(get_log_message('broadcast', 'service_starting', component='app.broadcast'))
            await broadcast_service.start_device_monitoring()
            logger.info(get_log_message('broadcast', 'service_started', component='app.broadcast'))
        else:
            logger.info(get_log_message('broadcast', 'service_disabled', component='app.broadcast'))
        
        # Start file monitoring service
        if enable_file_monitor:
            try:
                logger.info(get_log_message('file_monitoring', 'service_starting', component='app.file_monitor'))
                from backend.services.file_monitor_service import FileMonitorService
                from backend.api.endpoints.admin import file_monitor as monitor_module
                
                # Check if global monitoring service is initialized
                if monitor_module._monitor_service is None:
                    # Use configured path
                    monitor_config_path = get_config('paths.file_monitor_config',
                                                   str(project_root / "backend" / "config" / "file_monitor_config.json"),
                                                   'app.file_monitor')
                    
                    monitor_module._monitor_service = FileMonitorService(monitor_config_path)
                    
                if await monitor_module._monitor_service.initialize():
                    # Start monitoring in background
                    import asyncio
                    asyncio.create_task(monitor_module._monitor_service.start_monitoring_non_blocking())
                    logger.info(get_log_message('file_monitoring', 'service_started', component='app.file_monitor'))
                else:
                    logger.warning(get_log_message('file_monitoring', 'initialization_failed', component='app.file_monitor'))
            except Exception as e:
                logger.warning(get_log_message('file_monitoring', 'startup_failed', component='app.file_monitor', error=str(e)))
        else:
            logger.info(get_log_message('file_monitoring', 'service_disabled', component='app.file_monitor'))
        
        # Start WebSocket manager 
        if enable_websocket:
            try:
                logger.info(get_log_message('websocket', 'manager_starting', component='app.websocket'))
                from backend.api.websocket.manager_singleton import get_websocket_manager
                websocket_manager = get_websocket_manager()
                await websocket_manager.start()
                logger.info(get_log_message('websocket', 'manager_started', component='app.websocket'))
                
                # Restart broadcast service after WebSocket manager is ready
                # This ensures broadcast service gets the correct WebSocket manager instance
                if enable_broadcast:
                    logger.info(get_log_message('broadcast', 'service_restarting_post_websocket', component='app.broadcast'))
                    await broadcast_service.start_device_monitoring()  # 直接启动而不是ensure_service_running
                    logger.info(get_log_message('broadcast', 'service_restarted_post_websocket', component='app.broadcast'))
                    
                    # 验证广播服务是否真正运行
                    if not broadcast_service.is_running():
                        logger.error("Broadcast service failed to start")
                
            except ImportError:
                logger.warning(get_log_message('websocket', 'manager_unavailable', component='app.websocket'))
            except Exception as e:
                logger.warning(get_log_message('websocket', 'manager_startup_failed', component='app.websocket', error=str(e)))
        else:
            logger.info(get_log_message('websocket', 'manager_disabled', component='app.websocket'))
        
        # Final broadcast service verification and start
        if enable_broadcast:
            try:
                logger.info("🔧 最终广播服务验证和启动...")
                await broadcast_service.start_device_monitoring()
                
                # 验证状态
                if broadcast_service.is_active and len(broadcast_service.broadcast_tasks) > 0:
                    logger.info("✅ 最终验证: 广播服务正常运行")
                else:
                    logger.error("❌ 最终验证: 广播服务启动失败")
                    
            except Exception as e:
                logger.error(f"❌ 最终广播服务启动失败: {e}")
        
        # Startup completed
        architecture_type = get_config('server.architecture_type', 'database-driven', 'app.architecture')
        logger.info(get_log_message('startup', 'architecture_ready', component='app.startup', 
                                   architecture=architecture_type))
        
    except Exception as e:
        logger.critical(get_log_message('startup', 'critical_failure', component='app.startup', error=str(e)))
        raise RuntimeError(get_log_message('startup', 'system_cannot_start', component='app.startup', error=str(e))) from e
    
    yield
    
    # Cleanup
    shutdown_timeout = get_config('server.shutdown_timeout_seconds', 30, 'app.shutdown')
    logger.info(get_log_message('shutdown', 'starting', component='app.shutdown'))
    
    try:
        # Stop file monitoring service
        if enable_file_monitor:
            try:
                from backend.api.endpoints.admin import file_monitor as monitor_module
                if monitor_module._monitor_service and monitor_module._monitor_service.is_running:
                    await monitor_module._monitor_service.stop_monitoring()
                    logger.info(get_log_message('file_monitoring', 'service_stopped', component='app.shutdown'))
            except Exception as e:
                logger.warning(get_log_message('file_monitoring', 'stop_failed', component='app.shutdown', error=str(e)))
                
        # Stop WebSocket manager
        if enable_websocket:
            try:
                from backend.api.websocket.manager_singleton import get_websocket_manager
                websocket_manager = get_websocket_manager()
                await websocket_manager.stop()
                logger.info(get_log_message('websocket', 'manager_stopped', component='app.shutdown'))
            except ImportError:
                pass
            except Exception as e:
                logger.warning(get_log_message('websocket', 'manager_stop_failed', component='app.shutdown', error=str(e)))
                
        # Stop broadcast service
        if enable_broadcast:
            await broadcast_service.stop_device_monitoring()
            logger.info(get_log_message('broadcast', 'service_stopped', component='app.shutdown'))
        
        # Close database service
        if enable_database and database_service:
            await database_service.close()
            logger.info(get_log_message('database', 'service_closed', component='app.shutdown'))
            
        logger.info(get_log_message('shutdown', 'completed', component='app.shutdown'))
    except Exception as e:
        logger.error(get_log_message('shutdown', 'error', component='app.shutdown', error=str(e)))

# Create FastAPI app
app = FastAPI(
    title=config.APP_NAME,
    description=config.APP_DESCRIPTION,
    version=config.APP_VERSION,
    lifespan=lifespan
)

# Configure CORS
cors_settings = {
    'allow_origins': config.CORS_ORIGINS,
    'allow_credentials': get_config('server.cors.allow_credentials', True, 'app.cors'),
    'allow_methods': get_config('server.cors.allow_methods', ["*"], 'app.cors'),
    'allow_headers': get_config('server.cors.allow_headers', ["*"], 'app.cors')
}

app.add_middleware(CORSMiddleware, **cors_settings)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        health_info = {
            "status": "healthy",
            "version": config.APP_VERSION,
            "timestamp": get_config('features.include_timestamp_in_health', True, 'app.health'),
            "architecture": {
                "type": get_config('server.architecture_type', 'database-driven', 'app.health'),
                "data_layer": get_config('server.data_layer', 'database', 'app.health'),
                "api_layer": get_config('server.api_layer', 'fastapi', 'app.health')
            }
        }
        
        # Database health check
        enable_db_health_check = get_config('health_check.include_database', True, 'app.health')
        if enable_db_health_check and database_service:
            db_health = await database_service.get_database_health()
            health_info["architecture"]["database_status"] = db_health.get("status", "unknown")
            health_info["services"] = {
                "database_service": db_health.get("status", "unknown"),
                "broadcast_service": "running" if broadcast_service.is_running() else "stopped"
            }
        
        return health_info
        
    except Exception as e:
        error_message = get_log_message('admin', 'health_check_failed', component='app.health', error=str(e))
        logger.error(error_message)
        
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "version": config.APP_VERSION,
                "timestamp": get_config('features.include_timestamp_in_health', True, 'app.health')
            }
        )

# Test endpoint
@app.get("/api/test")
async def test_endpoint():
    """Simple test endpoint"""
    test_response = {
        "message": get_config('api.test_endpoint.message', 'Backend is working!', 'app.test'),
        "timestamp": "now()",
        "status": "success",
        "version": config.APP_VERSION
    }
    
    # Optional extended information
    include_config_info = get_config('api.test_endpoint.include_config_info', False, 'app.test')
    if include_config_info:
        test_response["config_info"] = {
            "environment": config_manager.environment,
            "total_config_accesses": config_manager.get_usage_stats()["total_accesses"]
        }
    
    return test_response

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": config.APP_NAME,
        "version": config.APP_VERSION,
        "architecture": get_config('server.architecture_type', 'database-driven', 'app.root'),
        "status": "running",
        "environment": config_manager.environment
    }

# Register routes
def register_routes():
    """Register API routes"""
    
    # Devices related routes
    if get_config('api.routes.devices.enabled', True, 'app.routes'):
        app.include_router(devices_list.router, prefix="/api/devices", tags=["devices"])
        app.include_router(devices_detail.router, prefix="/api/devices", tags=["devices"])
        app.include_router(devices_port_analysis.router, prefix="/api/devices", tags=["devices"])
        app.include_router(devices_resolution.router, prefix="/api/devices", tags=["devices"])
        app.include_router(devices_protocol_distribution.router, prefix="/api/devices", tags=["devices"])
        app.include_router(devices_network_topology.router, prefix="/api/devices", tags=["devices"])
        app.include_router(devices_activity_timeline.router, prefix="/api/devices", tags=["devices"])
        app.include_router(devices_traffic_trend.router, prefix="/api/devices", tags=["devices"])
        
        # v1 endpoints for high-throughput ingestion
        app.include_router(devices_ingest.router, prefix="/api/v1/devices", tags=["devices", "ingest"])

        app.include_router(devices_reference.router, prefix="/api/devices/reference", tags=["devices", "reference"])
        logger.info(get_log_message('startup', 'devices_routes_registered', component='app.routes'))
    
    # Experiments related routes
    if get_config('api.routes.experiments.enabled', True, 'app.routes'):
        app.include_router(experiments_overview.router, prefix="/api/experiments", tags=["experiments"])
        # Timezone routes must be before experiment detail routes to avoid /{experiment_id} matching /timezones
        app.include_router(experiments_timezone.router, prefix="/api/experiments", tags=["experiments"])
        app.include_router(experiments_detail.router, prefix="/api/experiments", tags=["experiments"])
        app.include_router(experiments_devices.router, prefix="/api/experiments", tags=["experiments"])
        app.include_router(experiments_network_flow.router, prefix="/api/experiments", tags=["experiments", "sankey"])
        logger.info(get_log_message('startup', 'experiments_routes_registered', component='app.routes'))

    # Admin routes - file monitoring
    if get_config('api.routes.admin.enabled', True, 'app.routes'):
        from backend.api.endpoints.admin import file_monitor
        app.include_router(file_monitor.router, prefix="/api", tags=["admin"])
        
        # Register broadcast test routes
        from backend.api.endpoints.admin import broadcast_test
        app.include_router(broadcast_test.router, prefix="/api", tags=["admin"])
        
        logger.info(get_log_message('startup', 'admin_routes_registered', component='app.routes'))
        


    # WebSocket routes
    if get_config('api.routes.websocket.enabled', True, 'app.routes'):
        app.include_router(websocket_router, prefix="/ws", tags=["websocket"])
        logger.info(get_log_message('app', 'websocket_routes_registered', component='app.routes'))

# Register all routes
register_routes()

if __name__ == "__main__":
    import uvicorn
    
    # Get server configuration
    server_host = config.HOST
    server_port = config.PORT
    server_reload = config.RELOAD
    server_log_level = config.LOG_LEVEL
    
    logger.info(get_log_message('startup', 'server_starting', component='app.server',
                               host=server_host, port=server_port))
    
    # Get uvicorn configuration
    uvicorn_config = {
        'host': server_host,
        'port': server_port,
        'reload': server_reload,
        'log_level': server_log_level
    }
    
    # Optional uvicorn configuration
    if get_config('server.uvicorn.workers', None, 'app.uvicorn'):
        uvicorn_config['workers'] = get_config('server.uvicorn.workers', 1, 'app.uvicorn')
    
    if get_config('server.uvicorn.access_log', None, 'app.uvicorn'):
        uvicorn_config['access_log'] = get_config('server.uvicorn.access_log', True, 'app.uvicorn')
    
    uvicorn.run("app:app", **uvicorn_config) 
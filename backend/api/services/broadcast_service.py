"""
WebSocket broadcast service
Handle real-time data broadcast for device monitoring
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Set, Optional

# Add config directory to Python path
config_path = Path(__file__).parent.parent.parent.parent / "config"
sys.path.insert(0, str(config_path))

# Import unified config manager
from config.unified_config_manager import UnifiedConfigManager, get_config, get_log_message

logger = logging.getLogger(__name__)

# Create config manager instance
config_manager = UnifiedConfigManager()

class BroadcastService:
    """
    WebSocket broadcast service
    """
    
    def __init__(self):
        """Initialize broadcast service"""
        self.is_active = False
        self.broadcast_tasks = set()
        self._websocket_manager = None
        self.config_manager = config_manager
        
    @property
    def websocket_manager(self):
        """Property to access WebSocket manager for external checks"""
        return self._get_websocket_manager()
        
    def _get_websocket_manager(self):
        """Get WebSocket manager instance"""
        if self._websocket_manager is None:
            try:
                from ..websocket.manager_singleton import get_websocket_manager
                self._websocket_manager = get_websocket_manager()
            except ImportError:
                logger.error(get_log_message(
                    'websocket', 'manager_import_failed',
                    component='broadcast.websocket'
                ))
                return None
        return self._websocket_manager
        
    async def add_connection(self, websocket):
        """Add connection - delegate to WebSocket manager"""
        logger.debug(get_log_message(
            'websocket', 'connection_delegated',
            component='broadcast.connection'
        ))
        
    async def remove_connection(self, websocket):
        """Remove connection - Delegate to the WebSocket manager"""
        logger.debug(get_log_message(
            'websocket', 'connection_delegated',
            component='broadcast.connection'
        ))
        
    async def emit_event(self, event_type: str, data: Dict[str, Any]):
        """Send events to all connected clients - through the WebSocket manager"""
        websocket_manager = self._get_websocket_manager()
        if not websocket_manager:
            logger.error(get_log_message(
                'websocket', 'manager_not_available',
                component='broadcast.emit',
                event_type=event_type
            ))
            return
            
        connection_count = websocket_manager.get_connection_count()
        
        # Get broadcast behavior settings from configuration
        should_broadcast_without_connections = get_config(
            'websocket.broadcast_without_connections', True, 'broadcast.emit'
        )
        suppress_warnings = get_config(
            'websocket.suppress_broadcast_warnings', True, 'broadcast.emit'
        )
        
        if connection_count == 0:
            if not should_broadcast_without_connections:
                if not suppress_warnings:
                    logger.info(get_log_message(
                        'broadcast', 'skipping_no_connections',
                        component='broadcast.emit',
                        event_type=event_type
                    ))
                return
            
            if not suppress_warnings:
                logger.warning(get_log_message(
                    'websocket', 'no_connections_warning',
                    component='broadcast.emit',
                    event_type=event_type
                ))
            else:
                logger.debug(get_log_message(
                    'broadcast', 'broadcasting_no_connections',
                    component='broadcast.emit',
                    event_type=event_type
                ))
            # 继续执行广播，不要return
        
        logger.info(get_log_message(
            'broadcast', 'event_broadcasting',
            component='broadcast.emit',
            topic=event_type,
            message_type="broadcast_update"
        ))
            
        # Use the broadcast method of the WebSocket manager
        await websocket_manager.broadcast_to_topic(event_type, data)
        
        logger.info(get_log_message(
            'broadcast', 'event_broadcasted',
            component='broadcast.emit',
            topic=event_type,
            subscriber_count=connection_count
        ))
    
    def _get_database_service(self):
        """Get database service instance from dependency injection registry"""
        try:
            # Use dependency injection system to get the properly initialized service
            from backend.api.common.dependencies import _service_registry
            
            # Check if database service is in registry (set by main app during startup)
            if 'database_service' in _service_registry and _service_registry['database_service'] is not None:
                logger.debug(get_log_message(
                    'database', 'service_from_registry',
                    component='broadcast.database'
                ))
                return _service_registry['database_service']
            
            logger.warning(get_log_message(
                'database', 'service_not_in_registry',
                component='broadcast.database',
                registry_keys=list(_service_registry.keys())
            ))
            return None
                
        except Exception as e:
            logger.error(get_log_message(
                'database', 'service_access_failed',
                component='broadcast.database',
                error=str(e)
            ))
            return None
    
    async def start_device_monitoring(self):
        """Start device monitoring broadcast"""
        try:
            # 清理已完成的任务
            self.broadcast_tasks = {t for t in self.broadcast_tasks if not t.done()}
            
            # 如果已经在运行且状态正确，直接返回
            if self.is_active and len(self.broadcast_tasks) > 0:
                logger.debug("Broadcast service already running with active tasks, skipping restart")
                return
            
            # 只有在状态不一致时才停止现有任务
            if len(self.broadcast_tasks) > 0 and not self.is_active:
                await self.stop_device_monitoring()
            
            self.is_active = True
            logger.info(get_log_message(
                'broadcast', 'device_monitoring_started',
                component='broadcast.monitoring'
            ))
            
            # Create periodic background tasks
            task = asyncio.create_task(self._periodic_device_updates())
            self.broadcast_tasks.add(task)
            
            # 验证任务是否成功创建
            if len(self.broadcast_tasks) == 0:
                logger.error("Failed to create broadcast task")
            
        except Exception as e:
            logger.error(get_log_message(
                'broadcast', 'monitoring_start_error',
                component='broadcast.monitoring',
                error=str(e)
            ))
    
    async def stop_device_monitoring(self):
        """Stop device monitoring broadcast"""
        try:
            self.is_active = False
            
            # Cancel all broadcast tasks
            for task in self.broadcast_tasks:
                if not task.done():
                    task.cancel()
            
            self.broadcast_tasks.clear()
            logger.info(get_log_message(
                'broadcast', 'monitoring_stopped',
                component='broadcast.monitoring'
            ))
            
        except Exception as e:
            logger.error(get_log_message(
                'broadcast', 'monitoring_stop_error',
                component='broadcast.monitoring',
                error=str(e)
            ))
    
    async def _periodic_device_updates(self):
        """Periodic device and experiment update broadcast"""
        while self.is_active:
            try:
                # Get broadcast interval from configuration
                broadcast_interval = get_config(
                    'device_monitoring.broadcast_interval_seconds', 30, 'broadcast.periodic'
                )
                
                # 确保WebSocket管理器可用
                websocket_manager = self._get_websocket_manager()
                if not websocket_manager:
                    await asyncio.sleep(broadcast_interval)
                    continue
                
                # Broadcast both devices and experiments overview
                await self.broadcast_devices_overview()
                await self.broadcast_experiments_overview()
                
                # NEW: 广播所有设备的详细信息更新
                await self.broadcast_all_device_details()
                
                await asyncio.sleep(broadcast_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Periodic broadcast error: {e}")
                await asyncio.sleep(10)
    

    
    async def broadcast_device_detail(self, device_id: str, experiment_id: str = None, time_window: str = "48h"):
        """Broadcast device detail update"""
        try:
            database_service = self._get_database_service()
            if not database_service:
                logger.debug(get_log_message(
                    'database', 'service_not_available',
                    component='broadcast.device_detail',
                    action='device detail broadcast'
                ))
                return
                
            device_data = await database_service.get_device_detail(device_id, experiment_id, time_window)
            
            await self.emit_event(
                f"devices.{device_id}.detail",
                device_data
            )
            logger.info(get_log_message(
                'broadcast', 'device_detail_updated',
                component='broadcast.device_detail',
                device_id=device_id,
                experiment_id=experiment_id,
                time_window=time_window
            ))
        except Exception as e:
            logger.error(get_log_message(
                'broadcast', 'device_detail_error',
                component='broadcast.device_detail',
                device_id=device_id,
                error=str(e)
            ))
    
    async def broadcast_device_traffic_trend(self, device_id: str, time_window: str = "24h"):
        """Broadcast device traffic trend update"""
        try:
            database_service = self._get_database_service()
            if not database_service:
                logger.debug(get_log_message(
                    'database', 'service_not_available',
                    component='broadcast.traffic_trend',
                    action='traffic trend broadcast'
                ))
                return
                
            trend_data = await database_service.get_device_traffic_trend(device_id, time_window)
            
            await self.emit_event(
                f"devices.{device_id}.traffic_trend",
                trend_data
            )
            logger.info(get_log_message(
                'broadcast', 'traffic_trend_updated',
                component='broadcast.traffic_trend',
                device_id=device_id,
                time_window=time_window
            ))
        except Exception as e:
            logger.error(get_log_message(
                'broadcast', 'traffic_trend_error',
                component='broadcast.traffic_trend',
                device_id=device_id,
                error=str(e)
            ))

    async def broadcast_devices_overview(self):
        """Broadcast devices overview data"""
        try:
            database_service = self._get_database_service()
            if not database_service:
                logger.debug(get_log_message(
                    'database', 'service_not_available',
                    component='broadcast.devices_overview',
                    action='devices overview broadcast'
                ))
                return
                
            devices_data = await database_service.get_all_devices()
            
            # Broadcast to devices overview topic
            await self.emit_event(
                "devices.overview",
                devices_data
            )
        except Exception as e:
            logger.error(get_log_message(
                'broadcast', 'devices_overview_error',
                component='broadcast.devices_overview',
                error=str(e)
            ))

    async def broadcast_experiments_overview(self):
        """Broadcast experiments overview data"""
        try:
            database_service = self._get_database_service()
            if not database_service:
                logger.debug(get_log_message(
                    'database', 'service_not_available',
                    component='broadcast.experiments_overview',
                    action='experiments overview broadcast'
                ))
                return
            
            # Ensure database manager is initialized
            if hasattr(database_service, 'db_manager') and database_service.db_manager:
                try:
                    # Check if db_manager is initialized, if not initialize it
                    if not hasattr(database_service.db_manager, '_initialized') or not database_service.db_manager._initialized:
                        await database_service.db_manager.initialize()
                except Exception as init_error:
                    logger.warning(get_log_message(
                        'database', 'manager_init_failed',
                        component='broadcast.experiments_overview',
                        error=str(init_error)
                    ))
                    return
                
            experiments_data = await database_service.get_experiments_overview()
            
            # Broadcast to experiments overview topic
            await self.emit_event(
                "experiments.overview",
                experiments_data
            )
        except Exception as e:
            logger.error(get_log_message(
                'broadcast', 'experiments_overview_error',
                component='broadcast.experiments_overview',
                error=str(e)
            ))

    async def broadcast_all_device_details(self):
        """广播所有设备的详细信息更新 - 解决device detail页面无法自动更新的问题"""
        try:
            database_service = self._get_database_service()
            if not database_service:
                return
            
            # 获取所有设备
            devices_data = await database_service.get_all_devices()
            if not devices_data:
                return
            
            # 检查是否有WebSocket连接
            websocket_manager = self._get_websocket_manager()
            if not websocket_manager or websocket_manager.get_connection_count() == 0:
                return  # 没有连接时不广播，节省资源
            
            # 为每个设备广播详细信息（只广播给有订阅的设备）
            broadcast_count = 0
            for device in devices_data:
                device_id = device.get('deviceId') or device.get('device_id')
                experiment_id = device.get('experimentId') or device.get('experiment_id', 'experiment_1')
                
                if not device_id:
                    continue
                
                # 检查是否有人订阅了这个设备的详情
                detail_topic = f"devices.{device_id}.detail"
                if websocket_manager.get_topic_subscriber_count(detail_topic) == 0:
                    continue  # 没有订阅者，跳过
                
                try:
                    # 获取设备详细信息
                    device_detail = await database_service.get_device_detail(device_id, experiment_id)
                    if device_detail:
                        # 广播到设备特定的topic
                        await self.emit_event(detail_topic, device_detail)
                        broadcast_count += 1
                    
                    # 限制广播频率，避免过载
                    await asyncio.sleep(0.02)  # 20ms间隔
                    
                except Exception as device_error:
                    logger.debug(f"Failed to broadcast detail for device {device_id}: {device_error}")
                    continue
            
            if broadcast_count > 0:
                logger.debug(f"Broadcasted device details for {broadcast_count} subscribed devices")
            
        except Exception as e:
            logger.debug(f"Error in broadcast_all_device_details: {e}")

    def is_running(self) -> bool:
        """Check if the broadcast service is running"""
        return self.is_active and len(self.broadcast_tasks) > 0
    
    async def ensure_service_running(self):
        """确保广播服务正在运行，如果不是则重启"""
        if not self.is_running():
            logger.warning("🔄 广播服务未运行，正在重启...")
            await self.start_device_monitoring()
            
            # 等待一会儿验证启动是否成功
            import asyncio
            await asyncio.sleep(1)
            
            if self.is_running():
                logger.info("✅ 广播服务重启成功")
            else:
                logger.error("❌ 广播服务重启失败")
        else:
            logger.debug("✅ 广播服务运行正常")
    
    async def trigger_immediate_update(self):
        """立即触发一次广播更新（用于数据变化时）"""
        try:
            websocket_manager = self._get_websocket_manager()
            if not websocket_manager:
                return
                
            connection_count = websocket_manager.get_connection_count()
            if connection_count == 0:
                return
            
            logger.info(f"Triggering immediate update for {connection_count} connections")
            await self.broadcast_devices_overview()
            await self.broadcast_experiments_overview()
            await self.broadcast_all_device_details()
            
        except Exception as e:
            logger.debug(f"Error in immediate broadcast update: {e}")

    async def broadcast_device_data_change(self, device_id: str, experiment_id: str, change_type: str = "update"):
        """当设备数据发生变化时触发的广播 - 解决数据更新广播问题"""
        try:
            websocket_manager = self._get_websocket_manager()
            if not websocket_manager:
                return
            
            # 检查是否有订阅者
            detail_topic = f"devices.{device_id}.detail"
            if websocket_manager.get_topic_subscriber_count(detail_topic) == 0:
                return
            
            database_service = self._get_database_service()
            if not database_service:
                return
            
            # 获取最新的设备详细信息
            device_detail = await database_service.get_device_detail(device_id, experiment_id)
            if device_detail:
                await self.emit_event(detail_topic, device_detail)
                logger.info(f"Broadcasted device data change: {device_id} ({change_type})")
                
                # 同时触发概览更新
                await self.broadcast_devices_overview()
            
        except Exception as e:
            logger.debug(f"Error broadcasting device data change: {e}")

    async def cleanup(self):
        """Clean up the broadcast service"""
        await self.stop_device_monitoring()
    
    # ========== Configuration related methods ==========
    
    def get_broadcast_interval(self) -> int:
        """Get broadcast interval configuration"""
        return get_config(
            'device_monitoring.broadcast_interval_seconds', 30, 'broadcast.config'
        )
    
    def should_broadcast_when_no_connections(self) -> bool:
        """Whether to continue broadcasting when there are no connections"""
        return get_config(
            'websocket.broadcast_without_connections', True, 'broadcast.config'
        )
    
    def should_suppress_broadcast_warnings(self) -> bool:
        """Whether to suppress broadcast warnings"""
        return get_config(
            'websocket.suppress_broadcast_warnings', True, 'broadcast.config'
        )
    
    def get_websocket_config(self) -> Dict[str, Any]:
        """Get WebSocket related configuration"""
        return {
            'enabled': get_config('websocket.enabled', True, 'broadcast.websocket'),
            'heartbeat_interval': get_config('websocket.heartbeat_interval', 30, 'broadcast.websocket'),
            'connection_timeout': get_config('websocket.connection_timeout', 60, 'broadcast.websocket'),
            'max_connections': get_config('websocket.max_connections', 100, 'broadcast.websocket'),
            'auto_reconnect': get_config('websocket.auto_reconnect', True, 'broadcast.websocket'),
            'reconnect_interval': get_config('websocket.reconnect_interval', 5, 'broadcast.websocket')
        }

# Global broadcast service instance
broadcast_service = BroadcastService() 
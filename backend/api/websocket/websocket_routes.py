"""
WebSocket routes processor
Handles WebSocket connection and message routing API endpoints
"""

import asyncio
import logging
import sys
from typing import Optional
from pathlib import Path
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from .manager_singleton import get_websocket_manager

# Add configuration path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent
config_path = project_root / "config"

# Add to Python path
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(config_path) not in sys.path:
    sys.path.insert(0, str(config_path))

# Import unified config manager
from unified_config_manager import config_manager, get_config, get_log_message

logger = logging.getLogger(__name__)

# Create router
def create_websocket_router() -> APIRouter:
    """Create WebSocket router"""
    router = APIRouter()
    
    # Load routes configuration
    enabled_routes = get_config('websocket_routes.enabled_routes', {}, 'websocket_routes.enabled_routes')
    route_paths = get_config('websocket_routes.route_paths', {}, 'websocket_routes.route_paths')
    
    # Add routes conditionally
    if enabled_routes.get('connect', True):
        connect_path = route_paths.get('connect', '/connect')
        router.add_websocket_route(connect_path, websocket_endpoint)
    
    if enabled_routes.get('subscribe_with_topic', True):
        subscribe_path = route_paths.get('subscribe_with_topic', '/subscribe/{topic}')
        router.add_websocket_route(subscribe_path, websocket_subscribe_endpoint)
    
    # Add custom endpoints
    if enabled_routes.get('custom_endpoints', False):
        _add_custom_endpoints(router, route_paths)
    
    if get_config('websocket_routes.logging.log_route_access', True, 'websocket_routes.logging'):
        logger.info(get_log_message('websocket_routes', 'routes_initialized',
                                   component='websocket_routes.init'))
    
    return router

def _add_custom_endpoints(router: APIRouter, route_paths: dict):
    """Add custom WebSocket endpoints"""
    # Add more custom endpoints
    # For example: health check endpoints, management endpoints, etc.
    pass

class ConfigurableWebSocketHandler:
    """WebSocket connection handler"""
    
    def __init__(self):
        self._load_configuration()
    
    def _load_configuration(self):
        """Load WebSocket routes configuration"""
        # Connection handling configuration
        self.enable_auto_subscription = get_config('websocket_routes.connection_handling.enable_auto_subscription',
                                                  True, 'websocket_routes.connection_handling')
        self.connection_timeout = get_config('websocket_routes.connection_handling.connection_timeout',
                                           60, 'websocket_routes.connection_handling')
        self.message_timeout = get_config('websocket_routes.connection_handling.message_timeout',
                                        30, 'websocket_routes.connection_handling')
        self.cleanup_timeout = get_config('websocket_routes.connection_handling.cleanup_timeout',
                                        10, 'websocket_routes.connection_handling')
        self.enable_connection_retry = get_config('websocket_routes.connection_handling.enable_connection_retry',
                                                False, 'websocket_routes.connection_handling')
        
        # Error handling configuration
        self.log_connection_errors = get_config('websocket_routes.error_handling.log_connection_errors',
                                              True, 'websocket_routes.error_handling')
        self.log_disconnection_events = get_config('websocket_routes.error_handling.log_disconnection_events',
                                                  True, 'websocket_routes.error_handling')
        self.log_message_errors = get_config('websocket_routes.error_handling.log_message_errors',
                                           True, 'websocket_routes.error_handling')
        self.detailed_error_logging = get_config('websocket_routes.error_handling.detailed_error_logging',
                                                True, 'websocket_routes.error_handling')
        self.enable_error_recovery = get_config('websocket_routes.error_handling.enable_error_recovery',
                                               True, 'websocket_routes.error_handling')
        
        # Feature configuration
        self.enable_route_logging = get_config('websocket_routes.features.enable_route_logging',
                                             True, 'websocket_routes.features')
        self.enable_connection_tracking = get_config('websocket_routes.features.enable_connection_tracking',
                                                   True, 'websocket_routes.features')
        self.enable_performance_monitoring = get_config('websocket_routes.features.enable_performance_monitoring',
                                                       False, 'websocket_routes.features')
        self.enable_debug_mode = get_config('websocket_routes.features.enable_debug_mode',
                                          True, 'websocket_routes.features')
        
        # Validation configuration
        self.validate_topic_format = get_config('websocket_routes.validation.validate_topic_format',
                                              True, 'websocket_routes.validation')
        self.require_authentication = get_config('websocket_routes.validation.require_authentication',
                                                False, 'websocket_routes.validation')
        self.enable_rate_limiting = get_config('websocket_routes.validation.enable_rate_limiting',
                                              False, 'websocket_routes.validation')
        self.max_connections_per_ip = get_config('websocket_routes.validation.max_connections_per_ip',
                                                10, 'websocket_routes.validation')
        
        # Logging configuration
        self.log_route_access = get_config('websocket_routes.logging.log_route_access',
                                         True, 'websocket_routes.logging')
        self.log_connection_lifecycle = get_config('websocket_routes.logging.log_connection_lifecycle',
                                                 True, 'websocket_routes.logging')
        self.log_auto_subscriptions = get_config('websocket_routes.logging.log_auto_subscriptions',
                                                True, 'websocket_routes.logging')
        self.log_cleanup_operations = get_config('websocket_routes.logging.log_cleanup_operations',
                                                True, 'websocket_routes.logging')
        self.log_performance_metrics = get_config('websocket_routes.logging.log_performance_metrics',
                                                 False, 'websocket_routes.logging')
    
    async def handle_websocket_connection(self, websocket: WebSocket, route_name: str = "connect", topic: Optional[str] = None):
        """WebSocket connection handling"""
        connection_id = None
        start_time = asyncio.get_event_loop().time() if self.enable_performance_monitoring else None
        
        try:
            # Get WebSocket manager
            websocket_manager = get_websocket_manager()
            
            # Connection establishment
            connection_id = await asyncio.wait_for(
                websocket_manager.connect_client(websocket),
                timeout=self.connection_timeout
            )
            
            if not connection_id:
                if self.log_connection_errors:
                    if topic:
                        logger.error(get_log_message('websocket_routes', 'topic_connection_failed',
                                                   component='websocket_routes.connect'))
                    else:
                        logger.error(get_log_message('websocket_routes', 'connection_failed',
                                                   component='websocket_routes.connect'))
                return
            
            # Log connection success
            if self.log_connection_lifecycle:
                logger.info(get_log_message('websocket_routes', 'connection_accepted',
                                          component='websocket_routes.connect',
                                          connection_id=connection_id))
            
            if self.log_route_access:
                logger.info(get_log_message('websocket_routes', 'route_accessed',
                                          component='websocket_routes.access',
                                          route=route_name, connection_id=connection_id))
            
            #  Auto subscription
            if topic and self.enable_auto_subscription:
                success = await self._handle_auto_subscription(websocket_manager, connection_id, topic)
                if not success and self.enable_error_recovery:
                    # Subscription failed but continue connection
                    pass
            
            # Message handling loop
            await self._message_handling_loop(websocket_manager, connection_id, websocket, topic)
        
        except asyncio.TimeoutError:
            if self.log_connection_errors:
                logger.error(get_log_message('websocket_routes', 'connection_timeout',
                                           component='websocket_routes.connect',
                                           connection_id=connection_id or "unknown"))
        except Exception as e:
            if self.log_connection_errors:
                if topic:
                    logger.error(get_log_message('websocket_routes', 'websocket_topic_error',
                                               component='websocket_routes.connect',
                                               error=str(e)))
                else:
                    logger.error(get_log_message('websocket_routes', 'websocket_connection_error',
                                               component='websocket_routes.connect',
                                               error=str(e)))
        
        finally:
            # Connection cleanup
            await self._cleanup_connection(connection_id, start_time)
    
    async def _handle_auto_subscription(self, websocket_manager, connection_id: str, topic: str) -> bool:
        """Auto subscription handling"""
        # Validate topic format
        if self.validate_topic_format and not self._is_valid_topic(topic):
            if self.log_auto_subscriptions:
                logger.warning(f"Invalid topic format for auto-subscription: {topic}")
            return False
        
        try:
            success = await websocket_manager.subscribe_client(connection_id, topic)
            
            if success:
                if self.log_auto_subscriptions:
                    logger.info(get_log_message('websocket_routes', 'auto_subscribed',
                                              component='websocket_routes.subscribe',
                                              connection_id=connection_id, topic=topic))
            else:
                if self.log_connection_errors:
                    logger.error(get_log_message('websocket_routes', 'auto_subscribe_failed',
                                               component='websocket_routes.subscribe',
                                               connection_id=connection_id, topic=topic))
            
            return success
        
        except Exception as e:
            if self.log_connection_errors:
                logger.error(f"Auto-subscription error for {connection_id}: {e}")
            return False
    
    def _is_valid_topic(self, topic: str) -> bool:
        """Validate topic format"""
        if not topic or not isinstance(topic, str):
            return False
        
        # Basic format check
        if len(topic.strip()) == 0:
            return False
        
        # Add more validation logic
        # For example: length limit, character limit, pattern matching, etc.
        max_topic_length = get_config('websocket.topics.max_topic_length', 100, 'websocket.topics')
        if len(topic) > max_topic_length:
            return False
        
        return True
    
    async def _message_handling_loop(self, websocket_manager, connection_id: str, websocket: WebSocket, topic: Optional[str] = None):
        """Message handling loop"""
        while True:
            try:
                # Message receive timeout
                message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=self.message_timeout
                )
                
                # Handle message
                await websocket_manager.handle_client_message(connection_id, message)
                
            except WebSocketDisconnect:
                if self.log_disconnection_events:
                    if topic:
                        logger.info(get_log_message('websocket_routes', 'topic_disconnected',
                                                  component='websocket_routes.disconnect',
                                                  connection_id=connection_id, topic=topic))
                    else:
                        logger.info(get_log_message('websocket_routes', 'client_disconnected_normal',
                                                  component='websocket_routes.disconnect',
                                                  connection_id=connection_id))
                break
            except asyncio.TimeoutError:
                if self.enable_debug_mode:
                    logger.debug(f"Message timeout for {connection_id}")
                # Timeout is not necessarily an error, continue loop
                continue
            except Exception as e:
                if self.log_message_errors:
                    if topic:
                        logger.error(get_log_message('websocket_routes', 'topic_subscription_error',
                                                   component='websocket_routes.message',
                                                   connection_id=connection_id, error=str(e)))
                    else:
                        logger.error(get_log_message('websocket_routes', 'message_loop_error',
                                                   component='websocket_routes.message',
                                                   connection_id=connection_id, error=str(e)))
                
                if not self.enable_error_recovery:
                    break
    
    async def _cleanup_connection(self, connection_id: Optional[str], start_time: Optional[float]):
        """Connection cleanup"""
        if connection_id:
            try:
                websocket_manager = get_websocket_manager()
                await asyncio.wait_for(
                    websocket_manager.disconnect_client(connection_id),
                    timeout=self.cleanup_timeout
                )
                
                if self.log_cleanup_operations:
                    logger.info(get_log_message('websocket_routes', 'cleanup_completed',
                                              component='websocket_routes.cleanup',
                                              connection_id=connection_id))
                
                # Performance monitoring logs
                if self.enable_performance_monitoring and start_time:
                    duration = asyncio.get_event_loop().time() - start_time
                    if self.log_performance_metrics:
                        logger.info(f"Connection {connection_id} duration: {duration:.2f}s")
                
            except Exception as e:
                if self.log_connection_errors and self.detailed_error_logging:
                    logger.error(f"Cleanup error for {connection_id}: {e}")

# Create configurable processor instance
websocket_handler = ConfigurableWebSocketHandler()

# Route endpoint function
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket connection endpoint"""
    await websocket_handler.handle_websocket_connection(websocket, "connect")

async def websocket_subscribe_endpoint(websocket: WebSocket, topic: str):
    """WebSocket endpoint with topic subscription"""
    await websocket_handler.handle_websocket_connection(websocket, "subscribe", topic)

# Create router
websocket_router = create_websocket_router() 
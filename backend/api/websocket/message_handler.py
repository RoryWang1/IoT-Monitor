"""
WebSocket message handler
Handles different types of WebSocket messages and message routing
"""

import logging
import asyncio
import sys
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

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
from config.unified_config_manager import UnifiedConfigManager, get_config, get_log_message

# Create config manager instance
config_manager = UnifiedConfigManager()

logger = logging.getLogger(__name__)

class MessageHandler:
    """WebSocket message handler"""
    
    def __init__(self, websocket_manager):
        self.websocket_manager = websocket_manager
        
        # Load configuration
        self._load_configuration()
        
        # Initialize message handler mapping
        self._init_message_handlers()
        
        if get_config('message_handler.logging.log_message_processing', True, 'message_handler.logging'):
            logger.info(get_log_message('message_handler', 'handler_initialized',
                                       component='message_handler.init'))
    
    def _load_configuration(self):
        """Load message handler configuration"""
        # Supported message types
        self.supported_message_types = get_config('message_handler.supported_message_types',
                                                 [], 'message_handler.supported_message_types')
        
        # Error message configuration
        self.error_messages = get_config('message_handler.error_messages',
                                       {}, 'message_handler.error_messages')
        self.error_codes = get_config('message_handler.error_codes',
                                    {}, 'message_handler.error_codes')
        
        # Message routing configuration
        self.enable_custom_handlers = get_config('message_handler.message_routing.enable_custom_handlers',
                                                True, 'message_handler.message_routing')
        self.enable_message_validation = get_config('message_handler.message_routing.enable_message_validation',
                                                   True, 'message_handler.message_routing')
        self.enable_topic_validation = get_config('message_handler.message_routing.enable_topic_validation',
                                                 True, 'message_handler.message_routing')
        self.enable_permission_checks = get_config('message_handler.message_routing.enable_permission_checks',
                                                  False, 'message_handler.message_routing')
        self.fallback_to_default = get_config('message_handler.message_routing.fallback_to_default',
                                             True, 'message_handler.message_routing')
        
        # Response template configuration
        self.include_timestamp = get_config('message_handler.response_templates.include_timestamp',
                                          True, 'message_handler.response_templates')
        self.include_connection_info = get_config('message_handler.response_templates.include_connection_info',
                                                 False, 'message_handler.response_templates')
        self.include_server_info = get_config('message_handler.response_templates.include_server_info',
                                             True, 'message_handler.response_templates')
        self.status_detail_level = get_config('message_handler.response_templates.status_response_detail_level',
                                             'full', 'message_handler.response_templates')
        
        # Topic validation configuration
        self.use_websocket_patterns = get_config('message_handler.topic_validation.use_websocket_patterns',
                                                True, 'message_handler.topic_validation')
        self.custom_patterns = get_config('message_handler.topic_validation.custom_patterns',
                                        [], 'message_handler.topic_validation')
        self.enable_wildcard_matching = get_config('message_handler.topic_validation.enable_wildcard_matching',
                                                  True, 'message_handler.topic_validation')
        self.case_sensitive = get_config('message_handler.topic_validation.case_sensitive',
                                       False, 'message_handler.topic_validation')
        self.max_topic_segments = get_config('message_handler.topic_validation.max_topic_segments',
                                           10, 'message_handler.topic_validation')
        
        # Feature configuration
        self.enable_ping_pong = get_config('message_handler.features.enable_ping_pong',
                                         True, 'message_handler.features')
        self.enable_subscriptions = get_config('message_handler.features.enable_subscriptions',
                                              True, 'message_handler.features')
        self.enable_status_requests = get_config('message_handler.features.enable_status_requests',
                                                True, 'message_handler.features')
        self.enable_custom_messages = get_config('message_handler.features.enable_custom_messages',
                                                True, 'message_handler.features')
        self.auto_respond_to_ping = get_config('message_handler.features.auto_respond_to_ping',
                                              True, 'message_handler.features')
        
        # Logging configuration
        self.log_message_processing = get_config('message_handler.logging.log_message_processing',
                                                True, 'message_handler.logging')
        self.log_ping_pong = get_config('message_handler.logging.log_ping_pong',
                                      False, 'message_handler.logging')
        self.log_subscriptions = get_config('message_handler.logging.log_subscriptions',
                                          True, 'message_handler.logging')
        self.log_errors = get_config('message_handler.logging.log_errors',
                                   True, 'message_handler.logging')
        self.log_status_requests = get_config('message_handler.logging.log_status_requests',
                                             True, 'message_handler.logging')
        self.log_unknown_messages = get_config('message_handler.logging.log_unknown_messages',
                                              True, 'message_handler.logging')
        
        # Performance configuration
        self.enable_message_caching = get_config('message_handler.performance.enable_message_caching',
                                                False, 'message_handler.performance')
        self.max_concurrent_messages = get_config('message_handler.performance.max_concurrent_messages',
                                                 100, 'message_handler.performance')
        self.message_processing_timeout = get_config('message_handler.performance.message_processing_timeout',
                                                    30, 'message_handler.performance')
        self.enable_batch_processing = get_config('message_handler.performance.enable_batch_processing',
                                                 False, 'message_handler.performance')
    
    def _init_message_handlers(self):
        """Initialize message handler mapping"""
        self.message_handlers = {}
        
        # Message handler registration
        if self.enable_ping_pong:
            self.message_handlers['ping'] = self._handle_ping
            self.message_handlers['pong'] = self._handle_pong
        
        if self.enable_subscriptions:
            self.message_handlers['subscribe'] = self._handle_subscribe
            self.message_handlers['unsubscribe'] = self._handle_unsubscribe
        
        if self.enable_status_requests:
            self.message_handlers['get_status'] = self._handle_get_status
        
        # Custom message handler
        if self.enable_custom_messages:
            self.message_handlers['custom_action'] = self._handle_custom_action
    
    async def process_message(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """Process message"""
        try:
            # Validate message
            if not self._validate_message(connection_id, message):
                return False
            
            message_type = message.get("type")
            
            # Check message type
            if not self._is_supported_message_type(message_type):
                await self._send_error(connection_id, "unknown_message_type", message_type=message_type)
                if self.log_unknown_messages:
                    logger.warning(get_log_message('message_handler', 'unknown_message_type',
                                                 component='message_handler.process',
                                                 connection_id=connection_id, message_type=message_type))
                return False
            
            # Check permissions
            if self.enable_permission_checks:
                if not self._check_permissions(connection_id, message_type):
                    await self._send_error(connection_id, "permission_denied", action=message_type)
                    return False
            
            # Message processing timeout
            handler = self.message_handlers.get(message_type)
            if handler:
                result = await asyncio.wait_for(
                    handler(connection_id, message),
                    timeout=self.message_processing_timeout
                )
                
                if self.log_message_processing:
                    logger.debug(f"Message {message_type} processed for {connection_id}: {result}")
                
                return result
            else:
                # Fallback processing
                if self.fallback_to_default:
                    return await self._handle_unknown_message(connection_id, message)
                else:
                    await self._send_error(connection_id, "handler_not_found", message_type=message_type)
                return False
        
        except asyncio.TimeoutError:
            await self._send_error(connection_id, "server_error")
            if self.log_errors:
                logger.error(f"Message processing timeout for {connection_id}")
            return False
        except Exception as e:
            if self.log_errors:
                logger.error(get_log_message('message_handler', 'process_error',
                                           component='message_handler.process',
                                           connection_id=connection_id, error=str(e)))
            await self._send_error(connection_id, "server_error")
            return False
    
    def _validate_message(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """Validate message"""
        if not self.enable_message_validation:
            return True
        
        # Check message type
        message_type = message.get("type")
        if not message_type:
            asyncio.create_task(self._send_error(connection_id, "missing_message_type"))
            if self.log_errors:
                logger.warning(get_log_message('message_handler', 'missing_message_type',
                                             component='message_handler.validation',
                                             connection_id=connection_id))
            return False
        
        return True
    
    def _is_supported_message_type(self, message_type: str) -> bool:
        """Check if message type is supported"""
        if not self.supported_message_types:
            return True  # If no configuration limit, allow all types
        
        return message_type in self.supported_message_types
    
    def _check_permissions(self, connection_id: str, message_type: str) -> bool:
        """Check permissions"""
        # Here you can add more complex permission check logic
        # Currently, simply return True, you can expand it as needed
        return True
    
    async def _handle_ping(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """Handle ping message"""
        if not self.auto_respond_to_ping:
            return True
        
        connection = self.websocket_manager.get_connection(connection_id)
        if connection:
            result = await connection.send_pong()
            if result and self.log_ping_pong:
                logger.debug(get_log_message('message_handler', 'ping_handled',
                                           component='message_handler.ping',
                                           connection_id=connection_id))
            return result
        return False
    
    async def _handle_pong(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """Handle pong message"""
        connection = self.websocket_manager.get_connection(connection_id)
        if connection:
            connection.last_ping = datetime.now()
            if self.log_ping_pong:
                logger.debug(get_log_message('message_handler', 'pong_received',
                                           component='message_handler.pong',
                                           connection_id=connection_id))
            return True
        return False
    
    async def _handle_subscribe(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """Handle subscription"""
        topic = message.get("topic")
        
        if not topic:
            await self._send_error(connection_id, "missing_topic", action="subscribe")
            if self.log_errors:
                logger.warning(get_log_message('message_handler', 'missing_topic',
                                             component='message_handler.subscribe',
                                             connection_id=connection_id))
            return False
        
        # Validate topic
        if self.enable_topic_validation and not self._is_valid_topic(topic):
            await self._send_error(connection_id, "invalid_topic", topic=topic)
            if self.log_errors:
                logger.warning(get_log_message('message_handler', 'invalid_topic',
                                             component='message_handler.subscribe',
                                             connection_id=connection_id, topic=topic))
            return False
        
        # Execute subscription
        success = await self.websocket_manager.subscribe_client(connection_id, topic)
        
        # Send confirmation message
        connection = self.websocket_manager.get_connection(connection_id)
        if connection:
            await connection.send_subscription_confirmation(topic, success)
        
        if self.log_subscriptions:
            logger.info(get_log_message('message_handler', 'subscription_processed',
                                       component='message_handler.subscribe',
                                       connection_id=connection_id, topic=topic, success=success))
        
        return success
    
    async def _handle_unsubscribe(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """Handle unsubscribe"""
        topic = message.get("topic")
        
        if not topic:
            await self._send_error(connection_id, "missing_topic", action="unsubscribe")
            if self.log_errors:
                logger.warning(get_log_message('message_handler', 'missing_topic',
                                             component='message_handler.unsubscribe',
                                             connection_id=connection_id))
            return False
        
        # Execute unsubscribe
        success = await self.websocket_manager.unsubscribe_client(connection_id, topic)
        
        # Confirmation message
        connection = self.websocket_manager.get_connection(connection_id)
        if connection:
            confirmation = self._create_unsubscription_response(topic, success)
            await connection.send_message(confirmation)
        
        if self.log_subscriptions:
            logger.info(get_log_message('message_handler', 'unsubscription_processed',
                                       component='message_handler.unsubscribe',
                                       connection_id=connection_id, topic=topic, success=success))
        
        return success
    
    def _create_unsubscription_response(self, topic: str, success: bool) -> Dict[str, Any]:
        """Create unsubscription response"""
        response = {
            "type": "unsubscription_response",
            "topic": topic,
            "success": success
        }
        
        if self.include_timestamp:
            response["timestamp"] = datetime.now().isoformat()
        
        return response
    
    async def _handle_get_status(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """Handle status request"""
        connection = self.websocket_manager.get_connection(connection_id)
        if not connection:
            return False
        
        # Status response
        status = self._create_status_response(connection)
        
        if self.log_status_requests:
            logger.info(get_log_message('message_handler', 'status_requested',
                                       component='message_handler.status',
                                       connection_id=connection_id))
        
        return await connection.send_message(status)
    
    def _create_status_response(self, connection) -> Dict[str, Any]:
        """Create status response"""
        status = {
            "type": "status_response"
        }
        
        # Include connection info
        if self.include_connection_info or self.status_detail_level == "full":
            status["connection_info"] = connection.get_connection_info()
        
        # Include server info
        if self.include_server_info:
            server_info = {
                "total_connections": self.websocket_manager.get_connection_count(),
                "total_subscriptions": self.websocket_manager.get_subscription_count()
            }
            
            if self.status_detail_level == "full":
                server_info["available_topics"] = self._get_available_topics()
            
            status["server_info"] = server_info
        
        if self.include_timestamp:
            status["timestamp"] = datetime.now().isoformat()
        
        return status
    
    async def _handle_custom_action(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """Handle custom action"""
        action = message.get("action", "unknown")
        
        if self.log_message_processing:
            logger.info(get_log_message('message_handler', 'custom_handler_processed',
                                       component='message_handler.custom',
                                       handler_type=action, connection_id=connection_id))
        
        # Add more custom logic here
        return True
    
    async def _handle_unknown_message(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """Handle unknown message type fallback"""
        message_type = message.get("type", "unknown")
        await self._send_error(connection_id, "unknown_message_type", message_type=message_type)
        return False
    
    async def _send_error(self, connection_id: str, error_key: str, **kwargs) -> bool:
        """Send error message"""
        error_message = self.error_messages.get(error_key, "Unknown error")
        error_code = self.error_codes.get(error_key, "UNKNOWN_ERROR")
        
        # Format error message
        try:
            formatted_message = error_message.format(**kwargs)
        except KeyError:
            formatted_message = error_message
        
        connection = self.websocket_manager.get_connection(connection_id)
        if connection:
            return await connection.send_error(formatted_message, error_code)
        return False
    
    def _is_valid_topic(self, topic: str) -> bool:
        """Validate topic"""
        if not topic or not isinstance(topic, str):
            return False
        
        # Case sensitivity configuration
        check_topic = topic if self.case_sensitive else topic.lower()
        
        # Topic segment check
        if len(check_topic.split('.')) > self.max_topic_segments:
            return False
        
        # Validate with WebSocket patterns
        if self.use_websocket_patterns:
            patterns = get_config('websocket.topics.allowed_topic_patterns', [], 'websocket.topics')
        else:
            patterns = self.custom_patterns
        
        if not patterns:
            return True  # If no configuration patterns, allow all topics
        
        # Check if matches any pattern
        for pattern in patterns:
            if self._topic_matches_pattern(check_topic, pattern):
                return True
        
        return False
    
    def _topic_matches_pattern(self, topic: str, pattern: str) -> bool:
        """Validate topic pattern"""
        import re
        
        # Wildcard support
        if self.enable_wildcard_matching:
            # Replace placeholders first, then handle case sensitivity
            regex_pattern = pattern.replace("{experimentId}", r"[^.]+").replace("{deviceId}", r"[^.]+")
            regex_pattern = f"^{regex_pattern}$"
            
            # Then handle case sensitivity
            check_topic = topic if self.case_sensitive else topic.lower()
            check_regex = regex_pattern if self.case_sensitive else regex_pattern.lower()
            
            return bool(re.match(check_regex, check_topic))
        else:
            # Exact match
            check_topic = topic if self.case_sensitive else topic.lower()
            check_pattern = pattern if self.case_sensitive else pattern.lower()
            return check_topic == check_pattern
    
    def _get_available_topics(self) -> List[str]:
        """Get available topics"""
        if self.use_websocket_patterns:
            return get_config('websocket.topics.allowed_topic_patterns', [], 'websocket.topics')
        else:
            return self.custom_patterns 
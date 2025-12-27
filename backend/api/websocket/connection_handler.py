"""
WebSocket connection processor
The core component for handling individual WebSocket connections and message transmission
"""

import json
import logging
import asyncio
import sys
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from pathlib import Path
import uuid

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

class ConnectionHandler:
    """WebSocket connection processor"""
    
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.connection_id = str(uuid.uuid4())
        self.subscriptions = set()
        self.connected_at = datetime.now()
        self.last_ping = datetime.now()
        self.is_active = True
        
        # Load configuration
        self._load_configuration()
    
    def _load_configuration(self):
        """Load connection processor configuration"""
        # Message limit configuration
        self.max_message_size = get_config('connection_handler.message_limits.max_message_size', 
                                         65536, 'connection_handler.message_limits')
        self.max_json_depth = get_config('connection_handler.message_limits.max_json_depth', 
                                       10, 'connection_handler.message_limits')
        self.enable_size_validation = get_config('connection_handler.message_limits.enable_size_validation', 
                                                True, 'connection_handler.message_limits')
        
        # Timeout configuration
        self.connection_timeout = get_config('connection_handler.timeouts.connection_timeout', 
                                           300, 'connection_handler.timeouts')
        self.ping_timeout = get_config('connection_handler.timeouts.ping_timeout', 
                                     30, 'connection_handler.timeouts')
        self.send_timeout = get_config('connection_handler.timeouts.send_timeout', 
                                     10, 'connection_handler.timeouts')
        self.receive_timeout = get_config('connection_handler.timeouts.receive_timeout', 
                                        60, 'connection_handler.timeouts')
        
        # Message template configuration
        self.include_timestamp = get_config('connection_handler.message_templates.include_timestamp', 
                                          True, 'connection_handler.message_templates')
        self.include_connection_id = get_config('connection_handler.message_templates.include_connection_id', 
                                              False, 'connection_handler.message_templates')
        self.custom_ping_data = get_config('connection_handler.message_templates.custom_ping_data', 
                                         {}, 'connection_handler.message_templates')
        self.custom_pong_data = get_config('connection_handler.message_templates.custom_pong_data', 
                                         {}, 'connection_handler.message_templates')
        self.error_details_level = get_config('connection_handler.message_templates.error_details_level', 
                                             'full', 'connection_handler.message_templates')
        
        # Feature configuration
        self.enable_ping_pong = get_config('connection_handler.features.enable_ping_pong', 
                                         True, 'connection_handler.features')
        self.enable_error_responses = get_config('connection_handler.features.enable_error_responses', 
                                                True, 'connection_handler.features')
        self.enable_subscription_confirmations = get_config('connection_handler.features.enable_subscription_confirmations', 
                                                           True, 'connection_handler.features')
        self.enable_connection_info = get_config('connection_handler.features.enable_connection_info', 
                                                True, 'connection_handler.features')
        self.auto_close_on_error = get_config('connection_handler.features.auto_close_on_error', 
                                             False, 'connection_handler.features')
        
        # Logging configuration
        self.log_connections = get_config('connection_handler.logging.log_connections', 
                                        True, 'connection_handler.logging')
        self.log_messages = get_config('connection_handler.logging.log_messages', 
                                     False, 'connection_handler.logging')
        self.log_subscriptions = get_config('connection_handler.logging.log_subscriptions', 
                                          True, 'connection_handler.logging')
        self.log_ping_pong = get_config('connection_handler.logging.log_ping_pong', 
                                      False, 'connection_handler.logging')
        self.log_errors = get_config('connection_handler.logging.log_errors', 
                                   True, 'connection_handler.logging')
        
        # Validation configuration
        self.validate_message_format = get_config('connection_handler.validation.validate_message_format', 
                                                True, 'connection_handler.validation')
        self.validate_subscription_topics = get_config('connection_handler.validation.validate_subscription_topics', 
                                                      True, 'connection_handler.validation')
        self.validate_json_structure = get_config('connection_handler.validation.validate_json_structure', 
                                                 True, 'connection_handler.validation')
        self.strict_type_checking = get_config('connection_handler.validation.strict_type_checking', 
                                              False, 'connection_handler.validation')
    
    async def accept_connection(self):
        """WebSocket connection acceptance"""
        try:
            # Connection timeout
            await asyncio.wait_for(
                self.websocket.accept(),
                timeout=self.connection_timeout
            )
            self.is_active = True
            
            if self.log_connections:
                logger.info(get_log_message('connection_handler', 'accepted',
                                          component='connection_handler.accept',
                                          connection_id=self.connection_id))
            return True
            
        except asyncio.TimeoutError:
            if self.log_errors:
                logger.error(get_log_message('connection_handler', 'connection_timeout',
                                           component='connection_handler.accept',
                                           connection_id=self.connection_id))
            return False
        except Exception as e:
            if self.log_errors:
                logger.error(get_log_message('connection_handler', 'accept_failed',
                                           component='connection_handler.accept',
                                           connection_id=self.connection_id, error=str(e)))
            return False
    
    async def send_message(self, message: Dict[str, Any]) -> bool:
        """Message sending"""
        if not self.is_active:
            return False
        
        try:
            # Message validation
            if not self._validate_outgoing_message(message):
                return False
            
            # Message enhancement
            enhanced_message = self._enhance_message(message)
            
            # Configurable send timeout
            message_text = json.dumps(enhanced_message)
            await asyncio.wait_for(
                self.websocket.send_text(message_text),
                timeout=self.send_timeout
            )
            
            if self.log_messages:
                logger.debug(f"Message sent to {self.connection_id}: {message.get('type', 'unknown')}")
            
            return True
            
        except asyncio.TimeoutError:
            if self.log_errors:
                logger.error(f"Send timeout for {self.connection_id}")
            self.is_active = False
            return False
        except Exception as e:
            if self.log_errors:
                logger.error(get_log_message('connection_handler', 'send_message_failed',
                                           component='connection_handler.send',
                                           connection_id=self.connection_id, error=str(e)))
            self.is_active = False
            if self.auto_close_on_error:
                self.close_connection()
            return False
    
    def _validate_outgoing_message(self, message: Dict[str, Any]) -> bool:
        """Outgoing message validation"""
        if not self.validate_message_format:
            return True
        
        try:
            # Message size validation
            if self.enable_size_validation:
                message_size = len(json.dumps(message).encode('utf-8'))
                if message_size > self.max_message_size:
                    if self.log_errors:
                        logger.warning(get_log_message('connection_handler', 'message_too_large',
                                                     component='connection_handler.validation',
                                                     connection_id=self.connection_id, size=message_size))
                    return False
            
            # JSON structure validation
            if self.validate_json_structure:
                if not isinstance(message, dict):
                    return False
                
                # Check JSON depth
                if self._get_dict_depth(message) > self.max_json_depth:
                    return False
            
            return True
            
        except Exception as e:
            if self.log_errors:
                logger.error(f"Message validation error for {self.connection_id}: {e}")
            return False
    
    def _get_dict_depth(self, d: Dict[str, Any], depth: int = 0) -> int:
        """Calculate dictionary depth"""
        if not isinstance(d, dict):
            return depth
        
        max_depth = depth
        for value in d.values():
            if isinstance(value, dict):
                max_depth = max(max_depth, self._get_dict_depth(value, depth + 1))
        
        return max_depth
    
    def _enhance_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Message enhancement"""
        enhanced = message.copy()
        
        # Add configurable timestamp
        if self.include_timestamp and 'timestamp' not in enhanced:
            enhanced['timestamp'] = datetime.now().isoformat()
        
        # Add configurable connection ID
        if self.include_connection_id and 'connection_id' not in enhanced:
            enhanced['connection_id'] = self.connection_id
        
        return enhanced
    
    async def receive_message(self) -> Optional[Dict[str, Any]]:
        """Message reception"""
        try:
            # Receive timeout
            text = await asyncio.wait_for(
                self.websocket.receive_text(),
                timeout=self.receive_timeout
            )
            
            # Message size validation
            if self.enable_size_validation:
                message_size = len(text.encode('utf-8'))
                if message_size > self.max_message_size:
                    if self.log_errors:
                        logger.warning(get_log_message('connection_handler', 'message_too_large',
                                                     component='connection_handler.receive',
                                                     connection_id=self.connection_id, size=message_size))
                    return None
            
            # JSON parsing
            message = json.loads(text)
            
            # Message validation
            if not self._validate_incoming_message(message):
                return None
            
            if self.log_messages:
                logger.debug(f"Message received from {self.connection_id}: {message.get('type', 'unknown')}")
            
            return message
            
        except WebSocketDisconnect:
            if self.log_connections:
                logger.info(get_log_message('connection_handler', 'client_disconnected',
                                          component='connection_handler.receive',
                                          connection_id=self.connection_id))
            self.is_active = False
            return None
        except asyncio.TimeoutError:
            if self.log_errors:
                logger.warning(f"Receive timeout for {self.connection_id}")
            return None
        except json.JSONDecodeError as e:
            if self.log_errors:
                logger.error(get_log_message('connection_handler', 'invalid_json',
                                           component='connection_handler.receive',
                                           connection_id=self.connection_id, error=str(e)))
            return None
        except Exception as e:
            if self.log_errors:
                logger.error(get_log_message('connection_handler', 'receive_error',
                                           component='connection_handler.receive',
                                           connection_id=self.connection_id, error=str(e)))
            self.is_active = False
            if self.auto_close_on_error:
                self.close_connection()
            return None
    
    def _validate_incoming_message(self, message: Dict[str, Any]) -> bool:
        """Incoming message validation"""
        if not self.validate_message_format:
            return True
        
        try:
            # Basic structure validation
            if not isinstance(message, dict):
                return False
            
            # Strict type checking
            if self.strict_type_checking:
                if 'type' not in message or not isinstance(message['type'], str):
                    return False
            
            # JSON depth check
            if self.validate_json_structure:
                if self._get_dict_depth(message) > self.max_json_depth:
                    return False
            
            return True
            
        except Exception as e:
            if self.log_errors:
                logger.error(f"Incoming message validation error for {self.connection_id}: {e}")
            return False
    
    async def send_ping(self) -> bool:
        """Send ping message"""
        if not self.enable_ping_pong:
            return True
        
        ping_message = {
            "type": "ping"
        }
        
        # Custom ping data
        if self.custom_ping_data:
            ping_message.update(self.custom_ping_data)
        
        result = await self.send_message(ping_message)
        if result:
            self.last_ping = datetime.now()
            if self.log_ping_pong:
                logger.debug(get_log_message('connection_handler', 'ping_sent',
                                           component='connection_handler.ping',
                                           connection_id=self.connection_id))
        return result
    
    async def send_pong(self) -> bool:
        """Send pong message"""
        if not self.enable_ping_pong:
            return True
        
        pong_message = {
            "type": "pong"
        }
        
        # Custom pong data
        if self.custom_pong_data:
            pong_message.update(self.custom_pong_data)
        
        result = await self.send_message(pong_message)
        if result and self.log_ping_pong:
            logger.debug(get_log_message('connection_handler', 'pong_sent',
                                       component='connection_handler.pong',
                                       connection_id=self.connection_id))
        return result
    
    async def send_error(self, error_message: str, error_code: str = "GENERAL_ERROR") -> bool:
        """Send error message"""
        if not self.enable_error_responses:
            return True
        
        error_msg = {
            "type": "error",
            "error_code": error_code,
            "message": error_message
        }
        
        # Error details level
        if self.error_details_level == "minimal":
            error_msg = {
                "type": "error",
                "error_code": error_code
            }
        elif self.error_details_level == "full":
            error_msg["details"] = {
                "connection_id": self.connection_id,
                "timestamp": datetime.now().isoformat()
        }
        
        result = await self.send_message(error_msg)
        if result and self.log_errors:
            logger.info(get_log_message('connection_handler', 'error_sent',
                                       component='connection_handler.error',
                                       connection_id=self.connection_id, error_code=error_code))
        return result
    
    async def send_subscription_confirmation(self, topic: str, success: bool) -> bool:
        """Send subscription confirmation"""
        if not self.enable_subscription_confirmations:
            return True
        
        confirmation = {
            "type": "subscription_response",
            "topic": topic,
            "success": success
        }
        
        return await self.send_message(confirmation)
    
    def add_subscription(self, topic: str):
        """Add subscription"""
        # Validate topic
        if self.validate_subscription_topics:
            if not self._validate_topic(topic):
                return False
        
        self.subscriptions.add(topic)
        
        if self.log_subscriptions:
            logger.info(get_log_message('connection_handler', 'subscription_added',
                                       component='connection_handler.subscription',
                                       connection_id=self.connection_id, topic=topic))
        return True
    
    def _validate_topic(self, topic: str) -> bool:
        """Validate topic format"""
        # Basic format check
        if not isinstance(topic, str) or len(topic.strip()) == 0:
            return False
        
        # Length check
        max_topic_length = get_config('websocket.topics.max_topic_length', 100, 'websocket.topics')
        if len(topic) > max_topic_length:
            return False
        
        return True
    
    def remove_subscription(self, topic: str):
        """Remove subscription"""
        self.subscriptions.discard(topic)
        
        if self.log_subscriptions:
            logger.info(get_log_message('connection_handler', 'subscription_removed',
                                       component='connection_handler.subscription',
                                       connection_id=self.connection_id, topic=topic))
    
    def has_subscription(self, topic: str) -> bool:
        """Check if subscribed to topic"""
        return topic in self.subscriptions
    
    def get_subscriptions(self) -> set:
        """Get all subscriptions"""
        return self.subscriptions.copy()
    
    def close_connection(self):
        """Close connection"""
        self.is_active = False
        
        if self.log_connections:
            logger.info(get_log_message('connection_handler', 'connection_closed',
                                       component='connection_handler.close',
                                       connection_id=self.connection_id))
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information"""
        if not self.enable_connection_info:
            return {
                "connection_id": self.connection_id,
                "is_active": self.is_active
            }
        
        return {
            "connection_id": self.connection_id,
            "connected_at": self.connected_at.isoformat(),
            "last_ping": self.last_ping.isoformat(),
            "is_active": self.is_active,
            "subscriptions": list(self.subscriptions),
            "subscription_count": len(self.subscriptions),
            "configuration": {
                "max_message_size": self.max_message_size,
                "connection_timeout": self.connection_timeout,
                "features_enabled": {
                    "ping_pong": self.enable_ping_pong,
                    "error_responses": self.enable_error_responses,
                    "subscription_confirmations": self.enable_subscription_confirmations
                }
            }
        } 
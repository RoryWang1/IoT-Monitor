"""
WebSocket connection manager
Unified system for managing WebSocket connections, subscriptions, and message broadcasting
"""

import asyncio
import json
import logging
import sys
from typing import Dict, List, Set, Optional, Any
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
from config.unified_config_manager import UnifiedConfigManager, get_config, get_log_message

from .connection_handler import ConnectionHandler
from .message_handler import MessageHandler

logger = logging.getLogger(__name__)

class WebSocketManager:
    """WebSocket connection manager"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WebSocketManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Only initialize once
        if WebSocketManager._initialized:
            return
            
        # Initialization
        self.connections: Dict[str, ConnectionHandler] = {}
        self.topic_subscribers: Dict[str, Set[str]] = {}
        self._running = False
        self.message_handler = None
        self._heartbeat_task = None
        
        # Load configuration
        self._load_configuration()
        
        WebSocketManager._initialized = True
        
        if get_config('websocket.logging.log_connections', True, 'websocket.logging'):
            logger.info(get_log_message('websocket', 'manager_initialized', 
                                       component='websocket.manager'))
    
    def _load_configuration(self):
        """Load WebSocket configuration"""
        # Connection configuration
        self.heartbeat_interval = get_config('websocket.connection.heartbeat_interval', 
                                           30, 'websocket.connection')
        self.ping_timeout = get_config('websocket.connection.ping_timeout', 
                                     10, 'websocket.connection')
        self.max_connections = get_config('websocket.connection.max_connections', 
                                        1000, 'websocket.connection')
        self.max_subscriptions_per_connection = get_config('websocket.connection.max_subscriptions_per_connection', 
                                                          50, 'websocket.connection')
        self.connection_timeout = get_config('websocket.connection.connection_timeout', 
                                           30, 'websocket.connection')
        
        # Feature configuration
        self.enable_heartbeat = get_config('websocket.features.enable_heartbeat', 
                                         True, 'websocket.features')
        self.enable_connection_cleanup = get_config('websocket.features.enable_connection_cleanup', 
                                                  True, 'websocket.features')
        self.enable_subscription_limits = get_config('websocket.features.enable_subscription_limits', 
                                                    True, 'websocket.features')
        self.enable_message_validation = get_config('websocket.features.enable_message_validation', 
                                                   True, 'websocket.features')
        self.enable_compression = get_config('websocket.features.enable_compression', 
                                           False, 'websocket.features')
        
        # Topic configuration
        self.allowed_topic_patterns = get_config('websocket.topics.allowed_topic_patterns', 
                                                [], 'websocket.topics')
        self.auto_create_topics = get_config('websocket.topics.auto_create_topics', 
                                           True, 'websocket.topics')
        self.cleanup_empty_topics = get_config('websocket.topics.cleanup_empty_topics', 
                                             True, 'websocket.topics')
        self.max_topic_length = get_config('websocket.topics.max_topic_length', 
                                         100, 'websocket.topics')
        
        # Message configuration
        self.welcome_message_enabled = get_config('websocket.messages.welcome_message_enabled', 
                                                True, 'websocket.messages')
        self.include_server_time = get_config('websocket.messages.include_server_time', 
                                            True, 'websocket.messages')
        self.include_available_topics = get_config('websocket.messages.include_available_topics', 
                                                 True, 'websocket.messages')
        
        # Performance configuration
        self.batch_broadcast = get_config('websocket.performance.batch_broadcast', 
                                        True, 'websocket.performance')
        self.batch_size = get_config('websocket.performance.batch_size', 
                                   50, 'websocket.performance')
        self.broadcast_timeout = get_config('websocket.performance.broadcast_timeout', 
                                          5, 'websocket.performance')
        
        # Logging configuration
        self.log_connections = get_config('websocket.logging.log_connections', 
                                        True, 'websocket.logging')
        self.log_subscriptions = get_config('websocket.logging.log_subscriptions', 
                                          True, 'websocket.logging')
        self.log_broadcasts = get_config('websocket.logging.log_broadcasts', 
                                       True, 'websocket.logging')
        self.log_heartbeats = get_config('websocket.logging.log_heartbeats', 
                                       False, 'websocket.logging')
        self.log_performance_stats = get_config('websocket.logging.log_performance_stats', 
                                               True, 'websocket.logging')
    
    async def start(self):
        """Start WebSocket manager"""
        self._running = True
        self.message_handler = MessageHandler(self)
        
        # Heartbeat start
        if self.enable_heartbeat:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        if self.log_connections:
            logger.info(get_log_message('websocket', 'manager_started', 
                                       component='websocket.manager'))
    
    async def stop(self):
        """Stop WebSocket manager"""
        self._running = False
        
        # Cancel heartbeat task
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        for connection in list(self.connections.values()):
            connection.close_connection()
        
        self.connections.clear()
        self.topic_subscribers.clear()
        
        if self.log_connections:
            logger.info(get_log_message('websocket', 'manager_stopped', 
                                       component='websocket.manager'))
    
    async def connect_client(self, websocket: WebSocket) -> str:
        """Connect client"""
        # Check connection limit
        if (self.enable_subscription_limits and 
            len(self.connections) >= self.max_connections):
            current_count = len(self.connections)
            logger.warning(get_log_message('websocket', 'connection_limit_reached',
                                         component='websocket.connection',
                                         current=current_count, max=self.max_connections))
            return None
        
        connection = ConnectionHandler(websocket)
        
        # Accept connection
        if not await connection.accept_connection():
            return None
        
        # Store connection
        self.connections[connection.connection_id] = connection
        
        # Welcome message
        if self.welcome_message_enabled:
            welcome_message = self._create_welcome_message(connection.connection_id)
            await connection.send_message(welcome_message)
        
        if self.log_connections:
            logger.info(get_log_message('websocket', 'client_connected',
                                       component='websocket.connection',
                                       connection_id=connection.connection_id))
        return connection.connection_id
    
    def _create_welcome_message(self, connection_id: str) -> Dict[str, Any]:
        """Create welcome message"""
        welcome_message = {
            "type": "connection_established",
            "connection_id": connection_id
        }
        
        if self.include_server_time:
            welcome_message["server_time"] = datetime.now().isoformat()
        
        if self.include_available_topics:
            welcome_message["available_topics"] = self._get_available_topics()
        
        return welcome_message
    
    async def disconnect_client(self, connection_id: str):
        """Disconnect client"""
        if connection_id not in self.connections:
            return
        
        connection = self.connections[connection_id]
        
        # Remove from all topic subscriptions
        for topic in connection.get_subscriptions():
            await self._remove_from_topic(connection_id, topic)
        
        # Close connection
        connection.close_connection()
        
        # Remove from connection
        del self.connections[connection_id]
        
        if self.log_connections:
            logger.info(get_log_message('websocket', 'client_disconnected',
                                       component='websocket.connection',
                                       connection_id=connection_id))
    
    async def handle_client_message(self, connection_id: str, message_text: str):
        """Handle client message"""
        if not self.message_handler:
            logger.error(get_log_message('websocket', 'message_handler_not_initialized',
                                        component='websocket.message'))
            return
        
        try:
            # Validate message
            if self.enable_message_validation:
                if not self._validate_message_format(message_text):
                    connection = self.get_connection(connection_id)
                    if connection:
                        await connection.send_error("Invalid message format", "INVALID_FORMAT")
                    return
            
            message = json.loads(message_text)
            await self.message_handler.process_message(connection_id, message)
            
        except json.JSONDecodeError as e:
            if get_config('websocket.logging.log_message_errors', True, 'websocket.logging'):
                logger.error(get_log_message('websocket', 'invalid_json',
                                           component='websocket.message',
                                           connection_id=connection_id, error=str(e)))
            connection = self.get_connection(connection_id)
            if connection:
                await connection.send_error("Invalid JSON format", "INVALID_JSON")
        except Exception as e:
            if get_config('websocket.logging.log_message_errors', True, 'websocket.logging'):
                logger.error(get_log_message('websocket', 'message_handler_error',
                                           component='websocket.message',
                                           connection_id=connection_id, error=str(e)))
    
    def _validate_message_format(self, message_text: str) -> bool:
        """Validate message format"""
        # Basic length check
        max_message_size = get_config('websocket.connection.message_queue_size', 
                                    100, 'websocket.connection') * 1024  # KB to bytes
        if len(message_text.encode('utf-8')) > max_message_size:
            return False
        
        return True
    
    async def subscribe_client(self, connection_id: str, topic: str) -> bool:
        """Subscribe client"""
        if connection_id not in self.connections:
            if self.log_subscriptions:
                logger.error(get_log_message('websocket', 'connection_not_found',
                                           component='websocket.subscription',
                                           connection_id=connection_id))
            return False
        
        # Validate topic format
        if not self._validate_topic(topic):
            logger.warning(get_log_message('websocket', 'topic_invalid',
                                         component='websocket.subscription',
                                         topic=topic))
            return False
        
        connection = self.connections[connection_id]
        
        # Check subscription limit
        if (self.enable_subscription_limits and
            len(connection.get_subscriptions()) >= self.max_subscriptions_per_connection):
            current_count = len(connection.get_subscriptions())
            logger.warning(get_log_message('websocket', 'subscription_limit_reached',
                                         component='websocket.subscription',
                                         connection_id=connection_id,
                                         current=current_count, max=self.max_subscriptions_per_connection))
            return False
        
        # Add to connection subscription
        connection.add_subscription(topic)
        
        # Add to topic subscribers
        if topic not in self.topic_subscribers:
            if self.auto_create_topics:
                self.topic_subscribers[topic] = set()
            else:
                return False
        
        self.topic_subscribers[topic].add(connection_id)
        
        if self.log_subscriptions:
            logger.info(get_log_message('websocket', 'subscription_added',
                                       component='websocket.subscription',
                                       connection_id=connection_id, topic=topic))
        return True
    
    def _validate_topic(self, topic: str) -> bool:
        """Validate topic format"""
        # Length check
        if len(topic) > self.max_topic_length:
            return False
        
        # Pattern check (if allowed patterns are configured)
        if self.allowed_topic_patterns:
            return any(self._topic_matches_pattern(topic, pattern) 
                     for pattern in self.allowed_topic_patterns)
        
        return True
    
    def _topic_matches_pattern(self, topic: str, pattern: str) -> bool:
        """Check if topic matches pattern"""
        # Simple pattern matching, support {variable} placeholders
        import re
        pattern_regex = pattern.replace('{', '(?P<').replace('}', '>[^.]+)')
        pattern_regex = f"^{pattern_regex}$"
        return bool(re.match(pattern_regex, topic))
    
    async def unsubscribe_client(self, connection_id: str, topic: str) -> bool:
        """Unsubscribe client"""
        if connection_id not in self.connections:
            return False
        
        connection = self.connections[connection_id]
        
        # Remove from connection subscription
        connection.remove_subscription(topic)
        
        # Remove from topic subscribers
        await self._remove_from_topic(connection_id, topic)
        
        if self.log_subscriptions:
            logger.info(get_log_message('websocket', 'subscription_removed',
                                       component='websocket.subscription',
                                       connection_id=connection_id, topic=topic))
        return True
    
    async def broadcast_to_topic(self, topic: str, data: Dict[str, Any]):
        """Broadcast to topic"""
        if topic not in self.topic_subscribers:
            # Smart logging: avoid warning for normal no-subscribers case
            if self.log_broadcasts:
                # For common data update topics, use debug level
                common_topics = ['devices.overview', 'experiments.overview', 'device_data_update']
                if any(common_topic in topic for common_topic in common_topics):
                    logger.debug(get_log_message('websocket', 'no_subscribers',
                                               component='websocket.broadcast',
                                               topic=topic))
                else:
                    logger.warning(get_log_message('websocket', 'no_subscribers',
                                                 component='websocket.broadcast',
                                                 topic=topic))
            return
        
        message = {
            "type": "data_update",
            "topic": topic,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        # Get subscribers for this topic
        subscribers = self.topic_subscribers[topic].copy()
        
        # Batch broadcast
        if self.batch_broadcast and len(subscribers) > self.batch_size:
            await self._batch_broadcast(subscribers, message)
        else:
            await self._direct_broadcast(subscribers, message)
        
        # Performance statistics
        if self.log_performance_stats:
            self._log_broadcast_stats(topic, len(subscribers))
    
    async def _batch_broadcast(self, subscribers: Set[str], message: Dict[str, Any]):
        """Batch broadcast"""
        successful_sends = 0
        failed_connections = []
        
        # Batch processing
        subscriber_list = list(subscribers)
        for i in range(0, len(subscriber_list), self.batch_size):
            batch = subscriber_list[i:i + self.batch_size]
            
            # Concurrent sending of this batch
            try:
                await asyncio.wait_for(
                    self._send_to_batch(batch, message),
                    timeout=self.broadcast_timeout
                )
            except asyncio.TimeoutError:
                logger.warning(get_log_message('websocket', 'performance_warning',
                                             component='websocket.broadcast',
                                             message=f"Batch broadcast timeout for {len(batch)} connections"))
    
    async def _send_to_batch(self, batch: List[str], message: Dict[str, Any]):
        """Send message to a batch of connections"""
        tasks = []
        for connection_id in batch:
            if connection_id in self.connections:
                connection = self.connections[connection_id]
                tasks.append(connection.send_message(message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _direct_broadcast(self, subscribers: Set[str], message: Dict[str, Any]):
        """Direct broadcast"""
        successful_sends = 0
        failed_connections = []
        
        for connection_id in subscribers:
            if connection_id in self.connections:
                connection = self.connections[connection_id]
                if await connection.send_message(message):
                    successful_sends += 1
                else:
                    failed_connections.append(connection_id)
            else:
                failed_connections.append(connection_id)
        
        # Clean up failed connections
        if self.enable_connection_cleanup:
            for connection_id in failed_connections:
                await self._remove_from_topic(connection_id, message.get("topic", ""))
        
        if self.log_broadcasts:
            logger.info(get_log_message('websocket', 'broadcast_topic_success',
                                       component='websocket.broadcast',
                                       topic=message.get("topic", "unknown"),
                                       subscriber_count=successful_sends))
    
    def _log_broadcast_stats(self, topic: str, subscriber_count: int):
        """Log broadcast statistics"""
        if subscriber_count > 100:  # Log performance warning when there are many connections
            logger.info(get_log_message('websocket', 'performance_warning',
                                       component='websocket.broadcast',
                                       message=f"Broadcasting to {subscriber_count} subscribers on topic {topic}"))
    
    async def broadcast_to_all(self, data: Dict[str, Any]):
        """Broadcast to all"""
        message = {
            "type": "broadcast",
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        successful_sends = 0
        failed_connections = []
        
        for connection_id, connection in self.connections.items():
            if await connection.send_message(message):
                successful_sends += 1
            else:
                failed_connections.append(connection_id)
        
        # Clean up failed connections
        if self.enable_connection_cleanup:
            for connection_id in failed_connections:
                await self.disconnect_client(connection_id)
        
        if self.log_broadcasts:
            logger.info(get_log_message('websocket', 'broadcast_all_success',
                                       component='websocket.broadcast',
                                       successful=successful_sends,
                                       failed=len(failed_connections)))
    
    def get_connection(self, connection_id: str) -> Optional[ConnectionHandler]:
        """Get connection"""
        return self.connections.get(connection_id)
    
    def is_running(self) -> bool:
        """Check if manager is running"""
        return self._running
    
    def get_connection_count(self) -> int:
        """Get connection count"""
        return len(self.connections)
    
    def get_subscription_count(self) -> int:
        """Get total subscription count"""
        return sum(len(subscribers) for subscribers in self.topic_subscribers.values())
    
    def get_topic_subscriber_count(self, topic: str) -> int:
        """Get subscriber count for a specific topic"""
        return len(self.topic_subscribers.get(topic, set()))
    
    def get_all_topics(self) -> List[str]:
        """Get all active topics"""
        return list(self.topic_subscribers.keys())
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get detailed connection information"""
        info = {
            "total_connections": len(self.connections),
            "active_connections": len([c for c in self.connections.values() if c.is_active]),
            "total_subscriptions": self.get_subscription_count(),
            "active_topics": len(self.topic_subscribers),
            "topics": {
                topic: len(subscribers) 
                for topic, subscribers in self.topic_subscribers.items()
            }
        }
        
        # Optional detailed connection information
        if get_config('websocket.performance.connection_stats_enabled', True, 'websocket.performance'):
            info["connections"] = [
                connection.get_connection_info() 
                for connection in self.connections.values()
            ]
        
        return info
    
    async def _remove_from_topic(self, connection_id: str, topic: str):
        """Remove connection from topic subscribers"""
        if topic in self.topic_subscribers:
            self.topic_subscribers[topic].discard(connection_id)
            
            # Clean up empty topics
            if self.cleanup_empty_topics and not self.topic_subscribers[topic]:
                del self.topic_subscribers[topic]
    
    async def _heartbeat_loop(self):
        """Heartbeat loop"""
        while self._running:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                if not self._running:
                    break
                
                # Send ping to all connections
                failed_connections = []
                
                for connection_id, connection in self.connections.items():
                    if not await connection.send_ping():
                        failed_connections.append(connection_id)
                
                # Clean up failed connections
                if self.enable_connection_cleanup:
                    for connection_id in failed_connections:
                        await self.disconnect_client(connection_id)
                
                if failed_connections and self.log_heartbeats:
                    logger.info(get_log_message('websocket', 'heartbeat_cleanup',
                                               component='websocket.heartbeat',
                                               count=len(failed_connections)))
                
                # Performance statistics
                if self.log_performance_stats and len(self.connections) > 0:
                    stats_interval = get_config('websocket.performance.stats_interval', 300, 'websocket.performance')
                    if int(datetime.now().timestamp()) % stats_interval == 0:
                        logger.info(get_log_message('websocket', 'stats_update',
                                                   component='websocket.stats',
                                                   connections=len(self.connections),
                                                   subscriptions=self.get_subscription_count(),
                                                   topics=len(self.topic_subscribers)))
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(get_log_message('websocket', 'heartbeat_error',
                                           component='websocket.heartbeat',
                                           error=str(e)))
    
    def _get_available_topics(self) -> List[str]:
        """Get available topic patterns"""
        return self.allowed_topic_patterns

# Global WebSocket manager instance - Singleton
websocket_manager = WebSocketManager() 

# Create config manager instance
config_manager = UnifiedConfigManager() 
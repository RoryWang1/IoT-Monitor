"""
PostgreSQL Database Connection Manager
The high-performance database layer of the IoT device monitoring system
"""

import asyncio
import asyncpg
import logging
import json
import ipaddress
import uuid
import time
import sys
import os
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from pathlib import Path

# Add configuration path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
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

class PostgreSQLDatabaseManager:
    """
    PostgreSQL Database Connection Manager
    Supports connection pooling, high-performance batch processing, and configuration-based maintenance
    """
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.is_initialized = False
        self._query_start_time = None
        
        # Get database settings from config
        self.connection_config = self._load_connection_config()
        self.pool_config = self._load_pool_config()
        self.server_settings = self._load_server_settings()
        self.maintenance_config = self._load_maintenance_config()
        self.performance_config = self._load_performance_config()
        
        logger.debug(f"Database manager initialized with config from {config_manager.environment} environment")
    
    def _get_database_port(self) -> int:
        """Get database port from unified config"""
        try:
            from config.unified_config_manager import UnifiedConfigManager
            config_manager = UnifiedConfigManager()
            return config_manager.get_database_port('database.connection')
        except Exception:
            return 5433  # fallback to default
    
    def _get_database_host(self) -> str:
        """Get database host from unified config"""
        try:
            from config.unified_config_manager import UnifiedConfigManager
            config_manager = UnifiedConfigManager()
            return config_manager.get_database_host('database.connection')
        except Exception:
            return 'localhost'  # fallback to default
    
    def _load_connection_config(self) -> Dict[str, Any]:
        """Load database connection settings from config with Docker environment detection"""
        # Check whether it is in a Docker environment
        is_docker = self._is_docker_environment()
        
        if is_docker:
            # Docker environment: use environment variables first, fall back to docker_connection configuration
            config_prefix = 'database.docker_connection'
            default_host = 'database'
            default_port = 5432
            default_user = 'postgres'
            default_password = 'postgres'
        else:
            # Local environment: use traditional configuration
            config_prefix = 'database.connection'
            default_host = self._get_database_host()
            default_port = self._get_database_port()
            default_user = 'iot_user'
            default_password = 'iot_password'
        
        return {
            'host': get_config(f'{config_prefix}.host', 
                             os.getenv('DB_HOST', default_host), 
                             'database.connection'),
            'port': get_config(f'{config_prefix}.port', 
                             int(os.getenv('DB_PORT', str(default_port))), 
                             'database.connection'),
            'database': get_config(f'{config_prefix}.database', 
                                 os.getenv('DB_NAME', 'iot_monitor'), 
                                 'database.connection'),
            'user': get_config(f'{config_prefix}.user', 
                             os.getenv('DB_USER', default_user), 
                             'database.connection'),
            'password': get_config(f'{config_prefix}.password', 
                                 os.getenv('DB_PASSWORD', default_password), 
                                 'database.connection')
        }
    
    def _is_docker_environment(self) -> bool:
        """Check if running in Docker environment"""
        # Method 1: check Docker environment variables
        if os.getenv('DOCKER_ENV') or os.getenv('DATABASE_HOST'):
            return True
        
        # Method 2: check /.dockerenv file
        if os.path.exists('/.dockerenv'):
            return True
            
        # Method 3: check cgroup information
        try:
            with open('/proc/1/cgroup', 'r') as f:
                if 'docker' in f.read():
                    return True
        except (FileNotFoundError, PermissionError):
            pass
        
        return False
    
    def _load_pool_config(self) -> Dict[str, Any]:
        """Load connection pool settings from config"""
        return {
            'min_size': get_config('database.pool.min_size', 5, 'database.pool'),
            'max_size': get_config('database.pool.max_size', 20, 'database.pool'),
            'command_timeout': get_config('database.pool.command_timeout', 60, 'database.pool'),
            'acquire_timeout': get_config('database.pool.acquire_timeout', 30, 'database.pool'),
            'idle_timeout': get_config('database.pool.idle_timeout', 300, 'database.pool')
        }
    
    def _load_server_settings(self) -> Dict[str, str]:
        """Load server settings from config"""
        return {
            'jit': get_config('database.server_settings.jit', 'off', 'database.server_settings'),
            'application_name': get_config('database.server_settings.application_name', 
                                         'IoT_Device_Monitor', 'database.server_settings'),
            'timezone': get_config('database.server_settings.timezone', 'UTC', 'database.server_settings'),
            'statement_timeout': get_config('database.server_settings.statement_timeout', 
                                          '30s', 'database.server_settings')
        }
    
    def _load_maintenance_config(self) -> Dict[str, Any]:
        """Load database maintenance settings from config"""
        return {
            'enable_auto_analyze': get_config('database.maintenance.enable_auto_analyze', 
                                            True, 'database.maintenance'),
            'enable_auto_vacuum': get_config('database.maintenance.enable_auto_vacuum', 
                                           False, 'database.maintenance'),
            'analyze_threshold': get_config('database.maintenance.analyze_threshold', 
                                          1000, 'database.maintenance'),
            'vacuum_threshold': get_config('database.maintenance.vacuum_threshold', 
                                         5000, 'database.maintenance')
        }
    
    def _load_performance_config(self) -> Dict[str, Any]:
        """Load performance monitoring settings from config"""
        return {
            'enable_query_logging': get_config('database.performance.enable_query_logging', 
                                             False, 'database.performance'),
            'slow_query_threshold_ms': get_config('database.performance.slow_query_threshold_ms', 
                                                1000, 'database.performance'),
            'enable_connection_pooling': get_config('database.performance.enable_connection_pooling', 
                                                   True, 'database.performance'),
            'max_connections_per_host': get_config('database.performance.max_connections_per_host', 
                                                  50, 'database.performance')
        }
    
    async def initialize(self) -> bool:
        """Initialize database connection pool with retry logic for Docker environments"""
        try:
            if self.pool:
                await self.close()
            
            logger.info(get_log_message('database', 'initializing', component='database.connection'))
            
            # Build connection pool configuration
            pool_kwargs = {
                **self.connection_config,
                **self.pool_config,
                'server_settings': self.server_settings
            }
            
            # Remove extra configuration items, only keep asyncpg needed
            pool_kwargs.pop('acquire_timeout', None)
            pool_kwargs.pop('idle_timeout', None)
            
            # Docker environment retry logic
            is_docker = self._is_docker_environment()
            max_retries = 30 if is_docker else 3
            retry_delay = 2 if is_docker else 1
            
            for attempt in range(1, max_retries + 1):
                try:
                    # Create connection pool
                    self.pool = await asyncpg.create_pool(**pool_kwargs)
                    
                    # Test connection
                    async with self.pool.acquire() as conn:
                        result = await conn.fetchval('SELECT version()')
                        logger.info(get_log_message('database', 'connected', component='database.connection',
                                                  version=result))
                    
                    self.is_initialized = True
                    
                    # Record pool configuration information
                    logger.info(get_log_message('database', 'pool_initialized', component='database.connection',
                                              min_size=self.pool_config['min_size'],
                                              max_size=self.pool_config['max_size']))
                    
                    # Optional performance logging
                    if self.performance_config['enable_query_logging']:
                        logger.debug(get_log_message('database', 'pool_stats', component='database.performance',
                                                   pool_size=self.pool.get_size(),
                                                   active=self.pool.get_size() - self.pool.get_idle_size(),
                                                   idle=self.pool.get_idle_size()))
                    
                    return True
                    
                except Exception as e:
                    if attempt < max_retries:
                        if is_docker:
                            logger.info(f"Database connection attempt {attempt}/{max_retries} failed, retrying in {retry_delay}s... ({str(e)})")
                        else:
                            logger.warning(f"Database connection attempt {attempt}/{max_retries} failed, retrying in {retry_delay}s...")
                        
                        # Clean up failed pool if exists
                        if self.pool:
                            try:
                                await self.pool.close()
                            except:
                                pass
                            self.pool = None
                        
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        raise e
            
            return False
            
        except Exception as e:
            logger.error(get_log_message('database', 'initialization_failed', component='database.connection',
                                       error=str(e)))
            self.is_initialized = False
            return False
    
    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            self.pool = None
            self.is_initialized = False
            logger.info(get_log_message('database', 'connection_closed', component='database.connection'))
    
    def _start_query_timer(self):
        """Start query timer (for performance monitoring)"""
        if self.performance_config['enable_query_logging']:
            self._query_start_time = time.time()
    
    def _check_query_performance(self, query: str):
        """Check query performance and record slow queries"""
        if (self.performance_config['enable_query_logging'] and 
            self._query_start_time is not None):
            
            duration_ms = (time.time() - self._query_start_time) * 1000
            
            if duration_ms > self.performance_config['slow_query_threshold_ms']:
                # Truncate long query for logging
                query_preview = query[:100] + "..." if len(query) > 100 else query
                logger.warning(get_log_message('database', 'slow_query_detected', 
                                             component='database.performance',
                                             duration=int(duration_ms),
                                             query=query_preview))
    
    async def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """Execute SELECT query and return dictionary list - with performance monitoring"""
        if not self.is_initialized or not self.pool:
            raise RuntimeError(get_log_message('database', 'not_initialized', component='database.connection'))
        
        self._start_query_timer()
        
        # Apply query timeout
        query_timeout = self.performance_config.get('query_timeout_seconds', 30)
        
        try:
            async with self.pool.acquire() as conn:
                if self.performance_config['enable_query_logging']:
                    logger.debug(get_log_message('database', 'connection_acquired', component='database.performance'))
                
                # Execute with timeout
                if params:
                    rows = await asyncio.wait_for(conn.fetch(query, *params), timeout=query_timeout)
                else:
                    rows = await asyncio.wait_for(conn.fetch(query), timeout=query_timeout)
                
                # Convert results, keep timezone information
                result = []
                for row in rows:
                    row_dict = dict(row)
                    # Convert special types to JSON serialization format
                    for key, value in row_dict.items():
                        if isinstance(value, (ipaddress.IPv4Address, ipaddress.IPv6Address)):
                            row_dict[key] = str(value)
                        elif isinstance(value, uuid.UUID):
                            row_dict[key] = str(value)
                        # Keep datetime object timezone information
                    result.append(row_dict)
                
                self._check_query_performance(query)
                
                if self.performance_config['enable_query_logging']:
                    logger.debug(get_log_message('database', 'connection_released', component='database.performance'))
                
                return result
                
        except Exception as e:
            logger.error(get_log_message('database', 'query_execution_failed', component='database.connection',
                                       error=str(e)))
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            raise
    
    async def execute_scalar(self, query: str, params: tuple = None) -> Any:
        """Execute query and return single scalar value"""
        if not self.is_initialized or not self.pool:
            raise RuntimeError(get_log_message('database', 'not_initialized', component='database.connection'))
        
        self._start_query_timer()
        
        try:
            async with self.pool.acquire() as conn:
                if params:
                    result = await conn.fetchval(query, *params)
                else:
                    result = await conn.fetchval(query)
                
                self._check_query_performance(query)
                return result
                    
        except Exception as e:
            logger.error(get_log_message('database', 'scalar_query_failed', component='database.connection',
                                       error=str(e)))
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            raise
    
    async def execute_command(self, command: str, params: tuple = None) -> str:
        """Execute INSERT/UPDATE/DELETE command and return status"""
        if not self.is_initialized or not self.pool:
            raise RuntimeError(get_log_message('database', 'not_initialized', component='database.connection'))
        
        self._start_query_timer()
        
        try:
            async with self.pool.acquire() as conn:
                if params:
                    result = await conn.execute(command, *params)
                else:
                    result = await conn.execute(command)
                
                self._check_query_performance(command)
                return result
                    
        except Exception as e:
            logger.error(get_log_message('database', 'command_execution_failed', component='database.connection',
                                       error=str(e)))
            logger.error(f"Command: {command}")
            logger.error(f"Params: {params}")
            raise
    
    async def execute_transaction(self, commands: List[tuple]) -> bool:
        """Execute multiple commands in a transaction"""
        if not self.is_initialized or not self.pool:
            raise RuntimeError(get_log_message('database', 'not_initialized', component='database.connection'))
        
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    for command, params in commands:
                        if params:
                            await conn.execute(command, *params)
                        else:
                            await conn.execute(command)
            return True
            
        except Exception as e:
            logger.error(get_log_message('database', 'transaction_failed', component='database.connection',
                                       error=str(e)))
            raise
    
    async def bulk_insert(self, table: str, columns: List[str], data: List[tuple]) -> int:
        """Use COPY for high-performance bulk insert"""
        if not self.is_initialized or not self.pool:
            raise RuntimeError(get_log_message('database', 'not_initialized', component='database.connection'))
        
        if not data:
            return 0
        
        try:
            async with self.pool.acquire() as conn:
                # Use COPY for high-performance bulk insert
                await conn.copy_records_to_table(
                    table, 
                    records=data, 
                    columns=columns
                )
                
                count = len(data)
                logger.info(get_log_message('database', 'bulk_insert_completed', component='database.connection',
                                          count=count, table=table))
                return count
                
        except Exception as e:
            logger.error(get_log_message('database', 'bulk_insert_failed', component='database.connection',
                                       error=str(e)))
            logger.error(f"Table: {table}, Columns: {columns}")
            raise
    
    async def get_table_stats(self) -> Dict[str, int]:
        """Get configured table statistics"""
        # Get monitored table list from config
        monitored_tables = get_config('database.tables.monitored', 
                                    ['devices', 'device_statistics', 'device_traffic_history', 'device_connections'],
                                    'database.tables')
        
        stats = {}
        timeout = get_config('database.health_check.table_stats_timeout', 5, 'database.health_check')
        
        for table in monitored_tables:
            try:
                # Add timeout control for each table query
                count = await asyncio.wait_for(
                    self.execute_scalar(f'SELECT COUNT(*) FROM {table}'),
                    timeout=timeout
                )
                stats[table] = count
            except asyncio.TimeoutError:
                logger.warning(f"Table stats timeout for {table}")
                stats[table] = -1  # Timeout
            except Exception as e:
                logger.warning(get_log_message('database', 'table_stats_failed', component='database.connection',
                                             table=table, error=str(e)))
                stats[table] = 0
        
        return stats
    
    async def optimize_database(self):
        """Run configured database optimization commands"""
        try:
            async with self.pool.acquire() as conn:
                # Run ANALYZE based on config
                if self.maintenance_config['enable_auto_analyze']:
                    logger.info(get_log_message('database', 'maintenance_analyze', component='database.maintenance'))
                await conn.execute('ANALYZE')
                
                # Run VACUUM based on config
                if self.maintenance_config['enable_auto_vacuum']:
                    logger.info(get_log_message('database', 'maintenance_vacuum', component='database.maintenance'))
                await conn.execute('VACUUM ANALYZE')
                
                logger.info(get_log_message('database', 'optimization_completed', component='database.maintenance'))
                
        except Exception as e:
            logger.error(get_log_message('database', 'optimization_failed', component='database.maintenance',
                                       error=str(e)))
    
    def format_json_param(self, data: Dict[str, Any]) -> str:
        """Format dictionary to PostgreSQL JSON string"""
        return json.dumps(data, default=str)
    
    def format_timestamp(self, dt: datetime) -> str:
        """Format datetime to PostgreSQL format"""
        return dt.isoformat()
    
    async def health_check(self) -> Dict[str, Any]:
        """Execute configured database health check"""
        try:
            if not self.is_initialized or not self.pool:
                return {
                    'status': 'error',
                    'message': get_log_message('database', 'not_initialized', component='database.health_check'),
                    'pool_size': 0,
                    'active_connections': 0
                }
            
            health_config = get_config('database.health_check', {}, 'database.health_check')
            result = {'status': 'healthy'}
            
            # Optional version information
            if health_config.get('include_version', True):
                version = await self.execute_scalar('SELECT version()')
                result['version'] = version
            
            # Optional connection pool statistics
            if health_config.get('include_pool_stats', True):
                pool_size = self.pool.get_size()
                active_connections = pool_size - self.pool.get_idle_size()
                result.update({
                    'pool_size': pool_size,
                    'active_connections': active_connections,
                    'idle_connections': self.pool.get_idle_size()
                })
            
            # Optional table statistics
            if health_config.get('include_table_stats', True):
                table_stats = await self.get_table_stats()
                result['table_stats'] = table_stats
            
            # Connection configuration information (without sensitive information)
            result['config'] = {
                'host': self.connection_config['host'],
                'port': self.connection_config['port'],
                'database': self.connection_config['database'],
                'pool_min_size': self.pool_config['min_size'],
                'pool_max_size': self.pool_config['max_size']
            }
            
            logger.debug(get_log_message('database', 'health_check_healthy', component='database.health_check'))
            return result
            
        except Exception as e:
            error_msg = str(e)
            logger.error(get_log_message('database', 'health_check_error', component='database.health_check',
                                       error=error_msg))
            return {
                'status': 'error',
                'message': error_msg,
                'pool_size': self.pool.get_size() if self.pool else 0,
                'active_connections': 0
            }

# Backward compatibility alias
DatabaseManager = PostgreSQLDatabaseManager 
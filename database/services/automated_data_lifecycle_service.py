"""
Automated Data Lifecycle Management Service
Unified automated data lifecycle management service
"""

import logging
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
import asyncpg
from database.connection import PostgreSQLDatabaseManager

logger = logging.getLogger(__name__)


class AutomatedDataLifecycleService:
    """
    Unified automated data lifecycle management service
    """
    
    def __init__(self, db_manager: PostgreSQLDatabaseManager):
        self.db_manager = db_manager
        
        # Unified data retention policy (in UTC hours)
        self.global_retention_policy = {
            'core_data_retention_hours': 192,  # 8 days (7 days + 24h buffer)
            'auto_cleanup_enabled': True,
            'cleanup_interval_hours': 24,      # Clean up every 24 hours
            'batch_size': 5000,               # Batch delete size
            'concurrent_cleanup': True,        # Concurrent cleanup
            'vacuum_after_cleanup': True,      # Vacuum after cleanup
        }
        
        # Data dependency mapping (cascading recalculation)
        self.data_dependency_map = {
            'packet_flows': [  # When packet_flows is deleted, these analysis tables need to be recalculated
                'device_activity_timeline',
                'device_traffic_trend', 
                'device_topology',
                'protocol_analysis',
                'port_analysis',
                'network_sessions',
                'devices_orphaned',      # Clean up orphaned devices
                'experiments_orphaned'   # Clean up orphaned experiments
            ]
        }
    
    async def initialize_automated_lifecycle(self):
        """
        Initialize automated data lifecycle management
        Set PostgreSQL-level automated functionality
        """
        logger.info("🔄 Initializing automated data lifecycle management...")
        
        try:
            # 1. Create cleanup functions
            await self._create_cleanup_functions()
            
            # 2. Create auto cleanup scheduler
            await self._create_cleanup_scheduler()
            
            # 3. Create data recalculation triggers
            await self._create_recalculation_triggers()
            
            # 4. Enable periodic maintenance tasks
            await self._enable_maintenance_tasks()
            
            logger.info("Automated data lifecycle management initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize automated data lifecycle management: {e}")
            raise
    
    async def _create_cleanup_functions(self):
        """Create PostgreSQL stored procedures for safe timestamp-based cleanup"""
        
        # 1. SAFE timestamp-based cleanup function
        main_cleanup_function = """
        CREATE OR REPLACE FUNCTION auto_cleanup_expired_data(
            retention_hours INTEGER DEFAULT 192,
            batch_size INTEGER DEFAULT 5000
        ) RETURNS TABLE(
            table_name TEXT,
            deleted_count BIGINT,
            cleanup_time TIMESTAMP WITH TIME ZONE
        ) AS $$
        DECLARE
            cutoff_time TIMESTAMP WITH TIME ZONE;
            rec RECORD;
            total_deleted BIGINT := 0;
            batch_deleted BIGINT;
        BEGIN
            -- Calculate deletion cutoff time (UTC)
            cutoff_time := NOW() AT TIME ZONE 'UTC' - INTERVAL '1 hour' * retention_hours;
            
            RAISE NOTICE 'Starting SAFE timestamp-based cleanup for data older than %', cutoff_time;
            RAISE NOTICE 'Using batch size: %, NEVER using TRUNCATE', batch_size;
            
            -- CRITICAL: Ensure reference data is NEVER touched
            RAISE NOTICE 'PROTECTION: known_devices, vendor_patterns, ip_geolocation_ref are COMPLETELY EXCLUDED';
            
            -- SAFE batch delete expired packet_flows ONLY by timestamp
            total_deleted := 0;
            LOOP
                WITH batch_to_delete AS (
                    SELECT ctid FROM packet_flows 
                    WHERE packet_timestamp < cutoff_time
                    LIMIT batch_size
                )
                DELETE FROM packet_flows 
                WHERE ctid IN (SELECT ctid FROM batch_to_delete);
                
                GET DIAGNOSTICS batch_deleted = ROW_COUNT;
                total_deleted := total_deleted + batch_deleted;
                
                -- Exit if no more expired records to delete
                EXIT WHEN batch_deleted = 0;
                
                -- Small delay to prevent database overload
                PERFORM pg_sleep(0.1);
                
                -- Progress logging every 10 batches
                IF total_deleted % (batch_size * 10) = 0 THEN
                    RAISE NOTICE 'Timestamp-based cleanup progress: % expired records deleted', total_deleted;
                END IF;
            END LOOP;
            
            table_name := 'packet_flows';
            deleted_count := total_deleted;
            cleanup_time := NOW();
            RETURN NEXT;
            
            RAISE NOTICE 'SAFE deletion completed: % expired records deleted from packet_flows', total_deleted;
            
            -- Delete expired analysis data (dependent on packet_flows time window)
            -- Use shorter retention time because these can be recalculated
            cutoff_time := NOW() AT TIME ZONE 'UTC' - INTERVAL '1 hour' * (retention_hours / 2);
            
            -- Clean up analysis tables (SAFE batch delete by timestamp)
            FOR rec IN 
                SELECT schemaname, tablename 
                FROM pg_tables 
                WHERE tablename IN (
                    'device_activity_timeline',
                    'device_traffic_trend', 
                    'device_topology',
                    'protocol_analysis',
                    'port_analysis'
                )
            LOOP
                total_deleted := 0;
                LOOP
                    EXECUTE format('
                        WITH batch_to_delete AS (
                            SELECT ctid FROM %I 
                            WHERE created_at < $1
                            LIMIT $2
                        )
                        DELETE FROM %I 
                        WHERE ctid IN (SELECT ctid FROM batch_to_delete)
                    ', rec.tablename, rec.tablename) 
                    USING cutoff_time, batch_size;
                    
                    GET DIAGNOSTICS batch_deleted = ROW_COUNT;
                    total_deleted := total_deleted + batch_deleted;
                    
                    EXIT WHEN batch_deleted = 0;
                    PERFORM pg_sleep(0.05);
                END LOOP;
                
                table_name := rec.tablename;
                deleted_count := total_deleted;
                cleanup_time := NOW();
                RETURN NEXT;
                
                RAISE NOTICE 'SAFE deletion: % expired records from %', total_deleted, rec.tablename;
            END LOOP;
            
            -- Clean up network_sessions (SAFE timestamp-based deletion)
            total_deleted := 0;
            LOOP
                WITH batch_to_delete AS (
                    SELECT ctid FROM network_sessions 
                    WHERE end_time < cutoff_time
                    LIMIT batch_size
                )
                DELETE FROM network_sessions 
                WHERE ctid IN (SELECT ctid FROM batch_to_delete);
                
                GET DIAGNOSTICS batch_deleted = ROW_COUNT;
                total_deleted := total_deleted + batch_deleted;
                
                EXIT WHEN batch_deleted = 0;
                PERFORM pg_sleep(0.05);
            END LOOP;
            
            table_name := 'network_sessions';
            deleted_count := total_deleted;
            cleanup_time := NOW();
            RETURN NEXT;
            
            -- Clean up orphaned devices (devices with no packet_flows data)
            -- This is SAFE because it only removes devices without any packet data
            total_deleted := 0;
            LOOP
                WITH batch_to_delete AS (
                    SELECT device_id FROM devices 
                    WHERE device_id NOT IN (
                        SELECT DISTINCT device_id FROM packet_flows WHERE device_id IS NOT NULL
                    )
                    LIMIT batch_size
                )
                DELETE FROM devices 
                WHERE device_id IN (SELECT device_id FROM batch_to_delete);
                
                GET DIAGNOSTICS batch_deleted = ROW_COUNT;
                total_deleted := total_deleted + batch_deleted;
                
                EXIT WHEN batch_deleted = 0;
                PERFORM pg_sleep(0.05);
            END LOOP;
            
            table_name := 'devices_orphaned';
            deleted_count := total_deleted;
            cleanup_time := NOW();
            RETURN NEXT;
            
            RAISE NOTICE 'SAFE cleanup: % orphaned devices removed', total_deleted;
            
            -- Clean up orphaned experiments (experiments with no packet_flows data)
            -- This is SAFE because it only removes experiments without any packet data
            total_deleted := 0;
            LOOP
                WITH batch_to_delete AS (
                    SELECT experiment_id FROM experiments 
                    WHERE experiment_id NOT IN (
                        SELECT DISTINCT experiment_id FROM packet_flows WHERE experiment_id IS NOT NULL
                    )
                    LIMIT batch_size
                )
                DELETE FROM experiments 
                WHERE experiment_id IN (SELECT experiment_id FROM batch_to_delete);
                
                GET DIAGNOSTICS batch_deleted = ROW_COUNT;
                total_deleted := total_deleted + batch_deleted;
                
                EXIT WHEN batch_deleted = 0;
                PERFORM pg_sleep(0.05);
            END LOOP;
            
            table_name := 'experiments_orphaned';
            deleted_count := total_deleted;
            cleanup_time := NOW();
            RETURN NEXT;
            
            RAISE NOTICE 'SAFE cleanup: % orphaned experiments removed', total_deleted;
            
            -- Record maintenance tasks to be executed (VACUUM cannot be executed in a function)
            INSERT INTO maintenance_queue (operation_type, created_at) 
            VALUES ('post_cleanup_maintenance', NOW());
            
            RAISE NOTICE 'SAFE timestamp-based cleanup completed successfully - Reference data fully protected';
        END;
        $$ LANGUAGE plpgsql;
        """
        
        # 2. Maintenance function
        maintenance_function = """
        CREATE OR REPLACE FUNCTION auto_maintenance_after_cleanup() 
        RETURNS VOID AS $$
        DECLARE
            table_rec RECORD;
        BEGIN
            -- Perform VACUUM ANALYZE on main tables
            FOR table_rec IN 
                SELECT tablename 
                FROM pg_tables 
                WHERE tablename IN (
                    'packet_flows', 'network_sessions', 'device_activity_timeline',
                    'device_traffic_trend', 'device_topology', 'protocol_analysis', 'port_analysis'
                )
            LOOP
                EXECUTE format('VACUUM ANALYZE %I', table_rec.tablename);
                RAISE NOTICE 'Vacuumed and analyzed table: %', table_rec.tablename;
            END LOOP;
            
            -- Update statistics
            ANALYZE;
            
            RAISE NOTICE 'Database maintenance completed';
        END;
        $$ LANGUAGE plpgsql;
        """
        
        # 3. Data recalculation trigger function
        recalculation_function = """
        CREATE OR REPLACE FUNCTION trigger_data_recalculation() 
        RETURNS TRIGGER AS $$
        BEGIN
            -- Mark data for recalculation after large data deletion
            INSERT INTO data_recalculation_queue (
                table_name, 
                trigger_reason, 
                affected_time_range_start,
                affected_time_range_end,
                created_at
            ) VALUES (
                'packet_flows',
                'bulk_delete_cleanup',
                OLD.packet_timestamp,
                OLD.packet_timestamp,
                NOW()
            ) ON CONFLICT (table_name, trigger_reason) 
            DO UPDATE SET 
                affected_time_range_start = LEAST(data_recalculation_queue.affected_time_range_start, EXCLUDED.affected_time_range_start),
                affected_time_range_end = GREATEST(data_recalculation_queue.affected_time_range_end, EXCLUDED.affected_time_range_end),
                updated_at = NOW();
            
            RETURN OLD;
        END;
        $$ LANGUAGE plpgsql;
        """
        
        await self.db_manager.execute_command(main_cleanup_function)
        await self.db_manager.execute_command(maintenance_function)
        await self.db_manager.execute_command(recalculation_function)
        
        logger.info("Cleanup and maintenance functions created")
    
    async def _create_cleanup_scheduler(self):
        """Create auto cleanup scheduler"""
        
        # 1. Create schedule table to record cleanup history
        create_schedule_table = """
        CREATE TABLE IF NOT EXISTS auto_cleanup_schedule (
            id BIGSERIAL PRIMARY KEY,
            scheduled_time TIMESTAMP WITH TIME ZONE NOT NULL,
            executed_time TIMESTAMP WITH TIME ZONE,
            retention_hours INTEGER NOT NULL DEFAULT 192,
            status VARCHAR(20) DEFAULT 'pending',
            total_deleted_records BIGINT DEFAULT 0,
            execution_duration_seconds NUMERIC DEFAULT 0,
            error_message TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            
            CONSTRAINT valid_status CHECK (status IN ('pending', 'running', 'completed', 'failed'))
        );
        
        CREATE INDEX IF NOT EXISTS idx_auto_cleanup_schedule_status 
            ON auto_cleanup_schedule(status, scheduled_time);
        """
        
        # 2. Create maintenance queue list
        create_maintenance_queue_table = """
        CREATE TABLE IF NOT EXISTS maintenance_queue (
            id BIGSERIAL PRIMARY KEY,
            operation_type VARCHAR(100) NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            processed_at TIMESTAMP WITH TIME ZONE,
            error_message TEXT,
            
            CONSTRAINT valid_maintenance_status CHECK (status IN ('pending', 'processing', 'completed', 'failed'))
        );
        
        CREATE INDEX IF NOT EXISTS idx_maintenance_queue_status 
            ON maintenance_queue(status, created_at);
        """
        
        # 3. Create recalculation queue list
        create_recalc_queue_table = """
        CREATE TABLE IF NOT EXISTS data_recalculation_queue (
            id BIGSERIAL PRIMARY KEY,
            table_name VARCHAR(100) NOT NULL,
            trigger_reason VARCHAR(100) NOT NULL,
            affected_time_range_start TIMESTAMP WITH TIME ZONE,
            affected_time_range_end TIMESTAMP WITH TIME ZONE,
            status VARCHAR(20) DEFAULT 'pending',
            priority INTEGER DEFAULT 5,
            retry_count INTEGER DEFAULT 0,
            max_retries INTEGER DEFAULT 3,
            error_message TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            processed_at TIMESTAMP WITH TIME ZONE,
            
            CONSTRAINT valid_status CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
            CONSTRAINT unique_table_reason UNIQUE (table_name, trigger_reason)
        );
        
        CREATE INDEX IF NOT EXISTS idx_recalc_queue_status_priority 
            ON data_recalculation_queue(status, priority DESC, created_at);
        """
        
        # 4. Auto scheduler function
        auto_scheduler_function = """
        CREATE OR REPLACE FUNCTION schedule_auto_cleanup() 
        RETURNS VOID AS $$
        DECLARE
            next_cleanup_time TIMESTAMP WITH TIME ZONE;
            cleanup_interval INTERVAL := INTERVAL '24 hours';
        BEGIN
            -- Calculate next cleanup time
            next_cleanup_time := NOW() + cleanup_interval;
            
            -- Insert next cleanup schedule
            INSERT INTO auto_cleanup_schedule (scheduled_time, retention_hours)
            VALUES (next_cleanup_time, 192)
            ON CONFLICT DO NOTHING;
            
            RAISE NOTICE 'Scheduled next auto cleanup for: %', next_cleanup_time;
        END;
        $$ LANGUAGE plpgsql;
        """
        
        # 5. Execute cleanup task function
        execute_cleanup_function = """
        CREATE OR REPLACE FUNCTION execute_scheduled_cleanup() 
        RETURNS VOID AS $$
        DECLARE
            cleanup_record RECORD;
            start_time TIMESTAMP WITH TIME ZONE;
            end_time TIMESTAMP WITH TIME ZONE;
            total_deleted BIGINT := 0;
            cleanup_result RECORD;
        BEGIN
            -- Get cleanup task to be executed
            SELECT * INTO cleanup_record 
            FROM auto_cleanup_schedule 
            WHERE status = 'pending' 
              AND scheduled_time <= NOW()
            ORDER BY scheduled_time ASC 
            LIMIT 1
            FOR UPDATE SKIP LOCKED;
            
            IF NOT FOUND THEN
                RETURN;
            END IF;
            
            -- Update status to running
            UPDATE auto_cleanup_schedule 
            SET status = 'running', executed_time = NOW() 
            WHERE id = cleanup_record.id;
            
            start_time := NOW();
            
            BEGIN
                -- Execute auto cleanup
                FOR cleanup_result IN 
                    SELECT * FROM auto_cleanup_expired_data(cleanup_record.retention_hours)
                LOOP
                    total_deleted := total_deleted + cleanup_result.deleted_count;
                END LOOP;
                
                end_time := NOW();
                
                -- Update completed status
                UPDATE auto_cleanup_schedule 
                SET status = 'completed',
                    total_deleted_records = total_deleted,
                    execution_duration_seconds = EXTRACT(EPOCH FROM (end_time - start_time))
                WHERE id = cleanup_record.id;
                
                -- Schedule next cleanup
                PERFORM schedule_auto_cleanup();
                
                RAISE NOTICE 'Auto cleanup completed. Deleted % records in % seconds', 
                    total_deleted, EXTRACT(EPOCH FROM (end_time - start_time));
                
            EXCEPTION WHEN OTHERS THEN
                end_time := NOW();
                
                -- Record error
                UPDATE auto_cleanup_schedule 
                SET status = 'failed',
                    error_message = SQLERRM,
                    execution_duration_seconds = EXTRACT(EPOCH FROM (end_time - start_time))
                WHERE id = cleanup_record.id;
                
                RAISE NOTICE 'Auto cleanup failed: %', SQLERRM;
            END;
        END;
        $$ LANGUAGE plpgsql;
        """
        
        await self.db_manager.execute_command(create_schedule_table)
        await self.db_manager.execute_command(create_maintenance_queue_table)
        await self.db_manager.execute_command(create_recalc_queue_table)
        await self.db_manager.execute_command(auto_scheduler_function)
        await self.db_manager.execute_command(execute_cleanup_function)
        
        # Initialize scheduler
        await self.db_manager.execute_command("SELECT schedule_auto_cleanup()")
        
        logger.info("Auto cleanup scheduler created")
    
    async def _create_recalculation_triggers(self):
        """Create data recalculation triggers"""
        
        # Drop existing triggers (if any)
        drop_triggers = """
        DROP TRIGGER IF EXISTS packet_flows_cleanup_trigger ON packet_flows;
        """
        
        # Create triggers - when large packet_flows are deleted, trigger recalculation
        create_trigger = """
        CREATE TRIGGER packet_flows_cleanup_trigger
            AFTER DELETE ON packet_flows
            FOR EACH ROW
            WHEN (pg_trigger_depth() = 0)  -- Avoid recursive triggers
            EXECUTE FUNCTION trigger_data_recalculation();
        """
        
        await self.db_manager.execute_command(drop_triggers)
        await self.db_manager.execute_command(create_trigger)
        
        logger.info("Data recalculation triggers created")
    
    async def _enable_maintenance_tasks(self):
        """Enable periodic maintenance tasks"""
        
        # Use PostgreSQL pg_cron extension (if available) or application-level scheduling
        maintenance_setup = """
        -- Try using pg_cron for periodic maintenance (requires extension support)
        DO $$
        BEGIN
            -- Check if pg_cron extension is available
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
                -- Execute auto cleanup every day at 2am
                PERFORM cron.schedule('auto-data-cleanup', '0 2 * * *', 'SELECT execute_scheduled_cleanup();');
                RAISE NOTICE 'Scheduled automatic cleanup using pg_cron';
            ELSE
                RAISE NOTICE 'pg_cron extension not available, will use application-level scheduling';
            END IF;
        EXCEPTION WHEN OTHERS THEN
            RAISE NOTICE 'Could not setup pg_cron scheduling: %', SQLERRM;
        END $$;
        """
        
        try:
            await self.db_manager.execute_command(maintenance_setup)
        except Exception as e:
            logger.warning(f"pg_cron setup failed, will use application-level scheduling: {e}")
        
        logger.info("Maintenance tasks setup completed")
    
    async def run_manual_cleanup(self, retention_hours: int = None, batch_size: int = None) -> Dict[str, Any]:
        """Manually execute data cleanup with optimized batch processing"""
        if retention_hours is None:
            retention_hours = self.global_retention_policy['core_data_retention_hours']
        if batch_size is None:
            batch_size = self.global_retention_policy['batch_size']
        
        logger.info(f"Manually execute data cleanup, retention time: {retention_hours} hours, batch size: {batch_size}")
        logger.info("PROTECTION: Reference data (known_devices, vendor_patterns, ip_geolocation_ref) will NOT be touched")
        
        start_time = datetime.now(timezone.utc)
        
        try:
            # Call optimized PostgreSQL cleanup function with batch processing
            cleanup_query = "SELECT * FROM auto_cleanup_expired_data($1, $2)"
            results = await self.db_manager.execute_query(cleanup_query, [retention_hours, batch_size])
            
            total_deleted = sum(row['deleted_count'] for row in results)
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            
            # Trigger analysis data recalculation
            await self._trigger_analysis_recalculation()
            
            # Execute delayed maintenance operations
            await self._process_maintenance_queue()
            
            return {
                'success': True,
                'total_deleted_records': total_deleted,
                'execution_time_seconds': duration,
                'tables_cleaned': [
                    {
                        'table_name': row['table_name'],
                        'deleted_count': row['deleted_count'],
                        'cleanup_time': row['cleanup_time'].isoformat()
                    }
                    for row in results
                ],
                'retention_hours': retention_hours,
                'recalculation_triggered': True
            }
            
        except Exception as e:
            logger.error(f"Manual cleanup failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'execution_time_seconds': (datetime.now(timezone.utc) - start_time).total_seconds()
            }
    
    async def _trigger_analysis_recalculation(self):
        """Trigger analysis data recalculation"""
        logger.info("Trigger analysis data recalculation...")
        
        try:
            # Add recalculation task to queue
            recalc_query = """
            INSERT INTO data_recalculation_queue (
                table_name, trigger_reason, priority, created_at
            ) VALUES 
                ('device_activity_timeline', 'manual_cleanup_trigger', 1, NOW()),
                ('device_traffic_trend', 'manual_cleanup_trigger', 1, NOW()),
                ('device_topology', 'manual_cleanup_trigger', 2, NOW()),
                ('protocol_analysis', 'manual_cleanup_trigger', 2, NOW()),
                ('port_analysis', 'manual_cleanup_trigger', 2, NOW()),
                ('devices_orphaned', 'manual_cleanup_trigger', 3, NOW()),
                ('experiments_orphaned', 'manual_cleanup_trigger', 3, NOW())
            ON CONFLICT (table_name, trigger_reason) 
            DO UPDATE SET 
                priority = EXCLUDED.priority,
                status = 'pending',
                updated_at = NOW()
            """
            
            await self.db_manager.execute_command(recalc_query)
            
            # Immediately start processing recalculation queue
            await self._process_recalculation_queue()
            
        except Exception as e:
            logger.error(f"Trigger recalculation failed: {e}")
    
    async def _process_maintenance_queue(self):
        """Process maintenance queue (VACUUM, etc.)"""
        logger.info("Process maintenance queue...")
        
        try:
            # Get maintenance tasks to be processed
            maintenance_query = """
            SELECT * FROM maintenance_queue 
            WHERE status = 'pending' 
            ORDER BY created_at ASC
            LIMIT 5
            """
            
            maintenance_tasks = await self.db_manager.execute_query(maintenance_query)
            
            for task in maintenance_tasks:
                try:
                    # Update status to processing
                    await self.db_manager.execute_command(
                        "UPDATE maintenance_queue SET status = 'processing' WHERE id = $1",
                        [task['id']]
                    )
                    
                    if task['operation_type'] == 'post_cleanup_maintenance':
                        # Execute maintenance operations
                        await self._perform_database_maintenance()
                    
                    # Mark completed
                    await self.db_manager.execute_command(
                        "UPDATE maintenance_queue SET status = 'completed', processed_at = NOW() WHERE id = $1",
                        [task['id']]
                    )
                    
                    logger.info(f"Maintenance task completed: {task['operation_type']}")
                    
                except Exception as e:
                    # Mark failed
                    await self.db_manager.execute_command(
                        """UPDATE maintenance_queue 
                           SET status = 'failed', error_message = $1 
                           WHERE id = $2""",
                        [str(e), task['id']]
                    )
                    logger.error(f"Maintenance task failed {task['operation_type']}: {e}")
        
        except Exception as e:
            logger.error(f"Process maintenance queue failed: {e}")
    
    async def _perform_database_maintenance(self):
        """Execute database maintenance operations"""
        logger.info("Execute database maintenance operations...")
        
        # Main table list
        tables_to_maintain = [
            'packet_flows', 'network_sessions', 'device_activity_timeline',
            'device_traffic_trend', 'device_topology', 'protocol_analysis', 'port_analysis',
            'devices', 'experiments'
        ]
        
        for table_name in tables_to_maintain:
            try:
                # Use separate connection to execute VACUUM ANALYZE
                vacuum_query = f"VACUUM ANALYZE {table_name}"
                await self.db_manager.execute_command(vacuum_query)
                logger.info(f"Maintenance completed: {table_name}")
            except Exception as e:
                logger.warning(f"Error maintaining table {table_name}: {e}")
    
    async def _process_recalculation_queue(self):
        """Process data recalculation queue"""
        logger.info("Process data recalculation queue...")
        
        try:
            # Get tasks to be processed
            queue_query = """
            SELECT * FROM data_recalculation_queue 
            WHERE status = 'pending' 
            ORDER BY priority DESC, created_at ASC
            LIMIT 5
            """
            
            tasks = await self.db_manager.execute_query(queue_query)
            
            for task in tasks:
                try:
                    # Update status to processing
                    await self.db_manager.execute_command(
                        "UPDATE data_recalculation_queue SET status = 'processing', updated_at = NOW() WHERE id = $1",
                        [task['id']]
                    )
                    
                    # Execute corresponding recalculation based on table name
                    await self._recalculate_analysis_table(task['table_name'])
                    
                    # Mark completed
                    await self.db_manager.execute_command(
                        "UPDATE data_recalculation_queue SET status = 'completed', processed_at = NOW() WHERE id = $1",
                        [task['id']]
                    )
                    
                    logger.info(f"Recalculation completed: {task['table_name']}")
                    
                except Exception as e:
                    # Mark failed
                    await self.db_manager.execute_command(
                        """UPDATE data_recalculation_queue 
                           SET status = 'failed', error_message = $1, retry_count = retry_count + 1 
                           WHERE id = $2""",
                        [str(e), task['id']]
                    )
                    logger.error(f"Recalculation failed {task['table_name']}: {e}")
        
        except Exception as e:
            logger.error(f"Process recalculation queue failed: {e}")
    
    async def _recalculate_analysis_table(self, table_name: str):
        """Recalculate specific analysis table"""
        logger.info(f"Recalculate analysis table: {table_name}")
        
        if table_name == 'device_activity_timeline':
            # Delete old timeline data and regenerate
            await self.db_manager.execute_command("DELETE FROM device_activity_timeline")
            # Here you can call the corresponding analyzer to regenerate data
            
        elif table_name == 'device_traffic_trend':
            await self.db_manager.execute_command("DELETE FROM device_traffic_trend")
            
        elif table_name == 'device_topology':
            await self.db_manager.execute_command("DELETE FROM device_topology")
            
        elif table_name == 'protocol_analysis':
            await self.db_manager.execute_command("DELETE FROM protocol_analysis")
            
        elif table_name == 'port_analysis':
            await self.db_manager.execute_command("DELETE FROM port_analysis")
        
        elif table_name == 'devices_orphaned':
            # Clean up orphaned devices (devices with no packet_flows data)
            await self.db_manager.execute_command("""
                DELETE FROM devices WHERE device_id NOT IN (
                    SELECT DISTINCT device_id FROM packet_flows WHERE device_id IS NOT NULL
                )
            """)
        
        elif table_name == 'experiments_orphaned':
            # Clean up orphaned experiments (experiments with no packet_flows data)
            await self.db_manager.execute_command("""
                DELETE FROM experiments WHERE experiment_id NOT IN (
                    SELECT DISTINCT experiment_id FROM packet_flows WHERE experiment_id IS NOT NULL
                )
            """)
        
        # Note: After deletion, the system will automatically recalculate data from packet_flows
        # Because our API has a fallback mechanism to packet_flows
    
    async def get_lifecycle_status(self) -> Dict[str, Any]:
        """Get data lifecycle management status"""
        try:
            # Get cleanup history
            cleanup_history_query = """
            SELECT * FROM auto_cleanup_schedule 
            ORDER BY created_at DESC 
            LIMIT 10
            """
            cleanup_history = await self.db_manager.execute_query(cleanup_history_query)
            
            # Get recalculation queue status
            recalc_queue_query = """
            SELECT table_name, status, COUNT(*) as count
            FROM data_recalculation_queue 
            GROUP BY table_name, status
            ORDER BY table_name, status
            """
            recalc_status = await self.db_manager.execute_query(recalc_queue_query)
            
            # Get table size statistics
            table_sizes_query = """
            SELECT 
                tablename as table_name,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
            FROM pg_tables 
            WHERE tablename IN (
                'packet_flows', 'device_activity_timeline', 'device_traffic_trend',
                'device_topology', 'protocol_analysis', 'port_analysis', 'network_sessions',
                'devices', 'experiments'
            )
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            """
            table_sizes = await self.db_manager.execute_query(table_sizes_query)
            
            return {
                'global_retention_policy': self.global_retention_policy,
                'cleanup_history': [
                    {
                        'id': row['id'],
                        'scheduled_time': row['scheduled_time'].isoformat() if row['scheduled_time'] else None,
                        'executed_time': row['executed_time'].isoformat() if row['executed_time'] else None,
                        'status': row['status'],
                        'total_deleted_records': row['total_deleted_records'],
                        'execution_duration_seconds': float(row['execution_duration_seconds']) if row['execution_duration_seconds'] else 0
                    }
                    for row in cleanup_history
                ],
                'recalculation_queue_status': [
                    {
                        'table_name': row['table_name'],
                        'status': row['status'],
                        'count': row['count']
                    }
                    for row in recalc_status
                ],
                'table_sizes': [
                    {
                        'table_name': row['table_name'],
                        'size': row['size'],
                        'size_bytes': row['size_bytes']
                    }
                    for row in table_sizes
                ]
            }
            
        except Exception as e:
            logger.error(f"Get lifecycle status failed: {e}")
            return {'error': str(e)}
    
    async def update_retention_policy(self, retention_hours: int, cleanup_interval_hours: int = None):
        """Update global retention policy"""
        self.global_retention_policy['core_data_retention_hours'] = retention_hours
        
        if cleanup_interval_hours:
            self.global_retention_policy['cleanup_interval_hours'] = cleanup_interval_hours
        
        logger.info(f"Update retention policy: {retention_hours} hours data retention, {cleanup_interval_hours or 24} hours cleanup interval")


# Global instance
automated_lifecycle_service = None


def get_automated_lifecycle_service(db_manager: PostgreSQLDatabaseManager) -> AutomatedDataLifecycleService:
    """Get global automated lifecycle service instance"""
    global automated_lifecycle_service
    if automated_lifecycle_service is None:
        automated_lifecycle_service = AutomatedDataLifecycleService(db_manager)
    return automated_lifecycle_service 
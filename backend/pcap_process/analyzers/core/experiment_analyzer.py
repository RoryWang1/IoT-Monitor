"""
Experiment analyzer
Extracted experiment-level analysis logic from DataAnalyzer
"""

import logging
from typing import Dict, List, Any
from datetime import datetime, timezone, timedelta
import asyncio
import json

logger = logging.getLogger(__name__)


class ExperimentAnalyzer:
    """Experiment-level data analyzer"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.utc_timezone = timezone.utc
    
    async def ensure_analysis_tables(self):
        """Ensure all analysis tables exist, create them if they don't"""
        
        logger.info("Checking and creating analysis tables if needed...")
        
        # Define SQL for creating all required analysis tables
        table_definitions = {
            'device_activity_timeline': """
                CREATE TABLE IF NOT EXISTS device_activity_timeline (
                    id BIGSERIAL PRIMARY KEY,
                    device_id UUID NOT NULL,
                    experiment_id VARCHAR(50) NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                    time_window VARCHAR(10) NOT NULL DEFAULT '1h',
                    hour INTEGER NOT NULL DEFAULT 0,
                    minute INTEGER NOT NULL DEFAULT 0,
                    activity_level DECIMAL(5,2) NOT NULL DEFAULT 0,
                    packets INTEGER NOT NULL DEFAULT 0,
                    bytes BIGINT NOT NULL DEFAULT 0,
                    sessions INTEGER NOT NULL DEFAULT 0,
                    pattern VARCHAR(20) DEFAULT 'normal',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    
                    CONSTRAINT valid_time_window CHECK (time_window IN ('1h', '6h', '12h', '24h', '48h')),
                    CONSTRAINT valid_pattern CHECK (pattern IN ('normal', 'peak', 'low', 'anomaly', 'business', 'morning', 'night', 'evening')),
                    CONSTRAINT valid_hour CHECK (hour >= 0 AND hour <= 23),
                    CONSTRAINT valid_minute CHECK (minute >= 0 AND minute <= 59),
                    CONSTRAINT positive_values CHECK (packets >= 0 AND bytes >= 0 AND sessions >= 0),
                    CONSTRAINT unique_device_activity_timeline UNIQUE (device_id, experiment_id, time_window, timestamp)
                );
                
                CREATE INDEX IF NOT EXISTS idx_device_activity_device_time 
                    ON device_activity_timeline(device_id, time_window);
                CREATE INDEX IF NOT EXISTS idx_device_activity_experiment 
                    ON device_activity_timeline(experiment_id, device_id);
                CREATE INDEX IF NOT EXISTS idx_device_activity_timestamp 
                    ON device_activity_timeline(timestamp DESC);
            """,
            
            'device_traffic_trend': """
                CREATE TABLE IF NOT EXISTS device_traffic_trend (
                    id BIGSERIAL PRIMARY KEY,
                    device_id UUID NOT NULL,
                    experiment_id VARCHAR(50) NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                    time_window VARCHAR(10) NOT NULL DEFAULT '1h',
                    packets INTEGER NOT NULL DEFAULT 0,
                    bytes BIGINT NOT NULL DEFAULT 0,
                    sessions INTEGER NOT NULL DEFAULT 0,
                    protocol_data JSONB DEFAULT '{}',
                    pattern VARCHAR(20) DEFAULT 'normal',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    
                    CONSTRAINT valid_time_window CHECK (time_window IN ('1h', '6h', '12h', '24h', '48h')),
                    CONSTRAINT valid_pattern CHECK (pattern IN ('normal', 'business', 'evening', 'night', 'weekend', 'low', 'peak', 'burst', 'idle', 'active')),
                    CONSTRAINT positive_values CHECK (packets >= 0 AND bytes >= 0 AND sessions >= 0),
                    CONSTRAINT unique_device_traffic_trend UNIQUE (device_id, experiment_id, time_window, timestamp)
                );
                
                CREATE INDEX IF NOT EXISTS idx_device_trend_device_time 
                    ON device_traffic_trend(device_id, time_window);
                CREATE INDEX IF NOT EXISTS idx_device_trend_experiment 
                    ON device_traffic_trend(experiment_id, device_id);
                CREATE INDEX IF NOT EXISTS idx_device_trend_timestamp 
                    ON device_traffic_trend(timestamp DESC);
            """,
            
            'device_topology': """
                CREATE TABLE IF NOT EXISTS device_topology (
                    id BIGSERIAL PRIMARY KEY,
                    device_id UUID NOT NULL,
                    experiment_id VARCHAR(50) NOT NULL,
                    time_window VARCHAR(10) NOT NULL DEFAULT '1h',
                    topology_data JSONB NOT NULL DEFAULT '{}',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    
                    CONSTRAINT valid_time_window CHECK (time_window IN ('1h', '6h', '12h', '24h', '48h')),
                    CONSTRAINT unique_device_topology UNIQUE (device_id, experiment_id, time_window)
                );
                
                CREATE INDEX IF NOT EXISTS idx_device_topology_device_time 
                    ON device_topology(device_id, time_window);
                CREATE INDEX IF NOT EXISTS idx_device_topology_experiment 
                    ON device_topology(experiment_id, device_id);
            """,
            
            'protocol_analysis': """
                CREATE TABLE IF NOT EXISTS protocol_analysis (
                    id BIGSERIAL PRIMARY KEY,
                    device_id UUID NOT NULL,
                    experiment_id VARCHAR(50) NOT NULL,
                    time_window VARCHAR(10) NOT NULL DEFAULT '1h',
                    protocol VARCHAR(50) NOT NULL,
                    packet_count BIGINT NOT NULL DEFAULT 0,
                    byte_count BIGINT NOT NULL DEFAULT 0,
                    session_count INTEGER NOT NULL DEFAULT 0,
                    percentage DECIMAL(5,2) NOT NULL DEFAULT 0.00,
                    avg_packet_size DECIMAL(10,2) NOT NULL DEFAULT 0.00,
                    formatted_bytes VARCHAR(50) DEFAULT '0 B',
                    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
                    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    
                    CONSTRAINT valid_time_window CHECK (time_window IN ('1h', '6h', '12h', '24h', '48h')),
                    CONSTRAINT positive_values CHECK (packet_count >= 0 AND byte_count >= 0 AND session_count >= 0 AND percentage >= 0),
                    CONSTRAINT unique_protocol_analysis UNIQUE (experiment_id, device_id, protocol, time_window)
                );
                
                CREATE INDEX IF NOT EXISTS idx_protocol_analysis_device_time 
                    ON protocol_analysis(device_id, time_window);
                CREATE INDEX IF NOT EXISTS idx_protocol_analysis_experiment 
                    ON protocol_analysis(experiment_id, device_id);
                CREATE INDEX IF NOT EXISTS idx_protocol_analysis_protocol 
                    ON protocol_analysis(protocol);
            """,
            
            'port_analysis': """
                CREATE TABLE IF NOT EXISTS port_analysis (
                    id BIGSERIAL PRIMARY KEY,
                    device_id UUID NOT NULL,
                    experiment_id VARCHAR(50) NOT NULL,
                    time_window VARCHAR(10) NOT NULL DEFAULT '1h',
                    port_number INTEGER NOT NULL,
                    port_type VARCHAR(20) DEFAULT 'unknown',
                    protocol VARCHAR(20) NOT NULL,
                    packet_count BIGINT NOT NULL DEFAULT 0,
                    byte_count BIGINT NOT NULL DEFAULT 0,
                    session_count INTEGER NOT NULL DEFAULT 0,
                    usage_percentage DECIMAL(5,2) NOT NULL DEFAULT 0.00,
                    status VARCHAR(20) DEFAULT 'active',
                    service VARCHAR(50) DEFAULT 'Unknown',
                    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
                    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    
                    CONSTRAINT valid_time_window CHECK (time_window IN ('1h', '6h', '12h', '24h', '48h')),
                    CONSTRAINT valid_port CHECK (port_number >= 0 AND port_number <= 65535),
                    CONSTRAINT valid_port_type CHECK (port_type IN ('system', 'user', 'dynamic', 'unknown')),
                    CONSTRAINT valid_status CHECK (status IN ('open', 'closed', 'filtered', 'active', 'inactive', 'blocked')),
                    CONSTRAINT positive_values CHECK (packet_count >= 0 AND byte_count >= 0 AND session_count >= 0 AND usage_percentage >= 0),
                    CONSTRAINT unique_port_analysis UNIQUE (experiment_id, device_id, port_number, protocol, time_window)
                );
                
                CREATE INDEX IF NOT EXISTS idx_port_analysis_device_time 
                    ON port_analysis(device_id, time_window);
                CREATE INDEX IF NOT EXISTS idx_port_analysis_experiment 
                    ON port_analysis(experiment_id, device_id);
                CREATE INDEX IF NOT EXISTS idx_port_analysis_port 
                    ON port_analysis(port_number);
            """
        }
        
        # Create all tables
        for table_name, create_sql in table_definitions.items():
            try:
                await self.db_manager.execute_command(create_sql)
                logger.info(f"Ensured table exists: {table_name}")
            except Exception as e:
                logger.error(f"Failed to create table {table_name}: {e}")
                raise
    
    async def analyze_experiment_data(self, experiment_id: str) -> Dict[str, Any]:
        """
        Main entry point for experiment data analysis
        (Wrapper method for compatibility with ModularDataAnalyzer)
        """
        return await self.analyze_experiment(experiment_id)

    async def analyze_experiment(self, experiment_id: str) -> Dict[str, Any]:
        """Analyze all devices in an experiment"""
        
        try:
            # Get all devices in the experiment
            devices_query = """
            SELECT device_id, device_name, manufacturer, mac_address
            FROM devices 
            WHERE experiment_id = $1
            ORDER BY device_name
            """
            devices = await self.db_manager.execute_query(devices_query, (experiment_id,))
            
            if not devices:
                logger.warning(f"No devices found for experiment: {experiment_id}")
                return {"status": "no_devices", "experiment_id": experiment_id}

            # Use device resolution service to get correct device names
            from database.services.device_resolution_service import ConfigurableDeviceResolutionService
            resolution_service = ConfigurableDeviceResolutionService(self.db_manager)
            
            # Batch resolve all device MAC addresses
            mac_addresses = [device['mac_address'] for device in devices if device['mac_address']]
            device_resolutions = await resolution_service.bulk_resolve_devices(mac_addresses)
            
            analysis_results = []
            successful_analyses = 0
            
            # Analyze each device
            for device in devices:
                device_id = device['device_id']
                mac_address = device['mac_address']
                
                # Get resolved device information
                resolved_info = device_resolutions.get(mac_address, {})
                resolved_name = resolved_info.get('resolvedName', device['device_name'])
                resolved_vendor = resolved_info.get('resolvedVendor', device['manufacturer'] or 'Unknown')
                
                logger.info(f"Analyzing device: {resolved_name} ({device_id})")
                
                try:
                    device_analysis = await self._analyze_device_comprehensive(
                        device_id, experiment_id, resolved_name, resolved_vendor
                    )
                    
                    if device_analysis.get('status') != 'no_data':
                        analysis_results.append({
                            'device_id': device_id,
                            'device_name': resolved_name,
                            'manufacturer': resolved_vendor,
                            'analysis': device_analysis
                        })
                        successful_analyses += 1
                        logger.info(f"Successfully analyzed device: {resolved_name}")
                    else:
                        logger.warning(f"No data found for device: {resolved_name}")
                        
                except Exception as device_error:
                    logger.error(f"Failed to analyze device {resolved_name}: {device_error}")
                    continue
                
            logger.info(f"Experiment analysis completed: {successful_analyses}/{len(devices)} devices analyzed successfully")
            
            return {
                "status": "success",
                "experiment_id": experiment_id,
                "total_devices": len(devices),
                "analyzed_devices": successful_analyses,
                "failed_devices": len(devices) - successful_analyses,
                "results": analysis_results
            }
            
        except Exception as e:
            logger.error(f"Experiment analysis failed for {experiment_id}: {e}")
            raise
    
    async def _analyze_device_comprehensive(self, device_id: str, experiment_id: str, 
                                         device_name: str, manufacturer: str) -> Dict[str, Any]:
        """Perform comprehensive analysis on the device and generate all analysis table data"""
        
        # Get packet flows for the device
        flows_query = """
        SELECT 
            packet_timestamp,
            protocol,
            packet_size,
            src_port,
            dst_port,
            src_ip,
            dst_ip
        FROM packet_flows 
        WHERE device_id = $1 AND experiment_id = $2
        ORDER BY packet_timestamp
        """
        flows = await self.db_manager.execute_query(flows_query, (device_id, experiment_id))
        
        if not flows:
            logger.warning(f"No packet flows found for device {device_name}")
            return {"status": "no_data"}
        
        # Generate various analysis data
        results = {}
        
        # 1. Generate activity timeline data
        activity_data = await self._generate_activity_timeline(device_id, experiment_id, flows)
        results['activity_timeline'] = activity_data
        
        # 2. Generate traffic trends data  
        traffic_data = await self._generate_traffic_trends(device_id, experiment_id, flows)
        results['traffic_trends'] = traffic_data
        
        # 3. Generate network topology data
        topology_data = await self._generate_network_topology(device_id, experiment_id, flows)
        results['network_topology'] = topology_data
        
        # 4. Generate protocol analysis data
        protocol_data = await self._generate_protocol_analysis(device_id, experiment_id, flows)
        results['protocol_analysis'] = protocol_data
        
        # 5. Generate port analysis data
        port_data = await self._generate_port_analysis(device_id, experiment_id, flows)
        results['port_analysis'] = port_data
        
        return results
    
    async def _generate_activity_timeline(self, device_id: str, experiment_id: str, flows: List[Dict]) -> Dict[str, int]:
        """Generate device activity timeline data"""
        
        # Aggregate activity data by hour
        hourly_data = {}
        
        for flow in flows:
            timestamp = flow['packet_timestamp']
            hour = timestamp.hour
            packet_size = flow['packet_size'] or 0
            
            if hour not in hourly_data:
                hourly_data[hour] = {
                    'packets': 0,
                    'bytes': 0,
                    'sessions': set()
                }
            
            hourly_data[hour]['packets'] += 1
            hourly_data[hour]['bytes'] += packet_size
            
            # Use src_ip:dst_ip:protocol as session identifier
            session_key = f"{flow['src_ip']}:{flow['dst_ip']}:{flow['protocol']}"
            hourly_data[hour]['sessions'].add(session_key)
        
        # Insert into database
        insert_count = 0
        for hour, data in hourly_data.items():
            # Use current day's timestamp
            base_time = flows[0]['packet_timestamp'].replace(hour=hour, minute=0, second=0, microsecond=0)
            
            insert_query = """
            INSERT INTO device_activity_timeline 
            (device_id, experiment_id, timestamp, time_window, hour, minute, 
             activity_level, packets, bytes, sessions, pattern)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ON CONFLICT (device_id, experiment_id, time_window, timestamp)
            DO UPDATE SET
                packets = EXCLUDED.packets,
                bytes = EXCLUDED.bytes,
                sessions = EXCLUDED.sessions,
                activity_level = EXCLUDED.activity_level,
                pattern = EXCLUDED.pattern,
                experiment_id = EXCLUDED.experiment_id,
                hour = EXCLUDED.hour,
                minute = EXCLUDED.minute,
                created_at = CURRENT_TIMESTAMP
            """
            
            # Calculate comprehensive activity level using real data metrics
            packets_count = data['packets']
            bytes_count = data['bytes']  
            sessions_count = len(data['sessions'])
            
            # Multi-dimensional activity level calculation
            # Normalize each component to 0-1 scale then combine
            packet_component = min(1.0, packets_count / 1000.0)  # 1000 packets = full score
            bytes_component = min(1.0, bytes_count / (1024 * 1024))  # 1MB = full score
            session_component = min(1.0, sessions_count / 50.0)  # 50 sessions = full score
            
            # Weighted combination (packets 40%, bytes 40%, sessions 20%)
            activity_level = (packet_component * 0.4 + bytes_component * 0.4 + session_component * 0.2) * 100.0
            activity_level = min(100.0, max(0.0, activity_level))
            
            # Improved pattern classification based on comprehensive metrics
            if activity_level >= 80:
                pattern = 'peak'
            elif activity_level >= 50:
                pattern = 'business'  # 修复：使用数据库允许的pattern值
            elif activity_level >= 20:
                pattern = 'normal'
            else:
                pattern = 'low'
            
            try:
                await self.db_manager.execute_command(insert_query, (
                    device_id, experiment_id, base_time, '1h', hour, 0,
                    activity_level, data['packets'], data['bytes'], 
                    len(data['sessions']), pattern
                ))
                insert_count += 1
            except Exception as e:
                logger.warning(f"Failed to insert activity timeline data: {e}")
        
        return {"inserted_records": insert_count}
    
    async def _generate_traffic_trends(self, device_id: str, experiment_id: str, flows: List[Dict]) -> Dict[str, int]:
        """Generate traffic trends data"""
        
        # Aggregate data by protocol
        protocol_data = {}
        
        for flow in flows:
            protocol = flow['protocol']
            packet_size = flow['packet_size'] or 0
            
            if protocol not in protocol_data:
                protocol_data[protocol] = {
                    'packets': 0,
                    'bytes': 0,
                    'sessions': set(),
                    'timestamp': flow['packet_timestamp']
                }
            
            protocol_data[protocol]['packets'] += 1
            protocol_data[protocol]['bytes'] += packet_size
            
            session_key = f"{flow['src_ip']}:{flow['dst_ip']}"
            protocol_data[protocol]['sessions'].add(session_key)
        
        # Insert into database
        insert_count = 0
        for protocol, data in protocol_data.items():
            insert_query = """
            INSERT INTO device_traffic_trend 
            (device_id, experiment_id, timestamp, time_window, packets, bytes, 
             sessions, protocol_data, pattern)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (device_id, experiment_id, time_window, timestamp)
            DO UPDATE SET
                packets = EXCLUDED.packets,
                bytes = EXCLUDED.bytes,
                sessions = EXCLUDED.sessions,
                protocol_data = EXCLUDED.protocol_data,
                pattern = EXCLUDED.pattern,
                experiment_id = EXCLUDED.experiment_id,
                created_at = CURRENT_TIMESTAMP
            """
            
            protocol_json = {
                'protocol': protocol,
                'packets': data['packets'],
                'bytes': data['bytes'],
                'sessions': len(data['sessions'])
            }
            
            # Comprehensive pattern classification for traffic trends
            packets_count = data['packets']
            bytes_count = data['bytes']
            sessions_count = len(data['sessions'])
            
            # Calculate traffic intensity score
            packet_score = min(1.0, packets_count / 500.0)  # 500 packets threshold
            bytes_score = min(1.0, bytes_count / (512 * 1024))  # 512KB threshold  
            session_score = min(1.0, sessions_count / 25.0)  # 25 sessions threshold
            
            # Combined intensity with weights
            intensity_score = (packet_score * 0.5 + bytes_score * 0.3 + session_score * 0.2)
            
            # Pattern classification based on intensity
            if intensity_score >= 0.8:
                pattern = 'peak'
            elif intensity_score >= 0.6:
                pattern = 'business'  # 修复：使用数据库允许的pattern值
            elif intensity_score >= 0.3:
                pattern = 'normal'
            elif intensity_score >= 0.1:
                pattern = 'low'
            else:
                pattern = 'idle'
            
            try:
                await self.db_manager.execute_command(insert_query, (
                    device_id, experiment_id, data['timestamp'], '1h',
                    data['packets'], data['bytes'], len(data['sessions']),
                    json.dumps(protocol_json), pattern
                ))
                insert_count += 1
            except Exception as e:
                logger.warning(f"Failed to insert traffic trend data: {e}")
        
        return {"inserted_records": insert_count}
    
    async def _generate_network_topology(self, device_id: str, experiment_id: str, flows: List[Dict]) -> Dict[str, int]:
        """Generate network topology data"""
        
        # Collect all connection information
        connections = {}
        
        for flow in flows:
            src_ip = str(flow['src_ip'])
            dst_ip = str(flow['dst_ip'])
            protocol = flow['protocol']
            
            connection_key = f"{src_ip}->{dst_ip}"
            
            if connection_key not in connections:
                connections[connection_key] = {
                    'src_ip': src_ip,
                    'dst_ip': dst_ip,
                    'protocols': set(),
                    'packets': 0,
                    'bytes': 0
                }
            
            connections[connection_key]['protocols'].add(protocol)
            connections[connection_key]['packets'] += 1
            connections[connection_key]['bytes'] += flow['packet_size'] or 0
        
        # Build topology data
        topology_data = {
            'connections': [],
            'total_connections': len(connections),
            'unique_ips': set()
        }
        
        for conn_key, conn_data in connections.items():
            topology_data['connections'].append({
                'source': conn_data['src_ip'],
                'target': conn_data['dst_ip'],
                'protocols': list(conn_data['protocols']),
                'packets': conn_data['packets'],
                'bytes': conn_data['bytes']
            })
            
            topology_data['unique_ips'].add(conn_data['src_ip'])
            topology_data['unique_ips'].add(conn_data['dst_ip'])
        
        topology_data['unique_ips'] = len(topology_data['unique_ips'])
        
        # Insert into database
        insert_query = """
        INSERT INTO device_topology 
        (device_id, experiment_id, time_window, topology_data)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (device_id, experiment_id, time_window)
        DO UPDATE SET
            topology_data = EXCLUDED.topology_data,
            experiment_id = EXCLUDED.experiment_id,
            created_at = CURRENT_TIMESTAMP
        """
        
        try:
            await self.db_manager.execute_command(insert_query, (
                device_id, experiment_id, '1h', json.dumps(topology_data)
            ))
            return {"inserted_records": 1, "connections": len(connections)}
        except Exception as e:
            logger.warning(f"Failed to insert topology data: {e}")
            return {"inserted_records": 0}
    
    async def _generate_protocol_analysis(self, device_id: str, experiment_id: str, flows: List[Dict]) -> Dict[str, int]:
        """Generate protocol analysis data"""
        
        # Aggregate protocol data
        protocol_stats = {}
        total_packets = len(flows)
        total_bytes = sum(flow['packet_size'] or 0 for flow in flows)
        
        for flow in flows:
            protocol = flow['protocol']
            packet_size = flow['packet_size'] or 0
            
            if protocol not in protocol_stats:
                protocol_stats[protocol] = {
                    'packets': 0,
                    'bytes': 0,
                    'sessions': set(),
                    'start_time': flow['packet_timestamp'],
                    'end_time': flow['packet_timestamp']
                }
            
            protocol_stats[protocol]['packets'] += 1
            protocol_stats[protocol]['bytes'] += packet_size
            
            if flow['packet_timestamp'] < protocol_stats[protocol]['start_time']:
                protocol_stats[protocol]['start_time'] = flow['packet_timestamp']
            if flow['packet_timestamp'] > protocol_stats[protocol]['end_time']:
                protocol_stats[protocol]['end_time'] = flow['packet_timestamp']
            
            session_key = f"{flow['src_ip']}:{flow['dst_ip']}"
            protocol_stats[protocol]['sessions'].add(session_key)
        
        # Insert into database
        insert_count = 0
        for protocol, stats in protocol_stats.items():
            percentage = (stats['packets'] / total_packets) * 100 if total_packets > 0 else 0
            avg_packet_size = stats['bytes'] / stats['packets'] if stats['packets'] > 0 else 0
            formatted_bytes = f"{stats['bytes']} B"
            
            insert_query = """
            INSERT INTO protocol_analysis 
            (device_id, experiment_id, time_window, protocol, packet_count, byte_count,
             session_count, percentage, avg_packet_size, formatted_bytes, start_time, end_time)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            ON CONFLICT (experiment_id, device_id, protocol, time_window)
            DO UPDATE SET
                packet_count = EXCLUDED.packet_count,
                byte_count = EXCLUDED.byte_count,
                session_count = EXCLUDED.session_count,
                percentage = EXCLUDED.percentage,
                avg_packet_size = EXCLUDED.avg_packet_size,
                formatted_bytes = EXCLUDED.formatted_bytes,
                end_time = EXCLUDED.end_time,
                start_time = EXCLUDED.start_time,
                updated_at = CURRENT_TIMESTAMP
            """
            
            try:
                await self.db_manager.execute_command(insert_query, (
                    device_id, experiment_id, '1h', protocol, stats['packets'], stats['bytes'],
                    len(stats['sessions']), percentage, avg_packet_size, formatted_bytes,
                    stats['start_time'], stats['end_time']
                ))
                insert_count += 1
            except Exception as e:
                logger.warning(f"Failed to insert protocol analysis data: {e}")
        
        return {"inserted_records": insert_count}
    
    async def _generate_port_analysis(self, device_id: str, experiment_id: str, flows: List[Dict]) -> Dict[str, int]:
        """Generate port analysis data"""
        
        # Aggregate port data
        port_stats = {}
        total_packets = len(flows)
        
        for flow in flows:
            src_port = flow['src_port']
            dst_port = flow['dst_port'] 
            protocol = flow['protocol']
            packet_size = flow['packet_size'] or 0
            
            # Analyze source and destination ports
            for port_num, port_type in [(src_port, 'source'), (dst_port, 'destination')]:
                if port_num is None:
                    continue
                    
                port_key = f"{port_num}_{protocol}"
                
                if port_key not in port_stats:
                    port_stats[port_key] = {
                        'port_number': port_num,
                        'protocol': protocol,
                        'packets': 0,
                        'bytes': 0,
                        'sessions': set(),
                        'start_time': flow['packet_timestamp'],
                        'end_time': flow['packet_timestamp']
                    }
                
                port_stats[port_key]['packets'] += 1
                port_stats[port_key]['bytes'] += packet_size
                
                if flow['packet_timestamp'] < port_stats[port_key]['start_time']:
                    port_stats[port_key]['start_time'] = flow['packet_timestamp']
                if flow['packet_timestamp'] > port_stats[port_key]['end_time']:
                    port_stats[port_key]['end_time'] = flow['packet_timestamp']
                
                session_key = f"{flow['src_ip']}:{flow['dst_ip']}"
                port_stats[port_key]['sessions'].add(session_key)
        
        # Insert into database
        insert_count = 0
        for port_key, stats in port_stats.items():
            port_number = stats['port_number']
            usage_percentage = (stats['packets'] / total_packets) * 100 if total_packets > 0 else 0
            
            # Determine port type
            if port_number < 1024:
                port_type = 'system'
            elif port_number < 49152:
                port_type = 'user'
            else:
                port_type = 'dynamic'
            
            # Determine service type
            service = 'Unknown'
            if port_number == 80:
                service = 'HTTP'
            elif port_number == 443:
                service = 'HTTPS'
            elif port_number == 53:
                service = 'DNS'
            elif port_number == 22:
                service = 'SSH'
            
            insert_query = """
            INSERT INTO port_analysis 
            (device_id, experiment_id, time_window, port_number, port_type, protocol,
             packet_count, byte_count, session_count, usage_percentage, status, service,
             start_time, end_time)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            ON CONFLICT (experiment_id, device_id, port_number, protocol, time_window)
            DO UPDATE SET
                packet_count = EXCLUDED.packet_count,
                byte_count = EXCLUDED.byte_count,
                session_count = EXCLUDED.session_count,
                usage_percentage = EXCLUDED.usage_percentage,
                port_type = EXCLUDED.port_type,
                status = EXCLUDED.status,
                service = EXCLUDED.service,
                end_time = EXCLUDED.end_time,
                start_time = EXCLUDED.start_time,
                updated_at = CURRENT_TIMESTAMP
            """
            
            try:
                await self.db_manager.execute_command(insert_query, (
                    device_id, experiment_id, '1h', port_number, port_type, stats['protocol'],
                    stats['packets'], stats['bytes'], len(stats['sessions']),
                    usage_percentage, 'active', service, stats['start_time'], stats['end_time']
                ))
                insert_count += 1
            except Exception as e:
                logger.warning(f"Failed to insert port analysis data: {e}")
        
        return {"inserted_records": insert_count}
    
    async def _generate_experiment_aggregates(self, experiment_id: str, devices: List[Dict], 
                                            analysis_results: List[Dict]) -> Dict[str, Any]:
        """Generate experiment-level aggregates"""
        
        # Calculate experiment-level statistics
        total_devices = len(devices)
        successful_devices = len([r for r in analysis_results if r.get('status') == 'success'])
        
        # Get packet flow statistics
        flows_query = """
        SELECT COUNT(*) as total_flows, SUM(packet_size) as total_bytes
        FROM packet_flows
        WHERE experiment_id = $1
        """
        flows_stats = await self.db_manager.execute_query(flows_query, (experiment_id,))
        total_flows = flows_stats[0]['total_flows'] if flows_stats else 0
        total_bytes = flows_stats[0]['total_bytes'] if flows_stats else 0
        
        return {
            "experiment_id": experiment_id,
            "total_devices": total_devices,
            "successful_analyses": successful_devices,
            "failed_analyses": total_devices - successful_devices,
            "total_packet_flows": total_flows,
            "total_bytes": total_bytes or 0,
            "analysis_completion_rate": (successful_devices / total_devices) * 100 if total_devices > 0 else 0
        }
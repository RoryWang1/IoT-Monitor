"""
Packet Storage

Focused storage layer for packet flows data with clean interface.
"""

import logging
import uuid
import sys
from typing import List, Dict, Any, Optional
from pathlib import Path

# Add project root to path for database imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from database.connection import PostgreSQLDatabaseManager

# Use absolute imports for internal modules
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

from pcap_process.models.packet_data import PacketFlow
from pcap_process.analyzers.modular_data_analyzer import ModularDataAnalyzer

logger = logging.getLogger(__name__)


class PacketStorage:
    """
    Storage layer for packet flows
    
    Responsibilities:
    - Store packet flows in database
    - Handle device registration  
    - Manage batch operations
    - Ensure data consistency
    """
    
    def __init__(self, db_manager: PostgreSQLDatabaseManager):
        """Initialize packet storage"""
        self.db_manager = db_manager
        self.device_cache = {}  # Cache device IDs to avoid repeated lookups
        self.experiment_cache = set()  # Cache created experiments
        self.data_analyzer = ModularDataAnalyzer(db_manager)  # Initialize modular data analyzer
        self.analyzed_devices = set()  # Track which devices have been analyzed
        logger.info("Packet Storage with integrated analysis initialized")
    
    async def initialize(self):
        """Initialize storage components"""
        try:
            # Verify required tables exist
            await self._verify_tables()
            logger.info("Storage initialization completed")
        except Exception as e:
            logger.error(f"Storage initialization failed: {e}")
            raise
    
    async def store_packet_flows(self, packet_flows: List[PacketFlow], 
                                experiment_id: str, device_mac: str) -> Dict[str, Any]:
        """
        Store packet flows in the database
        
        Args:
            packet_flows: List of packet flow objects
            experiment_id: Experiment identifier (VARCHAR)
            device_mac: Device MAC address
            
        Returns:
            Storage results
        """
        if not packet_flows:
            return {'stored_count': 0, 'message': 'No packets to store'}
        
        logger.info(f"Storing {len(packet_flows)} packet flows for device {device_mac}")
        
        try:
            # Ensure experiment exists FIRST
            await self._ensure_experiment_exists(experiment_id)
            
            # Then ensure device exists
            device_id = await self._get_or_create_device(device_mac, experiment_id)
            
            # Store packet flows
            stored_count = await self._batch_store_flows(packet_flows, device_id, experiment_id)
            
            logger.info(f"Stored {stored_count} packet flows successfully")
            
            # Update device IP address and traffic information
            await self._update_device_info(device_id, experiment_id, packet_flows)
            
            # Trigger data analysis immediately after storage
            await self._trigger_device_analysis(device_id, experiment_id, device_mac)
            
            return {
                'stored_count': stored_count,
                'device_id': device_id,
                'experiment_id': experiment_id,
                'analysis_triggered': True
            }
            
        except Exception as e:
            logger.error(f"Error storing packet flows: {e}")
            raise
    
    async def _ensure_experiment_exists(self, experiment_id: str):
        """Ensure experiment record exists"""
        if experiment_id in self.experiment_cache:
            return
        
        try:
            check_query = "SELECT experiment_id FROM experiments WHERE experiment_id = $1"
            result = await self.db_manager.execute_query(check_query, (experiment_id,))
            
            if not result:
                # Create experiment record
                insert_query = """
                INSERT INTO experiments (experiment_id, experiment_name, status, start_date)
                VALUES ($1, $2, 'active', NOW())
                ON CONFLICT (experiment_id) DO NOTHING
                """
                await self.db_manager.execute_command(
                    insert_query, (experiment_id, f"Experiment {experiment_id}")
                )
                logger.info(f"Created experiment record: {experiment_id}")
            
            # Cache the experiment
            self.experiment_cache.add(experiment_id)
            
        except Exception as e:
            logger.error(f"Error ensuring experiment exists: {e}")
            raise
    
    async def _get_or_create_device(self, device_mac: str, experiment_id: str) -> str:
        """Get existing device or create new one with enhanced info and proper uniqueness within experiment"""
        
        # Check cache first
        cache_key = f"{device_mac}:{experiment_id}"
        if cache_key in self.device_cache:
            return self.device_cache[cache_key]
        
        try:
            # Check for duplicate devices only within the same experimentId
            # Different experimentId's with the same MAC address should be independent device records
            check_query = """
            SELECT device_id FROM devices 
            WHERE mac_address = $1 AND experiment_id = $2
            """
            
            result = await self.db_manager.execute_query(check_query, (device_mac, experiment_id))
            
            if result:
                device_id = str(result[0]['device_id'])
                self.device_cache[cache_key] = device_id
                logger.debug(f"Found existing device in experiment {experiment_id}: {device_mac} -> {device_id}")
                return device_id
            
            # Create new device if not found in this experiment
            device_id = str(uuid.uuid4())
            device_name = await self._extract_device_name_from_mac_async(device_mac)
            
            # Resolve additional device information
            manufacturer = await self._resolve_manufacturer(device_mac)
            
            insert_query = """
            INSERT INTO devices (
                device_id, device_name, mac_address, experiment_id, 
                manufacturer, device_type, status, created_at
            ) VALUES ($1, $2, $3, $4, $5, 'unknown', 'offline', NOW())
            ON CONFLICT (mac_address, experiment_id) DO UPDATE SET
                device_name = EXCLUDED.device_name,
                manufacturer = EXCLUDED.manufacturer,
                status = 'online'
            RETURNING device_id
            """
            
            result = await self.db_manager.execute_query(
                insert_query, 
                (device_id, device_name, device_mac, experiment_id, manufacturer)
            )
            
            if result:
                final_device_id = str(result[0]['device_id'])
                self.device_cache[cache_key] = final_device_id
                logger.info(f"Created new device in experiment {experiment_id}: {device_name} ({device_mac}) -> {final_device_id}")
                return final_device_id
            else:
                # If INSERT failed but no result, try to get existing device again
                check_again_query = """
                SELECT device_id FROM devices 
                WHERE mac_address = $1 AND experiment_id = $2
                """
                check_result = await self.db_manager.execute_query(check_again_query, (device_mac, experiment_id))
                
                if check_result:
                    existing_device_id = str(check_result[0]['device_id'])
                    self.device_cache[cache_key] = existing_device_id
                    logger.info(f"Found device after insert attempt: {device_mac} -> {existing_device_id}")
                    return existing_device_id
                else:
                    # Last resort: use the generated device_id
                    self.device_cache[cache_key] = device_id
                    logger.warning(f"Using generated device_id as fallback: {device_id}")
                    return device_id
                
        except Exception as e:
            logger.error(f"Error getting/creating device for MAC {device_mac} in experiment {experiment_id}: {e}")
            
            # Do not return random ID, but retry device creation
            try:
                # Last resort: force create device, ignore conflicts
                fallback_device_id = str(uuid.uuid4())
                fallback_name = await self._extract_device_name_from_mac_async(device_mac)
                fallback_manufacturer = await self._resolve_manufacturer(device_mac)
                
                force_insert_query = """
                INSERT INTO devices (
                    device_id, device_name, mac_address, experiment_id, 
                    manufacturer, device_type, status, created_at
                ) VALUES ($1, $2, $3, $4, $5, 'unknown', 'offline', NOW())
                ON CONFLICT (mac_address, experiment_id) DO NOTHING
                """
                
                await self.db_manager.execute_command(
                    force_insert_query, 
                    (fallback_device_id, fallback_name, device_mac, experiment_id, fallback_manufacturer)
                )
                
                # Check again to ensure device exists
                final_check_query = """
                SELECT device_id FROM devices 
                WHERE mac_address = $1 AND experiment_id = $2
                """
                final_result = await self.db_manager.execute_query(final_check_query, (device_mac, experiment_id))
                
                if final_result:
                    final_device_id = str(final_result[0]['device_id'])
                    self.device_cache[cache_key] = final_device_id
                    logger.info(f"Fallback device creation successful: {device_mac} -> {final_device_id}")
                    return final_device_id
                else:
                    raise RuntimeError(f"Failed to create or find device for MAC {device_mac} in experiment {experiment_id}")
                    
            except Exception as fallback_error:
                logger.error(f"Fallback device creation failed: {fallback_error}")
                raise RuntimeError(f"Complete failure to create device for MAC {device_mac} in experiment {experiment_id}")
    
    def _generate_device_name(self, mac_address: str) -> str:
        """Generate a more meaningful device name"""
        # Use last 6 characters of MAC (without colons) for uniqueness
        mac_suffix = mac_address.replace(':', '').upper()[-6:]
        manufacturer = self._get_manufacturer_from_mac(mac_address)
        
        if manufacturer and manufacturer != 'Unknown':
            return f"{manufacturer}_{mac_suffix}"
        else:
            return f"Device_{mac_suffix}"
    
    def _infer_initial_device_type(self, mac_address: str) -> str:
        """Infer initial device type from MAC address OUI"""
        manufacturer = self._get_manufacturer_from_mac(mac_address)
        
        # Device type inference based on manufacturer
        if 'D-Link' in manufacturer:
            return 'router'
        elif 'TP-Link' in manufacturer:
            return 'smart_device'
        elif 'Belkin' in manufacturer:
            return 'smart_device'
        elif 'Edimax' in manufacturer:
            return 'camera'
        elif 'Amazon' in manufacturer:
            return 'iot_device'
        elif 'Philips' in manufacturer:
            return 'smart_device'
        elif 'Samsung' in manufacturer:
            return 'smart_device'
        elif 'Apple' in manufacturer:
            return 'mobile_device'
        else:
            return 'unknown'
    
    async def _resolve_manufacturer(self, mac_address: str) -> str:
        """Use unified device resolution service to resolve manufacturer information"""
        try:
            if not mac_address or len(mac_address) < 8:
                return 'Unknown'
            
            # Use unified device resolution service
            from database.services.device_resolution_service import DeviceResolutionService
            resolution_service = DeviceResolutionService(self.db_manager)
            
            device_info = await resolution_service.resolve_device_info(mac_address, use_cache=True)
            vendor_name = device_info.get('resolved_vendor', 'Unknown')
            
            logger.debug(f"Resolved manufacturer for {mac_address}: {vendor_name} (source: {device_info.get('source', 'unknown')})")
            return vendor_name
                
        except Exception as e:
            logger.error(f"Error resolving manufacturer for {mac_address}: {e}")
            return 'Unknown'

    def _get_manufacturer_from_mac(self, mac_address: str) -> str:
        """Use asynchronous database query for backward compatibility"""
        # This method is kept for backward compatibility, but now only does basic validation
        if not mac_address or len(mac_address) < 8:
            return 'Unknown'
        
        # For synchronous calls, we cannot query the database, return Unknown
        # Real manufacturer resolution should use the asynchronous _resolve_manufacturer method
        logger.debug(f"Sync manufacturer lookup for {mac_address} - returning Unknown (use async _resolve_manufacturer instead)")
        return 'Unknown'
    
    async def _batch_store_flows(self, packet_flows: List[PacketFlow], 
                                device_id: str, experiment_id: str) -> int:
        """
        Store packet flows in batches with enhanced duplicate prevention
        
        Enhanced: Use device-perspective deduplication to prevent duplicate communications
        """
        
        # Use ON CONFLICT to handle duplicate records
        insert_query = """
        INSERT INTO packet_flows (
            device_id, experiment_id, packet_timestamp, src_ip, dst_ip,
            src_port, dst_port, protocol, packet_size, flow_direction,
            flow_hash, tcp_flags, payload_size, src_mac, dst_mac, app_protocol
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
        ON CONFLICT (device_id, packet_timestamp, src_ip, dst_ip, src_port, dst_port, protocol, flow_direction)
        DO NOTHING
        """
        
        stored_count = 0
        duplicate_count = 0
        batch_size = 100
        
        for i in range(0, len(packet_flows), batch_size):
            batch = packet_flows[i:i + batch_size]
            
            try:
                for flow in batch:
                    flow_data = flow.to_dict()
                    
                    # Execute insert, duplicate records will be automatically ignored
                    result = await self.db_manager.execute_command(insert_query, (
                        device_id,
                        experiment_id,  # This is now a VARCHAR, not UUID
                        flow_data['packet_timestamp'],
                        flow_data['src_ip'],
                        flow_data['dst_ip'],
                        flow_data['src_port'],
                        flow_data['dst_port'],
                        flow_data['protocol'],
                        flow_data['packet_size'],
                        flow_data['flow_direction'],
                        flow_data['flow_hash'],
                        flow_data['tcp_flags'],
                        flow_data['payload_size'],
                        flow_data['src_mac'],
                        flow_data['dst_mac'],
                        flow_data['app_protocol']
                    ))
                    
                    # Check if records were actually inserted (if result supports it)
                    if result is None or (hasattr(result, 'rowcount') and result.rowcount > 0):
                        stored_count += 1
                    else:
                        duplicate_count += 1
                
                logger.debug(f"Stored batch of {len(batch)} flows (stored: {stored_count}, duplicates: {duplicate_count})")
                
            except Exception as e:
                logger.error(f"Error storing batch: {e}")
                # Continue with next batch
                continue
        
        if duplicate_count > 0:
            logger.info(f"Stored {stored_count} new flows, skipped {duplicate_count} duplicates for device {device_id}")
        
        return stored_count
    
    async def _update_device_info(self, device_id: str, experiment_id: str, packet_flows: List[PacketFlow]):
        """Update device IP address and traffic information"""
        try:
            if not packet_flows:
                return
            
            # Extract device IP addresses from packet flows
            device_ips = {}
            total_bytes = 0
            
            for flow in packet_flows:
                total_bytes += flow.packet_size
                
                # Collect source IP addresses (device outbound traffic)
                if flow.flow_direction == 'outbound' and flow.src_ip:
                    device_ips[flow.src_ip] = device_ips.get(flow.src_ip, 0) + 1
                # Collect destination IP addresses (device inbound traffic)
                elif flow.flow_direction == 'inbound' and flow.dst_ip:
                    device_ips[flow.dst_ip] = device_ips.get(flow.dst_ip, 0) + 1
            
            # Select most frequent IP as device IP
            device_ip = None
            if device_ips:
                # Filter out broadcast and multicast addresses
                valid_ips = {
                    ip: count for ip, count in device_ips.items() 
                    if ip and not ip.endswith('.255') and not ip.startswith('224.')
                    and not ip.startswith('239.') and ip != '0.0.0.0'
                }
                
                if valid_ips:
                    device_ip = max(valid_ips.items(), key=lambda x: x[1])[0]
            
            # Update device information
            if device_ip:
                update_query = """
                UPDATE devices 
                SET ip_address = $1, 
                    last_seen = NOW(),
                    updated_at = NOW()
                WHERE device_id = $2 AND experiment_id = $3
                """
                await self.db_manager.execute_command(update_query, (device_ip, device_id, experiment_id))
                logger.info(f"Updated device {device_id} IP address: {device_ip}")
            
        except Exception as e:
            logger.error(f"Error updating device info: {e}")
    
    async def _trigger_device_analysis(self, device_id: str, experiment_id: str, device_mac: str):
        """
        Trigger data analysis for a device
        
        Args:
            device_id: Device UUID
            experiment_id: Experiment identifier  
            device_mac: Device MAC address
        """
        analysis_key = f"{experiment_id}:{device_id}"
        
        # Check if analysis data already exists (based on database, not memory cache)
        try:
            check_analysis_query = """
            SELECT COUNT(*) as count FROM device_activity_timeline 
            WHERE device_id = $1 AND experiment_id = $2
            """
            result = await self.db_manager.execute_query(check_analysis_query, (device_id, experiment_id))
            
            if result and result[0]['count'] > 0:
                logger.debug(f"Device {device_mac} already has analysis data for experiment {experiment_id}")
                return
                
        except Exception as e:
            logger.warning(f"Failed to check existing analysis data: {e}")
        
        # Avoid duplicate analysis for the same device in the same experiment (memory deduplication)
        if analysis_key in self.analyzed_devices:
            logger.debug(f"Device {device_mac} analysis already in progress for experiment {experiment_id}")
            return

        try:
            logger.info(f"Triggering comprehensive analysis for device {device_mac} in experiment {experiment_id}")
            
            # Mark as being analyzed (to prevent duplicate calls)
            self.analyzed_devices.add(analysis_key)
            
            # Run complete data analysis with experiment isolation
            analysis_result = await self.data_analyzer.analyze_experiment_data(experiment_id)
            
            logger.info(f"Analysis completed for device {device_mac}: {analysis_result.get('devices_analyzed', 0)} devices analyzed")
            
            # Broadcast device detail updates after successful analysis
            await self._broadcast_device_updates(device_id, experiment_id)
            
        except Exception as e:
            logger.error(f"Error during data analysis for device {device_mac} in experiment {experiment_id}: {e}")
            # Clear the mark when analysis fails, allowing retry
            self.analyzed_devices.discard(analysis_key)
    
    async def _verify_tables(self):
        """Verify required database tables exist"""
        required_tables = ['experiments', 'devices', 'packet_flows']
        
        for table in required_tables:
            check_query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = $1
            )
            """
            
            result = await self.db_manager.execute_query(check_query, (table,))
            
            if not result or not result[0]['exists']:
                raise RuntimeError(f"Required table '{table}' does not exist")
        
        logger.debug("All required tables verified")
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        try:
            stats_query = """
            SELECT 
                COUNT(*) as total_flows,
                COUNT(DISTINCT device_id) as unique_devices,
                COUNT(DISTINCT experiment_id) as unique_experiments,
                MIN(packet_timestamp) as earliest_packet,
                MAX(packet_timestamp) as latest_packet
            FROM packet_flows
            """
            
            result = await self.db_manager.execute_query(stats_query)
            
            if result:
                return {
                    'total_packet_flows': result[0]['total_flows'],
                    'unique_devices': result[0]['unique_devices'],
                    'unique_experiments': result[0]['unique_experiments'],
                    'earliest_packet': result[0]['earliest_packet'],
                    'latest_packet': result[0]['latest_packet'],
                    'cached_devices': len(self.device_cache),
                    'cached_experiments': len(self.experiment_cache)
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return {'error': str(e)}
    
    async def analyze_data_quality(self, experiment_id: str = None) -> Dict[str, Any]:
        """
        Analyze data quality and deduplication effectiveness
        
        Analyze data quality in packet_flows table, detect potential duplicates and anomalies
        """
        try:
            base_conditions = ""
            query_params = []
            
            if experiment_id:
                base_conditions = "WHERE experiment_id = $1"
                query_params = [experiment_id]
            
            # 1. Basic statistics
            basic_stats_query = f"""
            SELECT 
                COUNT(*) as total_records,
                COUNT(DISTINCT flow_hash) as unique_flows,
                COUNT(DISTINCT CONCAT(src_ip, ':', dst_ip)) as unique_ip_pairs,
                COUNT(DISTINCT device_id) as unique_devices,
                COUNT(DISTINCT protocol) as unique_protocols,
                AVG(packet_size) as avg_packet_size,
                MIN(packet_timestamp) as earliest_timestamp,
                MAX(packet_timestamp) as latest_timestamp
            FROM packet_flows {base_conditions}
            """
            
            basic_stats = await self.db_manager.execute_query(basic_stats_query, query_params)
            
            # 2. Detect potential duplicates (same flow_hash but different records)
            duplicate_check_query = f"""
            SELECT 
                flow_hash,
                COUNT(*) as record_count,
                COUNT(DISTINCT device_id) as device_count,
                STRING_AGG(DISTINCT device_id::text, ', ') as device_ids
            FROM packet_flows {base_conditions}
            GROUP BY flow_hash
            HAVING COUNT(*) > 1
            ORDER BY record_count DESC
            LIMIT 10
            """
            
            duplicates = await self.db_manager.execute_query(duplicate_check_query, query_params)
            
            # 3. Analyze device perspective distribution
            device_perspective_query = f"""
            SELECT 
                device_id,
                COUNT(*) as total_flows,
                COUNT(CASE WHEN flow_direction = 'inbound' THEN 1 END) as inbound_flows,
                COUNT(CASE WHEN flow_direction = 'outbound' THEN 1 END) as outbound_flows,
                COUNT(DISTINCT flow_hash) as unique_flow_hashes
            FROM packet_flows {base_conditions}
            GROUP BY device_id
            ORDER BY total_flows DESC
            LIMIT 10
            """
            
            device_stats = await self.db_manager.execute_query(device_perspective_query, query_params)
            
            # 4. Protocol distribution
            protocol_distribution_query = f"""
            SELECT 
                protocol,
                COUNT(*) as flow_count,
                COUNT(DISTINCT device_id) as device_count,
                AVG(packet_size) as avg_size
            FROM packet_flows {base_conditions}
            GROUP BY protocol
            ORDER BY flow_count DESC
            """
            
            protocol_stats = await self.db_manager.execute_query(protocol_distribution_query, query_params)
            
            return {
                'basic_statistics': basic_stats[0] if basic_stats else {},
                'potential_duplicates': duplicates[:5],  # Limit return quantity
                'device_perspectives': device_stats[:5],
                'protocol_distribution': protocol_stats[:10],
                'data_quality_summary': {
                    'total_records': basic_stats[0]['total_records'] if basic_stats else 0,
                    'unique_flow_ratio': (basic_stats[0]['unique_flows'] / basic_stats[0]['total_records']) if basic_stats and basic_stats[0]['total_records'] > 0 else 0,
                    'duplicate_flows': len(duplicates),
                    'has_quality_issues': len(duplicates) > 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing data quality: {e}")
            return {'error': str(e)}
    
    def _extract_device_name_from_mac(self, mac_address: str) -> str:
        """Extract device name from MAC address (basic version)"""
        if not mac_address:
            return "Unknown_Device"
        
        # Use last 6 characters for uniqueness
        mac_suffix = mac_address.replace(':', '').upper()[-6:]
        return f"Device_{mac_suffix}"
    
    async def _extract_device_name_from_mac_async(self, mac_address: str) -> str:
        """Extract device name from MAC address using async manufacturer resolution"""
        if not mac_address:
            return "Unknown_Device"
        
        # Get manufacturer from database
        manufacturer = await self._resolve_manufacturer(mac_address)
        
        # Use last 6 characters for uniqueness
        mac_suffix = mac_address.replace(':', '').upper()[-6:]
        
        if manufacturer and manufacturer != 'Unknown':
            return f"{manufacturer}_{mac_suffix}"
        else:
            return f"Device_{mac_suffix}"
    
    async def _broadcast_device_updates(self, device_id: str, experiment_id: str):
        """Broadcast device detail updates to WebSocket clients"""
        try:
            # Import WebSocket manager
            from backend.api.websocket.manager_singleton import get_websocket_manager
            from backend.api.common.dependencies import get_database_service_instance
            
            # Get WebSocket manager instance
            websocket_manager = get_websocket_manager()
            
            # Get database service for fetching analysis data
            database_service = get_database_service_instance()
            if not database_service:
                logger.warning("Database service not available for broadcasting")
                return
            
            # Use default time window for analysis data
            time_window = "auto"
            
            # Get all device analysis data and broadcast each type
            tasks = []
            
            # Device detail
            try:
                device_detail = await database_service.get_device_detail(device_id, experiment_id)
                if device_detail:
                    serializable_data = self._serialize_datetime_objects(device_detail)
                    tasks.append(websocket_manager.broadcast_to_topic(
                        f"devices.{device_id}.detail", serializable_data
                    ))
            except Exception as e:
                logger.debug(f"Device detail broadcast failed: {e}")
            
            # Port analysis
            try:
                port_data = await database_service.get_device_port_analysis(device_id, experiment_id, time_window)
                if port_data:
                    serializable_data = self._serialize_datetime_objects(port_data)
                    tasks.append(websocket_manager.broadcast_to_topic(
                        f"devices.{device_id}.port-analysis", serializable_data
                    ))
            except Exception as e:
                logger.debug(f"Port analysis broadcast failed: {e}")
            
            # Protocol distribution
            try:
                protocol_data = await database_service.get_device_protocol_distribution(device_id, experiment_id, time_window)
                if protocol_data:
                    serializable_data = self._serialize_datetime_objects(protocol_data)
                    tasks.append(websocket_manager.broadcast_to_topic(
                        f"devices.{device_id}.protocol-distribution", serializable_data
                    ))
            except Exception as e:
                logger.debug(f"Protocol distribution broadcast failed: {e}")
            
            # Traffic trend
            try:
                traffic_data = await database_service.get_device_traffic_trend(device_id, experiment_id, time_window)
                if traffic_data:
                    serializable_data = self._serialize_datetime_objects(traffic_data)
                    tasks.append(websocket_manager.broadcast_to_topic(
                        f"devices.{device_id}.traffic-trend", serializable_data
                    ))
            except Exception as e:
                logger.debug(f"Traffic trend broadcast failed: {e}")
            
            # Network topology
            try:
                topology_data = await database_service.get_device_network_topology(device_id, experiment_id, time_window)
                if topology_data:
                    serializable_data = self._serialize_datetime_objects(topology_data)
                    tasks.append(websocket_manager.broadcast_to_topic(
                        f"devices.{device_id}.network-topology", serializable_data
                    ))
            except Exception as e:
                logger.debug(f"Network topology broadcast failed: {e}")
            
            # Activity timeline
            try:
                activity_data = await database_service.get_device_activity_timeline(device_id, experiment_id, time_window)
                if activity_data:
                    serializable_data = self._serialize_datetime_objects(activity_data)
                    tasks.append(websocket_manager.broadcast_to_topic(
                        f"devices.{device_id}.activity-timeline", serializable_data
                    ))
            except Exception as e:
                logger.debug(f"Activity timeline broadcast failed: {e}")
            
            # Execute all broadcasts concurrently
            if tasks:
                import asyncio
                await asyncio.gather(*tasks, return_exceptions=True)
                logger.info(f"Device analysis updates broadcasted for device {device_id}")
            
        except Exception as e:
            logger.warning(f"Failed to broadcast device updates: {e}")
    
    def _serialize_datetime_objects(self, data):
        """Serialize datetime objects to strings for JSON compatibility"""
        import json
        from datetime import datetime, date
        
        def default_serializer(obj):
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            elif hasattr(obj, 'isoformat'):
                return obj.isoformat()
            return str(obj)
        
        return json.loads(json.dumps(data, default=default_serializer))

    async def cleanup(self):
        """Cleanup storage resources"""
        self.device_cache.clear()
        self.experiment_cache.clear()
        self.analyzed_devices.clear()
        logger.info("Storage cleanup completed") 
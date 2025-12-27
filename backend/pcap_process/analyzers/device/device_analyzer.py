"""
Device data analyzer
Extracted device-level analysis logic from DataAnalyzer
"""

import logging
from typing import Dict, List, Any
from datetime import datetime, timezone
from .device_resolver import DeviceResolver

logger = logging.getLogger(__name__)


class DeviceAnalyzer:
    """Device-level data analyzer"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.device_resolver = DeviceResolver(db_manager)
        self.utc_timezone = timezone.utc
    
    async def analyze_device_data(self, device_id: str, experiment_id: str) -> Dict[str, Any]:
        """Analyze all data for a single device"""
        
        # Get packet flows
        packet_flows = await self._get_device_packet_flows(device_id)
        if not packet_flows:
            logger.warning(f"No packet flows found for device {device_id}")
            return {'packet_flows': 0}
        
        # Generate device statistics
        statistics = await self._generate_device_statistics(device_id, experiment_id, packet_flows)
        
        # Resolve device information
        device_info = await self.device_resolver.resolve_device_info(device_id, experiment_id)
        
        return {
            'device_id': device_id,
            'packet_flows': len(packet_flows),
            'statistics': statistics,
            'device_info': device_info,
            'analysis_timestamp': datetime.now(self.utc_timezone).isoformat()
        }
    
    async def _get_device_packet_flows(self, device_id: str) -> List[Dict[str, Any]]:
        """Get packet flows for the device"""
        query = """
        SELECT flow_id, packet_timestamp, src_ip, dst_ip, src_port, dst_port,
               protocol, packet_size, flow_direction
        FROM packet_flows
        WHERE device_id = $1
        ORDER BY packet_timestamp
        """
        return await self.db_manager.execute_query(query, (device_id,))
    
    async def _generate_device_statistics(self, device_id: str, experiment_id: str, 
                                        packet_flows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate device statistics"""
        if not packet_flows:
            return {
                'total_packets': 0,
                'total_bytes': 0,
                'unique_flows': 0,
                'protocols': {},
                'ports': {},
                'duration_seconds': 0
            }
        
        # Basic statistics
        total_packets = len(packet_flows)
        total_bytes = sum(flow.get('packet_size', 0) for flow in packet_flows)
        unique_flows = len(set(flow.get('flow_id') for flow in packet_flows if flow.get('flow_id')))
        
        # Protocol statistics
        protocols = {}
        for flow in packet_flows:
            protocol = flow.get('protocol', 'Unknown')
            protocols[protocol] = protocols.get(protocol, 0) + 1
        
        # Port statistics
        ports = {}
        for flow in packet_flows:
            for port_key in ['src_port', 'dst_port']:
                port = flow.get(port_key)
                if port:
                    ports[port] = ports.get(port, 0) + 1
        
        # Time span
        timestamps = [flow['packet_timestamp'] for flow in packet_flows if flow.get('packet_timestamp')]
        duration_seconds = 0
        if timestamps:
            timestamps.sort()
            duration = timestamps[-1] - timestamps[0]
            duration_seconds = duration.total_seconds()
        
        return {
            'total_packets': total_packets,
            'total_bytes': total_bytes,
            'unique_flows': unique_flows,
            'protocols': protocols,
            'ports': dict(list(ports.items())[:20]),  # Limit port count
            'duration_seconds': duration_seconds,
            'first_seen': timestamps[0].isoformat() if timestamps else None,
            'last_seen': timestamps[-1].isoformat() if timestamps else None
        }

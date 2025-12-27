"""
Device resolver
Extracted device information resolution logic from DataAnalyzer
"""

import logging
from typing import Dict, Any, Set, List
from .device_status_service import DeviceStatusService

logger = logging.getLogger(__name__)


class DeviceResolver:
    """Device information resolver"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.status_service = DeviceStatusService(db_manager)
    
    async def resolve_device_info(self, device_id: str, experiment_id: str) -> Dict[str, Any]:
        """Enhanced device information resolution"""
        enrichment_data = {}
        
        try:
            # Get device data from database
            device_query = """
            SELECT device_name, device_type, mac_address, ip_address, manufacturer
            FROM devices WHERE device_id = $1 AND experiment_id = $2
            """
            device_result = await self.db_manager.execute_query(device_query, (device_id, experiment_id))
            
            if device_result and len(device_result) > 0:
                device = device_result[0]
                mac_address = device['mac_address']
                
                # Device type inference
                device_type = await self.infer_device_type(device_id, experiment_id)
                
                # IP address resolution
                ip_address = await self.resolve_device_ip(device_id, experiment_id, mac_address)
                
                # Manufacturer resolution
                manufacturer = await self.resolve_manufacturer(mac_address)
                
                # Status determination - use real-time status calculation service
                status = await self.status_service.calculate_realtime_status(device_id, experiment_id)
                
                enrichment_data = {
                    'resolvedName': device['device_name'] or f"Device_{mac_address.replace(':', '').upper()[-6:]}",
                    'resolvedVendor': manufacturer,
                    'resolvedType': device_type,
                    'resolved_ip': ip_address,
                    'resolved_status': status,
                    'resolutionSource': 'enhanced_analysis'
                }
            
        except Exception as e:
            logger.debug(f"Could not resolve enhanced device info for {device_id}: {e}")
            
        return enrichment_data
    
    async def infer_device_type(self, device_id: str, experiment_id: str) -> str:
        """Infer device type based on traffic patterns"""
        try:
            # Get device traffic patterns
            traffic_query = """
            SELECT protocol, COUNT(*) as packet_count, 
                   AVG(packet_size) as avg_size,
                   ARRAY_AGG(DISTINCT dst_port) as dst_ports,
                   ARRAY_AGG(DISTINCT src_port) as src_ports,
                   COUNT(DISTINCT src_ip) as unique_src_ips,
                   COUNT(DISTINCT dst_ip) as unique_dst_ips
            FROM packet_flows 
            WHERE device_id = $1 AND experiment_id = $2 
            GROUP BY protocol
            ORDER BY packet_count DESC
            """
            
            traffic_result = await self.db_manager.execute_query(traffic_query, (device_id, experiment_id))
            
            if not traffic_result:
                logger.warning(f"No traffic data found for device {device_id}, defaulting to IoT device")
                return 'iot_device'
            
            # Analyze traffic patterns
            protocols = [row['protocol'] for row in traffic_result]
            all_ports = set()
            total_packets = sum(row['packet_count'] for row in traffic_result)
            avg_packet_size = sum(row['avg_size'] * row['packet_count'] for row in traffic_result) / total_packets if total_packets > 0 else 0
            unique_destinations = sum(row['unique_dst_ips'] for row in traffic_result)
            
            for row in traffic_result:
                if row['dst_ports']:
                    all_ports.update([p for p in row['dst_ports'] if p is not None])
                if row['src_ports']:
                    all_ports.update([p for p in row['src_ports'] if p is not None])
            
            # Device type inference rules
            return self._classify_device_by_patterns(protocols, all_ports, avg_packet_size, unique_destinations)
            
        except Exception as e:
            logger.error(f"Error inferring device type for {device_id}: {e}")
            return 'unknown'
    
    def _classify_device_by_patterns(self, protocols: List[str], ports: Set[int], 
                                   avg_packet_size: float, unique_destinations: int) -> str:
        """Classify device based on traffic patterns"""
        
        # Router/gateway detection (high priority)
        if ('DHCP' in protocols or 67 in ports or 68 in ports or 
            'ARP' in protocols or unique_destinations > 50):
            return 'router'
        
        # Camera
        if (554 in ports or 'RTSP' in protocols or 
            (80 in ports and avg_packet_size > 800) or
            ('HTTP' in protocols and avg_packet_size > 1000)):
            return 'camera'
        
        # Smart device detection
        if ('UPnP' in protocols or 'SSDP' in protocols or 
            1900 in ports or 8080 in ports or 8443 in ports):
            return 'smart_device'
        
        # IoT sensor detection
        if (1883 in ports or 8883 in ports or  # MQTT
            5683 in ports or  # CoAP
            avg_packet_size < 200):
            return 'sensor'
        
        # Speaker/speaker detection
        if ('Spotify' in protocols or 'AirPlay' in protocols or 
            5353 in ports or 7000 in ports):
            return 'speaker'
        
        # Smart plug detection
        if (6667 in ports or 9999 in ports):
            return 'smart_plug'
        
        # Default IoT device
        return 'iot_device'
    
    async def resolve_device_ip(self, device_id: str, experiment_id: str, mac_address: str) -> str:
        """Resolve device IP address"""
        try:
            # Find most common IP from traffic data
            ip_query = """
            SELECT src_ip, COUNT(*) as occurrence_count 
            FROM packet_flows 
            WHERE device_id = $1 AND experiment_id = $2 
            GROUP BY src_ip 
            ORDER BY occurrence_count DESC 
            LIMIT 1
            """
            
            result = await self.db_manager.execute_query(ip_query, (device_id, experiment_id))
            
            if result and result[0]['src_ip']:
                return result[0]['src_ip']
            
            # Fallback: get IP from device record
            device_query = "SELECT ip_address FROM devices WHERE device_id = $1"
            device_result = await self.db_manager.execute_query(device_query, (device_id,))
            
            if device_result and device_result[0]['ip_address']:
                return device_result[0]['ip_address']
                
            return 'unknown'
            
        except Exception as e:
            logger.debug(f"Could not resolve IP for device {device_id}: {e}")
            return 'unknown'
    
    async def resolve_manufacturer(self, mac_address: str) -> str:
        """Resolve manufacturer based on MAC address - use unified device resolution service"""
        try:
            if not mac_address or len(mac_address) < 8:
                return 'Unknown'
            
            # Use unified device resolution service to get manufacturer information
            from database.services.device_resolution_service import DeviceResolutionService
            resolution_service = DeviceResolutionService(self.db_manager)
            
            device_info = await resolution_service.resolve_device_info(mac_address, use_cache=True)
            vendor_name = device_info.get('resolvedVendor', 'Unknown')
            
            logger.debug(f"Resolved manufacturer for {mac_address}: {vendor_name} via unified resolution service")
            return vendor_name
            
        except Exception as e:
            logger.debug(f"Could not resolve manufacturer for MAC {mac_address}: {e}")
            return 'Unknown'
    
    async def determine_device_status(self, device_id: str, experiment_id: str) -> str:
        """Determine device status"""
        logger.warning("determine_device_status is deprecated, use DeviceStatusService.calculate_realtime_status instead")
        return await self.status_service.calculate_realtime_status(device_id, experiment_id)
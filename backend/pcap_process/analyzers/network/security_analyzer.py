"""
Security analyzer
Extracted security-related analysis logic from DataAnalyzer
"""

import logging
from typing import Dict, List, Any
from datetime import datetime
import ipaddress

logger = logging.getLogger(__name__)


class SecurityAnalyzer:
    """Network security analyzer"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def detect_security_events(self, flow: Dict[str, Any], timestamp: datetime) -> str:
        """Detect potential security events"""
        src_port = flow.get('src_port', 0)
        dst_port = flow.get('dst_port', 0)
        packet_size = flow.get('packet_size', 0)
        src_ip = flow.get('src_ip', '')
        dst_ip = flow.get('dst_ip', '')
        
        # Port scanning indicators
        if (dst_port or 0) in [22, 23, 3389] and packet_size < 100:
            return 'potential_login_attempt'
        
        # Abnormal port access
        if (dst_port or 0) > 60000 or (src_port or 0) > 60000:
            return 'high_port_communication'
        
        # Abnormal time large data transfer
        if 2 <= timestamp.hour <= 5 and packet_size > 8000:
            return 'suspicious_large_transfer'
        
        # External communication from abnormal source
        if not self.is_local_network_traffic(src_ip, dst_ip) and (src_port or 0) < 1024:
            return 'external_system_access'
        
        return None
    
    def detect_security_events_detailed(self, flow: Dict[str, Any], timestamp: datetime) -> List[str]:
        """Detect detailed security events"""
        events = []
        
        src_port = flow.get('src_port') or 0
        dst_port = flow.get('dst_port') or 0
        packet_size = flow.get('packet_size', 0)
        src_ip = flow.get('src_ip', '')
        dst_ip = flow.get('dst_ip', '')
        
        # Port scanning indicators
        if dst_port < 1024 and packet_size < 100:
            events.append('potential_port_scan')
        
        # Abnormal port combination
        if (src_port or 0) > 60000 and (dst_port or 0) < 100:
            events.append('high_port_to_system')
        
        # Abnormal time large packet transfer
        if 2 <= timestamp.hour <= 5 and packet_size > 8000:
            events.append('large_night_transfer')
        
        # Potential data leakage
        if not self.is_local_network_traffic(src_ip, dst_ip) and packet_size > 1400:
            events.append('potential_exfiltration')
        
        return events
    
    # Security scoring functionality removed - not used by frontend
    
    def has_encryption_indicators(self, flow: Dict[str, Any]) -> bool:
        """Check for encryption indicators in traffic"""
        dst_port = flow.get('dst_port', 0)
        src_port = flow.get('src_port', 0)
        packet_size = flow.get('packet_size', 0)
        
        # Common encrypted ports
        encrypted_ports = {443, 993, 995, 465, 587, 636, 989, 990, 992, 8443}
        
        if dst_port in encrypted_ports or src_port in encrypted_ports:
            return True
        
        # MQTT over TLS
        if (dst_port == 8883 or src_port == 8883):
            return True
        
        # VPN indicators
        if dst_port in {1194, 500, 4500} or src_port in {1194, 500, 4500}:
            return True
        
        return False
    
    def is_local_network_traffic(self, src_ip: str, dst_ip: str) -> bool:
        """Check if traffic is within local network range"""
        try:
            # Define local network range
            local_ranges = [
                ipaddress.ip_network('192.168.0.0/16'),
                ipaddress.ip_network('10.0.0.0/8'),
                ipaddress.ip_network('172.16.0.0/12'),
                ipaddress.ip_network('169.254.0.0/16'),  # Link-local
                ipaddress.ip_network('127.0.0.0/8'),    # Loopback
            ]
            
            # First verify IP addresses
            if not src_ip or not dst_ip or src_ip == 'unknown' or dst_ip == 'unknown':
                return False
                
            src = ipaddress.ip_address(src_ip)
            dst = ipaddress.ip_address(dst_ip)
            
            # Check if both IPs are within local range
            src_local = any(src in network for network in local_ranges)
            dst_local = any(dst in network for network in local_ranges)
            
            return src_local and dst_local
            
        except (ValueError, ipaddress.AddressValueError):
            # If IP parsing fails, assume non-local
            return False
    
    def is_cloud_service(self, ip: str) -> bool:
        """Check if IP belongs to major cloud services"""
        try:
            # Major cloud service IP ranges (simplified)
            cloud_ranges = [
                # AWS ranges (example)
                ipaddress.ip_network('3.0.0.0/8'),
                ipaddress.ip_network('13.0.0.0/8'),
                ipaddress.ip_network('18.0.0.0/8'),
                ipaddress.ip_network('52.0.0.0/8'),
                ipaddress.ip_network('54.0.0.0/8'),
                # Google Cloud (example)
                ipaddress.ip_network('8.8.8.0/24'),
                ipaddress.ip_network('8.8.4.0/24'),
                ipaddress.ip_network('35.0.0.0/8'),
                # Microsoft Azure (example)
                ipaddress.ip_network('20.0.0.0/8'),
                ipaddress.ip_network('40.0.0.0/8'),
                # Common CDN ranges
                ipaddress.ip_network('1.1.1.0/24'),  # Cloudflare
                ipaddress.ip_network('1.0.0.0/24'),  # Cloudflare
            ]
            
            ip_addr = ipaddress.ip_address(ip)
            return any(ip_addr in network for network in cloud_ranges)
            
        except (ValueError, ipaddress.AddressValueError):
            return False
    
    def is_multicast_traffic(self, ip: str) -> bool:
        """Check if IP is multicast"""
        try:
            ip_addr = ipaddress.ip_address(ip)
            return ip_addr.is_multicast
        except:
            return False
    
    # Security risk level analysis removed - not used by frontend
    
    def detect_anomalous_behavior(self, flow: Dict[str, Any], 
                                 timestamp: datetime) -> List[str]:
        """Detect anomalous behavior"""
        anomalies = []
        
        packet_size = flow.get('packet_size', 0)
        src_port = flow.get('src_port', 0)
        dst_port = flow.get('dst_port', 0)
        
        # Abnormal large packet
        if packet_size > 9000:  # Exceeds standard MTU
            anomalies.append('jumbo_packet')
        
        # Abnormal small packet (possibly scanning)
        if packet_size < 20:
            anomalies.append('tiny_packet')
        
        # Abnormal time activity
        if 2 <= timestamp.hour <= 5:
            anomalies.append('off_hours_activity')
        
        # Abnormal system port usage
        if (dst_port or 0) < 1024 and (src_port or 0) > 32768:
            anomalies.append('system_port_access')
        
        return anomalies
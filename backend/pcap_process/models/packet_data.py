"""
Simplified Packet Data Models

Core data models for packet flows and network information.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import pytz


@dataclass
class PacketFlow:
    """Represents a network packet flow for storage in packet_flows table"""
    
    # Core packet information
    packet_timestamp: datetime
    src_ip: str
    dst_ip: str
    protocol: str
    packet_size: int
    flow_direction: str  # 'inbound', 'outbound'
    flow_hash: str
    
    # Optional port information
    src_port: Optional[int] = None
    dst_port: Optional[int] = None
    
    # MAC address information (Ethernet layer)
    src_mac: Optional[str] = None
    dst_mac: Optional[str] = None
    
    # Application layer protocol
    app_protocol: Optional[str] = None
    
    # Additional metadata
    tcp_flags: Optional[str] = None
    payload_size: int = 0
    device_mac: Optional[str] = None
    
    def __post_init__(self):
        """Ensure timestamp is in UTC timezone"""
        if self.packet_timestamp.tzinfo is None:
            # If no timezone info, assume it's UTC
            self.packet_timestamp = self.packet_timestamp.replace(tzinfo=timezone.utc)
        elif self.packet_timestamp.tzinfo != timezone.utc:
            # Convert to UTC if it's in a different timezone
            self.packet_timestamp = self.packet_timestamp.astimezone(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage with UTC timestamp"""
        return {
            'packet_timestamp': self.packet_timestamp,  # Already UTC from __post_init__
            'src_ip': self.src_ip,
            'dst_ip': self.dst_ip,
            'src_port': self.src_port,
            'dst_port': self.dst_port,
            'protocol': self.protocol,
            'packet_size': self.packet_size,
            'flow_direction': self.flow_direction,
            'flow_hash': self.flow_hash,
            'tcp_flags': self.tcp_flags,
            'payload_size': self.payload_size,
            'src_mac': self.src_mac,
            'dst_mac': self.dst_mac,
            'app_protocol': self.app_protocol
        }
    
    @classmethod
    def from_pcap_timestamp(cls, timestamp: float, **kwargs) -> 'PacketFlow':
        """Create PacketFlow from PCAP timestamp (Unix timestamp)"""
        # Convert Unix timestamp to UTC datetime
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        return cls(packet_timestamp=dt, **kwargs)
    
    def get_source_endpoint(self) -> str:
        """Get source endpoint as IP:port"""
        if self.src_port:
            return f"{self.src_ip}:{self.src_port}"
        return self.src_ip
    
    def get_destination_endpoint(self) -> str:
        """Get destination endpoint as IP:port"""
        if self.dst_port:
            return f"{self.dst_ip}:{self.dst_port}"
        return self.dst_ip
    
    def is_tcp(self) -> bool:
        """Check if this is a TCP packet"""
        return self.protocol.upper() == 'TCP'
    
    def is_udp(self) -> bool:
        """Check if this is a UDP packet"""
        return self.protocol.upper() == 'UDP' 
"""
Unified Packet Parser

Simplified parser that combines the functionality of real_traffic_processor
with a cleaner, more modular interface.
Enhanced with timezone-aware processing for PCAP files.
"""

import hashlib
import logging
import warnings
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime, timezone

# Suppress Scapy warnings for virtual network interfaces
warnings.filterwarnings("ignore", message="No IPv4 address found on")
warnings.filterwarnings("ignore", message="more No IPv4 address found on")
# Suppress cryptography deprecation warnings from scapy
warnings.filterwarnings("ignore", category=DeprecationWarning, module="scapy")
# Suppress TripleDES deprecation warning
warnings.filterwarnings("ignore", message="TripleDES has been moved to cryptography.hazmat.decrepit*")
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*TripleDES.*")
from cryptography.hazmat.primitives.ciphers.algorithms import TripleDES

# Set scapy runtime logger to ERROR level to suppress warnings
scapy_logger = logging.getLogger("scapy.runtime")
scapy_logger.setLevel(logging.ERROR)

from scapy.all import rdpcap, IP, TCP, UDP, Ether, ARP, ICMP
try:
    from scapy.contrib.igmp import IGMP
except ImportError:
    # Fallback if IGMP is not available
    IGMP = None

from ..models.packet_data import PacketFlow
from ..utils.timezone_processor import timezone_processor

logger = logging.getLogger(__name__)


class PacketParser:
    """
    Unified parser for extracting packet flows from PCAP files
    
    Responsibilities:
    - Parse PCAP files using Scapy
    - Extract packet-level information including MAC addresses
    - Generate flow identifiers
    - Create packet flow objects with enhanced protocol detection
    """
    
    def __init__(self):
        """Initialize packet parser"""
        self.protocol_mapping = {
            1: 'ICMP',
            6: 'TCP', 
            17: 'UDP',
            2: 'IGMP',
            89: 'OSPF',
            41: 'IPv6',
            47: 'GRE',
            50: 'ESP',
            51: 'AH'
        }
        
        # Application layer protocol detection
        self.app_protocols = {
            # HTTP/HTTPS
            80: 'HTTP',
            443: 'HTTPS',
            8080: 'HTTP-ALT',
            8443: 'HTTPS-ALT',
            
            # DNS
            53: 'DNS',
            
            # DHCP
            67: 'DHCP',
            68: 'DHCP',
            
            # SMTP/POP/IMAP
            25: 'SMTP',
            110: 'POP3',
            143: 'IMAP',
            993: 'IMAPS',
            995: 'POP3S',
            
            # FTP
            20: 'FTP-DATA',
            21: 'FTP',
            
            # SSH/Telnet
            22: 'SSH',
            23: 'Telnet',
            
            # SNMP
            161: 'SNMP',
            162: 'SNMP',
            
            # NTP
            123: 'NTP',
            
            # SSDP (UPnP)
            1900: 'SSDP',
            
            # Common IoT protocols
            1883: 'MQTT',
            8883: 'MQTT-SSL',
            5683: 'CoAP',
            5684: 'CoAP-DTLS'
        }
        
        logger.info("Enhanced Packet Parser initialized with MAC address and protocol support")
    
    async def parse_pcap_file(self, pcap_path: Path, device_mac: str) -> List[PacketFlow]:
        """
        Parse PCAP file and extract packet flows with timezone-aware processing.
        
        Args:
            pcap_path: Path to PCAP file
            device_mac: MAC address of the device this file belongs to
            
        Returns:
            List of packet flow objects with UTC timestamps
        """
        logger.info(f"Parsing PCAP file: {pcap_path}")
        
        if not pcap_path.exists():
            raise FileNotFoundError(f"PCAP file not found: {pcap_path}")
        
        # ENHANCED: Process timezone metadata from filename
        pcap_metadata = timezone_processor.process_pcap_metadata(pcap_path)
        timezone_code = pcap_metadata.get('timezone_code', 'UTC')
        timezone_offset = pcap_metadata.get('timezone_offset', 0)
        
        logger.info(f"PCAP timezone detected: {timezone_code} (UTC{timezone_offset:+d})")
        
        # Validate MAC address from filename against provided device_mac
        filename_mac = pcap_metadata.get('mac_address')
        if filename_mac and filename_mac.upper() != device_mac.upper():
            logger.warning(f"MAC address mismatch: filename={filename_mac}, provided={device_mac}")
        
        try:
            # Read PCAP file
            packets = rdpcap(str(pcap_path))
            logger.info(f"Loaded {len(packets)} packets from {pcap_path}")
            
            if not packets:
                return []
            
            # Extract device IP from first few packets
            device_ip = self._extract_device_ip(packets, device_mac)
            if not device_ip:
                logger.warning(f"Could not determine device IP for {device_mac}")
                device_ip = "unknown"
            
            # Process packets into flows with timezone conversion
            packet_flows = []
            
            for i, packet in enumerate(packets):
                try:
                    flow = self._process_packet(packet, device_ip, device_mac, timezone_code)
                    if flow:
                        packet_flows.append(flow)
                        
                except Exception as e:
                    logger.debug(f"Error processing packet {i}: {e}")
                    continue
            
            logger.info(f"Extracted {len(packet_flows)} packet flows from {pcap_path} (timezone: {timezone_code})")
            return packet_flows
            
        except Exception as e:
            logger.error(f"Error parsing PCAP file {pcap_path}: {e}")
            raise
    
    def _extract_device_ip(self, packets, device_mac: str) -> Optional[str]:
        """Extract device IP address from packets using ARP or traffic analysis"""
        # Try to find device IP from ARP packets first
        for packet in packets[:200]:  # Check first 200 packets
            if packet.haslayer(ARP):
                arp = packet[ARP]
                if hasattr(arp, 'hwsrc') and arp.hwsrc.lower() == device_mac.lower():
                    if arp.psrc and arp.psrc != '0.0.0.0':  # Filter invalid IP
                        return arp.psrc
                if hasattr(arp, 'hwdst') and arp.hwdst.lower() == device_mac.lower():
                    if arp.pdst and arp.pdst != '0.0.0.0':  # Filter invalid IP
                        return arp.pdst
        
        # Fallback: look for most common source IP from device MAC
        ip_counts = {}
        for packet in packets[:200]:  # Increase check range
            if packet.haslayer(IP) and packet.haslayer(Ether):
                eth = packet[Ether]
                ip = packet[IP]
                # Only count IP from target device MAC
                if eth.src.lower() == device_mac.lower():
                    src_ip = ip.src
                    # Filter invalid IP address
                    if src_ip and src_ip != '0.0.0.0' and not src_ip.startswith('224.') and not src_ip.startswith('239.'):
                        ip_counts[src_ip] = ip_counts.get(src_ip, 0) + 1
        
        if ip_counts:
            return max(ip_counts.items(), key=lambda x: x[1])[0]
        
        return None
    
    def _process_packet(self, packet, device_ip: str, device_mac: str, timezone_code: str) -> Optional[PacketFlow]:
        """Process a single packet into a packet flow with timezone-aware timestamp conversion"""
        try:
            # Extract timestamp from packet
            packet_timestamp_raw = datetime.fromtimestamp(float(packet.time), tz=timezone.utc)
            
            # ENHANCED: Convert packet timestamp to UTC if timezone is specified
            if timezone_code != 'UTC':
                # The packet timestamp is assumed to be in the file's timezone
                # Convert it to UTC using timezone processor
                packet_timestamp_naive = packet_timestamp_raw.replace(tzinfo=None)
                packet_timestamp_utc = timezone_processor.convert_timestamp_to_utc(
                    packet_timestamp_naive, timezone_code
                )
                
                if packet_timestamp_utc:
                    packet_time = packet_timestamp_utc
                else:
                    logger.warning(f"Failed to convert timestamp to UTC, using raw timestamp")
                    packet_time = packet_timestamp_raw
            else:
                packet_time = packet_timestamp_raw
            
            # Extract MAC addresses from Ethernet layer
            src_mac = None
            dst_mac = None
            if packet.haslayer(Ether):
                ether = packet[Ether]
                src_mac = ether.src
                dst_mac = ether.dst
            
            # Check if packet has IP layer
            if not packet.haslayer(IP):
                return None
            
            ip_layer = packet[IP]
            src_ip = ip_layer.src
            dst_ip = ip_layer.dst
            protocol_num = ip_layer.proto
            protocol_name = self.protocol_mapping.get(protocol_num, f'PROTO_{protocol_num}')
            
            # Extract ports and detect application protocol
            src_port = None
            dst_port = None
            tcp_flags = None
            app_protocol = None
            
            if packet.haslayer(TCP):
                tcp_layer = packet[TCP]
                src_port = tcp_layer.sport
                dst_port = tcp_layer.dport
                tcp_flags = str(tcp_layer.flags)
                # Detect application protocol
                app_protocol = self._detect_app_protocol(src_port, dst_port, 'TCP')
            elif packet.haslayer(UDP):
                udp_layer = packet[UDP]
                src_port = udp_layer.sport
                dst_port = udp_layer.dport
                # Detect application protocol
                app_protocol = self._detect_app_protocol(src_port, dst_port, 'UDP')
            
            # Special handling for ICMP and IGMP
            if packet.haslayer(ICMP):
                app_protocol = 'ICMP'
            elif IGMP and packet.haslayer(IGMP):
                app_protocol = 'IGMP'
            
            # Calculate packet size
            packet_size = len(packet)
            payload_size = len(packet.payload) if packet.payload else 0
            
            # Determine flow direction
            flow_direction = self._classify_flow_direction(src_ip, dst_ip, device_ip)
            
            # Only process packets involving the target device
            if flow_direction == 'unknown':
                return None
            
            # Generate flow hash
            flow_hash = self._generate_flow_hash(
                src_ip, src_port or 0, dst_ip, dst_port or 0, protocol_name
            )
            
            # Create packet flow object with MAC addresses
            return PacketFlow(
                packet_timestamp=packet_time,
                src_ip=src_ip,
                dst_ip=dst_ip,
                src_port=src_port,
                dst_port=dst_port,
                protocol=protocol_name,
                packet_size=packet_size,
                flow_direction=flow_direction,
                flow_hash=flow_hash,
                tcp_flags=tcp_flags,
                payload_size=payload_size,
                device_mac=device_mac,
                src_mac=src_mac,
                dst_mac=dst_mac,
                app_protocol=app_protocol
            )
            
        except Exception as e:
            logger.debug(f"Error processing packet: {e}")
            return None
    
    def _detect_app_protocol(self, src_port: int, dst_port: int, transport_protocol: str) -> Optional[str]:
        """Detect application layer protocol based on port numbers"""
        # Check both source and destination ports
        for port in [src_port, dst_port]:
            if port in self.app_protocols:
                return self.app_protocols[port]
        
        # Return transport protocol if no specific application protocol detected
        return transport_protocol
    
    def _classify_flow_direction(self, src_ip: str, dst_ip: str, device_ip: str) -> str:
        """
        Classify flow direction relative to the device
        
        Enhanced logic: Only record flows where the target device is a participant
        This prevents duplicate recording of the same communication from multiple device perspectives
        """
        if src_ip == device_ip:
            return 'outbound'
        elif dst_ip == device_ip:
            return 'inbound'
        else:
            # Do not record communications that do not involve the target device
            # This prevents duplicate recording of the same communication in multiple PCAP files
            return 'unknown'  # Will be filtered out in _process_packet
    
    def _generate_flow_hash(self, src_ip: str, src_port: int, dst_ip: str, dst_port: int, protocol: str) -> str:
        """
        Generate a unique hash for the flow
        
        Enhanced: Create device-aware flow hash to support per-device perspective
        The hash includes directional information to distinguish inbound vs outbound flows
        """
        # Use standardized flow identifiers
        # Regardless of source/destination order, the same bidirectional communication uses the same base identifier
        if src_ip < dst_ip:
            base_flow = f"{src_ip}:{src_port}<->{dst_ip}:{dst_port}:{protocol}"
        else:
            base_flow = f"{dst_ip}:{dst_port}<->{src_ip}:{src_port}:{protocol}"
        
        return hashlib.md5(base_flow.encode()).hexdigest()
    
    def get_parser_stats(self) -> Dict[str, Any]:
        """Get parser statistics"""
        return {
            'supported_protocols': list(self.protocol_mapping.values()),
            'app_protocols': list(set(self.app_protocols.values())),
            'protocol_count': len(self.protocol_mapping),
            'app_protocol_count': len(set(self.app_protocols.values()))
        } 
"""
PCAP Processing Module for IoT Device Monitor
"""

from .core.engine import PcapProcessingEngine
from .core.coordinator import ProcessingCoordinator
from .parsers.packet_parser import PacketParser
from .storage.packet_storage import PacketStorage

# Version info removed
__author__ = "Developer"

# Public API
__all__ = [
    "PcapProcessingEngine",
    "ProcessingCoordinator", 
    "PacketParser",
    "PacketStorage"
]

# Module configuration
DEFAULT_CONFIG = {
    "batch_size": 1000,
    "max_workers": 4,
    "timeout_seconds": 300,
    "enable_real_time": True,
    "log_level": "INFO"
} 
"""
Configuration management for PCAP processing
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from pathlib import Path


@dataclass
class ProcessingConfig:
    """Configuration for PCAP processing operations"""
    
    # Processing parameters
    batch_size: int = 1000
    max_workers: int = 4
    timeout_seconds: int = 300
    
    # Feature flags
    enable_real_time: bool = True
    enable_packet_flows: bool = True
    enable_device_analysis: bool = True
    enable_topology_analysis: bool = True
    
    # Paths
    pcap_input_path: Optional[Path] = None
    output_path: Optional[Path] = None
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[Path] = None
    
    # Database
    db_batch_size: int = 500
    enable_transaction_batching: bool = True
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'ProcessingConfig':
        """Create config from dictionary"""
        return cls(**{k: v for k, v in config_dict.items() if hasattr(cls, k)})
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            'batch_size': self.batch_size,
            'max_workers': self.max_workers,
            'timeout_seconds': self.timeout_seconds,
            'enable_real_time': self.enable_real_time,
            'enable_packet_flows': self.enable_packet_flows,
            'enable_device_analysis': self.enable_device_analysis,
            'enable_topology_analysis': self.enable_topology_analysis,
            'log_level': self.log_level,
            'db_batch_size': self.db_batch_size,
            'enable_transaction_batching': self.enable_transaction_batching
        }
    
    def validate(self) -> bool:
        """Validate configuration parameters"""
        if self.batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if self.max_workers <= 0:
            raise ValueError("max_workers must be positive")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        return True 
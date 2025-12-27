"""
ID Generation Utilities
Provides utilities for generating consistent IDs only for experiments and devices
No lab concept needed
"""

import hashlib
from typing import Optional


class IdGenerator:
    """
    Centralized ID generation for experiments and devices
    """
    
    @classmethod
    def generate_device_id(cls, mac_address: str) -> str:
        """
        Generate deterministic device ID from MAC address
        
        Args:
            mac_address: Device MAC address
            
        Returns:
            Deterministic device ID
        """
        # Normalize MAC address
        normalized_mac = mac_address.upper().replace(':', '').replace('-', '')
        
        # Create hash
        hash_value = hashlib.sha256(f"device_{normalized_mac}".encode()).hexdigest()
        
        # Use first 16 characters for ID
        return f"dev_{hash_value[:12]}"
    
    @classmethod
    def generate_experiment_id(cls, experiment_name: str) -> str:
        """
        Generate deterministic experiment ID from name
        
        Args:
            experiment_name: Experiment name
            
        Returns:
            Deterministic experiment ID
        """
        # Normalize experiment name
        normalized_name = experiment_name.lower().strip().replace(' ', '_')
        
        # Create hash for deterministic ID
        hash_value = hashlib.sha256(f"experiment_{normalized_name}".encode()).hexdigest()
        
        # Use experiment name as ID if it's already formatted properly
        if normalized_name.startswith('experiment_'):
            return normalized_name
        else:
            return f"exp_{hash_value[:12]}"
    
    @classmethod
    def is_deterministic_device_id(cls, device_id: str, mac_address: str) -> bool:
        """
        Check if device ID is deterministic for given MAC address
        
        Args:
            device_id: Device ID to check
            mac_address: Device MAC address
            
        Returns:
            True if deterministic, False otherwise
        """
        expected_id = cls.generate_device_id(mac_address)
        return device_id == expected_id


# Convenience functions for backward compatibility
def generate_device_id(mac_address: str) -> str:
    """Generate device ID from MAC address"""
    return IdGenerator.generate_device_id(mac_address)

def generate_experiment_id(experiment_name: str) -> str:
    """Generate experiment ID from name"""
    return IdGenerator.generate_experiment_id(experiment_name) 
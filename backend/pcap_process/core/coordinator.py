"""
Processing Coordinator

Manages the workflow of processing PCAP files and coordinating between components.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

from .config import ProcessingConfig

# Import unified manager
from config.unified_config_manager import UnifiedConfigManager

# Initialize manager
config_manager = UnifiedConfigManager()

logger = logging.getLogger(__name__)


class ConfigurableProcessingCoordinator:
    """
    Coordinates the processing workflow between different components
    
    Responsibilities:
    - Manage processing workflow
    - Coordinate between parser and storage
    - Handle file discovery and metadata
    - Batch processing operations
    """
    
    def __init__(self, config: ProcessingConfig):
        """Initialize coordinator"""
        self.config = config
        
        # Load unified configuration
        self.unified_config = config_manager.get_config()
        self.log_templates = config_manager.get_log_templates()
        
        # Get service-specific configuration
        self.pcap_config = self.unified_config.get('pcap_processing', {})
        self.processing_params = self.pcap_config.get('processing_parameters', {})
        self.feature_flags = self.pcap_config.get('feature_flags', {})
        self.parser_config = self.pcap_config.get('parser_config', {})
        self.storage_config = self.pcap_config.get('storage_config', {})
        self.error_handling = self.pcap_config.get('error_handling', {})
        self.logging_config = self.pcap_config.get('logging', {})
        self.performance_config = self.pcap_config.get('performance', {})
        
        if self._should_log_coordination_steps():
            logger.info(self._get_log_message('coordinator_init'))
    
    def _get_log_message(self, template_key: str, **kwargs) -> str:
        """Get formatted log message from templates"""
        try:
            template = self.log_templates.get('pcap_processing', {}).get(template_key)
            if isinstance(template, str):
                return template.format(**kwargs)
            elif isinstance(template, dict):
                message_format = template.get('emoji', template_key)
                return message_format.format(**kwargs)
            else:
                return template_key
        except Exception:
            return f"[Missing log message: pcap_processing.{template_key}]"
    
    def _should_log_coordination_steps(self) -> bool:
        """Check if coordination steps logging is enabled"""
        return self.logging_config.get('log_coordination_steps', True)
    
    def _should_log_file_processing(self) -> bool:
        """Check if file processing logging is enabled"""
        return self.logging_config.get('log_file_processing', True)
    
    def _should_log_error_details(self) -> bool:
        """Check if error details logging is enabled"""
        return self.logging_config.get('log_error_details', True)
    
    def _should_continue_on_parse_error(self) -> bool:
        """Check if processing should continue on parse errors"""
        return self.error_handling.get('continue_on_parse_error', True)
    
    def _should_skip_corrupted_files(self) -> bool:
        """Check if corrupted files should be skipped"""
        return self.error_handling.get('skip_corrupted_files', True)
    
    def _get_batch_size(self) -> int:
        """Get processing batch size from configuration"""
        return self.processing_params.get('batch_size', 1000)
    
    def _should_enable_mac_validation(self) -> bool:
        """Check if MAC address validation is enabled"""
        return self.feature_flags.get('enable_mac_validation', True)
    
    async def process_experiment_directory(self, experiment_path: Path, experiment_id: str, 
                                         packet_parser, storage) -> Dict[str, Any]:
        """
        Process all PCAP files in an experiment directory
        
        Args:
            experiment_path: Path to experiment directory
            experiment_id: Experiment identifier
            packet_parser: Packet parser instance
            storage: Storage instance
            
        Returns:
            Processing results
        """
        if self._should_log_coordination_steps():
            logger.info(self._get_log_message('experiment_coordination', experiment_id=experiment_id))
        
        try:
            # Find PCAP files
            pcap_files = list(experiment_path.glob("*.pcap"))
            if not pcap_files:
                return {
                    'success': True,
                    'experiment_id': experiment_id,
                    'files_processed': 0,
                    'packets_processed': 0,
                    'message': 'No PCAP files found'
                }
            
            if self._should_log_coordination_steps():
                logger.info(self._get_log_message('pcap_files_found', count=len(pcap_files)))
            
            # Process files in batches
            total_packets = 0
            processed_files = 0
            failed_files = 0
            
            for pcap_file in pcap_files:
                # Extract device info from filename
                device_mac = self._extract_device_mac(pcap_file.name) if self._should_enable_mac_validation() else None
                if self._should_enable_mac_validation() and not device_mac:
                    if self._should_log_error_details():
                        logger.warning(self._get_log_message('mac_extraction_warning', filename=pcap_file.name))
                    if self._should_skip_corrupted_files():
                        continue
                
                # Process single file
                result = await self.process_single_pcap(
                    pcap_file, experiment_id, device_mac or "unknown", packet_parser, storage
                )
                
                if result.get('success'):
                    processed_files += 1
                    total_packets += result.get('packets_processed', 0)
                else:
                    failed_files += 1
                    if self._should_log_error_details():
                        logger.error(self._get_log_message('file_processing_failed', 
                                                         filename=pcap_file.name, 
                                                         error=result.get('error', 'Unknown error')))
                    if not self._should_continue_on_parse_error():
                        break
            
            return {
                'success': True,
                'experiment_id': experiment_id,
                'files_found': len(pcap_files),
                'files_processed': processed_files,
                'files_failed': failed_files,
                'packets_processed': total_packets
            }
            
        except Exception as e:
            if self._should_log_error_details():
                logger.error(self._get_log_message('coordination_error', error=str(e)))
            return {
                'success': False,
                'experiment_id': experiment_id,
                'error': str(e)
            }
    
    async def process_single_pcap(self, pcap_file: Path, experiment_id: str, device_mac: str,
                                packet_parser, storage) -> Dict[str, Any]:
        """
        Process a single PCAP file
        
        Args:
            pcap_file: Path to PCAP file
            experiment_id: Experiment identifier
            device_mac: Device MAC address
            packet_parser: Packet parser instance
            storage: Storage instance
            
        Returns:
            Processing results
        """
        if self._should_log_file_processing():
            logger.info(self._get_log_message('pcap_file_start', 
                                            filename=pcap_file.name, device_mac=device_mac))
        
        try:
            # Parse packets from file
            packets = await packet_parser.parse_pcap_file(pcap_file, device_mac)
            
            if not packets:
                if self._should_log_error_details():
                    logger.warning(self._get_log_message('no_packets_warning', filename=pcap_file.name))
                return {
                    'success': True,
                    'file': str(pcap_file),
                    'packets_processed': 0,
                    'message': 'No packets found'
                }
            
            # Store packets with experiment context
            storage_result = await storage.store_packet_flows(
                packets, experiment_id, device_mac
            )
            
            if self._should_log_file_processing():
                logger.info(self._get_log_message('packets_processed', 
                                                count=len(packets), filename=pcap_file.name))
            
            return {
                'success': True,
                'file': str(pcap_file),
                'device_mac': device_mac,
                'packets_processed': len(packets),
                'storage_result': storage_result
            }
            
        except Exception as e:
            if self._should_log_error_details():
                logger.error(self._get_log_message('pcap_processing_error', 
                                                 filename=pcap_file.name, error=str(e)))
            return {
                'success': False,
                'file': str(pcap_file),
                'error': str(e)
            }
    
    def _extract_device_mac(self, filename: str) -> Optional[str]:
        """Extract device MAC address from filename"""
        try:
            # Handle different filename formats
            # Format 1: MAC_timestamp.pcap
            # Format 2: device_name.pcap
            
            if '_' in filename:
                mac_part = filename.split('_')[0]
                # Check if it looks like a MAC address
                if self._is_mac_address(mac_part):
                    return self._normalize_mac_address(mac_part)
            
            # Try to extract MAC from beginning of filename
            name_without_ext = filename.replace('.pcap', '')
            if self._is_mac_address(name_without_ext):
                return self._normalize_mac_address(name_without_ext)
            
            return None
            
        except Exception as e:
            if self._should_log_error_details():
                logger.error(self._get_log_message('mac_extraction_error', 
                                                 filename=filename, error=str(e)))
            return None
    
    def _is_mac_address(self, text: str) -> bool:
        """Check if text looks like a MAC address"""
        # Remove common separators
        clean_text = text.replace(':', '').replace('-', '').replace('.', '')
        
        # Should be 12 hex characters
        if len(clean_text) == 12:
            try:
                int(clean_text, 16)
                return True
            except ValueError:
                pass
        
        return False
    
    def _normalize_mac_address(self, mac_str: str) -> str:
        """Normalize MAC address to standard format"""
        # Remove separators
        clean_mac = mac_str.replace(':', '').replace('-', '').replace('.', '')
        
        # Add colons every 2 characters
        normalized = ':'.join(clean_mac[i:i+2] for i in range(0, 12, 2))
        
        return normalized.upper()
    
    async def discover_experiment_metadata(self, experiment_path: Path) -> Dict[str, Any]:
        """
        Discover metadata about an experiment directory
        
        Args:
            experiment_path: Path to experiment directory
            
        Returns:
            Experiment metadata
        """
        try:
            pcap_files = list(experiment_path.glob("*.pcap"))
            devices = set()
            
            for pcap_file in pcap_files:
                device_mac = self._extract_device_mac(pcap_file.name)
                if device_mac:
                    devices.add(device_mac)
            
            return {
                'experiment_id': experiment_path.name,
                'path': str(experiment_path),
                'pcap_files_count': len(pcap_files),
                'devices_found': list(devices),
                'discovered_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            if self._should_log_error_details():
                logger.error(self._get_log_message('metadata_discovery_error', error=str(e)))
            return {
                'experiment_id': experiment_path.name,
                'error': str(e)
            } 


# Backward compatibility alias
ProcessingCoordinator = ConfigurableProcessingCoordinator
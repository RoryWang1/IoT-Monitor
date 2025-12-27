#!/usr/bin/env python3
"""
PCAP time processing script
=================

Function:
1. Convert historical PCAP files (2023) to real-time data within the last 48 hours
2. Modify file name format: from YYYY-MM-DD_HH.MM.SS_IP.pcap to MAC_YY-MM-DD-HH-MM-SS_TIMEZONE.pcap
3. Modify PCAP internal timestamps to make it look like recent data
4. Process by MAC address and output to datasets/processed/ directory

Utilization:
    python utils/pcap_time_processor.py [source_dir] [--timezone TIMEZONE] [--spread-hours HOURS]

Args:
    source_dir: Source directory path (e.g. datasets/original/ac:15:a2:46:9b:de)
    --timezone: Timezone code (default: UTC, supported: EDT, BST, CST, PST, etc.)
    --spread-hours: Time distribution range in hours (default: 48)
    --output-dir: Output directory (default: datasets/processed)
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import List, Tuple, Optional
import re
import random

# Add project root to path for imports (only when running as script)
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

try:
    from scapy.all import rdpcap, wrpcap, Packet
    from scapy.layers.inet import IP
    from scapy.layers.l2 import Ether
except ImportError:
    print("Error: scapy library is missing, please install: pip install scapy")
    sys.exit(1)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Supported timezone offsets (hours)
TIMEZONE_OFFSETS = {
    'UTC': 0,
    'GMT': 0,
    'BST': 1,      # British Summer Time
    'CEST': 2,     # Central European Summer Time
    'CET': 1,      # Central European Time
    'EDT': -4,     # Eastern Daylight Time
    'EST': -5,     # Eastern Standard Time
    'CDT': -5,     # Central Daylight Time
    'CST': -6,     # Central Standard Time
    'MDT': -6,     # Mountain Daylight Time
    'MST': -7,     # Mountain Standard Time
    'PDT': -7,     # Pacific Daylight Time
    'PST': -8,     # Pacific Standard Time
    'JST': 9,      # Japan Standard Time
    'KST': 9,      # Korea Standard Time
    'AEST': 10,    # Australian Eastern Standard Time
    'AEDT': 11,    # Australian Eastern Daylight Time
}


class PcapTimeProcessor:
    """PCAP time processor"""
    
    def __init__(self, timezone_code: str = 'UTC', spread_hours: int = 48, output_dir: str = None): # type: ignore
        """
        Initialize the processor
        
        Args:
            timezone_code: Target timezone code
            spread_hours: Time distribution range (hours)
            output_dir: Output directory
        """
        self.timezone_code = timezone_code.upper()
        self.spread_hours = spread_hours
        self.output_dir = Path(output_dir or 'datasets/processed')
        
        if self.timezone_code not in TIMEZONE_OFFSETS:
            raise ValueError(f"Unsupported timezone code: {timezone_code}")
        
        self.timezone_offset = TIMEZONE_OFFSETS[self.timezone_code]
        
        # Calculate target time range (relative to current time)
        now = datetime.now(timezone.utc)
        self.end_time = now - timedelta(hours=1)  # End time: 1 hour ago
        self.start_time = self.end_time - timedelta(hours=spread_hours)  # Start time: spread_hours hours ago
        
        logger.info(f"Processor initialized:")
        logger.info(f"  Timezone: {self.timezone_code} (UTC{self.timezone_offset:+d})")
        logger.info(f"  Time range: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')} ~ {self.end_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        logger.info(f"  Output directory: {self.output_dir}")
    
    def extract_mac_from_directory(self, dir_path: Path) -> str:
        """Extract MAC address from directory name"""
        dir_name = dir_path.name
        
        # Check if it is a valid MAC address format
        mac_pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
        if re.match(mac_pattern, dir_name):
            return dir_name.upper()
        
        raise ValueError(f"Directory name is not a valid MAC address format: {dir_name}")
    
    def parse_original_filename(self, filename: str) -> Tuple[datetime, str]:
        """
        Parse original file name format: YYYY-MM-DD_HH.MM.SS_IP.pcap
        
        Returns:
            Tuple[original timestamp, IP address]
        """
        # Remove .pcap extension
        name_without_ext = filename.replace('.pcap', '').replace('.PCAP', '')
        
        # Pattern: YYYY-MM-DD_HH.MM.SS_IP
        pattern = r'^(\d{4}-\d{2}-\d{2})_(\d{2})\.(\d{2})\.(\d{2})_(.+)$'
        match = re.match(pattern, name_without_ext)
        
        if not match:
            raise ValueError(f"Cannot parse file name format: {filename}")
        
        date_part, hour, minute, second, ip_part = match.groups()
        
        # Build time string
        time_str = f"{date_part} {hour}:{minute}:{second}"
        original_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
        
        return original_time, ip_part
    
    def generate_new_filename(self, mac_address: str, target_time: datetime) -> str:
        """
        Generate new file name format: MAC_YY-MM-DD-HH-MM-SS_TIMEZONE.pcap
        """
        # Convert to target timezone time (for file name)
        timezone_offset_td = timedelta(hours=self.timezone_offset)
        local_time = target_time + timezone_offset_td
        
        # Format time (2-digit year)
        time_str = local_time.strftime('%y-%m-%d-%H-%M-%S')
        
        return f"{mac_address}_{time_str}_{self.timezone_code}.pcap"
    
    def calculate_time_mapping(self, pcap_files: List[Path]) -> List[Tuple[Path, datetime]]:
        """
        Calculate file time mapping
        Sort original files by time, then evenly distribute to target time range
        """
        # Parse all file original timestamps
        file_times = []
        for file_path in pcap_files:
            try:
                original_time, _ = self.parse_original_filename(file_path.name)
                file_times.append((file_path, original_time))
            except ValueError as e:
                logger.warning(f"Skip unparsable file: {file_path.name} - {e}")
                continue
        
        if not file_times:
            raise ValueError("No parsable PCAP files found")
        
        # Sort by original time
        file_times.sort(key=lambda x: x[1])
        
        # Calculate target time distribution
        total_duration = self.end_time - self.start_time
        file_count = len(file_times)
        
        time_mappings = []
        for i, (file_path, original_time) in enumerate(file_times):
            # Calculate position in target time range
            if file_count > 1:
                progress = i / (file_count - 1)
            else:
                progress = 0.5  # Single file in the middle
            
            # Add some randomness to avoid too uniform file times
            jitter = random.uniform(-0.1, 0.1) * total_duration.total_seconds() / file_count
            jitter_td = timedelta(seconds=jitter)
            
            target_time = self.start_time + timedelta(seconds=progress * total_duration.total_seconds()) + jitter_td
            
            # Ensure not out of range
            target_time = max(self.start_time, min(self.end_time, target_time))
            
            time_mappings.append((file_path, target_time))
        
        return time_mappings
    
    def process_pcap_timestamps(self, input_file: Path, output_file: Path, time_offset: timedelta):
        """
        Process PCAP file internal timestamps
        
        Args:
            input_file: Input PCAP file path
            output_file: Output PCAP file path  
            time_offset: Time offset
        """
        logger.info(f"Processing PCAP timestamps: {input_file.name}")
        
        try:
            # Read PCAP file
            packets = rdpcap(str(input_file))
            
            if not packets:
                logger.warning(f"File is empty or cannot be read: {input_file}")
                return False
            
            # Get first packet timestamp as reference
            first_packet_time = datetime.fromtimestamp(float(packets[0].time), tz=timezone.utc)
            
            # Modify all packet timestamps
            modified_packets = []
            for packet in packets:
                # Calculate relative offset to first packet
                packet_time = datetime.fromtimestamp(float(packet.time), tz=timezone.utc)
                relative_offset = packet_time - first_packet_time
                
                # Calculate new timestamp
                new_time = first_packet_time + time_offset + relative_offset
                new_timestamp = new_time.timestamp()
                
                # Create new packet (copy packet content but modify timestamp)
                new_packet = packet.copy()
                new_packet.time = new_timestamp
                
                modified_packets.append(new_packet)
            
            # Write new PCAP file
            output_file.parent.mkdir(parents=True, exist_ok=True)
            wrpcap(str(output_file), modified_packets)
            
            logger.info(f"  Process completed: {len(modified_packets)} packets")
            logger.info(f"  Output file: {output_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing PCAP file: {input_file} - {e}")
            return False
    
    def process_directory(self, source_dir: Path) -> bool:
        """
        Process all PCAP files in the specified directory
        
        Args:
            source_dir: Source directory path
            
        Returns:
            Success or failure
        """
        logger.info(f"Processing directory: {source_dir}")
        
        if not source_dir.exists() or not source_dir.is_dir():
            logger.error(f"Source directory does not exist or is not a directory: {source_dir}")
            return False
        
        # Extract MAC address
        try:
            mac_address = self.extract_mac_from_directory(source_dir)
            logger.info(f"Detected device MAC address: {mac_address}")
        except ValueError as e:
            logger.error(str(e))
            return False
        
        # Find PCAP files
        pcap_files = list(source_dir.glob('*.pcap')) + list(source_dir.glob('*.PCAP'))
        
        if not pcap_files:
            logger.warning(f"No PCAP files found in directory: {source_dir}")
            return False
        
        logger.info(f"Found {len(pcap_files)} PCAP files")
        
        # Calculate time mapping
        try:
            time_mappings = self.calculate_time_mapping(pcap_files)
            logger.info(f"Successfully calculated time mapping for {len(time_mappings)} files")
        except ValueError as e:
            logger.error(str(e))
            return False
        
        # Create output directory
        output_mac_dir = self.output_dir / mac_address
        output_mac_dir.mkdir(parents=True, exist_ok=True)
        
        # Process each file
        success_count = 0
        for file_path, target_time in time_mappings:
            try:
                # Generate new file name
                new_filename = self.generate_new_filename(mac_address, target_time)
                output_file = output_mac_dir / new_filename
                
                # Calculate time offset
                original_time, _ = self.parse_original_filename(file_path.name)
                time_offset = target_time - original_time.replace(tzinfo=timezone.utc)
                
                # Process PCAP timestamps
                if self.process_pcap_timestamps(file_path, output_file, time_offset):
                    success_count += 1
                    logger.info(f"  File time mapping: {original_time.strftime('%Y-%m-%d %H:%M:%S')} -> {target_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
                
            except Exception as e:
                logger.error(f"Failed to process file: {file_path} - {e}")
                continue
        
        logger.info(f"Directory processing completed: successfully processed {success_count}/{len(time_mappings)} files")
        logger.info(f"Output directory: {output_mac_dir}")
        
        return success_count > 0


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='PCAP time processing script - convert historical PCAP data to real-time data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  Process a single MAC address directory:
    python utils/pcap_time_processor.py datasets/original/ac:15:a2:46:9b:de
  
  Specify timezone and time range:
    python utils/pcap_time_processor.py datasets/original/ac:15:a2:46:9b:de --timezone EDT --spread-hours 24
  
  Process all MAC address directories:
    python utils/pcap_time_processor.py datasets/original --all
  
Supported timezones: UTC, EDT, BST, CST, PST, JST, etc.
        """
    )
    
    parser.add_argument(
        'source_path',
        help='Source path (single MAC directory or parent directory containing multiple MAC directories)'
    )
    
    parser.add_argument(
        '--timezone', '-tz',
        default='UTC',
        choices=list(TIMEZONE_OFFSETS.keys()),
        help='Target timezone code (default: UTC)'
    )
    
    parser.add_argument(
        '--spread-hours', '-s',
        type=int,
        default=48,
        help='Time distribution range (hours, default: 48)'
    )
    
    parser.add_argument(
        '--output-dir', '-o',
        default='datasets/processed',
        help='Output directory (default: datasets/processed)'
    )
    
    parser.add_argument(
        '--all', '-a',
        action='store_true',
        help='Process all MAC address subdirectories under the source path'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate path
    source_path = Path(args.source_path)
    if not source_path.exists():
        logger.error(f"Source path does not exist: {source_path}")
        return 1
    
    # Create processor
    try:
        processor = PcapTimeProcessor(
            timezone_code=args.timezone,
            spread_hours=args.spread_hours,
            output_dir=args.output_dir
        )
    except ValueError as e:
        logger.error(str(e))
        return 1
    
    # Determine which directories to process
    if args.all:
        # Process all subdirectories
        if not source_path.is_dir():
            logger.error("When using --all option, source path must be a directory")
            return 1
        
        subdirs = [d for d in source_path.iterdir() if d.is_dir()]
        if not subdirs:
            logger.error(f"No subdirectories found in {source_path}")
            return 1
        
        total_success = 0
        for subdir in subdirs:
            logger.info(f"\n{'='*50}")
            logger.info(f"Processing subdirectory: {subdir.name}")
            logger.info(f"{'='*50}")
            
            if processor.process_directory(subdir):
                total_success += 1
        
        logger.info(f"\n🎉 Batch processing completed: successfully processed {total_success}/{len(subdirs)} directories")
        
    else:
        # Process single directory
        if not source_path.is_dir():
            logger.error("Source path must be a directory containing PCAP files")
            return 1
        
        logger.info(f"\n{'='*50}")
        logger.info(f"Processing directory: {source_path.name}")
        logger.info(f"{'='*50}")
        
        if processor.process_directory(source_path):
            logger.info("\nProcessing completed!")
            logger.info(f"Processed files are located in: {processor.output_dir}")
            logger.info("You can copy the processed files to the pcap_input/ directory for testing")
        else:
            logger.error("\nProcessing failed")
            return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 
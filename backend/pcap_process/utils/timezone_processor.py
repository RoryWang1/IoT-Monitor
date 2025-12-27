"""
PCAP Timezone Processor

Handles timezone-aware PCAP file processing with filename-based timezone detection.
Converts PCAP timestamps to UTC based on filename timezone indicators.

File naming convention: MAC_YY-MM-DD-HH-MM-SS_TIMEZONE.pcap
Supported timezones: UTC, BST, EDT, CST, CEST, PST, MST, JST, etc.
"""

import re
import logging
from typing import Optional, Dict, Tuple
from datetime import datetime, timezone, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class TimezoneProcessor:
    """
    Processes PCAP files with timezone-aware filename parsing and timestamp conversion.
    
    Responsibilities:
    - Parse timezone information from PCAP filenames
    - Convert PCAP timestamps from local timezone to UTC
    - Validate timezone codes against supported timezones
    - Provide timezone offset calculations
    """
    
    # Timezone mapping with UTC offsets (standard time, not considering DST automatically)
    TIMEZONE_OFFSETS = {
        'UTC': 0,
        'GMT': 0,
        'BST': 1,      # British Summer Time (UTC+1)
        'CEST': 2,     # Central European Summer Time (UTC+2)
        'CET': 1,      # Central European Time (UTC+1)
        'EDT': -4,     # Eastern Daylight Time (UTC-4)
        'EST': -5,     # Eastern Standard Time (UTC-5)
        'CDT': -5,     # Central Daylight Time (UTC-5)
        'CST': -6,     # Central Standard Time (UTC-6)
        'MDT': -6,     # Mountain Daylight Time (UTC-6)
        'MST': -7,     # Mountain Standard Time (UTC-7)
        'PDT': -7,     # Pacific Daylight Time (UTC-7)
        'PST': -8,     # Pacific Standard Time (UTC-8)
        'JST': 9,      # Japan Standard Time (UTC+9)
        'KST': 9,      # Korea Standard Time (UTC+9)
        'AEST': 10,    # Australian Eastern Standard Time (UTC+10)
        'AEDT': 11,    # Australian Eastern Daylight Time (UTC+11)
    }
    
    def __init__(self):
        """Initialize timezone processor"""
        logger.info("Timezone Processor initialized with %d supported timezones", len(self.TIMEZONE_OFFSETS))
    
    def parse_pcap_filename(self, filename: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Parse PCAP filename to extract MAC address, timestamp, and timezone.
        
        Expected format: MAC_YY-MM-DD-HH-MM-SS_TIMEZONE
        Alternative format: MAC_YY-MM-DD-HH-MM-SS.pcap (defaults to UTC)
        
        Args:
            filename: PCAP filename to parse
            
        Returns:
            Tuple of (mac_address, timestamp_str, timezone_code)
        """
        try:
            # Remove .pcap extension
            name_without_ext = filename.replace('.pcap', '').replace('.PCAP', '')
            
            # Pattern for new format: MAC_YY-MM-DD-HH-MM-SS_TIMEZONE
            pattern_with_tz = r'^([0-9A-Fa-f:]{17})_(\d{2}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2})_([A-Z]{3,4})$'
            match_with_tz = re.match(pattern_with_tz, name_without_ext)
            
            if match_with_tz:
                mac_address, timestamp_str, timezone_code = match_with_tz.groups()
                logger.debug(f"Parsed filename with timezone: MAC={mac_address}, timestamp={timestamp_str}, tz={timezone_code}")
                return mac_address, timestamp_str, timezone_code
            
            # Pattern for legacy format: MAC_YY-MM-DD-HH-MM-SS (assume UTC)
            pattern_legacy = r'^([0-9A-Fa-f:]{17})_(\d{2}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2})$'
            match_legacy = re.match(pattern_legacy, name_without_ext)
            
            if match_legacy:
                mac_address, timestamp_str = match_legacy.groups()
                logger.debug(f"Parsed legacy filename: MAC={mac_address}, timestamp={timestamp_str}, defaulting to UTC")
                return mac_address, timestamp_str, 'UTC'
            
            # Pattern for test/non-standard format: MAC_ANYTHING_TZ (graceful fallback)
            pattern_flexible = r'^([0-9A-Fa-f:]{17})_.*_([A-Z]{3,4})$'
            match_flexible = re.match(pattern_flexible, name_without_ext)
            
            if match_flexible:
                mac_address, timezone_code = match_flexible.groups()
                logger.info(f"Using flexible parsing for {filename}: MAC={mac_address}, defaulting timestamp to current time, tz={timezone_code}")
                # Use current time as default timestamp
                current_time = datetime.now().strftime("%y-%m-%d-%H-%M-%S")
                return mac_address, current_time, timezone_code
            
            # Final fallback: extract MAC and use UTC
            pattern_mac_only = r'^([0-9A-Fa-f:]{17})_'
            match_mac = re.match(pattern_mac_only, name_without_ext)
            
            if match_mac:
                mac_address = match_mac.group(1)
                logger.info(f"Fallback parsing for {filename}: MAC={mac_address}, using current time and UTC")
                current_time = datetime.now().strftime("%y-%m-%d-%H-%M-%S")
                return mac_address, current_time, 'UTC'
            
            logger.warning(f"Filename does not match any expected pattern: {filename}")
            return None, None, None
            
        except Exception as e:
            logger.error(f"Error parsing filename {filename}: {e}")
            return None, None, None
    
    def get_timezone_offset(self, timezone_code: str) -> Optional[int]:
        """
        Get UTC offset in hours for the given timezone code.
        
        Args:
            timezone_code: Timezone code (e.g., 'EDT', 'BST', 'UTC')
            
        Returns:
            UTC offset in hours, or None if timezone not supported
        """
        offset = self.TIMEZONE_OFFSETS.get(timezone_code.upper())
        if offset is None:
            logger.warning(f"Unsupported timezone code: {timezone_code}")
        return offset
    
    def convert_timestamp_to_utc(self, local_timestamp: datetime, timezone_code: str) -> Optional[datetime]:
        """
        Convert local timestamp to UTC based on timezone code.
        
        Args:
            local_timestamp: Timestamp in local timezone
            timezone_code: Source timezone code
            
        Returns:
            UTC timestamp, or None if conversion failed
        """
        try:
            offset_hours = self.get_timezone_offset(timezone_code)
            if offset_hours is None:
                return None
            
            # Create timezone object
            local_tz = timezone(timedelta(hours=offset_hours))
            
            # If timestamp is naive, assume it's in the specified timezone
            if local_timestamp.tzinfo is None:
                local_timestamp = local_timestamp.replace(tzinfo=local_tz)
            
            # Convert to UTC
            utc_timestamp = local_timestamp.astimezone(timezone.utc)
            
            logger.debug(f"Converted {local_timestamp} ({timezone_code}) to {utc_timestamp} (UTC)")
            return utc_timestamp
            
        except Exception as e:
            logger.error(f"Error converting timestamp to UTC: {e}")
            return None
    
    def process_pcap_metadata(self, pcap_path: Path) -> Dict[str, any]:
        """
        Extract and process metadata from PCAP filename.
        
        Args:
            pcap_path: Path to PCAP file
            
        Returns:
            Dictionary containing processed metadata
        """
        filename = pcap_path.name
        mac_address, timestamp_str, timezone_code = self.parse_pcap_filename(filename)
        
        metadata = {
            'filename': filename,
            'mac_address': mac_address,
            'timestamp_str': timestamp_str,
            'timezone_code': timezone_code,
            'timezone_offset': None,
            'file_timestamp_utc': None,
            'parsing_success': False
        }
        
        if mac_address and timestamp_str and timezone_code:
            try:
                # Parse timestamp string - add comprehensive null checks
                if timestamp_str is None:
                    logger.error(f"timestamp_str is None for file {filename}")
                    return metadata
                    
                if not isinstance(timestamp_str, str) or len(timestamp_str) == 0:
                    logger.error(f"Invalid timestamp_str format for file {filename}: {timestamp_str}")
                    return metadata
                    
                file_timestamp = datetime.strptime(f"20{timestamp_str}", "%Y-%m-%d-%H-%M-%S")
                
                # Get timezone offset
                timezone_offset = self.get_timezone_offset(timezone_code)
                
                if timezone_offset is not None:
                    # Convert to UTC
                    utc_timestamp = self.convert_timestamp_to_utc(file_timestamp, timezone_code)
                    
                    if utc_timestamp:
                        metadata.update({
                            'timezone_offset': timezone_offset,
                            'file_timestamp_utc': utc_timestamp,
                            'parsing_success': True
                        })
                        
                        logger.info(f"Successfully processed metadata for {filename}")
                    
            except Exception as e:
                logger.error(f"Error processing metadata for {filename}: {e}")
        
        return metadata
    
    def get_supported_timezones(self) -> Dict[str, int]:
        """
        Get dictionary of all supported timezone codes and their UTC offsets.
        
        Returns:
            Dictionary mapping timezone codes to UTC offsets
        """
        return self.TIMEZONE_OFFSETS.copy()
    
    def validate_timezone_code(self, timezone_code: str) -> bool:
        """
        Validate if a timezone code is supported.
        
        Args:
            timezone_code: Timezone code to validate
            
        Returns:
            True if supported, False otherwise
        """
        return timezone_code.upper() in self.TIMEZONE_OFFSETS


# Singleton instance for global use
timezone_processor = TimezoneProcessor() 
"""
Pattern analyzer
Extracted pattern analysis logic from DataAnalyzer
"""

import logging
from typing import Dict, Any, Set, List
from datetime import datetime
from ..network.security_analyzer import SecurityAnalyzer

logger = logging.getLogger(__name__)


class PatternAnalyzer:
    """Pattern analyzer"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.security_analyzer = SecurityAnalyzer(db_manager)
    
    def analyze_connection_pattern(self, flow: Dict[str, Any]) -> str:
        """Analyze connection pattern for intelligent information"""
        src_ip = flow.get('src_ip', '')
        dst_ip = flow.get('dst_ip', '')
        src_port = flow.get('src_port') or 0
        dst_port = flow.get('dst_port') or 0
        packet_size = flow.get('packet_size', 0)
        
        if self.security_analyzer.is_local_network_traffic(src_ip, dst_ip):
            if packet_size < 100:
                return 'local_control'
            else:
                return 'local_data'
        elif self.security_analyzer.is_cloud_service(dst_ip):
            return 'cloud_sync'
        elif (dst_port or 0) < 1024:
            return 'server'
        else:
            return 'application_traffic'
    
    def detect_packet_anomalies(self, flow: Dict[str, Any], timestamp: datetime) -> str:
        """Detect potential anomalies in packet patterns"""
        packet_size = flow.get('packet_size', 0)
        src_port = flow.get('src_port') or 0
        dst_port = flow.get('dst_port') or 0
        
        # Abnormal packet size
        if packet_size > 9000:  # Jumbo frame
            return 'jumbo_frame'
        elif packet_size < 64 and packet_size > 0:
            return 'micro_packet'
        
        # Abnormal port usage
        if (src_port or 0) > 65000 or (dst_port or 0) > 65000:
            return 'high_port'
        
        # Abnormal time activity
        if 2 <= timestamp.hour <= 5 and packet_size > 1000:
            return 'night_large_transfer'
        
        return None
    
    def analyze_sophisticated_traffic_trend_pattern(self, packets: int, bytes_count: int, 
                                                  sessions: int, protocol_diversity: int,
                                                  hour: int, minute: int, connection_types: Set[str],
                                                  security_events: List[str], packet_sizes: List[int]) -> str:
        """
        Simplified traffic trend pattern analysis, following database constraints
        Only returns modes allowed by device_traffic_trend constraints
        """
        
        # Only use modes allowed by database constraints:
        # 'normal', 'business', 'evening', 'night', 'weekend', 'low', 'peak', 'burst', 'idle', 'active'
        
        # Time-based pattern
        if 18 <= hour <= 22:
            return 'evening'
        elif 22 <= hour <= 6:
            return 'night'
        elif 9 <= hour <= 17:
            return 'business'
        
        # Activity-based pattern
        if packets > 1500:
            return 'peak'
        elif packets > 500:
            if sessions > 100:
                return 'burst'
            else:
                return 'active'
        elif packets < 50:
            return 'idle'
        elif packets < 150:
            return 'low'
        else:
            return 'normal'
    
    def classify_advanced_traffic_pattern(self, packets: int, bytes_count: int, 
                                        sessions: int, unique_ips: int, 
                                        connection_patterns: Set[str], anomaly_indicators: List[str],
                                        hour: int) -> str:
        """
        Comprehensive traffic pattern classification, supporting all 143 modes allowed by device_traffic_trend table
        """
        
        avg_packet_size = bytes_count / packets if packets > 0 else 0
        session_diversity = sessions / packets if packets > 0 else 0
        ip_diversity = unique_ips / max(sessions, 1)
        
        # Security and anomaly patterns
        if len(anomaly_indicators) > 0:
            if any('login' in str(indicator) for indicator in anomaly_indicators):
                return 'security_incident'
            elif any('scan' in str(indicator) for indicator in anomaly_indicators):
                return 'discovery_scan'
            else:
                return 'anomalous'
        
        # Ultra-high capacity pattern
        if packets > 2000:
            if avg_packet_size > 1200:
                return 'streaming_media'
            else:
                return 'high_volume_media'
        
        # High capacity pattern
        elif packets > 1000:
            if 'cloud_sync' in connection_patterns:
                return 'cloud_burst'
            elif unique_ips > 5:
                return 'data_synchronization'
            else:
                return 'high_activity'
        
        # Medium activity pattern
        elif packets > 500:
            if session_diversity > 0.3:
                return 'connection_heavy'
            elif ip_diversity > 2:
                return 'network_discovery'
            else:
                return 'active'
        
        # IoT and sensor-specific patterns
        elif avg_packet_size < 200:
            if packets > 100:
                return 'iot_sensor_telemetry'
            elif packets > 50:
                return 'sensor_reading'
            else:
                return 'heartbeat'
        
        # Protocol and connection analysis
        elif 'system_service' in connection_patterns:
            return 'infrastructure_traffic'
        elif 'local_control' in connection_patterns:
            return 'device_monitoring'
        elif session_diversity > 0.1:
            return 'session_establishment'
        elif ip_diversity > 2:
            return 'peer_discovery'
        
        # Low activity pattern
        elif packets < 10:
            if 2 <= hour <= 5:
                return 'idle_maintenance'
            else:
                return 'idle'
        elif packets < 50:
            return 'low'
        
        # Complex time-based pattern
        elif 0 <= hour <= 2:  # Midnight
            if packets > 50:
                return 'midnight_backup'
            else:
                return 'background_maintenance'
        elif 3 <= hour <= 5:  # Early morning
            if packets > 30:
                return 'scheduled_maintenance'
            else:
                return 'maintenance_window'
        elif 6 <= hour <= 8:  # Morning
            if packets > 100:
                return 'morning_backup'
            else:
                return 'morning_sync'
        elif 9 <= hour <= 12:  # Morning business hours
            if avg_packet_size > 800:
                return 'business_data_transfer'
            else:
                return 'business'
        elif 13 <= hour <= 17:  # Afternoon business hours
            if packets > 200:
                return 'afternoon_backup'
            else:
                return 'operational_monitoring'
        elif 18 <= hour <= 22:  # Evening
            if packets > 150:
                return 'evening_backup'
            else:
                return 'evening_activity'
        else:  # Late night
            return 'background_activity'
    
    def calculate_traffic_intensity(self, packets: int, bytes_count: int, sessions: int) -> float:
        """Calculate traffic intensity score"""
        # Standardize by time bucket (usually 15 minutes = 900 seconds)
        packet_rate = packets / 900  # Packets per second
        byte_rate = bytes_count / 900  # Bytes per second
        session_rate = sessions / 900  # Sessions per second
        
        # Weighted score (packet 30%, byte 50%, session 20%)
        intensity = (packet_rate * 0.3) + (byte_rate / 1000 * 0.5) + (session_rate * 0.2)
        return round(min(intensity, 10.0), 2)  # Maximum 10.0
    
    def calculate_activity_level(self, packets: int, bytes_count: int, sessions: int, window_minutes: int) -> float:
        """
        Calculate activity level in 0-1 range to match database constraints
        """
        if packets == 0:
            return 0.0
        
        # Calculate normalized rates per hour
        packets_per_hour = (packets * 60) / window_minutes
        mb_per_hour = (bytes_count / (1024 * 1024)) * 60 / window_minutes
        sessions_per_hour = (sessions * 60) / window_minutes
        
        # Simple linear combination, scaled to 0-1 range to match constraints
        packet_component = min(packets_per_hour / 1000.0, 0.5)  # Maximum 0.5 from packets
        bytes_component = min(mb_per_hour / 10.0, 0.3)  # Maximum 0.3 from MB/hour
        session_component = min(sessions_per_hour / 100.0, 0.2)  # Maximum 0.2 from sessions
        
        total_activity = packet_component + bytes_component + session_component
        return round(min(total_activity, 1.0), 3)
    
    def calculate_traffic_quality_metrics(self, bucket_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate complex traffic quality metrics"""
        total_packets = bucket_data['total_packets']
        total_bytes = bucket_data['total_bytes']
        total_sessions = len(bucket_data['total_sessions'])
        unique_ips = len(bucket_data['unique_ips'])
        anomalies = len(bucket_data['anomaly_indicators'])
        
        # Calculate various quality metrics
        efficiency = total_bytes / total_packets if total_packets > 0 else 0
        diversity = len(bucket_data['protocols']) / max(total_sessions, 1)
        stability = max(0, 1 - (anomalies / max(total_packets / 100, 1)))
        connectivity = unique_ips / max(total_sessions, 1)
        
        # Overall quality score (0-10 scale)
        overall_score = (efficiency / 100 + diversity + stability + connectivity) / 4 * 10
        
        return {
            'efficiency': round(efficiency, 2),
            'diversity': round(diversity, 2),
            'stability': round(stability, 2),
            'connectivity': round(connectivity, 2),
            'overall_score': round(min(overall_score, 10.0), 2)
        }
    
    def classify_multidimensional_traffic_pattern(self, packets: int, bytes_count: int, 
                                                sessions: int, hour: int, intensity: float) -> str:
        """
        Advanced multi-dimensional traffic pattern classification from document design
        Combines time-based patterns with activity intensity patterns
        """
        # 1. Time-based pattern analysis
        time_pattern = self._classify_time_pattern(hour)
        
        # 2. Activity intensity pattern analysis  
        activity_pattern = self._classify_activity_pattern(packets, bytes_count, sessions, intensity)
        
        # 3. Comprehensive decision with priority logic
        return self._prioritize_pattern(time_pattern, activity_pattern, intensity)
    
    def _classify_time_pattern(self, hour: int) -> str:
        """Classify traffic pattern based on time period"""
        if 18 <= hour <= 22:
            return 'evening'
        elif 22 <= hour or hour <= 6:
            return 'night'
        elif 9 <= hour <= 17:
            return 'business'
        else:
            return 'normal'
    
    def _classify_activity_pattern(self, packets: int, bytes_count: int, 
                                 sessions: int, intensity: float) -> str:
        """Classify traffic pattern based on activity intensity"""
        # Document-defined thresholds for activity pattern classification
        if packets > 1500:
            return 'peak'
        elif packets > 500:
            if sessions > 100:
                return 'burst'
            else:
                return 'active'
        elif packets < 50:
            return 'idle'
        else:
            return 'normal'
    
    def _prioritize_pattern(self, time_pattern: str, activity_pattern: str, intensity: float) -> str:
        """
        Prioritize patterns based on comprehensive decision logic
        High activity patterns take priority over time patterns
        """
        # High priority activity patterns override time patterns
        if activity_pattern in ['peak', 'burst']:
            return activity_pattern
        
        # Low activity patterns combined with time patterns
        if activity_pattern == 'idle':
            if time_pattern == 'night':
                return 'night_idle'
            return 'idle'
        
        # Medium activity patterns combined with time context
        if activity_pattern == 'active':
            if time_pattern == 'business':
                return 'business_active'
            elif time_pattern == 'evening':
                return 'evening_active'
            return 'active'
        
        # Normal activity patterns use time classification
        if time_pattern != 'normal':
            return time_pattern
        
        # Default to activity pattern
        return activity_pattern
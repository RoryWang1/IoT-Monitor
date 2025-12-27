"""
Activity analyzer
Extracted network activity analysis logic from DataAnalyzer
"""

import logging
from typing import Dict, List, Any, Tuple
from datetime import datetime, timedelta, timezone
from collections import defaultdict

logger = logging.getLogger(__name__)


class ActivityAnalyzer:
    """Network activity analyzer"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.utc_timezone = timezone.utc
    
    def calculate_activity_intensity(self, packets: int, bytes_count: int, 
                                   period_minutes: int) -> str:
        """Calculate activity intensity"""
        # Standardize to activity per minute
        packets_per_min = packets / period_minutes if period_minutes > 0 else 0
        bytes_per_min = bytes_count / period_minutes if period_minutes > 0 else 0
        
        # Activity intensity classification
        if packets_per_min >= 100 or bytes_per_min >= 50000:
            return 'very_high'
        elif packets_per_min >= 50 or bytes_per_min >= 20000:
            return 'high'
        elif packets_per_min >= 20 or bytes_per_min >= 5000:
            return 'medium'
        elif packets_per_min >= 5 or bytes_per_min >= 1000:
            return 'low'
        else:
            return 'very_low'
    
    def analyze_traffic_pattern(self, packets: int, bytes_count: int, 
                              period_minutes: int, hour: int) -> str:
        """Analyze traffic patterns"""
        intensity = self.calculate_activity_intensity(packets, bytes_count, period_minutes)
        
        # Time pattern analysis
        if 6 <= hour < 12:
            time_pattern = "morning"
        elif 12 <= hour < 18:
            time_pattern = "afternoon"
        elif 18 <= hour < 22:
            time_pattern = "evening"
        else:
            time_pattern = "night"
        
        # Traffic pattern analysis
        if bytes_count > 0 and packets > 0:
            avg_packet_size = bytes_count / packets
            
            if avg_packet_size > 1000:
                traffic_type = "bulk_transfer"
            elif avg_packet_size > 500:
                traffic_type = "media_streaming"
            elif avg_packet_size > 100:
                traffic_type = "web_browsing"
            else:
                traffic_type = "control_messages"
        else:
            traffic_type = "no_traffic"
        
        return f"{time_pattern}_{intensity}_{traffic_type}"
    
    def calculate_packet_size_variance(self, packet_sizes: List[int]) -> float:
        """Calculate packet size variance"""
        if not packet_sizes or len(packet_sizes) < 2:
            return 0.0
        
        mean_size = sum(packet_sizes) / len(packet_sizes)
        variance = sum((size - mean_size) ** 2 for size in packet_sizes) / len(packet_sizes)
        return variance
    
    def analyze_temporal_characteristics(self, hour: int, minute: int) -> str:
        """Analyze temporal characteristics"""
        if 6 <= hour < 12:
            return "morning_peak"
        elif 12 <= hour < 18:
            return "afternoon_normal"
        elif 18 <= hour < 22:
            return "evening_peak"
        elif 22 <= hour or hour < 6:
            return "night_low"
        else:
            return "transition"
    
    async def generate_activity_timeline(self, device_id: str, experiment_id: str, 
                                       packet_flows: List[Dict[str, Any]], 
                                       time_windows: List[str]) -> Dict[str, Any]:
        """Generate activity timeline"""
        if not packet_flows:
            return {}
        
        # Sort by time
        sorted_flows = sorted(packet_flows, key=lambda x: x['packet_timestamp'])
        
        # Calculate time range
        start_time = sorted_flows[0]['packet_timestamp']
        end_time = sorted_flows[-1]['packet_timestamp']
        
        timeline_data = {}
        
        for window in time_windows:
            # Calculate time periods
            periods = self._calculate_time_periods(start_time, end_time, window)
            
            window_timeline = []
            for period_start, period_end in periods:
                # Count activity for this period
                period_flows = [
                    flow for flow in sorted_flows
                    if period_start <= flow['packet_timestamp'] <= period_end
                ]
                
                if period_flows:
                    packets = len(period_flows)
                    bytes_count = sum(flow.get('packet_size', 0) for flow in period_flows)
                    period_minutes = (period_end - period_start).total_seconds() / 60
                    
                    # Analyze activity pattern
                    intensity = self.calculate_activity_intensity(packets, bytes_count, period_minutes)
                    pattern = self.analyze_traffic_pattern(packets, bytes_count, period_minutes, period_start.hour)
                    
                    window_timeline.append({
                        'period_start': period_start.isoformat(),
                        'period_end': period_end.isoformat(),
                        'packets': packets,
                        'bytes': bytes_count,
                        'intensity': intensity,
                        'pattern': pattern
                    })
            
            timeline_data[window] = window_timeline
        
        return timeline_data
    
    def _calculate_time_periods(self, start_time: datetime, end_time: datetime, 
                              window: str) -> List[Tuple[datetime, datetime]]:
        """Calculate time periods"""
        window_minutes = {
            '1h': 60, '2h': 120, '6h': 360, 
            '12h': 720, '24h': 1440, '48h': 2880
        }
        
        # Length of each time period (minutes)
        period_minutes = window_minutes.get(window, 60) // 12  # Each window is divided into 12 time periods
        period_delta = timedelta(minutes=period_minutes)
        
        periods = []
        current_time = start_time
        
        while current_time < end_time:
            period_end = min(current_time + period_delta, end_time)
            periods.append((current_time, period_end))
            current_time = period_end
        
        return periods
"""
Time window management tool
Extracted time processing logic from DataAnalyzer
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class TimeWindowManager:
    """Time window manager"""
    
    def __init__(self):
        self.time_windows = ['1h', '2h', '6h', '12h', '24h', '48h']
        self.window_to_minutes = {
            '1h': 60, '2h': 120, '6h': 360, 
            '12h': 720, '24h': 1440, '48h': 2880
        }
        self.utc_timezone = timezone.utc
    
    def get_time_window_bounds(self, window: str, reference_time: datetime = None) -> Tuple[datetime, datetime]:
        """Get start and end time of time window"""
        if reference_time is None:
            reference_time = datetime.now(self.utc_timezone)
        
        if window not in self.window_to_minutes:
            logger.warning(f"Unknown time window: {window}, using 24h")
            window = '24h'
        
        minutes = self.window_to_minutes[window]
        start_time = reference_time - timedelta(minutes=minutes)
        return start_time, reference_time
    
    def calculate_time_periods(self, start_time: datetime, end_time: datetime, 
                             period_minutes: int) -> List[Tuple[datetime, datetime]]:
        """Calculate time periods"""
        periods = []
        current_time = start_time
        period_delta = timedelta(minutes=period_minutes)
        
        while current_time < end_time:
            period_end = min(current_time + period_delta, end_time)
            periods.append((current_time, period_end))
            current_time = period_end
        
        return periods
    
    def format_duration(self, duration: timedelta) -> str:
        """Format duration"""
        total_seconds = int(duration.total_seconds())
        
        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}m {seconds}s"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"
    
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
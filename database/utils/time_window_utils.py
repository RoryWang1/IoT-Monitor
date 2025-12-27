"""
Time window processing tool function
"""

from datetime import datetime, timedelta, timezone
from typing import Tuple, Optional


def calculate_time_window(
    time_window: str, 
    current_time: Optional[datetime] = None
) -> Tuple[datetime, datetime]:
    """
    Calculate the start and end time of the time window
    
    Args:
        time_window: time window string ("1h", "2h", "6h", "12h", "24h", "48h")
        current_time: current time, if None then use current UTC time
        
    Returns:
        Tuple[datetime, datetime]: (start_time, end_time)
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)
    
    time_deltas = {
        "1h": timedelta(hours=1),
        "2h": timedelta(hours=2),
        "6h": timedelta(hours=6),
        "12h": timedelta(hours=12),
        "24h": timedelta(hours=24),
        "48h": timedelta(hours=48)
    }
    
    delta = time_deltas.get(time_window, timedelta(hours=24))
    start_time = current_time - delta
    end_time = current_time
    
    return start_time, end_time


def get_time_window_delta(time_window: str) -> timedelta:
    """
    Get the time difference corresponding to the time window
    
    Args:
        time_window: time window string
        
    Returns:
        timedelta: time difference object
    """
    time_deltas = {
        "1h": timedelta(hours=1),
        "2h": timedelta(hours=2),
        "6h": timedelta(hours=6),
        "12h": timedelta(hours=12),
        "24h": timedelta(hours=24),
        "48h": timedelta(hours=48)
    }
    
    return time_deltas.get(time_window, timedelta(hours=24))


def format_time_window_for_query(time_window: str) -> str:
    """
    Format the time window for SQL query
    
    Args:
        time_window: time window string
        
    Returns:
        str: time interval string used in SQL query
    """
    sql_intervals = {
        "1h": "1 hour",
        "2h": "2 hours", 
        "6h": "6 hours",
        "12h": "12 hours",
        "24h": "24 hours",
        "48h": "48 hours"
    }
    
    return sql_intervals.get(time_window, "24 hours")


def validate_time_window(time_window: str) -> bool:
    """
    Validate if the time window string is valid
    
    Args:
        time_window: time window string
        
    Returns:
        bool: whether valid
    """
    valid_windows = {"1h", "2h", "6h", "12h", "24h", "48h"}
    return time_window in valid_windows
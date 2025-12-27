"""
Database query construction tool function
Unify the SQL query construction logic and eliminate repetitive condition processing
"""

from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime


def build_device_query_conditions(
    device_id: str,
    experiment_id: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
) -> Tuple[str, Dict[str, Any]]:
    """
    Build device query conditions and parameters
    
    Args:
        device_id: device ID
        experiment_id: experiment ID (optional)
        start_time: start time (optional)
        end_time: end time (optional)
        
    Returns:
        Tuple[str, Dict[str, Any]]: (WHERE condition string, parameter dictionary)
    """
    conditions = ["device_id = %(device_id)s"]
    params = {"device_id": device_id}
    
    if experiment_id is not None:
        conditions.append("experiment_id = %(experiment_id)s")
        params["experiment_id"] = experiment_id
    
    if start_time is not None:
        conditions.append("packet_timestamp >= %(start_time)s")
        params["start_time"] = start_time
        
    if end_time is not None:
        conditions.append("packet_timestamp <= %(end_time)s")
        params["end_time"] = end_time
    
    where_clause = " AND ".join(conditions)
    return where_clause, params


def build_experiment_query_conditions(
    experiment_id: Optional[str] = None
) -> Tuple[str, Dict[str, Any]]:
    """
    Build experiment query conditions and parameters
    
    Args:
        experiment_id: experiment ID (optional)
        
    Returns:
        Tuple[str, Dict[str, Any]]: (WHERE condition string, parameter dictionary)
    """
    if experiment_id is not None:
        return "experiment_id = %(experiment_id)s", {"experiment_id": experiment_id}
    else:
        return "1=1", {}


def build_pagination_clause(
    page: int = 1, 
    page_size: int = 20
) -> Tuple[str, Dict[str, Any]]:
    """
    Build pagination query LIMIT and OFFSET clauses
    
    Args:
        page: page number (starts from 1)
        page_size: page size
        
    Returns:
        Tuple[str, Dict[str, Any]]: (pagination clause, parameter dictionary)
    """
    offset = (page - 1) * page_size
    clause = "LIMIT %(limit)s OFFSET %(offset)s"
    params = {"limit": page_size, "offset": offset}
    
    return clause, params


def build_order_by_clause(
    order_by: str = "created_at",
    order_direction: str = "DESC"
) -> str:
    """
    Build ORDER BY clause
    
    Args:
        order_by: sort field
        order_direction: sort direction (ASC or DESC)
        
    Returns:
        str: ORDER BY clause
    """
    # Validate sort direction
    direction = order_direction.upper()
    if direction not in ["ASC", "DESC"]:
        direction = "DESC"
    
    # Basic field name validation (prevent SQL injection)
    allowed_fields = {
        "created_at", "updated_at", "device_name", "mac_address",
        "last_seen", "device_type", "manufacturer", "experiment_id",
        "packet_timestamp", "total_packets", "total_bytes", "port",
        "protocol", "percentage"
    }
    
    if order_by not in allowed_fields:
        order_by = "created_at"
    
    return f"ORDER BY {order_by} {direction}"


def build_complete_query(
    base_query: str,
    where_conditions: str,
    order_by: Optional[str] = None,
    pagination: Optional[str] = None
) -> str:
    """
    Build complete SQL query
    
    Args:
        base_query: base query (SELECT ... FROM ...)
        where_conditions: WHERE condition
        order_by: ORDER BY clause (optional)
        pagination: pagination clause (optional)
        
    Returns:
        str: complete SQL query
    """
    query_parts = [base_query, f"WHERE {where_conditions}"]
    
    if order_by:
        query_parts.append(order_by)
        
    if pagination:
        query_parts.append(pagination)
    
    return "\n".join(query_parts)


def format_traffic_bytes(bytes_value: int) -> str:
    """
    Format traffic bytes to human readable format
    
    Args:
        bytes_value: bytes value
        
    Returns:
        str: formatted string 
    """
    if bytes_value < 1024:
        return f"{bytes_value} B"
    elif bytes_value < 1024 * 1024:
        return f"{bytes_value / 1024:.1f} KB"
    elif bytes_value < 1024 * 1024 * 1024:
        return f"{bytes_value / (1024 * 1024):.1f} MB"
    else:
        return f"{bytes_value / (1024 * 1024 * 1024):.1f} GB"


def calculate_percentage(value: int, total: int) -> float:
    """
    Calculate percentage
    
    Args:
        value: value
        total: total
        
    Returns:
        float: percentage (0-100)
    """
    if total == 0:
        return 0.0
    return round((value / total) * 100, 2)
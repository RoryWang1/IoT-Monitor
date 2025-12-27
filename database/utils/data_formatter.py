"""
Data formatting tool function
Uniformly handle API response data formatting to ensure front-end data compatibility
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import json


def format_device_detail_response(device_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format device detail response data to ensure front-end data compatibility
    
    Args:
        device_data: device data from database
        
    Returns:
        Dict[str, Any]: formatted device detail data
    """
    return {
        "deviceId": device_data.get("device_id"),
        "deviceName": device_data.get("device_name"),
        "resolved_name": device_data.get("resolved_name"),
        "macAddress": device_data.get("mac_address"),
        "ipAddress": device_data.get("ip_address"),
        "deviceType": device_data.get("device_type"),
        "resolved_type": device_data.get("resolved_type"),
        "manufacturer": device_data.get("manufacturer"),
        "resolved_vendor": device_data.get("resolved_vendor"),
        "status": device_data.get("status"),
        "firstSeen": _format_datetime(device_data.get("first_seen")),
        "lastSeen": _format_datetime(device_data.get("last_seen")),
        "totalSessions": device_data.get("total_sessions", 0),
        "totalTraffic": device_data.get("total_traffic", 0),
        "totalBytes": device_data.get("total_bytes", 0),
        "totalPackets": device_data.get("total_packets", 0),
        "activeDuration": device_data.get("active_duration", 0),
        "resolution_source": device_data.get("resolution_source"),
        "timeWindow": device_data.get("time_window", "24h"),
        "experimentId": device_data.get("experiment_id")
    }


def format_port_analysis_response(port_data: List[Dict[str, Any]], total_packets: int = 0) -> List[Dict[str, Any]]:
    """
    Format port analysis response data to ensure front-end data compatibility
    
    Args:
        port_data: port data from database
        total_packets: total packets, used to calculate percentage
        
    Returns:
        List[Dict[str, Any]]: formatted port analysis data
    """
    # If total_packets is 0, calculate total
    if total_packets == 0:
        total_packets = sum(row.get("total_packets", 0) for row in port_data)
    
    return [
        {
            "port": row.get("port"),
            "protocol": row.get("protocols", row.get("protocol", "")),
            "packets": row.get("total_packets", 0),
            "bytes": row.get("total_bytes", 0),
            "percentage": _calculate_percentage(row.get("total_packets", 0), total_packets),
            "status": _determine_port_status(row.get("port"))
        }
        for row in port_data
    ]


def format_protocol_distribution_response(protocol_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Format protocol distribution response data to ensure front-end data compatibility
    
    Args:
        protocol_data: protocol data from database
        
    Returns:
        List[Dict[str, Any]]: formatted protocol distribution data
    """
    total_packets = sum(row.get("packet_count", 0) for row in protocol_data)
    
    return [
        {
            "protocol": row.get("protocol"),
            "packet_count": row.get("packet_count", 0),
            "byte_count": row.get("byte_count", 0),
            "sessions": row.get("session_count", 0),
            "percentage": _calculate_percentage(row.get("packet_count", 0), total_packets)
        }
        for row in protocol_data
    ]


def format_network_topology_response(topology_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format network topology response data to ensure front-end data compatibility
    
    Args:
        topology_data: topology data from database
        
    Returns:
        Dict[str, Any]: formatted network topology data
    """
    return {
        "nodes": [
            {
                "id": node.get("id"),
                "label": node.get("label"),
                "type": node.get("type"),
                "ip": node.get("ip"),
                "color": node.get("color"),
                "size": node.get("size"),
                "resolvedLabel": node.get("resolvedLabel") or node.get("resolved_label"),
                "resolvedVendor": node.get("resolvedVendor") or node.get("resolved_vendor"),
                "resolvedType": node.get("resolvedType") or node.get("resolved_type"),
                "resolutionSource": node.get("resolutionSource") or node.get("resolution_source"),
                "macAddress": node.get("macAddress") or node.get("mac_address")
            }
            for node in topology_data.get("nodes", [])
        ],
        "edges": [
            {
                "source": edge.get("source"),
                "target": edge.get("target"),
                "protocol": edge.get("protocol"),
                "packets": edge.get("packets", 0),
                "bytes": edge.get("bytes", 0),
                "weight": edge.get("weight", 1),
                "firstSeen": edge.get("firstSeen") or edge.get("first_seen"),
                "lastSeen": edge.get("lastSeen") or edge.get("last_seen")
            }
            for edge in topology_data.get("edges", [])
        ],
        "deviceInfo": topology_data.get("deviceInfo", {})
    }


def format_activity_timeline_response(timeline_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Format activity timeline response data to ensure front-end data compatibility
    
    Args:
        timeline_data: timeline data from database
        
    Returns:
        List[Dict[str, Any]]: formatted activity timeline data
    """
    return [
        {
            "timestamp": _format_datetime(row.get("timestamp")),
            "period_start": _format_datetime(row.get("period_start")),
            "period_end": _format_datetime(row.get("period_end")),
            "packet_count": row.get("packet_count", 0),
            "byte_count": row.get("byte_count", 0),
            "session_count": row.get("session_count", 0),
            "activity_level": row.get("activity_level", "low")
        }
        for row in timeline_data
    ]


def format_traffic_trend_response(trend_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Format traffic trend response data to ensure front-end data compatibility
    
    Args:
        trend_data: trend data from database
        
    Returns:
        Dict[str, Any]: formatted traffic trend data
    """
    return {
        "timeline": [
            {
                "timestamp": _format_datetime(row.get("timestamp")),
                "bytes": row.get("bytes", 0),
                "packets": row.get("packets", 0),
                "sessions": row.get("sessions", 0)
            }
            for row in trend_data
        ],
        "protocols": _group_by_protocol(trend_data)
    }


def format_experiment_overview_response(experiment_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format experiment overview response data to ensure front-end data compatibility
    
    Args:
        experiment_data: experiment data from database
        
    Returns:
        Dict[str, Any]: formatted experiment overview data
    """
    return {
        "experimentId": experiment_data.get("experiment_id"),
        "experimentName": experiment_data.get("experiment_name"),
        "status": experiment_data.get("status"),
        "deviceCount": experiment_data.get("device_count", 0),
        "onlineDevices": experiment_data.get("online_devices", 0),
        "totalTraffic": experiment_data.get("total_traffic", 0),
        "deviceTypes": experiment_data.get("device_types", []),
        "description": experiment_data.get("description", ""),
        "createdAt": _format_datetime(experiment_data.get("created_at"))
    }


def _format_datetime(dt: Optional[datetime]) -> Optional[str]:
    """
    Format date time to ISO string
    
    Args:
        dt: date time object
        
    Returns:
        Optional[str]: ISO formatted date time string
    """
    if dt is None:
        return None
    
    # Ensure timezone information
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    return dt.isoformat()


def _calculate_percentage(value: int, total: int) -> float:
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


def _determine_port_status(port: int) -> str:
    """
    Determine port status based on port number
    
    Args:
        port: port number
        
    Returns:
        str: port status
    """
    if port is None:
        return "unknown"
    
    # Common port status classification
    well_known_ports = {
        22: "ssh", 23: "telnet", 25: "smtp", 53: "dns", 80: "http", 
        110: "pop3", 143: "imap", 443: "https", 993: "imaps", 995: "pop3s"
    }
    
    if port in well_known_ports:
        return "well_known"
    elif port < 1024:
        return "system"
    elif port < 49152:
        return "registered"
    else:
        return "dynamic"


def _group_by_protocol(trend_data: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Group trend data by protocol
    
    Args:
        trend_data: trend data list
        
    Returns:
        Dict[str, List[Dict[str, Any]]]: data grouped by protocol
    """
    protocols = {}
    
    for row in trend_data:
        protocol = row.get("protocol", "unknown")
        if protocol not in protocols:
            protocols[protocol] = []
        
        protocols[protocol].append({
            "timestamp": _format_datetime(row.get("timestamp")),
            "bytes": row.get("bytes", 0),
            "packets": row.get("packets", 0)
        })
    
    return protocols
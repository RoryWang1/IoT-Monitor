"""
Data formatter
Extracted data formatting logic from DataAnalyzer
"""

import logging
import json
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class AnalysisDataFormatter:
    """Data formatter"""
    
    def __init__(self):
        pass
    
    def format_protocol_data(self, protocols: set, protocol_counts: Dict[str, int]) -> Dict[str, Any]:
        """Format protocol data"""
        return {
            'protocols': list(protocols),
            'protocol_count': len(protocols),
            'protocol_distribution': dict(list(protocol_counts.items())[:10])  # Limit top 10 protocols
        }
    
    def format_connection_data(self, connections: set, nodes: set) -> Dict[str, Any]:
        """Format connection data"""
        return {
            'connections': list(connections),
            'nodes': list(nodes),
            'node_count': len(nodes),
            'connection_count': len(connections),
            'network_density': len(connections) / max(1, len(nodes)) if nodes else 0
        }
    
    def format_security_data(self, security_events: List[str]) -> Dict[str, Any]:
        """Format security data (scoring removed - not used by frontend)"""
        return {
            'events': security_events,
            'event_count': len(security_events),
            'has_events': len(security_events) > 0
        }
    
    def format_anomaly_data(self, anomalies: List[str]) -> Dict[str, Any]:
        """Format anomaly data"""
        return {
            'indicators': anomalies,
            'anomaly_count': len(anomalies),
            'has_anomalies': len(anomalies) > 0
        }
    
    def format_activity_summary(self, packets: int, bytes_count: int, sessions: int, 
                              duration_seconds: float) -> Dict[str, Any]:
        """Format activity summary"""
        return {
            'total_packets': packets,
            'total_bytes': bytes_count,
            'total_sessions': sessions,
            'duration_seconds': duration_seconds,
            'avg_packet_size': bytes_count / packets if packets > 0 else 0,
            'packets_per_second': packets / duration_seconds if duration_seconds > 0 else 0,
            'bytes_per_second': bytes_count / duration_seconds if duration_seconds > 0 else 0
        }
    
    def format_time_window_data(self, time_window: str, start_time: datetime, 
                              end_time: datetime, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format time window data"""
        return {
            'time_window': time_window,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration_minutes': (end_time - start_time).total_seconds() / 60,
            'data': data
        }
    
    def format_device_analysis_result(self, device_id: str, experiment_id: str, 
                                    analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format device analysis result"""
        return {
            'device_id': device_id,
            'experiment_id': experiment_id,
            'analysis_timestamp': datetime.now().isoformat(),
            'analysis_data': analysis_data,
            'summary': self._generate_analysis_summary(analysis_data)
        }
    
    def format_topology_data(self, nodes: List[str], connections: List[str], 
                           topology_type: str) -> Dict[str, Any]:
        """Format topology data"""
        return {
            'nodes': nodes,
            'connections': connections,
            'node_count': len(nodes),
            'connection_count': len(connections),
            'network_density': len(connections) / max(1, len(nodes)) if nodes else 0,
            'topology_type': topology_type
        }
    
    def format_trend_data(self, trend_pattern: str, intensity: float, 
                         quality_metrics: Dict[str, float]) -> Dict[str, Any]:
        """Format trend data"""
        return {
            'pattern': trend_pattern,
            'intensity': intensity,
            'quality_metrics': quality_metrics,
            'trend_classification': self._classify_trend(trend_pattern, intensity)
        }
    
    def format_port_analysis_data(self, port_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Format port analysis data"""
        if not port_data:
            return {
                'ports': [],
                'port_count': 0,
                'top_ports': [],
                'port_distribution': {}
            }
        
        # Sort by traffic
        sorted_ports = sorted(port_data, key=lambda x: x.get('total_bytes', 0), reverse=True)
        
        return {
            'ports': port_data,
            'port_count': len(port_data),
            'top_ports': sorted_ports[:10],  # Top 10 ports
            'port_distribution': {
                str(port['port']): port['total_bytes'] 
                for port in sorted_ports[:20]  # Top 20 ports distribution
            }
        }
    
    # Risk level determination removed - not used by frontend
    
    def _generate_analysis_summary(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate analysis summary"""
        summary = {
            'total_data_points': 0,
            'analysis_completeness': 0.0,
            'key_findings': []
        }
        
        # Calculate data points
        for key, value in analysis_data.items():
            if isinstance(value, list):
                summary['total_data_points'] += len(value)
            elif isinstance(value, dict):
                summary['total_data_points'] += len(value)
        
        # Calculate analysis completeness
        expected_sections = ['traffic_trend', 'protocol_analysis', 'port_analysis', 'topology_data']
        completed_sections = sum(1 for section in expected_sections if section in analysis_data)
        summary['analysis_completeness'] = completed_sections / len(expected_sections)
        
        # Generate key findings
        if 'security_events' in analysis_data and analysis_data['security_events']:
            summary['key_findings'].append('Security events detected')
        
        if 'anomaly_indicators' in analysis_data and analysis_data['anomaly_indicators']:
            summary['key_findings'].append('Traffic anomalies identified')
        
        return summary
    
    def _classify_trend(self, pattern: str, intensity: float) -> str:
        """Classify trend"""
        if intensity > 7.0:
            return 'high_intensity'
        elif intensity > 4.0:
            return 'medium_intensity'
        elif intensity > 1.0:
            return 'low_intensity'
        else:
            return 'minimal_activity'
    
    def serialize_for_database(self, data: Any) -> str:
        """Serialize data for database"""
        if isinstance(data, dict):
            # Ensure all datetime objects are serialized
            serializable_data = self._make_serializable(data)
            return json.dumps(serializable_data, ensure_ascii=False)
        else:
            return str(data)
    
    def _make_serializable(self, obj: Any) -> Any:
        """Make object serializable"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {key: self._make_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif isinstance(obj, set):
            return list(obj)
        else:
            return obj
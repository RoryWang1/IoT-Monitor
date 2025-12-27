"""
Modular data analyzer
"""

import logging
from typing import Dict, List, Any
from datetime import datetime, timezone

from .core.experiment_analyzer import ExperimentAnalyzer
from .device.device_analyzer import DeviceAnalyzer
from .network.activity_analyzer import ActivityAnalyzer
from .network.security_analyzer import SecurityAnalyzer
from .utils.time_utils import TimeWindowManager
from .utils.pattern_analyzer import PatternAnalyzer
from .utils.data_formatter import AnalysisDataFormatter

logger = logging.getLogger(__name__)


class ModularDataAnalyzer:
    """
    Modular data analyzer
    Use specialized analyzer modules for complete data analysis
    """
    
    def __init__(self, db_manager):
        """Initialize modular analyzer"""
        self.db_manager = db_manager
        self.utc_timezone = timezone.utc
        
        # Initialize all specialized analyzers
        self.experiment_analyzer = ExperimentAnalyzer(db_manager)
        self.device_analyzer = DeviceAnalyzer(db_manager)
        self.activity_analyzer = ActivityAnalyzer(db_manager)
        self.security_analyzer = SecurityAnalyzer(db_manager)
        self.time_manager = TimeWindowManager()
        self.pattern_analyzer = PatternAnalyzer(db_manager)
        self.data_formatter = AnalysisDataFormatter()
        
        logger.info("ModularDataAnalyzer initialized with all specialized analyzers")
    
    async def analyze_experiment_data(self, experiment_id: str) -> Dict[str, Any]:
        """
        Main entry point for analyzing experiment data
        
        Args:
            experiment_id: Experiment identifier
            
        Returns:
            Analysis results
        """
        logger.info(f"Starting modular analysis for experiment: {experiment_id}")
        
        try:
            # Use experiment analyzer for advanced analysis
            return await self.experiment_analyzer.analyze_experiment_data(experiment_id)
            
        except Exception as e:
            logger.error(f"Error in modular experiment analysis: {e}")
            raise
    
    async def analyze_device_comprehensive(self, device_id: str, experiment_id: str) -> Dict[str, Any]:
        """
        Comprehensive analysis for a single device
        Args:
            device_id: Device ID
            experiment_id: Experiment ID
            
        Returns:
            Comprehensive device analysis result
        """
        logger.info(f"Starting comprehensive device analysis for {device_id}")
        
        try:
            # Get device base data
            device_data = await self.device_analyzer.analyze_device_data(device_id, experiment_id)
            
            # If no traffic data, return base result
            if device_data.get('packet_flows', 0) == 0:
                return device_data
            
            # Get packet flows for further analysis
            packet_flows = await self._get_device_packet_flows(device_id)
            
            # Activity analysis
            time_windows = ['1h', '2h', '6h', '12h', '24h']
            activity_timeline = await self.activity_analyzer.generate_activity_timeline(
                device_id, experiment_id, packet_flows, time_windows
            )
            
            # Security analysis (scoring removed - not used by frontend)
            security_events = []
            
            for flow in packet_flows[:100]:  # Limit analysis to first 100 flows for performance
                timestamp = self.time_manager.safe_get_timestamp(flow)
                events = self.security_analyzer.detect_security_events_detailed(flow, timestamp)
                security_events.extend(events)
            
            # Pattern analysis
            connection_patterns = set()
            anomalies = []
            
            for flow in packet_flows[:100]:  # Limit analysis to first 100 flows for performance
                timestamp = self.time_manager.safe_get_timestamp(flow)
                pattern = self.pattern_analyzer.analyze_connection_pattern(flow)
                connection_patterns.add(pattern)
                
                anomaly = self.pattern_analyzer.detect_packet_anomalies(flow, timestamp)
                if anomaly:
                    anomalies.append(anomaly)
            
            # Integrate analysis results
            comprehensive_result = {
                **device_data,
                'activity_analysis': {
                    'timeline': activity_timeline,
                    'connection_patterns': list(connection_patterns),
                    'pattern_diversity': len(connection_patterns)
                },
                'security_analysis': {
                    'events': security_events,
                    'event_count': len(security_events),
                    'has_events': len(security_events) > 0
                },
                'anomaly_analysis': self.data_formatter.format_anomaly_data(anomalies),
                'analysis_metadata': {
                    'analyzer_type': 'modular_analyzer',
                    'analysis_timestamp': datetime.now(self.utc_timezone).isoformat(),
                    'packet_flows_analyzed': min(len(packet_flows), 100)
                }
            }
            
            return self.data_formatter.format_device_analysis_result(
                device_id, experiment_id, comprehensive_result
            )
            
        except Exception as e:
            logger.error(f"Error in comprehensive device analysis: {e}")
            raise
    
    async def _get_device_packet_flows(self, device_id: str) -> List[Dict[str, Any]]:
        """Get device packet flows"""
        query = """
        SELECT flow_id, packet_timestamp, src_ip, dst_ip, src_port, dst_port,
               protocol, packet_size, flow_direction, payload_size
        FROM packet_flows
        WHERE device_id = $1
        ORDER BY packet_timestamp DESC
        LIMIT 1000
        """
        return await self.db_manager.execute_query(query, (device_id,))
    
    async def get_analysis_summary(self, experiment_id: str) -> Dict[str, Any]:
        """Get experiment analysis summary"""
        try:
            # Get experiment devices
            devices = await self.experiment_analyzer._get_experiment_devices(experiment_id)
            
            summary = {
                'experiment_id': experiment_id,
                'total_devices': len(devices),
                'analysis_timestamp': datetime.now(self.utc_timezone).isoformat(),
                'devices_summary': []
            }
            
            # Generate brief summary for each device
            for device in devices[:10]:  # Limit to first 10 devices
                device_id = device['device_id']
                device_summary = await self.device_analyzer.analyze_device_data(device_id, experiment_id)
                
                summary['devices_summary'].append({
                    'device_id': device_id,
                    'device_name': device.get('device_name', 'Unknown'),
                    'packet_flows': device_summary.get('packet_flows', 0),
                    'status': 'active' if device_summary.get('packet_flows', 0) > 0 else 'inactive'
                })
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating analysis summary: {e}")
            raise
    
    def validate_analysis_modules(self) -> Dict[str, bool]:
        """Validate all analysis modules"""
        validation_results = {}
        
        try:
            # Test each analyzer module
            validation_results['experiment_analyzer'] = hasattr(self.experiment_analyzer, 'analyze_experiment_data')
            validation_results['device_analyzer'] = hasattr(self.device_analyzer, 'analyze_device_data')
            validation_results['activity_analyzer'] = hasattr(self.activity_analyzer, 'generate_activity_timeline')
            validation_results['security_analyzer'] = hasattr(self.security_analyzer, 'detect_security_events')
            validation_results['time_manager'] = hasattr(self.time_manager, 'safe_get_timestamp')
            validation_results['pattern_analyzer'] = hasattr(self.pattern_analyzer, 'analyze_connection_pattern')
            validation_results['data_formatter'] = hasattr(self.data_formatter, 'format_device_analysis_result')
            
            # Overall validation result
            validation_results['all_modules_valid'] = all(validation_results.values())
            
            logger.info(f"Module validation results: {validation_results}")
            return validation_results
            
        except Exception as e:
            logger.error(f"Error validating analysis modules: {e}")
            return {'validation_error': str(e), 'all_modules_valid': False}
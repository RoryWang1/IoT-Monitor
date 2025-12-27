"""
Device Network Topology API Endpoint
Handles device network connectivity and topology data retrieval with enhanced analysis
"""

import logging
import sys
import os
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Depends

# Setup unified path configuration
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
from config.unified_config_manager import UnifiedConfigManager

logger = logging.getLogger(__name__)

class ConfigurableNetworkTopologyAPI:
    """
    Configurable Network Topology API with all settings externalized
    """
    
    def __init__(self):
        self.config_manager = UnifiedConfigManager()
        self.config_key = "api_endpoints.network_topology"
    
    def get_default(self, key: str, fallback: Any = None) -> Any:
        """Get default configuration value"""
        return self.config_manager.get(f"{self.config_key}.defaults.{key}", fallback, 'network_topology.defaults')
    
    def get_query_limit(self, key: str, fallback: int = 50) -> int:
        """Get query limit configuration"""
        return self.config_manager.get(f"{self.config_key}.query_limits.{key}", fallback, 'network_topology.limits')
    
    def get_protocol_mapping(self, key: str, fallback: List = None) -> List:
        """Get protocol port mapping"""
        if fallback is None:
            fallback = []
        return self.config_manager.get(f"{self.config_key}.protocol_mapping.{key}", fallback, 'network_topology.protocols')
    
    def get_protocol_name(self, key: str, fallback: str = "Unknown") -> str:
        """Get protocol name mapping"""
        return self.config_manager.get(f"{self.config_key}.protocol_names.{key}", fallback, 'network_topology.protocols')
    
    def get_ip_filter(self, key: str, fallback: Any = None) -> Any:
        """Get IP filtering configuration"""
        return self.config_manager.get(f"{self.config_key}.ip_filtering.{key}", fallback, 'network_topology.filtering')
    
    def get_node_config(self, key: str, fallback: Any = None) -> Any:
        """Get node configuration"""
        return self.config_manager.get(f"{self.config_key}.node_configuration.{key}", fallback, 'network_topology.nodes')
    
    def get_node_color(self, key: str, fallback: str = "#6B7280") -> str:
        """Get node color configuration"""
        return self.config_manager.get(f"{self.config_key}.node_colors.{key}", fallback, 'network_topology.colors')
    
    def get_node_label(self, key: str, fallback: str = "Unknown") -> str:
        """Get node label configuration"""
        return self.config_manager.get(f"{self.config_key}.node_labels.{key}", fallback, 'network_topology.labels')
    
    def get_edge_config(self, key: str, fallback: Any = None) -> Any:
        """Get edge configuration"""
        return self.config_manager.get(f"{self.config_key}.edge_configuration.{key}", fallback, 'network_topology.edges')
    
    def get_error_message(self, key: str, **kwargs) -> str:
        """Get formatted error message from configuration"""
        message_template = self.config_manager.get(f"{self.config_key}.error_messages.{key}", 
                                                          f"Error: {key}", 'network_topology.errors')
        try:
            return message_template.format(**kwargs)
        except (KeyError, ValueError):
            return message_template
    
    def get_query_description(self, key: str, fallback: str = "") -> str:
        """Get query parameter description"""
        return self.config_manager.get(f"{self.config_key}.query_descriptions.{key}", fallback, 'network_topology.descriptions')
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled"""
        return self.config_manager.get(f"{self.config_key}.features.enable_{feature}", True, 'network_topology.features')
    
    def log_message(self, category: str, key: str, **kwargs):
        """Log a configurable message"""
        if self.is_feature_enabled('detailed_logging'):
            # Get the message directly from the log template
            templates = self.config_manager.get_log_templates()
            if 'api_endpoints' in templates and 'network_topology' in templates['api_endpoints']:
                message_template = templates['api_endpoints']['network_topology'].get(key, f"[Missing: {key}]")
                try:
                    message = message_template.format(**kwargs)
                    logger.info(message)
                except (KeyError, ValueError) as e:
                    logger.info(f"[Log template error: {e}] {message_template}")
            else:
                message = self.get_default('fallback_message_template', 
                                    "[Missing template] {category}.{key}: {kwargs}")
                logger.info(message.format(category=category, key=key, kwargs=kwargs))
    
    def identify_protocol(self, src_port: int, dst_port: int, app_protocol: str = None) -> str:
        """Configurable protocol identification"""
        if not self.is_feature_enabled('protocol_detection'):
            return self.get_protocol_name('tcp_fallback')
        
        # Check app_protocol first
        if app_protocol:
            app_lower = app_protocol.lower()
            if 'http' in app_lower:
                if dst_port in self.get_protocol_mapping('https_ports') or src_port in self.get_protocol_mapping('https_ports'):
                    return self.get_protocol_name('https_protocol')
                return self.get_protocol_name('http_protocol')
            elif 'dns' in app_lower:
                return self.get_protocol_name('dns_protocol')
            elif 'dhcp' in app_lower:
                return self.get_protocol_name('dhcp_protocol')
            elif 'ssdp' in app_lower:
                return self.get_protocol_name('upnp_protocol')
            else:
                return app_protocol.upper()
        
        # Port-based identification
        all_ports = [src_port, dst_port]
        
        if any(port in self.get_protocol_mapping('http_ports') for port in all_ports):
            return self.get_protocol_name('http_protocol')
        elif any(port in self.get_protocol_mapping('https_ports') for port in all_ports):
            return self.get_protocol_name('https_protocol')
        elif any(port in self.get_protocol_mapping('dns_ports') for port in all_ports):
            return self.get_protocol_name('dns_protocol')
        elif any(port in self.get_protocol_mapping('dhcp_ports') for port in all_ports):
            return self.get_protocol_name('dhcp_protocol')
        elif any(port in self.get_protocol_mapping('upnp_ports') for port in all_ports):
            return self.get_protocol_name('upnp_protocol')
        elif any(port in self.get_protocol_mapping('ssh_ports') for port in all_ports):
            return self.get_protocol_name('ssh_protocol')
        elif any(port in self.get_protocol_mapping('ftp_ports') for port in all_ports):
            return self.get_protocol_name('ftp_protocol')
        elif any(port in self.get_protocol_mapping('smtp_ports') for port in all_ports):
            return self.get_protocol_name('smtp_protocol')
        
        return self.get_protocol_name('tcp_fallback')
    
    def classify_node(self, ip: str, mac_address: str, vendor: str) -> Dict[str, Any]:
        """Configurable node classification"""
        if not self.is_feature_enabled('node_classification'):
            return {
                'type': 'unknown',
                'color': self.get_node_color('unknown'),
                'size': self.get_node_config('regular_device_size'),
                'label': f"Device {ip.split('.')[-1]}"
            }
        
        # Private network detection
        is_private = (ip.startswith('192.168.') or ip.startswith('10.') or ip.startswith('172.'))
        
        if is_private:
            # Gateway detection
            gateway_patterns = self.get_node_label('gateway_suffix_patterns')
            if any(ip.endswith(pattern) for pattern in gateway_patterns):
                return {
                    'type': 'gateway',
                    'color': self.get_node_color('gateway'),
                    'size': self.get_node_config('gateway_size'),
                    'label': self.get_node_label('gateway_label')
                }
            else:
                # Regular device
                device_label = f"{self.get_node_label('device_label_prefix')} {ip.split('.')[-1]}"
                return {
                    'type': 'device',
                    'color': self.get_node_color('device'),
                    'size': self.get_node_config('regular_device_size'),
                    'label': device_label
                }
        else:
            # External device
            external_label = f"{self.get_node_label('external_label_prefix')} {ip.split('.')[-1]}"
            return {
                'type': 'external',
                'color': self.get_node_color('external'),
                'size': self.get_node_config('external_device_size'),
                'label': external_label
            }
    
    def should_filter_ip(self, ip: str) -> bool:
        """Check if the IP should be filtered"""
        if not self.is_feature_enabled('ip_filtering'):
            return False
        
        # Check broadcast address
        exclude_ips = self.get_ip_filter('exclude_broadcast_ips')
        if exclude_ips and ip in exclude_ips:
            return True
        
        # Check multicast prefix
        exclude_prefixes = self.get_ip_filter('exclude_multicast_prefixes')
        if exclude_prefixes:
            for prefix in exclude_prefixes:
                if ip.startswith(prefix):
                    return True
        
        # Check invalid IP
        if ip in ['0.0.0.0', '255.255.255.255']:
            return True
        
        return False

# Create API instance
topology_api = ConfigurableNetworkTopologyAPI()

router = APIRouter()

# Setup unified path configuration
from ...common.path_config import setup_project_paths
setup_project_paths()

# Use the unified dependency injection
from ...common.dependencies import get_database_service_instance

# Academic Algorithm Implementation Module
class EdgeGravityOptimizer:
    """
    Edge Gravity algorithm optimizer
    """
    
    def __init__(self, config_api):
        import numpy as np
        self.np = np  # Store numpy reference for use in instance methods
        self.config_api = config_api
        self.learning_rate = 0.1  # Gradient descent learning rate
        
    def log_transform_normalization(self, packets, bytes_count, sessions):
        """
        Log transformation and normalization for heavy-tailed distributions
        """
        
        # Log transformation for heavy-tailed distributions
        log_packets = self.np.log1p(packets) if packets > 0 else 0
        log_bytes = self.np.log1p(bytes_count) if bytes_count > 0 else 0
        log_sessions = self.np.log1p(sessions) if sessions > 0 else 0
        
        return log_packets, log_bytes, log_sessions
    
    def calculate_network_centrality(self, edge_data, network_stats):
        """
        Calculate network centrality
        """
        
        packets = edge_data['packets']
        bytes_count = edge_data['bytes']
        sessions = edge_data['sessions']
        
        max_packets = network_stats['max_packets']
        max_bytes = network_stats['max_bytes']
        max_sessions = max([r.get('sessions', 0) for r in network_stats['all_results']])
        
        # 1. Degree centrality (based on connection strength)
        degree_centrality = (packets / max_packets) if max_packets > 0 else 0
        
        # 2. Closeness centrality (based on traffic size)
        closeness_centrality = (bytes_count / max_bytes) if max_bytes > 0 else 0
        
        # 3. Betweenness centrality (based on session diversity)
        betweenness_centrality = (sessions / max_sessions) if max_sessions > 0 else 0
        
        # 4. Comprehensive network centrality calculation
        centrality_score = (
            degree_centrality * 0.4 +       # Packet frequency weight
            closeness_centrality * 0.4 +    # Traffic size weight
            betweenness_centrality * 0.2     # Session diversity weight
        )
        
        return centrality_score
    
    def edge_gravity_algorithm(self, edge_data, network_stats):
        """
        Edge Gravity algorithm
        """
        
        packets = edge_data['packets']
        bytes_count = edge_data['bytes']
        sessions = edge_data['sessions']
        
        # 1. Log transformation and normalization
        log_packets, log_bytes, log_sessions = self.log_transform_normalization(
            packets, bytes_count, sessions
        )
        
        # 2. Network centrality calculation
        network_centrality = self.calculate_network_centrality(edge_data, network_stats)
        
        # 3. Edge Gravity core algorithm
        # Base weight - use log-standardized traffic data
        max_log_bytes = self.np.log1p(network_stats['max_bytes'])
        base_weight = log_bytes / max_log_bytes if max_log_bytes > 0 else 0
        
        # Path count factor - quantify the frequency of edges in all possible paths
        # Use session count as a proxy for path diversity
        path_count = sessions if sessions > 0 else 1
        path_frequency = self.np.sqrt(path_count)  # Avoid over-amplification
        
        # Structural importance factor - importance of edges in network topology
        structural_importance = network_centrality
        
        # 4. Edge Gravity strength calculation
        # gravity = base_weight × path_frequency × structural_importance
        edge_gravity = base_weight * path_frequency * structural_importance
        
        return edge_gravity, {
            'base_weight': round(base_weight, 4),
            'path_frequency': round(path_frequency, 4),
            'structural_importance': round(structural_importance, 4),
            'network_centrality': round(network_centrality, 4)
        }
    
    def graph_metric_gradient_descent(self, edge_gravity, edge_data, iteration_count):
        """
        Graph metric gradient descent optimization
        """
        
        packets = edge_data['packets']
        sessions = edge_data['sessions']
        
        # 1. Calculate graph metric derivative
        # Derivative based on connection degree and packet frequency
        degree_metric = self.np.log1p(packets) if packets > 0 else 0
        path_metric = self.np.log1p(sessions) if sessions > 0 else 0
        
        # 2. Gradient calculation
        # Use network topology features to calculate gradient
        gradient = degree_metric * path_metric * 0.01  # Scaling factor
        
        # 3. Gradient descent update
        # Adaptive learning_rate adjustment (prevent over-optimization)
        adaptive_lr = self.learning_rate / (1 + iteration_count * 0.01)
        
        # 4. Apply gradient descent optimization
        optimized_gravity = edge_gravity + (gradient * adaptive_lr)
        
        # 5. Network denoising - remove low-quality connections
        noise_threshold = 0.05
        if optimized_gravity < noise_threshold:
            optimized_gravity = 0.01  # Minimum retained value
        
        return optimized_gravity
    
    def bidirectional_communication_enhancement(self, edge_gravity, edge_data):
        """
        Bidirectional communication enhancement algorithm
        Based on Edge Gravity extension, identify important network paths
        """
        sessions = edge_data['sessions']
        packets = edge_data['packets']
        
        # Detect bidirectional communication pattern
        if sessions > 1 and packets > 10:  # Multiple sessions and substantial traffic
            # Bidirectional communication indicates an important network path
            bidirectional_factor = 1.0 + (self.np.log1p(sessions) * 0.1)
            enhanced_gravity = edge_gravity * bidirectional_factor
            
            return enhanced_gravity, True
        
        return edge_gravity, False
    
    def apply_scientific_optimization(self, edge_data, network_stats, iteration_count=0):
        """
        Apply complete algorithm flow
        """
        # 1. Edge Gravity algorithm
        edge_gravity, debug_info = self.edge_gravity_algorithm(edge_data, network_stats)
        
        # 2. Graph metric gradient descent optimization 
        optimized_gravity = self.graph_metric_gradient_descent(
            edge_gravity, edge_data, iteration_count
        )
        
        # 3. Bidirectional communication enhancement
        final_gravity, is_bidirectional = self.bidirectional_communication_enhancement(
            optimized_gravity, edge_data
        )
        
        # 4. Apply configuration limits
        min_strength = self.config_api.get_edge_config('min_strength', 0.01)
        max_strength = self.config_api.get_edge_config('max_strength', 1.0)
        
        normalized_strength = max(min_strength, min(max_strength, final_gravity))
        
        return normalized_strength, {
            **debug_info,
            'edge_gravity': round(edge_gravity, 4),
            'optimized_gravity': round(optimized_gravity, 4),
            'final_gravity': round(final_gravity, 4),
            'is_bidirectional': is_bidirectional,
            'normalized_strength': round(normalized_strength, 4)
        }
    
    def calculate_node_importance(self, node_data: Dict[str, Any]) -> float:
        """
        Node importance calculation algorithm
        Implements connection degree weight, traffic weight, and node type weight
        """
        # 1. Connection degree weight (0.6)
        connection_count = len(node_data.get('connections', []))
        connection_score = min(1.0, connection_count / 10)  # Normalize to [0,1]
        
        # 2. Traffic weight (0.4) 
        total_traffic = node_data.get('total_bytes', 0)
        traffic_score = min(1.0, self.np.log1p(total_traffic) / 20)  # Log standardization
        
        # 3. Node type weights from document
        node_type = node_data.get('type', 'device')
        type_weights = {
            'gateway': 1.5,     # Gateway highest weight
            'server': 1.3,      # Server higher weight
            'device': 1.0,      # Regular device standard weight
            'external': 0.8     # External node lower weight
        }
        
        # 4. Comprehensive scoring
        base_score = connection_score * 0.6 + traffic_score * 0.4
        type_weight = type_weights.get(node_type, 1.0)
        final_score = base_score * type_weight
        
        return min(1.0, final_score)
    
    def enhance_nodes_with_importance(self, nodes: List[Dict], edges: List[Dict]) -> List[Dict]:
        """
        Enhance nodes with importance scores and adjust visualization properties
        """
        # Calculate connections and traffic for each node
        node_stats = {}
        for node in nodes:
            node_id = node['id']
            node_stats[node_id] = {
                'connections': [],
                'total_bytes': 0,
                'type': node.get('type', 'device')
            }
        
        # Aggregate edge data for node statistics
        for edge in edges:
            source = edge['source']
            target = edge['target']
            bytes_count = edge.get('bytes', 0)
            
            if source in node_stats:
                node_stats[source]['connections'].append(target)
                node_stats[source]['total_bytes'] += bytes_count
                
            if target in node_stats:
                node_stats[target]['connections'].append(source)
                node_stats[target]['total_bytes'] += bytes_count
        
        # Calculate importance and enhance nodes
        enhanced_nodes = []
        for node in nodes:
            node_id = node['id']
            stats = node_stats.get(node_id, {'connections': [], 'total_bytes': 0, 'type': 'device'})
            
            # Calculate importance score using document algorithm
            importance_score = self.calculate_node_importance(stats)
            
            # Adjust node size based on importance
            base_size = node.get('size', 25)
            importance_multiplier = 0.5 + (importance_score * 1.5)  # Range: 0.5 to 2.0
            adjusted_size = int(base_size * importance_multiplier)
            
            # Create enhanced node
            enhanced_node = {
                **node,
                'importance_score': round(importance_score, 3),
                'connection_count': len(stats['connections']),
                'total_traffic': stats['total_bytes'],
                'size': max(15, min(60, adjusted_size)),  # Ensure reasonable size bounds
                'enhanced_by_algorithm': True
            }
            
            enhanced_nodes.append(enhanced_node)
        
        return enhanced_nodes

@router.get("/{device_id}/network-topology", response_model=Dict[str, Any])
async def get_device_network_topology(
    device_id: str, 
    background_tasks: BackgroundTasks,
    time_window: str = Query(
        default=topology_api.get_default('time_window'),
        alias="time_window", 
        description=topology_api.get_query_description('time_window_description')
    ),
    experiment_id: str = Query(
        default=None, 
        alias="experiment_id", 
        description=topology_api.get_query_description('experiment_id_description')
    ),
    database_service = Depends(get_database_service_instance)
):
    """
    Retrieve network topology for a specific device with configurable analysis
    """
    try:
        topology_api.log_message('topology', 'api_called', 
                                device_id=device_id, time_window=time_window, experiment_id=experiment_id)
        
        db_manager = database_service.db_manager
        
        # Get the device basic information
        device_query = "SELECT device_name, device_type, mac_address, ip_address, manufacturer FROM devices WHERE device_id = $1"
        device_params = [device_id]
        if experiment_id:
            device_query += " AND experiment_id = $2"
            device_params.append(experiment_id)
        
        device_result = await db_manager.execute_query(device_query, device_params)
        if not device_result:
            raise HTTPException(
                status_code=404, 
                detail=topology_api.get_error_message('device_not_found', device_id=device_id)
            )
        
        device_info = device_result[0]
        device_mac = device_info['mac_address']
        device_ip = device_info['ip_address']
        
        # Use device resolution service to get enhanced device information
        from database.services.device_resolution_service import DeviceResolutionService
        resolution_service = DeviceResolutionService(db_manager)
        
        # Get enhanced device information if MAC address is available
        if device_mac:
            try:
                enhanced_device_info = await resolution_service.resolve_device_info(device_mac)
                device_name = enhanced_device_info.get('resolvedName', device_info['device_name'])
                device_type = enhanced_device_info.get('resolvedType', device_info['device_type'])
                device_manufacturer = enhanced_device_info.get('resolvedVendor', device_info['manufacturer'])
            except Exception as e:
                logger.error(f"Error calling device resolution service: {e}")
                device_name = device_info['device_name']
                device_type = device_info['device_type']
                device_manufacturer = device_info['manufacturer']
        else:
            device_name = device_info['device_name']
            device_type = device_info['device_type']
            device_manufacturer = device_info['manufacturer']
        
        # Apply fallback values if still empty
        device_name = device_name or f"{topology_api.get_default('unknown_device_name')}_{device_id[:8]}"
        device_type = device_type or topology_api.get_default('fallback_device_type')
        device_manufacturer = device_manufacturer or topology_api.get_default('unknown_vendor')
        
        # Get the time window boundaries
        from database.services.timezone_time_window_service import timezone_time_window_service
        start_time, end_time = await timezone_time_window_service.get_timezone_aware_time_bounds(
            experiment_id, time_window, db_manager
        )
        
        # IP-MAC mapping build
        ip_to_mac_map = {}
        
        # 1. Get the mapping from the devices table
        devices_mapping_query = "SELECT ip_address, mac_address FROM devices WHERE ip_address IS NOT NULL AND mac_address IS NOT NULL"
        devices_mapping_params = []
        if experiment_id:
            devices_mapping_query += " AND experiment_id = $1"
            devices_mapping_params.append(experiment_id)
        
        devices_mapping_result = await db_manager.execute_query(devices_mapping_query, devices_mapping_params)
        for row in devices_mapping_result:
            if row['ip_address'] and row['mac_address']:
                ip_to_mac_map[str(row['ip_address'])] = row['mac_address']
        
        # 2. Get the mapping from the packet_flows
        if topology_api.is_feature_enabled('mac_resolution'):
            mac_mapping_query = """
            SELECT DISTINCT 
                src_ip, src_mac,
                dst_ip, dst_mac
            FROM packet_flows 
            WHERE device_id = $1 
            AND packet_timestamp >= $2 
            AND packet_timestamp <= $3
            AND (src_mac IS NOT NULL OR dst_mac IS NOT NULL)
            AND src_ip IS NOT NULL
            AND dst_ip IS NOT NULL
            """
            
            # Add IP filtering based on configuration
            exclude_ips = topology_api.get_ip_filter('exclude_broadcast_ips')
            for ip in exclude_ips:
                mac_mapping_query += f" AND src_ip != '{ip}' AND dst_ip != '{ip}'"
            
            mac_mapping_query += " AND LOWER(COALESCE(src_mac, '')) != 'ff:ff:ff:ff:ff:ff'"
            mac_mapping_query += " AND LOWER(COALESCE(dst_mac, '')) != 'ff:ff:ff:ff:ff:ff'"
            
            mac_mapping_params = [device_id, start_time, end_time]
            if experiment_id:
                mac_mapping_query += " AND experiment_id = $4"
                mac_mapping_params.append(experiment_id)
            
            mac_mapping_result = await db_manager.execute_query(mac_mapping_query, mac_mapping_params)
            
            for row in mac_mapping_result:
                if row['src_ip'] and row['src_mac'] and str(row['src_ip']) not in ip_to_mac_map:
                    ip_to_mac_map[str(row['src_ip'])] = row['src_mac']
                if row['dst_ip'] and row['dst_mac'] and str(row['dst_ip']) not in ip_to_mac_map:
                    ip_to_mac_map[str(row['dst_ip'])] = row['dst_mac']
        
        topology_api.log_message('topology', 'ip_mac_mapping_built', count=len(ip_to_mac_map))
        
        # Build the network topology query
        topology_query = f"""
        WITH connection_aggregates AS (
            SELECT 
                LEAST(src_ip, dst_ip) as node_a,
                GREATEST(src_ip, dst_ip) as node_b,
                COUNT(*) as packets,
                SUM(packet_size) as bytes,
                COUNT(DISTINCT flow_hash) as sessions,
                MIN(packet_timestamp) as first_seen,
                MAX(packet_timestamp) as last_seen,
                -- Get the most common protocol and port for this IP pair
                MODE() WITHIN GROUP (ORDER BY app_protocol) as app_protocol,
                MODE() WITHIN GROUP (ORDER BY protocol) as protocol,
                MODE() WITHIN GROUP (ORDER BY src_port) as src_port,
                MODE() WITHIN GROUP (ORDER BY dst_port) as dst_port
            FROM packet_flows 
            WHERE device_id = $1
            AND packet_timestamp >= $2 
            AND packet_timestamp <= $3
            AND src_ip IS NOT NULL 
            AND dst_ip IS NOT NULL
        """
        
        # Add configurable IP filtering
        if topology_api.get_ip_filter('exclude_self_connections'):
            topology_query += " AND src_ip != dst_ip"
        
        exclude_ips = topology_api.get_ip_filter('exclude_broadcast_ips')
        for ip in exclude_ips:
            topology_query += f" AND src_ip != '{ip}' AND dst_ip != '{ip}'"
        
        exclude_prefixes = topology_api.get_ip_filter('exclude_multicast_prefixes')
        for prefix in exclude_prefixes:
            topology_query += f" AND NOT (src_ip::text LIKE '{prefix}%' OR dst_ip::text LIKE '{prefix}%')"
        
        params = [device_id, start_time, end_time]
        if experiment_id:
            topology_query += " AND experiment_id = $4"
            params.append(experiment_id)
        
        topology_query += f"""
            GROUP BY node_a, node_b
        )
        SELECT 
            node_a as src_ip,
            node_b as dst_ip,
            app_protocol,
            protocol,
            src_port,
            dst_port,
            packets,
            bytes,
            sessions,
            first_seen,
            last_seen
        FROM connection_aggregates
        ORDER BY bytes DESC
        LIMIT {topology_api.get_query_limit('max_connections')}
        """
        
        topology_api.log_message('topology', 'executing_query', params=str(params))
        result = await db_manager.execute_query(topology_query, params)
        
        # Device resolution service
        resolution_cache = {}
        if topology_api.is_feature_enabled('mac_resolution'):
            from database.services.device_resolution_service import DeviceResolutionService
            resolution_service = DeviceResolutionService(db_manager)
            
            mac_addresses_to_resolve = []
            if device_mac:
                mac_addresses_to_resolve.append(device_mac)
            
            for clean_ip, mac in ip_to_mac_map.items():
                if mac and mac != topology_api.get_default('fallback_mac_address') and mac not in mac_addresses_to_resolve:
                    mac_addresses_to_resolve.append(mac)
            
            if mac_addresses_to_resolve:
                topology_api.log_message('topology', 'resolving_mac_addresses', count=len(mac_addresses_to_resolve))
                resolution_cache = await resolution_service.bulk_resolve_devices(mac_addresses_to_resolve)
        


        def get_device_info_from_mac(mac_address):
            """Get the device information"""
            if not mac_address or mac_address == topology_api.get_default('fallback_mac_address'):
                return {
                    'vendor': topology_api.get_default('unknown_vendor'),
                    'name': topology_api.get_default('unknown_device_name'),
                    'type': topology_api.get_default('fallback_device_type'),
                    'source': 'none'
                }
            
            if mac_address in resolution_cache:
                resolution = resolution_cache[mac_address]
                return {
                    'vendor': resolution.get('resolvedVendor', topology_api.get_default('unknown_vendor')),
                    'name': resolution.get('resolvedName', topology_api.get_default('unknown_device_name')),
                    'type': resolution.get('resolvedType', topology_api.get_default('fallback_device_type')),
                    'source': resolution.get('source', 'none')
                }
            else:
                return {
                    'vendor': topology_api.get_default('unknown_vendor'),
                    'name': topology_api.get_default('unknown_device_name'),
                    'type': topology_api.get_default('fallback_device_type'),
                    'source': 'none'
                }
        
        async def get_intelligent_device_info_for_ip(ip_address, connection_data=None):
            """Intelligent device information resolution using database reference data and service recognition"""
            # Default fallback info
            device_info = {
                'vendor': topology_api.get_default('unknown_vendor'),
                'name': topology_api.get_default('unknown_device_name'), 
                'type': topology_api.get_default('fallback_device_type'),
                'source': 'database_analysis'
            }
            
            try:
                # Priority 1: Check if IP exists in known_devices table (by IP address)
                ip_device_query = """
                SELECT device_name, device_type, vendor 
                FROM known_devices 
                WHERE device_name ILIKE '%' || $1 || '%' OR vendor ILIKE '%' || $1 || '%'
                LIMIT 1
                """
                ip_device_result = await db_manager.execute_query(ip_device_query, (ip_address,))
                
                if ip_device_result:
                    device_data = ip_device_result[0]
                    device_info.update({
                        'vendor': device_data['vendor'],
                        'name': device_data['device_name'],
                        'type': device_data['device_type'],
                        'source': 'known_device_ip'
                    })
                    return device_info
                
                # Priority 2: Use IP geolocation data to enhance information
                location_result = await db_manager.execute_query(
                    'SELECT * FROM lookup_ip_location($1)', (ip_address,)
                )
                
                if location_result and location_result[0]['country_name']:
                    location_data = location_result[0]
                    country = location_data['country_name']
                    country_code = location_data['country_code']
                    
                    # Enhanced geolocation-based inference
                    if country_code == 'US':
                        # US-based services - check for major providers
                        if ip_address.startswith(('216.58.', '142.250.', '172.217.', '74.125.')):
                            device_info.update({
                                'vendor': 'Google LLC',
                                'name': f'Google Service ({country})',
                                'type': 'cloud_service',
                                'source': 'geolocation_analysis'
                            })
                        elif ip_address.startswith(('52.', '54.', '3.', '13.224.')):
                            device_info.update({
                                'vendor': 'Amazon Web Services',
                                'name': f'AWS Service ({country})',
                                'type': 'cloud_service',
                                'source': 'geolocation_analysis'
                            })
                        elif ip_address.startswith(('40.', '13.', '104.', '52.')):
                            device_info.update({
                                'vendor': 'Microsoft Corporation',
                                'name': f'Azure Service ({country})',
                                'type': 'cloud_service',
                                'source': 'geolocation_analysis'
                            })
                        elif ip_address in ['8.8.8.8', '8.8.4.4']:
                            device_info.update({
                                'vendor': 'Google LLC',
                                'name': f'Google DNS ({country})',
                                'type': 'dns_service',
                                'source': 'geolocation_analysis'
                            })
                        elif ip_address in ['1.1.1.1', '1.0.0.1']:
                            device_info.update({
                                'vendor': 'Cloudflare Inc',
                                'name': f'Cloudflare DNS ({country})',
                                'type': 'dns_service',
                                'source': 'geolocation_analysis'
                            })
                        else:
                            device_info.update({
                                'vendor': f'{country} Service Provider',
                                'name': f'{country} Server ({ip_address})',
                                'type': 'external_service',
                                'source': 'geolocation_analysis'
                            })
                    else:
                        # International services
                        device_info.update({
                            'vendor': f'{country} Service Provider',
                            'name': f'{country} Server ({ip_address})',
                            'type': 'external_service',
                            'source': 'geolocation_analysis'
                        })
                
                # Priority 3: Private network analysis
                elif ip_address.startswith(('192.168.', '10.', '172.')):
                    if ip_address.endswith('.1'):
                        device_info.update({
                            'vendor': 'Network Infrastructure',
                            'name': f'Gateway ({ip_address})',
                            'type': 'gateway',
                            'source': 'network_analysis'
                        })
                    else:
                        device_info.update({
                            'vendor': 'Local Network Device',
                            'name': f'Local Device ({ip_address})',
                            'type': 'device',
                            'source': 'network_analysis'
                        })
                
                # Priority 4: Connection pattern analysis
                elif connection_data:
                    ports = connection_data.get('ports', [])
                    protocols = connection_data.get('protocols', [])
                    meaningful_ports = [p for p in ports if p > 0 and p < 49152]
                    
                    if 80 in meaningful_ports or 443 in meaningful_ports:
                        device_info.update({
                            'vendor': 'Web Service Provider',
                            'name': f'Web Server ({ip_address})',
                            'type': 'web_service',
                            'source': 'port_analysis'
                        })
                    elif 53 in meaningful_ports:
                        device_info.update({
                            'vendor': 'DNS Service Provider',
                            'name': f'DNS Server ({ip_address})',
                            'type': 'dns_service',
                            'source': 'port_analysis'
                        })
                    elif any(p in meaningful_ports for p in [25, 587, 993, 995]):
                        device_info.update({
                            'vendor': 'Email Service Provider',
                            'name': f'Email Server ({ip_address})',
                            'type': 'email_service',
                            'source': 'port_analysis'
                        })
                    else:
                        device_info.update({
                            'vendor': 'External Service',
                            'name': f'External Server ({ip_address})',
                            'type': 'external_service',
                            'source': 'port_analysis'
                        })
                
                # Final fallback
                else:
                    device_info.update({
                        'vendor': 'External Service',
                        'name': f'External Host ({ip_address})',
                        'type': 'external_service',
                        'source': 'fallback'
                    })
                    
            except Exception as e:
                logger.warning(f"Error in intelligent device info resolution for {ip_address}: {e}")
                # Keep default fallback values
                pass
            
            return device_info
        
        # Build the nodes and edges
        nodes = {}
        edges = []
        
        # Main device node
        if device_ip:
            # Use the already resolved device information
            main_label = f"{device_name}"
            if device_manufacturer != topology_api.get_default('unknown_vendor'):
                main_label += f" ({device_manufacturer})"
            
            nodes[device_ip] = {
                'id': device_ip,
                'label': main_label,
                'resolvedLabel': main_label,
                'resolvedVendor': device_manufacturer,
                'resolvedType': device_type,
                'resolutionSource': 'known_device' if device_mac else 'none',
                'type': device_type,
                'ip': device_ip,
                'macAddress': device_mac or topology_api.get_default('fallback_mac_address'),
                'size': topology_api.get_node_config('main_device_size'),
                'color': topology_api.get_node_color('main_device')
            }
        
        if not result:
            return {
                "nodes": list(nodes.values()),
                "edges": [],
                "metadata": {
                    "device_id": device_id,
                    "time_window": time_window,
                    "total_nodes": len(nodes),
                    "total_edges": 0
                }
            }
        
        # Process the connection data for Edge Gravity algorithm
        max_bytes = max([row['bytes'] or 0 for row in result])
        max_packets = max([row['packets'] or 0 for row in result])
        
        # Prepare data for Edge Gravity optimization
        network_stats = {
            'max_bytes': max_bytes,
            'max_packets': max_packets,
            'all_results': result # Pass all results for network_stats calculation
        }
        
        # Collect connection info for smart IP analysis
        connection_data_by_ip = {}
        for row in result:
            src_ip = str(row['src_ip'])
            dst_ip = str(row['dst_ip'])
            src_port = row['src_port'] or 0
            dst_port = row['dst_port'] or 0
            protocol = row['protocol'] or ''
            
            # Collect connection info for each IP
            for ip in [src_ip, dst_ip]:
                if ip not in connection_data_by_ip:
                    connection_data_by_ip[ip] = {'ports': set(), 'protocols': set()}
                connection_data_by_ip[ip]['ports'].update([src_port, dst_port])
                connection_data_by_ip[ip]['protocols'].add(protocol)
        
        for row in result:
            src_ip = str(row['src_ip'])
            dst_ip = str(row['dst_ip'])
            
            # Use the configurable protocol identification
            protocol = topology_api.identify_protocol(
                row['src_port'] or 0, 
                row['dst_port'] or 0, 
                row['app_protocol']
            )
            
            packets = row['packets'] or 0
            bytes_count = row['bytes'] or 0
            sessions = row['sessions'] or 0
            
            # Add the nodes
            for ip in [src_ip, dst_ip]:
                if ip not in nodes and not topology_api.should_filter_ip(ip):
                    clean_ip = str(ip).replace('/32', '') if '/32' in str(ip) else str(ip)
                    mac_address = ip_to_mac_map.get(clean_ip, topology_api.get_default('fallback_mac_address'))
                    
                    # Direct MAC lookup
                    if (mac_address == topology_api.get_default('fallback_mac_address') 
                        and topology_api.is_feature_enabled('direct_mac_lookup')):
                        topology_api.log_message('topology', 'direct_mac_lookup', ip=clean_ip)
                        direct_mac_query = """
                        SELECT src_mac, dst_mac 
                        FROM packet_flows 
                        WHERE (src_ip = $1 OR dst_ip = $1) 
                        AND (src_mac IS NOT NULL OR dst_mac IS NOT NULL)
                        """
                        direct_params = [clean_ip]
                        if experiment_id:
                            direct_mac_query += " AND experiment_id = $2"
                            direct_params.append(experiment_id)
                        direct_mac_query += f" LIMIT {topology_api.get_query_limit('direct_mac_lookup_limit')}"
                        
                        try:
                            direct_result = await db_manager.execute_query(direct_mac_query, direct_params)
                            if direct_result:
                                mac_address = (direct_result[0]['src_mac'] or 
                                             direct_result[0]['dst_mac'] or 
                                             topology_api.get_default('fallback_mac_address'))
                                topology_api.log_message('topology', 'found_mac_direct', ip=clean_ip, mac_address=mac_address)
                        except Exception as e:
                            topology_api.log_message('topology', 'direct_mac_lookup_failed', ip=clean_ip, error=str(e))
                    
                    # Device information from MAC address resolution first
                    device_info = get_device_info_from_mac(mac_address)
                    vendor = device_info['vendor']
                    resolved_name = device_info['name']
                    resolved_type = device_info['type']
                    resolution_source = device_info['source']
                    
                    # Use intelligent database-driven analysis for unknown devices or fallback MAC addresses
                    use_intelligent_analysis = (
                        mac_address == topology_api.get_default('fallback_mac_address') or
                        (vendor == topology_api.get_default('unknown_vendor') and 
                         resolved_name == topology_api.get_default('unknown_device_name')) or
                        resolution_source in ['none', 'fallback']
                    )
                    
                    if use_intelligent_analysis:
                        # This node lacks proper identification - use intelligent database analysis
                        connection_info = {
                            'ports': list(connection_data_by_ip.get(ip, {}).get('ports', [])),
                            'protocols': list(connection_data_by_ip.get(ip, {}).get('protocols', []))
                        }
                        intelligent_info = await get_intelligent_device_info_for_ip(clean_ip, connection_info)
                        
                        # Only override if intelligent analysis provides better information
                        if intelligent_info['vendor'] != topology_api.get_default('unknown_vendor'):
                            vendor = intelligent_info['vendor']
                            resolved_name = intelligent_info['name']
                            resolved_type = intelligent_info['type']
                            resolution_source = intelligent_info['source']
                            
                            topology_api.log_message('topology', 'intelligent_analysis_applied', 
                                                   ip=clean_ip, vendor=vendor, type=resolved_type, source=resolution_source)
                    
                    node_info = topology_api.classify_node(ip, mac_address, vendor)
                    
                    # Use resolved device name if available, otherwise use classified label
                    if resolved_name != topology_api.get_default('unknown_device_name'):
                        # Use resolved name from known_devices, vendor_patterns, or IP analysis
                        if vendor != topology_api.get_default('unknown_vendor'):
                            node_label = f"{resolved_name}" if 'Service' in resolved_name or 'Server' in resolved_name else f"{resolved_name} ({vendor})"
                        else:
                            node_label = resolved_name
                        node_type = resolved_type
                    else:
                        # Fallback to classified label
                        if vendor != topology_api.get_default('unknown_vendor'):
                            node_label = f"{node_info['label']} ({vendor})"
                        else:
                            node_label = node_info['label']
                        resolution_source = 'network_analysis'
                        node_type = node_info['type']
                    
                    nodes[ip] = {
                        'id': ip,
                        'label': node_label,
                        'resolvedLabel': node_label,
                        'resolvedVendor': vendor,
                        'resolvedType': node_type,
                        'resolutionSource': resolution_source,
                        'type': node_type,
                        'ip': ip,
                        'macAddress': mac_address,
                        'size': node_info['size'],
                        'color': node_info['color']
                    }
                    
                    topology_api.log_message('topology', 'node_created', 
                                           ip=ip, type=node_info['type'], mac_address=mac_address)
            
            # Create the edges with optimized connection strength calculation
            if topology_api.is_feature_enabled('edge_optimization'):
                # Initialize Edge Gravity Optimizer
                edge_optimizer = EdgeGravityOptimizer(topology_api)
                
                # Apply the scientific optimization
                optimized_strength, debug_info = edge_optimizer.apply_scientific_optimization(
                    {
                        'src_ip': src_ip,
                        'dst_ip': dst_ip,
                        'protocol': protocol,
                        'packets': packets,
                        'bytes': bytes_count,
                        'sessions': sessions
                    },
                    network_stats
                )
                
                # Calculate weight and strength for visualization
                min_weight = topology_api.get_edge_config('min_weight', 1)
                max_weight = topology_api.get_edge_config('max_weight', 10)
                
                # Convert optimized strength to weight for visualization
                weight = min(max_weight, max(min_weight, int(optimized_strength * max_weight)))
                strength = round(optimized_strength, 3)
                
                # Add Edge Gravity debug information
                edge_gravity_debug = {
                    **debug_info,
                    'final_strength': strength,
                    'visualization_weight': weight
                }
                
                # Record Edge Gravity calculation log
                topology_api.log_message('topology', 'edge_gravity_calculated', 
                                       src_ip=src_ip, dst_ip=dst_ip, 
                                       strength=strength, debug=edge_gravity_debug)
            else:
                weight = 1
                strength = 0.5
            
            edge = {
                'id': f"edge-{src_ip}-{dst_ip}-{protocol}",
                'source': src_ip,
                'target': dst_ip,
                'protocol': protocol,
                'packets': packets,
                'bytes': bytes_count,
                'sessions': sessions,
                'weight': weight,
                'strength': round(strength, 3),  # Keep precision for frontend display
                'firstSeen': row['first_seen'].isoformat() if row['first_seen'] else None,
                'lastSeen': row['last_seen'].isoformat() if row['last_seen'] else None
            }
            
            edges.append(edge)
            topology_api.log_message('topology', 'edge_created', 
                                    src_ip=src_ip, dst_ip=dst_ip, protocol=protocol, bytes=bytes_count)
        
        # Limit the number of nodes and edges
        max_nodes = topology_api.get_query_limit('max_nodes')
        max_edges = topology_api.get_query_limit('max_edges')
        
        # Use the new Edge Gravity algorithm to improve visualization quality
        
        # 1. Node classification and priority sorting
        priority_nodes = []  # High priority nodes (real devices)
        important_nodes = []  # Important external nodes (high strength connections)
        secondary_nodes = []  # Secondary nodes (low strength connections)
        
        # Calculate the maximum connection strength for each node
        node_max_strength = {}
        node_connection_count = {}
        node_total_bytes = {}
        
        for edge in edges:
            for node_id in [edge['source'], edge['target']]:
                if node_id not in node_max_strength:
                    node_max_strength[node_id] = 0
                    node_connection_count[node_id] = 0
                    node_total_bytes[node_id] = 0
                
                node_max_strength[node_id] = max(node_max_strength[node_id], edge['strength'])
                node_connection_count[node_id] += 1
                node_total_bytes[node_id] += edge['bytes']
        
        # 2. Node classification and priority sorting
        final_nodes = list(nodes.values())
        for node in final_nodes:
            node_id = node['id']
            max_strength = node_max_strength.get(node_id, 0)
            connection_count = node_connection_count.get(node_id, 0)
            total_bytes = node_total_bytes.get(node_id, 0)
            
            # Calculate comprehensive importance score 
            import numpy as np
            strength_factor = max_strength
            connectivity_factor = np.log1p(connection_count)
            traffic_factor = np.log1p(total_bytes) / 20  # Scaling traffic factor
            
            importance_score = strength_factor * 0.5 + connectivity_factor * 0.3 + traffic_factor * 0.2
            
            # Node classification
            is_real_device = (node.get('resolutionSource') == 'known_device' or 
                            node.get('type') in ['smart_tv', 'smartphone', 'device'])
            is_local_device = (node['ip'] and str(node['ip']).startswith('10.13.0.'))
            
            if is_real_device or is_local_device:
                # Real device or local device - highest priority
                priority_nodes.append({**node, 'importance_score': importance_score, 'category': 'real_device'})
            elif importance_score >= 0.8:  # High importance threshold
                # Important external node - high strength connection
                important_nodes.append({**node, 'importance_score': importance_score, 'category': 'important_external'})
            elif importance_score >= 0.3:  # Medium importance threshold
                # Medium importance external node
                secondary_nodes.append({**node, 'importance_score': importance_score, 'category': 'secondary_external'})
            else:
                # Low importance node - possibly filtered out
                secondary_nodes.append({**node, 'importance_score': importance_score, 'category': 'low_priority'})
        
        # 3. Intelligent node selection strategy
        # Sort by importance
        priority_nodes.sort(key=lambda x: x['importance_score'], reverse=True)
        important_nodes.sort(key=lambda x: x['importance_score'], reverse=True)
        secondary_nodes.sort(key=lambda x: x['importance_score'], reverse=True)
        
        # Adaptive node number limit
        total_available_slots = min(max_nodes, 25)  # Limit maximum display nodes
        
        # Allocate node slots
        priority_slots = min(len(priority_nodes), 8)  # Real devices are prioritized to ensure display
        important_slots = min(len(important_nodes), 12)  # Important external nodes
        remaining_slots = max(0, total_available_slots - priority_slots - important_slots)
        secondary_slots = min(len(secondary_nodes), remaining_slots)
        
        # 4. Build the final node list
        filtered_nodes = (
            priority_nodes[:priority_slots] +
            important_nodes[:important_slots] +
            secondary_nodes[:secondary_slots]
        )
        
        # 5. Filter edges - only keep edges related to displayed nodes
        displayed_node_ids = {node['id'] for node in filtered_nodes}
        filtered_edges = [
            edge for edge in edges 
            if edge['source'] in displayed_node_ids and edge['target'] in displayed_node_ids
        ]
        
        # Sort edges by strength, keeping the most important connections
        filtered_edges.sort(key=lambda x: x['strength'], reverse=True)
        filtered_edges = filtered_edges[:min(len(filtered_edges), max_edges)]
        
        # 6. Add visualization enhancement information to the frontend
        topology_response = {
            "nodes": filtered_nodes,
            "edges": filtered_edges,
            "metadata": {
                "device_id": device_id,
                "time_window": time_window,
                "total_nodes": len(filtered_nodes),
                "total_edges": len(filtered_edges),
                "ip_mac_mappings": len(ip_to_mac_map),
                # Visualization enhancement information
                "node_categories": {
                    "real_devices": len(priority_nodes),
                    "important_external": len(important_nodes),
                    "secondary_external": len(secondary_nodes),
                    "displayed_real_devices": priority_slots,
                    "displayed_important": important_slots,
                    "displayed_secondary": secondary_slots
                },
                "filtering_applied": True,
                "edge_gravity_enabled": topology_api.is_feature_enabled('edge_optimization'),
                "max_strength": max([edge['strength'] for edge in filtered_edges]) if filtered_edges else 0,
                "min_strength": min([edge['strength'] for edge in filtered_edges]) if filtered_edges else 0
            }
        }
        
        topology_api.log_message('topology', 'topology_retrieved', 
                                device_id=device_id, nodes=len(filtered_nodes), edges=len(filtered_edges))
        
        # Broadcast removed to prevent infinite loop with frontend re-fetching
        # background_tasks.add_task(_trigger_network_topology_broadcast, device_id, experiment_id, topology_response)
        
        return topology_response
        
    except HTTPException:
        raise
    except Exception as e:
        topology_api.log_message('topology', 'error_api', error=str(e))
        raise HTTPException(
            status_code=500,
            detail=topology_api.get_error_message('failed_retrieve_topology', device_id=device_id, error=str(e))
        )

# Background task for WebSocket broadcast
async def _trigger_network_topology_broadcast(device_id: str, experiment_id: str, response_data: dict):
    """Trigger WebSocket broadcast when network topology is accessed"""
    try:
        # Import broadcast service
        from ...services.broadcast_service import broadcast_service
        
        # Trigger broadcast for network topology update
        await broadcast_service.emit_event(f"devices.{device_id}.network-topology", response_data)
        
    except Exception as e:
        # Silent error handling for broadcast - don't affect API response
        logger.debug(f"Failed to trigger network topology broadcast for {device_id}: {e}") 
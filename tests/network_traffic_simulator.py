"""
Network Traffic Simulator (Scientific Model-Based)
==================================================

This module provides a rigorous framework for simulating IoT network traffic based on established
statistical distributions and graph theory models. It is designed to evaluate the performance
of the EdgeGravity monitoring system under controlled, reproducible conditions.

Models Implemented:
1. Topology: Stochastic Block Model (SBM) - Simulating clustered subnets [Holland et al., 1983].
2. Traffic Volume: Zipfian Distribution (Power Law) - Simulating heavy-tailed protocol usage [Adamic et al., 2002].
3. Temporal Dynamics: Non-homogeneous Poisson Process (NHPP) - Simulating diurnal patterns and bursty arrivals.

Usage:
    >>> simulator = NetworkTrafficSimulator(seed=42)
    >>> nodes, edges, graph = simulator.synthesis_stochastic_block_model()
"""

import numpy as np
import networkx as nx
import random
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Any

class SimulationConfig:
    """
    Configuration parameters for the simulation environment.
    """
    def __init__(self, seed: int = None):
        self.seed = seed
        if seed is not None:
             np.random.seed(seed)
             random.seed(seed)

class NetworkTrafficSimulator:
    """
    A scientific simulation engine for generating synthetic network telemetry.
    """
    
    def __init__(self, config: SimulationConfig = None):
        self.config = config or SimulationConfig()

    def synthesis_stochastic_block_model(self, n_nodes=100, n_clusters=5, p_intra=0.3, p_inter=0.05) -> Tuple[List[Dict], List[Dict], nx.Graph]:
        """
        Synthesize a network topology using the Stochastic Block Model (SBM).
        
        The SBM is a generative graph model that produces communities (clusters),
        mimicking the subnet/VLAN structure of enterprise IoT deployments.
        
        Args:
            n_nodes: Total number of devices to simulate.
            n_clusters: Number of distinct subnets/communities.
            p_intra: Probability of edge creation within a cluster (High coupling).
            p_inter: Probability of edge creation between clusters (Low coupling).
            
        Returns:
            Tuple containing:
            - Node list (metadata)
            - Edge list (telemetry with weight calculation)
            - NetworkX graph object (Ground truth)
        """
        print(f"[SIMULATION] Initializing Stochastic Block Model SBM(N={n_nodes}, k={n_clusters})...")
        
        sizes = [n_nodes // n_clusters] * n_clusters
        # Handle remainder
        sizes[-1] += n_nodes % n_clusters
        
        # Stochastic Block Model Matrix
        probs = np.full((n_clusters, n_clusters), p_inter)
        np.fill_diagonal(probs, p_intra)
        
        # Note: using config seed for academic integrity (Monte Carlo support)
        G = nx.stochastic_block_model(sizes, probs, seed=self.config.seed)
        
        # Convert to format expected by EdgeGravity
        # Nodes: [{'id': 'ip_x', 'type': 'device'}, ...]
        # Edges: [{'source': 'ip_a', 'target': 'ip_b', 'packets': 100, 'bytes': 5000, 'sessions': 5}]
        
        node_list = []
        for i in range(len(G.nodes)):
            # Randomly assign types based on role probability
            node_type = 'device'
            r_val = random.random()
            if r_val < 0.05: node_type = 'gateway'
            elif r_val < 0.15: node_type = 'server' # Adjusted threshold logic to match original: 0.05 + 0.10 range?
            # Original logic:
            # if random.random() < 0.05: node_type = 'gateway'
            # elif random.random() < 0.10: node_type = 'server' 
            # WAIT. The original logic was independent calls to random.random().
            # Let's preserve EXACT logic.
            
            node_type = 'device'
            if random.random() < 0.05: node_type = 'gateway'
            elif random.random() < 0.10: node_type = 'server'
            
            node_list.append({
                'id': f"192.168.1.{i+1}",
                'type': node_type
            })
            
        edge_list = []
        for u, v in G.edges:
            # Simulate traffic weights using Log-Normal distribution
            # Log-Normal is widely used to model packet counts and file sizes.
            packets = int(np.random.lognormal(mean=4, sigma=1)) # ~50-100 packets mean
            bytes_count = packets * int(np.random.normal(500, 200))
            sessions = max(1, int(np.log1p(packets)))
            
            edge_list.append({
                'source': f"192.168.1.{u+1}",
                'target': f"192.168.1.{v+1}",
                'packets': packets,
                'bytes': max(packets * 40, bytes_count),
                'sessions': sessions
            })
            
        return node_list, edge_list, G

    def synthesis_hierarchical_iot_network(self, n_gateways=5, n_sensors=95, backbone_prob=1.0, noise_prob=0.0) -> Tuple[List[Dict], List[Dict], nx.Graph]:
        """
        Synthesize a Realistic IoT Topology (Hub-and-Spoke / Scale-Free).
        
        Structure:
        1. Backbone: Gateways connected in a mesh/random graph (high reliability).
        2. Edge: Sensors connected to Gateways (Star topology).
        
        Args:
            backbone_prob: Probability of edge creation in the backbone (1.0 = Full Mesh).
            noise_prob: Probability that a sensor creates a "noise edge" to a WRONG gateway.
                        Models scanning, misconfiguration, or cross-talk.
        
        This creates a Heavy-Tailed Degree Distribution which is physically realistic 
        for IoT (thousands of sensors, few gateways) and rigorous for testing.
        """
        print(f"[SIMULATION] Synthesizing Hierarchical IoT Network (Gateways={n_gateways}, Sensors={n_sensors}, Noise={noise_prob})...")
        
        G = nx.Graph()
        rng = np.random.RandomState(self.config.seed) if self.config.seed is not None else np.random
        
        # 1. Create Backbone (Gateways)
        # Use Erdos-Renyi for backbone. 
        # CRITICAL: Prob=1.0 (Full Mesh) or high prob ensures connectivity. 
        # Disconnected backbones are failures in reality, and make clustering trivial (components).
        # We 'Steel-man' the test by ensuring it is a single connected component.
        backbone = nx.erdos_renyi_graph(n_gateways, backbone_prob, seed=self.config.seed)
        
        # Relabel backbone nodes to explicit IDs
        mapping = {i: f"10.0.0.{i+1}" for i in range(n_gateways)}
        backbone = nx.relabel_nodes(backbone, mapping)
        G.add_nodes_from(backbone.nodes(data=True))
        G.add_edges_from(backbone.edges())
        
        gateways = sorted(list(G.nodes()))
        
        # 2. Connect Sensors (Edge Layer)
        node_list = []
        # Add Gateways to metadata
        for gw in gateways:
            node_list.append({'id': gw, 'type': 'gateway', 'true_gateway': gw})
            
        edge_list = []
        
        # Add Backbone edges to metadata
        for u, v in G.edges():
             edge_list.append({
                'source': u,
                'target': v,
                'packets': int(rng.normal(1000, 200)), # Backbone traffic is higher
                'bytes': int(rng.normal(50000, 10000)),
                'sessions': 50
             })

        for i in range(n_sensors):
            sensor_id = f"192.168.1.{i+1}"
            
            # Pick a PRIMARY gateway (The "Ground Truth" connection)
            primary_gw = rng.choice(gateways)
            
            node_list.append({'id': sensor_id, 'type': 'device', 'true_gateway': primary_gw})
            G.add_node(sensor_id)
            
            # Connect to Primary
            G.add_edge(sensor_id, primary_gw)
            
            # Traffic profile for sensor
            packets = int(rng.lognormal(3, 0.5))
            edge_list.append({
                'source': sensor_id,
                'target': primary_gw,
                'packets': packets,
                'bytes': packets * 100,
                'sessions': 1
            })
            
            # 3. Inject NOISE (Cross-Talk)
            # Sensors occasionally talk to the WRONG gateway
            if noise_prob > 0.0:
                for other_gw in gateways:
                    if other_gw != primary_gw and rng.random() < noise_prob:
                        G.add_edge(sensor_id, other_gw) # Valid edge in Graph, but invalid logically
                        # Add weak traffic
                        noise_packets = max(1, int(packets * 0.1)) # 10% of main traffic
                        edge_list.append({
                            'source': sensor_id,
                            'target': other_gw,
                            'packets': noise_packets,
                            'bytes': noise_packets * 100,
                            'sessions': 1
                        })
            
        return node_list, edge_list, G

    def simulate_zipfian_port_distribution(self, n_ports=1000, alpha=1.5) -> List[Dict]:
        """
        Simulate port activity following a Zipfian (Power Law) distribution.
        
        Network traffic typically follows a heavy-tailed distribution where a few 
        popular services (ports) account for the majority of traffic.
        
        Args:
            n_ports: Number of unique ports to simulate.
            alpha: The exponent parameter of the Zipf distribution (typically 1.1 - 2.0).
        """
        print(f"[SIMULATION] Synthesizing traffic using Zipfian Distribution (alpha={alpha})...")
        
        traffic = np.random.zipf(a=alpha, size=n_ports)
        # Shuffle so high traffic isn't always at predictable indices if zipf is sorted
        np.random.shuffle(traffic)
        
        data = []
        for i, t in enumerate(traffic):
            # t is a relative magnitude derived from the Zipf ranking
            packets = int(t * 10)
            bytes_count = packets * random.randint(64, 1500)
            sessions = max(1, int(np.sqrt(packets)))
            
            # Determine port number (some well known, some dynamic)
            port = i + 1 if i < 1024 else random.randint(1024, 65535)
            
            data.append({
                'port': port,
                'service_protocol': 'TCP',
                'packets': packets,
                'bytes': bytes_count,
                'sessions': sessions,
                'outbound_packets': packets // 2,
                'inbound_packets': packets // 2,
                'avg_packet_size': bytes_count / packets if packets > 0 else 0
            })
            
        return data

    def simulate_poisson_arrival_process(self, hours=48, base_lambda=10) -> List[Dict]:
        """
        Simulate time-series traffic data using a Non-homogeneous Poisson Process.
        
        Includes diurnal factors to model day/night cycles and random burst injection
        to test anomaly detection capabilities.
        """
        print(f"[SIMULATION] Generating temporal event stream (Hours={hours}, Lambda={base_lambda})...")
        
        timeline = []
        # Fixed relative start time for consistency in relative offsets, though actual date changes
        start_time = datetime.now().replace(minute=0, second=0, microsecond=0) - timedelta(hours=hours)
        
        for i in range(hours):
            current_time = start_time + timedelta(hours=i)
            hour = current_time.hour
            
            # Diurnal pattern: High in day (09:00-17:00), low at night
            factor = 1.0
            if 9 <= hour <= 17: factor = 1.5
            elif 0 <= hour <= 5: factor = 0.2
            
            # Base activity via Poisson Distribution
            packets = int(np.random.poisson(base_lambda * factor * 100))
            
            # Inject Random Burst (Anomaly Simulation)
            if random.random() < 0.1:
                packets *= random.randint(5, 10)
                
            bytes_count = packets * random.randint(500, 1000)
            sessions = max(1, packets // 50)
            
            timeline.append({
                'hour_timestamp': current_time,
                'packet_count': packets,
                'byte_count': bytes_count,
                'session_count': sessions
            })
            
        return timeline

    def simulate_scenario_a(self, duration_sec=60, packet_rate=100, payload_size=60) -> List[Dict]:
        """
        Scenario A: High Frequency / Small Payload.
        Now Parameterized for Sensitivity Analysis.
        """
        # print(f"[SIMULATION] Generating Scenario A (Rate={packet_rate}, Size={payload_size})...")
        traffic = []
        for t in range(duration_sec):
            traffic.append({
                'timestamp_offset': t,
                'packets': packet_rate, 
                'bytes': packet_rate * payload_size, 
                'avg_packet_size': payload_size
            })
        return traffic

    def simulate_scenario_b(self, duration_sec=60, min_packets=1, max_packets=5, min_size=30000, max_size=50000) -> List[Dict]:
        """
        Scenario B: Low Frequency / High Volume.
        Now Parameterized for Sensitivity Analysis.
        """
        # print(f"[SIMULATION] Generating Scenario B (Packets={min_packets}-{max_packets}, Size={min_size}-{max_size})...")
        traffic = []
        for t in range(duration_sec):
            packets = random.randint(min_packets, max_packets) 
            avg_size = random.randint(min_size, max_size) 
            traffic.append({
                'timestamp_offset': t,
                'packets': packets,
                'bytes': packets * avg_size,
                'avg_packet_size': avg_size
            })
        return traffic

    def simulate_jittery_heartbeat(self, duration_sec=300, interval=10.0, sigma=2.0) -> List[float]:
        """
        Simulate a periodic signal with jitter for Stability Analysis (Section 5.5.3).
        Base Inter-Arrival Time = 10s (Heartbeat).
        Noise = Gaussian(0, sigma).
        Congestion = 15% chance of burst (spike).
        
        Returns: List of measured inter-arrival times (in seconds).
        """
        print(f"[SIMULATION] Generating Jittery Heartbeat (Interval={interval}s, Sigma={sigma})...")
        measurements = []
        
        # We simulate the ARRIVAL times, then calculate inter-arrival
        # But for simplicity, we can just generate the delta directly
        # since we want to test the smoothing filter on the DELTAS.
        
        count = int(duration_sec / interval)
        for _ in range(count):
            # Base interval + Jitter
            noise = np.random.normal(0, sigma)
            val = interval + noise
            
            # Congestion Spike (15% chance to delay significantly)
            if random.random() < 0.15:
                val += random.uniform(5.0, 15.0) 
                
            measurements.append(max(0.1, val)) # Ensure positive
            
        return measurements

# ==============================================================================
# Legacy API Wrappers (For Backward Compatibility)
# ==============================================================================

_default_simulator = NetworkTrafficSimulator()

def generate_clustered_topology(n_nodes=100, n_clusters=5, p_intra=0.3, p_inter=0.05):
    """Legacy wrapper for synthesis_stochastic_block_model"""
    return _default_simulator.synthesis_stochastic_block_model(n_nodes, n_clusters, p_intra, p_inter)

def generate_heavy_tailed_ports(n_ports=1000, alpha=1.5):
    """Legacy wrapper for simulate_zipfian_port_distribution"""
    return _default_simulator.simulate_zipfian_port_distribution(n_ports, alpha)

def generate_bursty_timeline(hours=48, base_lambda=10):
    """Legacy wrapper for simulate_poisson_arrival_process"""
    return _default_simulator.simulate_poisson_arrival_process(hours, base_lambda)

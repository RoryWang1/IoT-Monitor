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
        
        # Note: We enforce seed=42 here for topology consistency across runs, 
        # consistent with the original experimental setup.
        G = nx.stochastic_block_model(sizes, probs, seed=42)
        
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

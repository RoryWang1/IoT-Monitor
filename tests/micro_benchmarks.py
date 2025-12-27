import sys
import os
import json
import logging
import time
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import Data Generator
from tests.network_traffic_simulator import generate_clustered_topology, generate_heavy_tailed_ports, generate_bursty_timeline

# Import ACTUAL Backend Implementations
# Note: We need to mock dependencies that depend on DB or Config files if environment is not set up
# We will use the classes directly if possible, or mock the config API they use.

class MockConfigAPI:
    def get_edge_config(self, key, default): return default
    def get_node_config(self, key, default): return default
    def get_node_color(self, key, default): return default
    def get_default(self, key, default): return default
    
# Mock the unified config manager import for modules that might use it at top level
# Since we already imported sys, we can try to inject mocks if needed, 
# but the backend code uses graceful fallbacks (get_config_safe), so we might be fine.

from backend.api.endpoints.devices.network_topology import EdgeGravityOptimizer
from backend.api.endpoints.devices.port_analysis import ConfigurableDevicePortAnalysisAPI
from backend.api.endpoints.devices.activity_timeline import ConfigurableDeviceActivityTimelineAPI

RESULTS_FILE = "tests/results/micro_benchmark_results.json"

def benchmark_edge_gravity():
    print("Running Edge Gravity Benchmark (Real Implementation)...")
    nodes, edges, nx_graph = generate_clustered_topology(n_nodes=50, n_clusters=3)
    
    mock_config = MockConfigAPI()
    optimizer = EdgeGravityOptimizer(mock_config)
    
    # Calculate initial stats needed for algorithm
    max_packets = max(e['packets'] for e in edges)
    max_bytes = max(e['bytes'] for e in edges)
    network_stats = {
        'max_packets': max_packets,
        'max_bytes': max_bytes,
        'all_results': edges # Mocking the structure expected
    }
    
    iterations = 20
    stability_scores = []
    
    # Initialize state
    edge_states = []
    for edge in edges:
        grav, info = optimizer.edge_gravity_algorithm(edge, network_stats)
        edge_states.append({
            'edge': edge,
            'current_gravity': grav,
            'normalized_gravity': min(1.0, grav)
        })
        
    start_time = time.time()
    
    for i in range(iterations):
        # Store previous top edges to measure rank stability
        # Sort by normalized gravity
        edge_states.sort(key=lambda x: x['normalized_gravity'], reverse=True)
        top_10_prev = set(id(x) for x in edge_states[:10])
        
        total_change_normalized = 0
        
        for state in edge_states:
            old_norm = state['normalized_gravity']
            old_raw = state['current_gravity']
            
            # Run gradient descent step
            new_raw = optimizer.graph_metric_gradient_descent(old_raw, state['edge'], i)
            
            # Apply bidirectional enhancement
            final_raw, _ = optimizer.bidirectional_communication_enhancement(new_raw, state['edge'])
            
            # Normalize (Clip at 1.0 as per system design)
            final_norm = min(1.0, max(0.01, final_raw))
            
            state['current_gravity'] = final_raw
            state['normalized_gravity'] = final_norm
            
            total_change_normalized += abs(final_norm - old_norm)
        
        # Calculate Rank Stability (Jaccard Index of Top 10)
        edge_states.sort(key=lambda x: x['normalized_gravity'], reverse=True)
        top_10_curr = set(id(x) for x in edge_states[:10])
        
        jaccard = len(top_10_prev.intersection(top_10_curr)) / len(top_10_prev.union(top_10_curr))
        
        # Stability Score = 1.0 - (Average Normalized Delta / 10) ? 
        # Or better: Just verify that Delta drops to 0.
        avg_delta = total_change_normalized / len(edges)
        stability_scores.append(avg_delta)
        
    duration = (time.time() - start_time) * 1000
    print(f"Edge Gravity 20 iterations took {duration:.2f}ms")
    
    return {
        "iterations": list(range(iterations)),
        "stability_delta": stability_scores, # Should drop to 0 as values saturate
        "rank_stability_jaccard": jaccard, # Should be high (close to 1.0)
        "final_node_count": len(nodes),
        "final_edge_count": len(edges)
    }

def benchmark_port_analysis():
    print("Running Port Analysis Benchmark (Real Implementation)...")
    # Generate Heavy Tailed Data
    raw_data = generate_heavy_tailed_ports(n_ports=500, alpha=1.2)
    
    api = ConfigurableDevicePortAnalysisAPI()
    
    start_time = time.time()
    # Run the actual scoring algorithm
    result = api._calculate_dynamic_activity_scores(raw_data)
    duration = (time.time() - start_time) * 1000
    
    # Evaluate: Do high traffic ports get high scores?
    scores = result['scores']
    
    # Ground Truth: Sort by bytes (volume) and see if Score correlates
    sorted_ports = sorted(raw_data, key=lambda x: x['bytes'], reverse=True)
    top_50_ports = set(x['port'] for x in sorted_ports[:50])
    
    # Check how many of Top 50 are classified as "very_active" or high score
    # Threshold for very_active is dynamic
    threshold = result['thresholds']['very_active']
    
    detected_high = 0
    for p in top_50_ports:
        if scores[p]['score'] >= threshold:
            detected_high += 1
            
    accuracy = detected_high / 50.0
    print(f"Port Analysis Accuracy (Top 50 detection): {accuracy*100:.1f}%")
    
    return {
        "duration_ms": duration,
        "accuracy_top_50": accuracy,
        "threshold_very_active": threshold,
        "score_distribution": result['statistics']['score_distribution']
    }

def benchmark_timeline():
    print("Running Activity Timeline Benchmark (Real Implementation)...")
    timeline_data = generate_bursty_timeline(hours=48)
    
    api = ConfigurableDeviceActivityTimelineAPI()
    
    # Configs
    intensity_config = api._get_intensity_calculation_config()
    classification_config = api._get_pattern_classification_config()
    
    results = []
    
    start_time = time.time()
    for entry in timeline_data:
        packets = entry['packet_count']
        bytes_c = entry['byte_count']
        sessions = entry['session_count']
        
        # Run Algo
        intensity = api._calculate_intensity(packets, bytes_c, sessions, intensity_config)
        pattern = api._classify_pattern(packets, intensity, classification_config)
        
        results.append({
            'hour': entry['hour_timestamp'].hour,
            'intensity': intensity,
            'pattern': pattern,
            'packets': packets
        })
        
    duration = (time.time() - start_time) * 1000
    
    # Validation: Do "Burst" events get high intensity?
    # In our generator, bursts are random. We can check correlation.
    burst_intensities = [r['intensity'] for r in results if r['packets'] > 2000] # Arbitrary high number
    normal_intensities = [r['intensity'] for r in results if r['packets'] < 500]
    
    avg_burst = np.mean(burst_intensities) if burst_intensities else 0
    avg_normal = np.mean(normal_intensities) if normal_intensities else 0
    
    print(f"Timeline Separation: Burst={avg_burst:.2f} vs Normal={avg_normal:.2f}")
    
    return {
        "duration_ms": duration,
        "avg_burst_intensity": avg_burst,
        "avg_normal_intensity": avg_normal,
        "sample_period_count": len(results)
    }

if __name__ == "__main__":
    results = {
        "edge_gravity": benchmark_edge_gravity(),
        "port_analysis": benchmark_port_analysis(),
        "timeline": benchmark_timeline()
    }
    
    os.makedirs(os.path.dirname(RESULTS_FILE), exist_ok=True)
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Benchmarks Complete. Results saved to {RESULTS_FILE}")

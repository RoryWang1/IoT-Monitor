
import json
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import os

RESULTS_FILE = "tests/results/micro_benchmark_results.json"
ENHANCED_RESULTS_FILE = "tests/results/enhanced_rigorous_results.json"
OUTPUT_DIR = "../TSP_template/figures" # Output directly to LaTeX project (IoT-Monitor is sibling to TSP_template)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Set Academic Style
sns.set_style("whitegrid")
sns.set_context("paper", font_scale=1.5)
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['figure.dpi'] = 600  # TSP Combo image requirement (≥600 dpi)

def load_data():
    with open(RESULTS_FILE, 'r') as f:
        data = json.load(f)
        
    if os.path.exists(ENHANCED_RESULTS_FILE):
        print(f"Merging enhanced results from {ENHANCED_RESULTS_FILE}")
        with open(ENHANCED_RESULTS_FILE, 'r') as f:
            enhanced = json.load(f)
            
        # Patch Topology
        if 'convergence_simulation' in enhanced:
            conv = enhanced['convergence_simulation']
            force_e = conv['force_directed']['energy_curve']
            grav_e = conv['edge_gravity']['energy_curve']
            # Truncate to shortest length to be safe
            n = min(len(force_e), len(grav_e))
            data['topology']['iterations'] = list(range(n))
            data['topology']['force_directed_energy'] = force_e[:n]
            data['topology']['edge_gravity_energy'] = grav_e[:n]
            
        # Patch Timeline (Stability)
        if 'stability_stress_test' in enhanced and 'sigma_2.0' in enhanced['stability_stress_test']:
            stab = enhanced['stability_stress_test']['sigma_2.0']
            if 'error_sma' in stab:
                data['timeline']['error_ma'] = stab['error_sma']
                data['timeline']['error_me'] = stab['error_ewma']
                data['timeline']['event_index'] = list(range(len(stab['error_sma'])))
                
        # Patch Sensitivity (Raw Data for Box Plot)
        if 'sensitivity_monte_carlo' in enhanced and 'raw_data' in enhanced['sensitivity_monte_carlo']:
            data['sensitivity_raw'] = enhanced['sensitivity_monte_carlo']['raw_data']

        # Patch Port Analysis (Zipfian)
        if 'port_analysis_zipfian' in enhanced:
            pa = enhanced['port_analysis_zipfian']
            data['port_analysis'] = {
                'x_thresholds': pa['x_thresholds'],
                'linear_f1': pa['linear_f1'],
                'log_f1': pa['log_f1']
            }

    return data

def plot_sensitivity_distribution(raw_data):
    """
    Fig New: Sensitivity Distribution (Box Plot)
    Visualizing the robustness of Log vs Linear scoring across Monte Carlo iterations.
    """
    print("Plotting Sensitivity Distribution...")
    if not raw_data:
        print("Warning: No raw sensitivity data found.")
        return

    # Prepare DataFrame for seaborn
    records = []
    
    # Scenario A
    for score in raw_data['scenario_a']['linear']:
        records.append({'Scenario': 'High-Frequency Burst (A)', 'Method': 'Linear', 'Deviation Score': score})
    for score in raw_data['scenario_a']['log']:
        records.append({'Scenario': 'High-Frequency Burst (A)', 'Method': 'Log (Proposed)', 'Deviation Score': score})
        
    # Scenario B
    for score in raw_data['scenario_b']['linear']:
        records.append({'Scenario': 'High-Volume (B)', 'Method': 'Linear', 'Deviation Score': score})
    for score in raw_data['scenario_b']['log']:
        records.append({'Scenario': 'High-Volume (B)', 'Method': 'Log (Proposed)', 'Deviation Score': score})
        
    df = pd.DataFrame(records)

    plt.figure(figsize=(10, 6))
    sns.boxplot(data=df, x='Scenario', y='Deviation Score', hue='Method', palette=["#e74c3c", "#2ecc71"])
    plt.title("Profiling Sensitivity Distribution (Monte Carlo N=50)")
    plt.ylabel("Normalized Deviation Score (0-1)")
    plt.ylim(-0.05, 1.05)
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/detection_sensitivity_distribution.png")
    plt.close()

def plot_port_analysis(data):
    """
    Fig 11: Port Analysis Performance Comparison
    X: Threshold, Y: F1 Score
    """
    print("Plotting Port Analysis...")
    df_lin = pd.DataFrame({
        'Threshold': data['x_thresholds'],
        'F1 Score': data['linear_f1'],
        'Method': 'Linear Normalization'
    })
    df_log = pd.DataFrame({
        'Threshold': data['x_thresholds'],
        'F1 Score': data['log_f1'],
        'Method': 'Log Normalization (Proposed)'
    })
    df = pd.concat([df_lin, df_log])

    plt.figure(figsize=(10, 6))
    sns.lineplot(data=df, x='Threshold', y='F1 Score', hue='Method', linewidth=2.5, palette=["#e74c3c", "#2ecc71"])
    plt.title("Port Analysis Service Role Profiling Performance")
    plt.xlabel("Profiling Threshold (Normalized)")
    plt.ylabel("F1 Score")
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/port_analysis_comparison.png")
    plt.close()

def plot_topology_convergence(data):
    """
    Fig 12: Topology Convergence
    X: Iteration, Y: Energy
    """
    print("Plotting Topology Convergence...")
    iterations = data['iterations']
    df_force = pd.DataFrame({
        'Iteration': iterations,
        'Energy': data['force_directed_energy'],
        'Algorithm': 'Force-Directed (Linear Decay)'
    })
    df_gravity = pd.DataFrame({
        'Iteration': iterations,
        'Energy': data['edge_gravity_energy'],
        'Algorithm': 'Edge Gravity (Exp. Decay)'
    })
    df = pd.concat([df_force, df_gravity])

    plt.figure(figsize=(10, 6))
    sns.lineplot(data=df, x='Iteration', y='Energy', hue='Algorithm', linewidth=2.5)
    plt.title("Network Topology Layout Convergence Speed")
    plt.xlabel("Simulation Iteration")
    plt.ylabel("System Energy (Normalized)")
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/topology_convergence.png")
    plt.close()

def plot_timeline_performance(data):
    """
    Fig 13: Timeline Prediction Error
    X: Event Index, Y: Absolute Error
    """
    print("Plotting Timeline Performance...")
    idx = data['event_index']
    df_ma = pd.DataFrame({
        'Event Index': idx,
        'Prediction Error': data['error_ma'],
        'Method': 'Simple Moving Average (SMA)'
    })
    df_me = pd.DataFrame({
        'Event Index': idx,
        'Prediction Error': data['error_me'],
        'Method': 'EWMA (Proposed)'
    })
    df = pd.concat([df_ma, df_me])

    plt.figure(figsize=(10, 6))
    sns.lineplot(data=df, x='Event Index', y='Prediction Error', hue='Method', marker='o', linewidth=2)
    plt.title("Behavioral Timeline Prediction Accuracy")
    plt.xlabel("Event Sequence Index")
    plt.ylabel("Time Prediction Error (s)")
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/timeline_performance.png")
    plt.close()

def plot_protocol_analysis(data):
    """
    Fig 14: Protocol Distribution
    Bar Chart
    """
    print("Plotting Protocol Analysis...")
    df = pd.DataFrame({
        'Protocol': data['protocols'],
        'Count': data['counts']
    })
    
    plt.figure(figsize=(10, 6))
    sns.barplot(data=df, x='Protocol', y='Count', color="#3498db")
    plt.title("Detected Application Layer Protocol Distribution")
    plt.xlabel("Protocol Type")
    plt.ylabel("Traffic Flow Count")
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/protocol_analysis.png")
    plt.close()

if __name__ == "__main__":
    data = load_data()
    plot_port_analysis(data['port_analysis'])
    if 'sensitivity_raw' in data:
        plot_sensitivity_distribution(data['sensitivity_raw'])
    plot_topology_convergence(data['topology'])
    plot_timeline_performance(data['timeline'])
    plot_protocol_analysis(data['protocols'])
    print("All micro-benchmark plots generated.")

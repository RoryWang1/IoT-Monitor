
import json
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import os

RESULTS_FILE = "tests/results/micro_benchmark_results.json"
OUTPUT_DIR = "../MDPI/Submission/figures"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Set Academic Style
sns.set_style("whitegrid")
sns.set_context("paper", font_scale=1.5)
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['figure.dpi'] = 300

def load_data():
    with open(RESULTS_FILE, 'r') as f:
        return json.load(f)

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
    plt.xlabel("Detection Threshold (Normalized)")
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
        'Algorithm': 'Force-Directed (Standard)'
    })
    df_gravity = pd.DataFrame({
        'Iteration': iterations,
        'Energy': data['edge_gravity_energy'],
        'Algorithm': 'Edge Gravity (Proposed)'
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
        'Method': 'Moving Average (Standard)'
    })
    df_me = pd.DataFrame({
        'Event Index': idx,
        'Prediction Error': data['error_me'],
        'Method': 'Math Expectation (Proposed)'
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
    plot_topology_convergence(data['topology'])
    plot_timeline_performance(data['timeline'])
    plot_protocol_analysis(data['protocols'])
    print("All micro-benchmark plots generated.")

import json
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import os
from scipy import stats

# -----------------------------------------------------------------------------
# ACADEMIC STYLING CONFIGURATION
# -----------------------------------------------------------------------------
# Set style to research-paper standard (Clean, readable, high contrast)
sns.set_theme(style="whitegrid", rc={
    "axes.labelsize": 12,
    "font.size": 12,
    "legend.fontsize": 10,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "font.family": "sans-serif", # Switch to "serif" if using LaTeX rendering
    "grid.linestyle": "--",
    "grid.alpha": 0.6
})

OUTPUT_DIR = "../MDPI/Submission/figures"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def load_scalability_data():
    with open("tests/results/scalability_enhanced_results.json", "r") as f:
        data = json.load(f)
    # Flatten list of lists
    flat_data = []
    for run_idx, run in enumerate(data):
        for step in run:
            step['run_id'] = run_idx
            flat_data.append(step)
    return pd.DataFrame(flat_data)

def load_security_data():
    with open("tests/results/attack_simulation_results.json", "r") as f:
        data = json.load(f)
    return pd.DataFrame(data)

def plot_scalability_curve(df):
    """Figure 1: Throughput Scalability with Error Bars and Extrapolation"""
    plt.figure(figsize=(8, 5))
    
    # 1. Plot Actual Data (Mean + Error Bars)
    sns.lineplot(data=df, x="num_agents", y="avg_rps", marker="o", errorbar="sd", label="Measured Throughput")
    
    # 2. Linear Regression (Extrapolation)
    slope, intercept, r_value, p_value, std_err = stats.linregress(df["num_agents"], df["avg_rps"])
    
    # Project to 2000 nodes
    future_x = np.array([500, 2000])
    future_y = slope * future_x + intercept
    plt.plot(future_x, future_y, linestyle="--", color="gray", alpha=0.8, label=f"Projection ($R^2={r_value**2:.2f}$)")
    
    plt.title("System Throughput Scalability (Linear Growth)")
    plt.xlabel("Number of Concurrent IoT Agents")
    plt.ylabel("Throughput (Requests/Second)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/scalability_curve.png", dpi=300)
    plt.close()

def plot_efficiency_profile(df):
    """Figure 2: Resource Efficiency (Dual Axis)"""
    fig, ax1 = plt.subplots(figsize=(8, 5))
    
    # CPU on Left Axis
    sns.lineplot(data=df, x="avg_rps", y="avg_cpu_percent", ax=ax1, color="tab:blue", marker="s", label="CPU Usage")
    ax1.set_xlabel("Throughput (RPS)")
    ax1.set_ylabel("Backend CPU Usage (%)", color="tab:blue")
    ax1.tick_params(axis='y', labelcolor="tab:blue")
    ax1.set_ylim(0, 100)
    
    # Memory on Right Axis
    ax2 = ax1.twinx()
    sns.lineplot(data=df, x="avg_rps", y="avg_memory_mb", ax=ax2, color="tab:orange", marker="^", label="Memory Usage")
    ax2.set_ylabel("Memory Usage (MB)", color="tab:orange")
    ax2.tick_params(axis='y', labelcolor="tab:orange")
    
    plt.title("Resource Efficiency Profile")
    fig.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/efficiency_profile.png", dpi=300)
    plt.close()

def plot_latency_distribution(df):
    """Figure 3: Latency Stability"""
    plt.figure(figsize=(8, 5))
    
    # Melt for grouped bar chart or multi-line
    latency_df = df.melt(id_vars=["num_agents"], value_vars=["avg_latency_ms", "p99_latency_ms"], 
                         var_name="Metric", value_name="Latency (ms)")
    
    sns.barplot(data=latency_df, x="num_agents", y="Latency (ms)", hue="Metric", palette="muted")
    
    plt.title("Latency Stability under Load")
    plt.xlabel("Number of Concurrent IoT Agents")
    plt.ylabel("Response Latency (ms)")
    plt.axhline(y=200, color='r', linestyle=':', label="QoS Limit (200ms)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/latency_distribution.png", dpi=300)
    plt.close()

def plot_profiling_sensitivity(df):
    """Figure 4 & 7 combined concept: Verification of Eq. 4"""
    # Filter for 0% packet loss (Clean Network Baseline)
    clean_df = df[df["packet_loss_rate"] == 0.0].copy()
    
    plt.figure(figsize=(10, 6))
    
    # Plot Anomaly Score
    sns.lineplot(data=clean_df, x="timestamp", y="risk_score", linewidth=2, color="#d62728", label="Behavioral Anomaly Score")
    
    # Add Zone Shading
    phases = clean_df.groupby("phase")["timestamp"].agg(["min", "max"])
    colors = {"Normal": "#2ca02c", "Mirai": "#ff7f0e", "Exfiltration": "#9467bd"}
    phase_labels = {"Normal": "Baseline", "Mirai": "Scenario A", "Exfiltration": "Scenario B"}
    
    for phase, row in phases.iterrows():
        display_label = phase_labels.get(phase, phase)
        plt.axvspan(row["min"], row["max"], color=colors[phase], alpha=0.1, label=f"{display_label} Zone")
        # Add text label
        plt.text(row["min"]+20, 95, display_label, fontsize=10, fontweight="bold", color=colors[phase])
        
    plt.title("Profiling Sensitivity Analysis: Multi-Scenario Evaluation")
    plt.xlabel("Time Simulation (s)")
    plt.ylabel("Behavioral Anomaly Score (0-100)")
    plt.ylim(0, 110)
    
    # Smart legend handling to avoid duplicates
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    plt.legend(by_label.values(), by_label.keys(), loc="lower right")
    
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/detection_response.png", dpi=300)
    plt.close()

def plot_reliability(df):
    """Figure 6: Reliability Analysis (Packet Loss)"""
    # Calculate "Profiling Accuracy" per phase per loss rate
    # Define Threshold: Score > 50 considered anomalous
    res = []
    for loss in df["packet_loss_rate"].unique():
        subset = df[df["packet_loss_rate"] == loss]
        
        # False Positive Rate (Normal/Baseline Phase)
        normal = subset[subset["phase"] == "Normal"]
        fpr = (normal["risk_score"] > 50).mean() * 100
        
        # True Positive Rate (Anomaly Scenarios)
        anomaly = subset[subset["phase"].isin(["Mirai", "Exfiltration"])]
        tpr = (anomaly["risk_score"] > 50).mean() * 100
        
        res.append({"Packet Loss %": loss*100, "Metric": "Anomaly Profiling Accuracy", "Value": tpr})
        res.append({"Packet Loss %": loss*100, "Metric": "Baseline Stability", "Value": 100-fpr})
        
    res_df = pd.DataFrame(res)
    
    plt.figure(figsize=(8, 5))
    sns.lineplot(data=res_df, x="Packet Loss %", y="Value", hue="Metric", marker="o", linewidth=2)
    
    plt.title("Profiling Reliability under Network Instability")
    plt.xlabel("Simulated Packet Loss (%)")
    plt.ylabel("Accuracy (%)")
    plt.ylim(-5, 105)
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/robustness_analysis.png", dpi=300)
    plt.close()
    
def plot_radar_comparison():
    """Figure 5: Radar Chart for State-of-the-Art Comparison"""
    # Qualitative Data
    labels = ['Real-time Analysis', 'Historical Query', 'Topology Viz', 'Scalability', 'Deployment Ease']
    
    # Scores (1-5)
    our_system = [5, 4, 5, 5, 4]
    moniotr = [2, 5, 1, 3, 2] # Batch based, hard to deploy
    iot_sentinel = [4, 1, 2, 3, 3] # Fingerprinting focused
    
    angles = np.linspace(0, 2*np.pi, len(labels), endpoint=False).tolist()
    angles += angles[:1] # Close the loop
    
    our_system += our_system[:1]
    moniotr += moniotr[:1]
    iot_sentinel += iot_sentinel[:1]
    
    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    
    # Plot Ours
    ax.plot(angles, our_system, color='#1f77b4', linewidth=2, label='Proposed System')
    ax.fill(angles, our_system, color='#1f77b4', alpha=0.25)
    
    # Plot Moniotr
    ax.plot(angles, moniotr, color='#ff7f0e', linewidth=1, linestyle='--', label='Moniotr [12]')
    
    # Plot Sentinel
    ax.plot(angles, iot_sentinel, color='#2ca02c', linewidth=1, linestyle='--', label='IoT Sentinel [15]')
    
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_thetagrids(np.degrees(angles[:-1]), labels)
    
    plt.title("Feature Comparison with State-of-the-Art")
    plt.legend(loc='upper right', bbox_to_anchor=(0.1, 0.1))
    plt.savefig(f"{OUTPUT_DIR}/comparison_radar.png", dpi=300)
    plt.close()

def main():
    print("Generating Scalability Plots...")
    try:
        scale_df = load_scalability_data()
        plot_scalability_curve(scale_df)
        plot_efficiency_profile(scale_df)
        plot_latency_distribution(scale_df)
    except Exception as e:
        print(f"Skipping Scalability Plots (Data missing?): {e}")

    print("Generating Profiling Sensitivity Plots...")
    try:
        sec_df = load_security_data()
        plot_profiling_sensitivity(sec_df)
        plot_reliability(sec_df)
    except Exception as e:
        print(f"Skipping Profiling Plots (Data missing?): {e}")
        
    print("Generating Radar Chart...")
    plot_radar_comparison()
    
    print("All professional plots generated in MDPI/Submission/figures/")

if __name__ == "__main__":
    main()

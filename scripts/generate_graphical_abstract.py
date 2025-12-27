#!/usr/bin/env python3
"""
Generate Graphical Abstract for MDPI Journal Submission
Multi-Dimensional Profiling System for IoT Behavioral Characterization
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, Circle, Rectangle, FancyArrowPatch
import numpy as np

# Set up figure with high DPI for publication quality
fig = plt.figure(figsize=(12, 7), dpi=300)
ax = plt.axes([0, 0, 1, 1])
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis('off')

# Color palette - professional academic colors
color_functional = '#1976D2'    # Blue
color_structural = '#7B1FA2'    # Purple
color_temporal = '#388E3C'      # Green
color_input = '#455A64'         # Blue Grey
color_output = '#D84315'        # Deep Orange
color_light = '#ECEFF1'         # Light Grey

# ============================================================================
# TITLE
# ============================================================================
ax.text(50, 95, 'Multi-Dimensional Profiling System for IoT Behavioral Characterization',
        ha='center', va='top', fontsize=14, fontweight='bold', color='#263238')

# ============================================================================
# LEFT: INPUT - Network Traffic
# ============================================================================
input_box = FancyBboxPatch((2, 30), 18, 55, 
                           boxstyle="round,pad=0.5", 
                           edgecolor=color_input, facecolor=color_light, 
                           linewidth=2)
ax.add_patch(input_box)

ax.text(11, 78, 'Network Traffic', ha='center', va='center', 
        fontsize=11, fontweight='bold', color=color_input)
ax.text(11, 73, 'PCAP Data', ha='center', va='center', 
        fontsize=9, color=color_input, style='italic')

# IoT devices representation
devices = [
    ('Camera', 65),
    ('Sensor', 56),
    ('Smart Hub', 47),
    ('Unknown', 38)
]

for device, y_pos in devices:
    # Device icon (circle)
    circle = Circle((7, y_pos), 1.5, facecolor='white', edgecolor=color_input, linewidth=1.5)
    ax.add_patch(circle)
    # Device label
    ax.text(11, y_pos, device, ha='left', va='center', fontsize=8, color='#37474F')
    # Packet flow (arrows)
    ax.plot([15, 19], [y_pos, y_pos], color=color_input, linewidth=1.5, alpha=0.6)
    ax.plot([19], [y_pos], marker='>', color=color_input, markersize=6)

# ============================================================================
# CENTER: THREE PARALLEL DIMENSIONS
# ============================================================================

# Dimension 1: FUNCTIONAL (Port Analysis)
func_y = 68
func_box = FancyBboxPatch((23, func_y-8), 28, 16, 
                          boxstyle="round,pad=0.3", 
                          edgecolor=color_functional, facecolor='#E3F2FD', 
                          linewidth=2.5)
ax.add_patch(func_box)

ax.text(37, func_y+5, 'FUNCTIONAL DIMENSION', ha='center', va='center', 
        fontsize=10, fontweight='bold', color=color_functional)
ax.text(37, func_y+2, 'Port Analysis', ha='center', va='center', 
        fontsize=9, color=color_functional)

# Port visualization
ports = ['80', '443', '8883', '5353']
for i, port in enumerate(ports):
    port_x = 25 + i * 6.5
    rect = Rectangle((port_x, func_y-5), 4, 4, 
                     facecolor='white', edgecolor=color_functional, linewidth=1)
    ax.add_patch(rect)
    ax.text(port_x+2, func_y-3, port, ha='center', va='center', 
            fontsize=7, fontweight='bold', color=color_functional)

# Dimension 2: STRUCTURAL (Edge Gravity)
struct_y = 45
struct_box = FancyBboxPatch((23, struct_y-8), 28, 16, 
                            boxstyle="round,pad=0.3", 
                            edgecolor=color_structural, facecolor='#F3E5F5', 
                            linewidth=2.5)
ax.add_patch(struct_box)

ax.text(37, struct_y+5, 'STRUCTURAL DIMENSION', ha='center', va='center', 
        fontsize=10, fontweight='bold', color=color_structural)
ax.text(37, struct_y+2, 'Edge Gravity Analysis', ha='center', va='center', 
        fontsize=9, color=color_structural)

# Network graph visualization
nodes = [(28, struct_y-3), (33, struct_y-2), (38, struct_y-4), (43, struct_y-2), (48, struct_y-3)]
for node in nodes:
    circle = Circle(node, 1.2, facecolor='white', edgecolor=color_structural, linewidth=1.5)
    ax.add_patch(circle)

# Edges with varying thickness (representing gravity/weight)
edges = [
    ((28, struct_y-3), (33, struct_y-2), 2.5),
    ((33, struct_y-2), (38, struct_y-4), 1.5),
    ((38, struct_y-4), (43, struct_y-2), 3.0),
    ((43, struct_y-2), (48, struct_y-3), 1.0),
    ((28, struct_y-3), (38, struct_y-4), 1.0)
]
for start, end, weight in edges:
    ax.plot([start[0], end[0]], [start[1], end[1]], 
            color=color_structural, linewidth=weight, alpha=0.5)

# Dimension 3: TEMPORAL (Activity Timeline)
temp_y = 22
temp_box = FancyBboxPatch((23, temp_y-8), 28, 16, 
                          boxstyle="round,pad=0.3", 
                          edgecolor=color_temporal, facecolor='#E8F5E9', 
                          linewidth=2.5)
ax.add_patch(temp_box)

ax.text(37, temp_y+5, 'TEMPORAL DIMENSION', ha='center', va='center', 
        fontsize=10, fontweight='bold', color=color_temporal)
ax.text(37, temp_y+2, 'Activity Timeline', ha='center', va='center', 
        fontsize=9, color=color_temporal)

# Timeline visualization
timeline_x = np.linspace(25, 49, 50)
timeline_y = temp_y - 3 + 3 * np.sin(timeline_x/3) + np.random.normal(0, 0.3, 50)
ax.plot(timeline_x, timeline_y, color=color_temporal, linewidth=2)
ax.fill_between(timeline_x, temp_y-6, timeline_y, color=color_temporal, alpha=0.2)
ax.plot([25, 49], [temp_y-3, temp_y-3], '--', color=color_temporal, linewidth=0.8, alpha=0.5)

# Arrows from input to dimensions
for y in [func_y, struct_y, temp_y]:
    arrow = FancyArrowPatch((20.5, y), (22.5, y),
                           arrowstyle='->', mutation_scale=15, 
                           linewidth=2, color='#607D8B', alpha=0.6)
    ax.add_patch(arrow)

# ============================================================================
# RIGHT: OUTPUT - Behavioral Profile
# ============================================================================
output_box = FancyBboxPatch((54, 30), 22, 55, 
                            boxstyle="round,pad=0.5", 
                            edgecolor=color_output, facecolor='#FBE9E7', 
                            linewidth=2.5)
ax.add_patch(output_box)

ax.text(65, 78, 'Behavioral Profile', ha='center', va='center', 
        fontsize=11, fontweight='bold', color=color_output)
ax.text(65, 74, 'Anomaly Detection', ha='center', va='center', 
        fontsize=9, color=color_output, style='italic')

# Profile metrics
metrics = [
    ('Service Role:', 'Web Server', 68),
    ('Network Position:', 'Central Hub', 62),
    ('Activity Pattern:', 'Periodic Burst', 56),
    ('Anomaly Score:', '76/100', 50)
]

for label, value, y_pos in metrics:
    ax.text(56, y_pos, label, ha='left', va='center', 
            fontsize=8, fontweight='bold', color='#5D4037')
    ax.text(56, y_pos-2.5, value, ha='left', va='center', 
            fontsize=8, color='#6D4C41')

# Anomaly score visualization (gauge)
gauge_center = (65, 38)
gauge_radius = 4
# Background arc
theta = np.linspace(np.pi, 2*np.pi, 100)
x_arc = gauge_center[0] + gauge_radius * np.cos(theta)
y_arc = gauge_center[1] + gauge_radius * np.sin(theta)
ax.plot(x_arc, y_arc, color='#BCAAA4', linewidth=6, alpha=0.3)

# Filled arc (representing 76%)
theta_filled = np.linspace(np.pi, np.pi + 0.76*np.pi, 100)
x_filled = gauge_center[0] + gauge_radius * np.cos(theta_filled)
y_filled = gauge_center[1] + gauge_radius * np.sin(theta_filled)
ax.plot(x_filled, y_filled, color=color_output, linewidth=6)

ax.text(65, 34, '76', ha='center', va='center', 
        fontsize=14, fontweight='bold', color=color_output)

# Arrows from dimensions to output
for y in [func_y, struct_y, temp_y]:
    arrow = FancyArrowPatch((51.5, y), (53.5, y),
                           arrowstyle='->', mutation_scale=15, 
                           linewidth=2, color='#607D8B', alpha=0.6)
    ax.add_patch(arrow)

# ============================================================================
# BOTTOM: Key Features
# ============================================================================
features_y = 8
features = [
    (color_functional, 'Service Classification'),
    (color_structural, 'Network Topology Analysis'),
    (color_temporal, 'Behavioral Pattern Recognition')
]

feature_x = 15
for color, text in features:
    # Color indicator
    rect = Rectangle((feature_x, features_y-1), 2, 2, 
                     facecolor=color, edgecolor=color, linewidth=0)
    ax.add_patch(rect)
    # Text
    ax.text(feature_x+3, features_y, text, ha='left', va='center', 
            fontsize=8, color='#37474F')
    feature_x += 25

# ============================================================================
# SAVE
# ============================================================================
output_path = '/Users/rory/work/Dissertation_Journal/MDPI/Submission/figures/graphical_abstract.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight', 
            facecolor='white', edgecolor='none', pad_inches=0.1)
print(f"✓ Graphical Abstract generated: {output_path}")
print(f"  Resolution: 3600x2100 pixels (300 DPI)")
print(f"  Format: PNG with white background")

plt.close()

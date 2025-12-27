#!/usr/bin/env python3
"""
Generate System Architecture Diagram for MDPI Journal Submission
Simplified Block Diagram - Vertical Layout (Top-Down)
Refined based on user feedback (Title top, no Mirror, fixed arrows, no Anomaly text)
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

# Set up figure - Portrait orientation for vertical flow
fig = plt.figure(figsize=(8, 11), dpi=300) # Increased height slightly for title
ax = plt.axes([0, 0, 1, 1])
ax.set_xlim(0, 100)
ax.set_ylim(0, 105) # Increased Y limit to make room at top
ax.axis('off')

# Color palette (Clean, Professional)
color_functional = '#E3F2FD'    # Light Blue
color_structural = '#F3E5F5'    # Light Purple
color_temporal = '#E8F5E9'      # Light Green
edge_functional = '#1976D2'
edge_structural = '#7B1FA2'
edge_temporal = '#388E3C'

color_box = '#FAFAFA'
edge_box = '#455A64'

# text styles
font_title = {'fontsize': 12, 'fontweight': 'bold', 'color': '#263238'}
font_text = {'fontsize': 10, 'color': '#37474F'}
font_small = {'fontsize': 8, 'color': '#546E7A'}

def add_block(x, y, w, h, text, subtext=None, color=color_box, edge=edge_box):
    # Shadow
    shadow = FancyBboxPatch((x+0.5, y-0.5), w, h, boxstyle="round,pad=0.2", 
                           fc='#E0E0E0', ec='none')
    ax.add_patch(shadow)
    # Main box
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.2", 
                         fc=color, ec=edge, lw=1.5)
    ax.add_patch(box)
    
    ax.text(x + w/2, y + h/2 + (1.5 if subtext else 0), text, 
            ha='center', va='center', **font_title)
    if subtext:
        ax.text(x + w/2, y + h/2 - 2, subtext, 
                ha='center', va='center', **font_text)
    return box

def add_arrow(x1, y1, x2, y2):
    arrow = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle='->', 
                            mutation_scale=15, color='#78909C', lw=1.5)
    ax.add_patch(arrow)

# ============================================================================
# FLOW - Vertical (Top to Bottom)
# ============================================================================

# 1. INPUT (Top Center)
input_x, input_y = 40, 90
# Removed "Mirror/PCAP" subtext
add_block(input_x, input_y, 20, 8, "IoT Network\nTraffic", None)

# Arrow 1 (Down)
# From Input Bottom (90) to System Top (82)
add_arrow(50, 90, 50, 82)

# 2. PROFILING SYSTEM (Middle Container)
sys_x, sys_y = 15, 30
sys_w, sys_h = 70, 52
sys_bg = FancyBboxPatch((sys_x, sys_y), sys_w, sys_h, boxstyle="round,pad=0.5", 
                        fc='#F5F5F5', ec='#607D8B', lw=1, linestyle='--')
ax.add_patch(sys_bg)
ax.text(sys_x + 2, sys_y + sys_h + 1, "Multi-Dimensional Behavioral Profiling System", 
        ha='left', va='bottom', fontsize=11, fontweight='bold', color='#455A64')

# 2a. Preprocessing (Top of System)
# y range [70, 78]
add_block(sys_x + 10, sys_y + 40, 50, 8, "Packet Preprocessing", "Parsing & Extraction")

# Arrows to dimensions (Distribute from one source to 3 targets)
src_x, src_y = 50, sys_y + 40 # y=70 (Bottom of Preprocessing)

# Dimensions Top y = sys_y + 24 + 10 = 30 + 34 = 64
target_y = sys_y + 24 + 10 # 64

add_arrow(50, src_y, 25, target_y) # To Func (Left center x approx 24)
add_arrow(50, src_y, 50, target_y) # To Struct (Center x 50)
add_arrow(50, src_y, 75, target_y) # To Temp (Right center x approx 76)


# 2b. Three Dimensions (Middle of System, Side-by-Side)
dim_w, dim_h = 18, 10
dim_y_pos = sys_y + 24 # y=54. Box [54, 64]

# Functional (Left)
add_block(sys_x + 2, dim_y_pos, dim_w, dim_h, "Functional", "Port\nAnalysis", 
          color=color_functional, edge=edge_functional)

# Structural (Center)
add_block(sys_x + 26, dim_y_pos, dim_w, dim_h, "Structural", "Edge\nGravity", 
          color=color_structural, edge=edge_structural)

# Temporal (Right)
add_block(sys_x + 50, dim_y_pos, dim_w, dim_h, "Temporal", "Activity\nTimeline", 
          color=color_temporal, edge=edge_temporal)

# Arrows to Fusion (Converge)
dim_out_y = dim_y_pos # 54 (Bottom of Dim boxes)
fusion_in_y = sys_y + 4 + 8 # 30 + 4 + 8 = 42 (Top of fusion box)

# Center of boxes
x_left = sys_x + 2 + dim_w/2 # 17 + 9 = 26. Wait, sys_x=15. 15+2+9=26.
x_center = sys_x + 26 + dim_w/2 # 15+26+9=50.
x_right = sys_x + 50 + dim_w/2 # 15+50+9=74.

add_arrow(x_left, dim_out_y, 50, fusion_in_y)
add_arrow(x_center, dim_out_y, 50, fusion_in_y)
add_arrow(x_right, dim_out_y, 50, fusion_in_y)

# 2c. Fusion (Bottom of System)
# y range [34, 42]
# Removed "Anomaly Characterization" text
add_block(sys_x + 10, sys_y + 4, 50, 8, "Behavioral Profile Construction", "Profile Synthesis")

# Arrow out (Down)
# From Fusion Bottom (34) to Output Top (22)
add_arrow(50, sys_y + 4, 50, 22)

# 3. OUTPUT (Bottom Center)
# Box [5, 22] (y=5, h=17)
output_box = FancyBboxPatch((35, 5), 30, 17, boxstyle="round,pad=0.2", 
                            fc='#E0F7FA', ec='#006064', lw=1.5)
ax.add_patch(output_box)
ax.text(50, 17, "Profile\nVisualization", ha='center', va='center', **font_title)
ax.text(50, 12, "Service Role", ha='center', va='center', fontsize=8)
ax.text(50, 9, "Topology View", ha='center', va='center', fontsize=8)
ax.text(50, 6, "Behavior Pattern", ha='center', va='center', fontsize=8)

# Save
output_path = '/Users/rory/work/Dissertation_Journal/MDPI/Submission/figures/system_architecture.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
print(f"✓ Vertical System Architecture generated: {output_path}")

plt.close()

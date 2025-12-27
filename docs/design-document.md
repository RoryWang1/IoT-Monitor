# IoT Device Dashboard Design Document

## **Experiment Management**

### **Experiment Naming Convention**
- **Frontend Display Format**: Experiment XXXX 
- **Backend Storage Path**: pcap_input/experiment_XXXX

## **Device Identification & Naming**

### **Device Name Mapping Priority**
IoT device name resolution follows the **priority order** below:

- **First Priority**: Match fields (name, category, vendor) from *known_devices* table in database
- **Second Priority**: Match fields (category, vendor) from *vendor_patterns* table in database  
- **Fallback Option**: Use default generated names

### **Device Online Status Detection**
Device online status is determined by comparing **last activity time** with configured threshold:

- **Detection Logic**: Compare device last activity time with threshold
- **Default Threshold**: 24 hours
- **Configuration Location**: `device_status.online_detection.threshold_hours` in `config/user_config.json`
- **Implementation Location**: `_get_threshold_hours` function in `backend/pcap_process/analyzers/device/device_status_service.py`

## **Network Traffic Analysis**

### **Sankey Diagram Analysis Rules**
**Device->Location Mapping** mechanism:

- **Data Source**: Match IP addresses from *ip_geolocation_ref* table in database
- **Traffic Scope**: ***External traffic only***

## **Port Analysis Algorithm**

### **Analysis Scope Configuration**
- **Default Port Count**: Analyze top 50 ports maximum
- **Configuration Modification**: `analysis_limits.max_ports_per_device` in `config/user_config.json`

### **Port Activity Status Classification**
Ports are classified into 5 levels based on **activity scores**:

- **very_active**: 0.8~1.0
- **active**: 0.6~0.8  
- **moderate**: 0.3~0.6
- **low**: 0.1~0.3
- **inactive**: 0.0~0.1

*Score threshold configuration location*: `_calculate_dynamic_activity_scores` function in `backend/api/endpoints/devices/port_analysis.py`

### **Scoring Calculation Method**
Employs **logarithmic normalized port activity scoring algorithm**:

#### *Weight Configuration*
- Packet weight: **0.4**
- Byte weight: **0.4** 
- Session weight: **0.2**

#### *Port Type Weights*
- **system**: 1.5
- **well_known**: 1.2
- **registered**: 1.0
- **dynamic**: 0.8

#### *Bidirectional Communication Bonus*
- Base bonus: **0.15**
- Balance ratio bonus: **0.1**
- Final score range: **0.0-1.0**

*Algorithm implementation location*: `calculate_port_activity_score` function in `backend/api/endpoints/devices/port_analysis.py`

## **Activity Timeline Visualization**

### **Heatmap Intensity Calculation**
Activity intensity values range from **0~100**, using ***mathematical expectation-based adaptive intensity calculation***:

#### *Time Decay Factors*
- **Business Hours**: 1.2
- **Evening Peak**: 1.1
- **Night Low**: 0.8
- **Default Weight**: 1.0

### **Frontend Color Mapping**
Heatmap colors are divided by intensity percentage:

- **High (80%+)**: Red
- **Medium-High (60%-80%)**: Orange
- **Medium (40%-60%)**: Green
- **Low-Medium (20%-40%)**: Blue
- **Very Low (0%-20%)**: Gray

### **Intensity Algorithm Details**
Algorithm uses ***adaptive multi-dimensional weight calculation***:

#### *Core Weight Configuration*
- Packet weight: **0.4**
- Byte weight: **0.4**
- Session weight: **0.2**

#### *Optimization Techniques*
- Apply **logarithmic normalization** to avoid extreme value effects
- Integrate **energy weight factors**
- *Implementation location*: `_calculate_intensity` function in `backend/api/endpoints/devices/activity_timeline.py`

## **Network Topology Analysis**

### **Node Importance Algorithm**
Uses ***Edge Gravity algorithm combined with gradient descent optimization***:

#### *Scoring Weights*
- **Connection degree weight**: 0.6
- **Traffic weight**: 0.4

#### *Node Type Weights*
- **gateway**: 1.5
- **server**: 1.3
- **device**: 1.0
- **external**: 0.8

*Algorithm location*: Related algorithm functions in `backend/api/endpoints/devices/network_topology.py`

### **Frontend Visualization Differences**

#### *Node Size Differences* (By importance: **Large→Small**)
- **real_device** - *Largest size with glow effect*
- **important_external** - *Medium size*
- **secondary_external** - *Standard size*
- **low_priority** - *Smallest size*

#### *Spatial Layout Differences* (By position: **Inner→Outer**)
- **real_device** - *Center area*
- **important_external** - *Middle ring layout*
- **secondary_external** - *Outer ring layout*
- **low_priority** - *Dynamic position allocation* 
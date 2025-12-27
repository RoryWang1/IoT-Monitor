/**
 * Complete definition of the color system
 * Covering all possible protocols, states, device types and network modes
 */

// Basic Protocol Color Mapping 
// Based on the protocol definitions in packet_parser.py and data_analyzer.py
export const PROTOCOL_COLORS: Record<string, string> = {
  // Transport Layer Protocols
  'TCP': '#3B82F6',           // Blue - Transmission Control Protocol
  'UDP': '#10B981',           // Green - User Datagram Protocol  
  'ICMP': '#EF4444',          // Red - Internet Control Message Protocol
  'IGMP': '#F97316',          // Deep Orange - Internet Group Management Protocol
  'ARP': '#A855F7',           // Purple - Address Resolution Protocol
  'OSPF': '#EC4899',          // Pink - Open Shortest Path First Protocol
  
  // Web Protocol Family
  'HTTP': '#22c55e',          // Green - Web traffic
  'HTTPS': '#f59e0b',         // Orange - Secure Web traffic
  'HTTP-Alt': '#8b5cf6',      // Purple - Alternative HTTP port
  'HTTPS-Alt': '#ec4899',     // Pink - Alternative HTTPS port
  'HTTP/HTTPS-ALT': '#ec4899',// Pink - HTTP/HTTPS alternative port combination
  'WebSocket': '#4ade80',     // Light green - WebSocket
  'REST-API': '#22c55e',      // Green - REST API
  'JSON-API': '#16a34a',      // Dark green - JSON API
  'XML-Data': '#a3a3a3',      // Gray - XML data
  
  // Network Services Protocols
  'DNS': '#3b82f6',           // Blue - Domain Name System
  'mDNS': '#ec4899',          // Pink - Multicast DNS
  'MDNS': '#ec4899',          // Pink - Multicast DNS (uppercase alias)
  'DoH': '#8b5cf6',           // Purple - DNS over HTTPS
  'DoT': '#a855f7',           // Light purple - DNS over TLS
  'DHCP': '#8b5cf6',          // Purple - Dynamic Host Configuration Protocol
  'NTP': '#a855f7',           // Light purple - Network Time Protocol
  'SNMP': '#c084fc',          // Light purple - Simple Network Management Protocol
  'SNMP-Trap': '#d8b4fe',     // Lighter purple - SNMP traps
  'Syslog': '#e9d5ff',         // Light purple - System logs
  
  // Discovery and Announcement Protocols
  'UPnP/SSDP': '#34d399',     // Teal green - Device discovery
  'UPnP-SSDP': '#34d399',     // Teal green - UPnP SSDP
  'SSDP': '#34d399',          // Teal green - Simple Service Discovery Protocol
  'NetBIOS': '#4ade80',        // Green - NetBIOS
  'LLDP': '#67e8f9',          // Light cyan - Link Layer Discovery Protocol
  'Multicast-DNS': '#ec4899',  // Pink - Multicast DNS
  'mDNS-SD': '#f97316',       // Orange - mDNS service discovery
  
  // File Transfer Protocols
  'FTP': '#f59e0b',           // Orange - File transfer
  'FTP-Data': '#d97706',      // Dark orange - FTP data channel
  'SFTP': '#dc2626',          // Red - Secure Shell
  'SSH/SFTP': '#dc2626',      // Red - Secure Shell
  'TFTP': '#15803D',          // Dark green - Simple File Transfer Protocol
  
  // Mail Protocols
  'SMTP': '#7c3aed',          // Purple - Mail sending
  'SMTP-TLS': '#6d28d9',      // Dark purple - Secure mail
  'SMTPS': '#a21caf',         // Dark pink - Secure SMTP
  'POP3': '#c026d3',          // Pink - Mail receiving
  'POP3S': '#a21caf',         // Dark pink - Secure POP3
  'IMAP': '#db2777',          // Pink - IMAP protocol
  'IMAPS': '#be185d',          // Dark pink - Secure IMAP
  
  // IoT and Message Protocols
  'MQTT': '#06b6d4',          // Cyan - IoT message
  'MQTT-TLS': '#0891b2',      // Dark cyan - Secure MQTT
  'MQTT-KeepAlive': '#0284c7', // Blue cyan - MQTT heartbeat
  'MQTT-Data': '#67e8f9',     // Light cyan - MQTT data
  'CoAP': '#f59e0b',          // Orange - CoAP protocol
  'CoAP-DTLS': '#8b5cf6',      // Purple - Secure CoAP
  'CoAP-Secure': '#ec4899',   // Pink - Secure CoAP
  'AMQP': '#ef4444',          // Red - Advanced Message Queuing Protocol
  
  // Media and Streaming Protocols
  'RTSP': '#f97316',          // Orange - Real-time Streaming Protocol
  'RTMP': '#dc2626',          // Red - Media streaming
  'RTP': '#8b5cf6',           // Purple - Real-time Transport
  'RTP/RTCP': '#ec4899',       // Pink - Real-time media
  'Media-Stream': '#06b6d4',   // Cyan - Media streaming
  'High-Volume-Media': '#14b8a6', // Green - High-volume media
  
  // Database Protocols
  'MySQL': '#10b981',         // Green - MySQL database
  'PostgreSQL': '#f59e0b',    // Orange - PostgreSQL
  'Oracle': '#dc2626',         // Red - Oracle database
  'SQL-Server': '#8b5cf6',     // Purple - SQL Server
  'MongoDB': '#ec4899',        // Pink - MongoDB
  'Redis': '#06b6d4',          // Cyan - Redis cache
  
  // Remote Access Protocols
  'SSH': '#1F2937',           // Dark gray - Secure Shell protocol
  'Telnet': '#ef4444',         // Red - Telnet
  'RDP': '#8b5cf6',           // Purple - Remote Desktop
  'VNC': '#ec4899',           // Pink - VNC
  'SMB/CIFS': '#f59e0b',       // Orange - File sharing
  
  // Directory Service Protocols
  'LDAP': '#a3a3a3',           // Gray - LDAP
  'LDAPS': '#8b5cf6',          // Purple - Secure LDAP
  
  // VPN and Security Protocols
  'IKE': '#f59e0b',           // Orange - Key exchange
  'IPSec-NAT': '#ec4899',      // Pink - IPSec NAT traversal
  'OpenVPN': '#06b6d4',        // Cyan - OpenVPN
  'VPN-Tunnel': '#22c55e',      // Green - VPN tunnel
  
  // IoT Specific Protocols
  'IoT-TCP': '#06b6d4',        // Cyan - IoT TCP
  'IoT-UDP': '#8b5cf6',        // Purple - IoT UDP
  'IoT-Local': '#22c55e',       // Green - IoT local connection
  'IoT-Remote': '#f59e0b',      // Orange - IoT remote connection
  'IoT-Sensor-Telemetry': '#ec4899', // Pink - IoT sensor telemetry
  'Simple-Device': '#f3f4f6',   // Light gray - Simple device
  
  // Encryption and Data Types
  'Encrypted-Data': '#dc2626', // Red - Encrypted data
  'TLS': '#8b5cf6',           // Purple - Transport Layer Security
  'Bulk-Transfer': '#f59e0b',  // Orange - Bulk transfer
  'Bulk-Data': '#06b6d4',     // Cyan - Bulk data
  
  // Connection and Control Protocols
  'TCP-KeepAlive': '#ec4899',  // Pink - TCP heartbeat
  'TCP-Other': '#8b5cf6',      // Purple - Other TCP
  'TCP-Data': '#f59e0b',      // Orange - TCP data
  'UDP-Other': '#06b6d4',      // Cyan - Other UDP
  'UDP-Control': '#22c55e',    // Green - UDP control
  
  // Protocol Groups and Unknown Types
  'PROTO_89': '#EC4899',      // Pink - Protocol 89 (OSPF)
  'PROTO_1': '#EF4444',       // Red - Protocol 1 (ICMP)
  'PROTO_6': '#3B82F6',       // Blue - Protocol 6 (TCP)
  'PROTO_17': '#10B981',      // Green - Protocol 17 (UDP)
  'PROTO_2': '#F97316',       // Orange - Protocol 2 (IGMP)
  'Unknown': '#6b7280',       // Gray - Unknown protocol
  'OTHER': '#9ca3af',          // Light gray - Other protocol
  'Default': '#e5e7eb'         // Light gray - Default color
};

//Port Status Color Mapping
// Based on port analysis states in data_analyzer.py
export const PORT_STATUS_COLORS: Record<string, string> = {
  // Activity Levels
  'very_active': '#7f1d1d',    // Darker red - Very active
  'active': '#22c55e',         // Green - Active port
  'moderate': '#f59e0b',       // Orange - Moderate activity
  'low_activity': '#cbd5e1',   // Light blue gray - Low activity
  'high_activity': '#dc2626',  // Red - High activity
  
  // Communication Patterns
  'bidirectional': '#3b82f6',  // Blue - Bidirectional communication
  'outbound': '#06B6D4',       // Cyan - Outbound traffic
  'inbound': '#8B5CF6',        // Purple - Inbound traffic
  
  // Connection States
  'open': '#22C55E',           // Green - Open
  'closed': '#EF4444',         // Red - Closed
  'filtered': '#F59E0B',       // Orange - Filtered
  'blocked': '#7f1d1d',        // Dark red - Blocked
  'listening': '#059669',      // Dark green - Listening
  
  // Security Levels
  'insecure': '#EF4444',       // Red - Insecure
  'encrypted': '#059669',      // Dark cyan green - Encrypted
  'privileged': '#7c2d12',     // Brown - Privileged port
  'standard': '#6B7280',       // Gray - Standard port
  
  // Usage Patterns
  'system': '#dc2626',         // Red - System port (0-1023)
  'user': '#22c55e',           // Green - User port (1024-49151)
  'dynamic': '#3b82f6',        // Blue - Dynamic port (49152-65535)
  
  // General States
  'inactive': '#ef4444',       // Red - Inactive port
  'unknown': '#6b7280',        // Light gray - Unknown state
  'error': '#DC2626'           // Dark red - Error state
};

// Device Type Color Mapping
// Based on device classification in device_analyzer.py
export const DEVICE_TYPE_COLORS: Record<string, string> = {
  // Network Infrastructure
  'router': '#3b82f6',         // Blue - Router
  'gateway': '#2563eb',        // Dark blue - Gateway
  'switch': '#EC4899',         // Pink - Switch
  'hub': '#F97316',            // Orange - Hub
  'access_point': '#D97706',   // Dark orange - Access point
  
  // Computing Devices
  'computer': '#10b981',       // Green - Computer
  'laptop': '#2563EB',         // Dark blue - Laptop
  'server': '#059669',         // Dark green - Server
  'workstation': '#1E40AF',    // Dark blue - Workstation
  
  // Mobile Devices
  'mobile': '#34d399',         // Light green - Mobile device
  'smartphone': '#7C3AED',     // Dark purple - Smartphone
  'tablet': '#6D28D9',         // Darker purple - Tablet
  
  // IoT Devices
  'iot': '#06b6d4',            // Cyan - IoT device
  'iot_device': '#0891b2',     // Dark cyan - IoT device
  'iot_sensor': '#67e8f9',     // Light cyan - IoT sensor
  'smart_device': '#22d3ee',   // Light cyan - Smart device
  'sensor': '#14B8A6',         // Cyan - Sensor
  'actuator': '#0D9488',       // Dark cyan - Actuator
  
  // Media Devices
  'camera': '#f97316',         // Orange - Camera
  'ip_camera': '#B91C1C',      // Dark red - IP camera
  'media_player': '#991B1B',   // Darker red - Media player
  'tv': '#7F1D1D',             // Darkest red - TV
  'speaker': '#EF4444',        // Light red - Speaker
  
  // Home Automation
  'smart_home': '#84CC16',     // Green - Smart home
  'lighting': '#65A30D',       // Dark green - Lighting
  'thermostat': '#4ADE80',     // Light green - Thermostat
  'security_system': '#22C55E', // Green - Security system
  
  // Network Devices
  'network_device': '#1d4ed8', // Darker blue - Network device
  'active_device': '#1e40af',  // Dark blue - Active device
  'web_device': '#fb923c',     // Light orange - Web device
  
  // General Classification
  'unknown': '#6b7280',        // Gray - Unknown device
  'other': '#9CA3AF',          // Medium gray - Other device
  'simple_device': '#dbeafe'   // Light blue - Simple device
};

// Experiment and System Status Colors
export const EXPERIMENT_STATUS_COLORS: Record<string, string> = {
  'active': '#22C55E',         // Green - Active
  'running': '#10B981',        // Light green - Running
  'completed': '#3B82F6',      // Blue - Completed
  'paused': '#F59E0B',         // Orange - Paused
  'stopped': '#EF4444',        // Red - Stopped
  'failed': '#DC2626',         // Dark red - Failed
  'archived': '#6B7280',       // Gray - Archived
  'pending': '#8B5CF6'         // Purple - Pending
};

// Traffic and Activity Pattern Colors
export const TRAFFIC_PATTERN_COLORS: Record<string, string> = {
  // Time Patterns
  'normal': '#22c55e',         // Green - Normal traffic
  'business': '#059669',       // Dark green - Business time
  'evening': '#f59e0b',        // Orange - Evening activity
  'night': '#1e293b',          // Dark - Night traffic
  'weekend': '#7c3aed',        // Purple - Weekend traffic
  'morning_sync': '#fbbf24',   // Yellow - Morning sync
  'evening_activity': '#f59e0b', // Orange - Evening activity
  
  // Activity Intensity
  'low': '#cbd5e1',            // Light gray - Low traffic
  'peak': '#dc2626',           // Red - Peak traffic
  'burst': '#b91c1c',          // Dark red - Burst traffic
  'idle': '#f1f5f9',           // Very light gray - Idle state
  'active': '#16a34a',         // Dark green - Active state
  'high_activity': '#dc2626',  // Red - High activity
  'background_activity': '#9ca3af', // Light gray - Background activity
  
  // Connection Patterns
  'connection_establishment': '#3b82f6', // Blue - Connection establishment
  'data_transfer': '#2563eb',  // Dark blue - Data transfer
  'burst_activity': '#dc2626', // Red - Burst activity
  'idle_period': '#e2e8f0',    // Light gray - Idle period
  // IoT Patterns
  'sensor_telemetry': '#06b6d4', // Cyan - Sensor telemetry
  'iot_sensor_telemetry': '#0891b2', // Dark cyan - IoT sensor telemetry
  'firmware_update': '#8b5cf6', // Purple - Firmware update
  'discovery_scan': '#a855f7',        // Light purple - Discovery scan
  'discovery_announcement': '#c084fc', // Light purple - Discovery announcement
  'scheduled_maintenance': '#d97706',  // Dark orange - Scheduled maintenance
  
  // Special Events and System Activities
  'security_incident': '#dc2626', // Red - Security incident
  'maintenance_window': '#f59e0b', // Orange - Maintenance window
  'cloud_burst': '#0ea5e9',           // Blue - Cloud burst
  'infrastructure_traffic': '#6b7280', // Gray - Infrastructure traffic
  'high_volume_media': '#f97316',     // Orange - High-volume media
  'media_streaming': '#fb923c',       // Light orange - Media streaming
  'cloud_synchronization': '#0284c7', // Dark blue - Cloud synchronization
  'multi_service_burst': '#0369a1',   // Dark blue - Multi-service burst
  'high_volume_data': '#075985',      // Darker blue - High-volume data
  'sleep_mode_minimal': '#f1f5f9',    // Very light gray - Sleep mode minimal activity
  
  // IoT专用网络模式
  'local_iot_mesh': '#67e8f9',        // Light cyan - Local IoT network
  'iot_cloud_reporting': '#22d3ee',   // Light cyan - IoT cloud reporting
  'local_control': '#10b981',         // Light green - Local control
  'local_data': '#059669',            // Dark cyan green - Local data
  'cloud_sync': '#0ea5e9',            // Blue - Cloud sync
  'server_communication': '#3b82f6',  // Blue - Server communication
  'application_traffic': '#8b5cf6',   // Purple - Application traffic
  'connection_intensive': '#4b5563',  // Dark gray - Connection intensive
  'anomalous_behavior': '#dc2626',    // Red - Anomalous behavior
  
  // Default and unknown patterns
  'unknown': '#9ca3af',               // Light gray - Unknown pattern
  'default': '#e5e7eb'                // Light gray - Default pattern
};

// Network Topology and Connection Type Colors
export const CONNECTION_TYPE_COLORS: Record<string, string> = {
  'local': '#10B981',          // Green - Local connection
  'cloud': '#3B82F6',          // Blue - Cloud service
  'server': '#8B5CF6',         // Purple - Server connection
  'peer': '#F59E0B',           // Orange - Peer connection
  'multicast': '#EC4899',      // Pink - Multicast connection
  'broadcast': '#DC2626'       // Red - Broadcast connection
};

// Color Get Functions
export function getProtocolColor(protocol: string): string {
  const normalizedProtocol = protocol?.trim() || '';
  
  // Try direct match first
  if (PROTOCOL_COLORS[normalizedProtocol]) {
    return PROTOCOL_COLORS[normalizedProtocol];
  }
  
  // Try uppercase match next
  const upperProtocol = normalizedProtocol.toUpperCase();
  if (PROTOCOL_COLORS[upperProtocol]) {
    return PROTOCOL_COLORS[upperProtocol];
  }
  
  // Try lowercase match next
  const lowerProtocol = normalizedProtocol.toLowerCase();
  if (PROTOCOL_COLORS[lowerProtocol]) {
    return PROTOCOL_COLORS[lowerProtocol];
  }
  
  // Default to OTHER color
  return PROTOCOL_COLORS['OTHER'] || '#9ca3af';
}

export function getPortStatusColor(status: string): string {
  const normalizedStatus = status?.toLowerCase().trim() || '';
  return PORT_STATUS_COLORS[normalizedStatus] || PORT_STATUS_COLORS['unknown'];
}

export function getDeviceTypeColor(deviceType: string): string {
  const normalizedType = deviceType?.toLowerCase().trim() || '';
  return DEVICE_TYPE_COLORS[normalizedType] || DEVICE_TYPE_COLORS['unknown'];
}

export function getExperimentStatusColor(status: string): string {
  const normalizedStatus = status?.toLowerCase().trim() || '';
  return EXPERIMENT_STATUS_COLORS[normalizedStatus] || EXPERIMENT_STATUS_COLORS['active'];
}

export function getTrafficPatternColor(pattern: string): string {
  const normalizedPattern = pattern?.toLowerCase().trim() || '';
  return TRAFFIC_PATTERN_COLORS[normalizedPattern] || TRAFFIC_PATTERN_COLORS['normal'];
}

export function getConnectionTypeColor(type: string): string {
  const normalizedType = type?.toLowerCase().trim() || '';
  return CONNECTION_TYPE_COLORS[normalizedType] || CONNECTION_TYPE_COLORS['local'];
}

// Color Utility Functions
/**
 * Convert color to RGBA format (for semi-transparent effects)
 */
export const colorToRgba = (color: string, alpha: number = 1): string => {
  // Simple hex to rgba implementation
  const hex = color.replace('#', '');
  const r = parseInt(hex.substr(0, 2), 16);
  const g = parseInt(hex.substr(2, 2), 16);
  const b = parseInt(hex.substr(4, 2), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
};

/**
 * Alias for colorToRgba
 */
export const hexToRgba = colorToRgba;

export function generateColorPalette(count: number): string[] {
  const baseColors = [
    '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6',
    '#EC4899', '#14B8A6', '#F97316', '#6366F1', '#84CC16',
    '#06B6D4', '#F87171', '#A855F7', '#34D399', '#FBBF24'
  ];
  
  const palette: string[] = [];
  for (let i = 0; i < count; i++) {
    palette.push(baseColors[i % baseColors.length]);
  }
  return palette;
}

// Debug and Statistics Functions
export function getColorSystemStats(): {
  protocolCount: number;
  statusCount: number;
  deviceTypeCount: number;
  patternCount: number;
  totalDefinitions: number;
} {
  return {
    protocolCount: Object.keys(PROTOCOL_COLORS).length,
    statusCount: Object.keys(PORT_STATUS_COLORS).length,
    deviceTypeCount: Object.keys(DEVICE_TYPE_COLORS).length,
    patternCount: Object.keys(TRAFFIC_PATTERN_COLORS).length,
    totalDefinitions: Object.keys(PROTOCOL_COLORS).length + 
                     Object.keys(PORT_STATUS_COLORS).length + 
                     Object.keys(DEVICE_TYPE_COLORS).length + 
                     Object.keys(TRAFFIC_PATTERN_COLORS).length +
                     Object.keys(CONNECTION_TYPE_COLORS).length +
                     Object.keys(EXPERIMENT_STATUS_COLORS).length
  };
}

// Export all color systems for debugging
export const COLOR_SYSTEMS = {
  PROTOCOL_COLORS,
  PORT_STATUS_COLORS,
  DEVICE_TYPE_COLORS,
  TRAFFIC_PATTERN_COLORS
}; 
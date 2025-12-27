import React, { useState, useEffect, useMemo } from 'react';
import { useApiData } from '../../hooks/useApiData';
import { useTimezoneAwareApi } from '../../hooks/useTimezoneAwareApi';
import TimeWindowSelector from '../ui/TimeWindowSelector';
import { getProtocolColor as globalGetProtocolColor } from '../../styles/colors';
import { WS_TOPICS } from '../../config/api';
import { 
  NetworkIcon, 
  FilterIcon, 
  DeviceIcon, 
  GlobeIcon, 
  SatelliteIcon, 
  ListIcon, 
  CheckIcon, 
  CloseIcon 
} from '../ui/icons';

interface NetworkTopologyChartProps {
  deviceId: string;
  experimentId?: string | null;
  className?: string;
}

interface NetworkTopologyMetadata {
  device_id: string;
  time_window: string;
  total_nodes: number;
  total_edges: number;
  ip_mac_mappings: number;
  node_categories?: {
    real_devices: number;
    important_external: number;
    secondary_external: number;
    displayed_real_devices: number;
    displayed_important: number;
    displayed_secondary: number;
  };
  filtering_applied?: boolean;
  edge_gravity_enabled?: boolean;
  max_strength?: number;
  min_strength?: number;
}

interface NetworkNode {
  id: string;
  label: string;
  type: 'device' | 'gateway' | 'server' | 'dns' | 'cloud';
  ip?: string;
  macAddress?: string;
  resolved_label?: string;
  resolvedVendor?: string;
  resolvedType?: string;
  resolutionSource?: string;
  size: number;
  color: string;
  x?: number;
  y?: number;
  // Edge Gravity enhancement fields
  category?: 'real_device' | 'important_external' | 'secondary_external' | 'low_priority';
  importance_score?: number;
}

interface NetworkEdge {
  id: string;
  source: string;
  target: string;
  protocol: string;
  packets: number;
  bytes: number;
  weight: number;
  strength: number;
}

const NetworkTopologyChart: React.FC<NetworkTopologyChartProps> = ({ deviceId, experimentId, className }) => {
  const [selectedWindow, setSelectedWindow] = useState('48h');
  const [showFilters, setShowFilters] = useState(false);
  const [strengthThreshold, setStrengthThreshold] = useState(0.0);
  const [showExternalNodes, setShowExternalNodes] = useState(true);
  const [showLowPriorityNodes, setShowLowPriorityNodes] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  
  const { getDeviceNetworkTopology, formatTimestamp, timezoneInfo } = useTimezoneAwareApi({
    experimentId: experimentId || '',
    deviceId
  });

  const { data: topologyData, loading, error, refetch } = useApiData({
    fetchFn: () => getDeviceNetworkTopology(deviceId, selectedWindow, experimentId || undefined),
    wsTopics: [WS_TOPICS.DEVICE_NETWORK_TOPOLOGY(deviceId)],
    dependencies: [deviceId, selectedWindow, experimentId, timezoneInfo?.timezone, refreshTrigger],
    timeWindow: selectedWindow,
    enabled: !!deviceId && !!experimentId
  });

  // Listen for timezone change events
  React.useEffect(() => {
    const handleTimezoneChange = (event: CustomEvent) => {
      console.log('NetworkTopologyChart received timezone change event:', event.detail);
      // Trigger refresh by updating the refresh trigger
      setRefreshTrigger(prev => prev + 1);
      // Also manually refetch data
      setTimeout(() => {
        refetch(false); // Refetch without showing loading
      }, 200);
    };

    window.addEventListener('timezoneChanged', handleTimezoneChange as EventListener);
    
    return () => {
      window.removeEventListener('timezoneChanged', handleTimezoneChange as EventListener);
    };
  }, [refetch]);
  const [nodes, setNodes] = useState<NetworkNode[]>([]);
  const [edges, setEdges] = useState<NetworkEdge[]>([]);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  useEffect(() => {
    try {
      if (topologyData) {
        // Verify the data structure returned by the API
        if (!topologyData) {
          setNodes([]);
          setEdges([]);
          return;
        }
        
        // Ensure nodes and edges exist and are arrays
        const nodes = Array.isArray(topologyData.nodes) ? topologyData.nodes : [];
        const edges = Array.isArray(topologyData.edges) ? topologyData.edges : [];
        
        setNodes(processNodes(nodes));
        setEdges(processEdges(edges));
      }
    } catch (error) {
      setNodes([]);
      setEdges([]);
    }
  }, [topologyData]);

  const processNodes = (apiNodes: any[]): NetworkNode[] => {
    if (!Array.isArray(apiNodes)) {
      return [];
    }
    
    return apiNodes.map(node => ({
      id: node.id || `node-${Math.random()}`,
      label: node.resolved_label || node.label || 'Unknown',
      type: node.type || 'device',
      ip: node.ip,
      macAddress: node.macAddress,
      resolved_label: node.resolved_label,
      resolvedVendor: node.resolvedVendor,
      resolvedType: node.resolvedType,
      resolutionSource: node.resolutionSource,
      size: node.size || 25,
      color: node.color || '#3B82F6',
      // Edge Gravity enhancement fields
      category: node.category,
      importance_score: node.importance_score
    }));
  };

  const processEdges = (apiEdges: any[]): NetworkEdge[] => {
    if (!Array.isArray(apiEdges)) {
      return [];
    }
    
    return apiEdges.map((edge, index) => ({
      // Create a truly unique ID that includes index to avoid duplicates
      id: `edge-${edge.source || 'unknown'}-${edge.target || 'unknown'}-${edge.protocol || 'TCP'}-${index}-${Date.now()}`,
      source: edge.source || '',
      target: edge.target || '',
      protocol: edge.protocol || 'TCP',
      packets: edge.packets || 0,
      bytes: edge.bytes || 0,
      weight: edge.weight || Math.max(1, Math.floor((edge.strength || 0.5) * 8)),
      strength: edge.strength || 0.5
    }));
  };

  // Simplified filtering based on Edge Gravity strength and node types
  const filteredNodes = useMemo(() => {
    return nodes.filter(node => {
      // Always show real devices
      if (node.category === 'real_device') {
        return true;
      }
      
      // External nodes filter
      if (node.category === 'important_external' || node.category === 'secondary_external') {
        return showExternalNodes;
      }
      
      // Low priority nodes filter
      if (node.category === 'low_priority') {
        return showLowPriorityNodes;
      }
      
      return true;
    });
  }, [nodes, showExternalNodes, showLowPriorityNodes]);

  const filteredEdges = useMemo(() => {
    const nodeIds = new Set(filteredNodes.map(n => n.id));
    return edges.filter(edge => {
      // Only show edges between visible nodes
      if (!nodeIds.has(edge.source) || !nodeIds.has(edge.target)) {
        return false;
      }
      // Strength threshold filter
      if (edge.strength < strengthThreshold) {
        return false;
      }
      return true;
    });
  }, [edges, filteredNodes, strengthThreshold]);

  // Enhanced layout algorithm based on Edge Gravity importance
  const calculateIntelligentLayout = () => {
    if (filteredNodes.length === 0) return new Map();

    const svgWidth = 800;
    const svgHeight = 600;
    const centerX = svgWidth / 2;
    const centerY = svgHeight / 2;
    const positions = new Map();

    // 1. Position real devices in the center area
    const realDevices = filteredNodes.filter(n => n.category === 'real_device');
    const importantNodes = filteredNodes.filter(n => n.category === 'important_external');
    const secondaryNodes = filteredNodes.filter(n => n.category === 'secondary_external');

    // Center area for real devices
    if (realDevices.length > 0) {
      const mainDevice = realDevices.find(n => n.resolutionSource === 'known_device') || realDevices[0];
      positions.set(mainDevice.id, { x: centerX, y: centerY });

      // Position other real devices around the main device
      const otherRealDevices = realDevices.filter(n => n.id !== mainDevice.id);
      const innerRadius = 80;
      
      otherRealDevices.forEach((node, index) => {
        const angle = (index * 2 * Math.PI) / otherRealDevices.length;
        const x = centerX + innerRadius * Math.cos(angle);
        const y = centerY + innerRadius * Math.sin(angle);
        positions.set(node.id, { x, y });
      });
    }

    // 2. Position important external nodes in middle ring
    const middleRadius = 180;
    importantNodes.forEach((node, index) => {
      const angle = (index * 2 * Math.PI) / importantNodes.length;
      const x = centerX + middleRadius * Math.cos(angle);
      const y = centerY + middleRadius * Math.sin(angle);
      positions.set(node.id, { x, y });
    });

    // 3. Position secondary nodes in outer ring
    const outerRadius = 260;
    secondaryNodes.forEach((node, index) => {
      const angle = (index * 2 * Math.PI) / secondaryNodes.length;
      const x = centerX + outerRadius * Math.cos(angle);
      const y = centerY + outerRadius * Math.sin(angle);
      positions.set(node.id, { x, y });
    });

    return positions;
  };

  // Get node visualization properties based on category and importance
  const getNodeVisualization = (node: NetworkNode) => {
    const baseSize = node.size || 25;
    let size = baseSize;
    let strokeWidth = 2;
    let glowEffect = false;

    switch (node.category) {
      case 'real_device':
        size = baseSize + 8; // Larger for real devices
        strokeWidth = 3;
        glowEffect = true;
        break;
      case 'important_external':
        size = baseSize + 4; // Medium size for important external
        strokeWidth = 2;
        break;
      case 'secondary_external':
        size = baseSize; // Normal size
        strokeWidth = 1;
        break;
      default:
        size = baseSize - 2; // Smaller for low priority
        strokeWidth = 1;
        break;
    }

    return { size, strokeWidth, glowEffect };
  };

  const handleNodeClick = (nodeId: string) => {
    setSelectedNode(selectedNode === nodeId ? null : nodeId);
  };

  const getSelectedNodeConnections = () => {
    if (!selectedNode) return [];
    return edges.filter(edge => edge.source === selectedNode || edge.target === selectedNode);
  };

  const getSelectedNodeInfo = () => {
    if (!selectedNode) return null;
    return nodes.find(node => node.id === selectedNode);
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // Use global color system exclusively - no local color definitions
  const getProtocolColor = (protocol: string): string => {
    // Use global color system exclusively for unified color management
    return globalGetProtocolColor(protocol);
  };

  const renderNodeIcon = (node: NetworkNode, nodeId: string) => {
    const iconProps = {
      fill: "#fff",
      stroke: "#fff",
      strokeWidth: "1.5"
    };

    switch (node.type) {
      case 'device':
        return (
          <rect 
            key={`${nodeId}-icon`}
            x="6" y="8" width="12" height="8" rx="1" 
            fill="#fff" strokeWidth="1" stroke="rgba(0,0,0,0.3)" 
          />
        );
      
      case 'gateway':
        return (
          <g key={`${nodeId}-icon-group`}>
            <circle key={`${nodeId}-outer`} cx="12" cy="12" r="6" fill="none" stroke="#fff" strokeWidth="1.5" />
            <circle key={`${nodeId}-middle`} cx="12" cy="12" r="4" fill="none" stroke="#fff" strokeWidth="1" />
            <circle key={`${nodeId}-inner`} cx="12" cy="12" r="2" fill="#fff" />
          </g>
        );
      
      case 'server':
        return (
          <g key={`${nodeId}-icon-group`}>
            <rect key={`${nodeId}-rack1`} x="6" y="6" width="12" height="3" rx="0.5" fill="none" stroke="#fff" strokeWidth="1" />
            <rect key={`${nodeId}-rack2`} x="6" y="10" width="12" height="3" rx="0.5" fill="none" stroke="#fff" strokeWidth="1" />
            <rect key={`${nodeId}-rack3`} x="6" y="14" width="12" height="3" rx="0.5" fill="none" stroke="#fff" strokeWidth="1" />
            <circle key={`${nodeId}-led1`} cx="8" cy="7.5" r="0.5" fill="#fff" />
            <circle key={`${nodeId}-led2`} cx="8" cy="11.5" r="0.5" fill="#fff" />
            <circle key={`${nodeId}-led3`} cx="8" cy="15.5" r="0.5" fill="#fff" />
          </g>
        );
      
      default:
        return (
          <rect 
            key={`${nodeId}-icon`}
            x="6" y="8" width="12" height="8" rx="1" 
            fill="#fff" strokeWidth="1" stroke="rgba(0,0,0,0.3)" 
          />
        );
    }
  };

  const renderTopology = () => {
    if (nodes.length === 0) return null;

    const svgWidth = 800;
    const svgHeight = 600;
    const nodePositions = calculateIntelligentLayout();

    return (
      <svg 
        width={svgWidth} 
        height={svgHeight} 
        style={{ 
          backgroundColor: 'var(--color-bg-secondary)', 
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--color-border-primary)'
        }}
      >
        {/* Render edges */}
        {filteredEdges.map((edge, index) => {
          const sourcePos = nodePositions.get(edge.source);
          const targetPos = nodePositions.get(edge.target);
          
          if (!sourcePos || !targetPos) return null;
          
          const isHighlighted = selectedNode && (edge.source === selectedNode || edge.target === selectedNode);
          const isConnected = hoveredNode && (edge.source === hoveredNode || edge.target === hoveredNode);
          
          // Create a truly unique edge ID using source, target, protocol and index to avoid duplicates
          // Include protocol, weight, bytes, and packets to distinguish bidirectional connections
          const edgeKey = `edge-${edge.source}-${edge.target}-${edge.protocol}-${edge.weight}-${edge.bytes}-${edge.packets}-${index}`;
          
          return (
            <g key={edgeKey}>
              <line
                x1={sourcePos.x}
                y1={sourcePos.y}
                x2={targetPos.x}
                y2={targetPos.y}
                stroke={isHighlighted ? getProtocolColor(edge.protocol || 'Unknown') : '#6B7280'}
                strokeWidth={isHighlighted ? Math.min(edge.weight + 2, 8) : Math.min(edge.weight, 6)}
                strokeDasharray={edge.protocol === 'DNS' ? '5,5' : 'none'}
                opacity={isHighlighted || isConnected ? 1 : 0.8}
                style={{ transition: 'all 0.3s ease' }}
              />
              
              {isHighlighted && (
                <text
                  x={(sourcePos.x + targetPos.x) / 2}
                  y={(sourcePos.y + targetPos.y) / 2 - 8}
                  fill="var(--color-text-secondary)"
                  fontSize="11"
                  textAnchor="middle"
                  style={{
                    backgroundColor: 'var(--color-bg-primary)',
                    padding: '2px 4px',
                    borderRadius: '2px'
                  }}
                >
                  {edge.protocol}
                </text>
              )}
            </g>
          );
        })}

        {/* Render nodes */}
        {filteredNodes.map((node, index) => {
          const pos = nodePositions.get(node.id);
          if (!pos) return null;

          const isSelected = selectedNode === node.id;
          const isHovered = hoveredNode === node.id;
          const isConnected = selectedNode && edges.some(edge => 
            (edge.source === selectedNode && edge.target === node.id) ||
            (edge.target === selectedNode && edge.source === node.id)
          );

          const { size, strokeWidth, glowEffect } = getNodeVisualization(node);
          
          // Create a safe node ID
          const nodeId = node.id || `node-${node.type}-${index}`;

          return (
            <g 
              key={`node-group-${nodeId}`}
              style={{ cursor: 'pointer' }}
              onClick={() => handleNodeClick(nodeId)}
              onMouseEnter={() => setHoveredNode(nodeId)}
              onMouseLeave={() => setHoveredNode(null)}
            >
              <circle
                key={`circle-${nodeId}`}
                cx={pos.x}
                cy={pos.y}
                r={size}
                fill={node.color}
                stroke={isSelected ? 'var(--color-accent-blue)' : isHovered ? 'var(--color-text-secondary)' : 'var(--color-bg-primary)'}
                strokeWidth={strokeWidth}
                opacity={!selectedNode || isSelected || isConnected ? 1 : 0.4}
                style={{
                  filter: isSelected ? 'drop-shadow(0 0 12px rgba(59, 130, 246, 0.6))' : 
                          isHovered ? 'drop-shadow(0 0 8px rgba(0, 0, 0, 0.3))' : 'none',
                  transition: 'all 0.3s ease'
                }}
              />
              
              <g 
                key={`icon-container-${nodeId}`}
                transform={`translate(${pos.x - 12}, ${pos.y - 12})`}
                opacity={!selectedNode || isSelected || isConnected ? 1 : 0.4}
              >
                {renderNodeIcon(node, nodeId)}
              </g>
              
              <text
                key={`text-${nodeId}`}
                x={pos.x}
                y={pos.y + size + 18}
                fill={isSelected ? 'var(--color-text-primary)' : 'var(--color-text-secondary)'}
                fontSize="12"
                textAnchor="middle"
                fontWeight={isSelected ? 'bold' : '600'}
                opacity={!selectedNode || isSelected || isConnected ? 1 : 0.4}
              >
                {node.resolved_label || node.label}
              </text>
              
              {node.ip && (
                <text
                  key={`ip-${nodeId}`}
                  x={pos.x}
                  y={pos.y + size + 32}
                  fill="var(--color-text-tertiary)"
                  fontSize="10"
                  textAnchor="middle"
                  opacity={!selectedNode || isSelected || isConnected ? 1 : 0.4}
                  fontFamily="monospace"
                >
                  {node.ip}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    );
  };

  if (loading && !topologyData) {
    return (
      <div className={className} style={{
        backgroundColor: 'var(--color-bg-secondary)',
        border: '1px solid var(--color-border-primary)',
        borderRadius: 'var(--radius-lg)',
        padding: 'var(--card-padding-lg)',
        textAlign: 'center'
      }}>
        <div style={{
          width: 'var(--spacing-3xl)',
          height: 'var(--spacing-3xl)',
          border: '2px solid var(--color-border-primary)',
          borderTop: '2px solid var(--color-accent-blue)',
          borderRadius: '50%',
          margin: '0 auto var(--spacing-lg)',
          animation: 'spin 1s linear infinite'
        }}></div>
        <div style={{ color: 'var(--color-text-tertiary)' }}>
          Loading network topology...
        </div>
      </div>
    );
  }

  const selectedNodeInfo = getSelectedNodeInfo();
  const selectedConnections = getSelectedNodeConnections();
  const metadata = topologyData?.metadata;

  return (
    <div className={className} style={{
      backgroundColor: 'var(--color-bg-secondary)',
      border: '1px solid var(--color-border-primary)',
      borderRadius: 'var(--radius-lg)',
      padding: 'var(--card-padding-lg)'
    }}>
      <div style={{ marginBottom: 'var(--spacing-xl)' }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          marginBottom: 'var(--spacing-md)',
          flexWrap: 'wrap',
          gap: 'var(--spacing-md)'
        }}>
          <div>
            <h3 className="text-responsive-xl" style={{
              color: 'var(--color-text-primary)',
              fontWeight: 'bold',
              margin: '0 0 var(--spacing-xs) 0',
              lineHeight: '1.3'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <NetworkIcon size={18} color="#3B82F6" />
              Network Topology ({selectedWindow.toUpperCase()})
              {metadata?.filtering_applied && (
                <span style={{
                  backgroundColor: 'var(--color-accent-green)',
                  color: 'white',
                  padding: '2px 6px',
                  borderRadius: '4px',
                  fontSize: '10px',
                  fontWeight: 'bold'
                }}>
                  SMART FILTERED
                </span>
              )}
            </div>
            </h3>
            <p className="text-responsive-sm" style={{
              color: 'var(--color-text-tertiary)',
              margin: 0,
              lineHeight: '1.5'
            }}>
              {metadata?.edge_gravity_enabled ? 
                'Enhanced with Edge Gravity algorithm • Click devices for details' :
                'Click on any device to view its connections'
              }
            </p>
          </div>

          <div style={{ display: 'flex', gap: 'var(--spacing-sm)', alignItems: 'center' }}>
            <button
              onClick={() => setShowFilters(!showFilters)}
              style={{
                backgroundColor: showFilters ? 'var(--color-accent-blue)' : 'var(--color-bg-primary)',
                color: showFilters ? 'white' : 'var(--color-text-secondary)',
                border: '1px solid var(--color-border-primary)',
                borderRadius: 'var(--radius-sm)',
                padding: 'var(--spacing-xs) var(--spacing-sm)',
                fontSize: 'var(--text-sm)',
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}
            >
              <FilterIcon size={14} color={showFilters ? 'white' : 'var(--color-text-secondary)'} />
              <span style={{ marginLeft: 'var(--spacing-xs)' }}>Filters</span>
            </button>
            <TimeWindowSelector
              selectedWindow={selectedWindow}
              onWindowChange={setSelectedWindow}
              size="sm"
            />
          </div>
        </div>

        {/* Filtering Controls Panel */}
        {showFilters && (
          <div style={{
            backgroundColor: 'var(--color-bg-primary)',
            border: '1px solid var(--color-border-primary)',
            borderRadius: 'var(--radius-md)',
            padding: 'var(--card-padding-md)',
            marginBottom: 'var(--spacing-md)'
          }}>
            <h4 style={{
              color: 'var(--color-text-primary)',
              fontSize: 'var(--text-sm)',
              fontWeight: 'bold',
              margin: '0 0 var(--spacing-md) 0'
            }}>
              Visualization Filters
            </h4>

            {/* Simplified Node Filters */}
            <div style={{ marginBottom: 'var(--spacing-lg)' }}>
              <div style={{
                color: 'var(--color-text-secondary)',
                fontSize: 'var(--text-xs)',
                marginBottom: 'var(--spacing-sm)',
                fontWeight: '600'
              }}>
                Display Options
              </div>
              <div style={{
                display: 'flex',
                flexDirection: 'column',
                gap: 'var(--spacing-sm)'
              }}>
                {/* Real devices are always shown */}
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 'var(--spacing-xs)',
                  padding: 'var(--spacing-xs)',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: 'var(--color-bg-secondary)'
                }}>
                  <DeviceIcon size={14} color="#10B981" />
                  <span style={{
                    fontSize: 'var(--text-xs)',
                    color: 'var(--color-text-secondary)'
                  }}>
                    Real Devices (Always shown)
                  </span>
                  {metadata?.node_categories && (
                    <span style={{
                      backgroundColor: '#10B981',
                      color: 'white',
                      padding: '1px 4px',
                      borderRadius: '2px',
                      fontSize: '10px',
                      fontWeight: 'bold'
                    }}>
                      {metadata?.node_categories?.displayed_real_devices}
                    </span>
                  )}
                </div>

                {/* External nodes toggle */}
                <label style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 'var(--spacing-xs)',
                  cursor: 'pointer',
                  padding: 'var(--spacing-xs)',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: showExternalNodes ? 'var(--color-bg-secondary)' : 'transparent'
                }}>
                  <input
                    type="checkbox"
                    checked={showExternalNodes}
                    onChange={(e) => setShowExternalNodes(e.target.checked)}
                    style={{ accentColor: '#3B82F6' }}
                  />
                  <GlobeIcon size={14} color="#3B82F6" />
                  <span style={{
                    fontSize: 'var(--text-xs)',
                    color: 'var(--color-text-secondary)'
                  }}>
                    External Nodes
                  </span>
                  {metadata?.node_categories && (
                    <span style={{
                      backgroundColor: '#3B82F6',
                      color: 'white',
                      padding: '1px 4px',
                      borderRadius: '2px',
                      fontSize: '10px',
                      fontWeight: 'bold'
                    }}>
                                        {(metadata?.node_categories?.displayed_important || 0) +
                  (metadata?.node_categories?.displayed_secondary || 0)}
                    </span>
                  )}
                </label>

                {/* Low priority nodes toggle */}
                <label style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 'var(--spacing-xs)',
                  cursor: 'pointer',
                  padding: 'var(--spacing-xs)',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: showLowPriorityNodes ? 'var(--color-bg-secondary)' : 'transparent'
                }}>
                  <input
                    type="checkbox"
                    checked={showLowPriorityNodes}
                    onChange={(e) => setShowLowPriorityNodes(e.target.checked)}
                    style={{ accentColor: '#9CA3AF' }}
                  />
                  <ListIcon size={14} color="#9CA3AF" />
                  <span style={{
                    fontSize: 'var(--text-xs)',
                    color: 'var(--color-text-secondary)'
                  }}>
                    Low Priority Nodes
                  </span>
                </label>
              </div>
            </div>

            {/* Edge Strength Filter */}
            {metadata?.edge_gravity_enabled && (
              <div>
                <div style={{
                  color: 'var(--color-text-secondary)',
                  fontSize: 'var(--text-xs)',
                  marginBottom: 'var(--spacing-xs)',
                  fontWeight: '600'
                }}>
                  Edge Gravity Strength Threshold: {(strengthThreshold * 100).toFixed(0)}%
                </div>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={strengthThreshold}
                  onChange={(e) => setStrengthThreshold(parseFloat(e.target.value))}
                  style={{
                    width: '100%',
                    accentColor: 'var(--color-accent-blue)'
                  }}
                />
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  fontSize: 'var(--text-xs)',
                  color: 'var(--color-text-tertiary)',
                  marginTop: 'var(--spacing-xs)'
                }}>
                  <span>Show all ({filteredEdges.length} edges)</span>
                  <span>Show strongest only</span>
                </div>
              </div>
            )}

            {/* Statistics Summary */}
            {metadata && (
              <div style={{
                marginTop: 'var(--spacing-lg)',
                padding: 'var(--spacing-sm)',
                backgroundColor: 'var(--color-bg-secondary)',
                borderRadius: 'var(--radius-sm)',
                fontSize: 'var(--text-xs)',
                color: 'var(--color-text-tertiary)'
              }}>
                            <strong>Statistics:</strong> {filteredNodes.length}/{metadata?.total_nodes} nodes •
            {filteredEdges.length}/{metadata?.total_edges} edges •
            Edge Gravity: {metadata?.edge_gravity_enabled ? (
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '2px' }}>
                    <CheckIcon size={12} color="#10B981" />
                    <span>Enabled</span>
                  </span>
                ) : (
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '2px' }}>
                    <CloseIcon size={12} color="#EF4444" />
                    <span>Disabled</span>
                  </span>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: selectedNode ? '1fr 400px' : '1fr',
        gap: 'var(--spacing-xl)',
        alignItems: 'start'
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          overflowX: 'auto'
        }}>
          {renderTopology()}
        </div>

        {selectedNode && selectedNodeInfo && (
          <div style={{
            backgroundColor: 'var(--color-bg-primary)',
            border: '1px solid var(--color-border-primary)',
            borderRadius: 'var(--radius-md)',
            padding: 'var(--card-padding-lg)'
          }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: 'var(--spacing-lg)'
            }}>
              <h4 className="text-responsive-lg" style={{
                color: 'var(--color-text-primary)',
                fontWeight: 'bold',
                margin: 0
              }}>
                Connection Details
              </h4>
              <button
                onClick={() => setSelectedNode(null)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--color-text-tertiary)',
                  cursor: 'pointer',
                  fontSize: 'var(--text-lg)',
                  padding: 'var(--spacing-xs)'
                }}
              >
                ×
              </button>
            </div>
            
            <div style={{
              backgroundColor: 'var(--color-bg-secondary)',
              padding: 'var(--card-padding-md)',
              borderRadius: 'var(--radius-sm)',
              marginBottom: 'var(--spacing-lg)'
            }}>
              <div className="text-responsive-sm" style={{
                color: 'var(--color-text-tertiary)',
                marginBottom: 'var(--spacing-xs)'
              }}>
                Selected Device
              </div>
              <div className="text-responsive-lg" style={{
                color: 'var(--color-text-primary)',
                fontWeight: 'bold',
                marginBottom: 'var(--spacing-xs)'
              }}>
                {selectedNodeInfo.resolved_label || selectedNodeInfo.label}
              </div>
              
              {/* Resolution source indicator */}
              {selectedNodeInfo.resolutionSource && selectedNodeInfo.resolutionSource !== 'none' && (
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 'var(--spacing-xs)',
                  marginBottom: 'var(--spacing-xs)'
                }}>
                  <div style={{
                    width: '6px',
                    height: '6px',
                    borderRadius: '50%',
                    backgroundColor: selectedNodeInfo.resolutionSource === 'known_device' 
                      ? 'var(--color-accent-green)' 
                      : selectedNodeInfo.resolutionSource === 'vendor_pattern'
                      ? 'var(--color-accent-blue)'
                      : 'var(--color-text-tertiary)'
                  }} />
                  <span className="text-responsive-xs" style={{
                    color: 'var(--color-text-tertiary)',
                    textTransform: 'capitalize'
                  }}>
                    {selectedNodeInfo.resolutionSource === 'known_device' ? 'Known Device' :
                     selectedNodeInfo.resolutionSource === 'vendor_pattern' ? 'Vendor Pattern' : 'Original'}
                  </span>
                </div>
              )}

              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--spacing-sm)',
                marginBottom: 'var(--spacing-xs)'
              }}>
                <div
                  style={{
                    width: '12px',
                    height: '12px',
                    borderRadius: '50%',
                    backgroundColor: selectedNodeInfo.color
                  }}
                />
                <span className="text-responsive-sm" style={{
                  color: 'var(--color-text-secondary)',
                  textTransform: 'capitalize'
                }}>
                  {selectedNodeInfo.resolvedType || selectedNodeInfo.type}
                </span>
              </div>
              
              {/* Always show vendor information */}
              <div className="text-responsive-sm" style={{
                color: 'var(--color-text-secondary)',
                marginBottom: 'var(--spacing-xs)'
              }}>
                Vendor: {selectedNodeInfo.resolvedVendor || 'Unknown'}
              </div>
              
              {/* Always show IP */}
              <div className="text-responsive-sm" style={{
                color: 'var(--color-text-secondary)',
                fontFamily: 'monospace',
                marginBottom: 'var(--spacing-xs)'
              }}>
                IP: {selectedNodeInfo.ip || 'Unknown'}
              </div>

              {/* Always show MAC if available */}
              <div className="text-responsive-sm" style={{
                color: 'var(--color-text-secondary)',
                fontFamily: 'monospace',
                marginBottom: 'var(--spacing-xs)'
              }}>
                MAC: {selectedNodeInfo.macAddress || 'Not available'}
              </div>

              {/* Resolution source indicator */}
              {selectedNodeInfo.resolutionSource && selectedNodeInfo.resolutionSource !== 'none' && (
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  marginTop: 'var(--spacing-xs)',
                  fontSize: '11px',
                  color: 'var(--color-text-tertiary)'
                }}>
                  <div style={{
                    width: '6px',
                    height: '6px',
                    borderRadius: '50%',
                    backgroundColor: selectedNodeInfo.resolutionSource === 'known_device' ? '#10B981' : '#3B82F6',
                    marginRight: 'var(--spacing-xs)'
                  }} />
                  <span>
                    {selectedNodeInfo.resolutionSource === 'known_device' ? 'Known Device' : 'Vendor Pattern Match'}
                  </span>
                </div>
              )}
            </div>

            <div style={{
              backgroundColor: 'var(--color-bg-secondary)',
              padding: 'var(--card-padding-md)',
              borderRadius: 'var(--radius-sm)',
              marginBottom: 'var(--spacing-lg)'
            }}>
              <div className="text-responsive-sm" style={{
                color: 'var(--color-text-tertiary)',
                marginBottom: 'var(--spacing-xs)'
              }}>
                Active Connections
              </div>
              <div className="text-responsive-xl" style={{
                color: 'var(--color-accent-blue)',
                fontWeight: 'bold'
              }}>
                {selectedConnections.length}
              </div>
            </div>

            {selectedConnections.length > 0 && (
              <div>
                <h5 className="text-responsive-md" style={{
                  color: 'var(--color-text-primary)',
                  fontWeight: 'bold',
                  marginBottom: 'var(--spacing-md)'
                }}>
                  Connection Details
                </h5>
                <div style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 'var(--spacing-sm)',
                  maxHeight: '300px',
                  overflowY: 'auto'
                }}>
                  {selectedConnections.map((edge, index) => {
                    const targetNodeId = edge.source === selectedNode ? edge.target : edge.source;
                    const targetNode = nodes.find(n => n.id === targetNodeId);
                    
                    // Create a truly unique connection ID using multiple factors
                    const connectionId = `conn-${edge.source}-${edge.target}-${edge.protocol}-${edge.packets}-${edge.bytes}-${index}`;
                    
                    return (
                      <div
                        key={connectionId}
                        style={{
                          backgroundColor: 'var(--color-bg-secondary)',
                          padding: 'var(--card-padding-sm)',
                          borderRadius: 'var(--radius-sm)',
                          border: '1px solid var(--color-border-primary)'
                        }}
                      >
                        <div style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          marginBottom: 'var(--spacing-xs)'
                        }}>
                          <span className="text-responsive-sm" style={{
                            color: 'var(--color-text-primary)',
                            fontWeight: '600'
                          }}>
                            {targetNode?.label}
                          </span>
                          <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 'var(--spacing-xs)'
                          }}>
                            <div
                              style={{
                                width: '8px',
                                height: '8px',
                                borderRadius: '50%',
                                backgroundColor: getProtocolColor(edge.protocol || 'Unknown')
                              }}
                            />
                            <span style={{
                              backgroundColor: 'var(--color-bg-tertiary)',
                              color: 'var(--color-text-secondary)',
                              padding: 'var(--spacing-xs) var(--spacing-sm)',
                              borderRadius: 'var(--radius-xs)',
                              fontSize: 'var(--text-xs)',
                              fontWeight: '600'
                            }}>
                              {edge.protocol}
                            </span>
                          </div>
                        </div>
                        
                        <div className="text-responsive-xs" style={{
                          color: 'var(--color-text-tertiary)',
                          marginBottom: 'var(--spacing-xs)',
                          fontFamily: 'monospace'
                        }}>
                          {targetNode?.ip}
                        </div>
                        
                        <div style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          marginBottom: 'var(--spacing-xs)'
                        }}>
                          <span className="text-responsive-xs" style={{
                            color: 'var(--color-text-tertiary)'
                          }}>
                            {edge.packets.toLocaleString()} packets
                          </span>
                          <span className="text-responsive-xs" style={{
                            color: 'var(--color-text-tertiary)'
                          }}>
                            {formatBytes(edge.bytes)}
                          </span>
                        </div>
                        
                        <div style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 'var(--spacing-sm)'
                        }}>
                          <span className="text-responsive-xs" style={{
                            color: 'var(--color-text-tertiary)'
                          }}>
                            Strength:
                          </span>
                          <div style={{
                            flex: 1,
                            height: '4px',
                            backgroundColor: 'var(--color-bg-tertiary)',
                            borderRadius: 'var(--radius-xs)',
                            overflow: 'hidden'
                          }}>
                            <div style={{
                              width: `${edge.strength * 100}%`,
                              height: '100%',
                              backgroundColor: getProtocolColor(edge.protocol || 'Unknown'),
                              borderRadius: 'var(--radius-xs)'
                            }} />
                          </div>
                          <span className="text-responsive-xs" style={{
                            color: 'var(--color-text-secondary)',
                            fontFamily: 'monospace'
                          }}>
                            {(edge.strength * 100).toFixed(0)}%
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {selectedConnections.length === 0 && (
              <div style={{
                textAlign: 'center',
                padding: 'var(--spacing-xl)',
                color: 'var(--color-text-tertiary)'
              }}>
                No active connections found
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default NetworkTopologyChart; 
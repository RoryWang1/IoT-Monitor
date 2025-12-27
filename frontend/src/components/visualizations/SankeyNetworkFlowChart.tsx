import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { sankey, sankeyLinkHorizontal, SankeyNode, SankeyLink } from 'd3-sankey';
import Card from '../ui/Card';
import { ChartIcon, SearchIcon, WarningIcon } from '../ui/icons';

interface SankeyData {
  flow_type: string;
  nodes: Array<{
    id: string;
    name: string;
    category: string;
    value: number;
    color?: string;
    destination_count?: number;
    ip_count?: number;
  }>;
  links: Array<{
    source: string;
    target: string;
    value: number;
    color?: string;
    packets?: number;
  }>;
  metadata: {
    total_nodes: number;
    total_links: number;
    total_traffic: number;
    location_coverage?: number; // Added for device-to-location flow
  };
  time_window: string;
  group_by: string;
}

interface SankeyNetworkFlowChartProps {
  data: SankeyData | null;
  width?: number;
  height?: number;
  loading?: boolean;
  error?: string;
  title?: string;
  className?: string;
}

const SankeyNetworkFlowChart: React.FC<SankeyNetworkFlowChartProps> = ({
  data,
  width = 1200,  // 增大默认宽度
  height = 800,  // 增大默认高度
  loading = false,
  error = null,
  title = 'Network Flow Analysis',
  className = ''
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [tooltipData, setTooltipData] = useState<{
    x: number;
    y: number;
    content: string;
    visible: boolean;
  }>({ x: 0, y: 0, content: '', visible: false });

  // Color scheme functions (moved before useEffect to avoid dependency issues)
  const getNodeColor = (category: string): string => {
    const colors = {
      'source': '#3B82F6',      // Blue
      'target': '#10B981',      // Green
      'device': '#8B5CF6',      // Purple
      'protocol': '#F59E0B',    // Orange
      'service': '#06B6D4',     // Cyan
      'location': '#EC4899',    // Pink
      'default': '#6B7280'      // Gray
    };
    return colors[category as keyof typeof colors] || colors['default'];
  };

  const getLinkColor = React.useCallback((value: number): string => {
    const intensity = Math.min(1, value / (data?.metadata.total_traffic || 1));
    const opacity = 0.4 + (intensity * 0.6);
    return `rgba(59, 130, 246, ${opacity})`;
  }, [data?.metadata.total_traffic]);

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  useEffect(() => {
    if (!data || !svgRef.current) {
      return;
    }

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove(); // Clear previous chart

    const margin = { top: 60, right: 150, bottom: 60, left: 60 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    const g = svg
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Setup sankey layout
    const sankeyGenerator = sankey()
      .nodeWidth(25)
      .nodePadding(15)
      .extent([[1, 1], [innerWidth - 1, innerHeight - 1]]);

    // Transform data for D3 sankey with improved naming
    const nodes = data.nodes.map(node => ({
      id: node.id,
      name: node.name === 'unknown' ? 'Unknown Device' : node.name,
      category: node.category,
      value: node.value,
      color: node.color || getNodeColor(node.category)
    }));

    // Create a mapping from node ID to index
    const nodeIndexMap = new Map<string, number>();
    nodes.forEach((node, index) => {
      nodeIndexMap.set(node.id, index);
    });

    // Transform links to use node indices instead of IDs
    const links = data.links.map(link => {
      const sourceIndex = nodeIndexMap.get(link.source);
      const targetIndex = nodeIndexMap.get(link.target);
      
      if (sourceIndex === undefined || targetIndex === undefined) {
        console.warn('Missing node reference:', { source: link.source, target: link.target });
        return null;
      }
      
      return {
        source: sourceIndex,
        target: targetIndex,
        value: link.value,
        color: link.color || getLinkColor(link.value)
      };
    }).filter(link => link !== null);

    // Smart circular link detection and removal
    const processedLinks = smartCircularLinkDetection(nodes, links);

    const graph = {
      nodes: nodes,
      links: processedLinks
    };

    if (processedLinks.length === 0) {
      // Show improved message when no valid links remain
      g.append('text')
        .attr('x', innerWidth / 2)
        .attr('y', innerHeight / 2 - 10)
        .attr('text-anchor', 'middle')
        .style('font-size', '18px')
        .style('font-weight', '600')
        .style('fill', '#9CA3AF')
        .text('No Network Flow Data Available');
      
      g.append('text')
        .attr('x', innerWidth / 2)
        .attr('y', innerHeight / 2 + 20)
        .attr('text-anchor', 'middle')
        .style('font-size', '14px')
        .style('fill', '#6B7280')
        .text('Try using "auto" time window or selecting a longer time range');
      return;
    }

    let sankeyData;
    try {
      sankeyData = sankeyGenerator(graph);
    } catch (error) {
      console.error('Sankey generation failed:', error);
      // Show error message
      g.append('text')
        .attr('x', innerWidth / 2)
        .attr('y', innerHeight / 2)
        .attr('text-anchor', 'middle')
        .style('font-size', '16px')
        .style('font-weight', '500')
        .style('fill', 'var(--color-status-error)')
        .text('Failed to generate network flow diagram');
      return;
    }

    // Create gradient definitions
    const defs = svg.append('defs');
    
    // Add glow filter for enhanced visualization
    const glowFilter = defs.append('filter')
      .attr('id', 'glow')
      .attr('x', '-50%')
      .attr('y', '-50%')
      .attr('width', '200%')
      .attr('height', '200%');

    glowFilter.append('feGaussianBlur')
      .attr('stdDeviation', '3')
      .attr('result', 'coloredBlur');

    const feMerge = glowFilter.append('feMerge');
    feMerge.append('feMergeNode').attr('in', 'coloredBlur');
    feMerge.append('feMergeNode').attr('in', 'SourceGraphic');

    // Draw links with improved styling
    const link = g.append('g')
      .selectAll('path')
      .data(sankeyData.links)
      .enter().append('path')
      .attr('d', sankeyLinkHorizontal())
      .attr('stroke', (d: any) => d.color || '#3B82F6')
      .attr('stroke-width', (d: any) => Math.max(2, d.width))
      .attr('fill', 'none')
      .attr('opacity', 0.7)
      .style('cursor', 'pointer')
      .on('mouseover', function(event, d: any) {
        d3.select(this)
          .attr('opacity', 0.9)
          .attr('filter', 'url(#glow)');
        
        const linkData = data.links.find(link => 
          link.source === d.source.id && link.target === d.target.id
        );
        
        setTooltipData({
          x: event.pageX,
          y: event.pageY,
          content: `
            <div style="font-weight: 700; margin-bottom: 12px; color: #FFFFFF; font-size: 14px;">
              ${d.source.name} → ${d.target.name}
            </div>
            <div style="margin-bottom: 8px;">
              <div style="color: #60A5FA; font-weight: 600;">Traffic Statistics</div>
              <div style="color: #D1D5DB; margin-left: 8px;">Total: ${formatBytes(d.value)}</div>
              <div style="color: #D1D5DB; margin-left: 8px;">Share: ${((d.value / (data?.metadata?.total_traffic || 1)) * 100).toFixed(1)}%</div>
              ${linkData?.packets ? `<div style="color: #D1D5DB; margin-left: 8px;">Packets: ${new Intl.NumberFormat().format(linkData.packets)}</div>` : ''}
            </div>
            <div style="margin-bottom: 8px;">
              <div style="color: #34D399; font-weight: 600;">Connection Type</div>
              <div style="color: #D1D5DB; margin-left: 8px;">Source: ${d.source.category === 'source' ? 'Device' : d.source.category}</div>
              <div style="color: #D1D5DB; margin-left: 8px;">Target: ${d.target.category === 'target' ? 'Location' : d.target.category}</div>
            </div>
          `,
          visible: true
        });
      })
      .on('mouseout', function() {
        d3.select(this)
          .attr('opacity', 0.7)
          .attr('filter', null);
        setTooltipData(prev => ({ ...prev, visible: false }));
      });

    // Draw nodes with improved styling
    const node = g.append('g')
      .selectAll('g')
      .data(sankeyData.nodes)
      .enter().append('g')
      .style('cursor', 'pointer');

    // Node rectangles
    node.append('rect')
      .attr('x', (d: any) => d.x0)
      .attr('y', (d: any) => d.y0)
      .attr('height', (d: any) => d.y1 - d.y0)
      .attr('width', (d: any) => d.x1 - d.x0)
      .attr('fill', (d: any) => d.color)
      .attr('stroke', '#374151')
      .attr('stroke-width', 2)
      .attr('rx', 4)
      .attr('ry', 4)
      .on('mouseover', function(event, d: any) {
        d3.select(this)
          .attr('filter', 'url(#glow)')
          .attr('stroke-width', 3);
        
        const nodeData = data.nodes.find(n => n.id === d.id);
        
        setTooltipData({
          x: event.pageX,
          y: event.pageY,
          content: `
            <div style="font-weight: 700; margin-bottom: 12px; color: #FFFFFF; font-size: 14px;">
              ${d.name}
            </div>
            <div style="margin-bottom: 8px;">
              <div style="color: #60A5FA; font-weight: 600;">Node Information</div>
              <div style="color: #D1D5DB; margin-left: 8px;">Type: ${d.category === 'source' ? 'Source Device' : d.category === 'target' ? 'Target Location' : d.category}</div>
              <div style="color: #D1D5DB; margin-left: 8px;">Traffic: ${formatBytes(d.value)}</div>
              <div style="color: #D1D5DB; margin-left: 8px;">Share: ${((d.value / (data?.metadata?.total_traffic || 1)) * 100).toFixed(1)}%</div>
            </div>
            ${nodeData?.destination_count ? `
            <div style="margin-bottom: 8px;">
              <div style="color: #34D399; font-weight: 600;">Connection Stats</div>
              <div style="color: #D1D5DB; margin-left: 8px;">Destinations: ${nodeData.destination_count}</div>
            </div>` : ''}
            ${nodeData?.ip_count ? `
            <div style="margin-bottom: 8px;">
              <div style="color: #34D399; font-weight: 600;">Geographic Info</div>
              <div style="color: #D1D5DB; margin-left: 8px;">IP Addresses: ${nodeData.ip_count}</div>
            </div>` : ''}
          `,
          visible: true
        });
      })
      .on('mouseout', function() {
        d3.select(this)
          .attr('filter', null)
          .attr('stroke-width', 2);
        setTooltipData(prev => ({ ...prev, visible: false }));
      });

    // Node labels with improved positioning
    node.append('text')
      .attr('x', (d: any) => d.x0 < innerWidth / 2 ? d.x1 + 8 : d.x0 - 8)
      .attr('y', (d: any) => (d.y1 + d.y0) / 2)
      .attr('dy', '0.35em')
      .attr('text-anchor', (d: any) => d.x0 < innerWidth / 2 ? 'start' : 'end')
      .style('font-size', '12px')
      .style('font-weight', '600')
      .style('fill', '#FFFFFF')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .text((d: any) => d.name.length > 20 ? d.name.substring(0, 18) + '...' : d.name);

    // Add title
    svg.append('text')
      .attr('x', width / 2)
      .attr('y', 30)
      .attr('text-anchor', 'middle')
      .style('font-size', '18px')
      .style('font-weight', '700')
      .style('fill', '#FFFFFF')
      .text(title);

    // Add legend
    const legend = svg.append('g')
      .attr('transform', `translate(${width - 140}, 60)`);

    const categories = Array.from(new Set(data.nodes.map(n => n.category)));
    
    const legendItems = legend.selectAll('.legend-item')
      .data(categories)
      .enter().append('g')
      .attr('class', 'legend-item')
      .attr('transform', (d, i) => `translate(0, ${i * 25})`);

    legendItems.append('rect')
      .attr('width', 16)
      .attr('height', 16)
      .attr('rx', 3)
      .attr('ry', 3)
      .attr('fill', d => getNodeColor(d))
      .attr('stroke', '#374151')
      .attr('stroke-width', 1);

    legendItems.append('text')
      .attr('x', 22)
      .attr('y', 12)
      .style('font-size', '12px')
      .style('font-weight', '500')
      .style('fill', '#D1D5DB')
      .text(d => d.charAt(0).toUpperCase() + d.slice(1));

  }, [data, width, height, title, getLinkColor]);

  // Smart circular link detection
  const smartCircularLinkDetection = (nodes: any[], links: any[]) => {
    // Remove obvious self-loops
    const noSelfLoops = links.filter(link => {
      if (link.source === link.target) {
        console.warn('Self-loop removed:', link);
        return false;
      }
      return true;
    });

    // Build adjacency map for cycle detection
    const adjMap = new Map();
    noSelfLoops.forEach(link => {
      if (!adjMap.has(link.source)) {
        adjMap.set(link.source, []);
      }
      adjMap.get(link.source).push(link.target);
    });

    // DFS-based cycle detection
    const visited = new Set();
    const recStack = new Set();
    const cycleNodes = new Set();

    const hasCycle = (node: number): boolean => {
      if (recStack.has(node)) {
        cycleNodes.add(node);
        return true;
      }
      if (visited.has(node)) {
        return false;
      }

      visited.add(node);
      recStack.add(node);

      const neighbors = adjMap.get(node) || [];
      for (const neighbor of neighbors) {
        if (hasCycle(neighbor)) {
          cycleNodes.add(node);
          return true;
        }
      }

      recStack.delete(node);
      return false;
    };

    // Check for cycles
    for (let i = 0; i < nodes.length; i++) {
      if (!visited.has(i)) {
        hasCycle(i);
      }
    }

    // Remove links that are part of cycles
    const finalLinks = noSelfLoops.filter(link => {
      if (cycleNodes.has(link.source) && cycleNodes.has(link.target)) {
        console.warn('Cycle-causing link removed:', link);
        return false;
      }
      return true;
    });

    return finalLinks;
  };



  if (loading) {
    return (
      <Card className={className} padding="lg">
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: '400px',
          color: '#9CA3AF'
        }}>
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '16px'
          }}>
            <div style={{
              width: '40px',
              height: '40px',
              border: '4px solid #374151',
              borderTop: '4px solid #3B82F6',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite'
            }}></div>
            <div style={{ fontSize: '16px', fontWeight: '500' }}>
              Loading network flow data...
            </div>
          </div>
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={className} padding="lg">
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: '400px',
          color: '#EF4444'
        }}>
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '16px'
          }}>
            <div style={{
              fontSize: '48px',
              opacity: 0.5
            }}><WarningIcon size={20} color="#F59E0B" /></div>
            <div style={{ fontSize: '16px', fontWeight: '500' }}>
              Error loading network flow data
            </div>
            <div style={{ fontSize: '14px', color: '#9CA3AF' }}>
              {error}
            </div>
          </div>
        </div>
      </Card>
    );
  }

  if (!data || !data.nodes || data.nodes.length === 0) {
    return (
      <Card className={className} padding="lg">
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: '400px',
          color: '#9CA3AF'
        }}>
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '16px'
          }}>
            <div style={{
              fontSize: '48px',
              opacity: 0.5
            }}><ChartIcon size={20} color="#64748B" /></div>
            <div style={{ fontSize: '16px', fontWeight: '500' }}>
              No network flow data available
            </div>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card className={className} padding="lg">
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '20px'
      }}>
        <div style={{ position: 'relative' }}>
          <svg ref={svgRef} width={width} height={height} style={{
            backgroundColor: '#1F2937',
            borderRadius: '8px',
            border: '1px solid #374151'
          }} />
          
          {/* Enhanced Tooltip */}
          {tooltipData.visible && (
            <div
              style={{
                position: 'fixed',
                left: tooltipData.x + 10,
                top: tooltipData.y - 10,
                backgroundColor: '#111827',
                color: '#FFFFFF',
                padding: '16px',
                borderRadius: '8px',
                fontSize: '13px',
                pointerEvents: 'none',
                zIndex: 1000,
                border: '1px solid #374151',
                boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
                maxWidth: '320px',
                lineHeight: '1.4'
              }}
              dangerouslySetInnerHTML={{ __html: tooltipData.content }}
            />
          )}
        </div>

        {/* Enhanced Stats panel */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
          gap: '16px',
          padding: '20px',
          backgroundColor: '#1F2937',
          borderRadius: '8px',
          border: '1px solid #374151'
        }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{
              fontSize: '28px',
              fontWeight: '700',
              color: '#3B82F6'
            }}>
              {data?.metadata?.total_nodes || 0}
            </div>
            <div style={{
              fontSize: '13px',
              color: '#9CA3AF',
              textTransform: 'uppercase',
              fontWeight: '600',
              marginTop: '4px'
            }}>
              NODES
            </div>
          </div>
          
          <div style={{ textAlign: 'center' }}>
            <div style={{
              fontSize: '28px',
              fontWeight: '700',
              color: '#10B981'
            }}>
              {data?.metadata?.total_links || 0}
            </div>
            <div style={{
              fontSize: '13px',
              color: '#9CA3AF',
              textTransform: 'uppercase',
              fontWeight: '600',
              marginTop: '4px'
            }}>
              LINKS
            </div>
          </div>
          
          <div style={{ textAlign: 'center' }}>
            <div style={{
              fontSize: '28px',
              fontWeight: '700',
              color: '#F59E0B'
            }}>
              {formatBytes(data?.metadata?.total_traffic || 0)}
            </div>
            <div style={{
              fontSize: '13px',
              color: '#9CA3AF',
              textTransform: 'uppercase',
              fontWeight: '600',
              marginTop: '4px'
            }}>
              TOTAL TRAFFIC
            </div>
          </div>

          {/* Additional metadata for device-to-location flow */}
          {data.flow_type === 'device-to-location' && data?.metadata?.location_coverage && (
            <div style={{ textAlign: 'center' }}>
              <div style={{
                fontSize: '28px',
                fontWeight: '700',
                color: '#EC4899'
              }}>
                {Math.round(data?.metadata?.location_coverage || 0)}%
              </div>
              <div style={{
                fontSize: '13px',
                color: '#9CA3AF',
                textTransform: 'uppercase',
                fontWeight: '600',
                marginTop: '4px'
              }}>
                GEO COVERAGE
              </div>
            </div>
          )}
        </div>

        {/* Data scope information */}
        <div style={{
          padding: '12px',
          backgroundColor: '#374151',
          borderRadius: '6px',
          fontSize: '12px',
          color: '#D1D5DB',
          textAlign: 'center',
          border: '1px solid #4B5563'
        }}>
          Data Scope: {data.flow_type === 'device-to-location' ? 'Device to external locations traffic distribution' : 
                  data.flow_type === 'device-to-device' ? 'Inter-device local network traffic' : 
                  data.flow_type === 'protocol-to-service' ? 'Protocol to service traffic distribution' : 
                  `${data.flow_type} traffic analysis`} | 
          Time Window: {data.time_window} | 
          Group By: {data.group_by === 'device_type' ? 'Device Type' : 
                   data.group_by === 'manufacturer' ? 'Manufacturer' : 
                   data.group_by === 'device_name' ? 'Device Name' : data.group_by}
        </div>
      </div>
    </Card>
  );
};

export default SankeyNetworkFlowChart; 
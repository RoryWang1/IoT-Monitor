import React, { useState, useMemo } from 'react';
import { TrafficTrendData } from '../../lib/types/iot';
import { useApiData } from '../../hooks/useApiData';
import { useTimezoneAwareApi } from '../../hooks/useTimezoneAwareApi';
import { useTimezoneTimeWindows } from '../../hooks/useTimezone';
import { TimeWindowSelector } from '../ui';
import { getProtocolColor, generateColorPalette } from '../../styles/colors';
import { WS_TOPICS } from '../../config/api';
import { ChartIcon } from '../ui/icons';

interface TooltipData {
  x: number;
  y: number;
  timestamp: string;
  protocol: string;
  value: number;
  visible: boolean;
}

interface ProtocolStats {
  average: number;
  peak: number;
}

interface TrafficData {
  timestamp: string;
  full_timestamp?: string;
  protocols: {
    [key: string]: number;
  };
  pattern?: string;
}

interface TrafficTrendChartProps {
  deviceId: string;
  experimentId?: string | null;
}

const formatNumber = (value: number | string | undefined): string => {
  const numValue = typeof value === 'number' ? value : parseFloat(String(value || 0));
  if (isNaN(numValue)) return '0';
  
  // Format bytes with appropriate unit
  if (numValue >= 1024 * 1024 * 1024) {
    return `${(numValue / (1024 * 1024 * 1024)).toFixed(1)}GB`;
  } else if (numValue >= 1024 * 1024) {
    return `${(numValue / (1024 * 1024)).toFixed(1)}MB`;
  } else if (numValue >= 1024) {
    return `${(numValue / 1024).toFixed(1)}KB`;
  } else if (numValue >= 1000) {
    return `${(numValue / 1000).toFixed(1)}K`;
  }
  
  return Math.round(numValue).toString();
};

const formatPercentage = (value: number | string | undefined): string => {
  const numValue = typeof value === 'number' ? value : parseFloat(String(value || 0));
  if (isNaN(numValue)) return '0%';
  return `${numValue.toFixed(2)}%`;
};

// Helper function to generate time labels by pure string arithmetic (no Date objects)
// This completely avoids JavaScript Date timezone conversion issues
const generateTimeLabel = (isoString: string, offsetMinutes: number): string => {
  try {
    // Parse ISO string: 2025-06-27T00:52:54.564460+08:00
    const match = isoString.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?([+-]\d{2}):?(\d{2})$/);
    
    if (!match) {
      console.warn('Invalid ISO string format:', isoString);
      return isoString; // Return original if parsing fails
    }
    
    const [, year, month, day, hour, minute, second, fractional, timezone] = match;
    
    // Convert to pure minutes arithmetic
    let totalMinutes = parseInt(hour) * 60 + parseInt(minute) + offsetMinutes;
    let newDay = parseInt(day);
    let newMonth = parseInt(month);
    let newYear = parseInt(year);
    
    // Handle day overflow/underflow
    while (totalMinutes < 0) {
      totalMinutes += 24 * 60; // Add one day in minutes
      newDay -= 1;
      
      if (newDay < 1) {
        newMonth -= 1;
        if (newMonth < 1) {
          newMonth = 12;
          newYear -= 1;
        }
        // Simple month length logic (good enough for short-term offsets)
        const daysInMonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
        newDay = daysInMonth[newMonth - 1];
        if (newMonth === 2 && newYear % 4 === 0) newDay = 29; // Leap year
      }
    }
    
    while (totalMinutes >= 24 * 60) {
      totalMinutes -= 24 * 60; // Subtract one day in minutes
      newDay += 1;
      
      // Simple month length logic
      const daysInMonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
      let maxDays = daysInMonth[newMonth - 1];
      if (newMonth === 2 && newYear % 4 === 0) maxDays = 29; // Leap year
      
      if (newDay > maxDays) {
        newDay = 1;
        newMonth += 1;
        if (newMonth > 12) {
          newMonth = 1;
          newYear += 1;
        }
      }
    }
    
    // Calculate new hour and minute
    const newHour = Math.floor(totalMinutes / 60);
    const newMinute = totalMinutes % 60;
    
    // Format components with zero padding
    const yearStr = newYear.toString().padStart(4, '0');
    const monthStr = newMonth.toString().padStart(2, '0');
    const dayStr = newDay.toString().padStart(2, '0');
    const hourStr = newHour.toString().padStart(2, '0');
    const minuteStr = newMinute.toString().padStart(2, '0');
    
    // Reconstruct ISO string with original timezone and fractional seconds
    const fractionalPart = fractional ? `.${fractional}` : '';
    return `${yearStr}-${monthStr}-${dayStr}T${hourStr}:${minuteStr}:${second}${fractionalPart}${timezone}`;
    
  } catch (error) {
    console.error('Error generating time label:', error);
    return isoString; // Return original on error
  }
};

// Note: Time axis generation is now handled directly in renderChart() using timezone-aware bounds

const TrafficTrendChart: React.FC<TrafficTrendChartProps> = ({ deviceId, experimentId }) => {
  const [selectedWindow, setSelectedWindow] = useState('48h');
  const [selectedProtocols, setSelectedProtocols] = useState<string[]>([]);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  
  const { getDeviceTrafficTrend, formatTimestamp, timezoneInfo } = useTimezoneAwareApi({
    experimentId: experimentId || '',
    deviceId
  });
  
  const { generateTimeLabels, getTimeWindowBounds } = useTimezoneTimeWindows(experimentId || '');

  const { data: trafficData, loading, error, refetch } = useApiData({
    fetchFn: () => getDeviceTrafficTrend(deviceId, selectedWindow, experimentId || undefined),
    wsTopics: [WS_TOPICS.DEVICE_TRAFFIC_TREND(deviceId)],
    dependencies: [deviceId, selectedWindow, experimentId, timezoneInfo?.timezone, refreshTrigger],
    timeWindow: selectedWindow,
    enabled: !!deviceId && !!experimentId
  });

  // Listen for timezone change events
  React.useEffect(() => {
    const handleTimezoneChange = (event: CustomEvent) => {
      console.log('TrafficTrendChart received timezone change event:', event.detail);
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

  const processedData = React.useMemo(() => {
    if (!trafficData || !Array.isArray(trafficData)) return [];
    
    return trafficData.map((item: any) => {
      // Convert protocol objects to simple numbers (using bytes as the main metric)
      const protocols: { [key: string]: number } = {};
      
      // Check if API provides protocol breakdown data
      if (item.protocols && Object.keys(item.protocols).length > 0) {
        Object.keys(item.protocols || {}).forEach(protocol => {
          const protocolData = item.protocols[protocol];
          let value = 0;
          
          if (typeof protocolData === 'object' && protocolData !== null) {
            // Use bytes as primary metric for better visualization (larger values)
            value = protocolData.bytes || protocolData.packets || 0;
          } else if (typeof protocolData === 'number') {
            value = protocolData;
          }
          
          // Ensure value is a valid number
          protocols[protocol] = typeof value === 'number' && !isNaN(value) && isFinite(value) ? value : 0;
        });
      } else {
        // Fallback: If no protocol breakdown available, show total traffic as single metric
        protocols['Total Traffic'] = item.bytes || item.packets || 0;
      }
      
      const totalTraffic = Object.values(protocols).reduce((sum, val) => {
        return sum + (typeof val === 'number' && !isNaN(val) && isFinite(val) ? val : 0);
      }, 0);
      
      // Use enhanced timestamp formats from backend
      let displayTimestamp = item.display_timestamp || item.timestamp;  // MM/DD HH:MM format
      let shortTimestamp = item.short_timestamp;  // HH:MM format for compatibility
      let fullTimestamp = item.full_timestamp || item.timestamp;  // YYYY/MM/DD HH:MM format
      
      // If enhanced timestamps not provided, generate from full timestamp
      if (!item.display_timestamp && typeof item.timestamp === 'string') {
        try {
          const date = new Date(item.timestamp);
          if (!isNaN(date.getTime())) {
            displayTimestamp = date.toLocaleDateString('en-US', { 
              month: '2-digit', 
              day: '2-digit' 
            }) + ' ' + date.toLocaleTimeString('en-US', { 
              hour: '2-digit', 
              minute: '2-digit',
              hour12: false 
            });
            shortTimestamp = date.toLocaleTimeString('en-US', { 
              hour: '2-digit', 
              minute: '2-digit',
              hour12: false 
            });
            fullTimestamp = date.toLocaleDateString('en-US', { 
              year: 'numeric', 
              month: '2-digit', 
              day: '2-digit' 
            }) + ' ' + date.toLocaleTimeString('en-US', { 
              hour: '2-digit', 
              minute: '2-digit',
              hour12: false 
            });
          }
        } catch (e) {
          displayTimestamp = item.timestamp;
          shortTimestamp = item.timestamp;
          fullTimestamp = item.timestamp;
        }
      }
      
      return {
        timestamp: item.timestamp,  // Original timestamp for sorting
        displayTimestamp: displayTimestamp,  // Enhanced MM/DD HH:MM format for chart display
        shortTimestamp: shortTimestamp,  // Short HH:MM format for compact display
        fullTimestamp: fullTimestamp,  // Full YYYY/MM/DD HH:MM format for detailed view
        protocols: protocols,
        totalTraffic: totalTraffic,
        packets: item.packets || 0,
        bytes: item.bytes || 0,
        sessions: item.sessions || 0,
        pattern: item.pattern || 'normal'
      };
    });
  }, [trafficData]);

  // Enhanced protocol filtering - show ALL protocols with data
  const availableProtocols = React.useMemo(() => {
    if (processedData.length === 0) return [];
    
    const protocolStats: { [key: string]: { totalTraffic: number, nonZeroPoints: number } } = {};
    
    // Collect all protocol statistics
    processedData.forEach(item => {
      Object.keys(item.protocols).forEach(protocol => {
        if (!protocolStats[protocol]) {
          protocolStats[protocol] = { totalTraffic: 0, nonZeroPoints: 0 };
        }
        const value = item.protocols[protocol] || 0;
        if (typeof value === 'number' && !isNaN(value) && isFinite(value) && value > 0) {
          protocolStats[protocol].totalTraffic += value;
          protocolStats[protocol].nonZeroPoints += 1;
        }
      });
    });
    
    // Return ALL protocols that have any traffic (no filtering based on variation)
    return Object.keys(protocolStats)
      .filter(protocol => protocolStats[protocol].totalTraffic > 0)
      .sort((a, b) => protocolStats[b].totalTraffic - protocolStats[a].totalTraffic); // Sort by total traffic
  }, [processedData]);

  // Automatic protocol selection - show ALL available protocols
  React.useEffect(() => {
    if (availableProtocols.length > 0) {

      setSelectedProtocols(availableProtocols); // Show ALL available protocols
    } else {
      setSelectedProtocols([]);
    }
  }, [availableProtocols, selectedWindow]); // Include selectedWindow to trigger update

  // Enhanced max value calculation with better scaling
  const maxValue = React.useMemo(() => {
    if (processedData.length === 0 || selectedProtocols.length === 0) return 1;
    
    // Find the maximum value across all selected protocol values
    const allProtocolValues: number[] = [];
    processedData.forEach(item => {
      selectedProtocols.forEach(protocol => {
        const value = item.protocols[protocol] || 0;
        if (typeof value === 'number' && !isNaN(value) && isFinite(value) && value > 0) {
          allProtocolValues.push(value);
        }
      });
    });
    
    const max = allProtocolValues.length > 0 ? Math.max(...allProtocolValues) : 1;
    return max > 0 ? max : 1; // Ensure maxValue is always positive
  }, [processedData, selectedProtocols]);

  const toggleProtocol = (protocol: string) => {
    setSelectedProtocols(prev => 
      prev.includes(protocol) 
        ? prev.filter(p => p !== protocol)
        : [...prev, protocol]
    );
  };

  const getPatternLabel = (pattern?: string): string => {
    switch (pattern) {
      case 'business': return 'Business Hours';
      case 'evening': return 'Evening';
      case 'night': return 'Night';
      case 'weekend': return 'Weekend';
      default: return 'Normal';
    }
  };

  const [tooltip, setTooltip] = useState<TooltipData>({
    x: 0,
    y: 0,
    timestamp: '',
    protocol: '',
    value: 0,
    visible: false
  });

  const calculateProtocolStats = (): Record<string, ProtocolStats> => {
    if (!processedData || !Array.isArray(processedData) || processedData.length === 0 || !processedData[0] || !processedData[0].protocols) return {};
    
    const protocols = Object.keys(processedData[0].protocols);
    const stats: Record<string, ProtocolStats> = {};
    
    protocols.forEach(protocol => {
      const values = processedData.map(d => {
        const val = d.protocols[protocol];
        return typeof val === 'number' ? val : parseFloat(String(val || 0));
      }).filter(val => !isNaN(val));
      
      if (values.length > 0) {
        const average = values.reduce((sum, val) => sum + val, 0) / values.length;
        const peak = Math.max(...values);
        stats[protocol] = { average, peak };
      }
    });
    
    return stats;
  };

  const handleMouseMove = (event: React.MouseEvent<SVGElement>) => {
    if (!processedData || !Array.isArray(processedData)) return;
    
    const rect = event.currentTarget.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    
    // Find closest data point
    const chartWidth = 700;
    const chartHeight = 350;
    const padding = 60;
    const innerWidth = chartWidth - padding * 2;
    
    const dataIndex = Math.round(((x - padding) / innerWidth) * (processedData.length - 1));
    
    if (dataIndex >= 0 && dataIndex < processedData.length) {
      const dataPoint = processedData[dataIndex];
      if (!dataPoint || !dataPoint.protocols) return;
      const protocols = Object.keys(dataPoint.protocols);
      
      // Find closest protocol line
      let closestProtocol = protocols[0];
      let minDistance = Infinity;
      
      protocols.forEach(protocol => {
        const maxValue = Math.max(...processedData.flatMap(d => Object.values(d.protocols).filter((v): v is number => typeof v === 'number')));
        const protocolY = padding + (chartHeight - padding * 2) - (dataPoint.protocols[protocol] / maxValue) * (chartHeight - padding * 2);
        const distance = Math.abs(y - protocolY);
        
        if (distance < minDistance) {
          minDistance = distance;
          closestProtocol = protocol;
        }
      });
      
      if (minDistance < 30) { // Show tooltip only if mouse is close to a line
        setTooltip({
          x: event.clientX,
          y: event.clientY,
          timestamp: dataPoint.displayTimestamp,
          protocol: closestProtocol,
          value: dataPoint.protocols[closestProtocol],
          visible: true
        });
      } else {
        setTooltip(prev => ({ ...prev, visible: false }));
      }
    }
  };

  const handleMouseLeave = () => {
    setTooltip(prev => ({ ...prev, visible: false }));
  };

  const renderChart = () => {
    if (!processedData || !Array.isArray(processedData) || processedData.length === 0 || !processedData[0] || !processedData[0].protocols) {
      return (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '400px',
          backgroundColor: 'var(--color-bg-secondary)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--color-border-primary)',
          color: 'var(--color-text-secondary)'
        }}>
          No traffic data available for the selected time window
        </div>
      );
    }

    const chartWidth = 800;
    const chartHeight = 400;
    const padding = 80;
    const innerWidth = chartWidth - padding * 2;
    const innerHeight = chartHeight - padding * 2;

    // Get all protocol names
    const protocols = Object.keys(processedData[0].protocols);
    
    // Find max value for scaling with safety checks and dynamic adjustment
    const allValues = processedData.flatMap(d => 
      Object.values(d.protocols).filter((v): v is number => 
        typeof v === 'number' && !isNaN(v) && isFinite(v)
      )
    );
    const rawMaxValue = allValues.length > 0 ? Math.max(...allValues) : 1;
    
    // DYNAMIC Y-AXIS SCALING: Add 20% padding to max value for better visualization
    const maxValue = rawMaxValue > 0 ? rawMaxValue * 1.2 : 1;
    const safeMaxValue = maxValue > 0 ? maxValue : 1;
    


    // Calculate actual data time range for proper positioning
    const dataTimestamps = processedData
      .map(d => new Date(d.timestamp))
      .filter(date => !isNaN(date.getTime()))
      .sort((a, b) => a.getTime() - b.getTime());
    
    const actualStartTime = dataTimestamps.length > 0 ? dataTimestamps[0] : null;
    const actualEndTime = dataTimestamps.length > 0 ? dataTimestamps[dataTimestamps.length - 1] : null;
    const actualTimeRange = actualStartTime && actualEndTime ? 
      actualEndTime.getTime() - actualStartTime.getTime() : 0;

    // Create points for each protocol with CORRECT time positioning based on actual data range
    const protocolLines = selectedProtocols.filter(protocol => protocols.includes(protocol)).map(protocol => {
      const validPoints: { x: number, y: number, value: number, timestamp: string }[] = [];
      
      processedData.forEach((d, i) => {
        const rawValue = d.protocols[protocol] || 0;
        const safeValue = typeof rawValue === 'number' && !isNaN(rawValue) && isFinite(rawValue) ? rawValue : 0;
        
        let x = padding;
        
        // Use data-based positioning for better distribution
        if (actualStartTime && actualEndTime && actualTimeRange > 0) {
          try {
            const dataTime = new Date(d.timestamp);
            if (!isNaN(dataTime.getTime())) {
              // Calculate position based on actual data time range (0 = earliest data, 1 = latest data)
              const timePosition = (dataTime.getTime() - actualStartTime.getTime()) / actualTimeRange;
              const clampedPosition = Math.max(0, Math.min(1, timePosition));
              x = padding + clampedPosition * innerWidth;
            } else {
              // Fallback to index-based positioning
              x = processedData.length === 1 ? 
                padding + innerWidth / 2 : 
                padding + (i / Math.max(processedData.length - 1, 1)) * innerWidth;
            }
          } catch (error) {
            console.warn('Error calculating time position:', error);
            // Fallback to index-based positioning
            x = processedData.length === 1 ? 
              padding + innerWidth / 2 : 
              padding + (i / Math.max(processedData.length - 1, 1)) * innerWidth;
          }
        } else {
          // Fallback to index-based positioning when no valid time range
          x = processedData.length === 1 ? 
            padding + innerWidth / 2 : 
            padding + (i / Math.max(processedData.length - 1, 1)) * innerWidth;
        }
        
        const y = padding + innerHeight - (safeValue / safeMaxValue) * innerHeight;
        
        // Ensure coordinates are valid
        const safeX = typeof x === 'number' && !isNaN(x) && isFinite(x) ? x : padding;
        const safeY = typeof y === 'number' && !isNaN(y) && isFinite(y) ? y : padding + innerHeight;
        
        validPoints.push({ 
          x: safeX, 
          y: safeY, 
          value: safeValue, 
          timestamp: d.timestamp 
        });
      });

      // Create SVG path only from valid points
      const pathData = validPoints.length > 0 ? 
        validPoints.map((point, index) => {
          const safeX = typeof point.x === 'number' && !isNaN(point.x) && isFinite(point.x) ? point.x : padding;
          const safeY = typeof point.y === 'number' && !isNaN(point.y) && isFinite(point.y) ? point.y : padding + innerHeight;
          return index === 0 ? `M ${safeX} ${safeY}` : `L ${safeX} ${safeY}`;
        }).join(' ') : '';

      return {
        protocol,
        pathData,
        points: validPoints,
        color: getProtocolColor(protocol)
      };
    });

    // IMPROVED Y-AXIS LABELS: Better scaling and formatting
    const yAxisLabels = [0, 0.25, 0.5, 0.75, 1].map(ratio => {
      const value = Math.round(safeMaxValue * ratio);
      const y = padding + (1 - ratio) * innerHeight;
      const safeY = typeof y === 'number' && !isNaN(y) && isFinite(y) ? y : padding;
      return {
        value: typeof value === 'number' && !isNaN(value) && isFinite(value) ? value : 0,
        y: safeY,
        // Add formatted display value for better readability
        displayValue: formatNumber(value)
      };
    });
    


    // X-axis labels: use actual data time range for accurate representation
    let xAxisLabels;
    const labelCount = 6;
    
    // Use actual data time range for all modes to match data positioning
    if (actualStartTime && actualEndTime && actualTimeRange > 0) {
      xAxisLabels = Array.from({ length: labelCount }, (_, i) => {
        const x = padding + (i / (labelCount - 1)) * innerWidth;
        const timeOffset = (i / (labelCount - 1)) * actualTimeRange;
        const labelTime = new Date(actualStartTime.getTime() + timeOffset);
        
        const labelISO = labelTime.toISOString();
        const enhancedLabel = formatTimestamp ? 
          formatTimestamp(labelISO, 'chart') : 
          labelISO.substring(5, 10).replace('-', '/') + ' ' + labelISO.substring(11, 16);
        
        return {
          x: x,
          displayLabel: enhancedLabel,
          timestamp: labelISO,
          hasData: false,
          dataIndex: null
        };
      });
    } else if (timezoneInfo && timezoneInfo.current_time) {
      // Fallback to standard time axis when no valid data range
      xAxisLabels = Array.from({ length: labelCount }, (_, i) => {
        const x = padding + (i / (labelCount - 1)) * innerWidth;
        
        // Calculate time window and offset
        const windowMinutes = {
          '1h': 60, '2h': 120, '6h': 360, '12h': 720, '24h': 1440, '48h': 2880
        }[selectedWindow] || 1440;
        
        const offsetMinutes = (labelCount - 1 - i) * (windowMinutes / (labelCount - 1));
        
        // Parse current experiment time string directly
        const currentTimeISO = timezoneInfo.current_time;
        
        // Generate time axis label
        const labelISO = generateTimeLabel(currentTimeISO, -offsetMinutes);
        
        // Use our timezone-aware formatting
        const enhancedLabel = formatTimestamp ? 
          formatTimestamp(labelISO, 'chart') : 
          labelISO.substring(5, 10).replace('-', '/') + ' ' + labelISO.substring(11, 16);
        
        return {
          x: x,
          displayLabel: enhancedLabel,
          timestamp: labelISO,
          hasData: false,
          dataIndex: null
        };
      });
    } else {
      // Fallback if timezone info not available
      xAxisLabels = Array.from({ length: 6 }, (_, i) => ({
        x: padding + (i / 5) * innerWidth,
        displayLabel: 'Loading...',
        timestamp: new Date().toISOString(),
        hasData: false,
        dataIndex: null
      }));
    }

    return (
      <div style={{ position: 'relative' }}>
        <svg 
          width={chartWidth} 
          height={chartHeight} 
          style={{ 
            backgroundColor: 'var(--color-bg-secondary)', 
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--color-border-primary)'
          }}
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
        >
          {/* Background grid */}
          {yAxisLabels.map((label, index) => (
            <line
              key={`grid-${index}`}
              x1={padding}
              y1={label.y}
              x2={chartWidth - padding}
              y2={label.y}
              stroke="var(--color-border-secondary)"
              strokeWidth="1"
              strokeDasharray="2,2"
              opacity="0.3"
            />
          ))}

          {/* Y-axis */}
          <line
            x1={padding}
            y1={padding}
            x2={padding}
            y2={chartHeight - padding}
            stroke="var(--color-border-primary)"
            strokeWidth="1"
          />

          {/* X-axis */}
          <line
            x1={padding}
            y1={chartHeight - padding}
            x2={chartWidth - padding}
            y2={chartHeight - padding}
            stroke="var(--color-border-primary)"
            strokeWidth="1"
          />

          {/* Y-axis labels */}
          {yAxisLabels.map((label, index) => (
            <text
              key={`y-label-${index}`}
              x={padding - 10}
              y={label.y + 4}
              fill="var(--color-text-tertiary)"
              fontSize="11"
              textAnchor="end"
              fontFamily="monospace"
            >
              {label.displayValue || formatNumber(label.value)}
            </text>
          ))}

          {/* Protocol lines */}
          {protocolLines.map(line => (
            <path
              key={line.protocol}
              d={line.pathData}
              fill="none"
              stroke={line.color}
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          ))}

          {/* Data points */}
          {protocolLines.map(line => 
            line.points.map((point, i) => {
              const safeCx = typeof point.x === 'number' && !isNaN(point.x) && isFinite(point.x) ? point.x : padding;
              const safeCy = typeof point.y === 'number' && !isNaN(point.y) && isFinite(point.y) ? point.y : padding + innerHeight;
              return (
                <circle
                  key={`${line.protocol}-${i}`}
                  cx={safeCx}
                  cy={safeCy}
                  r="3"
                  fill={line.color}
                  stroke="var(--color-bg-primary)"
                  strokeWidth="1"
                  style={{ cursor: 'pointer' }}
                >
                  <title>
                    {`${processedData[i]?.displayTimestamp || 'Unknown'}: ${line.protocol} - ${formatNumber(point.value)}`}
                  </title>
                </circle>
              );
            })
          )}

          {/* X-axis labels */}
          {xAxisLabels.map((d, i) => {
            // Use pre-calculated x position from xAxisLabels
            const safeX = typeof d.x === 'number' && !isNaN(d.x) && isFinite(d.x) ? d.x : padding;
            const safeY = chartHeight - padding + 20;
            
            return (
              <text
                key={`x-label-${i}-${d.timestamp}`}
                x={safeX}
                y={safeY}
                fill="var(--color-text-tertiary)"
                fontSize="11"
                textAnchor="middle"
                fontFamily="monospace"
              >
                {d.displayLabel}
              </text>
            );
          })}
        </svg>

        {/* Tooltip */}
        {tooltip.visible && (
          <div
            style={{
              position: 'fixed',
              left: tooltip.x + 10,
              top: tooltip.y - 10,
              backgroundColor: 'var(--color-bg-primary)',
              border: '1px solid var(--color-border-primary)',
              borderRadius: 'var(--radius-sm)',
              padding: 'var(--spacing-sm)',
              fontSize: 'var(--text-sm)',
              color: 'var(--color-text-primary)',
              zIndex: 1000,
              pointerEvents: 'none',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)'
            }}
          >
            <div style={{ fontWeight: 'bold', marginBottom: 'var(--spacing-xs)' }}>
              {tooltip.timestamp}
            </div>
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: 'var(--spacing-xs)' 
            }}>
              <div
                style={{
                  width: '12px',
                  height: '12px',
                  borderRadius: '50%',
                  backgroundColor: getProtocolColor(tooltip.protocol)
                }}
              />
              <span>{tooltip.protocol}: {formatNumber(tooltip.value)}</span>
            </div>
          </div>
        )}
      </div>
    );
  };

  if (loading && !trafficData) {
    return (
      <div style={{
        backgroundColor: 'var(--color-bg-secondary)',
        border: '1px solid var(--color-border-primary)',
        borderRadius: 'var(--radius-lg)',
        padding: 'var(--card-padding-lg)',
        color: 'var(--color-text-tertiary)',
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
        Loading traffic trend...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{
        padding: 'var(--spacing-lg)',
        backgroundColor: 'var(--color-bg-primary)',
        borderRadius: 'var(--radius-lg)',
        border: '1px solid var(--color-border-danger)'
      }}>
        <div style={{
          color: 'var(--color-text-danger)',
          textAlign: 'center'
        }}>
          Error loading traffic trend: {error}
        </div>
      </div>
    );
  }

  const protocolStats = calculateProtocolStats();

  return (
    <div style={{
      padding: 'var(--spacing-lg)',
      backgroundColor: 'var(--color-bg-primary)',
      borderRadius: 'var(--radius-lg)',
      border: '1px solid var(--color-border-primary)'
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: 'var(--spacing-lg)',
        flexWrap: 'wrap',
        gap: 'var(--spacing-md)'
      }}>
        <div>
          <h3 className="text-responsive-lg" style={{
            color: 'var(--color-text-primary)',
            fontWeight: '600',
            margin: '0 0 var(--spacing-xs) 0'
          }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <ChartIcon size={18} color="#3B82F6" />
                Traffic Trend Analysis ({selectedWindow.toUpperCase()})
              </div>
          </h3>
          <p className="text-responsive-sm" style={{
            color: 'var(--color-text-secondary)',
            margin: 0
          }}>
            Protocol traffic patterns over time
          </p>
        </div>

        <TimeWindowSelector
          selectedWindow={selectedWindow}
          onWindowChange={setSelectedWindow}
          size="sm"
        />
      </div>

      {/* Protocol Legend & Selector */}
      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: 'var(--spacing-sm)',
        marginBottom: 'var(--spacing-lg)',
        padding: 'var(--spacing-sm)',
        backgroundColor: 'var(--color-bg-secondary)',
        borderRadius: 'var(--radius-md)',
        border: '1px solid var(--color-border-primary)'
      }}>
        {availableProtocols.map(protocol => (
          <button
            key={protocol}
            onClick={() => toggleProtocol(protocol)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--spacing-xs)',
              padding: 'var(--spacing-xs) var(--spacing-sm)',
              backgroundColor: selectedProtocols.includes(protocol) 
                ? getProtocolColor(protocol)
                : 'transparent',
              color: selectedProtocols.includes(protocol) 
                ? 'var(--color-text-primary)' 
                : 'var(--color-text-secondary)',
              border: `1px solid ${getProtocolColor(protocol)}`,
              borderRadius: 'var(--radius-sm)',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              fontSize: 'var(--text-xs)',
              fontWeight: '500'
            }}
          >
            <div style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: getProtocolColor(protocol)
            }}></div>
            {protocol}
          </button>
        ))}
      </div>

      {/* Chart */}
      <div style={{
        marginBottom: 'var(--spacing-lg)'
      }}>
        {renderChart()}
      </div>

      {/* Statistics Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: 'var(--spacing-md)',
        marginBottom: 'var(--spacing-lg)'
      }}>
        {selectedProtocols.map(protocol => {
          // Calculate stats from all available data points (no time filtering)
          const validData = processedData.filter(item => item.protocols && item.protocols[protocol] !== undefined);
          
          const totalTraffic = validData.reduce((sum, item) => sum + (item.protocols[protocol] || 0), 0);
          const avgTraffic = validData.length > 0 ? totalTraffic / validData.length : 0;
          const peakTraffic = validData.length > 0 ? Math.max(...validData.map(item => item.protocols[protocol] || 0)) : 0;

          return (
            <div key={protocol} style={{
              backgroundColor: 'var(--color-bg-secondary)',
              padding: 'var(--spacing-md)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--color-border-primary)'
            }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--spacing-xs)',
                marginBottom: 'var(--spacing-sm)'
              }}>
                <div style={{
                  width: '12px',
                  height: '12px',
                  borderRadius: '50%',
                  backgroundColor: getProtocolColor(protocol)
                }}></div>
                <h4 className="text-responsive-sm" style={{
                  color: 'var(--color-text-primary)',
                  fontWeight: '600',
                  margin: 0
                }}>
                  {protocol}
                </h4>
              </div>
              
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <div>
                  <div className="text-responsive-xs" style={{
                    color: 'var(--color-text-secondary)'
                  }}>
                    Avg
                  </div>
                  <div className="text-responsive-lg" style={{
                    color: 'var(--color-text-primary)',
                    fontWeight: '700',
                    fontFamily: 'monospace'
                  }}>
                    {formatNumber(avgTraffic)}
                  </div>
                </div>
                
                <div>
                  <div className="text-responsive-xs" style={{
                    color: 'var(--color-text-secondary)'
                  }}>
                    Peak
                  </div>
                  <div className="text-responsive-lg" style={{
                    color: getProtocolColor(protocol),
                    fontWeight: '700',
                    fontFamily: 'monospace'
                  }}>
                    {formatNumber(peakTraffic)}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Live Data Indicator */}
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        gap: 'var(--spacing-xs)',
        padding: 'var(--spacing-sm) var(--spacing-md)',
        backgroundColor: 'var(--color-bg-secondary)',
        borderRadius: 'var(--radius-full)',
        border: '1px solid var(--color-border-primary)'
      }}>
        <div style={{
          width: '8px',
          height: '8px',
          borderRadius: '50%',
          backgroundColor: 'var(--color-accent-green)',
          animation: 'pulse 2s infinite'
        }}></div>
        <span className="text-responsive-xs" style={{
          color: 'var(--color-text-secondary)',
          fontWeight: '500'
        }}>
          Real-time traffic analysis - {processedData.length} data points (Last {selectedWindow.toUpperCase()})
        </span>
      </div>
    </div>
  );
};

export default TrafficTrendChart; 
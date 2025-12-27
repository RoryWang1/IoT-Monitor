import React, { useState, useMemo } from 'react';
import { useApiData } from '../../hooks/useApiData';
import { useTimezoneAwareApi } from '../../hooks/useTimezoneAwareApi';
import TimeWindowSelector from '@/components/ui/TimeWindowSelector';
import { getProtocolColor } from '../../styles/colors';
import { WS_TOPICS } from '../../config/api';
import { NetworkIcon } from '../ui/icons';

interface ProtocolDistributionChartProps {
  deviceId: string;
  experimentId?: string | null;
}

interface BackendProtocolData {
  protocol: string;
  packet_count: string;
  byte_count: string;
  session_count: number;
  percentage: string;
  avg_packet_size: string;
  experiment_id: string;
  formatted_bytes: string;
}

interface ProcessedProtocolData {
  protocol: string;
  percentage: number;
  packets: number;
  bytes: number;
  color: string;
  displayValue: number;
  angle: number;
  startAngle: number;
}

// Unified data formatting function, keeping 2 decimal places
const formatValue = (value: number, type: string): string => {
  // Ensure value is a valid number
  const safeValue = typeof value === 'number' && !isNaN(value) && isFinite(value) ? value : 0;
  
  switch (type) {
    case 'bytes':
      if (safeValue >= 1024 * 1024 * 1024) return `${(safeValue / (1024 * 1024 * 1024)).toFixed(2)}GB`;
      if (safeValue >= 1024 * 1024) return `${(safeValue / (1024 * 1024)).toFixed(2)}MB`;
      if (safeValue >= 1024) return `${(safeValue / 1024).toFixed(2)}KB`;
      return `${safeValue.toFixed(2)}B`;
    case 'packets':
      if (safeValue >= 1000000) return `${(safeValue / 1000000).toFixed(2)}M`;
      if (safeValue >= 1000) return `${(safeValue / 1000).toFixed(2)}K`;
      return safeValue.toFixed(0);
    case 'percentage':
      return `${safeValue.toFixed(2)}%`;
    default:
      return safeValue.toFixed(2);
  }
};

const ProtocolDistributionChart: React.FC<ProtocolDistributionChartProps> = ({ deviceId, experimentId }) => {
  const [selectedWindow, setSelectedWindow] = useState('48h');
  const [selectedView, setSelectedView] = useState<'percentage' | 'packets' | 'bytes'>('percentage');
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  
  // Don't use 'default' as fallback, wait for the correct experimentId
  const { getDeviceProtocolDistribution, formatTimestamp, timezoneInfo } = useTimezoneAwareApi({
    experimentId: experimentId || '',
    deviceId
  });

  const { data: protocolData, loading, error, refetch } = useApiData({
    fetchFn: () => getDeviceProtocolDistribution(deviceId, selectedWindow, experimentId || undefined),
    wsTopics: [WS_TOPICS.DEVICE_PROTOCOL_DISTRIBUTION(deviceId)],
    dependencies: [deviceId, selectedWindow, experimentId, timezoneInfo?.timezone, refreshTrigger],
    timeWindow: selectedWindow,
    enabled: !!deviceId && !!experimentId
  });

  // Listen for timezone change events
  React.useEffect(() => {
    const handleTimezoneChange = (event: CustomEvent) => {
      console.log('ProtocolDistributionChart received timezone change event:', event.detail);
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

  const processedData = React.useMemo((): ProcessedProtocolData[] => {
    if (!protocolData || !Array.isArray(protocolData)) return [];
    
    // Convert backend data format to frontend format
    const convertedData = protocolData.map((item: BackendProtocolData) => {
      const percentage = parseFloat(item.percentage) || 0;
      const packets = parseInt(item.packet_count) || 0;
      const bytes = parseInt(item.byte_count) || 0;
      
      return {
        protocol: item.protocol || 'Unknown',
        percentage,
        packets,
        bytes,
        color: getProtocolColor(item.protocol || 'Unknown'),
        displayValue: 0, // Will be set below based on selectedView
        angle: 0, // Will be calculated below
        startAngle: 0 // Will be calculated below
      };
    });

    // Filter out protocols with no data
    const filteredData = convertedData.filter(item => 
      item.percentage > 0 || item.packets > 0 || item.bytes > 0
    );

    // If no valid data, return empty array
    if (filteredData.length === 0) return [];

    // Set display values and calculate angles
    return filteredData.map((item, index) => {
      const displayValue = item[selectedView] || 0;
      const angle = (item.percentage / 100) * 360;
      const startAngle = filteredData.slice(0, index).reduce((sum, p) => sum + (p.percentage / 100) * 360, 0);
      
      return {
        ...item,
        displayValue,
        angle,
        startAngle
      };
    });
  }, [protocolData, selectedView]);

  const totalValue = React.useMemo(() => {
    return processedData.reduce((sum, item) => sum + item.displayValue, 0);
  }, [processedData]);

  // Get the dominant protocol
  const dominantProtocol = React.useMemo(() => {
    if (processedData.length === 0) return null;
    return processedData.reduce((prev, current) => 
      prev.percentage > current.percentage ? prev : current
    );
  }, [processedData]);

  const createPieSlice = (item: ProcessedProtocolData, centerX: number, centerY: number, radius: number) => {
    const startAngleRad = (item.startAngle - 90) * (Math.PI / 180);
    const endAngleRad = (item.startAngle + item.angle - 90) * (Math.PI / 180);
    
    const x1 = centerX + radius * Math.cos(startAngleRad);
    const y1 = centerY + radius * Math.sin(startAngleRad);
    const x2 = centerX + radius * Math.cos(endAngleRad);
    const y2 = centerY + radius * Math.sin(endAngleRad);
    
    const largeArcFlag = item.angle > 180 ? 1 : 0;
    
    const pathData = [
      `M ${centerX} ${centerY}`,
      `L ${x1} ${y1}`,
      `A ${radius} ${radius} 0 ${largeArcFlag} 1 ${x2} ${y2}`,
      'Z'
    ].join(' ');
    
    return pathData;
  };

  if (loading && !protocolData) {
    return (
      <div style={{
        padding: 'var(--spacing-lg)',
        backgroundColor: 'var(--color-bg-primary)',
        borderRadius: 'var(--radius-lg)',
        border: '1px solid var(--color-border-primary)'
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '400px',
          color: 'var(--color-text-secondary)'
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--spacing-sm)'
          }}>
            <div style={{
              width: '20px',
              height: '20px',
              border: '2px solid var(--color-accent-blue)',
              borderTop: '2px solid transparent',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite'
            }}></div>
            Loading protocol distribution data...
          </div>
        </div>
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
          Error loading protocol distribution: {error}
        </div>
      </div>
    );
  }

  // Show "No Data" message if no valid protocols found
  if (processedData.length === 0) {
    return (
      <div style={{
        padding: 'var(--spacing-lg)',
        backgroundColor: 'var(--color-bg-primary)',
        borderRadius: 'var(--radius-lg)',
        border: '1px solid var(--color-border-primary)'
      }}>
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
              margin: '0 0 var(--spacing-xs) 0',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}>
              <NetworkIcon size={18} color="#3B82F6" />
              Protocol Distribution ({selectedWindow.toUpperCase()})
            </h3>
            <p className="text-responsive-sm" style={{
              color: 'var(--color-text-secondary)',
              margin: 0
            }}>
              Network protocol usage breakdown
            </p>
          </div>

          <TimeWindowSelector
            selectedWindow={selectedWindow}
            onWindowChange={setSelectedWindow}
            size="sm"
          />
        </div>

        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '300px',
          color: 'var(--color-text-secondary)'
        }}>
          <div style={{
            fontSize: 'var(--text-4xl)',
            marginBottom: 'var(--spacing-md)',
            opacity: 0.5
          }}>
            No Data
          </div>
          <h4 style={{
            margin: '0 0 var(--spacing-sm) 0',
            color: 'var(--color-text-primary)'
          }}>
            No Protocol Data Available
          </h4>
          <p style={{
            margin: 0,
            textAlign: 'center',
            maxWidth: '400px'
          }}>
            No network protocol activity found for the selected time window ({selectedWindow.toUpperCase()}). 
            Try selecting a different time range or check if the device has network activity.
          </p>
        </div>
      </div>
    );
  }

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
            margin: '0 0 var(--spacing-xs) 0',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <NetworkIcon size={18} color="#3B82F6" />
            Protocol Distribution ({selectedWindow.toUpperCase()})
          </h3>
          <p className="text-responsive-sm" style={{
            color: 'var(--color-text-secondary)',
            margin: 0
          }}>
            Network protocol usage breakdown
          </p>
        </div>

        <div style={{
          display: 'flex',
          gap: 'var(--spacing-sm)',
          alignItems: 'flex-end'
        }}>
          <TimeWindowSelector
            selectedWindow={selectedWindow}
            onWindowChange={setSelectedWindow}
            size="sm"
          />
          
          {/* View Selector */}
          <div style={{
            display: 'flex',
            gap: 'var(--spacing-xs)',
            backgroundColor: 'var(--color-bg-secondary)',
            padding: 'var(--spacing-xs)',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--color-border-primary)'
          }}>
            {(['percentage', 'packets', 'bytes'] as const).map((view) => (
              <button
                key={view}
                onClick={() => setSelectedView(view)}
                className="text-xs px-2 py-1"
                style={{
                  backgroundColor: selectedView === view 
                    ? 'var(--color-accent-blue)' 
                    : 'transparent',
                  color: selectedView === view 
                    ? 'var(--color-text-primary)' 
                    : 'var(--color-text-secondary)',
                  border: 'none',
                  borderRadius: 'var(--radius-sm)',
                  fontWeight: selectedView === view ? '600' : '500',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  textTransform: 'capitalize'
                }}
              >
                {view}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Chart and Legend Container */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 300px',
        gap: 'var(--spacing-lg)',
        marginBottom: 'var(--spacing-lg)'
      }}>
        {/* Pie Chart */}
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          backgroundColor: 'var(--color-bg-secondary)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--color-border-primary)',
          padding: 'var(--spacing-lg)',
          minHeight: '400px'
        }}>
          <div style={{ position: 'relative' }}>
            <svg width="300" height="300" viewBox="0 0 300 300">
              {processedData.map((item, index) => (
                <g key={item.protocol}>
                  <path
                    d={createPieSlice(item, 150, 150, 120)}
                    fill={item.color}
                    stroke="var(--color-bg-primary)"
                    strokeWidth="2"
                    style={{
                      cursor: 'pointer',
                      transition: 'all 0.2s ease'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.transform = 'scale(1.05)';
                      e.currentTarget.style.transformOrigin = '150px 150px';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = 'scale(1)';
                    }}
                  >
                    <title>
                      {`${item.protocol}: ${formatValue(item.displayValue, selectedView)}`}
                    </title>
                  </path>
                </g>
              ))}
              
              {/* Center circle */}
              <circle
                cx="150"
                cy="150"
                r="60"
                fill="var(--color-bg-primary)"
                stroke="var(--color-border-primary)"
                strokeWidth="2"
              />
              
              {/* Center text */}
              <text
                x="150"
                y="135"
                textAnchor="middle"
                className="text-responsive-xs"
                fill="var(--color-text-secondary)"
              >
                Dominant
              </text>
              <text
                x="150"
                y="155"
                textAnchor="middle"
                className="text-responsive-sm"
                fill="var(--color-text-primary)"
                fontWeight="700"
              >
                {dominantProtocol?.protocol || 'N/A'}
              </text>
              <text
                x="150"
                y="170"
                textAnchor="middle"
                className="text-responsive-xs"
                fill="var(--color-text-secondary)"
                fontFamily="monospace"
              >
                {dominantProtocol ? `${dominantProtocol.percentage.toFixed(2)}%` : ''}
              </text>
            </svg>
          </div>
        </div>

        {/* Legend with Scrollable Container */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--spacing-sm)',
          maxHeight: '400px', // Limit height to prevent page stretching
          overflow: 'hidden'
        }}>
          <h4 className="text-responsive-md" style={{
            color: 'var(--color-text-primary)',
            fontWeight: '600',
            margin: '0 0 var(--spacing-sm) 0'
          }}>
            Protocol Breakdown
          </h4>
          
          {/* Scrollable Protocol List */}
          <div style={{
            maxHeight: '350px', // Set max height for scrolling
            overflowY: 'auto',
            overflowX: 'hidden',
            paddingRight: 'var(--spacing-xs)', // Space for scrollbar
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--spacing-sm)',
            // Custom scrollbar styling
            scrollbarWidth: 'thin',
            scrollbarColor: 'var(--color-border-primary) transparent'
          }}>
          
          {processedData.map((item, index) => (
            <div
              key={item.protocol}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: 'var(--spacing-sm)',
                backgroundColor: 'var(--color-bg-secondary)',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--color-border-primary)',
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = 'var(--color-bg-tertiary)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'var(--color-bg-secondary)';
              }}
            >
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--spacing-sm)'
              }}>
                <div style={{
                  width: '16px',
                  height: '16px',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: item.color
                }}></div>
                <span className="text-responsive-sm" style={{
                  color: 'var(--color-text-primary)',
                  fontWeight: '600'
                }}>
                  {item.protocol}
                </span>
              </div>
              
              <div style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'flex-end',
                gap: 'var(--spacing-xs)'
              }}>
                <span className="text-responsive-sm" style={{
                  color: 'var(--color-text-primary)',
                  fontWeight: '700',
                  fontFamily: 'monospace'
                }}>
                  {formatValue(item.displayValue, selectedView)}
                </span>
                <span className="text-responsive-xs" style={{
                  color: 'var(--color-text-secondary)'
                }}>
                  {item.percentage.toFixed(2)}% of total
                </span>
              </div>
            </div>
          ))}
          
          </div> {/* End of scrollable container */}
        </div>
      </div>

      {/* Statistics Summary */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
        gap: 'var(--spacing-md)',
        marginBottom: 'var(--spacing-lg)'
      }}>
        <div style={{
          backgroundColor: 'var(--color-bg-secondary)',
          padding: 'var(--spacing-md)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--color-border-primary)',
          textAlign: 'center'
        }}>
          <div className="text-responsive-xs" style={{
            color: 'var(--color-text-secondary)',
            marginBottom: 'var(--spacing-xs)'
          }}>
            Total Protocols
          </div>
          <div className="text-responsive-lg" style={{
            color: 'var(--color-accent-blue)',
            fontWeight: '700',
            fontFamily: 'monospace'
          }}>
            {processedData.length}
          </div>
        </div>

        <div style={{
          backgroundColor: 'var(--color-bg-secondary)',
          padding: 'var(--spacing-md)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--color-border-primary)',
          textAlign: 'center'
        }}>
          <div className="text-responsive-xs" style={{
            color: 'var(--color-text-secondary)',
            marginBottom: 'var(--spacing-xs)'
          }}>
            Dominant Protocol
          </div>
          <div className="text-responsive-lg" style={{
            color: dominantProtocol?.color || 'var(--color-text-primary)',
            fontWeight: '700'
          }}>
            {dominantProtocol?.protocol || 'N/A'}
          </div>
        </div>

        <div style={{
          backgroundColor: 'var(--color-bg-secondary)',
          padding: 'var(--spacing-md)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--color-border-primary)',
          textAlign: 'center'
        }}>
          <div className="text-responsive-xs" style={{
            color: 'var(--color-text-secondary)',
            marginBottom: 'var(--spacing-xs)'
          }}>
            Total Packets
          </div>
          <div className="text-responsive-lg" style={{
            color: 'var(--color-accent-green)',
            fontWeight: '700',
            fontFamily: 'monospace'
          }}>
            {formatValue(processedData.reduce((sum, item) => sum + item.packets, 0), 'packets')}
          </div>
        </div>

        <div style={{
          backgroundColor: 'var(--color-bg-secondary)',
          padding: 'var(--spacing-md)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--color-border-primary)',
          textAlign: 'center'
        }}>
          <div className="text-responsive-xs" style={{
            color: 'var(--color-text-secondary)',
            marginBottom: 'var(--spacing-xs)'
          }}>
            Total Bytes
          </div>
          <div className="text-responsive-lg" style={{
            color: 'var(--color-accent-purple)',
            fontWeight: '700',
            fontFamily: 'monospace'
          }}>
            {(() => {
              const totalBytes = processedData.reduce((sum, item) => sum + item.bytes, 0);
              if (totalBytes >= 1024 * 1024 * 1024) {
                return `${(totalBytes / (1024 * 1024 * 1024)).toFixed(2)}GB`;
              } else if (totalBytes >= 1024 * 1024) {
                return `${(totalBytes / (1024 * 1024)).toFixed(2)}MB`;
              } else if (totalBytes >= 1024) {
                return `${(totalBytes / 1024).toFixed(2)}KB`;
              } else {
                return `${totalBytes}B`;
              }
            })()}
          </div>
        </div>
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
          Real-time protocol analysis - Last {selectedWindow.toUpperCase()}
        </span>
      </div>
    </div>
  );
};

export default ProtocolDistributionChart; 
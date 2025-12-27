import React, { useState } from 'react';
import Card from '../../ui/Card';
import { SortIcon, NetworkIcon } from '../../ui/icons';
import { TimeWindowSelector } from '../../ui';
import { useApiData } from '../../../hooks/useApiData';
import { useTimezoneAwareApi } from '../../../hooks/useTimezoneAwareApi';
import { PortAnalysisData } from '../../../lib/types/iot';
import { getProtocolColor, getPortStatusColor, hexToRgba } from '../../../styles/colors';
import { WS_TOPICS } from '../../../config/api';

interface PortAnalysisPanelProps {
  deviceId: string;
  experimentId?: string | null;
  className?: string;
}

type SortField = 'port' | 'protocol' | 'service' | 'packets' | 'bytes' | 'percentage';
type SortDirection = 'asc' | 'desc' | 'none';

const PortAnalysisPanel: React.FC<PortAnalysisPanelProps> = ({ deviceId, experimentId, className }) => {
  const [selectedWindow, setSelectedWindow] = useState<string>('48h');
  
  const { getDevicePortAnalysis, formatTimestamp, timezoneInfo } = useTimezoneAwareApi({
    experimentId: experimentId || '',
    deviceId
  });

  // Use timezone-aware API with proper error handling
  const { data: portData, loading, error, refetch } = useApiData({
    fetchFn: () => getDevicePortAnalysis(deviceId, selectedWindow, experimentId || undefined),
    wsTopics: [WS_TOPICS.DEVICE_PORT_ANALYSIS(deviceId)],
    dependencies: [deviceId, selectedWindow, experimentId],
    timeWindow: selectedWindow,
    enabled: !!deviceId && !!experimentId
  });
  
  const typedPortData = (portData as PortAnalysisData[]) || [];
  
  const [sortField, setSortField] = useState<SortField>('percentage');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      const nextDirection: SortDirection = 
        sortDirection === 'none' ? 'desc' : 
        sortDirection === 'desc' ? 'asc' : 'none';
      setSortDirection(nextDirection);
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const getSortedData = (): PortAnalysisData[] => {
    if (!portData || !Array.isArray(portData)) return [];
    
    // Filter out STATISTICS entries and ensure valid data
    const validData = portData.filter((item: any) => 
      item.port !== 'STATISTICS' && 
      typeof item.port === 'number' && 
      typeof item.packets === 'number' && 
      typeof item.bytes === 'number' &&
      typeof item.percentage === 'number'
    );
    
    if (sortDirection === 'none') return validData;
    
    return [...validData].sort((a, b) => {
      let aValue = a[sortField];
      let bValue = b[sortField];
      
      // Handle protocol field sorting
      if (sortField === 'protocol') {
        aValue = String(aValue).toLowerCase();
        bValue = String(bValue).toLowerCase();
      }
      
      // For numerical fields
      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return sortDirection === 'asc' ? aValue - bValue : bValue - aValue;
      }
      
      // For string fields
      const aStr = String(aValue).toLowerCase();
      const bStr = String(bValue).toLowerCase();
      
      if (sortDirection === 'asc') {
        return aStr.localeCompare(bStr);
      } else {
        return bStr.localeCompare(aStr);
      }
    });
  };

  // Status display mapping for better UX
  const getStatusDisplay = (status: string) => {
    const color = getPortStatusColor(status);
    const statusLabels: Record<string, string> = {
      'very_active': 'Very Active',
      'moderate': 'Moderate',
      'bidirectional': 'Bidirectional',
      'low_activity': 'Low Activity',
      'active': 'Active',
      'inactive': 'Inactive',
      'blocked': 'Blocked',
      'open': 'Open',
      'closed': 'Closed',
      'filtered': 'Filtered'
    };
    return { 
      label: statusLabels[status] || status,
      color: color
    };
  };

  if (loading && !portData) {
    return (
      <Card className={className} padding="lg">
        <div style={{ 
          textAlign: 'center', 
          padding: 'var(--spacing-4xl)',
          color: 'var(--color-text-tertiary)'
        }}>
          <div className="animate-spin" style={{
            width: 'var(--spacing-3xl)',
            height: 'var(--spacing-3xl)',
            border: '2px solid var(--color-border-primary)',
            borderTop: '2px solid var(--color-accent-blue)',
            borderRadius: '50%',
            margin: '0 auto var(--spacing-lg)'
          }}></div>
          Loading port analysis...
        </div>
      </Card>
    );
  }

  const sortedData = getSortedData();

  return (
    <Card className={className} padding="lg">
      {/* Header */}
      <div style={{ marginBottom: 'var(--spacing-2xl)' }}>
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
              lineHeight: '1.3',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}>
              <NetworkIcon size={18} color="#3B82F6" />
              Port Analysis ({selectedWindow.toUpperCase()})
            </h3>
            <p className="text-responsive-sm" style={{
              color: 'var(--color-text-tertiary)',
              margin: 0,
              lineHeight: '1.5'
            }}>
              Network port usage and protocol distribution
            </p>
          </div>
          
          <TimeWindowSelector
            selectedWindow={selectedWindow}
            onWindowChange={setSelectedWindow}
            size="sm"
          />
        </div>
      </div>

      {/* Summary Cards */}
      <div className="responsive-grid responsive-grid-3" style={{
        marginBottom: 'var(--spacing-2xl)'
      }}>
        <div style={{
          backgroundColor: 'var(--color-bg-primary)',
          padding: 'var(--card-padding-sm)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--color-border-primary)',
          textAlign: 'center'
        }}>
          <div className="text-responsive-sm" style={{
            color: 'var(--color-text-tertiary)',
            marginBottom: 'var(--spacing-xs)',
            fontWeight: '500'
          }}>
            Total Ports
          </div>
          <div className="text-responsive-lg" style={{
            color: 'var(--color-text-primary)',
            fontWeight: 'bold',
            lineHeight: '1.2'
          }}>
            {sortedData.length}
          </div>
        </div>

        <div style={{
          backgroundColor: 'var(--color-bg-primary)',
          padding: 'var(--card-padding-sm)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--color-border-primary)',
          textAlign: 'center'
        }}>
          <div className="text-responsive-sm" style={{
            color: 'var(--color-text-tertiary)',
            marginBottom: 'var(--spacing-xs)',
            fontWeight: '500'
          }}>
            Total Packets
          </div>
          <div className="text-responsive-lg" style={{
            color: 'var(--color-text-primary)',
            fontWeight: 'bold',
            lineHeight: '1.2'
          }}>
            {sortedData.reduce((sum, item) => sum + (item.packets || 0), 0).toLocaleString()}
          </div>
        </div>

        <div style={{
          backgroundColor: 'var(--color-bg-primary)',
          padding: 'var(--card-padding-sm)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--color-border-primary)',
          textAlign: 'center'
        }}>
          <div className="text-responsive-sm" style={{
            color: 'var(--color-text-tertiary)',
            marginBottom: 'var(--spacing-xs)',
            fontWeight: '500'
          }}>
            Total Data
          </div>
          <div className="text-responsive-lg" style={{
            color: 'var(--color-text-primary)',
            fontWeight: 'bold',
            lineHeight: '1.2'
          }}>
            {(() => {
              const totalBytes = sortedData.reduce((sum, item) => sum + (item.bytes || 0), 0);
              if (totalBytes >= 1024 * 1024 * 1024) {
                return `${(totalBytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
              } else if (totalBytes >= 1024 * 1024) {
                return `${(totalBytes / (1024 * 1024)).toFixed(1)} MB`;
              } else if (totalBytes >= 1024) {
                return `${(totalBytes / 1024).toFixed(1)} KB`;
              } else {
                return `${totalBytes} B`;
              }
            })()}
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="table-responsive" style={{ 
        maxHeight: '400px', 
        overflowY: 'auto',
        border: '1px solid var(--color-border-primary)',
        borderRadius: 'var(--radius-md)'
      }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead style={{ 
            position: 'sticky', 
            top: 0, 
            backgroundColor: 'var(--color-bg-secondary)', 
            zIndex: 1 
          }}>
            <tr style={{ borderBottom: '2px solid var(--color-border-primary)' }}>
              <th style={{
                padding: 'var(--spacing-lg)',
                textAlign: 'center',
                color: 'var(--color-text-secondary)',
                fontWeight: '600',
                fontSize: 'var(--text-sm)'
              }}>
                <button
                  onClick={() => handleSort('port')}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'inherit',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--spacing-xs)',
                    fontSize: 'inherit',
                    fontWeight: 'inherit',
                    margin: '0 auto'
                  }}
                >
                  PORT
                  <SortIcon 
                    direction={sortField === 'port' ? sortDirection : 'none'} 
                    size={14}
                  />
                </button>
              </th>
              <th style={{
                padding: 'var(--spacing-lg)',
                textAlign: 'center',
                color: 'var(--color-text-secondary)',
                fontWeight: '600',
                fontSize: 'var(--text-sm)'
              }}>
                <button
                  onClick={() => handleSort('protocol')}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'inherit',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--spacing-xs)',
                    fontSize: 'inherit',
                    fontWeight: 'inherit',
                    margin: '0 auto'
                  }}
                >
                  PROTOCOL
                  <SortIcon 
                    direction={sortField === 'protocol' ? sortDirection : 'none'} 
                    size={14}
                  />
                </button>
              </th>
              <th style={{
                padding: 'var(--spacing-lg)',
                textAlign: 'center',
                color: 'var(--color-text-secondary)',
                fontWeight: '600',
                fontSize: 'var(--text-sm)'
              }}>
                <button
                  onClick={() => handleSort('packets')}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'inherit',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--spacing-xs)',
                    fontSize: 'inherit',
                    fontWeight: 'inherit',
                    margin: '0 auto'
                  }}
                >
                  PACKETS
                  <SortIcon 
                    direction={sortField === 'packets' ? sortDirection : 'none'} 
                    size={14}
                  />
                </button>
              </th>
              <th style={{
                padding: 'var(--spacing-lg)',
                textAlign: 'center',
                color: 'var(--color-text-secondary)',
                fontWeight: '600',
                fontSize: 'var(--text-sm)'
              }}>
                <button
                  onClick={() => handleSort('bytes')}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'inherit',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--spacing-xs)',
                    fontSize: 'inherit',
                    fontWeight: 'inherit',
                    margin: '0 auto'
                  }}
                >
                  DATA
                  <SortIcon 
                    direction={sortField === 'bytes' ? sortDirection : 'none'} 
                    size={14}
                  />
                </button>
              </th>
              <th style={{
                padding: 'var(--spacing-lg)',
                textAlign: 'center',
                color: 'var(--color-text-secondary)',
                fontWeight: '600',
                fontSize: 'var(--text-sm)'
              }}>
                <button
                  onClick={() => handleSort('percentage')}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'inherit',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--spacing-xs)',
                    fontSize: 'inherit',
                    fontWeight: 'inherit',
                    margin: '0 auto'
                  }}
                >
                  USAGE %
                  <SortIcon 
                    direction={sortField === 'percentage' ? sortDirection : 'none'} 
                    size={14}
                  />
                </button>
              </th>
              <th style={{
                padding: 'var(--spacing-lg)',
                textAlign: 'center',
                color: 'var(--color-text-secondary)',
                fontWeight: '600',
                fontSize: 'var(--text-sm)'
              }}>
                STATUS
              </th>
            </tr>
          </thead>
          <tbody>
            {sortedData.map((item, index) => (
              <tr 
                key={`port-${item.port}-${item.protocol}-${item.packets}-${index}`}
                style={{
                  borderBottom: '1px solid var(--color-border-primary)',
                  transition: 'background-color 0.2s ease'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = 'var(--color-bg-tertiary)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'transparent';
                }}
              >
                <td style={{ 
                  padding: 'var(--spacing-lg)', 
                  textAlign: 'center',
                  color: 'var(--color-text-secondary)',
                  fontSize: 'var(--text-sm)',
                  fontWeight: '600',
                  fontFamily: 'monospace'
                }}>
                  {item.port}
                </td>
                <td style={{ 
                  padding: 'var(--spacing-lg)',
                  textAlign: 'center'
                }}>
                  <span style={{
                    backgroundColor: getProtocolColor(item.protocol || 'Unknown'),
                    color: 'var(--color-text-primary)',
                    padding: 'var(--spacing-xs) var(--spacing-sm)',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: 'var(--text-xs)',
                    fontWeight: '600',
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px'
                  }}>
                    {item.protocol || 'Unknown'}
                  </span>
                </td>
                <td style={{ 
                  padding: 'var(--spacing-lg)', 
                  textAlign: 'center',
                  color: 'var(--color-text-secondary)',
                  fontSize: 'var(--text-sm)',
                  fontWeight: '500',
                  fontFamily: 'monospace'
                }}>
                  {(item.packets || 0).toLocaleString()}
                </td>
                <td style={{ 
                  padding: 'var(--spacing-lg)', 
                  textAlign: 'center',
                  color: 'var(--color-text-secondary)',
                  fontSize: 'var(--text-sm)',
                  fontWeight: '500',
                  fontFamily: 'monospace'
                }}>
                  {(() => {
                    const bytes = item.bytes || 0;
                    if (bytes >= 1024 * 1024 * 1024) {
                      return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
                    } else if (bytes >= 1024 * 1024) {
                      return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
                    } else if (bytes >= 1024) {
                      return `${(bytes / 1024).toFixed(1)} KB`;
                    } else {
                      return `${bytes} B`;
                    }
                  })()}
                </td>
                <td style={{ 
                  padding: 'var(--spacing-lg)', 
                  textAlign: 'center'
                }}>
                  <div style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'center', 
                    gap: 'var(--spacing-sm)' 
                  }}>
                    <div style={{
                      width: 'clamp(3rem, 15vw, 4rem)',
                      height: 'var(--spacing-sm)',
                      backgroundColor: 'var(--color-bg-tertiary)',
                      borderRadius: 'var(--radius-sm)',
                      overflow: 'hidden',
                      position: 'relative'
                    }}>
                      <div style={{
                        width: `${Math.min(100, Math.max(0, item.percentage || 0))}%`,
                        height: '100%',
                        backgroundColor: getProtocolColor(item.protocol || 'Unknown'),
                        borderRadius: 'var(--radius-sm)',
                        transition: 'width 0.3s ease'
                      }} />
                    </div>
                    <span className="text-responsive-sm" style={{
                      color: 'var(--color-text-secondary)',
                      fontWeight: 'bold',
                      minWidth: 'var(--spacing-3xl)',
                      textAlign: 'center',
                      fontFamily: 'monospace'
                    }}>
                      {(item.percentage || 0).toFixed(1)}%
                    </span>
                  </div>
                </td>
                <td style={{ 
                  padding: 'var(--spacing-lg)', 
                  textAlign: 'center'
                }}>
                  <span style={{
                    backgroundColor: getStatusDisplay(item.status || 'unknown').color,
                    color: 'var(--color-text-primary)',
                    padding: 'var(--spacing-xs) var(--spacing-sm)',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: 'var(--text-xs)',
                    fontWeight: '600',
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px'
                  }}>
                    {getStatusDisplay(item.status || 'unknown').label}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {sortedData.length === 0 && (
        <div style={{
          padding: 'var(--spacing-4xl)',
          textAlign: 'center',
          color: 'var(--color-text-tertiary)'
        }}>
          No port analysis data available.
        </div>
      )}
    </Card>
  );
};

export default PortAnalysisPanel; 
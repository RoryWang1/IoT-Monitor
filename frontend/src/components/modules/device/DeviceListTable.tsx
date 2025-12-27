import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/router';
import Card from '../../ui/Card';
import StatusIndicator from '../../ui/StatusIndicator';
import Tooltip from '../../ui/Tooltip';
import Modal from '../../ui/Modal';
import { SortIcon } from '../../ui/icons';
import { DeviceData } from '../../../lib/types/iot';
import apiClient from '../../../services/apiClient';

interface DeviceListTableProps {
  experimentId: string;
  className?: string;
}

type SortField = 'deviceName' | 'deviceType' | 'status' | 'lastSeen';
type SortDirection = 'asc' | 'desc' | 'none';

const DeviceListTable: React.FC<DeviceListTableProps> = ({ experimentId, className }) => {
  const router = useRouter();
  const [devices, setDevices] = useState<DeviceData[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortField, setSortField] = useState<SortField>('deviceName');
  const [sortDirection, setSortDirection] = useState<SortDirection>('none');
  const [selectedDevice, setSelectedDevice] = useState<DeviceData | null>(null);
  const [showModal, setShowModal] = useState(false);

  const fetchDevices = useCallback(async () => {
    try {
      // Updated API call for experiment devices data using API client
      const data = await apiClient.getExperimentDevices(experimentId);
      setDevices(data as DeviceData[]);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch experiment devices:', error);
      setLoading(false);
    }
  }, [experimentId]);

  useEffect(() => {
    fetchDevices();
  }, [fetchDevices]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      const nextDirection: SortDirection = 
        sortDirection === 'none' ? 'asc' : 
        sortDirection === 'asc' ? 'desc' : 'none';
      setSortDirection(nextDirection);
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const getSortedDevices = () => {
    let filtered = devices.filter(device =>
      (device.deviceName || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (device.deviceType || '').toLowerCase().includes(searchTerm.toLowerCase())
    );

    if (sortDirection === 'none') return filtered;

    return filtered.sort((a, b) => {
      let aValue = a[sortField] || '';
      let bValue = b[sortField] || '';

      if (typeof aValue === 'string') aValue = aValue.toLowerCase();
      if (typeof bValue === 'string') bValue = bValue.toLowerCase();

      if (sortDirection === 'asc') {
        return aValue < bValue ? -1 : aValue > bValue ? 1 : 0;
      } else {
        return aValue > bValue ? -1 : aValue < bValue ? 1 : 0;
      }
    });
  };

  const handleDeviceClick = (device: DeviceData) => {
    // Use current experiment_id from props or fallback to localStorage
    const currentExperimentId = experimentId || (typeof window !== 'undefined' ? localStorage.getItem('current_experiment_id') : null) || 'experiment_1';
    
    // Store current experiment in localStorage for data consistency
    if (typeof window !== 'undefined') {
      localStorage.setItem('current_experiment_id', currentExperimentId);
    }
    
    router.push(`/device-detail/${device.deviceId}?experiment_id=${currentExperimentId}`);
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'online': return '#10B981';
      case 'offline': return '#EF4444';
      default: return 'var(--color-text-tertiary)';
    }
  };

  if (loading) {
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
          Loading devices...
        </div>
      </Card>
    );
  }

  const sortedDevices = getSortedDevices();

  return (
    <>
      <Card className={className} padding="lg">
        {/* Header */}
        <div className="responsive-flex" style={{
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 'var(--spacing-2xl)',
          flexWrap: 'wrap'
        }}>
          <h3 className="text-responsive-xl" style={{
            color: 'var(--color-text-primary)',
            fontWeight: 'bold',
            margin: 0,
            lineHeight: '1.3'
          }}>
            Device List ({sortedDevices.length})
          </h3>
          
          <input
            type="text"
            placeholder="Search devices..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              backgroundColor: 'var(--color-bg-primary)',
              border: '1px solid var(--color-border-primary)',
              borderRadius: 'var(--radius-md)',
              padding: 'var(--spacing-sm) var(--spacing-lg)',
              color: 'var(--color-text-primary)',
              fontSize: 'var(--text-sm)',
              minWidth: 'min(100%, 250px)',
              transition: 'border-color 0.2s ease'
            }}
            onFocus={(e) => e.target.style.borderColor = 'var(--color-accent-blue)'}
            onBlur={(e) => e.target.style.borderColor = 'var(--color-border-primary)'}
          />
        </div>

        {/* Table */}
        <div className="table-responsive">
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--color-border-primary)' }}>
                <th style={{
                  padding: 'var(--spacing-lg)',
                  textAlign: 'left',
                  color: 'var(--color-text-secondary)',
                  fontWeight: '600',
                  fontSize: 'var(--text-sm)'
                }}>
                  <button
                    onClick={() => handleSort('deviceName')}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'inherit',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 'var(--spacing-xs)',
                      fontSize: 'inherit',
                      fontWeight: 'inherit'
                    }}
                  >
                    Device Name
                    <SortIcon 
                      direction={sortField === 'deviceName' ? sortDirection : 'none'} 
                      size={14}
                    />
                  </button>
                </th>
                <th style={{
                  padding: 'var(--spacing-lg)',
                  textAlign: 'left',
                  color: 'var(--color-text-secondary)',
                  fontWeight: '600',
                  fontSize: 'var(--text-sm)'
                }}>
                  <button
                    onClick={() => handleSort('deviceType')}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'inherit',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 'var(--spacing-xs)',
                      fontSize: 'inherit',
                      fontWeight: 'inherit'
                    }}
                  >
                    Type
                    <SortIcon 
                      direction={sortField === 'deviceType' ? sortDirection : 'none'} 
                      size={14}
                    />
                  </button>
                </th>
                <th style={{
                  padding: 'var(--spacing-lg)',
                  textAlign: 'left',
                  color: 'var(--color-text-secondary)',
                  fontWeight: '600',
                  fontSize: 'var(--text-sm)'
                }}>
                  IP Address
                </th>
                <th style={{
                  padding: 'var(--spacing-lg)',
                  textAlign: 'left',
                  color: 'var(--color-text-secondary)',
                  fontWeight: '600',
                  fontSize: 'var(--text-sm)'
                }}>
                  MAC Address
                </th>
                <th style={{
                  padding: 'var(--spacing-lg)',
                  textAlign: 'left',
                  color: 'var(--color-text-secondary)',
                  fontWeight: '600',
                  fontSize: 'var(--text-sm)'
                }}>
                  Vendor
                </th>
                <th style={{
                  padding: 'var(--spacing-lg)',
                  textAlign: 'left',
                  color: 'var(--color-text-secondary)',
                  fontWeight: '600',
                  fontSize: 'var(--text-sm)'
                }}>
                  <button
                    onClick={() => handleSort('status')}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'inherit',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 'var(--spacing-xs)',
                      fontSize: 'inherit',
                      fontWeight: 'inherit'
                    }}
                  >
                    Status
                    <SortIcon 
                      direction={sortField === 'status' ? sortDirection : 'none'} 
                      size={14}
                    />
                  </button>
                </th>
                <th style={{
                  padding: 'var(--spacing-lg)',
                  textAlign: 'left',
                  color: 'var(--color-text-secondary)',
                  fontWeight: '600',
                  fontSize: 'var(--text-sm)'
                }}>
                  <button
                    onClick={() => handleSort('lastSeen')}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'inherit',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 'var(--spacing-xs)',
                      fontSize: 'inherit',
                      fontWeight: 'inherit'
                    }}
                  >
                    Last Seen
                    <SortIcon 
                      direction={sortField === 'lastSeen' ? sortDirection : 'none'} 
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
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedDevices.map((device) => (
                <tr 
                  key={device.deviceId}
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
                    color: 'var(--color-text-secondary)',
                    fontSize: 'var(--text-sm)',
                    fontWeight: '500'
                  }}>
                    <div>
                      {device.resolvedName || device.deviceName}
                      {device.resolutionSource && device.resolutionSource !== 'original' && (
                        <span style={{
                          fontSize: 'var(--text-xs)',
                          color: 'var(--color-text-tertiary)',
                          marginLeft: 'var(--spacing-xs)'
                        }}>
                          ({device.resolutionSource === 'known_device' ? 'Known' : 'OUI'})
                        </span>
                      )}
                    </div>
                  </td>
                  <td style={{ 
                    padding: 'var(--spacing-lg)', 
                    color: 'var(--color-text-secondary)',
                    fontSize: 'var(--text-sm)'
                  }}>
                    <span style={{
                      backgroundColor: 'var(--color-bg-primary)',
                      padding: 'var(--spacing-xs) var(--spacing-sm)',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: 'var(--text-xs)',
                      fontWeight: '500'
                    }}>
                      {device.resolvedType || device.deviceType}
                    </span>
                  </td>
                  <td style={{ 
                    padding: 'var(--spacing-lg)', 
                    color: 'var(--color-text-secondary)',
                    fontSize: 'var(--text-sm)',
                    fontFamily: 'monospace'
                  }}>
                    {device.ipAddress}
                  </td>
                  <td style={{ 
                    padding: 'var(--spacing-lg)', 
                    color: 'var(--color-text-secondary)',
                    fontSize: 'var(--text-sm)',
                    fontFamily: 'monospace'
                  }}>
                    {device.macAddress}
                  </td>
                  <td style={{ 
                    padding: 'var(--spacing-lg)', 
                    color: 'var(--color-text-secondary)',
                    fontSize: 'var(--text-sm)'
                  }}>
                    <div>
                      {device.resolvedVendor || 'Unknown'}
                      {device.resolutionSource === 'vendor_pattern' && (
                        <div style={{
                          fontSize: 'var(--text-xs)',
                          color: 'var(--color-text-tertiary)',
                          marginTop: '2px'
                        }}>
                          OUI Match
                        </div>
                      )}
                    </div>
                  </td>
                  <td style={{ padding: 'var(--spacing-lg)' }}>
                    <StatusIndicator 
                      status={device.status || 'unknown'} 
                      size="sm"
                      color={getStatusColor(device.status || 'unknown')}
                    />
                  </td>
                  <td style={{ 
                    padding: 'var(--spacing-lg)', 
                    color: 'var(--color-text-tertiary)', 
                    fontSize: 'var(--text-sm)'
                  }}>
                    {device.lastSeen}
                  </td>
                  <td style={{ 
                    padding: 'var(--spacing-lg)', 
                    textAlign: 'center' 
                  }}>
                    <button
                      onClick={() => handleDeviceClick(device)}
                      className="button-responsive"
                      style={{
                        backgroundColor: 'var(--color-accent-blue)',
                        color: 'var(--color-text-primary)',
                        border: 'none',
                        cursor: 'pointer',
                        fontWeight: '500'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor = '#2563EB';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = 'var(--color-accent-blue)';
                      }}
                    >
                      Details
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {sortedDevices.length === 0 && (
          <div style={{
            padding: 'var(--spacing-4xl)',
            textAlign: 'center',
            color: 'var(--color-text-tertiary)'
          }}>
            {searchTerm ? 'No devices found matching your search.' : 'No devices available.'}
          </div>
        )}
      </Card>

      {/* Device Details Modal */}
      <Modal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        title={selectedDevice?.deviceName}
        size="lg"
      >
        {selectedDevice && (
          <div className="responsive-grid responsive-grid-2">
            <div>
              <div className="text-responsive-sm" style={{
                color: 'var(--color-text-tertiary)',
                marginBottom: 'var(--spacing-xs)',
                fontWeight: '500'
              }}>
                Device Type
              </div>
              <div className="text-responsive-base" style={{
                color: 'var(--color-text-primary)',
                fontWeight: 'bold',
                marginBottom: 'var(--spacing-lg)'
              }}>
                {selectedDevice.deviceType || 'Unknown Type'}
              </div>

              <div className="text-responsive-sm" style={{
                color: 'var(--color-text-tertiary)',
                marginBottom: 'var(--spacing-xs)',
                fontWeight: '500'
              }}>
                IP Address
              </div>
              <div className="text-responsive-base" style={{
                color: 'var(--color-text-primary)',
                fontWeight: 'bold',
                marginBottom: 'var(--spacing-lg)',
                fontFamily: 'monospace'
              }}>
                {selectedDevice.ipAddress}
              </div>

              <div className="text-responsive-sm" style={{
                color: 'var(--color-text-tertiary)',
                marginBottom: 'var(--spacing-xs)',
                fontWeight: '500'
              }}>
                MAC Address
              </div>
              <div style={{
                color: 'var(--color-text-primary)',
                fontWeight: 'bold',
                marginBottom: 'var(--spacing-lg)',
                fontFamily: 'monospace',
                fontSize: 'var(--text-sm)'
              }}>
                {selectedDevice.macAddress}
              </div>

              <div className="text-responsive-sm" style={{
                color: 'var(--color-text-tertiary)',
                marginBottom: 'var(--spacing-xs)',
                fontWeight: '500'
              }}>
                Status
              </div>
              <div style={{ marginBottom: 'var(--spacing-lg)' }}>
                <StatusIndicator 
                  status={selectedDevice.status || 'unknown'} 
                  size="md"
                  color={getStatusColor(selectedDevice.status || 'unknown')}
                />
              </div>

              <div className="text-responsive-sm" style={{
                color: 'var(--color-text-tertiary)',
                marginBottom: 'var(--spacing-xs)',
                fontWeight: '500'
              }}>
                Last Seen
              </div>
              <div className="text-responsive-base" style={{
                color: 'var(--color-text-primary)',
                fontWeight: 'bold',
                marginBottom: 'var(--spacing-lg)'
              }}>
                {selectedDevice.lastSeen}
              </div>
            </div>

            <div>
              <div className="text-responsive-sm" style={{
                color: 'var(--color-text-tertiary)',
                marginBottom: 'var(--spacing-xs)',
                fontWeight: '500'
              }}>
                Traffic Statistics
              </div>
              <div style={{
                backgroundColor: 'var(--color-bg-primary)',
                padding: 'var(--spacing-lg)',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-border-primary)'
              }}>
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  marginBottom: 'var(--spacing-sm)'
                }}>
                  <span style={{ color: 'var(--color-text-tertiary)', fontSize: 'var(--text-sm)' }}>
                    Packets Sent:
                  </span>
                  <span style={{ color: 'var(--color-text-primary)', fontWeight: 'bold', fontSize: 'var(--text-sm)' }}>
                    {selectedDevice.packetsSent?.toLocaleString() || 'N/A'}
                  </span>
                </div>
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  marginBottom: 'var(--spacing-sm)'
                }}>
                  <span style={{ color: 'var(--color-text-tertiary)', fontSize: 'var(--text-sm)' }}>
                    Packets Received:
                  </span>
                  <span style={{ color: 'var(--color-text-primary)', fontWeight: 'bold', fontSize: 'var(--text-sm)' }}>
                    {selectedDevice.packetsReceived?.toLocaleString() || 'N/A'}
                  </span>
                </div>
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between'
                }}>
                  <span style={{ color: 'var(--color-text-tertiary)', fontSize: 'var(--text-sm)' }}>
                    Data Volume:
                  </span>
                  <span style={{ color: 'var(--color-text-primary)', fontWeight: 'bold', fontSize: 'var(--text-sm)' }}>
                    {selectedDevice.dataVolume || 'N/A'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}
      </Modal>
    </>
  );
};

export default DeviceListTable; 
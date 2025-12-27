import React from 'react';
import { useRouter } from 'next/router';
import Card from '../../ui/Card';
import ApiErrorHandler from '../../ui/ApiErrorHandler';
import { useExperimentsOverview } from '../../../hooks/useApiData';
import apiClient from '../../../services/apiClient';
import { DeviceIcon, NetworkIcon } from '../../ui/icons';

interface ExperimentOverviewGridProps {
  className?: string;
}

const ExperimentOverviewGrid: React.FC<ExperimentOverviewGridProps> = ({ className }) => {
  const router = useRouter();
  const { data: experimentsData, loading, error, refetch } = useExperimentsOverview();
  
  // The experimental data was obtained successfully. Continue rendering

  const handleExperimentClick = (experimentId: string) => {
    // Store current experiment in localStorage for data consistency
    if (typeof window !== 'undefined') {
      localStorage.setItem('current_experiment_id', experimentId);
    }
    
    const targetUrl = `/experiment-detail/${experimentId}?experiment_id=${experimentId}`;
    router.push(targetUrl);
  };



  const renderMiniChart = (data: any[]) => {
    if (!data || !Array.isArray(data) || data.length === 0) {
      return null;
    }
    
    // Convert data to numbers - handle both number[] and object[] formats
    const numbers = data.map(item => {
      if (typeof item === 'number') {
        return item;
      } else if (typeof item === 'object' && item !== null) {
        // If it's an object with bytes property, use bytes value
        return item.bytes || item.packets || item.value || 0;
      }
      return 0;
    }).filter(val => !isNaN(val) && isFinite(val));
    
    if (numbers.length === 0) {
      return null;
    }
    
    const maxValue = Math.max(...numbers);
    const validMaxValue = maxValue > 0 ? maxValue : 1;
    
    return (
      <svg width="40" height="20" style={{ marginLeft: 'var(--spacing-sm)' }}>
        {numbers.map((value, index) => {
          const barHeight = Math.max(1, (value / validMaxValue) * 18);
          const barWidth = Math.max(1, 35 / numbers.length);
          const x = index * (40 / numbers.length);
          const y = 20 - barHeight;
          
          return (
            <rect
              key={index}
              x={x}
              y={y}
              width={barWidth}
              height={barHeight}
              fill="var(--color-accent-blue)"
              opacity={0.7}
            />
          );
        })}
      </svg>
    );
  };

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'completed':
      case 'active':
      case 'running':
        return 'var(--color-accent-green)';
      case 'pending':
      case 'processing':
        return 'var(--color-accent-yellow)';
      case 'failed':
      case 'error':
        return 'var(--color-accent-red)';
      case 'paused':
      case 'stopped':
        return 'var(--color-text-tertiary)';
      default:
        return 'var(--color-accent-blue)';
    }
  };

  const formatBytes = (bytes: number | string): string => {
    const numBytes = typeof bytes === 'number' ? bytes : parseFloat(String(bytes)) || 0;
    
    if (numBytes >= 1024 * 1024 * 1024) {
      return `${(numBytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
    } else if (numBytes >= 1024 * 1024) {
      return `${(numBytes / (1024 * 1024)).toFixed(1)} MB`;
    } else if (numBytes >= 1024) {
      return `${(numBytes / 1024).toFixed(1)} KB`;
    }
    return `${numBytes} B`;
  };

  // if there is data, loading should not be displayed
  if (loading && (!experimentsData || !Array.isArray(experimentsData) || experimentsData.length === 0)) {
    return (
      <div className={className}>
        <div className="responsive-grid responsive-grid-auto">
          {Array.from({ length: 5 }).map((_, i) => (
            <Card key={`loading-${i}`} padding="lg">
              <div style={{ 
                color: 'var(--color-text-tertiary)', 
                textAlign: 'center',
                padding: 'var(--spacing-xl)'
              }}>
                <div className="animate-spin" style={{
                  width: 'var(--spacing-2xl)',
                  height: 'var(--spacing-2xl)',
                  border: '2px solid var(--color-border-primary)',
                  borderTop: '2px solid var(--color-accent-blue)',
                  borderRadius: '50%',
                  margin: '0 auto var(--spacing-md)'
                }}></div>
                Loading...
              </div>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (error && (!experimentsData || !Array.isArray(experimentsData) || experimentsData.length === 0)) {
    return (
      <div className={className}>
        <ApiErrorHandler
          error={error}
          onRetry={refetch}
          showRetry={true}
        />
      </div>
    );
  }

  // Check data validity
  if (!experimentsData || !Array.isArray(experimentsData) || experimentsData.length === 0) {
    return (
      <div className={className}>
        <Card padding="lg">
          <div style={{ 
            textAlign: 'center',
            color: 'var(--color-text-tertiary)',
            padding: 'var(--spacing-xl)'
          }}>
            <h3>No Experiments Found</h3>
            <p>No experiment data is available at the moment.</p>
            <button 
              onClick={() => refetch()}
              style={{
                backgroundColor: 'var(--color-accent-blue)',
                color: 'white',
                border: 'none',
                padding: 'var(--spacing-sm) var(--spacing-md)',
                borderRadius: 'var(--radius-md)',
                cursor: 'pointer'
              }}
            >
              Retry
            </button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className={className}>
      <div className="responsive-grid responsive-grid-auto">
        {experimentsData.map((experiment, index) => {
          // Verify required fields
          const experimentId = experiment.experimentId || `experiment_${index}`;
          const experimentName = experiment.experimentName || `Experiment ${index + 1}`;
          const deviceCount = experiment.deviceCount || 0;
          const onlineDevices = experiment.onlineDevices || 0;
          const totalTraffic = experiment.totalTraffic || '0 B';
          const status = experiment.status || 'unknown';
          const deviceTypes = experiment.deviceTypes || {};
          
          return (
            <Card
              key={experimentId}
              hover
              onClick={() => handleExperimentClick(experimentId)}
              padding="lg"
            >
              {/* Experiment Name */}
              <h3 className="text-responsive-xl" style={{
                color: 'var(--color-text-primary)',
                fontWeight: 'bold',
                margin: '0 0 var(--spacing-sm) 0',
                lineHeight: '1.3'
              }}>
                {experimentName}
              </h3>

              {/* Status Badge */}
              <div style={{
                display: 'inline-block',
                backgroundColor: getStatusColor(status),
                color: 'white',
                padding: 'var(--spacing-xs) var(--spacing-sm)',
                borderRadius: 'var(--radius-sm)',
                fontSize: 'var(--text-xs)',
                fontWeight: '500',
                textTransform: 'uppercase',
                marginBottom: 'var(--spacing-md)'
              }}>
                {status}
              </div>

              {/* Stats Grid */}
              <div className="responsive-grid responsive-grid-2">
                <div>
                  <div className="text-responsive-xs" style={{
                    color: 'var(--color-text-tertiary)',
                    marginBottom: 'var(--spacing-xs)',
                    fontWeight: '500',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}>
                    <DeviceIcon size={12} color="#6B7280" />
                    Devices
                  </div>
                  <div className="text-responsive-lg" style={{
                    color: 'var(--color-text-primary)',
                    fontWeight: 'bold',
                    lineHeight: '1.2'
                  }}>
                    {deviceCount}
                  </div>
                  <div className="text-responsive-xs" style={{
                    color: 'var(--color-text-secondary)',
                    marginTop: 'var(--spacing-xs)'
                  }}>
                    {onlineDevices} online
                  </div>
                </div>

                <div>
                  <div className="text-responsive-xs" style={{
                    color: 'var(--color-text-tertiary)',
                    marginBottom: 'var(--spacing-xs)',
                    fontWeight: '500',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}>
                    <NetworkIcon size={12} color="#6B7280" />
                    Total Traffic
                  </div>
                  <div className="text-responsive-lg" style={{
                    color: 'var(--color-accent-blue)',
                    fontWeight: 'bold',
                    lineHeight: '1.2'
                  }}>
                    {totalTraffic}
                  </div>
                </div>
              </div>

              {/* Device Types */}
              {Object.keys(deviceTypes).length > 0 && (
                <div style={{
                  marginTop: 'var(--spacing-md)'
                }}>
                  <div className="text-responsive-sm" style={{
                    color: 'var(--color-text-tertiary)',
                    marginBottom: 'var(--spacing-xs)',
                    fontWeight: '500'
                  }}>
                    Device Types
                  </div>
                  <div style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: 'var(--spacing-xs)'
                  }}>
                    {Object.entries(deviceTypes).map(([type, count]) => (
                      <span key={`${experimentId}-${type}`} style={{
                        backgroundColor: 'var(--color-bg-primary)',
                        color: 'var(--color-text-secondary)',
                        padding: 'var(--spacing-xs)',
                        borderRadius: 'var(--radius-sm)',
                        fontSize: 'var(--text-xs)',
                        border: '1px solid var(--color-border-primary)'
                      }}>
                        {type}: {count}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Description */}
              {experiment.description && (
                <div className="text-responsive-sm" style={{
                  color: 'var(--color-text-secondary)',
                  marginTop: 'var(--spacing-sm)',
                  fontStyle: 'italic'
                }}>
                  {experiment.description}
                </div>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
};

export default ExperimentOverviewGrid; 
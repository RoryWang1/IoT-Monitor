import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/router';
import PageLayout from '../../components/layout/PageLayout';
import Breadcrumb from '../../components/layout/Breadcrumb';
import { useExperimentDetail } from '../../hooks/useApiData';
import { useTimezone } from '../../hooks/useTimezone';
import { useTimezoneAwareApi } from '../../hooks/useTimezoneAwareApi';
import Card from '../../components/ui/Card';
import ApiErrorHandler from '../../components/ui/ApiErrorHandler';
import TimezoneSelector from '../../components/ui/TimezoneSelector';
import TimeWindowSelector from '../../components/ui/TimeWindowSelector';
import { SankeyNetworkFlowChart } from '../../components/visualizations';

import { ChartIcon, LinkIcon, GlobeIcon } from '../../components/ui/icons';

const ExperimentDetailPage: React.FC = () => {
  const router = useRouter();
  const { experimentId } = router.query;
  
  const { 
    data: experimentData, 
    loading, 
    error, 
    refetch 
  } = useExperimentDetail(experimentId);

  // Add timezone support for Last seen time formatting
  const { formatTimestamp } = useTimezone(typeof experimentId === 'string' ? experimentId : '');
  
  // Timezone-aware API calls
  const { 
    getNetworkFlowSankey, 
    timezoneInfo 
  } = useTimezoneAwareApi({ 
    experimentId: typeof experimentId === 'string' ? experimentId : '' 
  });

  // Sankey chart data and controls
  const [sankeyData, setSankeyData] = useState<any>(null);
  const [sankeyLoading, setSankeyLoading] = useState(false);
  const [sankeyError, setSankeyError] = useState<string | null>(null);
  const [sankeyFlowType, setSankeyFlowType] = useState('device-to-location');
  const [sankeyTimeWindow, setSankeyTimeWindow] = useState('48h');
  const [sankeyGroupBy, setSankeyGroupBy] = useState('device_name');

  // AbortController for canceling previous requests
  const abortControllerRef = useRef<AbortController | null>(null);

  // Timezone-aware fetch sankey data - fix AbortError by preventing race conditions
  const fetchSankeyData = useCallback(async () => {
    if (!experimentId || typeof experimentId !== 'string') {
      return;
    }

    // Cancel previous request if still running
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Create new AbortController for this request
    abortControllerRef.current = new AbortController();

    

    setSankeyLoading(true);
    setSankeyError(null);

    try {
      const response = await getNetworkFlowSankey(
        sankeyFlowType,
        sankeyTimeWindow,
        sankeyGroupBy,
        experimentId
      );

      setSankeyData(response);
    } catch (error: any) {
      // Only handle non-abort errors
      if (error.name !== 'AbortError') {
        console.error('Sankey API error:', error?.message);
        setSankeyError(error?.message || 'Failed to load network flow data');
      }
    } finally {
      setSankeyLoading(false);
      abortControllerRef.current = null;
    }
  }, [experimentId, sankeyFlowType, sankeyTimeWindow, sankeyGroupBy, getNetworkFlowSankey]);

  // Handle time window change
  const handleTimeWindowChange = useCallback((newTimeWindow: string) => {
    setSankeyTimeWindow(newTimeWindow);
  }, []);

  // Unified effect to fetch sankey data - prevent race conditions
  useEffect(() => {
    // Only proceed if we have all required data
    if (!experimentId || typeof experimentId !== 'string' || !timezoneInfo?.timezone) {
      return;
    }

    // Add debounce to prevent rapid requests
    const timer = setTimeout(() => {
      fetchSankeyData();
    }, 600); // Single debounce delay

    return () => {
      clearTimeout(timer);
      // Cancel any ongoing request when dependencies change
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [experimentId, sankeyFlowType, sankeyTimeWindow, sankeyGroupBy, timezoneInfo?.timezone, fetchSankeyData]); // All dependencies in one place

  // Show loading while router is not ready
  if (router.isFallback || !router.isReady) {
    return (
      <PageLayout
        title="Experiment Detail"
        subtitle="Loading experiment information..."
      >
        <div style={{ 
          display: 'flex', 
          justifyContent: 'center', 
          alignItems: 'center', 
          height: '50vh' 
        }}>
          <div className="animate-spin" style={{
            width: 'var(--spacing-3xl)',
            height: 'var(--spacing-3xl)',
            border: '3px solid var(--color-border-primary)',
            borderTop: '3px solid var(--color-accent-blue)',
            borderRadius: '50%'
          }}></div>
        </div>
      </PageLayout>
    );
  }

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat().format(num);
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'online':
        return '#10B981'; // Bright green, improve contrast
      case 'offline':
        return '#EF4444'; // Bright red, improve contrast
      default:
        return '#6B7280'; // Neutral gray, as fallback
    }
  };

  const handleDeviceClick = (deviceId: string) => {
    // Ensure experiment_id is passed when navigating to device detail
    const currentExperimentId = typeof experimentId === 'string' ? experimentId : 'experiment_1';
    
    // Store current experiment in localStorage for data consistency
    if (typeof window !== 'undefined') {
      localStorage.setItem('current_experiment_id', currentExperimentId);
    }
    
    router.push(`/device-detail/${deviceId}?experiment_id=${currentExperimentId}`);
  };

  const breadcrumbItems = [
    { label: 'IoT Monitor', href: '/' },
    { label: experimentData?.experimentName || 'Experiment' }
  ];

  if (loading && !experimentData) {
    return (
      <PageLayout
        title="Experiment Detail"
        subtitle="Loading experiment information..."
      >
        <div style={{ 
          display: 'flex', 
          justifyContent: 'center', 
          alignItems: 'center', 
          height: '50vh' 
        }}>
          <div className="animate-spin" style={{
            width: 'var(--spacing-3xl)',
            height: 'var(--spacing-3xl)',
            border: '3px solid var(--color-border-primary)',
            borderTop: '3px solid var(--color-accent-blue)',
            borderRadius: '50%'
          }}></div>
        </div>
      </PageLayout>
    );
  }

  if (error || !experimentData) {
    return (
      <PageLayout
        title="Experiment Detail"
        subtitle="Error loading experiment"
      >
        <ApiErrorHandler
          error={error || "Experiment not found"}
          onRetry={refetch}
          showRetry={true}
        />
      </PageLayout>
    );
  }

  return (
    <PageLayout
      title={experimentData.experimentName}
      subtitle={experimentData.description || "Experiment Details"}
      breadcrumb={<Breadcrumb items={breadcrumbItems} />}
    >
      <div style={{ 
        display: 'flex', 
        flexDirection: 'column', 
        gap: 'var(--spacing-lg)' 
      }}>
        
        {/* Timezone and Settings */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr auto',
          gap: 'var(--spacing-lg)',
          alignItems: 'start'
        }}>
          {/* Statistics Overview */}
          <Card padding="lg">
          <h2 style={{
            margin: '0 0 var(--spacing-lg) 0',
            color: 'var(--color-text-primary)',
            fontSize: 'var(--text-xl)',
            fontWeight: 'bold'
          }}>
            Experiment Statistics
          </h2>
          
          <div className="responsive-grid responsive-grid-4" style={{
            marginBottom: 'var(--spacing-lg)'
          }}>
            <div style={{
              backgroundColor: 'var(--color-bg-primary)',
              padding: 'var(--spacing-md)',
              borderRadius: 'var(--radius-md)',
              textAlign: 'center',
              border: '1px solid var(--color-border-primary)'
            }}>
              <div style={{
                color: 'var(--color-text-tertiary)',
                fontSize: 'var(--text-sm)',
                marginBottom: 'var(--spacing-xs)'
              }}>
                Total Devices
              </div>
              <div style={{
                color: 'var(--color-text-primary)',
                fontSize: 'var(--text-2xl)',
                fontWeight: 'bold'
              }}>
                {experimentData?.statistics?.totalDevices || 0}
              </div>
            </div>

            <div style={{
              backgroundColor: 'var(--color-bg-primary)',
              padding: 'var(--spacing-md)',
              borderRadius: 'var(--radius-md)',
              textAlign: 'center',
              border: '1px solid var(--color-border-primary)'
            }}>
              <div style={{
                color: 'var(--color-text-tertiary)',
                fontSize: 'var(--text-sm)',
                marginBottom: 'var(--spacing-xs)'
              }}>
                Online / Offline
              </div>
              <div style={{
                display: 'flex',
                justifyContent: 'center',
                gap: 'var(--spacing-sm)',
                alignItems: 'baseline'
              }}>
                <span style={{
                  color: 'var(--color-accent-green)',
                  fontSize: 'var(--text-xl)',
                  fontWeight: 'bold'
                }}>
                  {experimentData?.statistics?.onlineDevices || 0}
                </span>
                <span style={{
                  color: 'var(--color-text-tertiary)',
                  fontSize: 'var(--text-sm)'
                }}>
                  /
                </span>
                <span style={{
                  color: 'var(--color-accent-red)',
                  fontSize: 'var(--text-xl)',
                  fontWeight: 'bold'
                }}>
                  {experimentData?.statistics?.offlineDevices || 0}
                </span>
              </div>
            </div>

            <div style={{
              backgroundColor: 'var(--color-bg-primary)',
              padding: 'var(--spacing-md)',
              borderRadius: 'var(--radius-md)',
              textAlign: 'center',
              border: '1px solid var(--color-border-primary)'
            }}>
              <div style={{
                color: 'var(--color-text-tertiary)',
                fontSize: 'var(--text-sm)',
                marginBottom: 'var(--spacing-xs)'
              }}>
                Device Types
              </div>
              <div style={{
                color: 'var(--color-text-primary)',
                fontSize: 'var(--text-2xl)',
                fontWeight: 'bold'
              }}>
                {Object.keys(experimentData?.statistics?.deviceTypes || {}).length}
              </div>
            </div>

            <div style={{
              backgroundColor: 'var(--color-bg-primary)',
              padding: 'var(--spacing-md)',
              borderRadius: 'var(--radius-md)',
              textAlign: 'center',
              border: '1px solid var(--color-border-primary)'
            }}>
              <div style={{
                color: 'var(--color-text-tertiary)',
                fontSize: 'var(--text-sm)',
                marginBottom: 'var(--spacing-xs)'
              }}>
                Total Bytes
              </div>
              <div style={{
                color: 'var(--color-text-primary)',
                fontSize: 'var(--text-2xl)',
                fontWeight: 'bold'
              }}>
                {formatBytes(experimentData?.statistics?.totalBytes || 0)}
              </div>
            </div>
          </div>
        </Card>

        {/* Timezone Settings */}
        <TimezoneSelector 
          experimentId={typeof experimentId === 'string' ? experimentId : ''}
          onTimezoneChange={(newTimezone) => {
            console.log('Experiment detail timezone changed to:', newTimezone);
            
            // Data will auto-refresh via timezone useEffect
            refetch();
            
            // Notify all components about timezone change
            setTimeout(() => {
              window.dispatchEvent(new CustomEvent('timezoneChanged', { 
                detail: { 
                  newTimezone, 
                  experimentId: typeof experimentId === 'string' ? experimentId : ''
                } 
              }));
            }, 100);
          }}
        />
      </div>

      {/* Device List */}
        <Card padding="lg">
          <h2 style={{
            margin: '0 0 var(--spacing-lg) 0',
            color: 'var(--color-text-primary)',
            fontSize: 'var(--text-xl)',
            fontWeight: 'bold'
          }}>
            Devices ({experimentData?.devices?.length || 0})
          </h2>

          <div className="responsive-grid responsive-grid-auto" style={{
            gap: 'var(--spacing-md)'
          }}>
            {(experimentData?.devices || []).map((device) => (
              <Card
                key={device.deviceId}
                hover
                onClick={() => device.deviceId && handleDeviceClick(device.deviceId)}
                padding="md"
                style={{
                  cursor: 'pointer',
                  border: '1px solid var(--color-border-primary)'
                }}
              >
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  marginBottom: 'var(--spacing-sm)'
                }}>
                  <h3 style={{
                    margin: 0,
                    color: 'var(--color-text-primary)',
                    fontSize: 'var(--text-lg)',
                    fontWeight: 'bold'
                  }}>
                    {device.deviceName || 'Unknown Device'}
                  </h3>
                  <span style={{
                    padding: 'var(--spacing-xs)',
                    borderRadius: 'var(--radius-sm)',
                    backgroundColor: getStatusColor(device.status || 'unknown'),
                    color: 'white',
                    fontSize: 'var(--text-xs)',
                    fontWeight: '500',
                    textTransform: 'uppercase'
                  }}>
                    {device.status}
                  </span>
                </div>

                <div style={{
                  color: 'var(--color-text-secondary)',
                  fontSize: 'var(--text-sm)',
                  marginBottom: 'var(--spacing-xs)'
                }}>
                  {device.deviceType || 'Unknown Type'} • {device.manufacturer || 'Unknown'}
                </div>

                <div style={{
                  color: 'var(--color-text-tertiary)',
                  fontSize: 'var(--text-xs)',
                  fontFamily: 'monospace'
                }}>
                  MAC: {device.macAddress}
                  {device.ipAddress && (
                    <>
                      <br />
                      IP: {device.ipAddress}
                    </>
                  )}
                </div>

                {device.lastSeen && (
                  <div style={{
                    color: 'var(--color-text-tertiary)',
                    fontSize: 'var(--text-xs)',
                    marginTop: 'var(--spacing-xs)'
                  }}>
                    Last seen: {formatTimestamp(device.lastSeen, 'full')}
                  </div>
                )}
              </Card>
            ))}
          </div>
        </Card>

        {/* Device Types Summary */}
        <Card padding="lg">
          <h2 style={{
            margin: '0 0 var(--spacing-lg) 0',
            color: 'var(--color-text-primary)',
            fontSize: 'var(--text-xl)',
            fontWeight: 'bold'
          }}>
            Device Types Summary
          </h2>
          <div className="responsive-grid responsive-grid-auto" style={{
            gap: 'var(--spacing-md)'
          }}>
            {Object.entries(experimentData?.statistics?.deviceTypes || {}).map(([type, count]) => (
              <div key={type} style={{
                backgroundColor: 'var(--color-bg-primary)',
                padding: 'var(--spacing-md)',
                borderRadius: 'var(--radius-md)',
                textAlign: 'center',
                border: '1px solid var(--color-border-primary)'
              }}>
                <div style={{
                  color: 'var(--color-text-tertiary)',
                  fontSize: 'var(--text-sm)',
                  marginBottom: 'var(--spacing-xs)',
                  textTransform: 'capitalize'
                }}>
                  {type}
                </div>
                <div style={{
                  color: 'var(--color-text-primary)',
                  fontSize: 'var(--text-xl)',
                  fontWeight: 'bold'
                }}>
                  {count}
                </div>
              </div>
            ))}
          </div>
        </Card>



        {/* Network Flow Analysis */}
        <Card padding="lg">
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            marginBottom: 'var(--spacing-lg)'
          }}>
            <div>
              <h2 style={{
                margin: '0 0 var(--spacing-xs) 0',
                color: 'var(--color-text-primary)',
                fontSize: 'var(--text-xl)',
                fontWeight: 'bold'
              }}>
                Network Flow Analysis
              </h2>
              {/* Timezone and Data Info */}
              {timezoneInfo && (
                <div style={{
                  display: 'flex',
                  gap: 'var(--spacing-md)',
                  alignItems: 'center',
                  color: 'var(--color-text-tertiary)',
                  fontSize: 'var(--text-sm)'
                }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <GlobeIcon size={14} color="#6B7280" />
                    {timezoneInfo.timezone_display}
                  </span>
                  {sankeyData?.metadata?.total_traffic && (
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <ChartIcon size={14} color="#6B7280" />
                      {formatBytes(sankeyData.metadata.total_traffic)}
                    </span>
                  )}
                  {sankeyData?.metadata?.total_links && (
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <LinkIcon size={14} color="#6B7280" />
                      {sankeyData.metadata.total_links} connections
                    </span>
                  )}
                </div>
              )}
            </div>
            
            <div style={{
              display: 'flex',
              gap: 'var(--spacing-sm)',
              alignItems: 'center',
              flexWrap: 'wrap'
            }}>
              {/* Flow Type Selector */}
              <select
                value={sankeyFlowType}
                onChange={(e) => setSankeyFlowType(e.target.value)}
                style={{
                  padding: 'var(--spacing-sm)',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--color-border-primary)',
                  backgroundColor: 'var(--color-bg-primary)',
                  color: 'var(--color-text-primary)',
                  fontSize: 'var(--text-sm)',
                  minWidth: '160px'
                }}
              >
                <option value="device-to-location">Device → Location</option>
                <option value="device-to-device">Device → Device</option>
                <option value="protocol-to-service">Protocol → Service</option>
              </select>

              {/* Time Window Selector */}
              <TimeWindowSelector
                selectedWindow={sankeyTimeWindow}
                onWindowChange={setSankeyTimeWindow}
                size="sm"
              />

              {/* Group By Selector (only for relevant flow types) */}
              {sankeyFlowType === 'device-to-location' && (
                <select
                  value={sankeyGroupBy}
                  onChange={(e) => setSankeyGroupBy(e.target.value)}
                  style={{
                    padding: 'var(--spacing-sm)',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--color-border-primary)',
                    backgroundColor: 'var(--color-bg-primary)',
                    color: 'var(--color-text-primary)',
                    fontSize: 'var(--text-sm)',
                    minWidth: '140px'
                  }}
                >
                  <option value="device_type">By Device Type</option>
                  <option value="manufacturer">By Manufacturer</option>
                  <option value="device_name">By Device Name</option>
                </select>
              )}


            </div>
          </div>

          {/* Enhanced Data Summary */}
          {sankeyData?.metadata && (
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
              gap: 'var(--spacing-sm)',
              marginBottom: 'var(--spacing-md)',
              padding: 'var(--spacing-md)',
              backgroundColor: 'var(--color-bg-secondary)',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--color-border-primary)'
            }}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ color: 'var(--color-text-tertiary)', fontSize: 'var(--text-xs)' }}>
                  Flow Type
                </div>
                <div style={{ color: 'var(--color-text-primary)', fontSize: 'var(--text-sm)', fontWeight: 'bold' }}>
                  {sankeyFlowType.replace('-', ' → ').replace(/\b\w/g, l => l.toUpperCase())}
                </div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ color: 'var(--color-text-tertiary)', fontSize: 'var(--text-xs)' }}>
                  Time Window
                </div>
                <div style={{ color: 'var(--color-text-primary)', fontSize: 'var(--text-sm)', fontWeight: 'bold' }}>
                  {sankeyTimeWindow === 'auto' ? 'Auto (Full Range)' : sankeyTimeWindow}
                </div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ color: 'var(--color-text-tertiary)', fontSize: 'var(--text-xs)' }}>
                  Total Nodes
                </div>
                <div style={{ color: 'var(--color-text-primary)', fontSize: 'var(--text-sm)', fontWeight: 'bold' }}>
                  {sankeyData.metadata.total_nodes || 0}
                </div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ color: 'var(--color-text-tertiary)', fontSize: 'var(--text-xs)' }}>
                  Total Links
                </div>
                <div style={{ color: 'var(--color-text-primary)', fontSize: 'var(--text-sm)', fontWeight: 'bold' }}>
                  {sankeyData.metadata.total_links || 0}
                </div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ color: 'var(--color-text-tertiary)', fontSize: 'var(--text-xs)' }}>
                  Total Traffic
                </div>
                <div style={{ color: 'var(--color-text-primary)', fontSize: 'var(--text-sm)', fontWeight: 'bold' }}>
                  {formatBytes(sankeyData.metadata.total_traffic || 0)}
                </div>
              </div>
            </div>
          )}

          {/* Sankey Chart */}
          <SankeyNetworkFlowChart
            data={sankeyData}
            loading={sankeyLoading}
            error={sankeyError || undefined}
            width={1200}
            height={800}
          />
          
          {/* Data Scope Information */}
          {sankeyData?.metadata?.data_scope && (
            <div style={{
              marginTop: 'var(--spacing-md)',
              padding: 'var(--spacing-sm)',
              backgroundColor: 'var(--color-bg-tertiary)',
              borderRadius: 'var(--radius-sm)',
              fontSize: 'var(--text-xs)',
              color: 'var(--color-text-tertiary)',
              textAlign: 'center'
            }}>
              Data Scope: {sankeyData.metadata.data_scope}
            </div>
          )}
        </Card>
      </div>
    </PageLayout>
  );
};

export default ExperimentDetailPage; 
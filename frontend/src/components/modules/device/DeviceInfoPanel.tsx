import React, { useState } from 'react';
import Card from '../../ui/Card';
import StatusIndicator from '../../ui/StatusIndicator';
import TimeWindowSelector from '../../ui/TimeWindowSelector';
import { DeviceDetailInfo } from '../../../lib/types/iot';
import { useApiData } from '../../../hooks/useApiData';
import { useTimezoneAwareApi } from '../../../hooks/useTimezoneAwareApi';
import { WS_TOPICS } from '../../../config/api';
import { InfoIcon, ClockIcon, NetworkIcon } from '../../ui/icons';

interface DeviceInfoPanelProps {
  deviceId: string;
  experimentId: string | null;
  className?: string;
}

const DeviceInfoPanel: React.FC<DeviceInfoPanelProps> = ({ deviceId, experimentId, className }) => {
  const [timeWindow, setTimeWindow] = useState<string>('48h');
  
  const { getDeviceDetail, formatTimestamp, timezoneInfo } = useTimezoneAwareApi({
    experimentId: experimentId || '',
    deviceId
  });

  // Fetch device info with the selected time window using timezone-aware API
  const { data: deviceInfo, loading, error } = useApiData({
    fetchFn: () => getDeviceDetail(deviceId, experimentId || undefined, timeWindow),
    wsTopics: [WS_TOPICS.DEVICE_DETAIL(deviceId)],
    dependencies: [deviceId, experimentId, timeWindow, timezoneInfo?.timezone],
    timeWindow,
    enabled: !!deviceId && !!experimentId
  });

  if (loading && !deviceInfo) {
    return (
      <Card className={className} padding="lg">
        <div style={{ textAlign: 'center', color: '#9CA3AF', padding: '20px' }}>
          Loading device information...
        </div>
      </Card>
    );
  }

  if (error || !deviceInfo) {
    return (
      <Card className={className} padding="lg">
        <div style={{ textAlign: 'center', color: '#EF4444', padding: '20px' }}>
          {error || 'Failed to load device information'}
        </div>
      </Card>
    );
  }

  const infoItems = [
    { 
      label: 'Device Name', 
      value: (deviceInfo as any).resolvedName || (deviceInfo as any).deviceName,
      source: (deviceInfo as any).resolutionSource,
      icon: <InfoIcon size={12} color="#6B7280" />
    },
    { 
      label: 'MAC Address', 
      value: (deviceInfo as any).macAddress, 
      isCode: true,
      icon: <NetworkIcon size={12} color="#6B7280" />
    },
    { 
      label: 'Manufacturer', 
      value: (deviceInfo as any).resolvedVendor || (deviceInfo as any).manufacturer || 'Unknown',
      source: (deviceInfo as any).resolutionSource,
      icon: <InfoIcon size={12} color="#6B7280" />
    },
    { 
      label: 'Device Type', 
      value: (deviceInfo as any).resolvedType || (deviceInfo as any).deviceType,
      icon: <InfoIcon size={12} color="#6B7280" />
    },
    { 
      label: 'IP Address', 
      value: (deviceInfo as any).ipAddress, 
      isCode: true,
      icon: <NetworkIcon size={12} color="#6B7280" />
    },
    { 
      label: 'First Seen', 
      value: (deviceInfo as any).firstSeen ? formatTimestamp((deviceInfo as any).firstSeen, 'full') : 'N/A',
      icon: <ClockIcon size={12} color="#6B7280" />
    },
    { 
      label: 'Last Seen', 
      value: (deviceInfo as any).lastSeen ? formatTimestamp((deviceInfo as any).lastSeen, 'full') : 'N/A',
      icon: <ClockIcon size={12} color="#6B7280" />
    },
    { 
      label: 'Total Sessions', 
      value: (deviceInfo as any).totalSessions ? (deviceInfo as any).totalSessions.toLocaleString() : 'N/A',
      icon: <NetworkIcon size={12} color="#6B7280" />
    },
    { 
      label: 'Total Traffic', 
      value: (deviceInfo as any).totalTraffic,
      icon: <NetworkIcon size={12} color="#6B7280" />
    },
    { 
      label: 'Active Duration', 
      value: (deviceInfo as any).activeDuration,
      icon: <ClockIcon size={12} color="#6B7280" />
    }
  ];

  return (
    <Card className={className} padding="lg">
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: '24px'
      }}>
        <div>
          <h3 style={{
            color: '#fff',
            fontSize: '20px',
            fontWeight: 'bold',
            margin: '0 0 8px 0',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <InfoIcon size={20} color="#3B82F6" />
            Device Information ({timeWindow.toUpperCase()})
          </h3>
          <p style={{
            color: '#9CA3AF',
            fontSize: '14px',
            margin: 0
          }}>
            Basic device details and network information
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <TimeWindowSelector
            selectedWindow={timeWindow}
            onWindowChange={setTimeWindow}
          />
          <StatusIndicator status={(deviceInfo as any).status} size="lg" />
        </div>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
        gap: '20px'
      }}>
        {infoItems.map((item, index) => (
          <div key={index}>
            <div style={{
              color: '#9CA3AF',
              fontSize: '12px',
              fontWeight: 'bold',
              textTransform: 'uppercase',
              marginBottom: '6px',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}>
              {item.icon}
              {item.label}
            </div>
            <div style={{
              color: '#E5E7EB',
              fontSize: '16px',
              fontWeight: item.isCode ? 'normal' : 'bold',
              fontFamily: item.isCode ? 'monospace' : 'inherit',
              backgroundColor: item.isCode ? '#111827' : 'transparent',
              padding: item.isCode ? '6px 10px' : '0',
              borderRadius: item.isCode ? '6px' : '0',
              border: item.isCode ? '1px solid #374151' : 'none'
            }}>
              <div>
                {item.value}
                {item.source === 'vendor_pattern' && (
                  <div style={{
                    fontSize: '11px',
                    color: '#6B7280',
                    marginTop: '2px',
                    fontWeight: 'normal'
                  }}>
                    Resolved via OUI pattern
                  </div>
                )}
                {item.source === 'known_device' && (
                  <div style={{
                    fontSize: '11px',
                    color: '#10B981',
                    marginTop: '2px',
                    fontWeight: 'normal'
                  }}>
                    Known device
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
};

export default DeviceInfoPanel; 
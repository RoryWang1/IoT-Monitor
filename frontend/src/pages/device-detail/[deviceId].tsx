import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import PageLayout from '../../components/layout/PageLayout';
import Breadcrumb from '../../components/layout/Breadcrumb';
import DeviceInfoPanel from '../../components/modules/device/DeviceInfoPanel';
import PortAnalysisPanel from '../../components/modules/analysis/PortAnalysisPanel';
import ProtocolDistributionChart from '../../components/visualizations/ProtocolDistributionChart';
import TrafficTrendChart from '../../components/visualizations/TrafficTrendChart';
import NetworkTopologyChart from '../../components/visualizations/NetworkTopologyChart';
import ActivityTimelineChart from '../../components/visualizations/ActivityTimelineChart';
import { TimezoneDisplay, TimezoneSelector } from '../../components/ui';
import { useTimezone } from '../../hooks/useTimezone';

const DeviceDetail: React.FC = () => {
  const router = useRouter();
  const { deviceId, experimentId } = router.query;
  const [experimentIdState, setExperimentId] = useState<string | null>(null);
  // Use timezone hook to refresh timezone info
  const { timezoneInfo, refreshTimezone } = useTimezone(
    experimentIdState || ''
  );

  // Handle timezone changes with force refresh
  const handleTimezoneChange = async (newTimezone: string) => {
    try {
      console.log('Timezone changed to:', newTimezone);
      
      // Force refresh timezone info across all components
      await refreshTimezone(); // Force refresh to clear cache
      
      // Add a small delay to ensure timezone info propagation
      setTimeout(() => {
        // Force a re-render by updating a local state
        setExperimentId(prev => prev); // Trigger re-render
        
        // Clear any timezone caches in child components
        window.dispatchEvent(new CustomEvent('timezoneChanged', { 
          detail: { newTimezone, experimentId: experimentIdState } 
        }));
      }, 100);
      
      console.log('Timezone change completed, components should refresh');
    } catch (error) {
      console.error('Error handling timezone change:', error);
    }
  };

  useEffect(() => {
    if (router.isReady) {
      const experimentId = router.query.experiment_id as string;
      if (experimentId) {
        setExperimentId(experimentId);
      } else {
        setExperimentId('experiment_1');
      }
    }
  }, [router.isReady, router.query]);

  // Wait for router and required data
  if (router.isFallback || !router.isReady) {
    return (
      <PageLayout
        title="Device Detail"
        subtitle="Loading device information..."
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

  const breadcrumbItems = [
    { label: 'Dashboard', href: '/' },
    { 
      label: `Experiment ${experimentIdState || 'Unknown'}`, 
      href: `/experiment-detail/${experimentIdState}` 
    },
    { label: `Device ${typeof deviceId === 'string' ? deviceId.slice(-6) : 'Unknown'}` }
  ];

  return (
    <PageLayout
      title="Device Detail"
      subtitle={`Device Analysis Dashboard (${experimentIdState || 'Unknown Experiment'}) • ${timezoneInfo?.timezone_display || 'UTC'}`}
      actions={
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <TimezoneDisplay 
            experimentId={experimentIdState || ''} 
            compact={true} 
          />
          <TimezoneSelector 
            experimentId={experimentIdState || ''} 
            onTimezoneChange={handleTimezoneChange}
          />
        </div>
      }
      breadcrumb={<Breadcrumb items={breadcrumbItems} />}
    >
      <div style={{ 
        display: 'flex', 
        flexDirection: 'column', 
        gap: 'var(--spacing-2xl)' 
      }}>
        {/* Device Information Panel - now has its own time window selector */}
        <DeviceInfoPanel 
          deviceId={deviceId as string} 
          experimentId={experimentIdState || null} 
        />

        {/* Port Analysis - has its own time window selector */}
        <PortAnalysisPanel 
          deviceId={deviceId as string} 
          experimentId={experimentIdState || null} 
        />

        {/* Protocol Analysis and Traffic Trend - have their own time window selectors */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 2fr',
          gap: 'var(--spacing-2xl)',
          alignItems: 'start'
        }}>
          <ProtocolDistributionChart 
            deviceId={deviceId as string} 
            experimentId={experimentIdState || null} 
          />
          <TrafficTrendChart 
            deviceId={deviceId as string} 
            experimentId={experimentIdState || null} 
          />
        </div>

        {/* Network Topology - has its own time window selector */}
        <NetworkTopologyChart 
          deviceId={deviceId as string} 
          experimentId={experimentIdState || null} 
        />

        {/* Activity Timeline - has its own time window selector */}
        <ActivityTimelineChart 
          deviceId={deviceId as string} 
          experimentId={experimentIdState || null} 
        />
      </div>
    </PageLayout>
  );
};

export default DeviceDetail; 
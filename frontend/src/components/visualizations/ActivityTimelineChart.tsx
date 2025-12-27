import React, { useState, useMemo } from 'react';
import { useApiData } from '@/hooks/useApiData';
import { useTimezoneAwareApi } from '@/hooks/useTimezoneAwareApi';
import TimeWindowSelector from '@/components/ui/TimeWindowSelector';
import { WS_TOPICS } from '@/config/api';
import { ChartIcon, ClockIcon } from '../ui/icons';

interface ActivityTimelineChartProps {
  deviceId: string;
  experimentId?: string | null;
}

interface ActivityData {
  timestamp: string;
  hour: number;
  minute?: number;
  packets: number;
  sessions: number;
  bytes: number;
  intensity: number;
  pattern?: string;
}

// Helper functions moved outside component to avoid hoisting issues
const getIntensityColor = (intensity: number, maxIntensity: number = 1): string => {
  // Dynamically calculate thresholds based on actual data range
  if (maxIntensity === 0) return '#6B7280'; // Gray for no data
  
  const normalizedIntensity = intensity / maxIntensity;
  
  if (normalizedIntensity >= 0.8) return '#EF4444'; // High - Red
  if (normalizedIntensity >= 0.6) return '#F59E0B'; // Medium-High - Orange  
  if (normalizedIntensity >= 0.4) return '#10B981'; // Medium - Green
  if (normalizedIntensity >= 0.2) return '#3B82F6'; // Low-Medium - Blue
  return '#6B7280'; // Very Low - Gray
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

// Unified data formatting function, keeping 2 decimal places
const formatValue = (value: number, metric: string): string => {
  switch (metric) {
    case 'bytes':
      if (value >= 1024 * 1024 * 1024) return `${(value / (1024 * 1024 * 1024)).toFixed(2)}GB`;
      if (value >= 1024 * 1024) return `${(value / (1024 * 1024)).toFixed(2)}MB`;
      if (value >= 1024) return `${(value / 1024).toFixed(2)}KB`;
      return `${Math.round(value)}B`;
    case 'packets':
      if (value >= 1000000) return `${(value / 1000000).toFixed(2)}M`;
      if (value >= 1000) return `${(value / 1000).toFixed(2)}K`;
      return Math.round(value).toString();
    case 'sessions':
      return Math.round(value).toString();
    default:
      return value.toFixed(2);
  }
};

// Time formatting function (will be used in the timezone-aware version inside the component)

const ActivityTimelineChart: React.FC<ActivityTimelineChartProps> = ({ deviceId, experimentId }) => {
  const [selectedWindow, setSelectedWindow] = React.useState<'auto' | '1h' | '2h' | '6h' | '12h' | '24h' | '48h'>('48h');
  const [selectedMetric, setSelectedMetric] = React.useState<'packets' | 'sessions' | 'bytes'>('packets');
  const [refreshTrigger, setRefreshTrigger] = React.useState(0);

  const { getDeviceActivityTimeline, formatTimestamp, timezoneInfo } = useTimezoneAwareApi({
    experimentId: experimentId || '',
    deviceId
  });

  const { data: rawActivityData, loading, error, refetch } = useApiData({
    fetchFn: () => getDeviceActivityTimeline(deviceId, selectedWindow, experimentId || undefined),
    wsTopics: [WS_TOPICS.DEVICE_ACTIVITY_TIMELINE(deviceId)],
    dependencies: [deviceId, selectedWindow, experimentId, timezoneInfo?.timezone, refreshTrigger],
    timeWindow: selectedWindow,
    enabled: !!deviceId && !!experimentId
  });

  // Listen for timezone change events
  React.useEffect(() => {
    const handleTimezoneChange = (event: CustomEvent) => {
      console.log('ActivityTimelineChart received timezone change event:', event.detail);
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

  const activityData = React.useMemo(() => {
    if (!rawActivityData || !Array.isArray(rawActivityData)) return [];
    return rawActivityData as ActivityData[];
  }, [rawActivityData]);

  // Timezone-aware time formatting function
  const formatTimeDisplay = React.useCallback((item: ActivityData, selectedWindow: string): string => {
    // If display_timestamp is provided by the backend, use it
    if ((item as any).display_timestamp) {
      return (item as any).display_timestamp;
    }
    
    // If timestamp is already in "HH:MM" format, use it directly
    if (typeof item.timestamp === 'string' && /^\d{2}:\d{2}$/.test(item.timestamp)) {
      return item.timestamp;
    }
    
    // Use timezone-aware formatting
    const formatted = formatTimestamp(item.timestamp, 'short');
    
    // For detailed windows, show minutes; for broader windows, show only hours
    if (selectedWindow === '1h' || selectedWindow === '6h') {
      return formatted; // HH:MM format
    }
    
    // Extract hour part for broader windows
    return formatted.split(':')[0] + ':00';
  }, [formatTimestamp]);

  // Helper function to generate period labels based on time window with timezone awareness
  const getPeriodLabel = React.useCallback((periodIndex: number, timeWindow: string, timezoneInfo: any): { label: string, startTime: Date, endTime: Date, dateIndicator?: string } => {
    const windowMinutes = {
      '1h': 60,
      '2h': 120,
      '6h': 360, 
      '12h': 720,
      '24h': 1440,
      '48h': 2880
    };
    
    // For auto mode, use special handling
    if (timeWindow === 'auto') {
      // Use a reasonable default for auto mode period calculation
      const totalMinutes = 1440; // 24h as base
      const minutesPerPeriod = totalMinutes / 12;
      
      // Calculate absolute time boundaries using REAL timezone-aware current time
      let currentTime: Date;
      if (timezoneInfo && timezoneInfo.current_time) {
        // Parse ISO string with timezone info to get the REAL timezone time
        const isoString = timezoneInfo.current_time;
        // Extract time components from ISO string manually to preserve timezone
        const isoMatch = isoString.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})/);
        if (isoMatch) {
          const [, year, month, day, hour, minute, second] = isoMatch;
          currentTime = new Date(parseInt(year), parseInt(month) - 1, parseInt(day), parseInt(hour), parseInt(minute), parseInt(second));
        } else {
          // Fallback
          currentTime = new Date(timezoneInfo.current_time);
        }
      } else {
        currentTime = new Date();
      }
      
      // Calculate the absolute start and end time for this period
      const windowStartTime = new Date(currentTime.getTime() - totalMinutes * 60 * 1000);
      const periodStartTime = new Date(windowStartTime.getTime() + periodIndex * minutesPerPeriod * 60 * 1000);
      const periodEndTime = new Date(windowStartTime.getTime() + (periodIndex + 1) * minutesPerPeriod * 60 * 1000);
      
      // Format times using timezone-aware formatTimestamp function
      const formatTime = (date: Date): string => {
        // Use timezone-aware formatting with 'short' format (HH:MM)
        return formatTimestamp(date.toISOString(), 'short');
      };
      
      const startTimeStr = formatTime(periodStartTime);
      const endTimeStr = formatTime(periodEndTime);
      
      const label = `${startTimeStr}-${endTimeStr}`;
      
      return {
        label,
        startTime: periodStartTime,
        endTime: periodEndTime
      };
    }
    
    // Regular time window processing
    const totalMinutes = windowMinutes[timeWindow as keyof typeof windowMinutes] || 1440;
    const minutesPerPeriod = totalMinutes / 12;
    
    // Calculate absolute time boundaries using REAL timezone-aware current time
    let currentTime: Date;
    if (timezoneInfo && timezoneInfo.current_time) {
      // Parse ISO string with timezone info to get the REAL timezone time
      const isoString = timezoneInfo.current_time;
      // Extract time components from ISO string manually to preserve timezone
      const isoMatch = isoString.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})/);
      if (isoMatch) {
        const [, year, month, day, hour, minute, second] = isoMatch;
        currentTime = new Date(parseInt(year), parseInt(month) - 1, parseInt(day), parseInt(hour), parseInt(minute), parseInt(second));
      } else {
        // Fallback
        currentTime = new Date(timezoneInfo.current_time);
      }
    } else {
      currentTime = new Date();
    }
    
    // Calculate the absolute start and end time for this period
    const windowStartTime = new Date(currentTime.getTime() - totalMinutes * 60 * 1000);
    const periodStartTime = new Date(windowStartTime.getTime() + periodIndex * minutesPerPeriod * 60 * 1000);
    const periodEndTime = new Date(windowStartTime.getTime() + (periodIndex + 1) * minutesPerPeriod * 60 * 1000);
    
    // Format times using timezone-aware formatTimestamp function
    const formatTime = (date: Date): string => {
      // Use timezone-aware formatting with 'short' format (HH:MM)
      return formatTimestamp(date.toISOString(), 'short');
    };
    
    // Date indicator logic for cross-day periods (timezone-aware)
    let dateIndicator: string | undefined = undefined;
    
    // Use timezone-aware date calculations with manual date comparison
    const currentDate = new Date(currentTime);
    const periodDate = new Date(periodStartTime);
    
    // Get normalized dates for comparison (timezone-aware)
    const currentDayStart = new Date(currentDate.getFullYear(), currentDate.getMonth(), currentDate.getDate());
    const periodDayStart = new Date(periodDate.getFullYear(), periodDate.getMonth(), periodDate.getDate());
    
    const daysDiff = Math.round((currentDayStart.getTime() - periodDayStart.getTime()) / (24 * 60 * 60 * 1000));
    
    // Check if this period is on a different day than current time
    const isCurrentDay = daysDiff === 0;
    
    if (isCurrentDay) {
      // Check if this is the FIRST period of today
      let shouldShowTodayIndicator = false;
      if (periodIndex === 0) {
        shouldShowTodayIndicator = true;
      } else {
        // Check if the previous period was on a different day
        const prevPeriodTime = new Date(windowStartTime.getTime() + (periodIndex - 1) * minutesPerPeriod * 60 * 1000);
        const prevPeriodDayStart = new Date(prevPeriodTime.getFullYear(), prevPeriodTime.getMonth(), prevPeriodTime.getDate());
        const isPrevPeriodDifferentDay = periodDayStart.getTime() !== prevPeriodDayStart.getTime();
        if (isPrevPeriodDifferentDay) {
          shouldShowTodayIndicator = true;
        }
      }
      if (shouldShowTodayIndicator) {
        dateIndicator = 'Today';
      }
    } else if (daysDiff > 0) {
      // Check if this is the FIRST period of this specific day (scanning from left to right)
      let shouldShowIndicator = false;
      
      if (periodIndex === 0) {
        // Always show indicator for the first period if it's not current day
        shouldShowIndicator = true;
      } else {
        // Check if the previous period was on a different day than this period
        const prevPeriodTime = new Date(windowStartTime.getTime() + (periodIndex - 1) * minutesPerPeriod * 60 * 1000);
        const prevPeriodDayStart = new Date(prevPeriodTime.getFullYear(), prevPeriodTime.getMonth(), prevPeriodTime.getDate());
        
        const isPrevPeriodDifferentDay = periodDayStart.getTime() !== prevPeriodDayStart.getTime();
        
        if (isPrevPeriodDifferentDay) {
          shouldShowIndicator = true;
        }
      }
      
      if (shouldShowIndicator) {
        if (daysDiff === 1) {
          dateIndicator = 'Yesterday';
        } else if (daysDiff === 2) {
          dateIndicator = '2 days ago';
        } else if (daysDiff > 2) {
          // For older dates, show the actual date (MM/DD format)
          const month = (periodDate.getMonth() + 1).toString().padStart(2, '0');
          const day = periodDate.getDate().toString().padStart(2, '0');
          dateIndicator = `${month}/${day}`; // MM/DD
        }
      }
    }
    
    const startTimeStr = formatTime(periodStartTime);
    const endTimeStr = formatTime(periodEndTime);
    
    let label: string;
    
    // For all time windows, show actual time ranges
    if (timeWindow === '1h') {
      // For 1h window: show 5-minute intervals with actual times (e.g., "18:00-18:05")
      label = `${startTimeStr}-${endTimeStr}`;
    } else if (timeWindow === '2h') {
      // For 2h window: show 10-minute intervals with actual times (e.g., "18:00-18:10")
      label = `${startTimeStr}-${endTimeStr}`;
    } else if (timeWindow === '6h') {
      // For 6h window: show 30-minute intervals with actual times (e.g., "18:00-18:30")
      label = `${startTimeStr}-${endTimeStr}`;
    } else if (timeWindow === '12h') {
      // For 12h window: show 1-hour intervals with actual times (e.g., "18:00-19:00")
      label = `${startTimeStr}-${endTimeStr}`;
    } else if (timeWindow === '24h') {
      // For 24h window: show 2-hour intervals with actual times (e.g., "17:00-19:00")
      label = `${startTimeStr}-${endTimeStr}`;
    } else if (timeWindow === '48h') {
      // For 48h window: show 4-hour intervals with actual times (e.g., "15:06-19:06")
      label = `${startTimeStr}-${endTimeStr}`;
    } else if (timeWindow === 'auto') {
      // For auto mode: show 2-hour intervals with actual times
      label = `${startTimeStr}-${endTimeStr}`;
    } else {
      // Fallback
      label = `${startTimeStr}-${endTimeStr}`;
    }
    
    return {
      label,
      startTime: periodStartTime,
      endTime: periodEndTime,
      dateIndicator
    };
  }, [formatTimestamp]);

  // Process activity data into 12 time periods with dynamic intensity calculation
  const processedData = React.useMemo(() => {
    if (!activityData || activityData.length === 0) {
      return [];
    }

    // Group data into 12 periods based on selected time window
    const periods = 12;
    const processedPeriods: any[] = [];
    
    // For auto mode, don't filter by time window - include all data
    if (selectedWindow === 'auto') {
      // For auto mode, create periods based on data distribution
      // Calculate time window boundaries from actual data
      const dataTimestamps = activityData.map(item => {
        if (typeof item.timestamp === 'string') {
          return new Date(item.timestamp);
        }
        return new Date();
      }).sort((a, b) => a.getTime() - b.getTime());
      
      if (dataTimestamps.length === 0) {
        return [];
      }
      
      const dataStartTime = dataTimestamps[0];
      const dataEndTime = dataTimestamps[dataTimestamps.length - 1];
      const dataDuration = dataEndTime.getTime() - dataStartTime.getTime();
      const periodDuration = dataDuration / periods;
      
      // First pass: collect all period data without colors
      const tempPeriods: any[] = [];
      let maxPeriodValue = 0;
      
      for (let i = 0; i < periods; i++) {
        const periodStartTime = new Date(dataStartTime.getTime() + i * periodDuration);
        const periodEndTime = new Date(dataStartTime.getTime() + (i + 1) * periodDuration);
        
        const periodData = activityData.filter(item => {
          try {
            let itemTimestamp: Date;
            
            if (typeof item.timestamp === 'string') {
              itemTimestamp = new Date(item.timestamp);
            } else {
              const hour = item.hour || 0;
              const minute = item.minute || 0;
              
              const baseTime = new Date();
              itemTimestamp = new Date(baseTime);
              itemTimestamp.setHours(hour, minute, 0, 0);
            }
            
            return itemTimestamp >= periodStartTime && itemTimestamp < periodEndTime;
          } catch (error) {
            console.warn('Error processing activity data timestamp:', error);
            return false;
          }
        });
        
        // Calculate period metrics
        const periodPackets = periodData.reduce((sum, item) => sum + (item.packets || 0), 0);
        const periodSessions = periodData.reduce((sum, item) => sum + (item.sessions || 0), 0);
        const periodBytes = periodData.reduce((sum, item) => sum + (item.bytes || 0), 0);
        
        const periodValue = periodPackets + periodSessions + periodBytes;
        maxPeriodValue = Math.max(maxPeriodValue, periodValue);
        
        tempPeriods.push({
          period: i,
          packets: periodPackets,
          sessions: periodSessions,
          bytes: periodBytes,
          value: periodValue,
          startTime: periodStartTime,
          endTime: periodEndTime
        });
      }
      
      // Second pass: assign colors and labels
      for (let i = 0; i < periods; i++) {
        const period = tempPeriods[i];
        const intensity = maxPeriodValue > 0 ? (period.value / maxPeriodValue) : 0;
        
        // Generate period label for auto mode
        const startTimeStr = formatTimestamp(period.startTime.toISOString(), 'short');
        const endTimeStr = formatTimestamp(period.endTime.toISOString(), 'short');
        
        processedPeriods.push({
          ...period,
          label: `${startTimeStr}-${endTimeStr}`,
          intensity: intensity,
          color: `hsl(220, 70%, ${Math.max(90 - intensity * 40, 20)}%)`,
          borderColor: `hsl(220, 70%, ${Math.max(70 - intensity * 30, 10)}%)`
        });
      }
      
      return processedPeriods;
    }
    
    // Regular time window processing
    const windowMinutes = {
      '1h': 60,
      '2h': 120,
      '6h': 360,
      '12h': 720,
      '24h': 1440,
      '48h': 2880
    };
    
    const totalMinutes = windowMinutes[selectedWindow as keyof typeof windowMinutes] || 1440;
    const minutesPerPeriod = totalMinutes / periods;
    
    // First pass: collect all period data without colors
    const tempPeriods: any[] = [];
    let maxPeriodValue = 0;
    
    for (let i = 0; i < periods; i++) {
      const periodLabel = getPeriodLabel(i, selectedWindow, timezoneInfo);
      
      const periodData = activityData.filter(item => {
        // timezone-aware data interpretation
        try {
          let itemTimestamp: Date;
          
          // Parse the activity data timestamp  
          if (typeof item.timestamp === 'string') {
            // Reinterpret the timestamp in the current experiment timezone
            // The key insight: same UTC timestamp should be interpreted differently in different timezones
            const utcTimestamp = new Date(item.timestamp);
            
            // Get current experiment timezone
            const currentTimezone = timezoneInfo?.timezone || 'Europe/London';
            
            // Convert UTC timestamp to experiment timezone for proper comparison
            // This ensures that data positioning changes when timezone changes
            itemTimestamp = new Date(utcTimestamp.toLocaleString('en-US', { 
              timeZone: currentTimezone 
            }));
            
          } else {
            // Fallback: construct from hour/minute if available
            const hour = item.hour || 0;
            const minute = item.minute || 0;
            
            // Use current experiment time as base and adjust
            const baseTime = timezoneInfo && timezoneInfo.current_time ? 
              new Date(timezoneInfo.current_time) : new Date();
            itemTimestamp = new Date(baseTime);
            itemTimestamp.setHours(hour, minute, 0, 0);
          }
          
          // Check if item timestamp falls within this period's absolute time boundaries
          return itemTimestamp >= periodLabel.startTime && itemTimestamp < periodLabel.endTime;
          
        } catch (error) {
          console.warn('Error processing activity data timestamp:', error);
          return false;
        }
      });
      
      // Calculate period metrics
      const periodPackets = periodData.reduce((sum, item) => sum + (item.packets || 0), 0);
      const periodSessions = periodData.reduce((sum, item) => sum + (item.sessions || 0), 0);
      const periodBytes = periodData.reduce((sum, item) => sum + (item.bytes || 0), 0);
      
      const periodValue = periodPackets + periodSessions + periodBytes;
      maxPeriodValue = Math.max(maxPeriodValue, periodValue);
      
      tempPeriods.push({
        period: i,
        packets: periodPackets,
        sessions: periodSessions,
        bytes: periodBytes,
        value: periodValue,
        label: periodLabel.label,
        startTime: periodLabel.startTime,
        endTime: periodLabel.endTime,
        dateIndicator: periodLabel.dateIndicator
      });
    }
    
    // Second pass: assign colors based on intensity
    for (let i = 0; i < periods; i++) {
      const period = tempPeriods[i];
      const intensity = maxPeriodValue > 0 ? (period.value / maxPeriodValue) : 0;
      
      processedPeriods.push({
        ...period,
        intensity: intensity,
        color: `hsl(220, 70%, ${Math.max(90 - intensity * 40, 20)}%)`,
        borderColor: `hsl(220, 70%, ${Math.max(70 - intensity * 30, 10)}%)`
      });
    }
    
    return processedPeriods;
  }, [activityData, selectedWindow, timezoneInfo, formatTimestamp, getPeriodLabel]);

  const maxValue = React.useMemo(() => {
    if (processedData.length === 0) return 1;
    return Math.max(...processedData.map(d => d.value || 0));
  }, [processedData]);

  const getTimeRangeLabel = (): string => {
    if (!processedData.length) return '';
    return `${selectedWindow.toUpperCase()} Time Window (12 Periods)`;
  };

  const getMetricLabel = (): string => {
    switch (selectedMetric) {
      case 'packets': return 'Packets';
      case 'sessions': return 'Sessions';
      case 'bytes': return 'Bytes';
      default: return 'Activity';
    }
  };

  if (loading && !rawActivityData) {
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
          minHeight: '300px',
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
            Loading activity timeline data...
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
          Error loading activity timeline: {error}
        </div>
      </div>
    );
  }

  // Show "No Data" message when API returns empty data
  if (!activityData || activityData.length === 0 || processedData.length === 0) {
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
              margin: '0 0 var(--spacing-xs) 0'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ClockIcon size={18} color="#3B82F6" />
              Activity Timeline ({selectedWindow.toUpperCase()})
            </div>
            </h3>
            <p className="text-responsive-sm" style={{
              color: 'var(--color-text-secondary)',
              margin: 0
            }}>
              Network activity analysis over time
            </p>
          </div>

          <TimeWindowSelector
            selectedWindow={selectedWindow}
            onWindowChange={(window) => setSelectedWindow(window as typeof selectedWindow)}
            size="sm"
          />
        </div>

        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '200px',
          color: 'var(--color-text-secondary)',
          textAlign: 'center'
        }}>
          <div style={{
            fontSize: '48px',
            marginBottom: 'var(--spacing-md)',
            opacity: 0.3
          }}>
                              <ChartIcon size={20} color="#64748B" />
          </div>
          <div className="text-responsive-lg" style={{
            color: 'var(--color-text-secondary)',
            fontWeight: '600',
            marginBottom: 'var(--spacing-sm)'
          }}>
            No Activity Data Available
          </div>
          <div className="text-responsive-sm" style={{
            color: 'var(--color-text-secondary)',
            maxWidth: '400px'
          }}>
            No activity timeline data found for the selected {selectedWindow} time window. 
            This may be because the data is outside the current time range or no network activity was recorded.
          </div>
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
            margin: '0 0 var(--spacing-xs) 0'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ClockIcon size={18} color="#3B82F6" />
              Activity Timeline - {getMetricLabel()} ({selectedWindow.toUpperCase()})
            </div>
          </h3>
          <p className="text-responsive-sm" style={{
            color: 'var(--color-text-secondary)',
            margin: 0
          }}>
            Each cell shows {selectedMetric} activity for a time window
          </p>
        </div>

        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--spacing-sm)',
          alignItems: 'flex-end'
        }}>
          <TimeWindowSelector
            selectedWindow={selectedWindow}
            onWindowChange={(window) => setSelectedWindow(window as typeof selectedWindow)}
            size="sm"
          />
          
          {/* Metric Selector */}
          <div style={{
            display: 'flex',
            gap: 'var(--spacing-xs)',
            backgroundColor: 'var(--color-bg-secondary)',
            padding: 'var(--spacing-xs)',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--color-border-primary)'
          }}>
            {(['packets', 'sessions', 'bytes'] as const).filter(metric => 
              processedData.some(item => typeof item[metric] === 'number' && item[metric] > 0)
            ).map((metric) => (
              <button
                key={metric}
                onClick={() => setSelectedMetric(metric)}
                className="text-xs px-2 py-1"
                style={{
                  backgroundColor: selectedMetric === metric 
                    ? 'var(--color-accent-blue)' 
                    : 'transparent',
                  color: selectedMetric === metric 
                    ? 'var(--color-text-primary)' 
                    : 'var(--color-text-secondary)',
                  border: 'none',
                  borderRadius: 'var(--radius-sm)',
                  fontWeight: selectedMetric === metric ? '600' : '500',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  textTransform: 'capitalize'
                }}
              >
                {metric}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Timeline Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: processedData.length <= 12 
          ? `repeat(${Math.min(processedData.length, 12)}, 1fr)`
          : 'repeat(auto-fit, minmax(80px, 1fr))',
        gap: 'var(--spacing-xs)',
        marginBottom: 'var(--spacing-lg)'
      }}>
        {processedData.map((item, index) => (
          <div key={index} style={{ position: 'relative' }}>
            {/* Date indicator above the cell - no longer blocks time */}
            {(item as any).dateIndicator && (
              <div style={{
                position: 'absolute',
                top: '-20px',
                left: '50%',
                transform: 'translateX(-50%)',
                fontSize: '10px',
                color: '#FFFFFF',
                backgroundColor: (item as any).dateIndicator === 'Today' ? '#10B981' :
                                (item as any).dateIndicator === 'Yesterday' ? '#3B82F6' : 
                                (item as any).dateIndicator === '2 days ago' ? '#8B5CF6' : '#6B7280',
                padding: '3px 6px',
                borderRadius: '4px',
                fontWeight: '600',
                lineHeight: '1.2',
                textShadow: '0 1px 2px rgba(0, 0, 0, 0.8)',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                boxShadow: '0 2px 4px rgba(0, 0, 0, 0.3)',
                zIndex: 20,
                whiteSpace: 'nowrap'
              }}>
                {(item as any).dateIndicator}
              </div>
            )}
            
            <div
              style={{
                backgroundColor: item.color,
                borderRadius: 'var(--radius-sm)',
                padding: 'var(--spacing-sm)',
                textAlign: 'center',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                border: `1px solid ${item.borderColor}`,
                opacity: item.value > 0
                  ? Math.min(1, Math.max(0.3, (item.value / maxValue) * 0.7 + 0.3))
                  : 0.2,
                position: 'relative'
              }}
              title={`${item.label}: ${formatValue(item.value, selectedMetric)} ${selectedMetric} (${item.value > 0 ? getIntensityColor(item.intensity, 1) : 'No Data'})`}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'scale(1.05)';
                e.currentTarget.style.zIndex = '10';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'scale(1)';
                e.currentTarget.style.zIndex = '1';
              }}
            >
              <div className="text-responsive-xs" style={{
                color: 'var(--color-text-primary)',
                fontWeight: '600',
                marginBottom: 'var(--spacing-xs)'
              }}>
                {item.label}
              </div>
              <div className="text-responsive-sm" style={{
                color: 'var(--color-text-primary)',
                fontWeight: '700'
              }}>
                {formatValue(item.value, selectedMetric)}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Metric Statistics */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
        gap: 'var(--spacing-sm)',
        marginBottom: 'var(--spacing-md)',
        padding: 'var(--spacing-sm)',
        backgroundColor: 'var(--color-bg-secondary)',
        borderRadius: 'var(--radius-md)',
        border: '1px solid var(--color-border-primary)'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div className="text-responsive-xs" style={{ color: 'var(--color-text-secondary)' }}>
            Total {getMetricLabel()}
          </div>
          <div className="text-responsive-sm" style={{ 
            color: 'var(--color-text-primary)', 
            fontWeight: '700',
            fontFamily: 'monospace'
          }}>
            {formatValue(processedData.reduce((sum, item) => sum + item.value, 0), selectedMetric)}
          </div>
        </div>
        
        <div style={{ textAlign: 'center' }}>
          <div className="text-responsive-xs" style={{ color: 'var(--color-text-secondary)' }}>
            Average {getMetricLabel()}
          </div>
          <div className="text-responsive-sm" style={{ 
            color: 'var(--color-text-primary)', 
            fontWeight: '700',
            fontFamily: 'monospace'
          }}>
            {formatValue(processedData.length > 0 ? 
              processedData.reduce((sum, item) => sum + item.value, 0) / processedData.length : 0, 
              selectedMetric)}
          </div>
        </div>
        
        <div style={{ textAlign: 'center' }}>
          <div className="text-responsive-xs" style={{ color: 'var(--color-text-secondary)' }}>
            Peak {getMetricLabel()}
          </div>
          <div className="text-responsive-sm" style={{ 
            color: 'var(--color-accent-blue)', 
            fontWeight: '700',
            fontFamily: 'monospace'
          }}>
            {formatValue(maxValue, selectedMetric)}
          </div>
        </div>
        
        <div style={{ textAlign: 'center' }}>
          <div className="text-responsive-xs" style={{ color: 'var(--color-text-secondary)' }}>
            Data Points
          </div>
          <div className="text-responsive-sm" style={{ 
            color: 'var(--color-text-primary)', 
            fontWeight: '700',
            fontFamily: 'monospace'
          }}>
            {processedData.length}
          </div>
        </div>
      </div>

      {/* Live Data Indicator */}
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        marginBottom: 'var(--spacing-md)'
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--spacing-xs)',
          backgroundColor: 'var(--color-bg-secondary)',
          padding: 'var(--spacing-sm) var(--spacing-md)',
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
            Real-time {selectedMetric} analysis - {getTimeRangeLabel()} (Last {selectedWindow.toUpperCase()})
          </span>
        </div>
      </div>

      {/* Activity Legend */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: 'var(--spacing-md)'
      }}>
        <div>
          <span className="text-responsive-xs" style={{
            color: 'var(--color-text-secondary)',
            marginRight: 'var(--spacing-md)'
          }}>
            Low Activity
          </span>
          <div style={{
            display: 'inline-flex',
            gap: 'var(--spacing-xs)'
          }}>
            {Array.from({ length: 5 }, (_, index) => {
              const relativeIntensity = ((index + 1) / 5) * maxValue;
              return (
                <div
                  key={index}
                  style={{
                    width: '16px',
                    height: '16px',
                    backgroundColor: getIntensityColor(relativeIntensity, maxValue),
                    borderRadius: 'var(--radius-sm)',
                    opacity: Math.min(1, Math.max(0.3, ((index + 1) / 5) * 0.7 + 0.3))
                  }}
                />
              );
            })}
          </div>
          <span className="text-responsive-xs" style={{
            color: 'var(--color-text-secondary)',
            marginLeft: 'var(--spacing-md)'
          }}>
            High Activity
          </span>
        </div>

        <div className="text-responsive-xs" style={{
          color: 'var(--color-text-secondary)'
        }}>
          Intensity Scale: Low → High Activity
        </div>
      </div>
    </div>
  );
};

export default ActivityTimelineChart; 
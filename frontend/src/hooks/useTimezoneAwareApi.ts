import { useCallback } from 'react';
import { useTimezone, useTimezoneTimeWindows } from './useTimezone';
import { apiClient } from '../services/apiClient';

interface TimezoneAwareApiOptions {
  experimentId: string;
  deviceId?: string;
}

/**
 * Hook that provides timezone-aware API calls
 * Automatically applies experiment timezone to time windows and filters
 */
export const useTimezoneAwareApi = ({ experimentId, deviceId }: TimezoneAwareApiOptions) => {
  const { timezoneInfo, formatTimestamp, convertToExperimentTime } = useTimezone(experimentId);
  const { getTimeWindowBounds, getCurrentExperimentTime } = useTimezoneTimeWindows(experimentId);

  // Get current time bounds in experiment timezone
  const getTimezoneAwareTimeWindow = useCallback((window: string) => {
    const bounds = getTimeWindowBounds(window);
    if (!bounds) return null;

    return {
      start: bounds.start.toISOString(),
      end: bounds.end.toISOString(),
      startDisplay: formatTimestamp(bounds.start, 'full'),
      endDisplay: formatTimestamp(bounds.end, 'full')
    };
  }, [getTimeWindowBounds, formatTimestamp]);

  // Sankey Network Flow with timezone awareness
  const getNetworkFlowSankey = useCallback(async (
    flowType: string, 
    timeWindow: string, 
    groupBy: string = 'device_type',
    experimentIdParam?: string
  ) => {
    const expId = experimentIdParam || experimentId;
    
    if (!expId) {
      throw new Error('Experiment ID is required');
    }

    // Get timezone-aware time bounds for real-time windows
    const timeInfo = getTimezoneAwareTimeWindow(timeWindow);

    // Build URL parameters
    const params = new URLSearchParams({
      flow_type: flowType,
      time_window: timeWindow,
      group_by: groupBy
    });

    // Call API with timezone awareness using the proper API client method
    const data = await apiClient.getExperimentNetworkFlowSankey(
      expId,
      flowType,
      timeWindow,
      groupBy
    );
    
    // Post-process data to include timezone information
    if (data && typeof data === 'object') {
      return {
        ...data,
        timezone_info: {
          timezone: timezoneInfo?.timezone,
          timezone_display: timezoneInfo?.timezone_display,
          utc_offset: timezoneInfo?.utc_offset,
          time_bounds: timeInfo
        }
      };
    }
    
    return data;
  }, [experimentId, getTimezoneAwareTimeWindow, timezoneInfo?.timezone, timezoneInfo?.timezone_display, timezoneInfo?.utc_offset]);

  // Traffic Trend with timezone awareness
  const getDeviceTrafficTrend = useCallback(async (deviceIdParam: string, timeWindow: string, experimentIdParam?: string) => {
    const expId = experimentIdParam || experimentId;
    const devId = deviceIdParam || deviceId;
    
    if (!devId || !expId) {
      throw new Error('Device ID and Experiment ID are required');
    }

    // Get timezone-aware time bounds for real-time windows
    if (timeWindow !== 'auto') {
      const timeInfo = getTimezoneAwareTimeWindow(timeWindow);
    }

    // Call API with experiment ID for timezone-aware filtering
    const data = await apiClient.getDeviceTrafficTrend(devId, timeWindow, expId);
    
    // Post-process data to ensure timezone consistency
    if (Array.isArray(data)) {
      return data.map(item => ({
        ...item,
        // Add timezone-aware display timestamps if not provided by backend
        display_timestamp: item.display_timestamp || formatTimestamp(item.timestamp, 'chart'),
        short_timestamp: item.short_timestamp || formatTimestamp(item.timestamp, 'short'),
        full_timestamp: item.full_timestamp || formatTimestamp(item.timestamp, 'full'),
        timezone_info: {
          timezone: timezoneInfo?.timezone,
          timezone_display: timezoneInfo?.timezone_display,
          utc_offset: timezoneInfo?.utc_offset
        }
      }));
    }

    return data;
  }, [experimentId, deviceId, getTimezoneAwareTimeWindow, formatTimestamp, timezoneInfo?.timezone, timezoneInfo?.timezone_display, timezoneInfo?.utc_offset]);

  // Device Detail with timezone awareness
  const getDeviceDetail = useCallback(async (deviceIdParam: string, experimentIdParam?: string, timeWindow: string = '24h') => {
    const expId = experimentIdParam || experimentId;
    const devId = deviceIdParam || deviceId;
    
    if (!devId || !expId) {
      throw new Error('Device ID and Experiment ID are required');
    }

    const timeInfo = getTimezoneAwareTimeWindow(timeWindow);

    return await apiClient.getDeviceDetail(devId, expId, timeWindow);
  }, [experimentId, deviceId, getTimezoneAwareTimeWindow]);

  // Activity Timeline with timezone awareness
  const getDeviceActivityTimeline = useCallback(async (deviceIdParam: string, timeWindow: string, experimentIdParam?: string) => {
    const expId = experimentIdParam || experimentId;
    const devId = deviceIdParam || deviceId;
    
    if (!devId || !expId) {
      throw new Error('Device ID and Experiment ID are required');
    }

    const timeInfo = getTimezoneAwareTimeWindow(timeWindow);

    const data = await apiClient.getDeviceActivityTimeline(devId, timeWindow, expId);
    
    // Post-process timestamps for timezone consistency
    if (Array.isArray(data)) {
      return data.map(item => ({
        ...item,
        display_timestamp: formatTimestamp(item.timestamp, 'chart'),
        full_timestamp: formatTimestamp(item.timestamp, 'full')
      }));
    }

    return data;
  }, [experimentId, deviceId, getTimezoneAwareTimeWindow, formatTimestamp]);

  // Network Topology with timezone awareness
  const getDeviceNetworkTopology = useCallback(async (deviceIdParam: string, timeWindow: string, experimentIdParam?: string) => {
    const expId = experimentIdParam || experimentId;
    const devId = deviceIdParam || deviceId;
    
    if (!devId || !expId) {
      throw new Error('Device ID and Experiment ID are required');
    }

    const timeInfo = getTimezoneAwareTimeWindow(timeWindow);

    return await apiClient.getDeviceNetworkTopology(devId, timeWindow, expId);
  }, [experimentId, deviceId, getTimezoneAwareTimeWindow]);

  // Port Analysis with timezone awareness
  const getDevicePortAnalysis = useCallback(async (deviceIdParam: string, timeWindow: string, experimentIdParam?: string) => {
    const expId = experimentIdParam || experimentId;
    const devId = deviceIdParam || deviceId;
    
    if (!devId || !expId) {
      throw new Error('Device ID and Experiment ID are required');
    }

    const timeInfo = getTimezoneAwareTimeWindow(timeWindow);

    return await apiClient.getDevicePortAnalysis(devId, timeWindow, expId);
  }, [experimentId, deviceId, getTimezoneAwareTimeWindow]);

  // Protocol Distribution with timezone awareness
  const getDeviceProtocolDistribution = useCallback(async (deviceIdParam: string, timeWindow: string, experimentIdParam?: string) => {
    const expId = experimentIdParam || experimentId;
    const devId = deviceIdParam || deviceId;
    
    if (!devId || !expId) {
      throw new Error('Device ID and Experiment ID are required');
    }

    const timeInfo = getTimezoneAwareTimeWindow(timeWindow);

    return await apiClient.getDeviceProtocolDistribution(devId, timeWindow, expId);
  }, [experimentId, deviceId, getTimezoneAwareTimeWindow]);



  return {
    // Timezone information
    timezoneInfo,
    formatTimestamp,
    convertToExperimentTime,
    getCurrentExperimentTime,
    getTimezoneAwareTimeWindow,

    // Timezone-aware API calls
    getNetworkFlowSankey,
    getDeviceTrafficTrend,
    getDeviceDetail,
    getDeviceActivityTimeline,
    getDeviceNetworkTopology,
    getDevicePortAnalysis,
    getDeviceProtocolDistribution
  };
}; 
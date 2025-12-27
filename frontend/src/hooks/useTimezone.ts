import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../services/apiClient';

export interface TimezoneInfo {
  timezone: string;
  timezone_display: string;
  timezone_abbr: string;
  current_time: string;
  current_time_display: string;
  current_time_chart: string;
  utc_offset: string;
  utc_offset_display: string;
  is_dst: boolean;
}

// API response interface (different naming convention)
interface TimezoneApiResponse {
  experimentId: string;
  timezone: string;
  currentTime: string;
  currentTimeDisplay: string;
  utcOffset: string;
  isDst: boolean;
  supportedTimezones: string[];
}

interface UseTimezoneReturn {
  timezoneInfo: TimezoneInfo | null;
  loading: boolean;
  error: string | null;
  updateTimezone: (timezone: string) => Promise<boolean>;
  refreshTimezone: () => Promise<void>;
  convertToExperimentTime: (timestamp: string | Date) => Date | null;
  formatTimestamp: (timestamp: string | Date, format?: 'chart' | 'short' | 'full') => string;
  getCurrentExperimentTime: () => Date | null;
}

// Global timezone cache to avoid redundant API calls
const timezoneCache = new Map<string, { data: TimezoneInfo; timestamp: number }>();
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

// Helper functions to transform API response
const extractTimezoneAbbr = (display: string): string => {
  // Extract abbreviation from "Region | ABBR | Offset" format
  const parts = display.split(' | ');
  return parts[1] || 'UTC';
};

const formatForChart = (isoTime: string): string => {
  // Check undefined/null values
  if (!isoTime || typeof isoTime !== 'string') {
    console.warn('formatForChart received invalid input:', isoTime);
    return 'No Date';
  }

  try {
    // Parse ISO time string manually to preserve original timezone
    // Example input: "2025-06-26T12:09:35.558810-04:00"
    // We want to display: "06/26 12:09" (original timezone time, not browser local time)
    
    const isoMatch = isoTime.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})/);
    if (isoMatch) {
      const [, year, month, day, hour, minute] = isoMatch;
      return `${month}/${day} ${hour}:${minute}`;
    }
    
    // Fallback to previous method if regex fails
    const date = new Date(isoTime);
    if (isNaN(date.getTime())) {
      return 'Invalid Date';
    }
    return date.toLocaleDateString('en-US', { 
      month: '2-digit', 
      day: '2-digit',
      timeZone: 'UTC'
    }) + ' ' + date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: false,
      timeZone: 'UTC'
    });
  } catch (error) {
    console.error('formatForChart ERROR:', error, 'Input:', isoTime);
    return 'Invalid Date';
  }
};

const formatUtcOffset = (offset: string): string => {
  // Convert "+0800" to "+08:00" format
  if (offset.length === 5 && (offset.startsWith('+') || offset.startsWith('-'))) {
    return `${offset.slice(0, 3)}:${offset.slice(3)}`;
  }
  return offset;
};

export const useTimezone = (experimentId: string): UseTimezoneReturn => {
  const [timezoneInfo, setTimezoneInfo] = useState<TimezoneInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadTimezoneInfo = useCallback(async (forceRefresh: boolean = false) => {
    if (!experimentId) return;

    // Only run on client side to avoid SSR issues
    if (typeof window === 'undefined') {
      return;
    }

    // Check cache first (unless force refresh)
    if (!forceRefresh) {
      const cached = timezoneCache.get(experimentId);
      if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
        setTimezoneInfo(cached.data);
        return;
      }
    }

    try {
      setLoading(true);
      const apiResponse = await apiClient.get<TimezoneApiResponse>(`/api/experiments/${experimentId}/timezone`);
      
      // Transform API response to internal format
      const transformedInfo: TimezoneInfo = {
        timezone: apiResponse.timezone,
        timezone_display: apiResponse.currentTimeDisplay, // This contains "Region | ABBR | Offset"
        timezone_abbr: extractTimezoneAbbr(apiResponse.currentTimeDisplay),
        current_time: apiResponse.currentTime,
        current_time_display: formatForChart(apiResponse.currentTime), // Current time formatted for display
        current_time_chart: formatForChart(apiResponse.currentTime),
        utc_offset: apiResponse.utcOffset,
        utc_offset_display: formatUtcOffset(apiResponse.utcOffset),
        is_dst: apiResponse.isDst
      };
      
      // Update cache
      timezoneCache.set(experimentId, { data: transformedInfo, timestamp: Date.now() });
      
      setTimezoneInfo(transformedInfo);
      setError(null);
    } catch (err) {
      console.error('Failed to load timezone info:', err);
      setError('Failed to load timezone');
    } finally {
      setLoading(false);
    }
  }, [experimentId]);

  const updateTimezone = useCallback(async (timezone: string): Promise<boolean> => {
    if (!experimentId) return false;

    // Only run on client side to avoid SSR issues
    if (typeof window === 'undefined') {
      return false;
    }

    try {
      setLoading(true);
      await apiClient.put(`/api/experiments/${experimentId}/timezone`, { timezone });
      
      // Clear ALL timezone cache to force refresh
      timezoneCache.clear();
      
      // Force immediate reload with force refresh flag
      await loadTimezoneInfo(true);
      
      return true;
    } catch (err) {
      console.error('Failed to update timezone:', err);
      setError('Failed to update timezone');
      return false;
    } finally {
      setLoading(false);
    }
  }, [experimentId, loadTimezoneInfo]);

  const convertToExperimentTime = useCallback((timestamp: string | Date): Date | null => {
    if (!timezoneInfo) return null;

    try {
      let date: Date;
      
      if (typeof timestamp === 'string') {
        // Handle ISO string with timezone
        date = new Date(timestamp);
      } else {
        date = timestamp;
      }

      if (isNaN(date.getTime())) return null;

      // If timezone is UTC, return as is
      if (timezoneInfo.timezone === 'UTC') {
        return date;
      }

      // For other timezones, we rely on the backend to provide correct timestamps
      // The API should already return timestamps in the experiment's timezone
      return date;
      
    } catch (error) {
      console.error('Error converting timezone:', error);
      return null;
    }
  }, [timezoneInfo]);

  const formatTimestamp = useCallback((
    timestamp: string | Date, 
    format: 'chart' | 'short' | 'full' = 'chart'
  ): string => {
    try {
      // Use the same ISO parsing logic as formatForChart
      // to ensure consistent timezone handling across all timestamp formatting
      
      let isoString: string;
      if (typeof timestamp === 'string') {
        isoString = timestamp;
      } else {
        isoString = timestamp.toISOString();
      }
      
      // If we have an ISO string with timezone info, parse it directly
      const isoMatch = isoString.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})/);
      if (isoMatch) {
        const [, year, month, day, hour, minute] = isoMatch;
        
        switch (format) {
          case 'short':
            return `${hour}:${minute}`;
          case 'full':
            return `${year}/${month}/${day} ${hour}:${minute}`;
          case 'chart':
          default:
            return `${month}/${day} ${hour}:${minute}`;
        }
      }
      
      // Fallback to the old method for non-ISO strings
      const date = convertToExperimentTime(timestamp);
      if (!date) return 'Invalid Date';

      switch (format) {
        case 'short':
          return date.toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit',
            hour12: false 
          });
          
        case 'full':
          return date.toLocaleDateString('en-US', { 
            year: 'numeric', 
            month: '2-digit', 
            day: '2-digit' 
          }) + ' ' + date.toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit',
            hour12: false 
          });
          
        case 'chart':
        default:
          return date.toLocaleDateString('en-US', { 
            month: '2-digit', 
            day: '2-digit' 
          }) + ' ' + date.toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit',
            hour12: false 
          });
      }
    } catch (error) {
      console.error('formatTimestamp ERROR:', error);
      return 'Format Error';
    }
  }, [convertToExperimentTime]);

  const getCurrentExperimentTime = useCallback((): Date | null => {
    if (!timezoneInfo) return null;
    return convertToExperimentTime(new Date());
  }, [timezoneInfo, convertToExperimentTime]);

  // Load timezone info on mount and when experimentId changes
  useEffect(() => {
    loadTimezoneInfo(false); // Use cache on initial load
  }, [loadTimezoneInfo]);

  const refreshTimezone = useCallback(async () => {
    // Clear cache and force refresh
    timezoneCache.delete(experimentId);
    await loadTimezoneInfo(true);
  }, [experimentId, loadTimezoneInfo]);

  return {
    timezoneInfo,
    loading,
    error,
    updateTimezone,
    refreshTimezone,
    convertToExperimentTime,
    formatTimestamp,
    getCurrentExperimentTime
  };
};

// Utility functions for time window calculations in experiment timezone
export const useTimezoneTimeWindows = (experimentId: string) => {
  const { timezoneInfo, getCurrentExperimentTime } = useTimezone(experimentId);

  const getTimeWindowBounds = useCallback((window: string): { start: Date; end: Date } | null => {
    const now = getCurrentExperimentTime();
    if (!now) return null;

    const timeDeltas = {
      "1h": 1 * 60 * 60 * 1000,
      "2h": 2 * 60 * 60 * 1000,
      "6h": 6 * 60 * 60 * 1000,
      "12h": 12 * 60 * 60 * 1000,
      "24h": 24 * 60 * 60 * 1000,
      "48h": 48 * 60 * 60 * 1000
    };

    const deltaMs = timeDeltas[window as keyof typeof timeDeltas] || timeDeltas["24h"];
    const start = new Date(now.getTime() - deltaMs);

    return { start, end: now };
  }, [getCurrentExperimentTime]);

  const generateTimeLabels = useCallback((window: string, pointCount: number = 6): string[] => {
    const bounds = getTimeWindowBounds(window);
    if (!bounds) return [];

    const { start, end } = bounds;
    const duration = end.getTime() - start.getTime();
    const interval = duration / (pointCount - 1);

    const labels: string[] = [];
    for (let i = 0; i < pointCount; i++) {
      const time = new Date(start.getTime() + i * interval);
      const label = time.toLocaleDateString('en-US', { 
        month: '2-digit', 
        day: '2-digit' 
      }) + ' ' + time.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit',
        hour12: false 
      });
      labels.push(label);
    }

    return labels;
  }, [getTimeWindowBounds]);

  return {
    timezoneInfo,
    getTimeWindowBounds,
    generateTimeLabels,
    getCurrentExperimentTime
  };
}; 
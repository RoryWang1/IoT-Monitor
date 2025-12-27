/**
 * Custom Hook for API Data Fetching and WebSocket Subscriptions
 * Provides unified interface for data loading, error handling, and real-time updates
 */

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import apiClient from '@/services/apiClient';
import { WS_TOPICS, API_ENDPOINTS } from '@/config/api';
import wsClient from '@/services/websocketClient';
import { NetworkTopologyData } from '@/lib/types/iot';

interface UseApiDataOptions<T> {
  fetchFn: () => Promise<T>;
  wsTopics?: string[];
  dependencies?: any[];
  onError?: (error: Error) => void;
  timeWindow?: string;
  enabled?: boolean;
}

interface UseApiDataResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  isUpdating: boolean;
  refetch: (showLoading?: boolean) => Promise<void>;
}

export function useApiData<T>({
  fetchFn,
  wsTopics = [],
  dependencies = [],
  onError,
  timeWindow = '24h',
  enabled = true
}: UseApiDataOptions<T>): UseApiDataResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isInitialLoad, setIsInitialLoad] = useState(true);
  const [isUpdating, setIsUpdating] = useState(false);

  // Memoize wsTopics to prevent unnecessary re-subscriptions
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const memoizedWsTopics = useMemo(() => wsTopics, [wsTopics.join(',')]);
  
  // Stable fetchFn reference with timeWindow dependency
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const stableFetchFn = useCallback(fetchFn, [...dependencies, timeWindow]);

  // Initial data fetch
  useEffect(() => {
    // Only fetch if enabled is true and in client environment
    if (!enabled || typeof window === 'undefined') {
      setLoading(false);
      setData(null);
      setError(null);
      setIsInitialLoad(false);
      return;
    }
    
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const result = await stableFetchFn();
        setData(result);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred';
        
        // Don't set error for validation errors (missing required parameters)
        if (errorMessage.includes('is required')) {
          setLoading(false);
          setIsInitialLoad(false);
          return;
        }
        
        setError(errorMessage);
        
        if (onError) {
          onError(err instanceof Error ? err : new Error(errorMessage));
        }
      } finally {
        setLoading(false);
        setIsInitialLoad(false);
      }
    };

    fetchData();
  }, [stableFetchFn, onError, enabled]);

  const refetch = useCallback(async (showLoading: boolean = true) => {
    // Only refetch in client environment
    if (typeof window === 'undefined') {
      return;
    }

    try {
      if (showLoading) {
        setLoading(true);
      } else {
        setIsUpdating(true);
      }
      setError(null);
      
      const result = await stableFetchFn();
      setData(result);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred';
      setError(errorMessage);
      
      if (onError) {
        onError(err instanceof Error ? err : new Error(errorMessage));
      }
    } finally {
      if (showLoading) {
        setLoading(false);
      } else {
        setIsUpdating(false);
      }
    }
  }, [stableFetchFn, onError]);

  // WebSocket subscriptions - use ref to avoid dependency loop, but keep other functionality working
  const refetchRef = useRef(refetch);
  refetchRef.current = refetch;

  useEffect(() => {
    // Only subscribe to WebSocket in client environment
    if (typeof window === 'undefined' || memoizedWsTopics.length === 0) {
      return;
    }

    const unsubscribeFunctions = memoizedWsTopics.map(topic => 
      wsClient.subscribe(topic, (wsData: any) => {
        // WebSocket update does not show loading, avoid page jitter
        refetchRef.current(false).catch((err: Error) => {
          console.error(`Refetch failed for topic: ${topic}`, err);
        });
      })
    );

    return () => {
      unsubscribeFunctions.forEach(unsubscribe => unsubscribe());
    };
  }, [memoizedWsTopics]); // Remove refetch dependency, use ref

  return {
    data,
    loading,
    error,
    isUpdating,
    refetch
  };
}

/**
 * Hook for Experiments Overview Data
 */
export function useExperimentsOverview() {
  return useApiData({
    fetchFn: () => apiClient.getExperimentsOverview(),
    wsTopics: [WS_TOPICS.EXPERIMENTS_OVERVIEW],
    dependencies: [],
    enabled: true
  });
}

/**
 * Hook for Experiment Detail Data with timezone awareness
 */
export function useExperimentDetail(experimentId: string | string[] | undefined) {
  // Convert experimentId to string and validate
  const validExperimentId = typeof experimentId === 'string' ? experimentId : undefined;
  
  return useApiData({
    fetchFn: () => apiClient.getExperimentDetail(validExperimentId!),
    wsTopics: validExperimentId ? [WS_TOPICS.EXPERIMENT_DETAIL(validExperimentId)] : [],
    dependencies: [validExperimentId], // Removed circular timezone dependency
    enabled: !!validExperimentId
  });
}

/**
 * Hook for Experiment Devices Data
 */
export function useExperimentDevices(experimentId: string | string[] | undefined, limit?: number, offset?: number) {
  // Convert experimentId to string and validate
  const validExperimentId = typeof experimentId === 'string' ? experimentId : undefined;
  
  return useApiData({
    fetchFn: () => apiClient.getExperimentDevices(validExperimentId!, limit, offset),
    wsTopics: validExperimentId ? [WS_TOPICS.EXPERIMENT_DEVICES(validExperimentId)] : [],
    dependencies: [validExperimentId, limit, offset],
    enabled: !!validExperimentId
  });
}

/**
 * Hook for Device Detail Data
 */
export function useDeviceDetail(deviceId: string, experimentId?: string | null, timeWindow: string = '24h', enabled: boolean = true) {
  return useApiData({
    fetchFn: () => apiClient.getDeviceDetail(deviceId, experimentId || undefined, timeWindow),
    wsTopics: [WS_TOPICS.DEVICE_DETAIL(deviceId)],
    dependencies: [deviceId, experimentId, timeWindow],
    timeWindow,
    enabled: enabled && !!deviceId && !!experimentId  // Both deviceId and experimentId are required
  });
}

/**
 * Hook for Device Port Analysis Data
 */
export function useDevicePortAnalysis(deviceId: string, timeWindow: string = '24h', experimentId?: string | null) {
  return useApiData({
    fetchFn: () => apiClient.getDevicePortAnalysis(deviceId, timeWindow, experimentId || undefined),
    wsTopics: [WS_TOPICS.DEVICE_PORT_ANALYSIS(deviceId)],
    dependencies: [deviceId, timeWindow, experimentId],
    timeWindow,
    enabled: !!deviceId && !!experimentId  // Require both deviceId and experimentId
  });
}

/**
 * Hook for Device Protocol Distribution Data
 */
export function useDeviceProtocolDistribution(deviceId: string, timeWindow: string = '1h', experimentId?: string | null) {
  return useApiData({
    fetchFn: () => apiClient.getDeviceProtocolDistribution(deviceId, timeWindow, experimentId || undefined),
    wsTopics: [WS_TOPICS.DEVICE_PROTOCOL_DISTRIBUTION(deviceId)],
    dependencies: [deviceId, timeWindow, experimentId],
    timeWindow,
    enabled: !!deviceId && !!experimentId  // Require both deviceId and experimentId
  });
}

/**
 * Hook for Device Network Topology Data
 */
export function useDeviceNetworkTopology(deviceId: string, timeWindow: string = '24h', experimentId?: string | null) {
  return useApiData<NetworkTopologyData>({
    fetchFn: () => apiClient.getDeviceNetworkTopology(deviceId, timeWindow, experimentId || undefined),
    wsTopics: [WS_TOPICS.DEVICE_NETWORK_TOPOLOGY(deviceId)],
    dependencies: [deviceId, timeWindow, experimentId],
    timeWindow,
    enabled: !!deviceId && !!experimentId  // Require both deviceId and experimentId
  });
}

/**
 * Hook for Device Activity Timeline Data
 */
export function useDeviceActivityTimeline(deviceId: string, timeWindow: string = '24h', experimentId?: string | null) {
  return useApiData({
    fetchFn: () => apiClient.getDeviceActivityTimeline(deviceId, timeWindow, experimentId || undefined),
    wsTopics: [WS_TOPICS.DEVICE_ACTIVITY_TIMELINE(deviceId)],
    dependencies: [deviceId, timeWindow, experimentId],
    timeWindow,
    enabled: !!deviceId && !!experimentId  // Require both deviceId and experimentId
  });
}

/**
 * Hook for Device Traffic Trend Data
 */
export function useDeviceTrafficTrend(deviceId: string, timeWindow: string = '24h', experimentId?: string | null) {
  return useApiData({
    fetchFn: () => apiClient.getDeviceTrafficTrend(deviceId, timeWindow, experimentId || undefined),
    wsTopics: [WS_TOPICS.DEVICE_TRAFFIC_TREND(deviceId)],
    dependencies: [deviceId, timeWindow, experimentId],
    timeWindow,
    enabled: !!deviceId && !!experimentId  // Require both deviceId and experimentId
  });
}



 
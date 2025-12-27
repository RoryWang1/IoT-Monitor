/**
 * API Client Service
 * Handles HTTP requests to the backend API
 */

import { API_BASE_URL, API_ENDPOINTS, REQUEST_CONFIG } from '../config/api';
import { 
  NetworkTopologyData, 
  ExperimentOverviewData, 
  ExperimentDetailData,
  DeviceData,
  PortAnalysisData,
  ProtocolDistributionData,
  TrafficTrendData
} from '../lib/types/iot';

class ApiClient {
  private baseURL: string;
  private timeout: number;

  constructor() {
    this.baseURL = API_BASE_URL;
    this.timeout = REQUEST_CONFIG.timeout;
  }

  /**
   * Make HTTP request with error handling and retries
   */
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    
    // Check if we're in a browser environment
    if (typeof window === 'undefined') {
      throw new Error('API calls are not available during server-side rendering');
    }

    const config: RequestInit = {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    };

    let lastError: Error;
    
    for (let attempt = 1; attempt <= REQUEST_CONFIG.retries; attempt++) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => {
          controller.abort();
        }, this.timeout);

        const response = await fetch(url, {
          ...config,
          signal: controller.signal,
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        return data;
      } catch (error) {
        lastError = error as Error;
        
        // Don't retry on AbortError
        if ((error as Error).name === 'AbortError') {
          throw error;
        }
        
        if (attempt < REQUEST_CONFIG.retries) {
          await new Promise(resolve => 
            setTimeout(resolve, REQUEST_CONFIG.retryDelay * attempt)
          );
        }
      }
    }

    throw lastError!;
  }

  /**
   * GET request
   */
  async get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  /**
   * POST request
   */
  async post<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  /**
   * PUT request
   */
  async put<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  /**
   * DELETE request
   */
  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }

  // Experiments API methods
  async getExperimentsOverview(): Promise<ExperimentOverviewData[]> {
    return this.get<ExperimentOverviewData[]>(API_ENDPOINTS.EXPERIMENTS_OVERVIEW);
  }

  async getExperimentDetail(experimentId: string): Promise<ExperimentDetailData> {
    return this.get<ExperimentDetailData>(API_ENDPOINTS.EXPERIMENT_DETAIL(experimentId));
  }

  async getExperimentDevices(experimentId: string, limit?: number, offset?: number) {
    const params = new URLSearchParams();
    if (limit !== undefined) params.set('limit', limit.toString());
    if (offset !== undefined) params.set('offset', offset.toString());
    const query = params.toString() ? `?${params.toString()}` : '';
    return this.get(`${API_ENDPOINTS.EXPERIMENT_DEVICES(experimentId)}${query}`);
  }

  async getExperimentNetworkFlowSankey(
    experimentId: string, 
    flowType: string, 
    timeWindow: string, 
    groupBy: string = 'device_type'
  ) {
    const params = new URLSearchParams({
      flow_type: flowType,
      time_window: timeWindow,
      group_by: groupBy
    });
    return this.get(`${API_ENDPOINTS.EXPERIMENT_NETWORK_FLOW_SANKEY(experimentId)}?${params.toString()}`);
  }

  // Device API methods
  async getDeviceDetail(deviceId: string, experimentId?: string, timeWindow: string = '24h') {
    const params = new URLSearchParams();
    params.set('time_window', timeWindow);
    if (experimentId) params.set('experiment_id', experimentId);
    return this.get(`${API_ENDPOINTS.DEVICE_DETAIL(deviceId)}?${params.toString()}`);
  }

  async getDevicePortAnalysis(deviceId: string, timeWindow: string = '24h', experimentId?: string) {
    const params = new URLSearchParams();
    params.set('time_window', timeWindow);
    if (experimentId) params.set('experiment_id', experimentId);
    return this.get(`${API_ENDPOINTS.DEVICE_PORT_ANALYSIS(deviceId)}?${params.toString()}`);
  }

  async getDeviceProtocolDistribution(deviceId: string, timeWindow: string = '1h', experimentId?: string) {
    const params = new URLSearchParams();
    params.set('time_window', timeWindow);
    if (experimentId) params.set('experiment_id', experimentId);
    return this.get(`${API_ENDPOINTS.DEVICE_PROTOCOL_DISTRIBUTION(deviceId)}?${params.toString()}`);
  }

  async getDeviceNetworkTopology(deviceId: string, timeWindow: string = '24h', experimentId?: string): Promise<NetworkTopologyData> {
    const params = new URLSearchParams();
    params.set('time_window', timeWindow);
    if (experimentId) params.set('experiment_id', experimentId);
    return this.get<NetworkTopologyData>(`${API_ENDPOINTS.DEVICE_NETWORK_TOPOLOGY(deviceId)}?${params.toString()}`);
  }

  async getDeviceActivityTimeline(deviceId: string, timeWindow: string = '24h', experimentId?: string) {
    const params = new URLSearchParams();
    params.set('time_window', timeWindow);
    if (experimentId) params.set('experiment_id', experimentId);
    return this.get(`${API_ENDPOINTS.DEVICE_ACTIVITY_TIMELINE(deviceId)}?${params.toString()}`);
  }

  async getDeviceTrafficTrend(deviceId: string, timeWindow: string = '24h', experimentId?: string) {
    const params = new URLSearchParams();
    params.set('time_window', timeWindow);
    if (experimentId) params.set('experiment_id', experimentId);
    return this.get(`${API_ENDPOINTS.DEVICE_TRAFFIC_TREND(deviceId)}?${params.toString()}`);
  }



  // System API methods
  async getHealth() {
    return this.get(API_ENDPOINTS.HEALTH);
  }

  async getStatus() {
    return this.get(API_ENDPOINTS.STATUS);
  }
  
  // Test method
  async testConnection() {
    return this.get('/api/test');
  }
}

// Export singleton instance
export const apiClient = new ApiClient();
export default apiClient; 
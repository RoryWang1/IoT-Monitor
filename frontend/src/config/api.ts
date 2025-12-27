/**
 * API Configuration
 * Centralized configuration for backend API connections
 */

// Determine if we're in development or production
const isDevelopment = process.env.NODE_ENV === 'development';
const useFlexibleConfig = process.env.NEXT_PUBLIC_USE_FLEXIBLE_CONFIG === 'true';

// Dynamic IP detection function for client-side
function getClientHostIP(): string {
  if (typeof window !== 'undefined') {
    return window.location.hostname;
  }
  return '127.0.0.1';
}

// For production: use relative paths through Next.js API proxy
// For development: use direct backend URLs
let API_BASE_URL: string;
let WS_BASE_URL: string;

// Initialize URLs based on environment and configuration
if (isDevelopment) {
  // Development mode: use configured backend server or defaults
  const API_BASE_URL_ENV = process.env.NEXT_PUBLIC_API_BASE_URL;
  const WS_BASE_URL_ENV = process.env.NEXT_PUBLIC_WS_BASE_URL;
  const CONFIGURED_HOST = process.env.NEXT_PUBLIC_CONFIGURED_BACKEND_HOST;

  // Check if user configured a specific backend host
  if (CONFIGURED_HOST && CONFIGURED_HOST !== 'auto') {
    console.log(`🎯 使用用户配置的后端服务器: ${CONFIGURED_HOST}`);
  }

  if (!API_BASE_URL_ENV || API_BASE_URL_ENV === 'auto') {
    API_BASE_URL = '/auto'; // Use root-relative path to trigger proxy
  } else {
    API_BASE_URL = API_BASE_URL_ENV;
  }

  WS_BASE_URL = WS_BASE_URL_ENV || 'ws://127.0.0.1:8002';
} else {
  // Production mode: support flexible configuration
  const API_BASE_URL_ENV = process.env.NEXT_PUBLIC_API_BASE_URL;
  const WS_BASE_URL_ENV = process.env.NEXT_PUBLIC_WS_BASE_URL;
  const CONFIGURED_HOST = process.env.NEXT_PUBLIC_CONFIGURED_BACKEND_HOST;
  const API_PORT = process.env.NEXT_PUBLIC_API_PORT || '8001';
  const WS_PORT = process.env.NEXT_PUBLIC_WS_PORT || '8001';

  if (typeof window !== 'undefined') {
    // Browser: In production, API always goes through Next.js proxy to avoid CORS
    // Only WebSocket connects directly to backend
    API_BASE_URL = `${window.location.protocol}//${window.location.host}`;

    // WebSocket configuration: Always use dynamic detection in flexible mode
    if (useFlexibleConfig) {
      // Dynamic configuration: detect current host IP for WebSocket
      const currentHost = getClientHostIP();
      WS_BASE_URL = `ws://${currentHost}:${WS_PORT}`;
      console.log(`Dynamic IP configuration: API=${API_BASE_URL} (proxy), WebSocket=${WS_BASE_URL}`);
    } else {
      // Fixed configuration for WebSocket
      if (WS_BASE_URL_ENV && WS_BASE_URL_ENV !== 'auto') {
        WS_BASE_URL = WS_BASE_URL_ENV;
      } else {
        WS_BASE_URL = `ws://${window.location.hostname}:${WS_PORT}`;
      }
      console.log(` API=${API_BASE_URL} (proxy), WebSocket=${WS_BASE_URL}`);
    }
  } else {
    // Server-side: use environment variables or localhost fallback
    API_BASE_URL = (API_BASE_URL_ENV && API_BASE_URL_ENV !== 'auto') ? API_BASE_URL_ENV : `http://127.0.0.1:${API_PORT}`;
    WS_BASE_URL = (WS_BASE_URL_ENV && WS_BASE_URL_ENV !== 'auto') ? WS_BASE_URL_ENV : `ws://127.0.0.1:${WS_PORT}`;
  }
}

export { API_BASE_URL, WS_BASE_URL };

// Debug logging for development
if (isDevelopment && typeof window !== 'undefined') {
  console.log('API Configuration:', { API_BASE_URL, WS_BASE_URL, isDevelopment });
}

// Production logging for WebSocket configuration
if (!isDevelopment && typeof window !== 'undefined') {
  console.log('Production API Configuration:', {
    API_BASE_URL,
    WS_BASE_URL,
    useFlexibleConfig,
    note: 'API uses Next.js proxy (no CORS issues), WebSocket uses direct connection'
  });
}

// API endpoints
export const API_ENDPOINTS = {
  // Experiments endpoints
  EXPERIMENTS_OVERVIEW: '/api/experiments/overview',
  EXPERIMENT_DETAIL: (experimentId: string) => `/api/experiments/${experimentId}`,
  EXPERIMENT_DEVICES: (experimentId: string) => `/api/experiments/${experimentId}/devices`,
  EXPERIMENT_NETWORK_FLOW_SANKEY: (experimentId: string) => `/api/experiments/${experimentId}/network-flow-sankey`,



  // Device endpoints
  DEVICE_DETAIL: (deviceId: string) => `/api/devices/${deviceId}/detail`,
  DEVICE_PORT_ANALYSIS: (deviceId: string) => `/api/devices/${deviceId}/port-analysis`,
  DEVICE_PROTOCOL_DISTRIBUTION: (deviceId: string) => `/api/devices/${deviceId}/protocol-distribution`,
  DEVICE_NETWORK_TOPOLOGY: (deviceId: string) => `/api/devices/${deviceId}/network-topology`,
  DEVICE_ACTIVITY_TIMELINE: (deviceId: string) => `/api/devices/${deviceId}/activity-timeline`,
  DEVICE_TRAFFIC_TREND: (deviceId: string) => `/api/devices/${deviceId}/traffic-trend`,

  // System endpoints
  HEALTH: '/health',
  STATUS: '/api/status'
} as const;

// WebSocket topics
export const WS_TOPICS = {
  // Experiments topics
  EXPERIMENTS_OVERVIEW: 'experiments.overview',
  EXPERIMENT_DETAIL: (experimentId: string) => `experiments.${experimentId}`,
  EXPERIMENT_DEVICES: (experimentId: string) => `experiments.${experimentId}.devices`,



  // Device topics
  DEVICE_DETAIL: (deviceId: string) => `devices.${deviceId}.detail`,
  DEVICE_PORT_ANALYSIS: (deviceId: string) => `devices.${deviceId}.port-analysis`,
  DEVICE_PROTOCOL_DISTRIBUTION: (deviceId: string) => `devices.${deviceId}.protocol-distribution`,
  DEVICE_NETWORK_TOPOLOGY: (deviceId: string) => `devices.${deviceId}.network-topology`,
  DEVICE_ACTIVITY_TIMELINE: (deviceId: string) => `devices.${deviceId}.activity-timeline`,
  DEVICE_TRAFFIC_TREND: (deviceId: string) => `devices.${deviceId}.traffic-trend`
} as const;

// Request configuration
export const REQUEST_CONFIG = {
  timeout: 30000, // 30 seconds
  retries: 3,
  retryDelay: 1000 // 1 second
} as const;

// WebSocket configuration
export const WS_CONFIG = {
  reconnectInterval: 5000, // 5 seconds
  maxReconnectAttempts: 10,
  heartbeatInterval: 30000 // 30 seconds
} as const; 
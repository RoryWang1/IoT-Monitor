/** @type {import('next').NextConfig} */
const path = require('path');
const fs = require('fs');
const os = require('os');

// Auto-detect server IP function
function getServerIP() {
  // First check if running in browser (client-side)
  if (typeof window !== 'undefined') {
    return window.location.hostname;
  }
  
  // Server-side detection
  const interfaces = os.networkInterfaces();
  for (const name of Object.keys(interfaces)) {
    for (const iface of interfaces[name]) {
      // Skip internal loopback and non-IPv4 addresses
      if (iface.family === 'IPv4' && !iface.internal) {
        return iface.address;
      }
    }
  }
  return '127.0.0.1'; // fallback
}

// Read configuration from user_config.json
let userConfig;
try {
  const configPath = path.join(__dirname, '..', 'config', 'user_config.json');
  const configContent = fs.readFileSync(configPath, 'utf8');
  userConfig = JSON.parse(configContent);
} catch (error) {
  console.warn('Could not read user_config.json, using default ports');
  userConfig = {
    system_ports: {
      backend: 8002,
      frontend: 3002
    }
  };
}

const backendPort = userConfig.system_ports?.backend || 8002;
const frontendPort = userConfig.system_ports?.frontend || 3002;

// Read backend server configuration
const backendServer = userConfig.backend_server || { host: 'auto', api_port: 8002, websocket_port: 8002 };
const configuredHost = backendServer.host;
const apiPort = backendServer.api_port || backendPort;
const wsPort = backendServer.websocket_port || backendPort;

// Smart API host detection for Docker vs local development
let clientApiHost;
let websocketHost;
let useFlexibleConfig = false;

// Check if user has manually configured backend server host
if (configuredHost && configuredHost !== 'auto') {
  // User manually specified backend server IP
  clientApiHost = configuredHost;
  websocketHost = configuredHost;
  console.log(`User configured backend server: ${configuredHost}`);
} else if (process.env.NEXT_PUBLIC_API_BASE_URL) {
  // Docker environment: extract host from environment variable
  const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
  clientApiHost = apiUrl.replace('http://', '').replace(/:\d+$/, '');
  websocketHost = clientApiHost;
  console.log(`Docker environment detected, using API host: ${clientApiHost}`);
} else {
  // Use flexible configuration for local deployment
  // This allows dynamic IP detection at runtime
  useFlexibleConfig = true;
  clientApiHost = '127.0.0.1'; // Fallback for build time
  websocketHost = getServerIP();
  console.log(`Using flexible configuration mode for local deployment`);
}

const nextConfig = {
  reactStrictMode: false,
  swcMinify: true,
  
  async redirects() {
    return [
      {
        source: '/dashboard',
        destination: '/',
        permanent: true,
      },
    ];
  },
  async rewrites() {
    // In production, we can't rely on runtime environment variables
    // Use a more robust approach that works across different deployment scenarios
    return [
      {
        source: '/api/:path*',
        destination: `http://127.0.0.1:${apiPort}/api/:path*`,
      },
      {
        source: '/auto/api/:path*',
        destination: `http://127.0.0.1:${apiPort}/api/:path*`,
      },
      {
        source: '/health',
        destination: `http://127.0.0.1:${apiPort}/health`,
      }
    ];
  },
  async headers() {
    return [
      {
        source: '/api/:path*',
        headers: [
          { key: 'Access-Control-Allow-Origin', value: '*' },
          { key: 'Access-Control-Allow-Methods', value: 'GET,OPTIONS,PATCH,DELETE,POST,PUT' },
          { key: 'Access-Control-Allow-Headers', value: 'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version' },
        ],
      },
    ];
  },
  webpack: (config, { dev, isServer }) => {
    if (dev && !isServer) {
      config.watchOptions = {
        poll: 1000,
        aggregateTimeout: 300,
      };
    }
    return config;
  },
  env: {
    // Stable configuration for builds, runtime detection handled by client
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL || 'auto',
    NEXT_PUBLIC_WS_BASE_URL: process.env.NEXT_PUBLIC_WS_BASE_URL || 'auto',
    NEXT_PUBLIC_USE_FLEXIBLE_CONFIG: 'true',
    NEXT_PUBLIC_API_PORT: (apiPort || 8001).toString(),
    NEXT_PUBLIC_WS_PORT: (wsPort || 8001).toString(),
  },
}

module.exports = nextConfig 
#!/usr/bin/env node

const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const os = require('os');

// Read configuration from user_config.json
let userConfig;
try {
  const configPath = path.join(__dirname, '..', '..', 'config', 'user_config.json');
  const configContent = fs.readFileSync(configPath, 'utf8');
  userConfig = JSON.parse(configContent);
} catch (error) {
          console.warn('Could not read user_config.json, using default port 3001');
  userConfig = {
    system_ports: {
                  frontend: 3001
    }
  };
}

    const frontendPort = userConfig.system_ports?.frontend || 3001;
const hostname = '0.0.0.0'; // Listen on all network interfaces

// Auto-detect server IP for network deployment
function getServerIP() {
  const interfaces = os.networkInterfaces();
  for (const name of Object.keys(interfaces)) {
    for (const iface of interfaces[name]) {
      // Skip internal loopback and non-IPv4 addresses
      if (iface.family === 'IPv4' && !iface.internal) {
        return iface.address;
      }
    }
  }
  return '127.0.0.1'; // fallback to localhost
}

// Auto-detect and set server configuration
const serverIP = getServerIP();
process.env.NEXT_PUBLIC_SERVER_HOST = serverIP;
process.env.RUNTIME_API_HOST = serverIP; // For dynamic API rewrites

// Fix WebSocket URL to use current IP
const backendPort = userConfig.system_ports?.backend || 8001;
process.env.NEXT_PUBLIC_WS_BASE_URL = `ws://${serverIP}:${backendPort}`;

console.log(`Auto-detected server IP: ${serverIP}`);
console.log(`Setting RUNTIME_API_HOST to: ${serverIP}`);
console.log(`Setting NEXT_PUBLIC_WS_BASE_URL to: ws://${serverIP}:${backendPort}`);

console.log(`Starting Next.js production server on ${hostname}:${frontendPort}`);
console.log(`Frontend accessible at: http://${serverIP}:${frontendPort}`);
console.log(`API connections will use: ${process.env.NEXT_PUBLIC_SERVER_HOST}`);
console.log(`WebSocket connections will use: ws://${serverIP}:${userConfig.system_ports?.backend || 8001}`);

// Show access URLs for all network interfaces
console.log('\n=== Access URLs ===');
console.log(`Local:    http://localhost:${frontendPort}`);
console.log(`Network:  http://${serverIP}:${frontendPort}`);
if (hostname === '0.0.0.0') {
  console.log(`All IPs:  http://0.0.0.0:${frontendPort}`);
}
console.log('==================\n');

// Start Next.js production server with hostname binding
const nextProcess = spawn('npx', ['next', 'start', '-p', frontendPort.toString(), '-H', hostname], {
  stdio: 'inherit',
  shell: true,
  env: { ...process.env } // Pass environment variables including NEXT_PUBLIC_SERVER_HOST
});

nextProcess.on('exit', (code) => {
  process.exit(code);
});

process.on('SIGINT', () => {
  nextProcess.kill('SIGINT');
});

process.on('SIGTERM', () => {
  nextProcess.kill('SIGTERM');
}); 
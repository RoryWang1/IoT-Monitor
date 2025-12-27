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

// Set server host environment variable if not already set
if (!process.env.NEXT_PUBLIC_SERVER_HOST) {
  const serverIP = getServerIP();
  process.env.NEXT_PUBLIC_SERVER_HOST = serverIP;
  console.log(`Auto-detected server IP: ${serverIP}`);
}

console.log(`Starting Next.js development server on ${hostname}:${frontendPort}`);
console.log(`Frontend accessible at: http://${hostname}:${frontendPort}`);
console.log(`API connections will use: ${process.env.NEXT_PUBLIC_SERVER_HOST}`);

// Start Next.js development server with hostname binding
const nextProcess = spawn('npx', ['next', 'dev', '-p', frontendPort.toString(), '-H', hostname], {
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
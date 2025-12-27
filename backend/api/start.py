#!/usr/bin/env python3
"""
IoT Device Monitor API Service Launcher
Enhanced with port conflict detection
"""
import os
import sys
import socket
import time
import logging
import subprocess
from pathlib import Path

# Setup configuration path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
config_path = project_root / "config"

# Ensure project root exists
if not project_root.exists() or not (project_root / "config").exists():
    print(f"Project structure error: {project_root}")
    sys.exit(1)

# Set working directory to project root
os.chdir(str(project_root))

# Clean and set Python paths
sys.path = [path for path in sys.path if not path.endswith('backend/api')]

# Add Python paths - ensure correct order
paths_to_add = [str(project_root), str(config_path)]
for path in reversed(paths_to_add):  # Add in reverse to ensure correct priority
    if path not in sys.path:
        sys.path.insert(0, path)

# Set PYTHONPATH environment variable
pythonpath_parts = [str(project_root), str(config_path)]
existing_pythonpath = os.environ.get('PYTHONPATH', '')
if existing_pythonpath:
    pythonpath_parts.append(existing_pythonpath)
os.environ['PYTHONPATH'] = os.pathsep.join(pythonpath_parts)

# Verify path settings
print(f"Project root: {project_root}")
print(f"Working directory: {os.getcwd()}")
print(f"Python paths: {sys.path[:3]}")

# Try to import configuration module
config_imported = False
try:
    from config.unified_config_manager import get_config, get_log_message
    print("Config module imported successfully")
    config_imported = True
except ImportError as e:
    print(f"Package import failed: {e}")
    
if not config_imported:
    # Try to import directly
    try:
        sys.path.insert(0, str(config_path))
        import unified_config_manager
        from unified_config_manager import get_config, get_log_message
        print("Direct config import successful")
        config_imported = True
    except ImportError as e2:
        print(f"All import attempts failed: {e2}")
        print(f"Available files in config: {list(config_path.glob('*.py'))}")
        sys.exit(1)

if not config_imported:
    print("Failed to import configuration module")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_port_availability(host: str, port: int) -> bool:
    """Check if a port is available"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            return result != 0  # Port is available if connection fails
    except Exception:
        return False

def kill_process_on_port(port: int) -> bool:
    """Kill process using specified port"""
    try:
        # Find process using the port
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid:
                    logger.info(f"Killing process {pid} on port {port}")
                    subprocess.run(["kill", "-9", pid], timeout=5)
            time.sleep(2)  # Wait for process cleanup
            return True
    except Exception as e:
        logger.warning(f"Failed to kill process on port {port}: {e}")
    
    return False

def start_api_server():
    """Start API server with port conflict handling"""
    
    # Get configuration
    host = get_config('server_addresses.api_host', '0.0.0.0', 'api')
    port = get_config('system_ports.backend', 8002, 'api')
    
    logger.info("Starting IoT Device Monitor API...")
    logger.info(f"Using Python interpreter: {sys.executable}")
    
    # Check port availability
    if not check_port_availability(host, port):
        logger.warning(f"Port {port} is already in use")
        
        # Try to kill existing process
        if kill_process_on_port(port):
            logger.info(f"Successfully freed port {port}")
            time.sleep(1)  # Additional wait
        else:
            logger.error(f"Could not free port {port}")
            return False
    
    # Verify port is now available
    if not check_port_availability(host, port):
        logger.error(f"Port {port} is still occupied after cleanup attempt")
        return False
    
    # Change to project root directory
    os.chdir(project_root)
    logger.info(f"Working directory: {project_root}")
    
    try:
        logger.info("Starting API server...")
        
        # Use uvicorn programmatically to avoid shell escaping issues
        import uvicorn
        from backend.api.app import app
        
        # Configure uvicorn
        config = uvicorn.Config(
            app=app,
            host=host,
            port=port,
            log_level="info",
            reload=False,
            access_log=True
        )
        
        server = uvicorn.Server(config)
        logger.info(f"Starting server: http://{host}:{port}")
        
        # Run the server
        import asyncio
        asyncio.run(server.serve())
        
    except Exception as e:
        logger.error(f"API server failed to start: {e}")
        return False
    
    return True

if __name__ == "__main__":
    try:
        success = start_api_server()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1) 
#!/bin/bash
set -e

# Enable debugging if DEBUG environment variable is set
if [ "${DEBUG:-0}" = "1" ]; then
    set -x
    log_info "Debug mode enabled - showing all command execution"
fi

# IoT Device Monitor
echo "IoT Device Monitor - Local System Deployment"

# Global variables
PROJECT_ROOT=""
PG_BIN_DIR=""
DEPLOY_LOG=""

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Progress display function
show_progress() {
    local current=$1
    local total=$2
    local description="$3"
    local percent=$((current * 100 / total))
    printf "\r${BLUE}[PROGRESS]${NC} [%3d%%] Step %d/%d: %s" "$percent" "$current" "$total" "$description"
    if [ "$current" -eq "$total" ]; then
        echo ""
    fi
}

# Function to run command with timeout and progress monitoring
run_with_progress() {
    local command="$1"
    local description="$2"
    local timeout_seconds=${3:-300}  # Default 5 minutes timeout
    
    log_info "$description"
    log_info "Command: $command"
    log_info "Timeout: ${timeout_seconds}s (will show progress every 30s)"
    
    # Run command in background
    eval "$command" &
    local cmd_pid=$!
    
    # Monitor progress
    local elapsed=0
    while kill -0 $cmd_pid 2>/dev/null; do
        sleep 30
        elapsed=$((elapsed + 30))
        log_info "Still running... (${elapsed}s elapsed)"
        
        if [ $elapsed -ge $timeout_seconds ]; then
            log_error "Command timed out after ${timeout_seconds}s"
            kill $cmd_pid 2>/dev/null
            return 1
        fi
    done
    
    # Wait for command to complete and get exit status
    wait $cmd_pid
    return $?
}

# Auto-detect server IP function for deployment
get_deployment_server_ip() {
    local server_ip=""
    
    # Method 1: Use ip route (most reliable)
    if command -v ip >/dev/null 2>&1; then
        server_ip=$(ip route get 8.8.8.8 2>/dev/null | head -1 | awk '{print $7}' 2>/dev/null || echo "")
    fi
    
    # Method 2: Fallback to network interface detection
    if [ -z "$server_ip" ]; then
        for interface in $(ls /sys/class/net/ 2>/dev/null | grep -v lo); do
            local ip=$(ip addr show "$interface" 2>/dev/null | grep "inet " | head -1 | awk '{print $2}' | cut -d/ -f1)
            if [ -n "$ip" ] && [[ $ip =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] && [[ ! $ip =~ ^127\. ]]; then
                server_ip="$ip"
                break
            fi
        done
    fi
    
    # Method 3: Use hostname -I as final fallback
    if [ -z "$server_ip" ] && command -v hostname >/dev/null 2>&1; then
        server_ip=$(hostname -I 2>/dev/null | awk '{print $1}' | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$' || echo "")
    fi
    
    # Final fallback
    if [ -z "$server_ip" ]; then
        server_ip="127.0.0.1"
    fi
    
    echo "$server_ip"
}

# Error handling
error_exit() {
    log_error "Deployment failed, please check error information"
    log_error "Detailed log: $DEPLOY_LOG"
    
    # Try to stop PostgreSQL if it was started during deployment
    if [ -n "$PG_BIN_DIR" ] && [ -d "database/data/postgresql" ]; then
        log_info "Attempting to stop PostgreSQL before exit..."
        sudo -u postgres "$PG_BIN_DIR/pg_ctl" -D database/data/postgresql stop 2>/dev/null || true
    fi
    
    exit 1
}
trap error_exit ERR

# Step 1: Environment check
check_environment() {
    log_info "[1/13] Step 1: Environment check..."
    
    # Get project root directory
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
    cd "$PROJECT_ROOT"
    
    # Create log directory
    mkdir -p log
    DEPLOY_LOG="$PROJECT_ROOT/log/deployment.log"
    echo "=== IoT System Deployment Started $(date) ===" | tee -a "$DEPLOY_LOG"
    
    log_success "Project path: $PROJECT_ROOT"
    log_success "Target system: Debian/Ubuntu/Kali"
    log_success "Deployment log: $DEPLOY_LOG"
    
    # Check sudo privileges
    if ! sudo -n true 2>/dev/null; then
        log_error "Sudo privileges required, please ensure current user has sudo access"
        exit 1
    fi
    
    log_success "Environment check completed"
}

# Step 2: System dependencies installation
install_system_dependencies() {
    log_info "[2/13] Step 2: System dependencies installation..."
    
    # Configure environment for non-interactive installation
    export DEBIAN_FRONTEND=noninteractive
    export NEEDRESTART_MODE=a
    export UCF_FORCE_CONFFNEW=YES
    export APT_LISTCHANGES_FRONTEND=none
    export APT_LISTBUGS_FRONTEND=none
    
    # Additional GRUB-specific environment variables
    export GRUB_FORCE_PARTUUID=1
    export DEBIAN_PRIORITY=critical
    
    # Preconfigure common interactive prompts to avoid hanging
    log_info "Preconfiguring system to avoid interactive prompts..."
    
    # Configure GRUB to avoid prompts
    log_info "Configuring GRUB to prevent interactive prompts..."
    
    # Set all possible GRUB configurations to avoid prompts
    echo "grub-pc grub-pc/install_devices_disks_changed multiselect" | sudo debconf-set-selections
    echo "grub-pc grub-pc/install_devices multiselect" | sudo debconf-set-selections  
    echo "grub-pc grub-pc/install_devices_failed_upgrade boolean true" | sudo debconf-set-selections
    echo "grub-pc grub-pc/install_devices_empty boolean false" | sudo debconf-set-selections
    echo "grub-pc grub-pc/diskcheck boolean false" | sudo debconf-set-selections
    echo "grub-pc grub-pc/mixed_legacy_and_grub2 boolean true" | sudo debconf-set-selections
    echo "grub-pc grub-pc/postrm_purge_boot_grub boolean false" | sudo debconf-set-selections
    echo "grub-pc grub2/linux_cmdline_default string quiet splash" | sudo debconf-set-selections
    echo "grub-pc grub2/linux_cmdline string" | sudo debconf-set-selections
    
    # Also configure grub2-common
    echo "grub2-common grub2/update_nvram boolean true" | sudo debconf-set-selections
    echo "grub2-common grub-pc/install_devices_disks_changed multiselect" | sudo debconf-set-selections
    
    # Configure other common prompts
    echo "libc6 libraries/restart-without-asking boolean true" | sudo debconf-set-selections
    echo "libssl1.1:amd64 libraries/restart-without-asking boolean true" | sudo debconf-set-selections
    
    # Update system
    log_info "Updating system packages (this may take a few minutes)..."
    sudo apt-get update 2>&1 | tee -a "$DEPLOY_LOG"
    
    # System upgrade is disabled by default to avoid deployment issues
    # Set ENABLE_UPGRADE=1 to force system upgrade if needed
    if [ "${ENABLE_UPGRADE:-0}" = "1" ]; then
        log_info "System upgrade enabled - Upgrading system packages (this may take several minutes)..."
        log_warn "This may cause GRUB prompts or deployment issues"
        
        # First try: Safe upgrade excluding problematic packages
        log_info "Attempting safe upgrade (excluding GRUB-related packages)..."
        if sudo apt-get upgrade -y \
            -o Dpkg::Options::="--force-confdef" \
            -o Dpkg::Options::="--force-confnew" \
            -o APT::Get::Assume-Yes=true \
            -o APT::Get::Trivial-Only=true \
            --exclude=grub-pc,grub2-common,grub-pc-bin,grub-common 2>&1 | tee -a "$DEPLOY_LOG"; then
            log_success "Safe upgrade completed successfully"
        else
            log_warn "Safe upgrade failed or requires user interaction"
            log_info "Attempting minimal upgrade with GRUB handling..."
            
            # Second try: Full upgrade with GRUB handling
            sudo apt-get upgrade -y \
                -o Dpkg::Options::="--force-confdef" \
                -o Dpkg::Options::="--force-confnew" \
                -o Dpkg::Options::="--force-confold" \
                -o APT::Get::Assume-Yes=true \
                -o APT::Get::AllowUnauthenticated=true 2>&1 | tee -a "$DEPLOY_LOG" || {
                log_error "System upgrade failed or was interrupted by GRUB prompts"
                log_warn "Continuing without system upgrade..."
            }
        fi
    else
        log_info "System upgrade disabled by default (recommended for IoT deployment)"
        log_info "Only updating package lists to ensure latest package information"
        log_info "Use ENABLE_UPGRADE=1 to force system upgrade if absolutely needed"
    fi
    
    # Preconfigure PostgreSQL to avoid prompts
    log_info "Preconfiguring PostgreSQL installation..."
    # Check if PostgreSQL debconf questions exist before setting them
    if sudo debconf-show postgresql-common 2>/dev/null | grep -q "obsolete-major"; then
        echo "postgresql-common postgresql-common/obsolete-major seen true" | sudo debconf-set-selections
    fi
    # Set common PostgreSQL configurations that usually exist
    echo "postgresql-common postgresql-common/ssl boolean true" | sudo debconf-set-selections 2>/dev/null || true
    
    # Install base system dependencies
    log_info "Installing base system dependencies (this may take several minutes)..."
    # Note: python3-distutils is not available in Ubuntu 24.04+, removed from list
    sudo apt-get install -y \
        -o Dpkg::Options::="--force-confnew" \
        -o APT::Get::Assume-Yes=true \
        python3 python3-pip python3-dev python3-venv \
        postgresql postgresql-contrib postgresql-client libpq-dev \
        curl wget git build-essential \
        lsof net-tools htop \
        pkg-config libssl-dev libffi-dev \
        python3-setuptools python3-wheel 2>&1 | tee -a "$DEPLOY_LOG"
    
    # Install scientific computing library support
    log_info "Installing scientific computing libraries (this may take a few minutes)..."
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
        python3-numpy python3-scipy \
        libblas-dev liblapack-dev gfortran 2>&1 | tee -a "$DEPLOY_LOG"
    
    log_success "System dependencies installation completed"
}
# Step 3: Node.js installation
install_nodejs() {
    log_info "[3/13] Step 3: Node.js 18.x installation..."
    
    if ! command -v node &> /dev/null || [[ $(node --version | cut -d'.' -f1 | tr -d 'v') -lt 18 ]]; then
        # Uninstall old version
        sudo DEBIAN_FRONTEND=noninteractive apt-get remove -y nodejs npm 2>&1 | tee -a "$DEPLOY_LOG" || true
        
        # Install Node.js 18.x
        log_info "Installing Node.js 18.x via NodeSource repository..."
        curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash - 2>&1 | tee -a "$DEPLOY_LOG"
        sudo DEBIAN_FRONTEND=noninteractive apt-get install -y nodejs 2>&1 | tee -a "$DEPLOY_LOG"
        
        # Verify installation
        NODE_VERSION=$(node --version)
        NPM_VERSION=$(npm --version)
        log_success "Node.js installed: $NODE_VERSION"
        log_success "npm version: $NPM_VERSION"
    else
        NODE_VERSION=$(node --version)
        NPM_VERSION=$(npm --version)
        log_success "Node.js already exists: $NODE_VERSION"
        log_success "npm version: $NPM_VERSION"
    fi
}
# Step 4: Python dependencies installation
install_python_dependencies() {
    log_info "[4/13] Step 4: Python dependencies installation..."
    
    # Ensure pip is properly installed
    log_info "Ensuring pip is properly installed..."
    if ! command -v pip3 &> /dev/null; then
        log_warn "pip3 not found, installing python3-pip..."
        sudo apt-get install -y python3-pip 2>&1 | tee -a "$DEPLOY_LOG"
    fi
    
    # Upgrade pip
    log_info "Upgrading pip..."
    if python3 -m pip --version &> /dev/null; then
        # Check pip version to determine if --break-system-packages is supported
        pip_version=$(python3 -m pip --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+' | head -1)
        pip_major=$(echo "$pip_version" | cut -d. -f1)
        pip_minor=$(echo "$pip_version" | cut -d. -f2)
        
        if [ "$pip_major" -gt 22 ] || ([ "$pip_major" -eq 22 ] && [ "$pip_minor" -ge 2 ]); then
            sudo python3 -m pip install --upgrade pip --no-warn-script-location --break-system-packages 2>&1 | tee -a "$DEPLOY_LOG"
        else
            sudo python3 -m pip install --upgrade pip --no-warn-script-location 2>&1 | tee -a "$DEPLOY_LOG"
        fi
    else
        log_warn "Python pip module not available, installing via apt..."
        sudo apt-get install -y python3-pip 2>&1 | tee -a "$DEPLOY_LOG"
        # After installing pip, check version again
        pip_version=$(python3 -m pip --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+' | head -1)
        pip_major=$(echo "$pip_version" | cut -d. -f1)
        pip_minor=$(echo "$pip_version" | cut -d. -f2)
        
        if [ "$pip_major" -gt 22 ] || ([ "$pip_major" -eq 22 ] && [ "$pip_minor" -ge 2 ]); then
            sudo python3 -m pip install --upgrade pip --no-warn-script-location --break-system-packages 2>&1 | tee -a "$DEPLOY_LOG"
        else
            sudo python3 -m pip install --upgrade pip --no-warn-script-location 2>&1 | tee -a "$DEPLOY_LOG"
        fi
    fi
    
    # Install project dependencies
    log_info "Installing project Python dependencies (this may take several minutes)..."
    
    # Check pip version to determine if --break-system-packages is supported
    pip_version=$(python3 -m pip --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+' | head -1)
    pip_major=$(echo "$pip_version" | cut -d. -f1)
    pip_minor=$(echo "$pip_version" | cut -d. -f2)
    
    if [ "$pip_major" -gt 22 ] || ([ "$pip_major" -eq 22 ] && [ "$pip_minor" -ge 2 ]); then
        log_info "Note: Using --break-system-packages for system deployment (Ubuntu 24.04+ requirement)"
        sudo python3 -m pip install -r requirements.txt --no-warn-script-location --no-cache-dir --break-system-packages 2>&1 | tee -a "$DEPLOY_LOG"
    else
        log_info "Note: Using standard pip installation (Ubuntu 20.04 compatible)"
        sudo python3 -m pip install -r requirements.txt --no-warn-script-location --no-cache-dir 2>&1 | tee -a "$DEPLOY_LOG"
    fi
    
    # Verify critical packages
    log_info "Verifying critical Python packages..."
    python3 -c "import fastapi, uvicorn, asyncpg, sqlalchemy, pydantic, aiohttp" 2>/dev/null
    
    log_success "Python dependencies installation completed"
}
# Step 5: Frontend dependencies installation with dynamic IP configuration
install_frontend_dependencies() {
    log_info "[5/13] Step 5: Frontend dependencies installation with dynamic IP configuration..."
    
    # Detect server IP for frontend configuration
    local FRONTEND_IP=$(get_deployment_server_ip)
    log_info "Configuring frontend for IP: $FRONTEND_IP"
    
    cd frontend
    
    # Set environment variables for frontend build
    export NEXT_PUBLIC_API_BASE_URL="http://$FRONTEND_IP:8001"
    export NEXT_PUBLIC_WS_BASE_URL="ws://$FRONTEND_IP:8001"
    export NEXT_PUBLIC_USE_FLEXIBLE_CONFIG="true"
    export NEXT_PUBLIC_AUTO_DETECTED_HOST="$FRONTEND_IP"
    export NEXT_PUBLIC_API_PORT="8001"
    export NEXT_PUBLIC_WS_PORT="8001"
    export RUNTIME_API_HOST="$FRONTEND_IP"
    
    log_info "Frontend environment variables set:"
    log_info "  NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL"
    log_info "  NEXT_PUBLIC_WS_BASE_URL=$NEXT_PUBLIC_WS_BASE_URL"
    
    # Install npm dependencies
    log_info "Installing frontend npm dependencies (this may take several minutes)..."
    npm install --no-optional --progress=true 2>&1 | tee -a "$DEPLOY_LOG"
    
    # Build frontend with dynamic IP configuration
    log_info "Building frontend with dynamic IP configuration (this may take a few minutes)..."
    npm run build 2>&1 | tee -a "$DEPLOY_LOG"
    
    cd "$PROJECT_ROOT"
    log_success "Frontend dependencies installation completed with IP: $FRONTEND_IP"
}

# Step 6: Cleanup existing services
cleanup_services() {
    log_info "[6/13] Step 6: Cleanup existing services..."
    
    # Stop existing processes
    pkill -f "python.*start.py" 2>/dev/null || true
    pkill -f "npm.*start" 2>/dev/null || true
    sudo systemctl stop postgresql 2>/dev/null || true
    
    # Clean up ports
    for port in 5433 8001 3001; do
        lsof -Pi :$port -sTCP:LISTEN -t 2>/dev/null | xargs kill -9 2>/dev/null || true
    done
    
    log_success "Services cleanup completed"
}

# Step 7: Create directory structure
create_directories() {
    log_info "[7/13] Step 7: Create directory structure..."
    
    # Create postgres user if it doesn't exist (early creation)
    if ! id "postgres" &>/dev/null; then
        log_info "Creating postgres system user..."
        sudo useradd -r -s /bin/bash -d /var/lib/postgresql postgres
    fi
    
    # Create necessary directories
    mkdir -p log pcap_input database/{data/postgresql,logs,run,backups}
    
    # Fix directory access permissions for postgres user
    log_info "Setting up directory access permissions..."
    
    # Get current user and ensure postgres can access the project directory
    CURRENT_USER=$(whoami)
    sudo usermod -a -G "$CURRENT_USER" postgres 2>/dev/null || true
    
    # Make project directory and parent directories readable by group
    chmod 755 "$PROJECT_ROOT"
    # Ensure parent directories are also accessible
    chmod 755 "$(dirname "$PROJECT_ROOT")" 2>/dev/null || true
    chmod 755 "$(dirname "$(dirname "$PROJECT_ROOT")")" 2>/dev/null || true
    
    # Set correct ownership and permissions
    sudo chown -R postgres:postgres database/
    sudo chmod -R 755 log/ pcap_input/
    sudo chmod -R 755 database/
    
    # PostgreSQL requires strict 700 permissions for data directory
    sudo chmod 700 database/data/postgresql/
    log_info "PostgreSQL data directory set to 700 permissions (required by PostgreSQL)"
    
    log_success "Directory structure created with correct permissions"
}

# Step 8: Configure PostgreSQL
configure_postgresql() {
    log_info "[8/13] Step 8: Configure PostgreSQL..."
    
    # Find PostgreSQL path
    for version in {16,15,14,13,12,11,10}; do
        if [ -d "/usr/lib/postgresql/$version/bin" ]; then
            PG_BIN_DIR="/usr/lib/postgresql/$version/bin"
            break
        fi
    done
    
    if [ -z "$PG_BIN_DIR" ]; then
        log_error "PostgreSQL binary file path not found"
        exit 1
    fi
    
    log_info "Using PostgreSQL: $PG_BIN_DIR"
    
    # Clean and prepare data directory
    log_info "Preparing PostgreSQL data directory..."
    sudo rm -rf database/data/postgresql/*
    sudo mkdir -p database/data/postgresql
    sudo chown -R postgres:postgres database/data/postgresql/
    
    # PostgreSQL requires strict 700 permissions - critical security requirement
    sudo chmod 700 database/data/postgresql/
    log_info "PostgreSQL data directory permissions set to 700 (PostgreSQL security requirement)"
    
    # Initialize database as postgres user
    log_info "Initializing PostgreSQL database as postgres user..."
    sudo -u postgres "$PG_BIN_DIR/initdb" -D database/data/postgresql \
        --locale=C.UTF-8 --encoding=UTF8 --auth-local=trust --auth-host=md5 2>&1 | tee -a "$DEPLOY_LOG"
    
    # Configure PostgreSQL with temporary file approach
    log_info "Configuring PostgreSQL..."
    
    # Create temp config files
    cat > /tmp/postgresql_temp.conf << EOF
listen_addresses = 'localhost'
port = 5433
max_connections = 50
logging_collector = on
log_directory = '../../logs'
log_filename = 'postgresql.log'
shared_buffers = 128MB
EOF

    cat > /tmp/pg_hba_temp.conf << EOF
local   all             all                                     trust
host    all             all             127.0.0.1/32            trust
host    all             all             ::1/128                 trust
EOF
    
    # Copy config files as postgres user
    sudo -u postgres cp /tmp/postgresql_temp.conf database/data/postgresql/postgresql.conf
    sudo -u postgres cp /tmp/pg_hba_temp.conf database/data/postgresql/pg_hba.conf
    sudo -u postgres chmod 600 database/data/postgresql/{postgresql.conf,pg_hba.conf}
    
    # Clean up temp files
    rm -f /tmp/postgresql_temp.conf /tmp/pg_hba_temp.conf
    
    log_success "PostgreSQL configuration completed"
}

# Step 9: Create configuration file with dynamic IP detection
create_config() {
    log_info "[9/13] Step 9: Create configuration file with dynamic IP detection..."
    
    # Detect server IP for deployment
    local DETECTED_IP=$(get_deployment_server_ip)
    log_info "Detected server IP for deployment: $DETECTED_IP"
    
    # Check if a complete config already exists
    if [ -f "config/user_config.json" ] && grep -q "logging" config/user_config.json; then
        log_info "Complete configuration file already exists, updating database settings only..."
        
        # Update only database connection settings in existing config
        python3 -c "
import json
try:
    with open('config/user_config.json', 'r') as f:
        config = json.load(f)
    
    # Update database connection settings
    if 'database' not in config:
        config['database'] = {}
    
    config['database']['connection'] = {
        'host': 'localhost',
        'port': 5433,
        'database': 'iot_monitor',
        'user': 'iot_user',
        'password': 'iot_password'
    }
    
    # Remove docker_connection if it exists (not needed for local deployment)
    if 'docker_connection' in config['database']:
        del config['database']['docker_connection']
    
    with open('config/user_config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print('Updated existing configuration file')
except Exception as e:
    print(f'Error updating config: {e}')
"
    else
        log_info "Creating complete configuration file with dynamic IP support..."
        cat > config/user_config.json << EOF
{
  "deployment_info": {
    "deployment_time": "$(date -Iseconds)",
    "detected_ip": "$DETECTED_IP",
    "deployment_mode": "local_dynamic",
    "auto_ip_detection": true
  },
  "backend_server": {
    "host": "$DETECTED_IP",
    "api_port": 8001,
    "websocket_port": 8001,
    "auto_detect_ip": true,
    "fallback_host": "127.0.0.1"
  },
  "logging": {
    "level": {
      "current": "INFO",
      "available_options": [
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL"
      ],
      "description": "Global log level"
    },
    "categories": {
      "api_endpoints": "INFO",
      "database": "INFO",
      "websocket": "INFO",
      "file_monitor": "INFO",
      "device_analysis": "INFO",
      "description": "Independent log level settings for each module"
    },
    "rotation": {
      "enabled": true,
      "max_size_mb": 100,
      "backup_count": 5,
      "description": "Log file rotation settings"
    }
  },
  "database": {
    "connection": {
      "host": "localhost",
      "port": 5433,
      "database": "iot_monitor", 
      "user": "iot_user",
      "password": "iot_password"
    },
    "docker_connection": {
      "host": "database",
      "port": 5432,
      "database": "iot_monitor",
      "user": "postgres", 
      "password": "postgres"
    },
    "description": "Database configuration"
  },
  "server_addresses": {
    "localhost": "127.0.0.1",
    "api_host": "0.0.0.0",
    "description": "Server address configuration"
  },
  "server": {
    "api": {
      "host": "0.0.0.0",
      "port": 8001,
      "description": "Backend API server configuration"
    },
    "frontend": {
      "host": "0.0.0.0",
      "port": 3001,
      "description": "Frontend server configuration"
    }
  },
  "activity_thresholds": {
    "very_active": 0.9,
    "active": 0.6,
    "moderate": 0.3,
    "low": 0.1,
    "description": "Device activity classification threshold configuration"
  },
  "file_monitoring": {
    "schedule": {
      "enabled": true,
      "scan_times": [
        "06:00",
        "12:00",
        "18:00",
        "21:32"
      ],
      "timezone": "local",
      "description": "Daily PCAP file scanning time points"
    },
    "processing": {
      "auto_process_new_files": true,
      "batch_size": 10,
      "max_concurrent_files": 3,
      "description": "New PCAP file automatic processing configuration"
    },
    "file_types": {
      "supported_extensions": [
        ".pcap",
        ".pcapng",
        ".cap"
      ],
      "ignore_hidden_files": true,
      "ignore_temp_files": true,
      "description": "Supported file types and filtering rules"
    }
  },
  "device_status": {
    "online_detection": {
      "threshold_hours": 24,
      "description": "Device online detection threshold: device last activity time within this number of hours is considered online"
    }
  },
  "time_windows": {
    "default": "48h",
    "available_options": [
      "1h",
      "6h",
      "12h",
      "24h",
      "48h"
    ],
    "description": "Default time window for each feature module"
  },
  "analysis_limits": {
    "max_ports_per_device": 50,
    "max_devices_per_experiment": 100,
    "max_connections_per_topology": 200,
    "min_packets_threshold": 1,
    "description": "Basic analysis function restrictions to prevent excessive results from affecting performance"
  },
  "data_retention": {
    "packet_flows_days": 8,
    "device_history_days": 8,
    "experiment_data_days": 8,
    "log_files_days": 8,
    "description": "Number of days retained for various data"
  },
  "database_storage": {
    "data_directory": "database/data",
    "description": "Database data file storage directory"
  },
  "system_ports": {
    "frontend": 3001,
    "backend": 8001,
    "description": "Port configuration for each system service"
  },
  "ui_settings": {
    "refresh_intervals": {
      "device_list_seconds": 30,
      "port_analysis_seconds": 60,
      "network_topology_seconds": 120,
      "system_status_seconds": 10,
      "description": "Automatic refresh interval for each UI component"
    },
    "display_limits": {
      "items_per_page": 50,
      "show_inactive_devices": true,
      "enable_auto_refresh": true,
      "description": "UI display-related settings"
    }
  },
  "alerts": {
    "device_offline_threshold_hours": 6,
    "high_traffic_threshold_gb": 5,
    "description": "Alert threshold settings"
  },
  "maintenance": {
    "database_cleanup": {
      "enabled": true,
      "daily_time": "02:00",
      "description": "Database automatic cleanup settings"
    },
    "log_rotation": {
      "enabled": true,
      "max_size_mb": 100,
      "backup_count": 5,
      "description": "Log file rotation settings"
    }
  }
}
EOF
    fi
    
    log_success "Configuration file created with dynamic IP support"
    log_info "Server IP configured as: $DETECTED_IP"
    log_info "Frontend will be accessible at: http://$DETECTED_IP:3001"
    log_info "API will be accessible at: http://$DETECTED_IP:8001"
    log_info "WebSocket will be accessible at: ws://$DETECTED_IP:8001"
}

# Step 10: Start database and initialize
setup_database() {
    log_info "[10/13] Step 10: Start database and initialize..."
    
    # Ensure all directories exist with correct ownership
    sudo mkdir -p database/logs database/run
    
    # Fix parent directory permissions so postgres user can access the path
    log_info "Setting up directory permissions for postgres user access..."
    
    # Add postgres user to parallels group to access the directory
    sudo usermod -a -G parallels postgres 2>/dev/null || true
    
    # Make sure the project directory is accessible by the group
    chmod 755 "$PROJECT_ROOT"
    chmod -R 755 "$PROJECT_ROOT/database"
    
    # Set ownership for PostgreSQL directories
    sudo chown -R postgres:postgres database/data/postgresql/
    sudo chown -R postgres:postgres database/logs/
    sudo chown -R postgres:postgres database/run/
    
    # Ensure PostgreSQL data directory has correct 700 permissions
    sudo chmod 700 database/data/postgresql/
    log_info "Enforced PostgreSQL data directory 700 permissions before startup"
    
    # Remove any existing PID files
    sudo rm -f database/data/postgresql/postmaster.pid
    
    # Test postgres user access to the directory
    log_info "Testing postgres user access to data directory..."
    if ! sudo -u postgres test -r database/data/postgresql/PG_VERSION; then
        log_error "postgres user cannot access the data directory"
        log_error "Current directory permissions:"
        ls -la database/data/
        log_error "Path permissions:"
        ls -la "$PROJECT_ROOT" | head -1
        log_error "Please check directory permissions and try again"
        exit 1
    fi
    
    log_success "postgres user can access the data directory"
    
    # Start PostgreSQL as postgres user
    log_info "Starting PostgreSQL server as postgres user..."
    sudo -u postgres "$PG_BIN_DIR/pg_ctl" -D database/data/postgresql \
        -l database/logs/postgresql.log start 2>&1 | tee -a "$DEPLOY_LOG"
    
    # Wait longer for startup and verify it's running
    log_info "Waiting for PostgreSQL to fully start..."
    sleep 8
    
    # Verify PostgreSQL is running
    if ! sudo -u postgres "$PG_BIN_DIR/pg_ctl" -D database/data/postgresql status > /dev/null 2>&1; then
        log_error "PostgreSQL failed to start, check logs in database/logs/postgresql.log"
        
        # Check for common permission error
        if grep -q "has invalid permissions" database/logs/postgresql.log 2>/dev/null; then
            log_error "PostgreSQL data directory permission error detected!"
            log_error "Fixing permissions automatically..."
            sudo chmod 700 database/data/postgresql/
            log_info "Retrying PostgreSQL startup..."
            sudo -u postgres "$PG_BIN_DIR/pg_ctl" -D database/data/postgresql \
                -l database/logs/postgresql.log start 2>&1 | tee -a "$DEPLOY_LOG"
            sleep 5
        else
            exit 1
        fi
    fi
    
    log_success "PostgreSQL server started successfully"
    
    # Create user and database
    log_info "Creating database user and database..."
    sudo -u postgres "$PG_BIN_DIR/createuser" -h localhost -p 5433 iot_user 2>&1 | tee -a "$DEPLOY_LOG" || true
    sudo -u postgres "$PG_BIN_DIR/createdb" -h localhost -p 5433 -O iot_user iot_monitor 2>&1 | tee -a "$DEPLOY_LOG" || true
    sudo -u postgres "$PG_BIN_DIR/psql" -h localhost -p 5433 -d postgres \
        -c "ALTER USER iot_user PASSWORD 'iot_password';" 2>&1 | tee -a "$DEPLOY_LOG"
    
    # Test database connection
    log_info "Testing database connection..."
    if sudo -u postgres "$PG_BIN_DIR/psql" -h localhost -p 5433 -U iot_user -d iot_monitor -c "\q" 2>/dev/null; then
        log_success "Database connection test passed"
    else
        log_error "Database connection test failed"
        exit 1
    fi
    
    # Import Schema
    log_info "Importing database schema..."
    for sql_file in database/schema/*.sql; do
        if [ -f "$sql_file" ]; then
            log_info "Importing $(basename "$sql_file")..."
            if sudo -u postgres "$PG_BIN_DIR/psql" -h localhost -p 5433 -U iot_user -d iot_monitor \
                -f "$sql_file" 2>&1 | tee -a "$DEPLOY_LOG"; then
                log_success "Successfully imported $(basename "$sql_file")"
            else
                log_error "Failed to import $(basename "$sql_file")"
                exit 1
            fi
        fi
    done
    
    log_success "Database initialization completed successfully"
}

# Step 11: Import reference data
import_reference_data() {
    log_info "[11/13] Step 11: Import reference data..."
    
    if [ -f "utils/import_reference_data.py" ]; then
        # Verify database is still running before import
        if ! sudo -u postgres "$PG_BIN_DIR/pg_ctl" -D database/data/postgresql status > /dev/null 2>&1; then
            log_error "PostgreSQL is not running, cannot import reference data"
            exit 1
        fi
        
        export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/config:$PYTHONPATH"
        log_info "Importing reference data (this may take a few minutes)..."
        
        if python3 utils/import_reference_data.py --no-clear 2>&1 | tee -a "$DEPLOY_LOG"; then
            log_success "Reference data imported successfully"
        else
            log_warn "Reference data import had some issues, but continuing..."
        fi
    else
        log_warn "Reference data import script not found"
    fi
}

# Step 12: Create startup scripts
create_startup_scripts() {
    log_info "[12/13] Step 12: Create startup scripts..."
    
    # Create startup script with dynamic IP support
    cat > start_system.sh << 'EOF'
#!/bin/bash
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "Starting IoT Device Monitor system with dynamic IP detection..."

# Auto-detect server IP function
get_server_ip() {
    local server_ip=""
    
    # Method 1: Use ip route (most reliable)
    if command -v ip >/dev/null 2>&1; then
        server_ip=$(ip route get 8.8.8.8 2>/dev/null | head -1 | awk '{print $7}' 2>/dev/null || echo "")
    fi
    
    # Method 2: Fallback to network interface detection
    if [ -z "$server_ip" ]; then
        for interface in $(ls /sys/class/net/ 2>/dev/null | grep -v lo); do
            local ip=$(ip addr show "$interface" 2>/dev/null | grep "inet " | head -1 | awk '{print $2}' | cut -d/ -f1)
            if [ -n "$ip" ] && [[ $ip =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] && [[ ! $ip =~ ^127\. ]]; then
                server_ip="$ip"
                break
            fi
        done
    fi
    
    # Method 3: Use hostname -I as final fallback
    if [ -z "$server_ip" ] && command -v hostname >/dev/null 2>&1; then
        server_ip=$(hostname -I 2>/dev/null | awk '{print $1}' | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$' || echo "")
    fi
    
    # Final fallback
    if [ -z "$server_ip" ]; then
        server_ip="127.0.0.1"
    fi
    
    echo "$server_ip"
}

# Detect current server IP
CURRENT_IP=$(get_server_ip)
echo "Detected server IP: $CURRENT_IP"

# Set environment variables for runtime
# API_BASE_URL should not be set to backend directly (causes CORS)
# Let frontend handle API proxy configuration
export NEXT_PUBLIC_WS_BASE_URL="ws://$CURRENT_IP:8001"
export RUNTIME_API_HOST="$CURRENT_IP"

# Find PostgreSQL path
PG_BIN_DIR=""
for version in {16,15,14,13,12,11,10}; do
    if [ -d "/usr/lib/postgresql/$version/bin" ]; then
        PG_BIN_DIR="/usr/lib/postgresql/$version/bin"
        break
    fi
done

# Start database
echo "Starting PostgreSQL..."
# Check if PostgreSQL is already running
if sudo -u postgres "$PG_BIN_DIR/pg_ctl" -D database/data/postgresql status > /dev/null 2>&1; then
    echo "PostgreSQL is already running"
else
    # Ensure proper ownership and permissions
    sudo chown -R postgres:postgres database/data/postgresql/
    sudo chown -R postgres:postgres database/logs/
    sudo rm -f database/data/postgresql/postmaster.pid 2>/dev/null || true
    
    # PostgreSQL requires strict 700 permissions for data directory
    sudo chmod 700 database/data/postgresql/
    
    # Fix directory permissions for postgres user access
    chmod 755 "$PROJECT_ROOT"
    CURRENT_USER=$(whoami)
    sudo usermod -a -G "$CURRENT_USER" postgres 2>/dev/null || true
    
    # Test postgres access before starting
    if ! sudo -u postgres test -r database/data/postgresql/PG_VERSION; then
        echo "Error: postgres user cannot access data directory"
        echo "Run debug script: ./deployment/local/debug_permissions.sh"
        exit 1
    fi
    
    # Start as postgres user
    sudo -u postgres "$PG_BIN_DIR/pg_ctl" -D database/data/postgresql -l database/logs/postgresql.log start
    sleep 8
    
    # Verify startup
    if sudo -u postgres "$PG_BIN_DIR/pg_ctl" -D database/data/postgresql status > /dev/null 2>&1; then
        echo "PostgreSQL started successfully"
    else
        echo "Error: PostgreSQL failed to start, check database/logs/postgresql.log"
        echo "Or run debug script: ./deployment/local/debug_permissions.sh"
        exit 1
    fi
fi

# Start backend API in background
echo "Starting backend API..."
export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/config:$PYTHONPATH"
cd backend/api && nohup python3 start.py > "$PROJECT_ROOT/log/backend.log" 2>&1 &
BACKEND_PID=$!
cd "$PROJECT_ROOT"

# Start frontend in background
echo "Starting frontend..."
cd frontend && nohup npm start > "$PROJECT_ROOT/log/frontend.log" 2>&1 &
FRONTEND_PID=$!
cd "$PROJECT_ROOT"

# Save process IDs for stopping
echo "$BACKEND_PID" > log/backend.pid
echo "$FRONTEND_PID" > log/frontend.pid

echo "System started in background!"
echo ""
echo "=== Access URLs ==="
echo "Frontend (Local):   http://localhost:3001"
echo "Frontend (Network): http://$CURRENT_IP:3001"
echo "API (Local):        http://127.0.0.1:8001/docs"
echo "API (Network):      http://$CURRENT_IP:8001/docs"
echo "WebSocket:          ws://$CURRENT_IP:8001"
echo "=================="
echo ""
echo "Process logs:"
echo "  Backend: log/backend.log"
echo "  Frontend: log/frontend.log"
echo "  Database: database/logs/postgresql.log"
echo ""
echo "To stop the system: ./stop_system.sh"
echo "To check status: ps aux | grep -E '(python.*start\.py|npm.*start)'"
echo ""
echo "NOTE: Use Network URLs to access from other devices on the same network"
EOF

    # Create stop script
    cat > stop_system.sh << 'EOF'
#!/bin/bash
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "Stopping IoT Device Monitor system..."

# Function to safely kill processes
safe_kill() {
    local pids=$1
    local service_name=$2
    
    if [ -n "$pids" ]; then
        echo "Stopping $service_name processes: $pids"
        echo "$pids" | xargs kill -TERM 2>/dev/null || true
        sleep 3
        # Check if still running and force kill
        local still_running=""
        for pid in $pids; do
            if kill -0 "$pid" 2>/dev/null; then
                still_running="$still_running $pid"
            fi
        done
        if [ -n "$still_running" ]; then
            echo "Force killing remaining $service_name processes: $still_running"
            echo "$still_running" | xargs kill -9 2>/dev/null || true
        fi
    else
        echo "No $service_name processes found"
    fi
}

# Stop backend using PID file
echo "1. Stopping backend services..."
if [ -f "log/backend.pid" ]; then
    BACKEND_PID=$(cat log/backend.pid)
    if kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo "Stopping backend (PID: $BACKEND_PID)..."
        safe_kill "$BACKEND_PID" "backend"
    fi
    rm -f log/backend.pid
fi

# Fallback: Stop all Python API processes
PYTHON_PIDS=$(pgrep -f "python.*start\.py" 2>/dev/null || true)
PYTHON_PIDS="$PYTHON_PIDS $(pgrep -f "python.*app\.py" 2>/dev/null || true)"
PYTHON_PIDS="$PYTHON_PIDS $(pgrep -f "uvicorn.*app" 2>/dev/null || true)"
safe_kill "$PYTHON_PIDS" "Python API"

# Stop frontend using PID file  
echo "2. Stopping frontend services..."
if [ -f "log/frontend.pid" ]; then
    FRONTEND_PID=$(cat log/frontend.pid)
    if kill -0 "$FRONTEND_PID" 2>/dev/null; then
        echo "Stopping frontend (PID: $FRONTEND_PID)..."
        safe_kill "$FRONTEND_PID" "frontend"
    fi
    rm -f log/frontend.pid
fi

# Fallback: Stop all Node.js processes
NODE_PIDS=$(pgrep -f "npm.*start" 2>/dev/null || true)
NODE_PIDS="$NODE_PIDS $(pgrep -f "next.*start" 2>/dev/null || true)"
NODE_PIDS="$NODE_PIDS $(pgrep -f "node.*server" 2>/dev/null || true)"
safe_kill "$NODE_PIDS" "Node.js"

# Stop database
echo "3. Stopping PostgreSQL..."
PG_BIN_DIR=""
for version in {16,15,14,13,12,11,10}; do
    if [ -d "/usr/lib/postgresql/$version/bin" ]; then
        PG_BIN_DIR="/usr/lib/postgresql/$version/bin"
        break
    fi
done

if [ -n "$PG_BIN_DIR" ]; then
    if [ -f "database/data/postgresql/postmaster.pid" ]; then
        echo "Stopping PostgreSQL gracefully..."
        sudo -u postgres "$PG_BIN_DIR/pg_ctl" -D database/data/postgresql stop -m fast 2>/dev/null || true
        sleep 2
    fi
    # Force stop any remaining PostgreSQL processes
    POSTGRES_PIDS=$(pgrep -f "postgres" 2>/dev/null || true)
    if [ -n "$POSTGRES_PIDS" ]; then
        echo "Force stopping remaining PostgreSQL processes..."
        safe_kill "$POSTGRES_PIDS" "PostgreSQL"
    fi
else
    echo "Warning: PostgreSQL binary directory not found"
    # Try to stop PostgreSQL processes anyway
    POSTGRES_PIDS=$(pgrep -f "postgres" 2>/dev/null || true)
    safe_kill "$POSTGRES_PIDS" "PostgreSQL"
fi

# Clean up occupied ports
echo "4. Cleaning up occupied ports..."
for port in 5433 8001 3001; do
    PORT_PIDS=$(lsof -ti :$port 2>/dev/null || true)
    if [ -n "$PORT_PIDS" ]; then
        echo "Cleaning up port $port..."
        safe_kill "$PORT_PIDS" "port $port"
    fi
done

# Clean up log file handlers (optional)
echo "5. Log file cleanup..."
read -p "Do you want to clear log files? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Clearing log files..."
    > log/api.log 2>/dev/null || true
    > log/backend.log 2>/dev/null || true
    > log/frontend.log 2>/dev/null || true
    > database/logs/postgresql.log 2>/dev/null || true
    echo "Log files cleared"
else
    echo "Log files preserved"
fi

echo ""
echo "System stopped successfully!"
echo "=================================="
echo ""
echo "All services have been stopped."
echo "To restart: ./start_system.sh"
echo "To check status: ps aux | grep -E '(python.*start\.py|npm.*start|postgres)'"
echo ""
EOF

    chmod +x start_system.sh stop_system.sh
    log_success "Startup scripts created"
}

# Step 13: Verify deployment
verify_deployment() {
    log_info "[13/13] Step 13: Verify deployment..."
    
    # Verify critical files
    [ -f "database/data/postgresql/PG_VERSION" ] && log_success "✓ PostgreSQL data directory"
    [ -d "frontend/node_modules" ] && log_success "✓ Frontend dependencies"
    [ -d "frontend/.next" ] && log_success "✓ Frontend build files"
    [ -f "config/user_config.json" ] && log_success "✓ Configuration file"
    
    # Verify PostgreSQL is running
    if sudo -u postgres "$PG_BIN_DIR/pg_ctl" -D database/data/postgresql status > /dev/null 2>&1; then
        log_success "✓ PostgreSQL server is running"
    else
        log_error "✗ PostgreSQL server is not running"
        return 1
    fi
    
    # Verify database connection
    if sudo -u postgres "$PG_BIN_DIR/psql" -h localhost -p 5433 -U iot_user -d iot_monitor \
        -c "SELECT 1;" > /dev/null 2>&1; then
        log_success "✓ Database connection"
    else
        log_error "✗ Database connection failed"
        return 1
    fi
    
    # Verify PostgreSQL data directory permissions
    local pg_perms=$(stat -c "%a" database/data/postgresql/)
    if [ "$pg_perms" = "700" ]; then
        log_success "✓ PostgreSQL data directory has correct 700 permissions"
    else
        log_warn "⚠ PostgreSQL data directory has $pg_perms permissions (should be 700)"
    fi
    
    # Verify database tables exist
    local table_count=$(sudo -u postgres "$PG_BIN_DIR/psql" -h localhost -p 5433 -U iot_user -d iot_monitor \
        -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ')
    
    if [ "$table_count" -gt 0 ]; then
        log_success "✓ Database schema loaded ($table_count tables)"
    else
        log_error "✗ No database tables found"
        return 1
    fi
    
    log_success "Deployment verification completed successfully"
}

# Show deployment results with dynamic IP information
show_results() {
    echo ""
    log_success "==========================================="
    log_success "IoT Device Monitor system deployment completed!"
    log_success "==========================================="
    echo ""
    
    # Get final IP address for display
    local FINAL_IP=$(get_deployment_server_ip)
    
    log_success "DYNAMIC IP CONFIGURATION COMPLETE"
    log_info "Detected Server IP: $FINAL_IP"
    echo ""
    
    log_info "Access addresses:"
    log_info "  Frontend (Local):   http://localhost:3001"
    log_info "  Frontend (Network): http://$FINAL_IP:3001"
    log_info "  API (Local):        http://127.0.0.1:8001/docs"
    log_info "  API (Network):      http://$FINAL_IP:8001/docs"
    log_info "  WebSocket:          ws://$FINAL_IP:8001"
    echo ""
    
    log_info "Management commands:"
    log_info "  Start system: ./start_system.sh"
    log_info "  Stop system: ./stop_system.sh"
    echo ""
    
    log_info "System information:"
    log_info "  Project path: $PROJECT_ROOT"
    log_info "  Database port: 5433"
    log_info "  API port: 8001"
    log_info "  Frontend port: 3001"
    log_info "  Dynamic IP support: ENABLED"
    echo ""
    
    log_success "IMPORTANT NOTES:"
    log_success "• System automatically detects IP changes"
    log_success "• Use Network URLs to access from other devices"
    log_success "• WebSocket will automatically reconnect on IP changes"
    log_success "• No manual configuration needed for IP changes"
    echo ""
    
    echo "=== IoT Device Monitor system deployment completed $(date) ===" >> "$DEPLOY_LOG"
}

# Main function
main() {
    cd "$(dirname "$0")"
    
    echo "========================================="
    echo "IoT Device Monitor - Local Deployment"
    echo "========================================="
    echo ""
    log_info "Starting deployment process..."
    log_info "This process will install and configure all required components"
    log_info "Installation progress will be shown in real-time"
    log_info "Complete logs will be saved to the deployment log file"
    log_info ""
    log_info "Deployment options:"
    log_info "  - System upgrade: DISABLED by default (recommended for stable deployment)"
    log_info "  - Force system upgrade: ENABLE_UPGRADE=1 ./local_deploy.sh (use with caution)"
    log_info "  - Debug mode: DEBUG=1 ./local_deploy.sh"
    log_info "  - System upgrade is not required for IoT dashboard functionality"
    log_info "  - Script auto-handles interactive prompts and dependency installation"
    log_info "  - Check log file for detailed error information"
    echo ""
    
    # Execute all steps in order
    check_environment                 # Step 1: Environment check
    install_system_dependencies      # Step 2: System dependencies installation
    install_nodejs                  # Step 3: Node.js installation
    install_python_dependencies     # Step 4: Python dependencies installation
    install_frontend_dependencies   # Step 5: Frontend dependencies installation
    cleanup_services                # Step 6: Cleanup existing services
    create_directories              # Step 7: Create directory structure
    configure_postgresql            # Step 8: Configure PostgreSQL
    create_config                   # Step 9: Create configuration file
    setup_database                  # Step 10: Start database and initialize
    import_reference_data           # Step 11: Import reference data
    create_startup_scripts          # Step 12: Create startup scripts
    verify_deployment               # Step 13: Verify deployment
    show_results                    # Show results
}

# Execute main function
main "$@"
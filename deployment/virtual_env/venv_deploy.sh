#!/bin/bash

echo "IoT Device Monitor - System Deployment Script"
echo "======================================="
echo "This script will complete all environment configurations, only need to run once"
echo ""

# Get the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "Project Path: $PROJECT_ROOT"

# Check operating system
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    else
        echo "unknown"
    fi
}

OS_TYPE=$(detect_os)
echo "Operating System: $OS_TYPE"

# Set error handling
set -e
trap 'echo " Error occurred during deployment, please check the logs above"; exit 1' ERR

echo ""
echo "Step 1: System Dependencies Check and Installation"
echo "=================================="

# Check and install Python3
if ! command -v python3 &> /dev/null; then
    echo "Python3 is not installed"
    if [[ "$OS_TYPE" == "linux" ]]; then
        echo "Installing Python3..."
        sudo apt update
        sudo apt install -y python3 python3-pip python3-venv python3-dev
    elif [[ "$OS_TYPE" == "macos" ]]; then
        echo "Please install Python3: brew install python3"
        exit 1
    fi
else
    echo "Python3: $(python3 --version)"
fi

# Check and install Node.js
if ! command -v node &> /dev/null; then
    echo "Node.js is not installed"
    if [[ "$OS_TYPE" == "linux" ]]; then
        echo "Installing Node.js..."
        curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
        sudo apt-get install -y nodejs
    elif [[ "$OS_TYPE" == "macos" ]]; then
        echo "Please install Node.js: brew install node"
        exit 1
    fi
else
    echo "Node.js: $(node --version)"
fi

# Check and install PostgreSQL
if ! command -v psql &> /dev/null; then
    echo "PostgreSQL is not installed"
    if [[ "$OS_TYPE" == "linux" ]]; then
        echo "Installing PostgreSQL..."
        sudo apt install -y postgresql postgresql-contrib postgresql-client
        sudo systemctl stop postgresql
        sudo systemctl disable postgresql
    elif [[ "$OS_TYPE" == "macos" ]]; then
        echo "Please install PostgreSQL: brew install postgresql"
        exit 1
    fi
else
    echo "PostgreSQL: $(psql --version | head -1)"
fi

# Check and install system-level dependencies
if [[ "$OS_TYPE" == "linux" ]]; then
    echo "Installing system-level dependencies..."
    sudo apt install -y \
        build-essential \
        libpq-dev \
        libssl-dev \
        libffi-dev \
        curl \
        wget \
        unzip \
        git
fi

echo ""
echo "Step 2: Python Virtual Environment Configuration"
echo "=================================="

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
else
    echo "Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo "Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "requirements.txt does not exist"
    exit 1
fi

# Install additional necessary packages
echo "Installing additional dependencies..."
pip install watchdog psutil

echo ""
echo "Step 3: Directory Structure and Permission Configuration"
echo "=================================="

# Create necessary directories
echo "Creating project directories..."
mkdir -p log
mkdir -p pcap_input
mkdir -p database/data/postgresql
mkdir -p database/logs
mkdir -p database/run
mkdir -p database/backups

# Set directory permissions
if [[ "$OS_TYPE" == "linux" ]]; then
    echo "Setting directory permissions..."
    chmod -R 755 log/
    chmod -R 755 pcap_input/
    chmod -R 755 database/
    chmod 700 database/data/postgresql/
    chmod 755 database/run/
    
    # Ensure current user owns all files
    chown -R $(whoami):$(whoami) log/ pcap_input/ database/
fi

# Create necessary log files
touch log/api.log
touch log/frontend.log
touch log/file_monitor.log

# Set log file permissions
chmod 664 log/*.log

echo ""
echo "Step 4: PostgreSQL Configuration"
echo "=================================="

# Stop any running PostgreSQL processes
echo "Stopping existing PostgreSQL processes..."
if [[ "$OS_TYPE" == "linux" ]]; then
    sudo systemctl stop postgresql 2>/dev/null || true
    sudo pkill -f postgres 2>/dev/null || true
elif [[ "$OS_TYPE" == "macos" ]]; then
    brew services stop postgresql 2>/dev/null || true
    pkill -f postgres 2>/dev/null || true
fi
sleep 2

# Clean up and recreate data directory (solve Linux environment issues)
echo "Preparing PostgreSQL data directory..."
if [[ "$OS_TYPE" == "linux" ]]; then
    # Linux environment special handling
    if [ -d "database/data/postgresql" ]; then
        echo "Cleaning up existing data directory..."
        rm -rf database/data/postgresql/*
    fi
    mkdir -p database/data/postgresql
    # Ensure current user owns directory
    sudo chown -R $(whoami):$(whoami) database/data/postgresql
    chmod 700 database/data/postgresql
fi

# Initialize PostgreSQL data directory
echo "Initializing PostgreSQL data directory..."
if [[ "$OS_TYPE" == "linux" ]]; then
    # Linux environment using full path and specific parameters
    INITDB_CMD="/usr/lib/postgresql/14/bin/initdb"
    if [ ! -f "$INITDB_CMD" ]; then
        # Try to find PostgreSQL binary file
        INITDB_CMD=$(find /usr/lib/postgresql -name "initdb" | head -1)
    fi
    
    if [ -n "$INITDB_CMD" ]; then
        echo "Using $INITDB_CMD to initialize database..."
        $INITDB_CMD -D database/data/postgresql -U postgres --locale=C.UTF-8 --encoding=UTF8 --auth-local=trust --auth-host=md5
    else
        echo "Cannot find initdb command"
        exit 1
    fi
elif [[ "$OS_TYPE" == "macos" ]]; then
    initdb -D database/data/postgresql --auth-local=trust --auth-host=md5
fi

# Verify initialization success
if [ ! -f "database/data/postgresql/PG_VERSION" ]; then
    echo " PostgreSQL data directory initialization failed"
    echo "Check directory content:"
    ls -la database/data/postgresql/
    exit 1
fi

echo "PostgreSQL data directory initialization successful"

# Create PostgreSQL configuration file
echo "Configuring PostgreSQL..."
cat > database/data/postgresql/postgresql.conf << EOF
# PostgreSQL Configuration for IoT Device Monitor
listen_addresses = 'localhost'
port = 5433
max_connections = 50

# Socket Configuration  
unix_socket_directories = '$PROJECT_ROOT/database/run'

# Logging
logging_collector = on
log_directory = 'log'
log_filename = 'postgresql.log'
log_statement = 'none'
log_min_messages = warning

# Memory
shared_buffers = 128MB
work_mem = 4MB

# Storage
checkpoint_completion_target = 0.7
wal_buffers = 16MB
default_statistics_target = 100
EOF

# Create access control configuration
cat > database/data/postgresql/pg_hba.conf << EOF
# PostgreSQL Access Control for IoT Device Monitor
# TYPE  DATABASE        USER            ADDRESS                 METHOD
local   all             all                                     trust
host    all             all             127.0.0.1/32            trust
host    all             all             ::1/128                 trust
host    all             all             localhost               trust
EOF

# Set correct permissions
if [[ "$OS_TYPE" == "linux" ]]; then
    sudo chown -R $(whoami):$(whoami) database/
    chmod 700 database/data/postgresql
    chmod 600 database/data/postgresql/postgresql.conf
    chmod 600 database/data/postgresql/pg_hba.conf
fi

echo "PostgreSQL configuration completed"

echo ""
echo "Step 5: Frontend Dependency Installation and Build"
echo "=================================="

cd frontend
if [ ! -d "node_modules" ]; then
    echo "Installing Frontend dependencies..."
    npm install
else
    echo "Frontend dependencies already installed"
fi

# 构建生产版本
echo "Building Frontend production version..."
if [ ! -d ".next" ] || [ ! -f ".next/BUILD_ID" ]; then
    echo "Starting build..."
    npm run build
    if [ $? -eq 0 ]; then
        echo "Frontend build successful"
    else
        echo "Frontend build failed"
        exit 1
    fi
else
    echo "Frontend already built"
fi
cd ..

echo ""
echo "Step 6: Configuration File Adjustment"
echo "=================================="

# Ensure configuration file exists and is correctly configured
if [ ! -f "config/user_config.json" ]; then
    echo "Creating user configuration file..."
    cat > config/user_config.json << EOF
{
  "environment": "production",
  "database": {
    "host": "localhost",
    "port": 5433,
    "user": "iot_user",
    "password": "iot_password",
    "database": "iot_monitor"
  },
  "api": {
    "host": "127.0.0.1",
    "port": 8001
  },
  "frontend": {
    "host": "localhost",
    "port": 3001
  },
  "file_monitor": {
    "enabled": true,
    "scan_times": ["06:00", "12:00", "18:00", "23:59"],
    "directories": ["pcap_input"],
    "logging": {
      "log_level": "INFO",
      "log_file": "log/file_monitor.log"
    }
  }
}
EOF
fi

echo ""
echo "Step 7: Database Initialization"
echo "=================================="

# Start PostgreSQL for initialization
echo "Starting PostgreSQL for initialization..."
if [[ "$OS_TYPE" == "linux" ]]; then
    # Linux environment using full path
    PG_CTL_CMD="/usr/lib/postgresql/14/bin/pg_ctl"
    if [ ! -f "$PG_CTL_CMD" ]; then
        PG_CTL_CMD=$(find /usr/lib/postgresql -name "pg_ctl" | head -1)
    fi
    
    if [ -n "$PG_CTL_CMD" ]; then
        echo "Using $PG_CTL_CMD to start PostgreSQL..."
        $PG_CTL_CMD -D database/data/postgresql -l database/logs/postgresql.log -o "-p 5433" start
    else
        echo "Cannot find pg_ctl command"
        exit 1
    fi
elif [[ "$OS_TYPE" == "macos" ]]; then
    pg_ctl -D database/data/postgresql -l database/logs/postgresql.log -o "-p 5433" start
fi

# Wait for PostgreSQL to start
echo "Waiting for PostgreSQL to start..."
sleep 5

# Verify PostgreSQL startup status
if [[ "$OS_TYPE" == "linux" ]]; then
    if ! $PG_CTL_CMD -D database/data/postgresql status > /dev/null 2>&1; then
        echo "PostgreSQL startup failed"
        echo "Check log:"
        cat database/logs/postgresql.log
        exit 1
    fi
fi

echo "PostgreSQL startup successful"

# Create user and database
echo "Creating database user and database..."

# Set environment variables
export PGPORT=5433
export PGHOST=localhost

# Create database
if [[ "$OS_TYPE" == "linux" ]]; then
    CREATEDB_CMD="/usr/lib/postgresql/14/bin/createdb"
    PSQL_CMD="/usr/lib/postgresql/14/bin/psql"
    CREATEUSER_CMD="/usr/lib/postgresql/14/bin/createuser"
    
    # Try to find commands
    [ ! -f "$CREATEDB_CMD" ] && CREATEDB_CMD=$(find /usr/lib/postgresql -name "createdb" | head -1)
    [ ! -f "$PSQL_CMD" ] && PSQL_CMD=$(find /usr/lib/postgresql -name "psql" | head -1)
    [ ! -f "$CREATEUSER_CMD" ] && CREATEUSER_CMD=$(find /usr/lib/postgresql -name "createuser" | head -1)
elif [[ "$OS_TYPE" == "macos" ]]; then
    CREATEDB_CMD="createdb"
    PSQL_CMD="psql"
    CREATEUSER_CMD="createuser"
fi

# Create user and database
$CREATEUSER_CMD -h localhost -p 5433 -U postgres -s iot_user 2>/dev/null || echo "User may already exist"
$CREATEDB_CMD -h localhost -p 5433 -U postgres -O iot_user iot_monitor 2>/dev/null || echo "Database may already exist"

# Set user password
$PSQL_CMD -h localhost -p 5433 -U postgres -d postgres -c "ALTER USER iot_user PASSWORD 'iot_password';" 2>/dev/null || true

# Test database connection
echo "Testing database connection..."
if $PSQL_CMD -h localhost -p 5433 -U iot_user -d iot_monitor -c "SELECT version();" > /dev/null 2>&1; then
    echo "Database connection test successful"
else
    echo "Database connection test failed"
    # Display detailed information for debugging
    echo "Connection information: postgresql://iot_user:iot_password@localhost:5433/iot_monitor"
fi

# Initialize database schema
echo "Initializing database schema..."
for sql_file in database/schema/*.sql; do
    if [ -f "$sql_file" ]; then
        echo "Loading $(basename "$sql_file")..."
        $PSQL_CMD -h localhost -p 5433 -U iot_user -d iot_monitor -f "$sql_file" > /dev/null 2>&1 || true
    fi
done

# Import reference data (if exists)
echo "Importing reference data..."
if [ -d "reference_backup/export_data" ] && [ -f "reference_backup/export_data/export_summary.json" ]; then
    echo "Found reference data backup, starting import..."
    if python3 utils/import_reference_data.py --no-clear > /dev/null 2>&1; then
        echo "Reference data import successful"
        
        # Display import statistics
        VENDOR_COUNT=$($PSQL_CMD -h localhost -p 5433 -U iot_user -d iot_monitor -t -c "SELECT COUNT(*) FROM vendor_patterns;" 2>/dev/null | tr -d ' ')
        DEVICE_COUNT=$($PSQL_CMD -h localhost -p 5433 -U iot_user -d iot_monitor -t -c "SELECT COUNT(*) FROM known_devices;" 2>/dev/null | tr -d ' ')
        IP_COUNT=$($PSQL_CMD -h localhost -p 5433 -U iot_user -d iot_monitor -t -c "SELECT COUNT(*) FROM ip_geolocation_ref;" 2>/dev/null | tr -d ' ')
        
        echo "Import statistics:"
        echo "     - Vendor patterns: ${VENDOR_COUNT:-0}"
        echo "     - Known devices: ${DEVICE_COUNT:-0}"
        echo "     - IP geolocation: ${IP_COUNT:-0}"
    else
        echo "Reference data import failed, continuing deployment..."
    fi
else
    echo "No reference data backup found, skipping import"
    echo "If you need to import, please run: python utils/export_reference_data.py"
fi

# Stop PostgreSQL
echo "Stopping temporary PostgreSQL instance..."
if [[ "$OS_TYPE" == "linux" ]]; then
    $PG_CTL_CMD -D database/data/postgresql stop
elif [[ "$OS_TYPE" == "macos" ]]; then
    pg_ctl -D database/data/postgresql stop
fi

echo "Database initialization completed"

echo ""
echo "Step 8: Cleaning Temporary Files"
echo "=================================="

# Create .gitignore to ensure temporary files are not committed
cat >> .gitignore << EOF

# Generated temporary files
*.tmp
*.temp
.deployment_lock
EOF

echo ""
echo "Step 9: Verifying Deployment"
echo "=================================="

# Verify critical files exist
echo "Verifying critical files..."
[ -d "venv" ] && echo "Python virtual environment" || echo " Python virtual environment"
[ -f "database/data/postgresql/PG_VERSION" ] && echo "PostgreSQL data directory" || echo " PostgreSQL data directory"
[ -d "frontend/node_modules" ] && echo "Frontend dependencies" || echo " Frontend dependencies"
[ -f "config/user_config.json" ] && echo "Configuration file" || echo " Configuration file"

echo ""
echo "Deployment completed!"
echo "======================================="
echo ""
echo "Next steps:"
echo "   1. Run start script: ./utils/start_system.sh"
echo "   2. Access system: http://localhost:3001"
echo "   3. API documentation: http://127.0.0.1:8001/docs"
echo ""
echo "Management commands:"
echo "   Start system: ./utils/start_system.sh"
echo "   Stop system: ./utils/stop_system.sh"
echo ""
echo "Deployment information:"
echo "   - Database port: 5433"
echo "   - API port: 8001"
echo "   - Frontend port: 3001"
echo "   - Log directory: log/"
echo ""
echo "Reference data management:"
echo "    Export data: python utils/export_reference_data.py"
echo "    Import data: python utils/import_reference_data.py"
echo "    Quick operation: python utils/quick_reference_setup.py help"
echo ""
echo "Reference documentation:"
echo "   - System documentation: README.md"
echo "   - Data migration: docs/REFERENCE_DATA_MIGRATION_GUIDE.md"
echo "   - Tool description: utils/README_REFERENCE_DATA_TOOLS.md"
echo ""
echo "Note: This deployment script only needs to be run once, after which the start script can be used" 
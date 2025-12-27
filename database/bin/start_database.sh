#!/bin/bash
# PostgreSQL Database Startup Script for IoT Device Monitor
# This script starts the project-local PostgreSQL instance

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DATABASE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Read configuration from user_config.json
CONFIG_FILE="$PROJECT_ROOT/config/user_config.json"
if [ -f "$CONFIG_FILE" ]; then
    # Extract port and data directory from config
    PORT=$(python3 -c "
import json
try:
    with open('$CONFIG_FILE', 'r') as f:
        config = json.load(f)
    print(config.get('system_architecture', {}).get('ports', {}).get('database', {}).get('port', 5433))
except:
    print(5433)
")
    DB_DATA_DIR=$(cd "$PROJECT_ROOT" && python -c "
import sys
import os
sys.path.insert(0, os.path.join('$PROJECT_ROOT', 'config'))
try:
    from unified_config_manager import UnifiedConfigManager
    config = UnifiedConfigManager()
    print(config.get_database_data_directory())
except:
    print('database/data')
")
    DB_HOST=$(python3 -c "
import json
try:
    with open('$CONFIG_FILE', 'r') as f:
        config = json.load(f)
    print(config.get('system_architecture', {}).get('hosts', {}).get('database', {}).get('host', 'localhost'))
except:
    print('localhost')
")
    # Convert relative path to absolute path
    if [[ "$DB_DATA_DIR" = /* ]]; then
        PGDATA="$DB_DATA_DIR/postgresql"
    else
        PGDATA="$PROJECT_ROOT/$DB_DATA_DIR/postgresql"
    fi
else
    echo "Config file not found, using default settings"
    PORT=5433
    PGDATA="$DATABASE_ROOT/data/postgresql"
    DB_HOST="localhost"
fi

LOGFILE="$DATABASE_ROOT/logs/postgresql.log"

echo "Starting IoT Device Monitor Database..."
echo "Data Directory: $PGDATA"
echo "Log File: $LOGFILE"
echo "Port: $PORT"

# Ensure log directory exists
mkdir -p "$(dirname "$LOGFILE")"

# Check if data directory exists
if [ ! -d "$PGDATA" ]; then
    echo "PostgreSQL data directory not found: $PGDATA"
    echo "Initializing new PostgreSQL instance..."
    
    # Ensure parent directory exists and has correct permissions
    mkdir -p "$(dirname "$PGDATA")"
    
    # Initialize PostgreSQL data directory
    initdb -D "$PGDATA" -U $(whoami) --auth-local=trust --auth-host=trust --encoding=UTF8 --locale=C
    
    if [ $? -eq 0 ]; then
        echo "PostgreSQL data directory initialized"
    else
        echo "Failed to initialize PostgreSQL data directory"
        exit 1
    fi
fi

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Applying Linux-specific fixes..."
    
    # Ensure data directory permissions are correct
    chmod 700 "$PGDATA"
    
    # Set Unix socket directory to project internal, avoid /var/run permission issues
    SOCKET_DIR="$DATABASE_ROOT/run"
    mkdir -p "$SOCKET_DIR"
    chmod 755 "$SOCKET_DIR"
    
    # Update PostgreSQL configuration to use project-internal socket directory
    if [ -f "$PGDATA/postgresql.conf" ]; then
        # Set socket directory to project internal
        sed -i "s|#unix_socket_directories = '/tmp'|unix_socket_directories = '$SOCKET_DIR'|" "$PGDATA/postgresql.conf" 2>/dev/null || true
        sed -i "s|unix_socket_directories = '/tmp'|unix_socket_directories = '$SOCKET_DIR'|" "$PGDATA/postgresql.conf" 2>/dev/null || true
        
        # Ensure log directory configuration is correct
        sed -i "s|#log_directory = 'log'|log_directory = '$(dirname "$LOGFILE")'|" "$PGDATA/postgresql.conf" 2>/dev/null || true
        
        # Set more lenient connection configuration
        sed -i "s|#listen_addresses = 'localhost'|listen_addresses = 'localhost'|" "$PGDATA/postgresql.conf" 2>/dev/null || true
        sed -i "s|#max_connections = 100|max_connections = 50|" "$PGDATA/postgresql.conf" 2>/dev/null || true
        
        echo "Linux PostgreSQL configuration updated"
    fi
    
    # Check and create pg_hba.conf if it doesn't exist
    if [ ! -f "$PGDATA/pg_hba.conf" ]; then
        echo "Creating pg_hba.conf..."
        cat > "$PGDATA/pg_hba.conf" << EOF
# TYPE  DATABASE        USER            ADDRESS                 METHOD
local   all             all                                     trust
host    all             all             127.0.0.1/32            trust
host    all             all             ::1/128                 trust
EOF
    fi
fi

# Update PostgreSQL configuration for custom port
echo "Configuring PostgreSQL for port $PORT..."
# Cross-platform sed command (works on both macOS and Linux)
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS requires empty string after -i
    sed -i '' "s/#port = 5432/port = $PORT/" "$PGDATA/postgresql.conf" 2>/dev/null || true
    sed -i '' "s/port = 5432/port = $PORT/" "$PGDATA/postgresql.conf" 2>/dev/null || true
else
    # Linux doesn't require empty string after -i
    sed -i "s/#port = 5432/port = $PORT/" "$PGDATA/postgresql.conf" 2>/dev/null || true
    sed -i "s/port = 5432/port = $PORT/" "$PGDATA/postgresql.conf" 2>/dev/null || true
fi

# Start PostgreSQL
if pg_ctl -D "$PGDATA" status > /dev/null 2>&1; then
    echo "PostgreSQL is already running"
else
    echo "Starting PostgreSQL..."
    pg_ctl -D "$PGDATA" -l "$LOGFILE" -o "-p $PORT" start
    
    if [ $? -eq 0 ]; then
        echo "PostgreSQL started successfully"
        echo "Connection: postgresql://$DB_HOST:$PORT/"
        sleep 2
    else
        echo "Failed to start PostgreSQL"
        exit 1
    fi
fi

# Create database and user if they don't exist
echo "Setting up database and user..."
createdb -h $DB_HOST -p $PORT -U $(whoami) iot_monitor 2>/dev/null || echo "Database 'iot_monitor' already exists"

# Create user if not exists
psql -h $DB_HOST -p $PORT -U $(whoami) -d postgres -c "
CREATE USER iot_user WITH PASSWORD 'iot_password';
GRANT ALL PRIVILEGES ON DATABASE iot_monitor TO iot_user;
ALTER USER iot_user CREATEDB;
" 2>/dev/null || echo "User 'iot_user' already configured"

# Initialize modular schema if needed
SCHEMA_DIR="$DATABASE_ROOT/schema"
echo "Checking database schema..."
TABLE_COUNT=$(psql -h $DB_HOST -p $PORT -U iot_user -d iot_monitor -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | xargs)

if [ "$TABLE_COUNT" -lt 5 ]; then
    echo "Initializing modular database schema..."
    
    # Load schema modules in correct dependency order
    SCHEMA_FILES=(
        "01_core_schema.sql"
        "02_reference_schema.sql" 
        "03_analytics_schema.sql"
        "04_geolocation_schema.sql"
        "05_functions_triggers.sql"
        "06_views_indexes.sql"
    )
    
    for SCHEMA_FILE in "${SCHEMA_FILES[@]}"; do
        SCHEMA_PATH="$SCHEMA_DIR/$SCHEMA_FILE"
        if [ -f "$SCHEMA_PATH" ]; then
            echo "   Loading $SCHEMA_FILE..."
            psql -h $DB_HOST -p $PORT -U iot_user -d iot_monitor -f "$SCHEMA_PATH"
            if [ $? -eq 0 ]; then
                echo "  $SCHEMA_FILE loaded successfully"
            else
                echo "  Failed to load $SCHEMA_FILE"
                exit 1
            fi
        else
            echo "  Schema file not found: $SCHEMA_PATH"
        fi
    done
    
    echo "Modular database schema initialized"
else
    echo "Database schema already exists ($TABLE_COUNT tables)"
fi

# Verify database connection
echo "Verifying database connection..."
if psql -h $DB_HOST -p $PORT -U iot_user -d iot_monitor -c "SELECT 1;" > /dev/null 2>&1; then
    echo "Database connection verified"
    
    # Get database statistics
    DEVICE_COUNT=$(psql -h $DB_HOST -p $PORT -U iot_user -d iot_monitor -t -c "SELECT COUNT(*) FROM devices;" 2>/dev/null | xargs)
    PACKET_COUNT=$(psql -h $DB_HOST -p $PORT -U iot_user -d iot_monitor -t -c "SELECT COUNT(*) FROM packet_flows;" 2>/dev/null | xargs)
    
    echo "Database Status:"
    echo "   - Devices: ${DEVICE_COUNT:-0}"
    echo "   - Packet Flows: ${PACKET_COUNT:-0}"
else
    echo "Database connection failed"
    exit 1
fi

echo "Project Database is ready for IoT Device Monitor!"
echo "Connection string: postgresql://iot_user:iot_password@$DB_HOST:$PORT/iot_monitor" 
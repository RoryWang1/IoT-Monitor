#!/bin/bash
set -e

# IoT Device Monitor - Docker Deployment
echo "IoT Device Monitor - Docker Deployment"
echo "=================================="
echo "Usage: ./docker_deploy.sh [SERVER_IP]"
echo ""
echo "IP address configuration (priority from high to low):"
echo "  1. Command line argument: ./docker_deploy.sh 192.168.1.100"
echo "  2. .env file: create .env file and set SERVER_IP=192.168.1.100"
echo "  3. Automatic detection: system automatically detects network interface IP"
echo ""

# Global variables
DOCKER_CMD=""
SERVER_IP=""
WS_BASE_URL=""

# Check Docker environment
check_docker() {
    if ! command -v docker >/dev/null 2>&1; then
        echo "Error: Docker is not installed"
        echo "Please install Docker: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! docker info >/dev/null 2>&1; then
        echo "Error: Docker service is not running or permission is insufficient"
        echo "Solution:"
        echo "  1. Start Docker service: sudo systemctl start docker"
        echo "  2. Add user to docker group: sudo usermod -aG docker $USER"
        echo "  3. Or run this script with sudo"
        exit 1
    fi
    
    echo "Docker environment check passed"
}

# Set Docker command
setup_docker_command() {
    if docker info >/dev/null 2>&1; then
        DOCKER_CMD="docker-compose"
    elif sudo docker info >/dev/null 2>&1; then
        DOCKER_CMD="sudo docker-compose"
        echo "Note: Running Docker with sudo permissions"
    else
        echo "Error: Unable to access Docker, please check Docker installation and permissions"
        exit 1
    fi
}

# Automatic detection of server IP
detect_server_ip() {
    local input_ip="$1"
    
    echo "Detecting server IP address..."
    
    # Priority 1: command line argument
    if [ -n "$input_ip" ]; then
        SERVER_IP="$input_ip"
        echo "Using command line argument IP: $SERVER_IP"
    # Priority 2: .env file
    elif [ -f ".env" ] && grep -q "SERVER_IP=" .env; then
        SERVER_IP=$(grep "SERVER_IP=" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'")
        echo "Using .env file IP: $SERVER_IP"
    # Priority 3: automatic detection
    else
        SERVER_IP=$(ip route get 8.8.8.8 2>/dev/null | awk '{print $7; exit}' || hostname -I | awk '{print $1}' || echo "localhost")
        echo "Automatically detected server IP: $SERVER_IP"
    fi
    
    WS_BASE_URL="ws://$SERVER_IP:8001"
    echo "WebSocket URL: $WS_BASE_URL"
}

# Manage .env file
manage_env() {
    echo "Creating .env configuration file..."
    cat > .env << EOF
SERVER_IP=$SERVER_IP
WS_BASE_URL=$WS_BASE_URL
EOF
    echo "Automatically generated .env file: SERVER_IP=$SERVER_IP"
}

# Clean up existing services
cleanup_services() {
    echo "Cleaning up existing service processes..."
    $DOCKER_CMD down >/dev/null 2>&1 || true
}

# Deploy services
deploy_services() {
    echo "Building Docker image..."
    $DOCKER_CMD build --no-cache
    
    echo "Starting services..."
    $DOCKER_CMD up -d
    
    echo "Waiting for services to start..."
    sleep 20
}

# Verify database schema
verify_database() {
    echo "Verifying database schema initialization..."
    
    for i in {1..30}; do
        if $DOCKER_CMD exec backend python -c "
import sys, asyncio
sys.path.append('/app')
from database.connection import PostgreSQLDatabaseManager

async def check_db():
    try:
        db = PostgreSQLDatabaseManager()
        await db.initialize()
        table_count = await db.execute_scalar(\"\"\"
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = 'public'
        \"\"\")
        await db.close()
        print(f'SUCCESS:{table_count}')
    except Exception as e:
        print(f'FAILED:{e}')

asyncio.run(check_db())
" 2>/dev/null | grep -q "SUCCESS"; then
            table_count=$($DOCKER_CMD exec backend python -c "
import sys, asyncio
sys.path.append('/app')
from database.connection import PostgreSQLDatabaseManager

async def get_count():
    db = PostgreSQLDatabaseManager()
    await db.initialize()
    count = await db.execute_scalar(\"\"\"
        SELECT COUNT(*) FROM information_schema.tables 
        WHERE table_schema = 'public'
    \"\"\")
    await db.close()
    print(count)

asyncio.run(get_count())
" 2>/dev/null)
            echo "✓ Database schema automatically initialized successfully, found $table_count tables"
            return 0
        fi
        
        if [ $i -eq 30 ]; then
            echo "✗ Database initialization timeout"
            return 1
        fi
        sleep 2
    done
}

# Import reference data
import_reference_data() {
    echo "========================================"
    echo "Import reference data - device mapping core functionality"
    echo "========================================"
    
    # Wait for backend container to start completely
    echo "Waiting for backend container to start..."
    for i in {1..30}; do
        if $DOCKER_CMD ps | grep -q "backend.*Up"; then
            echo "Backend container started"
            break
        fi
        if [ $i -eq 30 ]; then
            echo "Error: backend container startup timeout"
            return 1
        fi
        sleep 1
    done
    
    # Check or copy reference data files
    if ! $DOCKER_CMD exec backend test -d "/app/reference_backup/export_data" 2>/dev/null; then
        echo "No reference data files found, attempting to copy to container..."
        
        if [ -d "../../reference_backup/export_data" ]; then
            echo "Found reference data on host, copying to container..."
            
            # Create directory and copy files
            sudo docker exec iot-monitor-backend mkdir -p /app/reference_backup/export_data
            
            echo "Copying core reference files..."
            sudo docker cp ../../reference_backup/export_data/vendor_patterns.json iot-monitor-backend:/app/reference_backup/export_data/
            sudo docker cp ../../reference_backup/export_data/known_devices.json iot-monitor-backend:/app/reference_backup/export_data/
            sudo docker cp ../../reference_backup/export_data/export_summary.json iot-monitor-backend:/app/reference_backup/export_data/
            sudo docker cp ../../reference_backup/export_data/ip_geolocation_ref_index.json iot-monitor-backend:/app/reference_backup/export_data/
            
            echo "Copying IP geolocation data files..."
            for part_file in ../../reference_backup/export_data/ip_geolocation_ref_part_*.json; do
                if [ -f "$part_file" ]; then
                    sudo docker cp "$part_file" iot-monitor-backend:/app/reference_backup/export_data/
                fi
            done
            echo "Reference data copied successfully"
        else
            echo "Error: reference data directory not found"
            echo "Please ensure ../../reference_backup/export_data directory exists"
            return 1
        fi
    fi
    
    # Wait for database to be fully ready
    echo "Waiting for database to be ready..."
    for i in {1..20}; do
        if $DOCKER_CMD exec backend python -c "
import sys, asyncio
sys.path.append('/app')
from database.connection import PostgreSQLDatabaseManager

async def test_db():
    try:
        db = PostgreSQLDatabaseManager()
        await db.initialize()
        await db.execute_scalar('SELECT 1')
        await db.close()
        print('SUCCESS')
    except:
        print('FAILED')

asyncio.run(test_db())
" 2>/dev/null | grep -q "SUCCESS"; then
            echo "Database connection successful"
            break
        fi
        if [ $i -eq 20 ]; then
            echo "Error: database connection timeout"
            return 1
        fi
        sleep 3
    done
    
    # Execute import
    echo "Starting to import reference data..."
    if $DOCKER_CMD exec backend python /app/utils/import_reference_data.py --no-clear; then
        echo "Reference data import completed successfully!"
        return 0
    else
        echo "Reference data import failed"
        return 1
    fi
}

# Verify deployment
verify_deployment() {
    echo ""
    echo "Executing deployment verification..."
    echo "Verifying service status:"
    $DOCKER_CMD ps
    
    # Simple service check
    echo ""
    echo "Checking core services..."
    
    # Database check
    if $DOCKER_CMD ps | grep -q "database.*Up"; then
        echo "✓ Database service: running"
        db_ok=true
    else
        echo "✗ Database service: abnormal"
        db_ok=false
    fi
    
    # API check
    if $DOCKER_CMD ps | grep -q "backend.*Up"; then
        echo "✓ API backend service: running"
        api_ok=true
    else
        echo "✗ API backend service: abnormal"
        api_ok=false
    fi
    
    # Frontend check
    if $DOCKER_CMD ps | grep -q "frontend.*Up"; then
        echo "✓ Frontend interface: running"
        frontend_ok=true
    else
        echo "✗ Frontend interface: abnormal"
        frontend_ok=false
    fi
    
    # Start WebSocket broadcast service
    echo ""
    echo "Starting WebSocket broadcast service..."
    $DOCKER_CMD exec backend python -c "
import sys, asyncio
sys.path.append('/app')
from backend.api.services.broadcast_service import broadcast_service

async def start_broadcast():
    try:
        await broadcast_service.start_device_monitoring()
        if broadcast_service.is_running():
            print('Broadcast service started successfully')
        else:
            print('Broadcast service startup failed')
    except Exception as e:
        print(f'Broadcast service startup failed: {e}')

asyncio.run(start_broadcast())
" 2>/dev/null || echo "Broadcast service startup failed"
    
    return 0
}

# Show deployment result
show_result() {
    echo ""
    echo "IoT Device Monitor deployment successful!"
    echo "Frontend access address: http://$SERVER_IP:3001"
    echo "API documentation address: http://$SERVER_IP:8001/docs"
    echo ""
    echo "Deployment completed!"
    echo "=================================="
    echo "Access address:"
    echo "  Frontend interface: http://$SERVER_IP:3001"
    echo "  API documentation: http://$SERVER_IP:8001/docs"
    echo "  Local access: http://localhost:3001 (if running locally)"
    echo ""
    echo "Management commands:"
    echo "  View logs: $DOCKER_CMD logs -f"
    echo "  Stop service: $DOCKER_CMD down"
    echo "  Restart service: $DOCKER_CMD restart"
    echo ""
    echo "Configuration information:"
    echo "  Current server IP: $SERVER_IP"
    echo "  WebSocket address: $WS_BASE_URL"
    echo "  Configuration file: .env (already exists)"
    echo ""
    echo "To stop the service, run: $DOCKER_CMD down"
}

# Main function
main() {
    cd "$(dirname "$0")"
    
    check_docker
    setup_docker_command
    detect_server_ip "$1"
    manage_env
    cleanup_services
    deploy_services
    verify_database
    import_reference_data
    verify_deployment
    show_result
}

# Execute main function
main "$@" 
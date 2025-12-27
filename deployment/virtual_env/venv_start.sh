#!/bin/bash

echo "IoT Device Monitor - Virtual Environment startup"
echo "=================================="

# Get project root directory (adjusted for new location)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

# Detect operating system
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

# Clean up existing service processes
echo "Cleaning up existing service processes..."
pkill -f "python.*start.py" 2>/dev/null || true
pkill -f "npm.*start" 2>/dev/null || true
pkill -f "next.*start" 2>/dev/null || true
pkill -f "node.*server" 2>/dev/null || true

# Clean up occupied ports
for port in 5433 8001 3001; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "Port $port is occupied, cleaning up..."
        lsof -Pi :$port -sTCP:LISTEN -t | xargs kill -9 2>/dev/null || true
    fi
done

echo ""
echo "1. Start database service"
echo "=================================="

# Start PostgreSQL
echo "Starting PostgreSQL..."
if [[ "$OS_TYPE" == "linux" ]]; then
    /usr/lib/postgresql/*/bin/pg_ctl -D database/data/postgresql -l database/logs/postgresql.log start
elif [[ "$OS_TYPE" == "macos" ]]; then
    pg_ctl -D database/data/postgresql -l database/logs/postgresql.log start
fi

# Wait for database to start
echo "Waiting for database to start..."
sleep 3

# Verify database connection
if psql -h localhost -p 5433 -U iot_user -d iot_monitor -c "SELECT 1;" >/dev/null 2>&1; then
    echo "Database started successfully"
else
    echo "Database failed to start"
    exit 1
fi

echo ""
echo "2. Start API service"
echo "=================================="

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment and start API
echo "Starting API service..."
cd backend/api
source ../../venv/bin/activate
export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/config:$PYTHONPATH"

# Install dependencies if requirements.txt is newer than venv
if [ "../../requirements.txt" -nt "../../venv/pyvenv.cfg" ]; then
    echo "Installing/updating Python dependencies..."
    pip install -r ../../requirements.txt
fi

# Start API service in background
nohup python start.py > ../../log/api.log 2>&1 &
API_PID=$!
echo "API service PID: $API_PID"

# Wait for API service to start
echo "Waiting for API service to start..."
for i in {1..30}; do
    if curl -s http://127.0.0.1:8001/api/experiments >/dev/null 2>&1; then
        echo "API service started successfully"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "API service timed out"
        exit 1
    fi
    sleep 1
done

cd "$PROJECT_ROOT"

echo ""
echo "3. Start frontend service"
echo "=================================="

# Start frontend service
echo "Starting frontend service..."
cd frontend

# Install frontend dependencies if needed
if [ ! -d "node_modules" ] || [ "package.json" -nt "node_modules/.package-lock.json" ]; then
    echo "Installing/updating frontend dependencies..."
    npm install
fi

nohup npm start > ../log/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend service PID: $FRONTEND_PID"

# Wait for frontend service to start
echo "Waiting for frontend service to start..."
for i in {1..30}; do
    if curl -s http://localhost:3001 >/dev/null 2>&1; then
        echo "Frontend service started successfully"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "Frontend service timed out"
        exit 1
    fi
    sleep 1
done

cd "$PROJECT_ROOT"

echo ""
echo "4. Verify service status"
echo "=================================="

# Verify File Monitor service
echo "Checking File Monitor service..."
if curl -s http://127.0.0.1:8001/api/admin/file-monitor/status >/dev/null 2>&1; then
    echo "File Monitor service is running normally"
else
    echo "File Monitor service status unknown"
fi

echo ""
echo "System startup completed!"
echo "=================================="
echo ""
echo "Access address:"
echo "   Main page: http://localhost:3001"
echo "   API documentation: http://127.0.0.1:8001/docs"
echo ""
echo "Service status:"
echo "   Database: PostgreSQL (port 5433)"
echo "   API service: http://127.0.0.1:8001 (PID: $API_PID)"
echo "   Frontend service: http://localhost:3001 (PID: $FRONTEND_PID)"
echo ""
echo "To stop services, run: ./deployment/venv/venv_stop.sh"
echo ""
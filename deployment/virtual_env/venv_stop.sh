#!/bin/bash

echo "IoT Device Monitor - Virtual Environment shutdown"
echo "=================================="

# Get project root directory (adjusted for new location)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

# Function to safely kill processes
safe_kill() {
    local pids=$1
    local service_name=$2
    
    if [ -n "$pids" ]; then
        echo "Stopping $service_name processes: $pids"
        echo "$pids" | xargs kill -TERM 2>/dev/null || true
        sleep 2
        # Force kill if still running
        echo "$pids" | xargs kill -9 2>/dev/null || true
    else
        echo "No $service_name processes found"
    fi
}

echo "Stopping IoT Device Monitor services..."

# Stop frontend services
echo ""
echo "1. Stopping frontend services"
echo "=================================="
FRONTEND_PIDS=$(pgrep -f "npm.*start" 2>/dev/null || true)
FRONTEND_PIDS="$FRONTEND_PIDS $(pgrep -f "next.*start" 2>/dev/null || true)"
FRONTEND_PIDS="$FRONTEND_PIDS $(pgrep -f "node.*server" 2>/dev/null || true)"
safe_kill "$FRONTEND_PIDS" "frontend"

# Stop API services
echo ""
echo "2. Stopping API services"
echo "=================================="
API_PIDS=$(pgrep -f "python.*start.py" 2>/dev/null || true)
safe_kill "$API_PIDS" "API"

# Stop database services
echo ""
echo "3. Stopping database services"
echo "=================================="
echo "Stopping PostgreSQL..."

# Try to stop PostgreSQL gracefully
if command -v pg_ctl &> /dev/null; then
    if [ -f "database/data/postgresql/postmaster.pid" ]; then
        pg_ctl -D database/data/postgresql stop -m fast 2>/dev/null || true
    fi
fi

# Force stop any remaining PostgreSQL processes
POSTGRES_PIDS=$(pgrep -f "postgres" 2>/dev/null || true)
if [ -n "$POSTGRES_PIDS" ]; then
    echo "Force stopping remaining PostgreSQL processes..."
    safe_kill "$POSTGRES_PIDS" "PostgreSQL"
fi

# Clean up ports
echo ""
echo "4. Cleaning up occupied ports"
echo "=================================="
for port in 5433 8001 3001; do
    PORT_PIDS=$(lsof -ti :$port 2>/dev/null || true)
    if [ -n "$PORT_PIDS" ]; then
        echo "Cleaning up port $port..."
        echo "$PORT_PIDS" | xargs kill -9 2>/dev/null || true
    fi
done

# Clean up log files (optional)
echo ""
echo "5. Log file cleanup"
echo "=================================="
read -p "Do you want to clear log files? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Clearing log files..."
    > log/api.log 2>/dev/null || true
    > log/frontend.log 2>/dev/null || true
    > database/logs/postgresql.log 2>/dev/null || true
    echo "Log files cleared"
else
    echo "Log files preserved"
fi

echo ""
echo "Shutdown completed!"
echo "=================================="
echo ""
echo "All services have been stopped."
echo "To start services again, run: ./deployment/venv/venv_start.sh"
echo "" 
#!/bin/bash
# PostgreSQL Database Stop Script for IoT Device Monitor

DATABASE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PGDATA="$DATABASE_ROOT/data/postgresql"

echo "Stopping IoT Device Monitor Database..."

if pg_ctl -D "$PGDATA" status > /dev/null 2>&1; then
    echo "Shutting down PostgreSQL..."
    pg_ctl -D "$PGDATA" stop -m fast
    
    if [ $? -eq 0 ]; then
        echo "PostgreSQL stopped successfully"
    else
        echo "Failed to stop PostgreSQL"
        exit 1
    fi
else
    echo "PostgreSQL is not running"
fi

echo "Database shutdown complete!" 
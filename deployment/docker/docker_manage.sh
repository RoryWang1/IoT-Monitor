#!/bin/bash

# IoT Device Monitor - Docker Service Management Script
# Provides functions for starting, stopping, restarting, and viewing logs

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Log functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check Docker environment
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi

    # Set Docker command
    if ! docker ps &> /dev/null; then
        if sudo docker ps &> /dev/null 2>&1; then
            DOCKER_CMD="sudo docker-compose"
        else
            log_error "Docker permission denied"
            exit 1
        fi
    else
        DOCKER_CMD="docker-compose"
    fi
}

# Check service status
check_service_status() {
    cd "$SCRIPT_DIR"
    
    if $DOCKER_CMD ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -q "iot-monitor"; then
        return 0
    else
        return 1
    fi
}

# Show service status
show_status() {
    echo "IoT Device Monitor - Service Status"
    echo "=================================="
    
    cd "$SCRIPT_DIR"
    
    if check_service_status; then
        log_info "Service is running"
        echo ""
        $DOCKER_CMD ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        
        echo ""
        echo "Access address:"
        # Try to read IP from .env file
        if [ -f ".env" ]; then
            source .env
            echo "  Frontend interface: http://${SERVER_IP:-localhost}:3001"
            echo "  API documentation: http://${SERVER_IP:-localhost}:8001/docs"
        else
            echo "  Frontend interface: http://localhost:3001"
            echo "  API documentation: http://localhost:8001/docs"
        fi
    else
        log_warn "Service is not running"
    fi
}

# Start services
start_services() {
    echo "IoT Device Monitor - Start Service"
    echo "=================================="
    
    cd "$SCRIPT_DIR"
    
    if check_service_status; then
        log_warn "Service is already running"
        show_status
        return 0
    fi

    # Check if .env file exists
    if [ ! -f ".env" ]; then
        log_warn "No .env file found, it is recommended to run ./docker_deploy.sh for initial deployment"
    fi

    log_info "Starting Docker service..."
    $DOCKER_CMD up -d

    log_info "Waiting for service to start..."
    sleep 10

    # Verify service startup
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:8001/health >/dev/null 2>&1 && \
           curl -s http://localhost:3001 >/dev/null 2>&1; then
            log_info "All services started successfully"
            show_status
            return 0
        fi
        
        echo -n "."
        sleep 1
        ((attempt++))
    done
    
    echo ""
    log_error "Service startup timeout, please check the logs"
    return 1
}

# Stop services
stop_services() {
    echo "IoT Device Monitor - Stop Service"
    echo "=================================="
    
    cd "$SCRIPT_DIR"
    
    if ! check_service_status; then
        log_warn "Service is not running"
        return 0
    fi

    log_info "Stopping Docker service..."
    $DOCKER_CMD down
    
    log_info "Service stopped"
}

# Restart services
restart_services() {
    echo "IoT Device Monitor - Restart Service"
    echo "=================================="
    
    stop_services
    echo ""
    start_services
}

# View logs
view_logs() {
    local service=$1
    
    cd "$SCRIPT_DIR"
    
    if ! check_service_status; then
        log_error "Service is not running"
        return 1
    fi

    if [ -z "$service" ]; then
        echo "View all service logs (Ctrl+C to exit):"
        echo "=================================="
        $DOCKER_CMD logs -f
    else
        case $service in
            "frontend"|"frontend")
                echo "View frontend service logs (Ctrl+C to exit):"
                echo "=================================="
                $DOCKER_CMD logs -f frontend
                ;;
            "backend"|"backend"|"api")
                echo "View backend API logs (Ctrl+C to exit):"
                echo "=================================="
                $DOCKER_CMD logs -f backend
                ;;
            "database"|"database"|"db")
                echo "View database logs (Ctrl+C to exit):"
                echo "=================================="
                $DOCKER_CMD logs -f database
                ;;
            "file-monitor"|"file-monitor"|"pcap")
                echo "View file monitor logs (Ctrl+C to exit):"
                echo "=================================="
                # Directly view the dedicated file monitor log file
                if docker exec iot-monitor-backend test -f /app/log/file_monitor.log; then
                    docker exec iot-monitor-backend tail -f /app/log/file_monitor.log
                else
                    log_error "File monitor log file does not exist, view file monitor information in the backend logs..."
                    $DOCKER_CMD logs -f backend | grep -i "file.*monitor\|pcap\|analyzer"
                fi
                ;;
            "file-monitor-restart"|"file-monitor-restart")
                echo "Restart file monitor service:"
                echo "=================================="
                log_info "Restarting file monitor service..."
                curl -X POST http://localhost:8001/api/admin/file-monitor/restart 2>/dev/null && {
                    log_info "File monitor service restarted successfully"
                    echo "View status: curl -s http://localhost:8001/api/admin/file-monitor/status"
                } || {
                    log_error "File monitor service restart failed"
                }
                ;;
            *)
                log_error "Unknown service: $service"
                echo "Available services: frontend, backend, database, file-monitor"
        
                return 1
                ;;
        esac
    fi
}

# Clean system
clean_system() {
    echo "IoT Device Monitor - Clean System"
    echo "=================================="
    
    cd "$SCRIPT_DIR"
    
    log_warn "This will delete all containers, images, and data!"
    read -p "Continue? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Stopping and deleting containers..."
        $DOCKER_CMD down -v
        
        log_info "Deleting images..."
        docker rmi -f docker-backend docker-frontend 2>/dev/null || true
        
        log_info "Cleaning system cache..."
        docker system prune -f
        
        log_info "System cleanup completed"
    else
        log_info "Cancel cleanup operation"
    fi
}

# Show help information
show_help() {
    echo "IoT Device Monitor - Docker Service Management"
    echo "=================================="
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  start                    Start all services"
    echo "  stop                     Stop all services"
    echo "  restart                  Restart all services"
    echo "  status                   Show service status"
    echo "  logs [service]           View logs (optional specify service)"

    echo "  clean                    Clean system (delete all data)"
    echo "  help                     Show help information"
    echo ""
    echo "Log service options:"
    echo "  frontend        Frontend service logs"
    echo "  backend         Backend API logs"
    echo "  database        Database logs"
    echo "  file-monitor    File monitor logs"
    echo ""
    echo "Special commands:"

    echo ""
    echo "Examples:"
    echo "  $0 start                    # Start all services"
    echo "  $0 logs backend             # View backend logs"
    echo "  $0 logs file-monitor        # View file monitor logs"

    echo "  $0 status                   # View service status"
}

# Main function
main() {
    check_docker
    
    case ${1:-help} in
        "start"|"start")
            start_services
            ;;
        "stop"|"stop")
            stop_services
            ;;
        "restart"|"restart")
            restart_services
            ;;
        "status"|"status")
            show_status
            ;;
        "logs"|"logs")
            view_logs "$2"
            ;;

        "clean"|"clean")
            clean_system
            ;;
        "help"|"help"|"-h"|"--help")
            show_help
            ;;
        *)
            log_error "Unknown command: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Execute main function
main "$@" 
# Deployment Module
IoT Device Monitor deployment module, providing Docker and virtual environment deployment options.

## Architecture

```
deployment/
├── docker/                  # Docker containerized deployment
│   ├── docker_deploy.sh     # One-click deployment script
│   ├── docker_manage.sh     # Service management script
│   ├── docker-compose.yml  # Container orchestration
│   ├── Dockerfile.backend  # Backend image
│   └── Dockerfile.frontend # Frontend image
└── virtual_env/             # Virtual environment deployment
    ├── venv_deploy.sh       # Environment setup script
    ├── venv_start.sh        # Start script
    └── venv_stop.sh         # Stop script
```

## Executable Scripts

### Docker Deployment

```bash
# One-click deployment with auto IP detection
cd deployment/docker
./docker_deploy.sh

# Deploy with specific IP
./docker_deploy.sh 192.168.1.100

# Service management
./docker_manage.sh start     # Start services
./docker_manage.sh stop      # Stop services
./docker_manage.sh restart   # Restart services
./docker_manage.sh status    # Check status
./docker_manage.sh logs      # View logs
./docker_manage.sh clean     # Clean all data
```

### Virtual Environment Deployment

```bash
# Initial deployment
cd deployment/virtual_env
./venv_deploy.sh

# Start/stop services
./venv_start.sh             # Start all services
./venv_stop.sh              # Stop all services
```

## Functionality 

**Docker Deployment:**
- Automatic IP detection and configuration
- One-click deployment of all services
- Environment isolation and dependency management
- Automatic reference data import

**Virtual Environment Deployment:**
- Lightweight local deployment
- Direct system resource access
- Development-friendly

## Access URLs

- **Frontend**: http://server-ip:3001
- **API Documentation**: http://server-ip:8001/docs
- **Local Access**: http://localhost:3001

## Configuration

**Environment Variables** (auto-generated in `.env`):
```bash
SERVER_IP=192.168.1.100
WS_BASE_URL=ws://192.168.1.100:8001
```

**Service Ports:**
- Frontend: 3001
- Backend API: 8001  
- Database: 5433 
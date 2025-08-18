# Docker Containerization Documentation

## Overview

This directory contains comprehensive Docker configuration for the Parking Management System, supporting both development and production environments with advanced features like:

- Multi-stage builds for optimization
- Health checks and monitoring
- Load balancing and scaling
- Security configurations
- Log management
- Performance tuning

## File Structure

```
docker/
├── docker-compose.yml              # Development environment
├── docker-compose.prod.yml         # Production environment
├── docker-compose.override.yml     # Local development overrides
├── docker-compose.swarm.yml        # Docker Swarm configuration
├── docker-manager.sh               # Management script
├── .env.dev                       # Development environment variables
├── .env.prod                      # Production environment variables
├── nginx/
│   ├── nginx.conf                 # Development Nginx config
│   └── nginx-prod.conf            # Production Nginx config
├── postgres/
│   └── postgresql.conf            # PostgreSQL configuration
├── redis/
│   └── redis.conf                 # Redis configuration
└── monitoring/
    ├── prometheus.yml             # Prometheus configuration
    └── grafana/                   # Grafana provisioning
```

## Quick Start

### Development Environment

```bash
# Start all services
make dev-up
# or
./docker/docker-manager.sh dev-up

# View logs
make logs SERVICE=backend
make logs SERVICE=frontend

# Stop services
make dev-down
```

### Production Environment

```bash
# Build production images
make build-prod

# Start production environment
make prod-up

# Check health
make health
```

## Services

### Backend (FastAPI)
- **Port**: 8000
- **Health Check**: `/health` endpoint
- **Features**: 
  - Multi-stage build for optimization
  - Non-root user for security
  - Health checks every 30s
  - Debug port 5678 (development)

### Frontend (React + Nginx)
- **Port**: 3000
- **Features**:
  - Optimized Nginx configuration
  - Static asset caching
  - Gzip compression
  - Security headers

### Database (PostgreSQL + PostGIS)
- **Port**: 5432
- **Features**:
  - PostGIS spatial extensions
  - Custom configuration
  - Health checks
  - Backup support

### Cache (Redis)
- **Port**: 6379
- **Features**:
  - Persistence enabled
  - Memory optimization
  - Password protection

### Message Queue (Kafka)
- **Port**: 9092
- **Features**:
  - Zookeeper coordination
  - Auto topic creation
  - Health monitoring

### Search (Elasticsearch)
- **Port**: 9200
- **Features**:
  - Single-node setup
  - Memory optimization
  - Health checks

### Load Balancer (Nginx)
- **Port**: 80, 443
- **Features**:
  - Rate limiting
  - SSL termination
  - WebSocket support
  - Health checks

### Monitoring (Prometheus + Grafana)
- **Prometheus**: Port 9090
- **Grafana**: Port 3001
- **Features**:
  - Service monitoring
  - Custom dashboards
  - Alerting (configurable)

## Environment Variables

### Development (.env.dev)
- DEBUG mode enabled
- Local database connections
- Permissive CORS settings
- Detailed logging

### Production (.env.prod)
- Production optimizations
- Secure passwords (change defaults!)
- Restricted CORS origins
- SSL configuration

## Health Checks

All services include comprehensive health checks:

```bash
# Check all service health
make health

# Individual service checks
docker-compose ps
docker-compose exec backend curl http://localhost:8000/health
```

## Scaling

### Horizontal Scaling
```bash
# Scale backend service
docker-compose up -d --scale backend=3

# Scale frontend service
docker-compose up -d --scale frontend=2
```

### Docker Swarm (Production)
```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.swarm.yml parking-system
```

## Security Features

### Container Security
- Non-root users in all containers
- Read-only file systems where possible
- Resource limits and reservations
- Security headers and CORS protection

### Network Security
- Isolated Docker networks
- Rate limiting
- SSL/TLS encryption
- Secret management

### Access Control
- Password-protected services
- JWT authentication
- OAuth integration
- Brute force protection

## Monitoring and Logging

### Log Management
- Centralized logging with rotation
- Structured JSON logs
- Log aggregation ready

### Metrics Collection
- Prometheus metrics
- Grafana dashboards
- Custom application metrics
- Infrastructure monitoring

## Backup and Recovery

### Database Backup
```bash
# Create backup
make backup

# Restore from backup
make restore FILE=backup_20231201_120000.sql
```

### Volume Management
```bash
# List volumes
docker volume ls

# Backup volume
docker run --rm -v parking_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .
```

## Performance Optimization

### Build Optimization
- Multi-stage builds
- Layer caching
- Minimal base images
- Dependency optimization

### Runtime Optimization
- Resource limits
- Connection pooling
- Caching strategies
- Load balancing

## Troubleshooting

### Common Issues

1. **Port conflicts**
   ```bash
   # Check port usage
   lsof -i :8000
   
   # Stop conflicting services
   sudo service nginx stop
   ```

2. **Permission issues**
   ```bash
   # Fix ownership
   sudo chown -R $USER:$USER ./
   
   # Reset Docker permissions
   docker system prune -a
   ```

3. **Memory issues**
   ```bash
   # Increase Docker memory limit
   # Docker Desktop -> Settings -> Resources -> Memory
   
   # Check container memory usage
   docker stats
   ```

### Debug Mode

Enable debug mode for detailed troubleshooting:

```bash
# Start with debug logging
LOG_LEVEL=debug make dev-up

# Attach debugger to backend
# VSCode: Connect to localhost:5678
```

## Deployment Strategies

### Blue-Green Deployment
```bash
# Build new version
docker build -t parking-backend:v2 .

# Update compose file with new image
# Deploy without downtime
docker-compose up -d
```

### Rolling Updates
```bash
# Update service gradually
docker service update --image parking-backend:v2 parking_backend
```

## SSL/TLS Configuration

### Development SSL
```bash
# Generate self-signed certificates
make ssl-setup
```

### Production SSL
- Use Let's Encrypt with Traefik
- Configure in docker-compose.swarm.yml
- Automatic certificate renewal

## Contributing

When adding new services:

1. Add Dockerfile with multi-stage build
2. Include health checks
3. Add to docker-compose files
4. Update documentation
5. Add monitoring endpoints
6. Configure security settings

## Support

For issues and questions:
- Check logs: `make logs`
- Check health: `make health`
- Review configuration files
- Consult Docker documentation

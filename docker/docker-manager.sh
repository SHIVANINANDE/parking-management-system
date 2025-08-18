#!/bin/bash

# Docker Management Scripts for Parking Management System

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    print_status "Docker is running."
}

# Function to check if Docker Compose is available
check_docker_compose() {
    if ! command -v docker-compose > /dev/null 2>&1; then
        print_error "Docker Compose is not installed."
        exit 1
    fi
    print_status "Docker Compose is available."
}

# Development environment
dev_up() {
    print_status "Starting development environment..."
    check_docker
    check_docker_compose
    
    cd "$(dirname "$0")"
    cp .env.dev .env
    docker-compose -f docker-compose.yml up -d
    
    print_status "Development environment started successfully!"
    print_status "Frontend: http://localhost:3000"
    print_status "Backend API: http://localhost:8000"
    print_status "Backend Docs: http://localhost:8000/docs"
    print_status "Grafana: http://localhost:3001 (admin/admin)"
    print_status "Prometheus: http://localhost:9090"
}

dev_down() {
    print_status "Stopping development environment..."
    cd "$(dirname "$0")"
    docker-compose -f docker-compose.yml down
    print_status "Development environment stopped."
}

dev_logs() {
    cd "$(dirname "$0")"
    docker-compose -f docker-compose.yml logs -f "${@:1}"
}

# Production environment
prod_up() {
    print_status "Starting production environment..."
    check_docker
    check_docker_compose
    
    cd "$(dirname "$0")"
    if [ ! -f .env.prod ]; then
        print_error ".env.prod file not found. Please create it from .env.prod.example"
        exit 1
    fi
    
    cp .env.prod .env
    docker-compose -f docker-compose.prod.yml up -d
    
    print_status "Production environment started successfully!"
    print_status "Application: http://localhost"
    print_status "Grafana: http://localhost:3001"
}

prod_down() {
    print_status "Stopping production environment..."
    cd "$(dirname "$0")"
    docker-compose -f docker-compose.prod.yml down
    print_status "Production environment stopped."
}

prod_logs() {
    cd "$(dirname "$0")"
    docker-compose -f docker-compose.prod.yml logs -f "${@:1}"
}

# Build services
build() {
    print_status "Building Docker images..."
    cd "$(dirname "$0")"
    docker-compose -f docker-compose.yml build --no-cache
    print_status "Build completed."
}

build_prod() {
    print_status "Building production Docker images..."
    cd "$(dirname "$0")"
    docker-compose -f docker-compose.prod.yml build --no-cache
    print_status "Production build completed."
}

# Clean up
clean() {
    print_warning "This will remove all containers, images, and volumes. Are you sure? (y/N)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        print_status "Cleaning up Docker resources..."
        cd "$(dirname "$0")"
        docker-compose -f docker-compose.yml down -v --remove-orphans
        docker-compose -f docker-compose.prod.yml down -v --remove-orphans
        docker system prune -f
        print_status "Cleanup completed."
    else
        print_status "Cleanup cancelled."
    fi
}

# Health check
health() {
    print_status "Checking service health..."
    cd "$(dirname "$0")"
    
    services=("postgres" "redis" "elasticsearch" "kafka" "backend" "frontend")
    
    for service in "${services[@]}"; do
        if docker-compose ps -q "$service" > /dev/null 2>&1; then
            health_status=$(docker inspect --format='{{.State.Health.Status}}' "parking_${service}" 2>/dev/null || echo "no-healthcheck")
            if [ "$health_status" = "healthy" ]; then
                print_status "$service: healthy"
            elif [ "$health_status" = "no-healthcheck" ]; then
                status=$(docker inspect --format='{{.State.Status}}' "parking_${service}" 2>/dev/null || echo "not-found")
                if [ "$status" = "running" ]; then
                    print_status "$service: running (no health check)"
                else
                    print_error "$service: $status"
                fi
            else
                print_error "$service: $health_status"
            fi
        else
            print_error "$service: not running"
        fi
    done
}

# Show usage
usage() {
    echo "Usage: $0 {dev-up|dev-down|dev-logs|prod-up|prod-down|prod-logs|build|build-prod|clean|health}"
    echo ""
    echo "Development commands:"
    echo "  dev-up      Start development environment"
    echo "  dev-down    Stop development environment"
    echo "  dev-logs    Show development logs (optional: service name)"
    echo ""
    echo "Production commands:"
    echo "  prod-up     Start production environment"
    echo "  prod-down   Stop production environment"
    echo "  prod-logs   Show production logs (optional: service name)"
    echo ""
    echo "Utility commands:"
    echo "  build       Build development images"
    echo "  build-prod  Build production images"
    echo "  clean       Remove all containers, images, and volumes"
    echo "  health      Check service health status"
    echo ""
    echo "Examples:"
    echo "  $0 dev-up"
    echo "  $0 dev-logs backend"
    echo "  $0 health"
}

# Main script logic
case "${1:-}" in
    dev-up)
        dev_up
        ;;
    dev-down)
        dev_down
        ;;
    dev-logs)
        dev_logs "${@:2}"
        ;;
    prod-up)
        prod_up
        ;;
    prod-down)
        prod_down
        ;;
    prod-logs)
        prod_logs "${@:2}"
        ;;
    build)
        build
        ;;
    build-prod)
        build_prod
        ;;
    clean)
        clean
        ;;
    health)
        health
        ;;
    *)
        usage
        exit 1
        ;;
esac

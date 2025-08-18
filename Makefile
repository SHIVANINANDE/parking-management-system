# Makefile for Docker operations

.PHONY: help dev-up dev-down prod-up prod-down build build-prod clean health logs test

# Default target
help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Development environment
dev-up: ## Start development environment
	@echo "Starting development environment..."
	@cd docker && ./docker-manager.sh dev-up

dev-down: ## Stop development environment
	@echo "Stopping development environment..."
	@cd docker && ./docker-manager.sh dev-down

dev-restart: dev-down dev-up ## Restart development environment

# Production environment
prod-up: ## Start production environment
	@echo "Starting production environment..."
	@cd docker && ./docker-manager.sh prod-up

prod-down: ## Stop production environment
	@echo "Stopping production environment..."
	@cd docker && ./docker-manager.sh prod-down

prod-restart: prod-down prod-up ## Restart production environment

# Build targets
build: ## Build development images
	@echo "Building development images..."
	@cd docker && ./docker-manager.sh build

build-prod: ## Build production images
	@echo "Building production images..."
	@cd docker && ./docker-manager.sh build-prod

rebuild: clean build ## Clean and rebuild development images

rebuild-prod: clean build-prod ## Clean and rebuild production images

# Utility targets
logs: ## Show logs (usage: make logs SERVICE=backend)
	@cd docker && docker-compose logs -f $(SERVICE)

logs-prod: ## Show production logs (usage: make logs-prod SERVICE=backend)
	@cd docker && docker-compose -f docker-compose.prod.yml logs -f $(SERVICE)

health: ## Check service health
	@cd docker && ./docker-manager.sh health

clean: ## Clean up Docker resources
	@cd docker && ./docker-manager.sh clean

# Database operations
db-migrate: ## Run database migrations
	@echo "Running database migrations..."
	@cd docker && docker-compose exec backend alembic upgrade head

db-reset: ## Reset database
	@echo "Resetting database..."
	@cd docker && docker-compose exec backend alembic downgrade base
	@cd docker && docker-compose exec backend alembic upgrade head

db-shell: ## Access database shell
	@cd docker && docker-compose exec postgres psql -U postgres -d parking_db

redis-shell: ## Access Redis shell
	@cd docker && docker-compose exec redis redis-cli

# Testing
test: ## Run tests
	@echo "Running tests..."
	@cd docker && docker-compose exec backend python -m pytest

test-coverage: ## Run tests with coverage
	@echo "Running tests with coverage..."
	@cd docker && docker-compose exec backend python -m pytest --cov=app --cov-report=html

lint: ## Run linting
	@echo "Running linting..."
	@cd docker && docker-compose exec backend python -m flake8 app/
	@cd docker && docker-compose exec backend python -m black app/ --check
	@cd docker && docker-compose exec frontend npm run lint

format: ## Format code
	@echo "Formatting code..."
	@cd docker && docker-compose exec backend python -m black app/
	@cd docker && docker-compose exec backend python -m isort app/
	@cd docker && docker-compose exec frontend npm run format

# Monitoring
monitor: ## Open monitoring dashboards
	@echo "Opening monitoring dashboards..."
	@echo "Grafana: http://localhost:3001"
	@echo "Prometheus: http://localhost:9090"
	@echo "Elasticsearch: http://localhost:9200"

# Backup and restore
backup: ## Backup database
	@echo "Creating database backup..."
	@cd docker && docker-compose exec postgres pg_dump -U postgres parking_db > backup_$(shell date +%Y%m%d_%H%M%S).sql

restore: ## Restore database (usage: make restore FILE=backup.sql)
	@echo "Restoring database from $(FILE)..."
	@cd docker && docker-compose exec -T postgres psql -U postgres parking_db < $(FILE)

# Security scanning
security-scan: ## Run security scanning
	@echo "Running security scan..."
	@cd docker && docker run --rm -v $(PWD):/code sonarqube/sonar-scanner-cli
	@cd docker && docker-compose exec backend python -m safety check
	@cd docker && docker-compose exec frontend npm audit

# SSL setup
ssl-setup: ## Generate SSL certificates for development
	@echo "Generating SSL certificates..."
	@mkdir -p docker/nginx/ssl
	@openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
		-keyout docker/nginx/ssl/key.pem \
		-out docker/nginx/ssl/cert.pem \
		-subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# Performance testing
load-test: ## Run load tests
	@echo "Running load tests..."
	@cd docker && docker run --rm -i grafana/k6 run - < ../tests/load/basic-load-test.js

# Documentation
docs: ## Generate documentation
	@echo "Generating documentation..."
	@cd docker && docker-compose exec backend python -m pdoc app --html --output-dir docs
	@cd docker && docker-compose exec frontend npm run build-docs

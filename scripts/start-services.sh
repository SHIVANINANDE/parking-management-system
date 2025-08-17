#!/bin/bash

# Start all services for Smart Parking Management System

echo "Starting Smart Parking Management System services..."

# Start Docker services
echo "Starting Docker services (PostgreSQL, Redis, Elasticsearch, Kafka)..."
docker-compose -f docker/docker-compose.yml up -d postgres redis elasticsearch zookeeper kafka

echo "Waiting for services to be ready..."
sleep 30

echo "Services started successfully!"
echo ""
echo "Service URLs:"
echo "- PostgreSQL: localhost:5432"
echo "- Redis: localhost:6379"
echo "- Elasticsearch: http://localhost:9200"
echo "- Kafka: localhost:9092"
echo ""
echo "To start the backend API:"
echo "cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
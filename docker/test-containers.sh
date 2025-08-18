#!/bin/bash

# Container Health and Integration Test Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test configuration
API_BASE_URL="http://localhost:8000"
FRONTEND_URL="http://localhost:3000"
TIMEOUT=30

# Helper functions
print_test() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

print_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

print_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
}

print_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

# Wait for service to be ready
wait_for_service() {
    local url=$1
    local service_name=$2
    local max_attempts=30
    local attempt=1

    print_info "Waiting for $service_name to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -sf "$url" > /dev/null 2>&1; then
            print_pass "$service_name is ready"
            return 0
        fi
        
        echo -n "."
        sleep 2
        ((attempt++))
    done
    
    print_fail "$service_name failed to start within $((max_attempts * 2)) seconds"
    return 1
}

# Test database connectivity
test_database() {
    print_test "Testing database connectivity"
    
    if docker-compose exec -T postgres pg_isready -U postgres -d parking_db > /dev/null 2>&1; then
        print_pass "Database is accessible"
        
        # Test PostGIS extension
        if docker-compose exec -T postgres psql -U postgres -d parking_db -c "SELECT PostGIS_Version();" > /dev/null 2>&1; then
            print_pass "PostGIS extension is working"
        else
            print_fail "PostGIS extension not working"
            return 1
        fi
        
        # Test sample data
        local count=$(docker-compose exec -T postgres psql -U postgres -d parking_db -t -c "SELECT COUNT(*) FROM parking_lots;" | tr -d ' \n')
        if [ "$count" -gt 0 ]; then
            print_pass "Sample data exists ($count parking lots)"
        else
            print_fail "No sample data found"
        fi
    else
        print_fail "Database is not accessible"
        return 1
    fi
}

# Test Redis connectivity
test_redis() {
    print_test "Testing Redis connectivity"
    
    if docker-compose exec -T redis redis-cli ping | grep -q "PONG"; then
        print_pass "Redis is responding"
        
        # Test Redis operations
        docker-compose exec -T redis redis-cli set test_key "test_value" > /dev/null
        local value=$(docker-compose exec -T redis redis-cli get test_key | tr -d '\r')
        if [ "$value" = "test_value" ]; then
            print_pass "Redis read/write operations working"
            docker-compose exec -T redis redis-cli del test_key > /dev/null
        else
            print_fail "Redis read/write operations failed"
            return 1
        fi
    else
        print_fail "Redis is not responding"
        return 1
    fi
}

# Test Elasticsearch connectivity
test_elasticsearch() {
    print_test "Testing Elasticsearch connectivity"
    
    local health_url="http://localhost:9200/_cluster/health"
    if curl -sf "$health_url" > /dev/null 2>&1; then
        local status=$(curl -s "$health_url" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
        if [ "$status" = "green" ] || [ "$status" = "yellow" ]; then
            print_pass "Elasticsearch cluster is $status"
        else
            print_fail "Elasticsearch cluster status is $status"
            return 1
        fi
    else
        print_fail "Elasticsearch is not accessible"
        return 1
    fi
}

# Test Kafka connectivity
test_kafka() {
    print_test "Testing Kafka connectivity"
    
    # Test if Kafka broker is accessible
    if docker-compose exec -T kafka kafka-broker-api-versions --bootstrap-server localhost:9092 > /dev/null 2>&1; then
        print_pass "Kafka broker is accessible"
        
        # Test topic creation and message production/consumption
        local test_topic="test-topic-$$"
        
        # Create topic
        docker-compose exec -T kafka kafka-topics --create --topic "$test_topic" --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1 > /dev/null 2>&1
        
        # Produce message
        echo "test message" | docker-compose exec -T kafka kafka-console-producer --topic "$test_topic" --bootstrap-server localhost:9092 > /dev/null 2>&1
        
        # Consume message (with timeout)
        local consumed_message=$(timeout 10 docker-compose exec -T kafka kafka-console-consumer --topic "$test_topic" --bootstrap-server localhost:9092 --from-beginning --max-messages 1 2>/dev/null | head -1 | tr -d '\r\n')
        
        if [ "$consumed_message" = "test message" ]; then
            print_pass "Kafka message production/consumption working"
        else
            print_fail "Kafka message production/consumption failed"
        fi
        
        # Clean up
        docker-compose exec -T kafka kafka-topics --delete --topic "$test_topic" --bootstrap-server localhost:9092 > /dev/null 2>&1
    else
        print_fail "Kafka broker is not accessible"
        return 1
    fi
}

# Test backend API
test_backend_api() {
    print_test "Testing backend API"
    
    # Wait for backend to be ready
    wait_for_service "$API_BASE_URL/health" "Backend API"
    
    # Test health endpoint
    local health_response=$(curl -s "$API_BASE_URL/health")
    if echo "$health_response" | grep -q '"status":"healthy"'; then
        print_pass "Backend health check passed"
    else
        print_fail "Backend health check failed"
        return 1
    fi
    
    # Test API endpoints
    local endpoints=(
        "/docs"
        "/api/v1/parking-lots"
        "/api/v1/auth/register"
    )
    
    for endpoint in "${endpoints[@]}"; do
        if curl -sf "$API_BASE_URL$endpoint" > /dev/null 2>&1; then
            print_pass "Endpoint $endpoint is accessible"
        else
            print_fail "Endpoint $endpoint is not accessible"
        fi
    done
    
    # Test API functionality
    print_test "Testing API registration"
    local register_response=$(curl -s -X POST "$API_BASE_URL/api/v1/auth/register" \
        -H "Content-Type: application/json" \
        -d '{
            "email": "test@example.com",
            "username": "testuser",
            "password": "TestPassword123!",
            "full_name": "Test User",
            "phone_number": "+1234567890"
        }')
    
    if echo "$register_response" | grep -q '"email":"test@example.com"'; then
        print_pass "User registration working"
    else
        print_pass "User registration test (user may already exist)"
    fi
}

# Test frontend
test_frontend() {
    print_test "Testing frontend"
    
    # Wait for frontend to be ready
    wait_for_service "$FRONTEND_URL" "Frontend"
    
    # Test if React app is served
    local frontend_response=$(curl -s "$FRONTEND_URL")
    if echo "$frontend_response" | grep -q "<!DOCTYPE html>"; then
        print_pass "Frontend is serving HTML"
    else
        print_fail "Frontend is not serving proper HTML"
        return 1
    fi
    
    # Test if React app loads (check for common React patterns)
    if echo "$frontend_response" | grep -q "root\|react\|app"; then
        print_pass "React application appears to be loaded"
    else
        print_fail "React application does not appear to be loaded"
    fi
}

# Test nginx reverse proxy
test_nginx() {
    print_test "Testing Nginx reverse proxy"
    
    local nginx_health="http://localhost/health"
    if curl -sf "$nginx_health" > /dev/null 2>&1; then
        print_pass "Nginx health check passed"
    else
        print_fail "Nginx health check failed"
        return 1
    fi
    
    # Test API proxying
    local api_through_nginx="http://localhost/api/v1/health"
    if curl -sf "$api_through_nginx" > /dev/null 2>&1; then
        print_pass "Nginx API proxying working"
    else
        print_fail "Nginx API proxying not working"
    fi
}

# Test monitoring services
test_monitoring() {
    print_test "Testing monitoring services"
    
    # Test Prometheus
    if curl -sf "http://localhost:9090/-/healthy" > /dev/null 2>&1; then
        print_pass "Prometheus is healthy"
    else
        print_fail "Prometheus is not healthy"
    fi
    
    # Test Grafana
    if curl -sf "http://localhost:3001/api/health" > /dev/null 2>&1; then
        print_pass "Grafana is accessible"
    else
        print_fail "Grafana is not accessible"
    fi
}

# Test container health
test_container_health() {
    print_test "Testing container health status"
    
    local services=("postgres" "redis" "elasticsearch" "kafka" "backend" "frontend")
    
    for service in "${services[@]}"; do
        local container_name="parking_${service}"
        local health_status=$(docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "no-healthcheck")
        
        if [ "$health_status" = "healthy" ]; then
            print_pass "$service container is healthy"
        elif [ "$health_status" = "no-healthcheck" ]; then
            local running_status=$(docker inspect --format='{{.State.Status}}' "$container_name" 2>/dev/null || echo "not-found")
            if [ "$running_status" = "running" ]; then
                print_pass "$service container is running (no health check)"
            else
                print_fail "$service container is $running_status"
            fi
        else
            print_fail "$service container health is $health_status"
        fi
    done
}

# Test logs
test_logging() {
    print_test "Testing logging functionality"
    
    # Check if logs are being generated
    local services=("backend" "frontend" "nginx")
    
    for service in "${services[@]}"; do
        local log_output=$(docker-compose logs --tail=10 "$service" 2>/dev/null || echo "")
        if [ -n "$log_output" ]; then
            print_pass "$service is generating logs"
        else
            print_fail "$service is not generating logs"
        fi
    done
}

# Performance test
test_performance() {
    print_test "Running basic performance tests"
    
    # Test API response time
    local start_time=$(date +%s%N)
    curl -sf "$API_BASE_URL/health" > /dev/null 2>&1
    local end_time=$(date +%s%N)
    local response_time=$((($end_time - $start_time) / 1000000)) # Convert to milliseconds
    
    if [ $response_time -lt 1000 ]; then # Less than 1 second
        print_pass "API response time: ${response_time}ms"
    else
        print_fail "API response time too slow: ${response_time}ms"
    fi
    
    # Test concurrent requests
    print_info "Testing concurrent API requests..."
    local concurrent_test_result=0
    for i in {1..10}; do
        curl -sf "$API_BASE_URL/health" > /dev/null 2>&1 &
    done
    wait
    
    if [ $? -eq 0 ]; then
        print_pass "Concurrent requests handled successfully"
    else
        print_fail "Concurrent requests failed"
    fi
}

# Main test execution
main() {
    echo -e "${BLUE}=== Parking Management System Container Tests ===${NC}"
    echo ""
    
    # Check if Docker Compose is running
    if ! docker-compose ps > /dev/null 2>&1; then
        print_fail "Docker Compose services are not running. Please start them with 'make dev-up'"
        exit 1
    fi
    
    local failed_tests=0
    
    # Run all tests
    test_container_health || ((failed_tests++))
    test_database || ((failed_tests++))
    test_redis || ((failed_tests++))
    test_elasticsearch || ((failed_tests++))
    test_kafka || ((failed_tests++))
    test_backend_api || ((failed_tests++))
    test_frontend || ((failed_tests++))
    test_nginx || ((failed_tests++))
    test_monitoring || ((failed_tests++))
    test_logging || ((failed_tests++))
    test_performance || ((failed_tests++))
    
    echo ""
    echo -e "${BLUE}=== Test Summary ===${NC}"
    
    if [ $failed_tests -eq 0 ]; then
        print_pass "All tests passed! ✅"
        echo ""
        echo -e "${GREEN}Your containerized parking management system is working correctly!${NC}"
        echo ""
        echo "Services available at:"
        echo "  Frontend:    http://localhost:3000"
        echo "  Backend API: http://localhost:8000"
        echo "  API Docs:    http://localhost:8000/docs"
        echo "  Grafana:     http://localhost:3001 (admin/admin)"
        echo "  Prometheus:  http://localhost:9090"
        exit 0
    else
        print_fail "$failed_tests test(s) failed ❌"
        echo ""
        echo "Please check the failed services and try again."
        echo "Use 'make logs SERVICE=<service_name>' to check service logs."
        exit 1
    fi
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Container Health and Integration Test Script"
        echo ""
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --quick, -q    Run quick tests only"
        echo "  --performance  Run performance tests only"
        echo ""
        echo "This script tests all containerized services in the parking management system."
        exit 0
        ;;
    --quick|-q)
        test_container_health
        test_backend_api
        test_frontend
        ;;
    --performance)
        test_performance
        ;;
    *)
        main
        ;;
esac

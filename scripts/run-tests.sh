#!/bin/bash

# Test Runner Script for Parking Management System
# This script runs different types of tests based on the argument provided

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if dependencies are installed
check_dependencies() {
    print_status "Checking dependencies..."
    
    # Check Python dependencies
    if ! python -c "import pytest" 2>/dev/null; then
        print_error "pytest not found. Installing test dependencies..."
        pip install -r requirements.txt
    fi
    
    # Check if database is running (for integration tests)
    if ! pg_isready -h localhost -p 5432 2>/dev/null; then
        print_warning "PostgreSQL is not running. Some integration tests may fail."
    fi
    
    # Check if Redis is running (for caching tests)
    if ! redis-cli ping 2>/dev/null; then
        print_warning "Redis is not running. Some integration tests may fail."
    fi
    
    print_success "Dependencies checked"
}

# Function to run unit tests
run_unit_tests() {
    print_status "Running unit tests..."
    
    cd backend
    
    pytest tests/unit/ \
        -v \
        --tb=short \
        --cov=app \
        --cov-report=term-missing \
        --cov-report=html:htmlcov/unit \
        --junit-xml=test-results/unit-results.xml \
        -m "unit"
    
    if [ $? -eq 0 ]; then
        print_success "Unit tests passed!"
    else
        print_error "Unit tests failed!"
        return 1
    fi
}

# Function to run integration tests
run_integration_tests() {
    print_status "Running integration tests..."
    
    cd backend
    
    # Set test environment variables
    export DATABASE_URL="postgresql+asyncpg://test_user:test_pass@localhost:5432/test_parking_db"
    export REDIS_URL="redis://localhost:6379/1"
    export JWT_SECRET_KEY="test_secret_key_for_testing_only"
    
    pytest tests/integration/ \
        -v \
        --tb=short \
        --cov=app \
        --cov-report=term-missing \
        --cov-report=html:htmlcov/integration \
        --junit-xml=test-results/integration-results.xml \
        -m "integration"
    
    if [ $? -eq 0 ]; then
        print_success "Integration tests passed!"
    else
        print_error "Integration tests failed!"
        return 1
    fi
}

# Function to run end-to-end tests
run_e2e_tests() {
    print_status "Running end-to-end tests..."
    
    # Start backend server in background
    cd backend
    export DATABASE_URL="postgresql+asyncpg://test_user:test_pass@localhost:5432/test_parking_db"
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 &
    BACKEND_PID=$!
    
    # Wait for backend to start
    sleep 5
    
    # Check if backend is running
    if ! curl -s http://localhost:8001/health > /dev/null; then
        print_error "Backend failed to start"
        kill $BACKEND_PID 2>/dev/null || true
        return 1
    fi
    
    # Start frontend in background
    cd ../frontend
    npm run build
    npm run preview &
    FRONTEND_PID=$!
    
    # Wait for frontend to start
    sleep 10
    
    # Run frontend tests
    npm test
    FRONTEND_TEST_RESULT=$?
    
    # Run API end-to-end tests
    cd ../backend
    pytest tests/e2e/ \
        -v \
        --tb=short \
        --junit-xml=test-results/e2e-results.xml \
        -m "e2e"
    BACKEND_E2E_RESULT=$?
    
    # Cleanup
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    
    if [ $FRONTEND_TEST_RESULT -eq 0 ] && [ $BACKEND_E2E_RESULT -eq 0 ]; then
        print_success "End-to-end tests passed!"
    else
        print_error "End-to-end tests failed!"
        return 1
    fi
}

# Function to run load tests
run_load_tests() {
    print_status "Running load tests..."
    
    # Check if backend is running
    if ! curl -s http://localhost:8000/health > /dev/null; then
        print_warning "Backend not running on port 8000. Starting backend..."
        cd backend
        python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
        BACKEND_PID=$!
        sleep 5
    fi
    
    cd backend
    
    # Run Locust load tests
    print_status "Running Locust load tests (30 seconds)..."
    locust -f tests/load/locustfile.py \
        --host=http://localhost:8000 \
        --users=20 \
        --spawn-rate=2 \
        --run-time=30s \
        --headless \
        --html=test-results/load-test-report.html
    
    # Run custom performance tests
    print_status "Running custom performance tests..."
    python tests/load/performance_test.py
    
    # Cleanup if we started the backend
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    
    print_success "Load tests completed!"
}

# Function to run all tests
run_all_tests() {
    print_status "Running all tests..."
    
    run_unit_tests
    run_integration_tests
    run_e2e_tests
    run_load_tests
    
    print_success "All tests completed!"
}

# Function to generate test report
generate_report() {
    print_status "Generating test report..."
    
    cd backend
    
    # Combine coverage reports
    coverage combine
    coverage report --include="app/*"
    coverage html --include="app/*" -d htmlcov/combined
    
    # Generate badges (if coverage-badge is installed)
    if command -v coverage-badge &> /dev/null; then
        coverage-badge -o coverage.svg
    fi
    
    print_success "Test report generated in htmlcov/combined/"
}

# Function to setup test environment
setup_test_env() {
    print_status "Setting up test environment..."
    
    # Create test database
    createdb test_parking_db 2>/dev/null || true
    
    # Run migrations
    cd backend
    export DATABASE_URL="postgresql+asyncpg://test_user:test_pass@localhost:5432/test_parking_db"
    alembic upgrade head
    
    # Install frontend dependencies
    cd ../frontend
    npm install
    
    print_success "Test environment setup complete!"
}

# Function to cleanup test environment
cleanup_test_env() {
    print_status "Cleaning up test environment..."
    
    # Drop test database
    dropdb test_parking_db 2>/dev/null || true
    
    # Clean cache
    cd backend
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    
    # Clean frontend
    cd ../frontend
    rm -rf node_modules/.cache 2>/dev/null || true
    
    print_success "Test environment cleaned up!"
}

# Function to show help
show_help() {
    echo "Test Runner for Parking Management System"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  unit           Run unit tests"
    echo "  integration    Run integration tests"
    echo "  e2e            Run end-to-end tests"
    echo "  load           Run load tests"
    echo "  all            Run all tests"
    echo "  report         Generate test report"
    echo "  setup          Setup test environment"
    echo "  cleanup        Cleanup test environment"
    echo "  help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 unit                    # Run only unit tests"
    echo "  $0 integration            # Run only integration tests"
    echo "  $0 all                    # Run all test suites"
    echo "  $0 setup && $0 all        # Setup environment and run all tests"
}

# Main script logic
case "${1:-help}" in
    "unit")
        check_dependencies
        run_unit_tests
        ;;
    "integration")
        check_dependencies
        run_integration_tests
        ;;
    "e2e")
        check_dependencies
        run_e2e_tests
        ;;
    "load")
        check_dependencies
        run_load_tests
        ;;
    "all")
        check_dependencies
        run_all_tests
        generate_report
        ;;
    "report")
        generate_report
        ;;
    "setup")
        setup_test_env
        ;;
    "cleanup")
        cleanup_test_env
        ;;
    "help"|*)
        show_help
        ;;
esac

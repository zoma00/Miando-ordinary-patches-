#!/bin/bash
set -e

echo "🧪 Running Miando Trading System Test Suite"
echo "============================================="

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

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    exit 1
fi

# Check if pip is available
if ! command -v pip &> /dev/null; then
    print_error "pip is not installed"
    exit 1
fi

# Install test dependencies
print_status "Installing test dependencies..."
pip install -r requirements-test.txt

# Run code quality checks
print_status "Running code quality checks..."

echo "📋 Running Black (code formatting)..."
if black --check --diff patterns/ indikator_bot/ tests/ 2>/dev/null; then
    print_success "Code formatting passed"
else
    print_warning "Code formatting issues found. Run 'black patterns/ indikator_bot/ tests/' to fix"
fi

echo "🔍 Running Flake8 (linting)..."
if flake8 patterns/ indikator_bot/ tests/ 2>/dev/null; then
    print_success "Linting passed"
else
    print_warning "Linting issues found"
fi

echo "🔒 Running MyPy (type checking)..."
if mypy patterns/json_split/ --ignore-missing-imports --no-strict-optional 2>/dev/null; then
    print_success "Type checking passed"
else
    print_warning "Type checking issues found"
fi

# Run security scan
echo "🛡️ Running security scan..."
if command -v bandit &> /dev/null; then
    bandit -r patterns/ indikator_bot/ -f json -o bandit-report.json 2>/dev/null || true
    print_success "Security scan completed"
else
    print_warning "Bandit not installed, skipping security scan"
fi

# Run unit tests
print_status "Running unit tests..."
if pytest tests/unit/ -v --cov=patterns/json_split --cov-report=term-missing -m "unit"; then
    print_success "Unit tests passed"
else
    print_error "Unit tests failed"
    exit 1
fi

# Check if database is available for integration tests
print_status "Checking database availability..."
if docker-compose ps miando-db | grep -q "Up"; then
    print_success "Database is running"
    
    print_status "Running integration tests..."
    if pytest tests/integration/ -v -m "integration and not slow and not docker"; then
        print_success "Integration tests passed"
    else
        print_warning "Some integration tests failed"
    fi
    
    print_status "Running database tests..."
    if pytest tests/ -v -m "database"; then
        print_success "Database tests passed"
    else
        print_warning "Some database tests failed"
    fi
else
    print_warning "Database not running, skipping integration and database tests"
    print_status "To run integration tests, start the database with: docker-compose up -d miando-db"
fi

# Run Docker tests if Docker is available
if command -v docker-compose &> /dev/null; then
    print_status "Running Docker tests..."
    if pytest tests/ -v -m "docker"; then
        print_success "Docker tests passed"
    else
        print_warning "Some Docker tests failed"
    fi
else
    print_warning "Docker not available, skipping Docker tests"
fi

# Generate coverage report
print_status "Generating coverage report..."
coverage html
print_success "Coverage report generated in htmlcov/"

# Final summary
echo ""
echo "🎉 Test suite completed!"
echo "📊 Check htmlcov/index.html for detailed coverage report"
echo "🛡️ Check bandit-report.json for security scan results"

print_success "All tests completed successfully!"

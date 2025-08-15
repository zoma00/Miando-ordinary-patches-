#!/bin/bash

echo "🚀 Miando Trading Platform Setup"
echo "================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi

print_status "Docker is running ✅"

# Check if SSL certificates exist
if [ ! -f "server.crt" ] || [ ! -f "server.key" ]; then
    print_warning "SSL certificates not found. Generating new ones..."
    ./generate_ssl.sh
    print_status "SSL certificates generated ✅"
else
    print_status "SSL certificates found ✅"
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    print_warning ".env file not found. Creating from template..."
    cp .env.example .env
    print_status "Environment file created ✅"
    print_warning "Please review and modify .env file as needed"
else
    print_status "Environment file found ✅"
fi

# Make scripts executable
chmod +x *.sh
print_status "Scripts made executable ✅"

# Clean up old containers and volumes if requested
if [ "$1" == "--clean" ]; then
    print_warning "Cleaning up existing containers and volumes..."
    docker-compose down -v
    docker system prune -f
    print_status "Cleanup completed ✅"
fi

# Build and start services
print_status "Building and starting services..."
docker-compose up --build -d

# Wait for services to be ready
print_status "Waiting for services to be ready..."
sleep 10

# Check service status
if docker-compose ps | grep -q "Up"; then
    print_status "Services are running ✅"
    echo ""
    echo "🎉 Miando Trading Platform is ready!"
    echo ""
    echo "📊 Access Information:"
    echo "   Database: localhost:5434"
    echo "   User: miando"
    echo "   Database: miando"
    echo ""
    echo "📋 Useful Commands:"
    echo "   View logs: docker-compose logs -f"
    echo "   Stop services: docker-compose down"
    echo "   Database shell: docker exec -it miando-db psql -U miando -d miando"
    echo ""
else
    print_error "Some services failed to start. Check logs with: docker-compose logs"
    exit 1
fi

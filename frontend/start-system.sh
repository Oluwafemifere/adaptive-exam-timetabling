#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
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

print_header() {
    echo -e "${PURPLE}=================================${NC}"
    echo -e "${PURPLE}$1${NC}"
    echo -e "${PURPLE}=================================${NC}"
}

# Print welcome message
print_header "BAZE UNIVERSITY EXAM SCHEDULER"
echo -e "${CYAN}Adaptive Exam Timetabling System${NC}"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

print_status "Docker and Docker Compose are installed."

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p backend/app
mkdir -p frontend/src
mkdir -p scheduling_engine
mkdir -p config/nginx/conf.d
mkdir -p config/postgres

# Copy files to correct locations
print_status "Setting up project files..."

# Backend files
cp backend-dockerfile.md backend/Dockerfile
cp requirements.txt backend/
cp entrypoint.sh backend/Scripts/
chmod +x backend/Scripts/entrypoint.sh
cp main.py backend/app/

# Frontend files
cp frontend-dockerfile.md frontend/Dockerfile
cp frontend-nginx.conf frontend/nginx.conf
cp app.jsx frontend/src/App.jsx
cp app.css frontend/src/App.css

# Create a basic scheduling engine Dockerfile
cat > scheduling_engine/Dockerfile << EOF
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    build-essential \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Default command
CMD ["python", "-c", "print('Scheduling engine ready')"]
EOF

# Create requirements for scheduling engine
cat > scheduling_engine/requirements.txt << EOF
ortools==9.8.3296
numpy==1.25.2
scipy==1.11.4
redis==5.0.1
psycopg2-binary==2.9.9
EOF

# Check if .env file exists, create if not
if [ ! -f .env ]; then
    print_warning ".env file not found. Creating default .env file..."
    cp .env .env
fi

# Start the system
print_header "STARTING BAZE EXAM SCHEDULER"

print_status "Building Docker containers..."
docker-compose build

print_status "Starting services..."
docker-compose up -d

print_status "Waiting for services to be ready..."
sleep 10

# Check service health
print_header "CHECKING SERVICE HEALTH"

# Check database
print_status "Checking database connection..."
if docker-compose exec -T database pg_isready -U postgres > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Database: Running${NC}"
else
    echo -e "${RED}✗ Database: Failed${NC}"
fi

# Check Redis
print_status "Checking Redis connection..."
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Redis: Running${NC}"
else
    echo -e "${RED}✗ Redis: Failed${NC}"
fi

# Check backend
print_status "Checking backend service..."
sleep 5
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend: Running${NC}"
else
    echo -e "${RED}✗ Backend: Failed${NC}"
fi

# Check frontend
print_status "Checking frontend service..."
if curl -f http://localhost:3000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Frontend: Running${NC}"
else
    echo -e "${RED}✗ Frontend: Failed${NC}"
fi

print_header "SYSTEM STATUS"
echo -e "${CYAN}Frontend:${NC}     http://localhost:3000"
echo -e "${CYAN}Backend API:${NC}  http://localhost:8000"
echo -e "${CYAN}API Docs:${NC}     http://localhost:8000/docs"
echo -e "${CYAN}Database:${NC}     localhost:5432 (postgres/postgres123)"
echo -e "${CYAN}Redis:${NC}        localhost:6379"
echo -e "${CYAN}Prometheus:${NC}   http://localhost:9090"
echo -e "${CYAN}Grafana:${NC}      http://localhost:3001 (admin/admin123)"

echo ""
print_status "System startup complete!"
print_warning "If any services show as failed, check logs with: docker-compose logs [service-name]"
echo ""
print_status "To stop the system: docker-compose down"
print_status "To view logs: docker-compose logs -f"
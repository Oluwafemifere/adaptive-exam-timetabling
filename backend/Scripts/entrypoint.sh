#!/bin/bash
# =================================================================
# BAZE UNIVERSITY ADAPTIVE EXAM TIMETABLING SYSTEM - ENTRYPOINT
# =================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Baze University Exam Timetabling System${NC}"

# Function to wait for service
wait_for_service() {
    local host=$1
    local port=$2
    local service=$3
    
    echo -e "${YELLOW}⏳ Waiting for $service to be ready...${NC}"
    
    while ! nc -z $host $port; do
        sleep 1
    done
    
    echo -e "${GREEN}✅ $service is ready!${NC}"
}

# Wait for PostgreSQL
if [ "$POSTGRES_HOST" ]; then
    wait_for_service $POSTGRES_HOST ${POSTGRES_PORT:-5432} "PostgreSQL"
fi

# Wait for Redis
if [ "$REDIS_HOST" ]; then
    wait_for_service $REDIS_HOST ${REDIS_PORT:-6379} "Redis"
fi

# Run database migrations only if we're the backend service
if [ "$1" = "uvicorn" ]; then
    echo -e "${YELLOW}🔄 Running database migrations...${NC}"
    
    # Initialize alembic if not already done
    if [ ! -f "alembic.ini" ]; then
        echo -e "${YELLOW}🔧 Initializing Alembic...${NC}"
        alembic init alembic
    fi
    
    # Run migrations
    alembic upgrade head || echo -e "${YELLOW}⚠️  Migration failed or no migrations to run${NC}"
fi

# Create directories if they don't exist
mkdir -p /app/uploads /app/logs

echo -e "${GREEN}✅ Setup complete! Starting application...${NC}"

# Execute the main command
exec "$@"
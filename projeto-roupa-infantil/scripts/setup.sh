#!/bin/bash

# SuperDevSecOps Setup Script

set -e

echo "🚀 Starting SuperDevSecOps setup..."

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check prerequisites
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}❌ $1 is not installed${NC}"
        exit 1
    else
        echo -e "${GREEN}✓ $1 is installed${NC}"
    fi
}

echo "Checking prerequisites..."
check_command docker
check_command docker-compose
check_command python3
check_command node
check_command npm

# Create necessary directories
echo -e "\n${YELLOW}Creating directories...${NC}"
mkdir -p logs/{auth,tasks,nginx}
mkdir -p backups
mkdir -p security/certificates/ssl

# Generate SSL certificates if not exists
if [ ! -f "security/certificates/ssl/cert.pem" ]; then
    echo -e "\n${YELLOW}Generating SSL certificates...${NC}"
    cd security/certificates
    ./generate-certs.sh
    cd ../..
fi

# Copy environment files
if [ ! -f ".env" ]; then
    echo -e "\n${YELLOW}Setting up environment files...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}Please edit .env file with your configuration${NC}"
    read -p "Press enter to continue after editing .env file..."
fi

# Build Docker images
echo -e "\n${YELLOW}Building Docker images...${NC}"
docker-compose build

# Start services
echo -e "\n${YELLOW}Starting services...${NC}"
docker-compose up -d

# Wait for services to be ready
echo -e "\n${YELLOW}Waiting for services to be ready...${NC}"
sleep 30

# Run database migrations
echo -e "\n${YELLOW}Running database migrations...${NC}"
docker-compose exec -T auth-service python manage.py migrate
docker-compose exec -T task-service flask db upgrade

# Create superuser
echo -e "\n${YELLOW}Creating superuser...${NC}"
docker-compose exec auth-service python manage.py createsuperuser

# Show service URLs
echo -e "\n${GREEN}✅ Setup complete!${NC}"
echo -e "\n${YELLOW}Service URLs:${NC}"
echo "- Frontend: https://localhost"
echo "- API Gateway: https://localhost/api"
echo "- Kibana: http://localhost:5601"
echo "- Grafana: http://localhost:3001 (admin/admin123)"
echo "- Prometheus: http://localhost:9090"

echo -e "\n${YELLOW}Default credentials:${NC}"
echo "- Grafana: admin/admin123"
echo "- Superuser: (as created above)"

echo -e "\n${GREEN}🎉 SuperDevSecOps is ready!${NC}"
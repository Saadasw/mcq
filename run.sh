#!/bin/bash
# One-click run script for MCQ Application

set -e

echo "🚀 Starting MCQ Application..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    echo "Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo "❌ Docker daemon is not running. Please start Docker."
    exit 1
fi

# Create necessary directories if they don't exist
echo "📁 Creating necessary directories..."
mkdir -p web/generated web/answers web/sessions web/answer_keys

# Pull latest changes if in a git repository
if [ -d ".git" ]; then
    echo "📥 Pulling latest changes..."
    git pull || echo "⚠️  Warning: Could not pull latest changes (not a git repo or no internet)"
fi

# Build and start the application
echo "🏗️  Building and starting application..."
docker compose up --build -d

# Wait for the application to be ready
echo "⏳ Waiting for application to start..."
sleep 5

# Check if the container is running
if docker compose ps | grep -q "mcq-app.*Up"; then
    echo "✅ Application is running!"
    echo ""
    echo "🌐 Access the application at:"
    echo "   Local:   http://localhost:5000"
    
    # Get IP address for network access
    if command -v hostname &> /dev/null; then
        IP=$(hostname -I | awk '{print $1}')
        if [ ! -z "$IP" ]; then
            echo "   Network: http://$IP:5000"
        fi
    fi
    
    echo ""
    echo "📊 View logs: docker compose logs -f"
    echo "🛑 Stop:      docker compose down"
    echo "🔄 Restart:   docker compose restart"
else
    echo "❌ Application failed to start. Check logs with: docker compose logs"
    exit 1
fi


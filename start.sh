startsh#!/bin/bash

# RAG Server Startup Script

echo "🚀 Starting RAG Server..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p uploads logs

# Start services
echo "🐳 Starting services with Docker Compose..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 15

# Check if services are running
echo "🔍 Checking service status..."
if docker-compose ps | grep -q "Up"; then
    echo "✅ Services are running"
else
    echo "❌ Some services failed to start"
    docker-compose logs
    exit 1
fi

# Test health endpoint
echo "🏥 Testing health endpoint..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null; then
        echo "✅ RAG Server is healthy and ready!"
        break
    else
        echo "⏳ Waiting for server to be ready... (attempt $i/30)"
        sleep 2
    fi
done

if [ $i -eq 30 ]; then
    echo "❌ Server failed to start within 60 seconds"
    docker-compose logs rag_server
    exit 1
fi

echo ""
echo "🎉 RAG Server is now running!"
echo ""
echo "📊 Service URLs:"
echo "   - RAG Server API: http://localhost:8000"
echo "   - API Documentation: http://localhost:8000/docs"
echo "   - Health Check: http://localhost:8000/health"
echo ""
echo "🗄️  Database URLs:"
echo "   - MongoDB: mongodb://localhost:27017"
echo "   - Redis: redis://localhost:6379"
echo "   - Qdrant: http://localhost:6333"
echo ""
echo "🤖 LLM Service:"
echo "   - Ollama: http://localhost:11434 (if enabled)"
echo ""
echo "📝 To stop the server, run: docker-compose down"
echo "📝 To view logs, run: docker-compose logs -f"
echo ""
echo "🧪 To run tests, execute: python test_rag_server.py"

# Windows
start.bat

# Linux/Mac
./start.sh 
@echo off
REM RAG Server Startup Script for Windows

echo 🚀 Starting RAG Server...

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not running. Please start Docker first.
    pause
    exit /b 1
)

REM Check if Docker Compose is available
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker Compose is not installed. Please install Docker Compose first.
    pause
    exit /b 1
)

REM Create necessary directories
echo 📁 Creating directories...
if not exist uploads mkdir uploads
if not exist logs mkdir logs

REM Start services
echo 🐳 Starting services with Docker Compose...
docker-compose up -d

REM Wait for services to be ready
echo ⏳ Waiting for services to be ready...
timeout /t 15 /nobreak >nul

REM Check if services are running
echo 🔍 Checking service status...
docker-compose ps | findstr "Up" >nul
if errorlevel 1 (
    echo ❌ Some services failed to start
    docker-compose logs
    pause
    exit /b 1
) else (
    echo ✅ Services are running
)

REM Test health endpoint
echo 🏥 Testing health endpoint...
for /l %%i in (1,1,30) do (
    curl -s http://localhost:8000/health >nul 2>&1
    if not errorlevel 1 (
        echo ✅ RAG Server is healthy and ready!
        goto :ready
    ) else (
        echo ⏳ Waiting for server to be ready... (attempt %%i/30)
        timeout /t 2 /nobreak >nul
    )
)

echo ❌ Server failed to start within 60 seconds
docker-compose logs rag_server
pause
exit /b 1

:ready
echo.
echo 🎉 RAG Server is now running!
echo.
echo 📊 Service URLs:
echo    - RAG Server API: http://localhost:8000
echo    - API Documentation: http://localhost:8000/docs
echo    - Health Check: http://localhost:8000/health
echo.
echo 🗄️  Database URLs:
echo    - MongoDB: mongodb://localhost:27017
echo    - Redis: redis://localhost:6379
echo    - Qdrant: http://localhost:6333
echo.
echo 🤖 LLM Service:
echo    - Ollama: http://localhost:11434 (if enabled)
echo.
echo 📝 To stop the server, run: docker-compose down
echo 📝 To view logs, run: docker-compose logs -f
echo.
echo 🧪 To run tests, execute: python test_rag_server.py
echo.
pause 
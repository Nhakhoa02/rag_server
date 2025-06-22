from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
import structlog
from typing import List, Optional
import os

from app.core.config import settings
from app.core.database import init_db, close_db
from app.core.logging import setup_logging
from app.core.middleware import RequestLoggingMiddleware
from app.core.monitoring import setup_monitoring

# Setup logging
setup_logging()
logger = structlog.get_logger()

# Online mode - all services enabled
logger.info("Running in online mode - all services enabled")

from app.api.v1.api import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting RAG Server...")
    await init_db()
    setup_monitoring()
    logger.info("RAG Server started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down RAG Server...")
    await close_db()
    logger.info("RAG Server shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="RAG Server",
    description="Scalable Retrieval-Augmented Generation Server",
    version="1.0.0",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(RequestLoggingMiddleware)

# Include API routes
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "RAG Server is running",
        "version": "1.0.0",
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Add basic health checks here
        return {
            "status": "healthy",
            "timestamp": structlog.stdlib.get_logger().handlers[0].formatter.formatTime(
                structlog.stdlib.get_logger().handlers[0].formatter, 
                structlog.stdlib.get_logger().handlers[0].formatter.converter()
            )
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service unhealthy")

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error("Unhandled exception", 
                error=str(exc), 
                path=request.url.path,
                method=request.method)
    
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        workers=1,
        log_level="debug"
    ) 
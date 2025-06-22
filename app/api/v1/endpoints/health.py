from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
import structlog
from typing import Dict, Any
from datetime import datetime

from app.core.database import get_mongodb
from app.services.multi_index_vector_store import MultiIndexVectorStore
from app.core.monitoring import get_metrics

logger = structlog.get_logger()
router = APIRouter()

# Initialize services
vector_store = MultiIndexVectorStore()

@router.get("/")
async def health_check() -> Dict[str, Any]:
    """Basic health check"""
    try:
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow(),
            "service": "rag-server"
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=500, detail="Health check failed")

@router.get("/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """Detailed health check with all services"""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow(),
            "services": {}
        }
        
        # Check MongoDB
        try:
            mongodb = get_mongodb()
            await mongodb.admin.command('ping')
            health_status["services"]["mongodb"] = "healthy"
        except Exception as e:
            health_status["services"]["mongodb"] = f"unhealthy: {str(e)}"
            health_status["status"] = "degraded"
        
        # Check Qdrant
        try:
            qdrant_healthy = await vector_store.health_check()
            health_status["services"]["qdrant"] = "healthy" if qdrant_healthy else "unhealthy"
            if not qdrant_healthy:
                health_status["status"] = "degraded"
        except Exception as e:
            health_status["services"]["qdrant"] = f"unhealthy: {str(e)}"
            health_status["status"] = "degraded"
        
        # Check Redis
        try:
            import redis.asyncio as redis
            redis_client = redis.Redis(
                host="localhost",
                port=6379,
                decode_responses=True
            )
            await redis_client.ping()
            await redis_client.close()
            health_status["services"]["redis"] = "healthy"
        except Exception as e:
            health_status["services"]["redis"] = f"unhealthy: {str(e)}"
            health_status["status"] = "degraded"
        
        # Check LLM services
        try:
            from app.services.llm_service import LLMService
            llm_service = LLMService()
            # Simple test - try to get model info
            await llm_service.get_model_info()
            health_status["services"]["llm"] = "healthy"
        except Exception as e:
            health_status["services"]["llm"] = f"unhealthy: {str(e)}"
            health_status["status"] = "degraded"
        
        return health_status
        
    except Exception as e:
        logger.error("Detailed health check failed", error=str(e))
        raise HTTPException(status_code=500, detail="Health check failed")

@router.get("/metrics")
async def get_metrics_endpoint() -> Dict[str, Any]:
    """Get system metrics"""
    try:
        # Get basic system metrics
        system_metrics = {
            "timestamp": datetime.utcnow(),
            "service": "rag-server"
        }
        
        # Add vector store metrics
        try:
            vector_metrics = await vector_store.get_metrics()
            system_metrics["vector_store"] = vector_metrics
        except Exception as e:
            logger.warning("Failed to get vector store metrics", error=str(e))
            system_metrics["vector_store"] = {"error": str(e)}
        
        return system_metrics
        
    except Exception as e:
        logger.error("Failed to get metrics", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get metrics")

@router.get("/ready")
async def readiness_check() -> Dict[str, Any]:
    """Readiness check for Kubernetes"""
    try:
        # Check if all critical services are ready
        mongodb = get_mongodb()
        await mongodb.admin.command('ping')
        
        qdrant_healthy = await vector_store.health_check()
        if not qdrant_healthy:
            raise Exception("Qdrant is not healthy")
        
        return {
            "ready": True,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        return {
            "ready": False,
            "timestamp": datetime.utcnow(),
            "error": str(e)
        }

@router.get("/llm/info")
async def llm_info():
    """Get LLM service information"""
    try:
        from app.services.llm_service import LLMService
        llm_service = LLMService()
        model_info = await llm_service.get_model_info()
        return model_info
    except Exception as e:
        logger.error("Failed to get LLM info", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get LLM info")

@router.get("/vector-store/stats")
async def vector_store_stats():
    """Get vector store statistics"""
    try:
        stats = await vector_store.get_collection_stats()
        return stats
    except Exception as e:
        logger.error("Failed to get vector store stats", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get vector store stats") 
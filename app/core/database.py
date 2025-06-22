from motor.motor_asyncio import AsyncIOMotorClient
import redis.asyncio as redis
from typing import Optional
import structlog
from .config import settings

logger = structlog.get_logger()

# Global database clients
mongodb_client: Optional[AsyncIOMotorClient] = None
redis_client: Optional[redis.Redis] = None

async def init_db():
    """Initialize database connections"""
    global mongodb_client, redis_client
    
    if settings.offline_mode:
        logger.info("Offline mode enabled - skipping database initialization")
        return
    
    try:
        # Initialize MongoDB
        mongodb_client = AsyncIOMotorClient(settings.mongodb_uri)
        await mongodb_client.admin.command('ping')
        logger.info("MongoDB connection established")
        
        # Initialize Redis
        redis_client = redis.from_url(settings.redis_url)
        await redis_client.ping()
        logger.info("Redis connection established")
        
    except Exception as e:
        logger.error("Database initialization failed", error=str(e))
        raise

async def close_db():
    """Close database connections"""
    global mongodb_client, redis_client
    
    try:
        if mongodb_client:
            mongodb_client.close()
            logger.info("MongoDB connection closed")
        
        if redis_client:
            await redis_client.close()
            logger.info("Redis connection closed")
            
    except Exception as e:
        logger.error("Database cleanup failed", error=str(e))

def get_mongodb():
    """Get MongoDB client"""
    if settings.offline_mode:
        raise RuntimeError("MongoDB not available in offline mode")
    if not mongodb_client:
        raise RuntimeError("MongoDB client not initialized")
    return mongodb_client

def get_redis():
    """Get Redis client"""
    if settings.offline_mode:
        raise RuntimeError("Redis not available in offline mode")
    if not redis_client:
        raise RuntimeError("Redis client not initialized")
    return redis_client

async def health_check():
    """Check database health"""
    try:
        # Check MongoDB
        mongodb = get_mongodb()
        await mongodb.admin.command('ping')
        
        # Check Redis
        redis_client = get_redis()
        await redis_client.ping()
        
        return True
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return False 
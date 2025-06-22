from fastapi import APIRouter
from .endpoints import documents, queries, health

api_router = APIRouter()
 
# Include all endpoint routers
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(queries.router, prefix="/queries", tags=["queries"])
api_router.include_router(health.router, prefix="/health", tags=["health"]) 
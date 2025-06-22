from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import structlog
import uuid
from datetime import datetime

from app.core.database import get_mongodb
from app.services.multi_index_vector_store import MultiIndexVectorStore
from app.services.llm_service import LLMService
from app.core.monitoring import record_query
from app.core.config import settings

logger = structlog.get_logger()
router = APIRouter()

# Initialize services
vector_store = MultiIndexVectorStore()
llm_service = LLMService()

class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = None
    filter_metadata: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    search_mode: Optional[str] = "all"  # all, file_type, collection

class QueryResponse(BaseModel):
    query_id: str
    query: str
    answer: str
    sources: List[Dict[str, Any]]
    metadata: Dict[str, Any]

@router.post("/ask", response_model=QueryResponse)
async def ask_question(request: QueryRequest):
    """Ask a question using RAG with multi-index search"""
    try:
        query_id = str(uuid.uuid4())
        
        logger.info("Processing query", 
                   query_id=query_id,
                   query=request.query,
                   user_id=request.user_id,
                   search_mode=request.search_mode)
        
        # Search for relevant documents using multi-index
        search_results = await vector_store.search(
            query=request.query,
            top_k=request.top_k or settings.top_k,
            filter_metadata=request.filter_metadata or {},
            search_mode=request.search_mode or "all"
        )
        
        if not search_results:
            # No relevant documents found
            answer = "I don't have enough information in my knowledge base to answer this question. Please upload relevant documents first."
            sources = []
        else:
            # Generate answer using LLM
            answer = await llm_service.generate_response(request.query, search_results)
            sources = search_results
        
        # Prepare response
        response = QueryResponse(
            query_id=query_id,
            query=request.query,
            answer=answer,
            sources=sources,
            metadata={
                'sources_count': len(sources),
                'timestamp': datetime.utcnow(),
                'user_id': request.user_id,
                'search_mode': request.search_mode
            }
        )
        
        # Save query to MongoDB (if available)
        try:
            mongodb = get_mongodb()
            query_record = {
                'query_id': query_id,
                'query': request.query,
                'answer': answer,
                'sources_count': len(sources),
                'user_id': request.user_id,
                'timestamp': datetime.utcnow(),
                'filter_metadata': request.filter_metadata,
                'search_mode': request.search_mode
            }
            
            await mongodb.rag_db.queries.insert_one(query_record)
        except Exception as e:
            logger.warning("MongoDB not available, skipping query storage", error=str(e))
        
        logger.info("Query processed successfully", 
                   query_id=query_id,
                   sources_count=len(sources),
                   answer_length=len(answer),
                   search_mode=request.search_mode)
        
        record_query("success")
        
        return response
        
    except Exception as e:
        logger.error("Query processing failed", 
                    query=request.query,
                    error=str(e))
        record_query("failed")
        raise HTTPException(status_code=500, detail="Failed to process query")

@router.get("/")
async def list_queries(
    user_id: Optional[str] = None,
    limit: int = 50,
    skip: int = 0
):
    """List previous queries"""
    try:
        mongodb = get_mongodb()
        
        # Build query
        query = {}
        if user_id:
            query['user_id'] = user_id
        
        # Get queries
        cursor = mongodb.rag_db.queries.find(query).sort('timestamp', -1).skip(skip).limit(limit)
        queries = await cursor.to_list(length=limit)
        
        # Get total count
        total = await mongodb.rag_db.queries.count_documents(query)
        
        return {
            "queries": queries,
            "total": total,
            "limit": limit,
            "skip": skip
        }
        
    except Exception as e:
        logger.warning("MongoDB not available, returning empty query list", error=str(e))
        return {
            "queries": [],
            "total": 0,
            "limit": limit,
            "skip": skip
        }

@router.get("/{query_id}")
async def get_query(query_id: str):
    """Get specific query details"""
    try:
        mongodb = get_mongodb()
        
        query = await mongodb.rag_db.queries.find_one({'query_id': query_id})
        if not query:
            raise HTTPException(status_code=404, detail="Query not found")
        
        return query
        
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("MongoDB not available, query not found", error=str(e))
        raise HTTPException(status_code=404, detail="Query not found")

@router.get("/stats/summary")
async def get_query_stats():
    """Get query statistics"""
    try:
        mongodb = get_mongodb()
        
        # Get total queries
        total_queries = await mongodb.rag_db.queries.count_documents({})
        
        # Get queries by user
        pipeline = [
            {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        user_stats = await mongodb.rag_db.queries.aggregate(pipeline).to_list(length=None)
        
        # Get recent activity
        recent_queries = await mongodb.rag_db.queries.count_documents({
            "timestamp": {"$gte": datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)}
        })
        
        return {
            "total_queries": total_queries,
            "today_queries": recent_queries,
            "user_stats": user_stats
        }
        
    except Exception as e:
        logger.warning("MongoDB not available, returning empty stats", error=str(e))
        return {
            "total_queries": 0,
            "today_queries": 0,
            "user_stats": []
        } 
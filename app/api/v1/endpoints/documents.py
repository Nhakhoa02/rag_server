from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Optional
import structlog
import uuid
import os
import aiofiles
from datetime import datetime
from pathlib import Path

from app.core.config import settings
from app.core.database import get_mongodb
from app.services.multi_index_vector_store import MultiIndexVectorStore
from app.core.monitoring import record_document_upload

logger = structlog.get_logger()
router = APIRouter()

# Initialize services
vector_store = MultiIndexVectorStore()

@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: Optional[str] = None
):
    """Upload and process a document"""
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Check file size
        file_size = 0
        content = await file.read()
        file_size = len(content)
        
        if file_size > settings.max_file_size:
            raise HTTPException(
                status_code=413, 
                detail=f"File too large. Maximum size is {settings.max_file_size} bytes"
            )
        
        # Get file extension
        file_extension = Path(file.filename).suffix.lower().lstrip('.')
        if file_extension not in settings.supported_formats:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type. Supported types: {', '.join(settings.supported_formats)}"
            )
        
        # Generate file ID
        file_id = str(uuid.uuid4())
        
        # Save file
        upload_dir = Path(settings.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_dir / f"{file_id}.{file_extension}"
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        # Prepare metadata
        metadata = {
            'original_filename': file.filename,
            'file_size': file_size,
            'upload_date': datetime.utcnow(),
            'user_id': user_id
        }
        
        # Add to background task for processing
        background_tasks.add_task(
            process_document_background,
            str(file_path),
            file_extension,
            file_id,
            metadata
        )
        
        # Save document info to MongoDB (if available)
        try:
            mongodb = get_mongodb()
            document_info = {
                'file_id': file_id,
                'original_filename': file.filename,
                'file_type': file_extension,
                'file_size': file_size,
                'upload_date': datetime.utcnow(),
                'user_id': user_id,
                'status': 'processing',
                'file_path': str(file_path)
            }
            
            await mongodb.rag_db.documents.insert_one(document_info)
        except Exception as e:
            logger.warning("MongoDB not available, skipping document metadata storage", error=str(e))
        
        logger.info("Document upload initiated", 
                   file_id=file_id,
                   filename=file.filename,
                   file_type=file_extension,
                   file_size=file_size)
        
        record_document_upload(file_extension, "uploaded")
        
        # Return appropriate status based on mode
        if settings.offline_mode:
            status_message = "Document uploaded successfully (offline mode - no vector processing)"
            status = "completed"
        else:
            status_message = "Document uploaded successfully and is being processed"
            status = "processing"
        
        return {
            "file_id": file_id,
            "filename": file.filename,
            "status": status,
            "message": status_message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Document upload failed", 
                    filename=file.filename if file else "unknown",
                    error=str(e))
        raise HTTPException(status_code=500, detail="Failed to upload document")

async def process_document_background(file_path: str, file_type: str, file_id: str, metadata: dict):
    """Background task to process document"""
    try:
        # Add to vector store
        await vector_store.add_document(file_path, file_type, file_id, metadata)
        
        # Update status in MongoDB (if available)
        try:
            mongodb = get_mongodb()
            await mongodb.rag_db.documents.update_one(
                {'file_id': file_id},
                {'$set': {'status': 'completed', 'processed_date': datetime.utcnow()}}
            )
        except Exception as e:
            logger.warning("MongoDB not available, skipping status update", error=str(e))
        
        logger.info("Document processing completed", file_id=file_id)
        record_document_upload(file_type, "processed")
        
    except Exception as e:
        logger.error("Document processing failed", 
                    file_id=file_id,
                    error=str(e))
        
        # Update status in MongoDB (if available)
        try:
            mongodb = get_mongodb()
            await mongodb.rag_db.documents.update_one(
                {'file_id': file_id},
                {'$set': {'status': 'failed', 'error': str(e)}}
            )
        except Exception as db_error:
            logger.warning("MongoDB not available, skipping error status update", error=str(db_error))
        
        record_document_upload(file_type, "failed")

@router.get("/")
async def list_documents(
    user_id: Optional[str] = None,
    limit: int = 50,
    skip: int = 0
):
    """List uploaded documents"""
    try:
        mongodb = get_mongodb()
        
        # Build query
        query = {}
        if user_id:
            query['user_id'] = user_id
        
        # Get documents
        cursor = mongodb.rag_db.documents.find(query).sort('upload_date', -1).skip(skip).limit(limit)
        documents = await cursor.to_list(length=limit)
        
        # Get total count
        total = await mongodb.rag_db.documents.count_documents(query)
        
        return {
            "documents": documents,
            "total": total,
            "limit": limit,
            "skip": skip
        }
        
    except Exception as e:
        logger.warning("MongoDB not available, returning empty document list", error=str(e))
        return {
            "documents": [],
            "total": 0,
            "limit": limit,
            "skip": skip
        }

@router.get("/{file_id}")
async def get_document(file_id: str):
    """Get document information"""
    try:
        mongodb = get_mongodb()
        
        document = await mongodb.rag_db.documents.find_one({'file_id': file_id})
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return document
        
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("MongoDB not available, document not found", error=str(e))
        raise HTTPException(status_code=404, detail="Document not found")

@router.delete("/{file_id}")
async def delete_document(file_id: str):
    """Delete document"""
    try:
        # Try to get document info from MongoDB
        try:
            mongodb = get_mongodb()
            document = await mongodb.rag_db.documents.find_one({'file_id': file_id})
            if not document:
                raise HTTPException(status_code=404, detail="Document not found")
            
            # Delete from MongoDB
            await mongodb.rag_db.documents.delete_one({'file_id': file_id})
        except Exception as e:
            logger.warning("MongoDB not available, skipping metadata deletion", error=str(e))
            document = None
        
        # Delete from vector store
        await vector_store.delete_document(file_id)
        
        # Delete file if we have the path
        if document and document.get('file_path') and os.path.exists(document['file_path']):
            os.remove(document['file_path'])
        else:
            # Try to delete by file_id pattern
            upload_dir = Path(settings.upload_dir)
            for file_path in upload_dir.glob(f"{file_id}.*"):
                if file_path.exists():
                    os.remove(file_path)
                    break
        
        logger.info("Document deleted", file_id=file_id)
        
        return {"message": "Document deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete document", file_id=file_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete document")

@router.get("/{file_id}/chunks")
async def get_document_chunks(file_id: str):
    """Get document chunks from vector store"""
    try:
        # Verify document exists (if MongoDB is available)
        try:
            mongodb = get_mongodb()
            document = await mongodb.rag_db.documents.find_one({'file_id': file_id})
            if not document:
                raise HTTPException(status_code=404, detail="Document not found")
        except Exception as e:
            logger.warning("MongoDB not available, skipping document verification", error=str(e))
        
        # Get chunks from vector store
        chunks = await vector_store.get_document_chunks(file_id)
        
        return {
            "file_id": file_id,
            "chunks": chunks,
            "total_chunks": len(chunks)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get document chunks", file_id=file_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get document chunks")

@router.get("/{file_id}/status")
async def get_document_status(file_id: str):
    """Get document processing status"""
    try:
        # Check if file exists in uploads directory
        upload_dir = Path(settings.upload_dir)
        file_exists = False
        file_path = None
        
        for file_path in upload_dir.glob(f"{file_id}.*"):
            if file_path.exists():
                file_exists = True
                break
        
        if not file_exists:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Try to get status from MongoDB if available
        try:
            mongodb = get_mongodb()
            document = await mongodb.rag_db.documents.find_one({'file_id': file_id})
            if document:
                return {
                    "file_id": file_id,
                    "status": document.get('status', 'unknown'),
                    "file_path": str(file_path),
                    "file_size": file_path.stat().st_size if file_path else 0,
                    "offline_mode": settings.offline_mode
                }
        except Exception as e:
            logger.warning("MongoDB not available, using file system status", error=str(e))
        
        # Return status based on file system
        return {
            "file_id": file_id,
            "status": "completed" if settings.offline_mode else "processing",
            "file_path": str(file_path),
            "file_size": file_path.stat().st_size if file_path else 0,
            "offline_mode": settings.offline_mode,
            "message": "File uploaded successfully" if settings.offline_mode else "File uploaded, processing in background"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get document status", file_id=file_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get document status") 
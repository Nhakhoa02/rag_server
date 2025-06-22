from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer
import structlog
from typing import List, Dict, Any, Optional, Union
import uuid
from .document_processor import DocumentProcessor
from app.core.config import settings

logger = structlog.get_logger()

class MultiIndexVectorStore:
    """Multi-index vector store service using Qdrant with multiple collections"""
    
    def __init__(self):
        self.client = QdrantClient(url=settings.qdrant_url)
        self.embedding_model = SentenceTransformer(settings.embedding_model)
        self.document_processor = DocumentProcessor()
        
        # Define collection names for different document types
        self.collections = {
            'pdf': 'rag_pdf_documents',
            'docx': 'rag_docx_documents', 
            'xlsx': 'rag_xlsx_documents',
            'csv': 'rag_csv_documents',
            'txt': 'rag_txt_documents',
            'image': 'rag_image_documents',  # PNG, JPG, JPEG
            'default': 'rag_documents'  # Fallback collection
        }
        
        # Get embedding dimension first
        def _get_embedding_dim(val):
            try:
                return int(val)
            except Exception:
                return 384
        dim = self.embedding_model.get_sentence_embedding_dimension()
        self.embedding_dim = _get_embedding_dim(dim)
        
        # Ensure all collections exist (with error handling)
        if not settings.offline_mode:
            try:
                self._ensure_collections()
            except Exception as e:
                logger.warning("Failed to connect to Qdrant, collections will be created when needed", error=str(e))
        else:
            logger.info("Running in offline mode - Qdrant initialization skipped")
    
    def _ensure_collections(self):
        """Ensure all collections exist with proper configuration"""
        try:
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            for collection_name in self.collections.values():
                if collection_name not in collection_names:
                    # Create collection with proper vector configuration
                    self.client.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(
                            size=self.embedding_dim,
                            distance=Distance.COSINE
                        )
                    )
                    logger.info("Created Qdrant collection", collection_name=collection_name)
                else:
                    logger.info("Using existing Qdrant collection", collection_name=collection_name)
                    
        except Exception as e:
            logger.error("Failed to ensure collections exist", error=str(e))
            raise
    
    def _get_collection_name(self, file_type: str) -> str:
        """Get the appropriate collection name for a file type"""
        if file_type in ['png', 'jpg', 'jpeg']:
            return self.collections['image']
        elif file_type in self.collections:
            return self.collections[file_type]
        else:
            return self.collections['default']
    
    async def add_document(self, file_path: str, file_type: str, file_id: str, metadata: Dict[str, Any] = {}) -> str:
        """Add document to appropriate collection based on file type"""
        try:
            if settings.offline_mode:
                logger.info("Offline mode - skipping vector store operations", file_id=file_id)
                return file_id
            
            # Process document
            content = await self.document_processor.process_document(file_path, file_type)
            text = content.get('text', '')
            
            if not text.strip():
                raise ValueError("No text content extracted from document")
            
            # Chunk text
            chunks = self.document_processor.chunk_text(
                text, 
                chunk_size=settings.chunk_size, 
                overlap=settings.chunk_overlap
            )
            
            # Get appropriate collection
            collection_name = self._get_collection_name(file_type)
            
            # Prepare data for vector store
            points = []
            
            for i, chunk in enumerate(chunks):
                # Generate embedding
                embedding = self.embedding_model.encode(chunk)
                if not isinstance(embedding, list) and hasattr(embedding, 'tolist'):
                    embedding = embedding.tolist()
                embedding = list(map(float, embedding))
                
                # Prepare metadata
                point_metadata = {
                    'file_id': file_id,
                    'file_type': file_type,
                    'collection': collection_name,
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'chunk_size': len(chunk),
                    'text': chunk
                }
                
                if metadata:
                    point_metadata.update(metadata)
                if content.get('metadata'):
                    point_metadata['document_metadata'] = content['metadata']
                
                # Create point
                point = PointStruct(
                    id=f"{file_id}_chunk_{i}",
                    vector=embedding,
                    payload=point_metadata
                )
                points.append(point)
            
            # Add to vector store
            self.client.upsert(
                collection_name=collection_name,
                points=points
            )
            
            logger.info("Document added to multi-index vector store", 
                       file_id=file_id,
                       file_type=file_type,
                       collection=collection_name,
                       chunks_count=len(chunks))
            
            return file_id
            
        except Exception as e:
            logger.error("Failed to add document to multi-index vector store", 
                        file_id=file_id,
                        file_type=file_type,
                        error=str(e))
            raise
    
    async def search_single_collection(self, query: str, collection_name: str, top_k: int = 5, filter_metadata: Dict[str, Any] = {}) -> List[Dict[str, Any]]:
        """Search in a specific collection"""
        try:
            if top_k is None:
                top_k = settings.top_k
            
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query)
            if not isinstance(query_embedding, list) and hasattr(query_embedding, 'tolist'):
                query_embedding = query_embedding.tolist()
            query_embedding = list(map(float, query_embedding))
            
            # Prepare filter
            search_filter = None
            if filter_metadata:
                conditions = []
                for key, value in filter_metadata.items():
                    conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
                search_filter = Filter(must=conditions)
            
            # Search in specific collection
            search_result = self.client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=top_k,
                query_filter=search_filter,
                with_payload=True,
                with_vectors=False
            )
            
            # Format results
            formatted_results = []
            for result in search_result:
                payload = result.payload if result.payload is not None else {}
                formatted_results.append({
                    'content': payload.get('text', ''),
                    'metadata': {k: v for k, v in payload.items() if k != 'text'},
                    'distance': result.score,
                    'id': result.id,
                    'collection': collection_name
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error("Single collection search failed", 
                        query=query,
                        collection=collection_name,
                        error=str(e))
            raise
    
    async def search_multiple_collections(self, query: str, collections: List[str] = [], top_k_per_collection: int = 1, filter_metadata: Dict[str, Any] = {}) -> List[Dict[str, Any]]:
        """Search across multiple collections and merge results"""
        try:
            if collections is None:
                collections = list(self.collections.values())
            
            if top_k_per_collection is None:
                top_k_per_collection = max(1, settings.top_k // len(collections))
            
            all_results = []
            
            # Search in each collection
            for collection_name in collections:
                try:
                    collection_results = await self.search_single_collection(
                        query=query,
                        collection_name=collection_name,
                        top_k=top_k_per_collection,
                        filter_metadata=filter_metadata
                    )
                    all_results.extend(collection_results)
                except Exception as e:
                    logger.warning(f"Failed to search collection {collection_name}", error=str(e))
                    continue
            
            # Sort by distance and take top results
            all_results.sort(key=lambda x: x['distance'])
            final_results = all_results[:settings.top_k]
            
            logger.info("Multi-collection search completed", 
                       query_length=len(query),
                       collections_searched=len(collections),
                       total_results=len(all_results),
                       final_results=len(final_results))
            
            return final_results
            
        except Exception as e:
            logger.error("Multi-collection search failed", 
                        query=query,
                        error=str(e))
            raise
    
    async def search_by_file_type(self, query: str, file_types: List[str], top_k: int = 1, filter_metadata: Dict[str, Any] = {}) -> List[Dict[str, Any]]:
        """Search in collections based on file types"""
        try:
            collections = []
            for file_type in file_types:
                collection_name = self._get_collection_name(file_type)
                if collection_name not in collections:
                    collections.append(collection_name)
            
            return await self.search_multiple_collections(
                query=query,
                collections=collections,
                top_k_per_collection=top_k,
                filter_metadata=filter_metadata
            )
            
        except Exception as e:
            logger.error("File type search failed", 
                        query=query,
                        file_types=file_types,
                        error=str(e))
            raise
    
    async def search(self, query: str, top_k: int = 5, filter_metadata: Dict[str, Any] = {}, search_mode: str = "all") -> List[Dict[str, Any]]:
        """Main search method with different search modes"""
        try:
            if settings.offline_mode:
                logger.info("Offline mode - returning empty search results")
                return []
            
            if search_mode == "all":
                # Search all collections
                return await self.search_multiple_collections(
                    query=query,
                    top_k_per_collection=top_k,
                    filter_metadata=filter_metadata
                )
            
            elif search_mode == "file_type" and filter_metadata and "file_type" in filter_metadata:
                # Search specific file type
                file_type = filter_metadata["file_type"]
                collection_name = self._get_collection_name(file_type)
                return await self.search_single_collection(
                    query=query,
                    collection_name=collection_name,
                    top_k=top_k,
                    filter_metadata=filter_metadata
                )
            
            elif search_mode == "collection" and filter_metadata and "collection" in filter_metadata:
                # Search specific collection
                return await self.search_single_collection(
                    query=query,
                    collection_name=filter_metadata["collection"],
                    top_k=top_k,
                    filter_metadata=filter_metadata
                )
            
            else:
                # Default to all collections
                return await self.search_multiple_collections(
                    query=query,
                    top_k_per_collection=top_k,
                    filter_metadata=filter_metadata
                )
                
        except Exception as e:
            logger.error("Search failed", 
                        query=query,
                        search_mode=search_mode,
                        error=str(e))
            raise
    
    async def delete_document(self, file_id: str) -> bool:
        """Delete document from all collections"""
        try:
            if settings.offline_mode:
                logger.info("Offline mode - skipping vector store deletion", file_id=file_id)
                return True
            
            deleted_count = 0
            
            for collection_name in self.collections.values():
                try:
                    # Create filter for all chunks of this document
                    filter_condition = Filter(
                        must=[FieldCondition(key="file_id", match=MatchValue(value=file_id))]
                    )
                    
                    # Delete all points matching the filter
                    self.client.delete(
                        collection_name=collection_name,
                        points_selector=filter_condition
                    )
                    deleted_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to delete from collection {collection_name}", error=str(e))
                    continue
            
            logger.info("Document deleted from multi-index vector store", 
                       file_id=file_id,
                       collections_processed=len(self.collections),
                       successful_deletions=deleted_count)
            
            return deleted_count > 0
                
        except Exception as e:
            logger.error("Failed to delete document from multi-index vector store", 
                        file_id=file_id,
                        error=str(e))
            raise
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics for all collections"""
        try:
            all_stats = {}
            total_points = 0
            
            for collection_name in self.collections.values():
                try:
                    # Get collection info
                    collection_info = self.client.get_collection(collection_name)
                    points_count = collection_info.points_count or 0
                    total_points += points_count
                    
                    # Get sample points for metadata analysis
                    sample_result = self.client.scroll(
                        collection_name=collection_name,
                        limit=50,
                        with_payload=True,
                        with_vectors=False
                    )
                    
                    file_types = {}
                    for point in sample_result[0]:
                        payload = point.payload if point.payload is not None else {}
                        file_type = payload.get('file_type', 'unknown')
                        file_types[file_type] = file_types.get(file_type, 0) + 1
                    
                    vector_size = ''
                    distance = ''
                    vectors = collection_info.config.params.vectors
                    if vectors is None:
                        vector_size = ''
                        distance = ''
                    elif isinstance(vectors, dict):
                        vector_size = vectors.get('size', '') if 'size' in vectors and vectors.get('size', None) is not None else ''
                        distance = vectors.get('distance', '') if 'distance' in vectors and vectors.get('distance', None) is not None else ''
                        if distance is not None and not isinstance(distance, str) and hasattr(distance, 'value'):
                            distance = str(distance)
                    else:
                        if hasattr(vectors, 'size') and getattr(vectors, 'size', None) is not None:
                            vector_size = vectors.size
                        if hasattr(vectors, 'distance') and getattr(vectors, 'distance', None) is not None:
                            d = vectors.distance
                            if d is not None and not isinstance(d, str) and hasattr(d, 'value'):
                                distance = d.value
                            else:
                                distance = d
                    
                    all_stats[collection_name] = {
                        'points_count': points_count,
                        'file_types': file_types,
                        'vector_size': vector_size,
                        'distance': distance
                    }
                    
                except Exception as e:
                    logger.warning(f"Failed to get stats for collection {collection_name}", error=str(e))
                    all_stats[collection_name] = {'error': str(e)}
            
            return {
                'total_points': total_points,
                'collections': all_stats,
                'collection_names': list(self.collections.values())
            }
            
        except Exception as e:
            logger.error("Failed to get multi-index collection stats", error=str(e))
            raise

    async def health_check(self) -> bool:
        """Check if Qdrant is healthy"""
        try:
            # Try to get collections info
            collections = self.client.get_collections()
            return True
        except Exception as e:
            logger.error("Qdrant health check failed", error=str(e))
            return False

    async def get_metrics(self) -> Dict[str, Any]:
        """Get metrics for all collections"""
        try:
            stats = await self.get_collection_stats()
            return {
                'status': 'healthy',
                'collections_count': len(self.collections),
                'total_points': stats.get('total_points', 0),
                'collections': stats.get('collections', {}),
                'embedding_model': settings.embedding_model
            }
        except Exception as e:
            logger.error("Failed to get metrics", error=str(e))
            return {
                'status': 'error',
                'error': str(e)
            }

    async def get_document_chunks(self, file_id: str) -> List[Dict[str, Any]]:
        """Get all chunks for a specific document"""
        try:
            if settings.offline_mode:
                logger.info("Offline mode - returning empty chunks", file_id=file_id)
                return []
            
            all_chunks = []
            
            for collection_name in self.collections.values():
                try:
                    # Create filter for all chunks of this document
                    filter_condition = Filter(
                        must=[FieldCondition(key="file_id", match=MatchValue(value=file_id))]
                    )
                    
                    # Get all points matching the filter
                    result = self.client.scroll(
                        collection_name=collection_name,
                        scroll_filter=filter_condition,
                        limit=1000,  # Adjust as needed
                        with_payload=True,
                        with_vectors=False
                    )
                    
                    for point in result[0]:
                        payload = point.payload if point.payload is not None else {}
                        chunk_data = {
                            'id': point.id,
                            'content': payload.get('text', ''),
                            'metadata': {k: v for k, v in payload.items() if k != 'text'},
                            'collection': collection_name
                        }
                        all_chunks.append(chunk_data)
                        
                except Exception as e:
                    logger.warning(f"Failed to get chunks from collection {collection_name}", error=str(e))
                    continue
            
            # Sort by chunk index
            all_chunks.sort(key=lambda x: x['metadata'].get('chunk_index', 0))
            
            logger.info("Retrieved document chunks", 
                       file_id=file_id,
                       chunks_count=len(all_chunks))
            
            return all_chunks
            
        except Exception as e:
            logger.error("Failed to get document chunks", 
                        file_id=file_id,
                        error=str(e))
            raise 
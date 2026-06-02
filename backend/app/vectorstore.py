"""
PHASE 1: Qdrant Vector Database Integration

Purpose: Replace FAISS with production-grade Qdrant for:
- Metadata storage (filename, page_number, upload_timestamp, document_type)
- Scalability for enterprise deployments
- Advanced filtering and search capabilities
- Health checks and monitoring

Why Qdrant over FAISS:
1. Server-based (scalable across machines)
2. Full-featured metadata support
3. Real-time backups and persistence
4. Advanced filtering capabilities
5. Multi-tenancy support
"""

import os
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from uuid import uuid4

from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

from app.config import get_settings
from app.logger import logger
from app.exceptions import VectorDBError


class QdrantVectorStore:
    """
    Wrapper around Qdrant for enterprise vector database operations.
    
    Design Pattern: Singleton pattern ensures single connection to Qdrant
    Responsibility: All vector database operations (create, insert, search)
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern - ensures single instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize Qdrant client and embeddings."""
        if self._initialized:
            return
        
        self.settings = get_settings()
        self._initialized = True
        
        try:
            # Connect to Qdrant server
            self.client = QdrantClient(
                url=self.settings.QDRANT_URL,
                timeout=self.settings.QDRANT_TIMEOUT
            )
            
            # Initialize embeddings model
            self.embeddings = HuggingFaceEmbeddings(
                model_name=self.settings.EMBEDDING_MODEL
            )
            
            # Embedding dimension (all-MiniLM-L6-v2 = 384 dims)
            self.embedding_size = 384
            
            logger.info("Qdrant vector store initialized")
            
        except Exception as e:
            raise VectorDBError(f"Failed to initialize Qdrant: {str(e)}")
    
    def _ensure_collection_exists(self) -> None:
        """
        Create Qdrant collection if it doesn't exist.
        
        Collection schema includes:
        - Vector: Dense embeddings for semantic search
        - Metadata: filename, page_number, upload_timestamp, document_type, chunk_index
        """
        try:
            # Check if collection exists
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.settings.QDRANT_COLLECTION_NAME in collection_names:
                logger.debug(f"Collection {self.settings.QDRANT_COLLECTION_NAME} already exists")
                return
            
            # Create new collection with vector config
            self.client.create_collection(
                collection_name=self.settings.QDRANT_COLLECTION_NAME,
                vectors_config=qdrant_models.VectorParams(
                    size=self.embedding_size,
                    distance=qdrant_models.Distance.COSINE  # Cosine distance for embeddings
                ),
                # Enable payload indexing for metadata filtering
                optimizers_config=qdrant_models.OptimizersConfig(
                    default_segment_number=5,
                    snapshot_on_replica=False
                )
            )
            
            logger.info(
                f"Created Qdrant collection: {self.settings.QDRANT_COLLECTION_NAME}"
            )
            
        except Exception as e:
            if "already exists" not in str(e):
                raise VectorDBError(f"Failed to create collection: {str(e)}")
    
    def add_documents(
        self,
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        document_name: str,
        document_type: str = "pdf"
    ) -> int:
        """
        Add document chunks to Qdrant with metadata.
        
        Args:
            texts: List of text chunks from document
            metadatas: List of metadata dicts (from LangChain)
            document_name: Name of the source document
            document_type: Type of document (pdf, txt, etc.)
        
        Returns:
            Number of chunks successfully added
        
        Metadata stored for each chunk:
            - filename: Source document name
            - page: Page number from the document
            - upload_timestamp: When document was uploaded
            - document_type: Type of source document
            - chunk_index: Sequential index of chunk
        """
        try:
            self._ensure_collection_exists()
            
            if not texts:
                logger.warning("No texts provided to add to Qdrant")
                return 0
            
            logger.info(f"Adding {len(texts)} chunks for document: {document_name}")
            
            # Generate embeddings for all texts
            embeddings = self.embeddings.embed_documents(texts)
            
            upload_timestamp = datetime.utcnow().isoformat()
            
            # Prepare points for Qdrant
            points = []
            for idx, (text, embedding, metadata) in enumerate(
                zip(texts, embeddings, metadatas)
            ):
                # Extract page number from metadata (LangChain provides this)
                page_number = metadata.get("page", 0)
                
                # Create enriched metadata payload
                payload = {
                    "text": text,
                    "filename": document_name,
                    "page": int(page_number),
                    "upload_timestamp": upload_timestamp,
                    "document_type": document_type,
                    "chunk_index": idx,
                    "source_metadata": metadata  # Store original metadata for reference
                }
                
                # Create Qdrant point
                point = qdrant_models.PointStruct(
                    id=str(uuid4()),  # Unique ID for each chunk
                    vector=embedding,
                    payload=payload
                )
                points.append(point)
            
            # Batch insert into Qdrant (more efficient than one-by-one)
            self.client.upsert(
                collection_name=self.settings.QDRANT_COLLECTION_NAME,
                points=points
            )
            
            logger.info(f"Successfully added {len(points)} chunks to Qdrant")
            return len(points)
            
        except Exception as e:
            raise VectorDBError(f"Failed to add documents to Qdrant: {str(e)}")
    
    def search(
        self,
        query: str,
        k: int = 3,
        score_threshold: float = 0.5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Semantic search in Qdrant.
        
        Args:
            query: Search query string
            k: Number of results to return
            score_threshold: Minimum similarity score (0-1)
            filters: Optional metadata filters (e.g., {"document_type": "pdf"})
        
        Returns:
            List of search results with text, metadata, and similarity score
        """
        try:
            if not query.strip():
                raise VectorDBError("Query cannot be empty")
            
            # Generate embedding for query
            query_embedding = self.embeddings.embed_query(query)
            
            # Build Qdrant filter if provided
            qdrant_filter = None
            if filters:
                qdrant_filter = self._build_qdrant_filter(filters)
            
            # Search in Qdrant
            results = self.client.search(
                collection_name=self.settings.QDRANT_COLLECTION_NAME,
                query_vector=query_embedding,
                query_filter=qdrant_filter,
                limit=k,
                score_threshold=score_threshold
            )
            
            # Format results for consumption
            search_results = []
            for result in results:
                search_results.append({
                    "text": result.payload.get("text", ""),
                    "filename": result.payload.get("filename", ""),
                    "page": result.payload.get("page", 0),
                    "upload_timestamp": result.payload.get("upload_timestamp", ""),
                    "document_type": result.payload.get("document_type", ""),
                    "chunk_index": result.payload.get("chunk_index", 0),
                    "score": result.score  # Similarity score
                })
            
            logger.debug(f"Search found {len(search_results)} results for query")
            return search_results
            
        except Exception as e:
            raise VectorDBError(f"Search failed: {str(e)}")
    
    def _build_qdrant_filter(self, filters: Dict[str, Any]) -> qdrant_models.Filter:
        """
        Build Qdrant filter from filter dictionary.
        
        Example filters:
            {"filename": "document.pdf"}
            {"document_type": "pdf"}
            {"page": {"gte": 1, "lte": 10}}
        """
        conditions = []
        
        for key, value in filters.items():
            if isinstance(value, dict):
                # Range filter
                if "gte" in value:
                    conditions.append(
                        qdrant_models.FieldCondition(
                            key=key,
                            range=qdrant_models.Range(gte=value["gte"])
                        )
                    )
                if "lte" in value:
                    conditions.append(
                        qdrant_models.FieldCondition(
                            key=key,
                            range=qdrant_models.Range(lte=value["lte"])
                        )
                    )
            else:
                # Equality filter
                conditions.append(
                    qdrant_models.FieldCondition(
                        key=key,
                        match=qdrant_models.MatchValue(value=value)
                    )
                )
        
        if conditions:
            return qdrant_models.Filter(must=conditions)
        
        return None
    
    def health_check(self) -> Dict[str, Any]:
        """
        Health check for Qdrant server and collection.
        
        Returns:
            Dict with health status, collection info, and metrics
        """
        try:
            # Get server info
            server_info = self.client.get_raft_info()
            
            # Get collection info
            collection_info = self.client.get_collection(
                collection_name=self.settings.QDRANT_COLLECTION_NAME
            )
            
            health_data = {
                "status": "healthy",
                "server": {
                    "is_leader": server_info.leader,
                    "peers": len(server_info.peers) if server_info.peers else 0
                },
                "collection": {
                    "name": self.settings.QDRANT_COLLECTION_NAME,
                    "vectors_count": collection_info.points_count,
                    "status": collection_info.status
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return health_data
            
        except Exception as e:
            logger.error(f"Qdrant health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def delete_collection(self) -> bool:
        """
        Delete entire collection (careful - use for cleanup/testing only).
        """
        try:
            self.client.delete_collection(
                collection_name=self.settings.QDRANT_COLLECTION_NAME
            )
            logger.info(f"Deleted collection: {self.settings.QDRANT_COLLECTION_NAME}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete collection: {str(e)}")
            return False


def get_vectorstore() -> QdrantVectorStore:
    """
    Factory function to get Qdrant vector store singleton.
    Use this instead of instantiating directly.
    """
    return QdrantVectorStore()

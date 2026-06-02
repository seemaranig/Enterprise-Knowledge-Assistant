"""
PHASE 5: Redis Caching Layer

Purpose: Cache expensive operations:
- Embeddings: Cache query embeddings to avoid recomputation
- Retrieval Results: Cache search results for identical queries
- LLM Responses: Cache generated responses
- Conversation Chunks: Cache frequently accessed context

Why Redis:
1. Sub-millisecond latency
2. In-memory persistence
3. TTL support for automatic expiration
4. Atomic operations for consistency
5. Scalable across instances with proper configuration

Caching Strategy:
- Query embedding: 24h TTL (rarely changes)
- Search results: 4h TTL (documents updated frequently)
- LLM responses: 12h TTL (can be regenerated)
- Conversation context: Session duration
"""

import json
import hashlib
from typing import Any, Dict, Optional
import redis
from datetime import datetime, timedelta

from app.config import get_settings
from app.logger import logger
from app.exceptions import VectorDBError


class CacheManager:
    """
    Manages Redis caching for enterprise RAG operations.
    
    Design Pattern: Singleton ensures single Redis connection
    Responsibility: Cache operations with TTL and serialization
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.settings = get_settings()
        self._initialized = True
        
        try:
            # Parse Redis URL
            self.redis_client = redis.from_url(
                self.settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=30
            )
            
            # Test connection
            self.redis_client.ping()
            logger.info("Redis cache connected")
            
        except Exception as e:
            logger.warning(f"Redis connection failed: {str(e)} - caching disabled")
            self.redis_client = None
    
    def _generate_key(self, prefix: str, query: str) -> str:
        """Generate cache key with hash of query."""
        query_hash = hashlib.md5(query.encode()).hexdigest()
        return f"{prefix}:{query_hash}"
    
    def cache_embedding(self, query: str, embedding: list, ttl_hours: int = 24) -> bool:
        """
        Cache query embedding.
        
        Args:
            query: Original query text
            embedding: Embedding vector
            ttl_hours: Time to live in hours
        
        Returns:
            True if cached, False if Redis unavailable
        """
        if not self.redis_client:
            return False
        
        try:
            key = self._generate_key("embedding", query)
            value = json.dumps({"query": query, "embedding": embedding})
            ttl_seconds = ttl_hours * 3600
            
            self.redis_client.setex(key, ttl_seconds, value)
            logger.debug(f"Cached embedding: {key}")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to cache embedding: {str(e)}")
            return False
    
    def get_cached_embedding(self, query: str) -> Optional[list]:
        """
        Retrieve cached embedding.
        
        Args:
            query: Query text
        
        Returns:
            Embedding vector or None if not cached
        """
        if not self.redis_client:
            return None
        
        try:
            key = self._generate_key("embedding", query)
            cached = self.redis_client.get(key)
            
            if cached:
                data = json.loads(cached)
                logger.debug(f"Retrieved cached embedding: {key}")
                return data["embedding"]
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to get cached embedding: {str(e)}")
            return None
    
    def cache_search_results(
        self,
        query: str,
        results: list,
        ttl_hours: int = 4
    ) -> bool:
        """
        Cache search results (hybrid BM25 + semantic).
        
        Args:
            query: Search query
            results: Retrieved documents
            ttl_hours: Time to live in hours
        
        Returns:
            True if cached, False if Redis unavailable
        """
        if not self.redis_client:
            return False
        
        try:
            key = self._generate_key("search_results", query)
            value = json.dumps({
                "query": query,
                "results": results,
                "timestamp": datetime.utcnow().isoformat(),
                "result_count": len(results)
            })
            ttl_seconds = ttl_hours * 3600
            
            self.redis_client.setex(key, ttl_seconds, value)
            logger.debug(f"Cached search results: {key} ({len(results)} results)")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to cache search results: {str(e)}")
            return False
    
    def get_cached_search_results(self, query: str) -> Optional[list]:
        """
        Retrieve cached search results.
        
        Args:
            query: Search query
        
        Returns:
            List of cached results or None if not cached
        """
        if not self.redis_client:
            return None
        
        try:
            key = self._generate_key("search_results", query)
            cached = self.redis_client.get(key)
            
            if cached:
                data = json.loads(cached)
                logger.debug(f"Retrieved cached search results: {key}")
                return data["results"]
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to get cached search results: {str(e)}")
            return None
    
    def cache_llm_response(
        self,
        query: str,
        response: str,
        ttl_hours: int = 12
    ) -> bool:
        """
        Cache LLM generated response.
        
        Args:
            query: Original query
            response: LLM response
            ttl_hours: Time to live in hours
        
        Returns:
            True if cached, False if Redis unavailable
        """
        if not self.redis_client:
            return False
        
        try:
            key = self._generate_key("llm_response", query)
            value = json.dumps({
                "query": query,
                "response": response,
                "timestamp": datetime.utcnow().isoformat(),
                "response_length": len(response)
            })
            ttl_seconds = ttl_hours * 3600
            
            self.redis_client.setex(key, ttl_seconds, value)
            logger.debug(f"Cached LLM response: {key}")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to cache LLM response: {str(e)}")
            return False
    
    def get_cached_llm_response(self, query: str) -> Optional[str]:
        """
        Retrieve cached LLM response.
        
        Args:
            query: Query text
        
        Returns:
            Cached response or None if not cached
        """
        if not self.redis_client:
            return None
        
        try:
            key = self._generate_key("llm_response", query)
            cached = self.redis_client.get(key)
            
            if cached:
                data = json.loads(cached)
                logger.debug(f"Retrieved cached LLM response: {key}")
                return data["response"]
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to get cached LLM response: {str(e)}")
            return None
    
    def invalidate_cache(self, pattern: str) -> int:
        """
        Invalidate cache entries matching pattern.
        
        Args:
            pattern: Redis key pattern (e.g., "search_results:*")
        
        Returns:
            Number of keys deleted
        """
        if not self.redis_client:
            return 0
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.info(f"Invalidated {deleted} cache keys for pattern: {pattern}")
                return deleted
            return 0
            
        except Exception as e:
            logger.warning(f"Failed to invalidate cache: {str(e)}")
            return 0
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check Redis health status.
        
        Returns:
            Health status dict
        """
        if not self.redis_client:
            return {
                "status": "unavailable",
                "error": "Redis not connected"
            }
        
        try:
            self.redis_client.ping()
            info = self.redis_client.info()
            
            return {
                "status": "healthy",
                "memory_used_mb": info.get("used_memory_mb", 0),
                "connected_clients": info.get("connected_clients", 0),
                "keys_count": self.redis_client.dbsize(),
                "version": info.get("redis_version", "unknown")
            }
            
        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }


def get_cache() -> CacheManager:
    """Get CacheManager singleton."""
    return CacheManager()

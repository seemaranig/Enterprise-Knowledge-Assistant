"""
PHASE 3: Hybrid Search - BM25 Keyword + Semantic

Purpose: Combine two retrieval strategies for comprehensive results:
1. BM25 (keyword-based): Fast, deterministic, good for specific terms
2. Semantic (embedding-based): Captures meaning, good for concept search

Why Hybrid Search:
- BM25 alone misses concept-based queries ("CEO's thoughts on AI")
- Semantic alone can be slower and less precise for exact matches
- Combined: Best of both worlds with configurable weights
- Enterprise requirement: Different users prefer different search types

Implementation:
1. Index documents with BM25 during ingestion
2. On query: run both searches in parallel
3. Merge results using configurable weights (default: 70% semantic, 30% BM25)
4. Return combined results with hybrid scores
5. Log retrieval metrics for observability (Phase 8)
"""

from typing import List, Dict, Any, Optional
import time
from rank_bm25 import BM25Okapi

from app.config import get_settings
from app.logger import logger
from app.exceptions import VectorDBError
from app.vectorstore import get_vectorstore


class HybridSearchEngine:
    """
    Combines BM25 keyword search with semantic search.
    
    Design Pattern: Singleton ensures single instance and consistent indexing
    Responsibility: Manage BM25 index and hybrid search operations
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize BM25 index and settings."""
        if self._initialized:
            return
        
        self.settings = get_settings()
        self._initialized = True
        self.bm25_index = None
        self.indexed_documents = []
        
        logger.info("Hybrid Search Engine initialized")
    
    def build_bm25_index(self, documents: List[Dict[str, Any]]) -> None:
        """
        Build BM25 index from documents.
        
        Called during PDF ingestion to prepare documents for keyword search.
        
        Args:
            documents: List of documents with 'text' and metadata
            
        Example:
            documents = [
                {
                    "id": "chunk-1",
                    "text": "The CEO discussed AI strategy",
                    "filename": "document.pdf",
                    "page": 1
                },
                ...
            ]
        """
        try:
            # Extract texts for BM25
            texts = [doc["text"].lower().split() for doc in documents]
            
            # Build BM25 index
            self.bm25_index = BM25Okapi(texts)
            self.indexed_documents = documents
            
            logger.info(f"BM25 index built for {len(documents)} documents")
            
        except Exception as e:
            logger.error(f"Failed to build BM25 index: {str(e)}")
            raise VectorDBError(f"BM25 indexing failed: {str(e)}")
    
    def keyword_search(
        self,
        query: str,
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        BM25 keyword-based search.
        
        Fast, deterministic search based on term frequency.
        Good for:
        - Exact keyword matches
        - Technical terms (API, database names)
        - Proper nouns (company names, people)
        
        Args:
            query: Search query
            k: Number of results
            
        Returns:
            List of results with BM25 scores (0-1 normalized)
        """
        if not self.bm25_index or not self.indexed_documents:
            logger.warning("BM25 index not available, returning empty results")
            return []
        
        try:
            query_tokens = query.lower().split()
            scores = self.bm25_index.get_scores(query_tokens)
            
            # Get top K results
            ranked_indices = sorted(
                range(len(scores)),
                key=lambda i: scores[i],
                reverse=True
            )[:k]
            
            results = []
            for idx in ranked_indices:
                doc = self.indexed_documents[idx].copy()
                doc["bm25_score"] = float(scores[idx])
                # Normalize BM25 score to 0-1 range (rough normalization)
                doc["normalized_score"] = min(float(scores[idx]) / 10, 1.0)
                results.append(doc)
            
            logger.debug(f"BM25 search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"BM25 search failed: {str(e)}")
            return []
    
    def semantic_search(
        self,
        query: str,
        k: int = 5,
        score_threshold: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Semantic search using Qdrant embeddings.
        
        Embedding-based search capturing semantic meaning.
        Good for:
        - Concept-based queries ("impact on business")
        - Paraphrased searches
        - Multi-language support (embeddings capture meaning)
        
        Args:
            query: Search query
            k: Number of results
            score_threshold: Minimum similarity score
            
        Returns:
            List of results with semantic scores (0-1)
        """
        try:
            vectorstore = get_vectorstore()
            results = vectorstore.search(
                query=query,
                k=k,
                score_threshold=score_threshold
            )
            
            logger.debug(f"Semantic search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Semantic search failed: {str(e)}")
            return []
    
    def hybrid_search(
        self,
        query: str,
        k: int = 5,
        semantic_weight: float = 0.7,
        bm25_weight: float = 0.3,
        score_threshold: float = 0.2
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining BM25 and semantic results.
        
        Algorithm:
        1. Run BM25 keyword search
        2. Run semantic search in parallel
        3. Merge results by document
        4. Calculate hybrid score: (semantic * weight) + (bm25 * weight)
        5. Sort by hybrid score
        6. Return top K
        
        Args:
            query: Search query
            k: Number of results to return
            semantic_weight: Weight for semantic scores (default: 0.7)
            bm25_weight: Weight for BM25 scores (default: 0.3)
            score_threshold: Minimum hybrid score to include
            
        Returns:
            List of merged results with hybrid scores
            
        Example:
            >>> results = hybrid_search("CEO's AI strategy")
            >>> for r in results:
            >>>     print(f"{r['text'][:50]}... (score: {r['hybrid_score']:.2f})")
        """
        start_time = time.time()
        
        try:
            # Run both searches (could be parallel for performance)
            bm25_results = self.keyword_search(query, k=k * 2)
            semantic_results = self.semantic_search(query, k=k * 2)
            
            # Merge results by document ID
            merged = {}
            
            # Add BM25 results
            for doc in bm25_results:
                doc_id = doc.get("filename") + "_" + str(doc.get("chunk_index", 0))
                merged[doc_id] = {
                    **doc,
                    "bm25_score": doc.get("normalized_score", 0),
                    "semantic_score": 0.0
                }
            
            # Add semantic results, merging with BM25
            for doc in semantic_results:
                doc_id = doc.get("filename") + "_" + str(doc.get("chunk_index", 0))
                if doc_id in merged:
                    merged[doc_id]["semantic_score"] = doc.get("score", 0)
                else:
                    merged[doc_id] = {
                        **doc,
                        "bm25_score": 0.0,
                        "semantic_score": doc.get("score", 0)
                    }
            
            # Calculate hybrid score for each result
            for doc_id, doc in merged.items():
                doc["hybrid_score"] = (
                    doc.get("semantic_score", 0) * semantic_weight +
                    doc.get("bm25_score", 0) * bm25_weight
                )
            
            # Filter by score threshold and sort
            final_results = [
                doc for doc in merged.values()
                if doc.get("hybrid_score", 0) >= score_threshold
            ]
            
            final_results.sort(
                key=lambda x: x.get("hybrid_score", 0),
                reverse=True
            )[:k]
            
            # Log metrics (Phase 8 - Langfuse ready)
            latency = time.time() - start_time
            logger.info(
                f"Hybrid search: {len(bm25_results)} BM25 + "
                f"{len(semantic_results)} semantic = "
                f"{len(final_results)} merged results ({latency:.2f}s)"
            )
            
            return final_results
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {str(e)}")
            raise VectorDBError(f"Hybrid search error: {str(e)}")


def get_hybrid_search() -> HybridSearchEngine:
    """
    Factory function to get HybridSearchEngine singleton.
    Use this instead of instantiating directly.
    """
    return HybridSearchEngine()

"""
PHASE 1, 3 & 6: Enhanced RAG Pipeline with Hybrid Search

Features:
1. Hybrid search: BM25 (keyword) + Semantic (embedding) combined
2. Configurable weights for search strategies
3. Source metadata retrieval with scoring
4. LLM response generation with context
5. Performance metrics and logging
6. Structured responses with sources (Phase 6 ready)
"""

import time
from typing import List, Dict, Any

from langchain_community.llms import Ollama

from app.config import get_settings
from app.logger import logger
from app.exceptions import (
    LLMError,
    VectorDBError,
    InvalidQueryError
)
from app.hybrid_search import get_hybrid_search  # PHASE 3: Hybrid search


def ask_question(
    query: str,
    use_rag: bool = True,
    semantic_weight: float = 0.7,
    bm25_weight: float = 0.3
) -> dict:
    """
    PHASE 1, 3 & 6: Enhanced RAG + LLM pipeline with hybrid search.
    
    Architecture:
    1. Query validation
    2. Hybrid search (BM25 + Semantic) in Qdrant
    3. Source citation preparation (Phase 6 ready)
    4. LLM response generation
    5. Structured response with metadata
    6. Performance metrics
    
    Args:
        query: User's question
        use_rag: Whether to use RAG context (default: True)
        semantic_weight: Weight for semantic search (default: 0.7)
        bm25_weight: Weight for BM25 search (default: 0.3)
    
    Returns:
        Response dict with answer, sources, and metrics
    """

    settings = get_settings()
    start_time = time.time()

    try:
        # ==========================================
        # Step 1: Validate Query
        # ==========================================
        if not query or not query.strip():
            raise InvalidQueryError("Query cannot be empty")

        logger.info(f"Processing query: {query[:100]}...")

        # ==========================================
        # Step 2: PHASE 3 - Hybrid Search
        # ==========================================
        retrieved_docs = []
        
        if use_rag:
            try:
                hybrid_search = get_hybrid_search()
                
                logger.debug("Performing hybrid search (BM25 + Semantic)")
                retrieved_docs = hybrid_search.hybrid_search(
                    query=query,
                    k=settings.RETRIEVER_K,
                    semantic_weight=semantic_weight,
                    bm25_weight=bm25_weight,
                    score_threshold=0.2
                )
                
                logger.info(
                    f"Hybrid search returned {len(retrieved_docs)} documents"
                )
                
                # Log search strategy metrics (Phase 8 - Langfuse ready)
                if retrieved_docs:
                    avg_score = sum(
                        doc.get("hybrid_score", 0) for doc in retrieved_docs
                    ) / len(retrieved_docs)
                    logger.info(f"Average hybrid score: {avg_score:.3f}")
                    
                    # Log component scores
                    semantic_avg = sum(
                        doc.get("semantic_score", 0) for doc in retrieved_docs
                    ) / len(retrieved_docs)
                    bm25_avg = sum(
                        doc.get("bm25_score", 0) for doc in retrieved_docs
                    ) / len(retrieved_docs)
                    logger.debug(
                        f"Semantic avg: {semantic_avg:.3f}, BM25 avg: {bm25_avg:.3f}"
                    )
                
            except VectorDBError as e:
                # If hybrid search fails, log and continue with LLM only
                logger.warning(f"Hybrid search failed: {str(e)}")
                logger.info("Falling back to LLM-only response")
                retrieved_docs = []
        
        # ==========================================
        # Step 3: Build Context from Retrieved Docs
        # ==========================================
        context = ""
        source_documents = []
        
        if retrieved_docs:
            context_parts = []
            
            for doc in retrieved_docs:
                # Build context string
                context_parts.append(doc.get("text", ""))
                
                # Prepare source metadata with hybrid scores (Phase 6)
                source_documents.append({
                    "document": doc.get("filename", "unknown"),
                    "page": doc.get("page", 0),
                    "score": round(doc.get("hybrid_score", 0), 3),
                    "semantic_score": round(doc.get("semantic_score", 0), 3),
                    "bm25_score": round(doc.get("bm25_score", 0), 3),
                    "chunk_index": doc.get("chunk_index", 0),
                    "upload_timestamp": doc.get("upload_timestamp", ""),
                    "document_type": doc.get("document_type", "")
                })
            
            context = "\n\n".join(context_parts)
        
        # ==========================================
        # Step 4: Build Enhanced Prompt
        # ==========================================
        if context:
            system_prompt = f"""You are an advanced enterprise AI assistant.

Your goal is to provide intelligent, accurate, and helpful answers.

IMPORTANT RULES:
1. Use retrieved document context as PRIMARY source
2. Use your reasoning and knowledge as SECONDARY support
3. If context partially answers the question, expand intelligently
4. If context is missing information, still provide a useful answer
5. Clearly mention when information comes from general knowledge
6. Be concise, professional, and accurate
7. Never hallucinate information

RETRIEVED CONTEXT (from hybrid BM25 + semantic search):
{context}

---"""
        else:
            system_prompt = """You are an advanced enterprise AI assistant.

Your goal is to provide intelligent, accurate, and helpful answers.

NOTE: No relevant documents were found in the knowledge base.
Please provide the best answer based on your general knowledge."""
        
        prompt = f"""{system_prompt}

USER QUESTION: {query}

HELPFUL ANSWER:"""
        
        # ==========================================
        # Step 5: Generate LLM Response
        # ==========================================
        try:
            logger.info("Generating LLM response")
            
            llm = Ollama(
                model=settings.OLLAMA_MODEL,
                base_url=settings.OLLAMA_BASE_URL,
                temperature=0.4
            )

            response = llm.invoke(prompt)
            
            logger.info("LLM response generated successfully")
            
        except Exception as e:
            logger.error(f"LLM generation failed: {str(e)}")
            raise LLMError(f"Failed to generate response: {str(e)}")
        
        # ==========================================
        # Step 6: Calculate Metrics
        # ==========================================
        latency = round(time.time() - start_time, 2)
        
        logger.info(
            f"Request completed in {latency}s with {len(retrieved_docs)} sources "
            f"(semantic_w={semantic_weight}, bm25_w={bm25_weight})"
        )
        
        # ==========================================
        # Step 7: Return Structured Response
        # ==========================================
        return {
            "response": response,
            "sources": source_documents,  # Phase 6: Structured source format
            "retrieved_chunks": len(retrieved_docs),
            "latency_seconds": latency,
            "model": settings.OLLAMA_MODEL,
            "search_strategy": "hybrid_bm25_semantic"  # Phase 8: Observability
        }

    except InvalidQueryError as e:
        logger.warning(f"Query validation failed: {str(e)}")
        raise

    except (VectorDBError, LLMError):
        raise

    except Exception as e:
        logger.error(f"Unexpected error in ask_question: {str(e)}")
        raise LLMError(f"Request processing failed: {str(e)}")
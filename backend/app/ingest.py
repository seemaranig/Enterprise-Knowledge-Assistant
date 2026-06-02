import os
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import get_settings
from app.logger import logger
from app.exceptions import PDFProcessingError, VectorDBError
from app.vectorstore import get_vectorstore
from app.hybrid_search import get_hybrid_search  # PHASE 3: Hybrid search


def ingest_pdf(pdf_path: str) -> int:
    """
    PHASE 1-3: Ingest PDF with Qdrant vectors + BM25 indexing.
    
    Uses:
    - PHASE 1: Qdrant for semantic vectors
    - PHASE 3: BM25 for keyword indexing
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Number of chunks created
        
    Raises:
        PDFProcessingError: If PDF processing fails
        VectorDBError: If vector DB operation fails
    """
    settings = get_settings()
    
    try:
        logger.info(f"Starting PDF ingestion: {pdf_path}")
        
        # ==========================================
        # Step 1: Validate and load PDF
        # ==========================================
        if not os.path.exists(pdf_path):
            raise PDFProcessingError(f"PDF file not found: {pdf_path}")
        
        # Get document name for metadata
        document_name = Path(pdf_path).name
        logger.info(f"Document name: {document_name}")
        
        loader = PyPDFLoader(pdf_path)
        documents = loader.load()
        logger.info(f"Loaded {len(documents)} pages from PDF")
        
        if not documents:
            raise PDFProcessingError("PDF appears to be empty")
        
        # ==========================================
        # Step 2: Split into chunks
        # ==========================================
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP
        )
        
        chunks = splitter.split_documents(documents)
        logger.info(f"Created {len(chunks)} chunks from {len(documents)} pages")
        
        # ==========================================
        # Step 3: Extract texts and metadata
        # ==========================================
        texts = [chunk.page_content for chunk in chunks]
        metadatas = [chunk.metadata for chunk in chunks]
        
        logger.debug(f"Sample metadata: {metadatas[0] if metadatas else 'None'}")
        
        # ==========================================
        # Step 4: Store in Qdrant with metadata
        # ==========================================
        try:
            vectorstore = get_vectorstore()
            chunks_added = vectorstore.add_documents(
                texts=texts,
                metadatas=metadatas,
                document_name=document_name,
                document_type="pdf"
            )
            
            if chunks_added == 0:
                raise VectorDBError("No chunks were added to vector database")
            
            logger.info(
                f"Successfully stored {chunks_added} chunks in Qdrant "
                f"for document: {document_name}"
            )
            
        except Exception as e:
            raise VectorDBError(f"Failed to store in Qdrant: {str(e)}")
        
        # ==========================================
        # Step 5: PHASE 3 - Build BM25 index
        # ==========================================
        try:
            hybrid_search = get_hybrid_search()
            
            # Prepare documents for BM25 indexing
            bm25_documents = []
            for idx, (text, metadata) in enumerate(zip(texts, metadatas)):
                bm25_documents.append({
                    "text": text,
                    "filename": document_name,
                    "page": metadata.get("page", 0),
                    "chunk_index": idx,
                    "upload_timestamp": metadata.get("upload_timestamp", ""),
                    "document_type": "pdf"
                })
            
            hybrid_search.build_bm25_index(bm25_documents)
            logger.info(f"Built BM25 index for {len(bm25_documents)} chunks")
            
        except Exception as e:
            logger.warning(f"BM25 indexing failed (non-critical): {str(e)}")
            # Don't fail PDF ingestion if BM25 fails
            # User can still query with semantic search only
        
        # ==========================================
        # Step 6: Return summary
        # ==========================================
        logger.info(f"PDF ingestion completed successfully: {chunks_added} chunks")
        return chunks_added
        
    except PDFProcessingError:
        raise
    except VectorDBError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during PDF ingestion: {str(e)}")
        raise PDFProcessingError(f"PDF ingestion failed: {str(e)}")
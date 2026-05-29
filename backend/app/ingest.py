import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

from app.config import get_settings
from app.logger import logger
from app.exceptions import PDFProcessingError, VectorDBError


def ingest_pdf(pdf_path: str) -> int:
    """
    Ingest PDF and update vector database.
    
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
        
        # Load PDF
        if not os.path.exists(pdf_path):
            raise PDFProcessingError(f"PDF file not found: {pdf_path}")
        
        loader = PyPDFLoader(pdf_path)
        documents = loader.load()
        logger.info(f"Loaded {len(documents)} pages from PDF")
        
        if not documents:
            raise PDFProcessingError("PDF appears to be empty")
        
        # Split documents
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP
        )
        
        chunks = splitter.split_documents(documents)
        logger.info(f"Created {len(chunks)} chunks")
        
        # Create embeddings
        embeddings = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL
        )
        
        # Update or create vector database
        try:
            # Try to load existing DB
            if os.path.exists(settings.VECTOR_DB_PATH):
                logger.info("Loading existing vector database")
                db = FAISS.load_local(
                    settings.VECTOR_DB_PATH,
                    embeddings,
                    allow_dangerous_deserialization=True
                )
                # Merge new chunks
                db.add_documents(chunks)
                logger.info(f"Merged {len(chunks)} new chunks to existing database")
            else:
                logger.info("Creating new vector database")
                db = FAISS.from_documents(chunks, embeddings)
                logger.info(f"Created new database with {len(chunks)} chunks")
            
            # Save database
            db.save_local(settings.VECTOR_DB_PATH)
            logger.info(f"Vector database saved to {settings.VECTOR_DB_PATH}")
            
        except Exception as e:
            raise VectorDBError(f"Failed to update vector database: {str(e)}")
        
        logger.info(f"PDF ingestion completed successfully: {len(chunks)} chunks")
        return len(chunks)
        
    except PDFProcessingError:
        raise
    except VectorDBError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during PDF ingestion: {str(e)}")
        raise PDFProcessingError(f"PDF ingestion failed: {str(e)}")
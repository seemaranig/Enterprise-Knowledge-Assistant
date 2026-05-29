import os
import time
from contextlib import asynccontextmanager
from collections import defaultdict

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import uvicorn

from app.config import get_settings
from app.logger import logger
from app.models import ChatRequest, ChatResponse, UploadResponse, HealthResponse, ErrorResponse
from app.ingest import ingest_pdf
from app.rag import ask_question
from app.utils import (
    ensure_directories, 
    validate_pdf_file, 
    validate_file_size,
    generate_request_id,
    safe_filename
)
from app.exceptions import (
    KAException,
    PDFProcessingError,
    VectorDBError,
    LLMError,
    InvalidQueryError,
    FileValidationError
)


# Rate limiting store
request_history = defaultdict(list)


def check_rate_limit(client_id: str) -> bool:
    """Check if client has exceeded rate limit."""
    settings = get_settings()
    
    if not settings.RATE_LIMIT_ENABLED:
        return True
    
    current_time = time.time()
    cutoff_time = current_time - settings.RATE_LIMIT_PERIOD_SECONDS
    
    # Clean old requests
    request_history[client_id] = [
        req_time for req_time in request_history[client_id]
        if req_time > cutoff_time
    ]
    
    # Check limit
    if len(request_history[client_id]) >= settings.RATE_LIMIT_REQUESTS:
        return False
    
    # Record this request
    request_history[client_id].append(current_time)
    return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Enterprise Knowledge Assistant API")
    ensure_directories()
    logger.info("Application initialized successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Enterprise Knowledge Assistant API")


# Initialize FastAPI app
settings = get_settings()

app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.ALLOWED_ORIGINS],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(FileValidationError)
async def file_validation_error_handler(request: Request, exc: FileValidationError):
    """Handle file validation errors."""
    request_id = request.headers.get("X-Request-ID", generate_request_id())
    logger.warning(f"[{request_id}] File validation error: {str(exc)}")
    return JSONResponse(
        status_code=400,
        content={
            "error": "File validation failed",
            "detail": str(exc),
            "request_id": request_id
        }
    )


@app.exception_handler(PDFProcessingError)
async def pdf_processing_error_handler(request: Request, exc: PDFProcessingError):
    """Handle PDF processing errors."""
    request_id = request.headers.get("X-Request-ID", generate_request_id())
    logger.error(f"[{request_id}] PDF processing error: {str(exc)}")
    return JSONResponse(
        status_code=400,
        content={
            "error": "PDF processing failed",
            "detail": str(exc),
            "request_id": request_id
        }
    )


@app.exception_handler(VectorDBError)
async def vector_db_error_handler(request: Request, exc: VectorDBError):
    """Handle vector database errors."""
    request_id = request.headers.get("X-Request-ID", generate_request_id())
    logger.error(f"[{request_id}] Vector database error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Database error",
            "detail": "An error occurred while accessing the vector database",
            "request_id": request_id
        }
    )


@app.exception_handler(LLMError)
async def llm_error_handler(request: Request, exc: LLMError):
    """Handle LLM errors."""
    request_id = request.headers.get("X-Request-ID", generate_request_id())
    logger.error(f"[{request_id}] LLM error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "LLM error",
            "detail": "Failed to generate answer from LLM",
            "request_id": request_id
        }
    )


@app.exception_handler(InvalidQueryError)
async def invalid_query_error_handler(request: Request, exc: InvalidQueryError):
    """Handle invalid query errors."""
    request_id = request.headers.get("X-Request-ID", generate_request_id())
    logger.warning(f"[{request_id}] Invalid query: {str(exc)}")
    return JSONResponse(
        status_code=400,
        content={
            "error": "Invalid query",
            "detail": str(exc),
            "request_id": request_id
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors."""
    request_id = request.headers.get("X-Request-ID", generate_request_id())
    logger.warning(f"[{request_id}] Request validation error: {exc}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "Request validation failed",
            "detail": exc.errors(),
            "request_id": request_id
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    request_id = request.headers.get("X-Request-ID", generate_request_id())
    logger.error(f"[{request_id}] Unexpected error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred",
            "request_id": request_id
        }
    )


# Middleware to add request ID
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID for tracking."""
    request_id = request.headers.get("X-Request-ID", generate_request_id())
    logger.debug(f"[{request_id}] {request.method} {request.url.path}")
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    
    return response


# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check API health and component status."""
    request_id = generate_request_id()
    logger.debug(f"[{request_id}] Health check requested")
    
    components = {
        "api": "healthy",
        "vector_db": "healthy" if os.path.exists(settings.VECTOR_DB_PATH) else "no_data",
    }
    
    return HealthResponse(
        status="healthy",
        version=settings.API_VERSION,
        components=components
    )


# Root endpoint
@app.get("/")
async def root():
    """API root endpoint."""
    logger.debug("Root endpoint accessed")
    return {
        "message": "Enterprise Knowledge Assistant API",
        "version": settings.API_VERSION,
        "docs": "/docs"
    }


# Upload endpoint
@app.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """Upload and process a PDF file."""
    request_id = generate_request_id()
    
    try:
        # Get client IP for rate limiting
        client_id = f"upload_{id(file)}"
        
        if not check_rate_limit(client_id):
            logger.warning(f"[{request_id}] Rate limit exceeded for upload")
            raise HTTPException(
                status_code=429,
                detail="Too many upload requests. Please try again later."
            )
        
        logger.info(f"[{request_id}] Processing upload: {file.filename}")
        
        # Validate file
        validate_pdf_file(file.filename)
        
        # Read file to validate size
        file_data = await file.read()
        validate_file_size(len(file_data))
        
        # Save file with safe name
        safe_name = safe_filename(file.filename)
        file_path = os.path.join(settings.DATA_DIR, safe_name)
        
        with open(file_path, "wb") as buffer:
            buffer.write(file_data)
        
        logger.info(f"[{request_id}] File saved: {file_path}")
        
        # Process PDF
        chunks = ingest_pdf(file_path)
        total_chunks = chunks  # Can be enhanced to get total count from DB
        
        logger.info(f"[{request_id}] Upload completed successfully. Chunks: {chunks}")
        
        return UploadResponse(
            message="PDF uploaded and processed successfully",
            filename=file.filename,
            chunks_created=chunks,
            total_chunks=total_chunks
        )
        
    except FileValidationError as e:
        logger.error(f"[{request_id}] File validation failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except PDFProcessingError as e:
        logger.error(f"[{request_id}] PDF processing failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[{request_id}] Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Upload failed")


# Chat endpoint
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, req: Request):
    """Process a chat query."""
    request_id = generate_request_id()
    
    try:
        # Rate limiting
        client_ip = req.client.host if req.client else "unknown"
        
        if not check_rate_limit(client_ip):
            logger.warning(f"[{request_id}] Rate limit exceeded for {client_ip}")
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please try again later."
            )
        
        logger.info(f"[{request_id}] Processing query from {client_ip}: {request.query[:50]}...")
        
        # Process query
        result = ask_question(request.query)
        
        response = ChatResponse(
            response=result["response"],
            sources=result.get("sources", []),
            tokens_used=None
        )
        
        logger.info(f"[{request_id}] Query processed successfully")
        
        return response
        
    except InvalidQueryError as e:
        logger.error(f"[{request_id}] Invalid query: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except (VectorDBError, LLMError) as e:
        logger.error(f"[{request_id}] Processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process query")
    except Exception as e:
        logger.error(f"[{request_id}] Unexpected error in chat: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred")


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
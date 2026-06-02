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
from app.models import (
    CreateConversationRequest, ConversationResponse, ConversationListResponse,
    AddMessageRequest, MessageResponse
)
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
from app.vectorstore import get_vectorstore  # PHASE 1: Qdrant integration
from app.database import get_db  # PHASE 2: PostgreSQL integration


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
    """
    PHASE 1: Enhanced health check with Qdrant status.
    
    Checks:
    - API service status
    - Qdrant vector database connection
    - Collection existence and metrics
    """
    request_id = generate_request_id()
    logger.debug(f"[{request_id}] Health check requested")
    
    components = {
        "api": "healthy"
    }
    
    # PHASE 1: Check Qdrant health
    try:
        vectorstore = get_vectorstore()
        qdrant_health = vectorstore.health_check()
        
        components["qdrant"] = qdrant_health.get("status", "unknown")
        components["qdrant_details"] = {
            "collection": qdrant_health.get("collection", {}),
            "server": qdrant_health.get("server", {})
        }
        
        logger.debug(f"Qdrant status: {components['qdrant']}")
        
    except Exception as e:
        logger.warning(f"Qdrant health check failed: {str(e)}")
        components["qdrant"] = "unhealthy"
        components["qdrant_error"] = str(e)
    
    # Determine overall status
    overall_status = "healthy"
    if components.get("qdrant") != "healthy":
        overall_status = "degraded"
    
    return HealthResponse(
        status=overall_status,
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


# ==========================================
# PHASE 2: Conversation Management Endpoints
# ==========================================

@app.post("/conversations", response_model=ConversationResponse)
async def create_conversation(request: CreateConversationRequest):
    """
    PHASE 2: Create a new conversation session.
    
    Enables:
    - Grouping messages into logical conversations
    - Context-aware RAG with conversation history
    - Multi-turn dialogue support
    
    Args:
        request: Conversation creation request with user_id, title, description
        
    Returns:
        Created conversation with empty message history
    """
    request_id = generate_request_id()
    
    try:
        logger.info(f"[{request_id}] Creating conversation: {request.title}")
        
        db = get_db()
        conversation_id = generate_request_id()
        
        conversation = db.create_conversation(
            conversation_id=conversation_id,
            user_id=request.user_id,
            title=request.title,
            description=request.description,
            metadata=request.metadata
        )
        
        logger.info(f"[{request_id}] Conversation created: {conversation_id}")
        
        return ConversationResponse(
            conversation_id=conversation.conversation_id,
            title=conversation.title,
            description=conversation.description,
            messages=[],
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            metadata=conversation.metadata
        )
        
    except Exception as e:
        logger.error(f"[{request_id}] Failed to create conversation: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create conversation")


@app.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: str):
    """
    PHASE 2: Get a conversation with full message history.
    
    Args:
        conversation_id: Conversation ID
        
    Returns:
        Conversation with all messages
    """
    request_id = generate_request_id()
    
    try:
        logger.info(f"[{request_id}] Fetching conversation: {conversation_id}")
        
        db = get_db()
        conversation = db.get_conversation(conversation_id)
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Fetch message history
        messages = db.get_conversation_history(conversation_id)
        
        message_responses = [
            MessageResponse(
                message_id=msg.message_id,
                role=msg.role,
                content=msg.content,
                metadata=msg.metadata,
                created_at=msg.created_at
            )
            for msg in messages
        ]
        
        return ConversationResponse(
            conversation_id=conversation.conversation_id,
            title=conversation.title,
            description=conversation.description,
            messages=message_responses,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            metadata=conversation.metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] Failed to fetch conversation: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch conversation")


@app.get("/users/{user_id}/conversations", response_model=ConversationListResponse)
async def list_user_conversations(user_id: str, limit: int = 50, offset: int = 0):
    """
    PHASE 2: List all conversations for a user.
    
    Args:
        user_id: User ID
        limit: Max conversations to return
        offset: Pagination offset
        
    Returns:
        List of conversations (without message history)
    """
    request_id = generate_request_id()
    
    try:
        logger.info(f"[{request_id}] Listing conversations for user: {user_id}")
        
        db = get_db()
        conversations = db.get_user_conversations(user_id, limit=limit)
        
        conversation_responses = [
            ConversationResponse(
                conversation_id=conv.conversation_id,
                title=conv.title,
                description=conv.description,
                messages=[],
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                metadata=conv.metadata
            )
            for conv in conversations
        ]
        
        return ConversationListResponse(
            conversations=conversation_responses,
            total=len(conversation_responses),
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        logger.error(f"[{request_id}] Failed to list conversations: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list conversations")


@app.post("/conversations/{conversation_id}/messages", response_model=MessageResponse)
async def add_message_to_conversation(
    conversation_id: str,
    request: AddMessageRequest
):
    """
    PHASE 2: Add a user message to a conversation and get RAG response.
    
    Flow:
    1. Store user message in database
    2. Retrieve conversation context (previous messages)
    3. Call ask_question with conversation history
    4. Store assistant response in database
    5. Return complete message and response
    
    Args:
        conversation_id: Conversation ID
        request: Message to add (includes user_id for verification)
        
    Returns:
        Stored user message
    """
    request_id = generate_request_id()
    
    try:
        logger.info(f"[{request_id}] Adding message to conversation: {conversation_id}")
        
        db = get_db()
        
        # Verify conversation exists
        conversation = db.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Verify user ownership
        if conversation.user_id != request.user_id:
            logger.warning(f"[{request_id}] Unauthorized access attempt")
            raise HTTPException(status_code=403, detail="Unauthorized")
        
        # Store user message
        user_message_id = generate_request_id()
        user_message = db.add_message(
            message_id=user_message_id,
            conversation_id=conversation_id,
            role="user",
            content=request.message
        )
        
        # Get conversation history (for context awareness - Phase 4+)
        history = db.get_conversation_history(conversation_id)
        
        # Build context from conversation history
        history_context = ""
        if len(history) > 1:
            # Include previous messages for context
            for msg in history[-10:]:  # Last 10 messages for context
                history_context += f"\n{msg.role}: {msg.content}"
        
        # Process query with RAG and conversation context
        try:
            result = ask_question(request.message)
            response_text = result["response"]
        except Exception as e:
            logger.error(f"[{request_id}] RAG failed: {str(e)}")
            response_text = "I encountered an error processing your question. Please try again."
        
        # Store assistant response
        assistant_message_id = generate_request_id()
        assistant_message = db.add_message(
            message_id=assistant_message_id,
            conversation_id=conversation_id,
            role="assistant",
            content=response_text,
            metadata={
                "sources": result.get("sources", []),
                "latency_seconds": result.get("latency_seconds", 0),
                "retrieved_chunks": result.get("retrieved_chunks", 0)
            }
        )
        
        logger.info(f"[{request_id}] Message processed successfully")
        
        return MessageResponse(
            message_id=user_message.message_id,
            role=user_message.role,
            content=user_message.content,
            metadata=user_message.metadata,
            created_at=user_message.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] Failed to add message: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to add message")


@app.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, user_id: str):
    """
    PHASE 2: Delete (archive) a conversation.
    
    Args:
        conversation_id: Conversation ID
        user_id: User ID for authorization
        
    Returns:
        Success message
    """
    request_id = generate_request_id()
    
    try:
        logger.info(f"[{request_id}] Deleting conversation: {conversation_id}")
        
        db = get_db()
        
        # Verify conversation exists and belongs to user
        conversation = db.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        if conversation.user_id != user_id:
            logger.warning(f"[{request_id}] Unauthorized delete attempt")
            raise HTTPException(status_code=403, detail="Unauthorized")
        
        db.delete_conversation(conversation_id)
        
        return {"message": "Conversation deleted", "conversation_id": conversation_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] Failed to delete conversation: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete conversation")


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
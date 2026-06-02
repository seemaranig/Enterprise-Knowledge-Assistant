from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="The user's question"
    )
    include_sources: bool = Field(
        default=True,
        description="Whether to include source documents in response"
    )
    conversation_id: Optional[str] = Field(
        None,
        description="Optional conversation ID for context awareness (Phase 2)"
    )


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str = Field(..., description="Generated answer to the query")
    sources: List[str] = Field(default_factory=list, description="Source pages")
    tokens_used: Optional[int] = Field(None, description="Tokens used in generation")


class UploadResponse(BaseModel):
    """Response model for upload endpoint."""
    message: str
    filename: str
    chunks_created: int
    total_chunks: int


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str = Field(..., description="Health status")
    version: str = Field(..., description="API version")
    components: dict = Field(..., description="Component health status")


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Error details")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")


# ==========================================
# PHASE 2: Conversation Memory Models
# ==========================================

class MessageResponse(BaseModel):
    """Response model for a single message."""
    message_id: str
    role: str  # "user" or "assistant"
    content: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    """Response model for a conversation."""
    conversation_id: str
    title: str
    description: Optional[str] = None
    messages: List[MessageResponse] = []
    created_at: datetime
    updated_at: datetime
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class CreateConversationRequest(BaseModel):
    """Request model to create a conversation."""
    user_id: str = Field(..., description="User ID")
    title: str = Field(..., min_length=1, max_length=500, description="Conversation title")
    description: Optional[str] = Field(None, max_length=2000, description="Optional description")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")


class ConversationListResponse(BaseModel):
    """Response model for list of conversations."""
    conversations: List[ConversationResponse]
    total: int
    limit: int
    offset: int


class AddMessageRequest(BaseModel):
    """Request model to add a message to a conversation."""
    conversation_id: str = Field(..., description="Conversation ID")
    user_id: str = Field(..., description="User ID for verification")
    message: str = Field(..., min_length=1, max_length=5000, description="Message content")


class MessageCreateRequest(BaseModel):
    """Internal model for adding messages."""
    message_id: str
    conversation_id: str
    role: str
    content: str
    metadata: Optional[Dict[str, Any]] = None


from pydantic import BaseModel, Field
from typing import List, Optional


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

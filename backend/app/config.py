import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration from environment variables."""
    
    # API Settings
    API_TITLE: str = "Enterprise Knowledge Assistant API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "Production-grade RAG API for enterprise document Q&A"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # CORS Settings
    ALLOWED_ORIGINS: list = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:8501,http://localhost:3000"
    ).split(",")
    
    # Model Settings
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    EMBEDDING_MODEL: str = os.getenv(
        "EMBEDDING_MODEL",
        "sentence-transformers/all-MiniLM-L6-v2"
    )
    
    # Storage Settings
    VECTOR_DB_PATH: str = os.getenv("VECTOR_DB_PATH", "vectorstore/faiss_index")
    DATA_DIR: str = os.getenv("DATA_DIR", "data")
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
    
    # PHASE 1: Qdrant Vector Database Settings
    # Why Qdrant: Production-grade vector DB with metadata support, scalability, and filtering
    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_COLLECTION_NAME: str = os.getenv("QDRANT_COLLECTION_NAME", "enterprise_knowledge")
    QDRANT_TIMEOUT: int = int(os.getenv("QDRANT_TIMEOUT", "30"))
    QDRANT_BATCH_SIZE: int = int(os.getenv("QDRANT_BATCH_SIZE", "100"))
    
    # PHASE 2: PostgreSQL Database Settings
    # Why PostgreSQL: ACID compliance, JSON support, scalability, full-text search
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://knowledge_user:knowledge_password_secure@localhost:5432/enterprise_knowledge"
    )
    
    # PHASE 5: Redis Cache Settings
    # Why Redis: In-memory caching for embeddings, retrieval results, LLM responses
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_CACHE_TTL_SECONDS: int = int(os.getenv("REDIS_CACHE_TTL_SECONDS", "3600"))
    
    # PHASE 8: Langfuse Observability Settings
    # Why Langfuse: Open-source observability for LLM applications
    LANGFUSE_SECRET_KEY: str = os.getenv("LANGFUSE_SECRET_KEY", "")
    LANGFUSE_PUBLIC_KEY: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    LANGFUSE_HOST: str = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
    
    # PHASE 9: Security Settings
    # Why JWT: Stateless authentication for distributed systems
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRATION_HOURS: int = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
    
    # RAG Settings
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "500"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "50"))
    RETRIEVER_K: int = int(os.getenv("RETRIEVER_K", "3"))
    
    # PHASE 3: Hybrid Search Settings
    # Why Hybrid: BM25 for keywords, semantic for concepts, combined for best results
    SEMANTIC_WEIGHT: float = float(os.getenv("SEMANTIC_WEIGHT", "0.7"))
    BM25_WEIGHT: float = float(os.getenv("BM25_WEIGHT", "0.3"))
    HYBRID_SEARCH_ENABLED: bool = os.getenv("HYBRID_SEARCH_ENABLED", "True").lower() == "true"
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "True").lower() == "true"
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_PERIOD_SECONDS: int = int(os.getenv("RATE_LIMIT_PERIOD_SECONDS", "60"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
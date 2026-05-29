"""Streamlit configuration and setup."""

import os
from functools import lru_cache
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class Config:
    """Frontend configuration."""
    
    # API Settings
    API_URL: str = os.getenv("API_URL", "http://localhost:8000")
    API_TIMEOUT: int = int(os.getenv("API_TIMEOUT", "120"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY: int = int(os.getenv("RETRY_DELAY", "1"))
    
    # Upload Settings
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
    ALLOWED_FILE_TYPES: list = field(default_factory=lambda: ["pdf"])
    
    # UI Settings
    PAGE_TITLE: str = "Enterprise Knowledge Assistant"
    PAGE_LAYOUT: str = "wide"
    THEME: str = os.getenv("THEME", "light")
    
    # Query Settings
    MIN_QUERY_LENGTH: int = 1
    MAX_QUERY_LENGTH: int = 1000
    DEFAULT_SOURCES_LIMIT: int = 5
    
    # Session Settings
    SESSION_STATE_TIMEOUT: int = 3600  # 1 hour
    ENABLE_SESSION_STATE: bool = True
    
    # Feature Flags
    SHOW_ADVANCED_OPTIONS: bool = os.getenv("SHOW_ADVANCED_OPTIONS", "False").lower() == "true"
    ENABLE_CHAT_HISTORY: bool = os.getenv("ENABLE_CHAT_HISTORY", "True").lower() == "true"
    ENABLE_FEEDBACK: bool = os.getenv("ENABLE_FEEDBACK", "False").lower() == "true"
    
    # Security
    ENABLE_HTTPS: bool = os.getenv("ENABLE_HTTPS", "False").lower() == "true"
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    ENABLE_LOGS: bool = True


@lru_cache(maxsize=1)
def get_config() -> Config:
    """Get cached configuration instance."""
    return Config()


def validate_config() -> tuple[bool, Optional[str]]:
    """Validate configuration on startup."""
    config = get_config()
    
    # Check API URL
    if not config.API_URL:
        return False, "API_URL is not configured"
    
    # Validate timeout values
    if config.API_TIMEOUT < 10:
        return False, "API_TIMEOUT must be >= 10 seconds"
    
    if config.MAX_RETRIES < 0:
        return False, "MAX_RETRIES must be >= 0"
    
    # Validate upload size
    if config.MAX_UPLOAD_SIZE_MB < 1:
        return False, "MAX_UPLOAD_SIZE_MB must be >= 1"
    
    # Validate query lengths
    if config.MAX_QUERY_LENGTH < config.MIN_QUERY_LENGTH:
        return False, "MAX_QUERY_LENGTH must be >= MIN_QUERY_LENGTH"
    
    return True, None

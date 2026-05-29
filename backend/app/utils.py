import os
import uuid
from pathlib import Path
from app.config import get_settings
from app.logger import logger
from app.exceptions import FileValidationError


def ensure_directories():
    """Ensure required directories exist."""
    settings = get_settings()
    
    directories = [
        settings.DATA_DIR,
        settings.VECTOR_DB_PATH,
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logger.debug(f"Directory ensured: {directory}")


def validate_pdf_file(filename: str) -> bool:
    """Validate PDF file."""
    if not filename:
        raise FileValidationError("Filename cannot be empty")
    
    if not filename.lower().endswith('.pdf'):
        raise FileValidationError("File must be a PDF")
    
    # Check for path traversal attempts
    if ".." in filename or "/" in filename or "\\" in filename:
        raise FileValidationError("Invalid filename: potential path traversal")
    
    return True


def validate_file_size(file_size: int, max_size_mb: int = None) -> bool:
    """Validate file size."""
    settings = get_settings()
    max_size = max_size_mb or settings.MAX_UPLOAD_SIZE_MB
    max_bytes = max_size * 1024 * 1024
    
    if file_size > max_bytes:
        raise FileValidationError(
            f"File size exceeds maximum of {max_size}MB"
        )
    
    return True


def generate_request_id() -> str:
    """Generate unique request ID for tracking."""
    return str(uuid.uuid4())


def safe_filename(filename: str) -> str:
    """Generate safe filename with unique ID."""
    name, ext = os.path.splitext(filename)
    # Remove special characters and add uuid
    safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_'))
    return f"{safe_name}_{uuid.uuid4().hex[:8]}{ext}"
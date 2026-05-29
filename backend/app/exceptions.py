"""Custom exceptions for the Enterprise Knowledge Assistant API."""


class KAException(Exception):
    """Base exception for the application."""
    pass


class PDFProcessingError(KAException):
    """Raised when PDF processing fails."""
    pass


class VectorDBError(KAException):
    """Raised when vector database operations fail."""
    pass


class LLMError(KAException):
    """Raised when LLM operations fail."""
    pass


class InvalidQueryError(KAException):
    """Raised when query validation fails."""
    pass


class FileValidationError(KAException):
    """Raised when file validation fails."""
    pass


class ConfigurationError(KAException):
    """Raised when configuration is invalid."""
    pass

"""API client for communicating with the backend."""

import requests
from typing import Dict, Any, Optional, Tuple
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time

from config import get_config
from logger import logger


class APIClient:
    """Production-grade API client with retry logic and error handling."""
    
    def __init__(self):
        """Initialize API client with retry strategy."""
        self.config = get_config()
        self.session = self._create_session()
        self._last_error: Optional[str] = None
    
    def _create_session(self) -> requests.Session:
        """Create requests session with retry strategy."""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.config.MAX_RETRIES,
            backoff_factor=self.config.RETRY_DELAY,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "HEAD"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def health_check(self) -> Tuple[bool, str]:
        """
        Check if API is healthy.
        
        Returns:
            Tuple of (is_healthy, message)
        """
        try:
            logger.debug(f"Checking API health: {self.config.API_URL}/health")
            response = self.session.get(
                f"{self.config.API_URL}/health",
                timeout=self.config.API_TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get("status", "unknown")
                return status == "healthy", f"API Status: {status}"
            else:
                error_msg = f"Health check failed with status {response.status_code}"
                logger.error(error_msg)
                self._last_error = error_msg
                return False, error_msg
                
        except requests.ConnectionError as e:
            error_msg = f"Cannot connect to API at {self.config.API_URL}. Is the backend running?"
            logger.error(f"{error_msg}: {str(e)}")
            self._last_error = error_msg
            return False, error_msg
        except requests.Timeout:
            error_msg = f"API health check timed out (timeout: {self.config.API_TIMEOUT}s)"
            logger.error(error_msg)
            self._last_error = error_msg
            return False, error_msg
        except Exception as e:
            error_msg = f"Health check error: {str(e)}"
            logger.error(error_msg)
            self._last_error = error_msg
            return False, error_msg
    
    def upload_pdf(self, filename: str, file_content: bytes) -> Tuple[bool, Dict[str, Any]]:
        """
        Upload a PDF file to the backend.
        
        Args:
            filename: Name of the PDF file
            file_content: Binary content of the file
            
        Returns:
            Tuple of (success, response_data)
        """
        try:
            # Validate file
            if not filename.lower().endswith('.pdf'):
                error_msg = "File must be a PDF"
                logger.warning(f"Upload validation failed: {error_msg}")
                self._last_error = error_msg
                return False, {"error": error_msg}
            
            # Check file size
            file_size_mb = len(file_content) / (1024 * 1024)
            if file_size_mb > self.config.MAX_UPLOAD_SIZE_MB:
                error_msg = f"File size ({file_size_mb:.2f}MB) exceeds maximum ({self.config.MAX_UPLOAD_SIZE_MB}MB)"
                logger.warning(f"Upload validation failed: {error_msg}")
                self._last_error = error_msg
                return False, {"error": error_msg}
            
            logger.info(f"Uploading PDF: {filename} ({file_size_mb:.2f}MB)")
            
            files = {
                "file": (filename, file_content, "application/pdf")
            }
            
            response = self.session.post(
                f"{self.config.API_URL}/upload",
                files=files,
                timeout=self.config.API_TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Upload successful: {data.get('chunks_created', 0)} chunks created")
                return True, data
            else:
                error_msg = response.json().get("detail", f"Upload failed with status {response.status_code}")
                logger.error(f"Upload failed: {error_msg}")
                self._last_error = error_msg
                return False, {"error": error_msg}
                
        except requests.Timeout:
            error_msg = f"Upload timed out after {self.config.API_TIMEOUT}s"
            logger.error(error_msg)
            self._last_error = error_msg
            return False, {"error": error_msg}
        except requests.ConnectionError as e:
            error_msg = f"Connection error during upload: {str(e)}"
            logger.error(error_msg)
            self._last_error = error_msg
            return False, {"error": "Cannot connect to API"}
        except Exception as e:
            error_msg = f"Upload error: {str(e)}"
            logger.error(error_msg)
            self._last_error = error_msg
            return False, {"error": error_msg}
    
    def chat(self, query: str, include_sources: bool = True) -> Tuple[bool, Dict[str, Any]]:
        """
        Send a query to the backend and get an answer.
        
        Args:
            query: The user's question
            include_sources: Whether to include source documents
            
        Returns:
            Tuple of (success, response_data)
        """
        try:
            # Validate query
            if not query or not query.strip():
                error_msg = "Query cannot be empty"
                logger.warning(error_msg)
                self._last_error = error_msg
                return False, {"error": error_msg}
            
            if len(query) > self.config.MAX_QUERY_LENGTH:
                error_msg = f"Query exceeds maximum length of {self.config.MAX_QUERY_LENGTH} characters"
                logger.warning(error_msg)
                self._last_error = error_msg
                return False, {"error": error_msg}
            
            logger.info(f"Sending query: {query[:50]}...")
            
            payload = {
                "query": query,
                "include_sources": include_sources
            }
            
            response = self.session.post(
                f"{self.config.API_URL}/chat",
                json=payload,
                timeout=self.config.API_TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Query successful, received {len(data.get('sources', []))} sources")
                return True, data
            else:
                error_msg = response.json().get("detail", f"Query failed with status {response.status_code}")
                logger.error(f"Query failed: {error_msg}")
                self._last_error = error_msg
                return False, {"error": error_msg}
                
        except requests.Timeout:
            error_msg = f"Query timed out after {self.config.API_TIMEOUT}s. Try a simpler query."
            logger.error(error_msg)
            self._last_error = error_msg
            return False, {"error": error_msg}
        except requests.ConnectionError as e:
            error_msg = f"Connection error during query: {str(e)}"
            logger.error(error_msg)
            self._last_error = error_msg
            return False, {"error": "Cannot connect to API"}
        except Exception as e:
            error_msg = f"Query error: {str(e)}"
            logger.error(error_msg)
            self._last_error = error_msg
            return False, {"error": error_msg}
    
    def get_last_error(self) -> Optional[str]:
        """Get the last error message."""
        return self._last_error
    
    def close(self):
        """Close the session."""
        self.session.close()


# Global API client instance
_api_client: Optional[APIClient] = None


def get_api_client() -> APIClient:
    """Get or create the global API client instance."""
    global _api_client
    if _api_client is None:
        _api_client = APIClient()
    return _api_client

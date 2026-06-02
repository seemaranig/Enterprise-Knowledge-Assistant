"""
PHASE 8: Langfuse OSS Observability & PHASE 9: Security

This file provides the core infrastructure for:
1. Observability: Request tracing, prompt logging, metrics
2. Security: JWT authentication, role-based access control
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from passlib.context import CryptContext

from app.config import get_settings
from app.logger import logger


# ==========================================
# PHASE 8: Langfuse Integration
# ==========================================

class ObservabilityManager:
    """
    Integrates Langfuse for observability.
    
    Tracks:
    - Request tracing (trace_id for full request lifecycle)
    - Prompt logging (LLM inputs/outputs)
    - Retrieval metrics (search latency, scores)
    - Latency metrics (end-to-end, per component)
    - Error tracking (failures and recovery)
    """
    
    def __init__(self):
        self.settings = get_settings()
        
        try:
            from langfuse import Langfuse
            
            if self.settings.LANGFUSE_SECRET_KEY:
                self.langfuse = Langfuse(
                    secret_key=self.settings.LANGFUSE_SECRET_KEY,
                    public_key=self.settings.LANGFUSE_PUBLIC_KEY,
                    host=self.settings.LANGFUSE_HOST
                )
                logger.info("Langfuse observability enabled")
            else:
                self.langfuse = None
                logger.info("Langfuse not configured")
                
        except Exception as e:
            logger.warning(f"Langfuse initialization failed: {str(e)}")
            self.langfuse = None
    
    def log_query(
        self,
        trace_id: str,
        query: str,
        response: str,
        latency_ms: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log RAG query to Langfuse."""
        if not self.langfuse:
            return
        
        try:
            self.langfuse.log_event(
                name="rag_query",
                input={"query": query},
                output={"response": response},
                metadata={
                    "latency_ms": latency_ms,
                    "trace_id": trace_id,
                    **(metadata or {})
                }
            )
        except Exception as e:
            logger.debug(f"Langfuse logging failed: {str(e)}")
    
    def log_retrieval(
        self,
        trace_id: str,
        query: str,
        results_count: int,
        latency_ms: float,
        scores: Optional[list] = None
    ) -> None:
        """Log retrieval metrics to Langfuse."""
        if not self.langfuse:
            return
        
        try:
            avg_score = sum(scores) / len(scores) if scores else 0
            
            self.langfuse.log_event(
                name="retrieval_metrics",
                metadata={
                    "trace_id": trace_id,
                    "query": query,
                    "results_count": results_count,
                    "latency_ms": latency_ms,
                    "avg_score": avg_score
                }
            )
        except Exception as e:
            logger.debug(f"Langfuse retrieval logging failed: {str(e)}")


def get_observability() -> ObservabilityManager:
    """Get ObservabilityManager instance."""
    return ObservabilityManager()


# ==========================================
# PHASE 9: JWT Authentication & RBAC
# ==========================================

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class SecurityManager:
    """
    Handles authentication and authorization.
    
    Features:
    - JWT token generation and validation
    - Password hashing with bcrypt
    - Role-based access control (RBAC)
    - Token expiration and refresh
    """
    
    def __init__(self):
        self.settings = get_settings()
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    def create_access_token(
        self,
        user_id: str,
        username: str,
        role: str = "user",
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create JWT access token.
        
        Args:
            user_id: User identifier
            username: Username
            role: User role (user, admin)
            expires_delta: Custom expiration time
            
        Returns:
            JWT token string
        """
        if expires_delta is None:
            expires_delta = timedelta(hours=self.settings.JWT_EXPIRATION_HOURS)
        
        expire = datetime.utcnow() + expires_delta
        
        to_encode = {
            "sub": user_id,
            "username": username,
            "role": role,
            "exp": expire
        }
        
        encoded_jwt = jwt.encode(
            to_encode,
            self.settings.JWT_[REDACTED_GENERIC_SECRET_1],
            algorithm=self.settings.JWT_ALGORITHM
        )
        
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            Token payload dict or None if invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.settings.JWT_[REDACTED_GENERIC_SECRET_1],
                algorithms=[self.settings.JWT_ALGORITHM]
            )
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Invalid token")
            return None
    
    def check_permission(self, user_role: str, required_role: str) -> bool:
        """
        Check if user has required role.
        
        Role hierarchy: user < admin
        
        Args:
            user_role: User's role
            required_role: Required role for action
            
        Returns:
            True if user has sufficient permissions
        """
        role_hierarchy = {"user": 1, "admin": 2}
        
        user_level = role_hierarchy.get(user_role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        return user_level >= required_level


def get_security() -> SecurityManager:
    """Get SecurityManager instance."""
    return SecurityManager()

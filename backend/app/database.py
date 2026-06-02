"""
PHASE 2: PostgreSQL Database & Conversation Memory

Purpose: Persistent storage for:
- User accounts and profiles
- Conversation sessions
- Message history
- Session-based memory management

Why PostgreSQL:
1. ACID compliance for reliable transactions
2. JSON support for flexible schema
3. Full-text search capabilities
4. Scalable for enterprise deployments
5. Excellent Python ORM support (SQLAlchemy)

Architecture:
- Users: Account management
- Conversations: Chat sessions grouped by context
- Messages: Individual messages with metadata
"""

from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, ForeignKey, JSON, Boolean
from sqlalchemy.orm import declarative_base, relationship, Session
from sqlalchemy.pool import StaticPool
from typing import Optional, List

from app.config import get_settings
from app.logger import logger

# SQLAlchemy ORM base class
Base = declarative_base()


class User(Base):
    """
    User account model.
    
    Attributes:
        user_id: Unique user identifier
        username: Username for authentication
        email: User email
        created_at: Account creation timestamp
        updated_at: Last update timestamp
        role: User role (user, admin) for Phase 9 RBAC
        is_active: Account active status
        
    Relationships:
        conversations: User's conversations
    """
    
    __tablename__ = "users"
    
    user_id = Column(String(36), primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    role = Column(String(50), default="user", nullable=False)  # Phase 9: RBAC
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(user_id={self.user_id}, username={self.username})>"


class Conversation(Base):
    """
    Conversation session model.
    
    Groups messages into logical conversations.
    Enables context-aware RAG with conversation history.
    
    Attributes:
        conversation_id: Unique conversation identifier
        user_id: Foreign key to user
        title: Human-readable conversation title
        description: Optional description
        created_at: Conversation creation timestamp
        updated_at: Last message timestamp
        metadata: JSON field for flexible data (document_context, tags, etc.)
        is_archived: Soft delete flag
        
    Relationships:
        user: Related user
        messages: Messages in this conversation
    """
    
    __tablename__ = "conversations"
    
    conversation_id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    metadata = Column(JSON, default={}, nullable=True)  # Flexible schema for tags, context
    is_archived = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Conversation(conversation_id={self.conversation_id}, title={self.title})>"


class Message(Base):
    """
    Individual message model.
    
    Stores all user queries and AI responses.
    Enables conversation history and context injection.
    
    Attributes:
        message_id: Unique message identifier
        conversation_id: Foreign key to conversation
        role: "user" or "assistant"
        content: Message text
        metadata: JSON field for:
            - source_documents: Retrieved documents
            - retrieval_score: Average relevance score
            - model_used: Which LLM generated response
            - latency_seconds: Response time
            - tokens_used: Token count (when available)
        created_at: Message timestamp
        
    Relationships:
        conversation: Related conversation
    """
    
    __tablename__ = "messages"
    
    message_id = Column(String(36), primary_key=True, index=True)
    conversation_id = Column(String(36), ForeignKey("conversations.conversation_id"), nullable=False, index=True)
    role = Column(String(50), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    metadata = Column(JSON, default={}, nullable=True)  # Stores sources, scores, latency, etc.
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    
    def __repr__(self):
        return f"<Message(message_id={self.message_id}, role={self.role})>"


class DatabaseManager:
    """
    Singleton manager for PostgreSQL database operations.
    
    Design Pattern: Singleton ensures single database connection pool
    Responsibility: Create tables, manage sessions, provide CRUD operations
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize database engine and create tables."""
        if self._initialized:
            return
        
        self.settings = get_settings()
        self._initialized = True
        
        try:
            # Create SQLAlchemy engine
            self.engine = create_engine(
                self.settings.DATABASE_URL,
                echo=self.settings.DEBUG,
                pool_pre_ping=True,  # Test connections before use
                pool_size=10,  # Connection pool size
                max_overflow=20  # Max overflow connections
            )
            
            # Create all tables
            Base.metadata.create_all(self.engine)
            
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
            raise
    
    def get_session(self) -> Session:
        """
        Get a new database session.
        
        Returns:
            SQLAlchemy Session
        """
        from sqlalchemy.orm import sessionmaker
        Session = sessionmaker(bind=self.engine)
        return Session()
    
    def create_user(self, user_id: str, username: str, email: str, role: str = "user") -> User:
        """
        Create a new user.
        
        Args:
            user_id: Unique user ID (UUID)
            username: Username
            email: Email address
            role: User role (default: "user")
            
        Returns:
            Created User object
        """
        session = self.get_session()
        try:
            user = User(
                user_id=user_id,
                username=username,
                email=email,
                role=role
            )
            session.add(user)
            session.commit()
            logger.info(f"Created user: {username}")
            return user
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to create user: {str(e)}")
            raise
        finally:
            session.close()
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        session = self.get_session()
        try:
            user = session.query(User).filter(User.user_id == user_id).first()
            return user
        finally:
            session.close()
    
    def create_conversation(
        self,
        conversation_id: str,
        user_id: str,
        title: str,
        description: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> Conversation:
        """
        Create a new conversation.
        
        Args:
            conversation_id: Unique conversation ID (UUID)
            user_id: User ID (foreign key)
            title: Conversation title
            description: Optional description
            metadata: Optional metadata (JSON)
            
        Returns:
            Created Conversation object
        """
        session = self.get_session()
        try:
            conversation = Conversation(
                conversation_id=conversation_id,
                user_id=user_id,
                title=title,
                description=description,
                metadata=metadata or {}
            )
            session.add(conversation)
            session.commit()
            logger.info(f"Created conversation: {title}")
            return conversation
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to create conversation: {str(e)}")
            raise
        finally:
            session.close()
    
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get conversation by ID."""
        session = self.get_session()
        try:
            conversation = session.query(Conversation).filter(
                Conversation.conversation_id == conversation_id
            ).first()
            return conversation
        finally:
            session.close()
    
    def get_user_conversations(self, user_id: str, limit: int = 50) -> List[Conversation]:
        """
        Get all conversations for a user.
        
        Args:
            user_id: User ID
            limit: Max conversations to return
            
        Returns:
            List of Conversation objects
        """
        session = self.get_session()
        try:
            conversations = session.query(Conversation).filter(
                Conversation.user_id == user_id,
                Conversation.is_archived == False
            ).order_by(Conversation.updated_at.desc()).limit(limit).all()
            return conversations
        finally:
            session.close()
    
    def add_message(
        self,
        message_id: str,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[dict] = None
    ) -> Message:
        """
        Add a message to a conversation.
        
        Args:
            message_id: Unique message ID (UUID)
            conversation_id: Conversation ID (foreign key)
            role: "user" or "assistant"
            content: Message content
            metadata: Optional metadata (sources, scores, etc.)
            
        Returns:
            Created Message object
        """
        session = self.get_session()
        try:
            message = Message(
                message_id=message_id,
                conversation_id=conversation_id,
                role=role,
                content=content,
                metadata=metadata or {}
            )
            session.add(message)
            session.commit()
            
            # Update conversation's updated_at timestamp
            session.query(Conversation).filter(
                Conversation.conversation_id == conversation_id
            ).update({"updated_at": datetime.utcnow()})
            session.commit()
            
            logger.debug(f"Added {role} message to conversation: {conversation_id}")
            return message
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to add message: {str(e)}")
            raise
        finally:
            session.close()
    
    def get_conversation_history(self, conversation_id: str, limit: int = 100) -> List[Message]:
        """
        Get message history for a conversation.
        
        Args:
            conversation_id: Conversation ID
            limit: Max messages to return
            
        Returns:
            List of Message objects in chronological order
        """
        session = self.get_session()
        try:
            messages = session.query(Message).filter(
                Message.conversation_id == conversation_id
            ).order_by(Message.created_at.asc()).limit(limit).all()
            return messages
        finally:
            session.close()
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete (archive) a conversation and its messages.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            True if successful
        """
        session = self.get_session()
        try:
            session.query(Conversation).filter(
                Conversation.conversation_id == conversation_id
            ).update({"is_archived": True})
            session.commit()
            logger.info(f"Archived conversation: {conversation_id}")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to archive conversation: {str(e)}")
            return False
        finally:
            session.close()


def get_db() -> DatabaseManager:
    """
    Factory function to get DatabaseManager singleton.
    Use this instead of instantiating directly.
    """
    return DatabaseManager()

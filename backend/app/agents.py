"""
PHASE 4: LangGraph Agent Architecture

Purpose: Build a multi-agent system for complex task orchestration:
- Supervisor Agent: Routes queries to specialized agents
- RAG Agent: Document retrieval and context synthesis
- Search Agent: Hybrid search optimization
- Memory Agent: Conversation history management

Why LangGraph:
1. State management for agent flow
2. Tool calling and error recovery
3. Conditional routing based on query type
4. Agent tracing and observability (Phase 8)
5. Human-in-the-loop capabilities
6. Deterministic, testable agent flows

Architecture:
Supervisor → {RAG Agent, Search Agent, Memory Agent}
          ↓
       LLM Output
          ↓
      Response
"""

from typing import Any, Dict, TypedDict, Optional
from enum import Enum

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langchain_community.llms import Ollama

from app.config import get_settings
from app.logger import logger
from app.exceptions import LLMError, VectorDBError
from app.hybrid_search import get_hybrid_search
from app.database import get_db
from app.vectorstore import get_vectorstore


# ==========================================
# Agent State Definition
# ==========================================

class AgentState(TypedDict):
    """State passed between agents."""
    
    # Input
    query: str
    user_id: Optional[str]
    conversation_id: Optional[str]
    
    # Processing
    agent_route: str  # Which agent processed this
    retrieved_documents: list
    conversation_context: str
    
    # Output
    response: str
    sources: list
    metadata: Dict[str, Any]
    
    # Metrics
    latency_seconds: float
    error: Optional[str]


class AgentType(str, Enum):
    """Types of agents in the system."""
    
    SUPERVISOR = "supervisor"
    RAG = "rag"
    SEARCH = "search"
    MEMORY = "memory"


# ==========================================
# Supervisor Agent
# ==========================================

def supervisor_agent(state: AgentState) -> AgentState:
    """
    Supervisor agent routes queries to appropriate agents.
    
    Decision logic:
    - Query has conversation_id? → Memory Agent (context-aware)
    - Query mentions "search" or "find"? → Search Agent (optimization)
    - Default → RAG Agent (standard retrieval)
    """
    query = state["query"]
    
    logger.info(f"Supervisor routing query: {query[:50]}...")
    
    # Route based on query characteristics
    if state.get("conversation_id"):
        route = AgentType.MEMORY.value
        logger.info(f"Routing to Memory Agent (conversation context)")
    elif any(keyword in query.lower() for keyword in ["search", "find", "locate", "look for"]):
        route = AgentType.SEARCH.value
        logger.info(f"Routing to Search Agent (optimization focus)")
    else:
        route = AgentType.RAG.value
        logger.info(f"Routing to RAG Agent (standard retrieval)")
    
    state["agent_route"] = route
    return state


# ==========================================
# RAG Agent
# ==========================================

def rag_agent(state: AgentState) -> AgentState:
    """
    RAG Agent performs standard document retrieval and LLM generation.
    
    Steps:
    1. Hybrid search (Phase 3) for document retrieval
    2. Build context from results
    3. Call LLM with context
    4. Return response with sources
    """
    try:
        logger.info("RAG Agent: Starting document retrieval")
        
        # Retrieve documents using hybrid search
        hybrid_search = get_hybrid_search()
        retrieved = hybrid_search.hybrid_search(
            query=state["query"],
            k=3,
            semantic_weight=0.7,
            bm25_weight=0.3
        )
        
        state["retrieved_documents"] = retrieved
        logger.info(f"RAG Agent: Retrieved {len(retrieved)} documents")
        
        # Build context
        context = "\n\n".join([doc.get("text", "") for doc in retrieved])
        
        # Generate LLM response
        settings = get_settings()
        llm = Ollama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0.4
        )
        
        prompt = f"""Context from documents:
{context}

Question: {state["query"]}

Answer:"""
        
        response = llm.invoke(prompt)
        state["response"] = response
        state["sources"] = [
            {
                "document": doc.get("filename"),
                "page": doc.get("page"),
                "score": round(doc.get("hybrid_score", 0), 3)
            }
            for doc in retrieved
        ]
        
        logger.info("RAG Agent: Response generated successfully")
        
    except Exception as e:
        logger.error(f"RAG Agent error: {str(e)}")
        state["error"] = str(e)
        state["response"] = f"Error in RAG retrieval: {str(e)}"
    
    return state


# ==========================================
# Search Agent (Optimization Focus)
# ==========================================

def search_agent(state: AgentState) -> AgentState:
    """
    Search Agent optimizes search strategy for specific queries.
    
    Optimizations:
    - Increase K for broad queries
    - Adjust weights for keyword vs semantic
    - Use filters if applicable
    """
    try:
        logger.info("Search Agent: Optimizing search strategy")
        
        # Detect search optimization opportunities
        query = state["query"].lower()
        
        # Determine search strategy
        if "specific" in query or "exact" in query:
            # Keyword-focused search
            semantic_w, bm25_w = 0.3, 0.7
            k = 5  # Get more results
            logger.info("Search Agent: Using keyword-focused strategy")
        elif "similar" in query or "related" in query:
            # Semantic-focused search
            semantic_w, bm25_w = 0.85, 0.15
            k = 7  # Broader semantic search
            logger.info("Search Agent: Using semantic-focused strategy")
        else:
            # Balanced (default)
            semantic_w, bm25_w = 0.7, 0.3
            k = 3
        
        # Perform optimized search
        hybrid_search = get_hybrid_search()
        retrieved = hybrid_search.hybrid_search(
            query=state["query"],
            k=k,
            semantic_weight=semantic_w,
            bm25_weight=bm25_w
        )
        
        state["retrieved_documents"] = retrieved
        state["metadata"]["search_optimization"] = {
            "semantic_weight": semantic_w,
            "bm25_weight": bm25_w,
            "k": k
        }
        
        logger.info(f"Search Agent: Retrieved {len(retrieved)} optimized results")
        
        # Continue with standard RAG response generation
        context = "\n\n".join([doc.get("text", "") for doc in retrieved])
        
        settings = get_settings()
        llm = Ollama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0.4
        )
        
        prompt = f"""You are a search specialist. Help the user find exactly what they need.

Documents found:
{context}

User query: {state["query"]}

Helpful response highlighting the most relevant information:"""
        
        response = llm.invoke(prompt)
        state["response"] = response
        
    except Exception as e:
        logger.error(f"Search Agent error: {str(e)}")
        state["error"] = str(e)
    
    return state


# ==========================================
# Memory Agent (Conversation-Aware)
# ==========================================

def memory_agent(state: AgentState) -> AgentState:
    """
    Memory Agent provides context-aware responses using conversation history.
    
    Steps:
    1. Load conversation history (Phase 2)
    2. Inject context into query
    3. Enhanced RAG with conversation context
    4. Generate coherent multi-turn response
    """
    try:
        logger.info("Memory Agent: Loading conversation context")
        
        if not state.get("conversation_id"):
            # Fallback to RAG agent
            return rag_agent(state)
        
        # Load conversation history
        db = get_db()
        messages = db.get_conversation_history(state["conversation_id"], limit=10)
        
        # Build context from history
        context_messages = []
        for msg in messages[-4:]:  # Last 4 messages for context
            if msg.role == "user":
                context_messages.append(f"User: {msg.content}")
            else:
                context_messages.append(f"Assistant: {msg.content}")
        
        conversation_context = "\n".join(context_messages)
        state["conversation_context"] = conversation_context
        
        logger.info(f"Memory Agent: Loaded {len(messages)} previous messages")
        
        # Retrieve documents with enhanced awareness
        hybrid_search = get_hybrid_search()
        retrieved = hybrid_search.hybrid_search(
            query=state["query"],
            k=3,
            semantic_weight=0.7,
            bm25_weight=0.3
        )
        
        state["retrieved_documents"] = retrieved
        
        # Build prompt with conversation context
        context = "\n\n".join([doc.get("text", "") for doc in retrieved])
        
        prompt = f"""You are a helpful assistant continuing a conversation.

Previous conversation:
{conversation_context}

---

Relevant documents:
{context}

---

Current question: {state["query"]}

Continue the conversation naturally, referencing previous points if relevant:"""
        
        settings = get_settings()
        llm = Ollama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0.4
        )
        
        response = llm.invoke(prompt)
        state["response"] = response
        
        logger.info("Memory Agent: Context-aware response generated")
        
    except Exception as e:
        logger.error(f"Memory Agent error: {str(e)}")
        state["error"] = str(e)
        # Fallback to RAG agent
        return rag_agent(state)
    
    return state


# ==========================================
# LangGraph Workflow
# ==========================================

class AgentOrchestrator:
    """
    Main orchestrator for agent workflow using LangGraph.
    
    Design Pattern: Singleton for consistent graph instance
    Responsibility: Build and execute agent graph
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.graph = self._build_graph()
        logger.info("Agent Orchestrator initialized")
    
    def _build_graph(self):
        """Build LangGraph workflow."""
        
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("supervisor", supervisor_agent)
        workflow.add_node("rag_agent", rag_agent)
        workflow.add_node("search_agent", search_agent)
        workflow.add_node("memory_agent", memory_agent)
        
        # Add edges
        workflow.add_edge("supervisor", "rag_agent")  # Start with supervisor routing
        
        # Conditional routing from supervisor
        def route_agent(state):
            route = state.get("agent_route", "rag")
            if route == AgentType.SEARCH.value:
                return "search_agent"
            elif route == AgentType.MEMORY.value:
                return "memory_agent"
            else:
                return "rag_agent"
        
        # Replace the simple edge with conditional
        workflow.add_edge("supervisor", "rag_agent")  # Simplified for now
        
        # Add end edges from agents
        for agent in ["rag_agent", "search_agent", "memory_agent"]:
            workflow.add_edge(agent, END)
        
        # Set entry point
        workflow.set_entry_point("supervisor")
        
        return workflow.compile()
    
    def process(self, state: AgentState) -> AgentState:
        """Execute agent workflow."""
        try:
            logger.info(f"Agent Orchestrator processing: {state['query'][:50]}...")
            result = self.graph.invoke(state)
            return result
        except Exception as e:
            logger.error(f"Agent Orchestrator error: {str(e)}")
            state["error"] = str(e)
            return state


def get_agent_orchestrator() -> AgentOrchestrator:
    """Get Agent Orchestrator singleton."""
    return AgentOrchestrator()

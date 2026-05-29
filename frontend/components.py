"""Reusable UI components for the Streamlit frontend."""

import streamlit as st
from typing import Optional, Callable
from logger import logger


def show_info_banner(message: str, icon: str = "ℹ️"):
    """Display an information banner."""
    st.info(f"{icon} {message}")


def show_success_banner(message: str, icon: str = "✅"):
    """Display a success banner."""
    st.success(f"{icon} {message}")


def show_warning_banner(message: str, icon: str = "⚠️"):
    """Display a warning banner."""
    st.warning(f"{icon} {message}")


def show_error_banner(message: str, icon: str = "❌"):
    """Display an error banner."""
    st.error(f"{icon} {message}")


def show_loading_message(message: str = "Processing..."):
    """Display a loading message with spinner."""
    with st.spinner(message):
        return True


def upload_section() -> Optional[bytes]:
    """
    Render the PDF upload section.
    
    Returns:
        File content if uploaded, None otherwise
    """
    st.sidebar.markdown("---")
    st.sidebar.header("📄 Upload Document")
    
    uploaded_file = st.sidebar.file_uploader(
        "Upload a PDF file",
        type=["pdf"],
        help="Maximum file size depends on backend configuration"
    )
    
    if uploaded_file is not None:
        st.sidebar.markdown(f"""
        **File Info:**
        - Name: {uploaded_file.name}
        - Size: {uploaded_file.size / 1024 / 1024:.2f} MB
        """)
        
        return uploaded_file.getvalue()
    
    return None


def query_section() -> Optional[str]:
    """
    Render the query input section.
    
    Returns:
        Query string if entered, None otherwise
    """
    st.markdown("---")
    st.header("🤖 Ask Questions")
    
    col1, col2 = st.columns([4, 1])
    
    with col1:
        query = st.text_input(
            "Enter your question",
            placeholder="What is this document about?",
            help="Ask any question about the uploaded documents"
        )
    
    with col2:
        submit_button = st.button("🔍 Ask", use_container_width=True)
    
    return query if submit_button and query else None


def display_response(response: str, sources: list) -> None:
    """
    Display the API response in a formatted way.
    
    Args:
        response: The generated answer
        sources: List of source documents
    """
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📝 Answer")
        st.write(response)
    
    if sources:
        with col2:
            st.subheader("📚 Sources")
            for i, source in enumerate(sources[:5], 1):
                st.write(f"- {source}")


def show_api_status(is_healthy: bool, message: str) -> None:
    """
    Display API connection status.
    
    Args:
        is_healthy: Whether API is healthy
        message: Status message
    """
    if is_healthy:
        st.sidebar.success(f"✅ Connected: {message}")
    else:
        st.sidebar.error(f"❌ Disconnected: {message}")
        with st.sidebar.expander("Troubleshooting"):
            st.markdown("""
            **Connection Issues?**
            
            1. Ensure backend is running:
               ```bash
               docker-compose up backend
               ```
            
            2. Check if Ollama is running:
               ```bash
               ollama serve
               ```
            
            3. Verify API URL in .env:
               ```bash
               API_URL=http://localhost:8000
               ```
            
            4. Check backend logs:
               ```bash
               docker-compose logs backend
               ```
            """)


def show_chat_history(history: list) -> None:
    """
    Display chat history.
    
    Args:
        history: List of chat messages
    """
    if history:
        st.markdown("---")
        st.subheader("💬 Chat History")
        
        for i, item in enumerate(reversed(history), 1):
            with st.expander(f"Q{len(history) - i + 1}: {item['query'][:50]}..."):
                st.write(f"**Question:** {item['query']}")
                st.write(f"**Answer:** {item['response']}")
                if item['sources']:
                    st.write(f"**Sources:** {', '.join(item['sources'])}")


def show_loading_animation(message: str = "Loading...") -> None:
    """Show a loading animation."""
    with st.spinner(message):
        import time
        time.sleep(0.5)


def sidebar_info() -> None:
    """Display information in the sidebar."""
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    ### 📚 Help
    
    **How to use:**
    1. Upload a PDF file using the upload button
    2. Ask questions about the document
    3. Get AI-powered answers with sources
    
    **Tips:**
    - Use clear, specific questions
    - Reference specific sections
    - Ask follow-up questions
    
    **Issues?** Check the troubleshooting section above.
    """)
    
    st.sidebar.markdown("---")
    st.sidebar.caption("Enterprise Knowledge Assistant v1.0.0")

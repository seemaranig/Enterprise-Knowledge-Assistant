"""
Enterprise Knowledge Assistant - Production Frontend

A Streamlit-based web interface for interacting with the enterprise 
knowledge assistant backend. Supports PDF upload, document Q&A, and 
history tracking.
"""

import streamlit as st
from typing import Optional, List, Dict, Any
import time

from config import get_config, validate_config
from logger import logger
from api_client import get_api_client
from components import (
    show_info_banner,
    show_success_banner,
    show_warning_banner,
    show_error_banner,
    upload_section,
    query_section,
    display_response,
    show_api_status,
    show_chat_history,
    sidebar_info,
)


def initialize_session():
    """Initialize Streamlit session state."""
    config = get_config()
    
    if not config.ENABLE_SESSION_STATE:
        return
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    if "uploaded_files" not in st.session_state:
        st.session_state.uploaded_files = []
    
    if "api_client" not in st.session_state:
        st.session_state.api_client = get_api_client()
    
    if "api_healthy" not in st.session_state:
        st.session_state.api_healthy = None


def setup_page():
    """Configure Streamlit page settings."""
    config = get_config()
    
    st.set_page_config(
        page_title=config.PAGE_TITLE,
        layout=config.PAGE_LAYOUT,
        initial_sidebar_state="expanded",
        menu_items={
            "Get Help": "https://github.com/",
            "Report a bug": "https://github.com/",
            "About": "Enterprise Knowledge Assistant v1.0.0"
        }
    )
    
    # Custom CSS for better styling
    st.markdown("""
    <style>
        .main {
            padding-top: 2rem;
        }
        .stButton > button {
            width: 100%;
        }
        .success-box {
            padding: 1rem;
            border-radius: 0.5rem;
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
        }
        .error-box {
            padding: 1rem;
            border-radius: 0.5rem;
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
        }
    </style>
    """, unsafe_allow_html=True)


def check_api_health():
    """Check and display API health status."""
    api_client = st.session_state.get("api_client", get_api_client())
    is_healthy, message = api_client.health_check()
    
    st.session_state.api_health = is_healthy
    show_api_status(is_healthy, message)
    
    return is_healthy


def handle_file_upload():
    """Handle PDF file upload."""
    config = get_config()
    api_client = st.session_state.get("api_client", get_api_client())
    
    file_content = upload_section()
    
    if file_content is not None:
        # Check if API is healthy
        if not st.session_state.get("api_health"):
            show_error_banner("Cannot upload: Backend is not accessible")
            logger.warning("Upload attempted with unhealthy API")
            return
        
        # Get filename from session state (we need to use a workaround)
        col1, col2 = st.sidebar.columns([3, 1])
        with col1:
            custom_name = st.sidebar.text_input("File name", value="document.pdf")
        
        if st.sidebar.button("📤 Upload", use_container_width=True):
            logger.info(f"Uploading file: {custom_name}")
            
            with st.spinner("📤 Uploading and processing PDF..."):
                success, response = api_client.upload_pdf(custom_name, file_content)
            
            if success:
                st.session_state.uploaded_files.append(custom_name)
                show_success_banner(
                    f"✅ PDF uploaded successfully! "
                    f"({response.get('chunks_created', 0)} chunks created)"
                )
                logger.info(f"Upload successful: {custom_name}")
            else:
                error_msg = response.get("error", "Unknown error")
                show_error_banner(f"Upload failed: {error_msg}")
                logger.error(f"Upload failed: {error_msg}")


def handle_query():
    """Handle user query."""
    config = get_config()
    api_client = st.session_state.get("api_client", get_api_client())
    
    query = query_section()
    
    if query:
        # Check if API is healthy
        if not st.session_state.get("api_health"):
            show_error_banner("Cannot query: Backend is not accessible")
            logger.warning("Query attempted with unhealthy API")
            return
        
        # Check if documents uploaded
        if not st.session_state.uploaded_files:
            show_warning_banner("⚠️ Please upload a PDF first!")
            return
        
        logger.info(f"Processing query: {query[:50]}...")
        
        with st.spinner("🤖 Generating answer..."):
            success, response = api_client.chat(query, include_sources=True)
        
        if success:
            answer = response.get("response", "")
            sources = response.get("sources", [])
            
            # Store in history
            if config.ENABLE_CHAT_HISTORY:
                st.session_state.chat_history.append({
                    "query": query,
                    "response": answer,
                    "sources": sources,
                    "timestamp": time.time()
                })
            
            # Display response
            display_response(answer, sources)
            logger.info(f"Query processed successfully")
        else:
            error_msg = response.get("error", "Unknown error")
            show_error_banner(f"❌ Error: {error_msg}")
            logger.error(f"Query failed: {error_msg}")


def main():
    """Main application function."""
    # Setup
    setup_page()
    initialize_session()
    
    # Validate configuration
    is_valid, error_msg = validate_config()
    if not is_valid:
        show_error_banner(f"Configuration error: {error_msg}")
        logger.error(f"Configuration validation failed: {error_msg}")
        return
    
    config = get_config()
    
    # Title and intro
    st.markdown("""
    # 🚀 Enterprise Knowledge Assistant
    
    Ask questions about your documents and get instant AI-powered answers.
    """)
    
    # Show welcome banner
    if not st.session_state.uploaded_files:
        show_info_banner(
            "👈 Upload a PDF file in the sidebar to get started!",
            icon="ℹ️"
        )
    
    # Sidebar
    with st.sidebar:
        st.title("🎛️ Control Panel")
        
        # API Health Check
        st.subheader("API Status")
        if st.button("🔄 Check Connection", use_container_width=True):
            check_api_health()
        else:
            # Auto-check on first load
            if st.session_state.api_health is None:
                check_api_health()
        
        # Upload section
        if config.SHOW_ADVANCED_OPTIONS:
            st.subheader("Advanced Options")
            include_sources = st.checkbox("Include sources", value=True)
        
        # Info section
        sidebar_info()
    
    # Main content
    st.markdown("---")
    
    # Handle uploads
    handle_file_upload()
    
    # Handle queries
    handle_query()
    
    # Show chat history
    if config.ENABLE_CHAT_HISTORY and st.session_state.chat_history:
        show_chat_history(st.session_state.chat_history)
    
    # Footer
    st.markdown("---")
    st.caption("""
    Enterprise Knowledge Assistant v1.0.0 | 
    Powered by FastAPI, Streamlit, and Ollama
    """)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        show_error_banner(f"An unexpected error occurred: {str(e)}")
        st.stop()
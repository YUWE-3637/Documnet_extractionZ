"""
Streamlit UI for Production RAG System
Multi-user document Q&A interface
"""

import streamlit as st
import requests
import os
from datetime import datetime

# API Configuration
RAG_API_URL = os.getenv("RAG_API_URL", "http://localhost:8001")

st.set_page_config(
    page_title="Document Q&A System",
    page_icon="🔍",
    layout="centered"
)

st.title("🔍 Document Q&A System")
st.caption("Upload documents and ask questions with AI-powered search")

# User ID input (in production, this would come from authentication)
user_id = st.text_input(
    "Your User ID",
    value="user_demo",
    help="Enter a unique identifier (in production, this would be automatic)"
)

if not user_id:
    st.warning("Please enter a User ID to continue")
    st.stop()

st.divider()

# Tabs for upload and query
tab1, tab2, tab3 = st.tabs(["📤 Upload Documents", "💬 Ask Questions", "📊 My Stats"])

with tab1:
    st.subheader("Upload Document")
    
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["pdf", "txt"],
        help="Upload PDF or text documents"
    )
    
    if uploaded_file is not None:
        st.info(f"📄 **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB)")
        
        if st.button("🚀 Upload & Index", type="primary"):
            with st.spinner("Processing document..."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
                    headers = {"user_id": user_id}
                    
                    response = requests.post(
                        f"{RAG_API_URL}/upload-document",
                        files=files,
                        headers=headers,
                        timeout=120
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        st.success("✅ Document indexed successfully!")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Chunks Created", result.get("chunks_processed", 0))
                        with col2:
                            st.metric("Shard Date", result.get("shard_date", "N/A"))
                    else:
                        st.error(f"❌ Upload failed: {response.status_code}")
                        st.code(response.text)
                
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

with tab2:
    st.subheader("Ask a Question")
    
    query = st.text_area(
        "Your Question",
        placeholder="What are the key terms in my rental agreement?",
        height=100
    )
    
    col1, col2 = st.columns([3, 1])
    with col1:
        top_k = st.slider("Number of sources to retrieve", 3, 10, 5)
    
    if st.button("🔍 Search & Answer", type="primary", disabled=not query):
        with st.spinner("Searching documents and generating answer..."):
            try:
                headers = {"user_id": user_id}
                payload = {
                    "query": query,
                    "top_k": top_k
                }
                
                response = requests.post(
                    f"{RAG_API_URL}/query",
                    json=payload,
                    headers=headers,
                    timeout=60
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if result.get("success"):
                        st.success("✅ Answer generated")
                        
                        # Display answer
                        st.markdown("### 💡 Answer")
                        st.markdown(result.get("answer", "No answer"))
                        
                        st.divider()
                        
                        # Display sources
                        sources = result.get("sources", [])
                        if sources:
                            st.markdown("### 📚 Sources")
                            
                            for source in sources:
                                with st.expander(
                                    f"📄 {source.get('document_name')} - Page {source.get('page_number')} "
                                    f"(Relevance: {source.get('relevance_score', 0):.2f})"
                                ):
                                    st.text(source.get("chunk_preview", ""))
                        
                        st.caption(f"Retrieved {result.get('chunks_retrieved', 0)} chunks")
                    else:
                        st.warning(result.get("answer", "No documents found"))
                else:
                    st.error(f"❌ Query failed: {response.status_code}")
                    st.code(response.text)
            
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

with tab3:
    st.subheader("Your Statistics")
    
    if st.button("🔄 Refresh Stats"):
        try:
            headers = {"user_id": user_id}
            response = requests.get(
                f"{RAG_API_URL}/user-stats",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                stats = response.json()
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Chunks", stats.get("total_chunks", 0))
                with col2:
                    st.metric("Active Shards", stats.get("active_shards", 0))
                with col3:
                    st.metric("Retention", f"{stats.get('retention_days', 3)} days")
                
                st.info("📅 Data older than 3 days is automatically deleted")
            else:
                st.error(f"Failed to load stats: {response.status_code}")
        
        except Exception as e:
            st.error(f"Error: {str(e)}")

st.divider()

with st.expander("ℹ️ About This System"):
    st.markdown("""
    **Features:**
    - 🔒 Multi-user isolation (your documents are private)
    - 📅 Automatic 3-day retention (old data auto-deletes)
    - ⚡ Fast FAISS vector search
    - 🎯 AI-powered answers with source citations
    
    **How it works:**
    1. Upload your documents (PDF or text)
    2. System chunks and indexes them with embeddings
    3. Ask questions in natural language
    4. Get answers with exact source citations
    
    **Privacy:**
    - Documents are stored for 3 days only
    - Each user's data is completely isolated
    - Daily cleanup runs automatically at 2 AM
    """)

st.caption("Powered by FAISS + OpenAI + FastAPI")

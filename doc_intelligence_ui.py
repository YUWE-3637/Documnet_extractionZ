"""
Document Intelligence System - Professional Streamlit UI
Enterprise-grade SaaS legal-tech dashboard
"""

import streamlit as st
import requests
import os
from datetime import datetime
import json

# API Configuration
API_URL = os.getenv("DOC_INTELLIGENCE_API", "http://localhost:8003")

# Page Configuration
st.set_page_config(
    page_title="Document Intelligence System",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #1E1E1E;
        padding: 2rem 1rem;
    }
    
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
        color: #FFFFFF;
    }
    
    /* Main content */
    .main-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1rem 0 2rem 0;
        border-bottom: 2px solid #E0E0E0;
        margin-bottom: 2rem;
    }
    
    .doc-title {
        font-size: 2rem;
        font-weight: 700;
        color: #1E1E1E;
    }
    
    .status-badge {
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.9rem;
    }
    
    .status-active {
        background-color: #10B981;
        color: white;
    }
    
    .status-expired {
        background-color: #EF4444;
        color: white;
    }
    
    /* Card styling */
    .detail-card {
        background: #F9FAFB;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border-left: 4px solid #3B82F6;
    }
    
    .card-label {
        font-size: 0.85rem;
        color: #6B7280;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.5rem;
    }
    
    .card-value {
        font-size: 1.1rem;
        color: #1F2937;
        font-weight: 600;
    }
    
    /* Risk levels */
    .risk-high {
        color: #DC2626;
        font-weight: 700;
    }
    
    .risk-medium {
        color: #F59E0B;
        font-weight: 700;
    }
    
    .risk-low {
        color: #10B981;
        font-weight: 700;
    }
    
    /* Chat styling */
    .chat-message {
        padding: 1rem;
        border-radius: 12px;
        margin-bottom: 1rem;
    }
    
    .user-message {
        background: #3B82F6;
        color: white;
        margin-left: 2rem;
    }
    
    .ai-message {
        background: #F3F4F6;
        color: #1F2937;
        margin-right: 2rem;
    }
    
    /* Button styling */
    .stButton>button {
        border-radius: 8px;
        padding: 0.6rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s;
    }
    
    /* Navigation */
    .nav-item {
        padding: 0.75rem 1rem;
        margin: 0.5rem 0;
        border-radius: 8px;
        cursor: pointer;
        transition: background 0.3s;
    }
    
    .nav-item:hover {
        background: #374151;
    }
    
    .nav-item-active {
        background: #3B82F6;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'current_document' not in st.session_state:
    st.session_state.current_document = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# ========== SIDEBAR NAVIGATION ==========
with st.sidebar:
    st.markdown("# 📄 DocIntel")
    st.markdown("---")
    
    # Navigation menu
    menu_items = {
        "🏠 Home": "home",
        "📁 Documents": "documents",
        "📋 Contracts": "contracts",
        "📊 Reports": "reports",
        "⚙️ Settings": "settings"
    }
    
    selected_page = st.radio(
        "Navigation",
        options=list(menu_items.keys()),
        index=2,  # Default to Contracts
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    # Upload section in sidebar
    st.markdown("### 📤 Upload Document")
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["pdf", "png", "jpg", "jpeg", "txt"],
        label_visibility="collapsed"
    )
    
    if uploaded_file and st.button("Process Document", use_container_width=True):
        with st.spinner("Processing..."):
            try:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
                response = requests.post(
                    f"{API_URL}/api/v1/document/upload",
                    files=files,
                    timeout=120
                )
                
                if response.status_code == 200:
                    result = response.json()
                    st.session_state.current_document = result
                    st.session_state.chat_history = []
                    st.success("✅ Document processed!")
                    st.rerun()
                else:
                    st.error(f"Upload failed: {response.status_code}")
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    st.markdown("---")
    st.caption("v1.0.0 | Enterprise Edition")

# ========== MAIN CONTENT AREA ==========
if st.session_state.current_document:
    doc = st.session_state.current_document
    
    # Header with title and status
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.markdown(f"<h1 class='doc-title'>{doc['filename']}</h1>", unsafe_allow_html=True)
    with col2:
        st.markdown("<span class='status-badge status-active'>Active</span>", unsafe_allow_html=True)
    with col3:
        if st.button("🗑️ Delete", use_container_width=True):
            st.session_state.current_document = None
            st.rerun()
    
    st.markdown("<div style='margin-bottom: 2rem;'></div>", unsafe_allow_html=True)
    
    # Two-column layout
    left_panel, right_panel = st.columns([3, 2])
    
    # ========== LEFT PANEL: DOCUMENT PREVIEW ==========
    with left_panel:
        st.markdown("### 📄 Document Preview")
        
        with st.container():
            st.info(f"**Document ID:** {doc['document_id']}")
            st.info(f"**Pages:** {doc['pages']}")
            st.info(f"**Status:** Processed ({doc['extracted_text_length']:,} characters)")
            
            # Show first part of extracted text
            if st.checkbox("Show extracted text"):
                st.text_area(
                    "Extracted Content",
                    value=f"[First 1000 characters]\n\n{doc.get('preview_text', 'Processing...')[:1000]}...",
                    height=400,
                    disabled=True
                )
    
    # ========== RIGHT PANEL: TABBED INSIGHTS ==========
    with right_panel:
        st.markdown("### 🔍 AI Insights")
        
        tab1, tab2, tab3 = st.tabs(["📋 Key Details", "📊 Summary", "💬 Chat Assistant"])
        
        # ===== TAB 1: KEY DETAILS =====
        with tab1:
            if st.button("🔄 Extract Key Details", key="extract_details"):
                with st.spinner("Analyzing document..."):
                    try:
                        response = requests.post(
                            f"{API_URL}/api/v1/document/key-details",
                            json={"document_id": doc['document_id']},
                            timeout=60
                        )
                        
                        if response.status_code == 200:
                            details = response.json()
                            
                            # Document Type
                            st.markdown("#### 📄 Document Type")
                            st.markdown(f"**{details['document_type']}**")
                            
                            # Parties
                            st.markdown("#### 👥 Parties Involved")
                            for party in details['parties_involved']:
                                st.markdown(f"- {party}")
                            
                            # Dates
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown("#### 📅 Issued Date")
                                st.markdown(f"**{details['issued_date'] or 'N/A'}**")
                            with col2:
                                st.markdown("#### ⏰ Expiry Date")
                                st.markdown(f"**{details['expiry_date'] or 'N/A'}**")
                            
                            # Risk Level
                            st.markdown("#### ⚠️ Risk Level")
                            risk_class = f"risk-{details['risk_level'].lower()}"
                            st.markdown(f"<span class='{risk_class}'>{details['risk_level']}</span>", unsafe_allow_html=True)
                            
                            # Obligations
                            st.markdown("#### 📌 Key Obligations")
                            for obligation in details['key_obligations']:
                                st.markdown(f"- {obligation}")
                            
                            # Payment Terms
                            st.markdown("#### 💰 Payment Terms")
                            st.markdown(f"**{details['payment_terms']}**")
                            
                        else:
                            st.error(f"Failed: {response.status_code}")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
        
        # ===== TAB 2: SUMMARY =====
        with tab2:
            if st.button("📝 Generate Summary", key="generate_summary"):
                with st.spinner("Analyzing risks..."):
                    try:
                        response = requests.post(
                            f"{API_URL}/api/v1/document/summary",
                            json={
                                "document_id": doc['document_id'],
                                "highlight_risks": True
                            },
                            timeout=60
                        )
                        
                        if response.status_code == 200:
                            summary = response.json()
                            
                            # Executive Summary
                            st.markdown("#### 📋 Executive Summary")
                            st.info(summary['executive_summary'])
                            
                            # Key Clauses
                            st.markdown("#### 📑 Key Clauses")
                            for clause in summary['key_clauses']:
                                st.markdown(f"- {clause}")
                            
                            # Risk Analysis
                            st.markdown("#### ⚠️ Risk Analysis")
                            risk_data = summary['risk_analysis']
                            
                            risk_class = f"risk-{risk_data['risk_level'].lower()}"
                            st.markdown(f"**Overall Risk:** <span class='{risk_class}'>{risk_data['risk_level']}</span>", unsafe_allow_html=True)
                            
                            st.markdown("**Risk Flags:**")
                            for flag in risk_data['risk_flags']:
                                st.warning(f"🚩 {flag}")
                        else:
                            st.error(f"Failed: {response.status_code}")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
        
        # ===== TAB 3: CHAT ASSISTANT =====
        with tab3:
            st.markdown("#### 💡 Ask anything about this document")
            
            # Quick questions
            st.markdown("**Quick Questions:**")
            quick_questions = [
                "What are the main risks?",
                "Who are the parties involved?",
                "What are the payment terms?",
                "What are the key obligations?"
            ]
            
            for i, q in enumerate(quick_questions):
                if st.button(q, key=f"quick_{i}"):
                    st.session_state.chat_history.append({"role": "user", "content": q})
            
            # Display chat history
            for msg in st.session_state.chat_history:
                if msg['role'] == 'user':
                    st.markdown(f"<div class='chat-message user-message'>👤 {msg['content']}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='chat-message ai-message'>🤖 {msg['content']}</div>", unsafe_allow_html=True)
            
            # Chat input
            user_question = st.text_input(
                "Your question",
                placeholder="Ask anything about this document...",
                key="chat_input"
            )
            
            if st.button("Send", key="send_chat") and user_question:
                with st.spinner("Thinking..."):
                    try:
                        # Prepare chat history
                        history = [
                            {"role": msg['role'], "content": msg['content']}
                            for msg in st.session_state.chat_history
                        ]
                        
                        response = requests.post(
                            f"{API_URL}/api/v1/document/chat",
                            json={
                                "document_id": doc['document_id'],
                                "question": user_question,
                                "chat_history": history
                            },
                            timeout=60
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            
                            # Add to chat history
                            st.session_state.chat_history.append({"role": "user", "content": user_question})
                            st.session_state.chat_history.append({"role": "assistant", "content": result['answer']})
                            
                            st.rerun()
                        else:
                            st.error(f"Failed: {response.status_code}")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

else:
    # No document loaded - show welcome screen
    st.markdown("# 📄 Document Intelligence System")
    st.markdown("### Enterprise-grade document analysis platform")
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 📤 Upload")
        st.markdown("Upload your legal or financial documents in PDF or image format.")
    
    with col2:
        st.markdown("### 🔍 Analyze")
        st.markdown("AI extracts key details, analyzes risks, and generates summaries.")
    
    with col3:
        st.markdown("### 💬 Chat")
        st.markdown("Ask questions about your documents and get instant answers.")
    
    st.markdown("---")
    
    st.info("👈 Upload a document from the sidebar to get started")
    
    # Feature highlights
    st.markdown("### ✨ Features")
    
    features = [
        "🔒 **Multi-document support** - Manage multiple contracts simultaneously",
        "🎯 **Smart key details extraction** - Parties, dates, obligations, payment terms",
        "⚠️ **Risk analysis** - Identify legal, financial, and compliance risks",
        "📊 **Executive summaries** - Quick overviews of lengthy documents",
        "💬 **Document chat** - Ask questions in natural language",
        "🚀 **Fast processing** - Optimized for text-based and scanned PDFs"
    ]
    
    for feature in features:
        st.markdown(feature)

import streamlit as st
import requests
import os
from datetime import datetime
import json

# API Configuration
API_URL = os.getenv("API_URL", "http://localhost:8003")

st.set_page_config(
    page_title="Document Intelligence System",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        background-color: #2563eb;
        color: white;
        font-weight: 600;
        padding: 0.75rem;
        border-radius: 8px;
        border: none;
        font-size: 1rem;
    }
    .stButton>button:hover {
        background-color: #1d4ed8;
    }
    .risk-high { color: #DC2626; font-weight: 700; }
    .risk-medium { color: #F59E0B; font-weight: 700; }
    .risk-low { color: #10B981; font-weight: 700; }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'document_id' not in st.session_state:
    st.session_state.document_id = None
if 'document_filename' not in st.session_state:
    st.session_state.document_filename = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

st.title("📄 Document Intelligence System")
st.caption("AI-powered analysis: Key Details, Summary & Chat with your documents")

st.divider()

# ========== DOCUMENT UPLOAD SECTION ==========
uploaded_file = st.file_uploader(
    "Upload Document (PDF, PNG, JPG)",
    type=["pdf", "png", "jpg", "jpeg"],
    help="Supports single and multi-page PDFs"
)

if uploaded_file is not None:
    st.info(f"📄 **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB)")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("🔍 Process Document", type="primary"):
            with st.spinner("Processing document... Please wait."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    
                    response = requests.post(
                        f"{API_URL}/api/v1/document/upload",
                        files=files,
                        timeout=300
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        st.session_state.document_id = result['document_id']
                        st.session_state.document_filename = result['filename']
                        st.session_state.chat_history = []
                        st.success(f"✅ Document processed! ({result['pages']} pages, {result['extracted_text_length']:,} characters)")
                        st.rerun()
                    else:
                        st.error(f"❌ Upload failed: {response.status_code}")
                        st.code(response.text)
                
                except requests.exceptions.Timeout:
                    st.error("⏱️ Request timed out. Document may be too large.")
                except requests.exceptions.ConnectionError:
                    st.error(f"🔌 Cannot connect to API. Ensure server is running at {API_URL}")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    with col2:
        if st.session_state.document_id:
            if st.button("🗑️ Clear"):
                st.session_state.document_id = None
                st.session_state.document_filename = None
                st.session_state.chat_history = []
                st.rerun()

# ========== 3-TAB INTERFACE (ONLY IF DOCUMENT IS LOADED) ==========
if st.session_state.document_id:
    st.divider()
    st.markdown(f"### Analyzing: **{st.session_state.document_filename}**")
    st.caption(f"Document ID: `{st.session_state.document_id}`")
    
    tab1, tab2, tab3 = st.tabs(["📋 Key Details", "📊 Summary", "💬 Chat Assistant"])
    
    # ========== TAB 1: KEY DETAILS ==========
    with tab1:
        st.markdown("### 📋 Key Details Extraction")
        st.caption("Extract structured information: parties, dates, obligations, payment terms")
        
        if st.button("🔄 Extract Key Details", key="extract_details"):
            with st.spinner("Analyzing document structure..."):
                try:
                    response = requests.post(
                        f"{API_URL}/api/v1/document/key-details",
                        json={"document_id": st.session_state.document_id},
                        timeout=60
                    )
                    
                    if response.status_code == 200:
                        details = response.json()
                        
                        # Display in organized layout
                        st.success("✅ Key details extracted successfully!")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("#### 📄 Document Type")
                            st.info(details['document_type'])
                            
                            st.markdown("#### 👥 Parties Involved")
                            for party in details['parties_involved']:
                                st.write(f"• {party}")
                            
                            st.markdown("#### ⚠️ Risk Level")
                            risk_class = f"risk-{details['risk_level'].lower()}"
                            st.markdown(f"<h3 class='{risk_class}'>{details['risk_level']}</h3>", unsafe_allow_html=True)
                        
                        with col2:
                            st.markdown("#### 📅 Issued Date")
                            st.info(details['issued_date'] or 'Not specified')
                            
                            st.markdown("#### ⏰ Expiry Date")
                            st.info(details['expiry_date'] or 'Not specified')
                            
                            st.markdown("#### 💰 Payment Terms")
                            st.info(details['payment_terms'])
                        
                        st.markdown("#### 📌 Key Obligations")
                        for obligation in details['key_obligations']:
                            st.write(f"• {obligation}")
                        
                    else:
                        st.error(f"❌ Failed: {response.status_code}")
                        st.code(response.text)
                
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    # ========== TAB 2: SUMMARY ==========
    with tab2:
        st.markdown("### 📊 Document Summary & Risk Analysis")
        st.caption("Executive summary with comprehensive risk assessment")
        
        if st.button("📝 Generate Summary", key="generate_summary"):
            with st.spinner("Analyzing risks and generating summary..."):
                try:
                    response = requests.post(
                        f"{API_URL}/api/v1/document/summary",
                        json={
                            "document_id": st.session_state.document_id,
                            "highlight_risks": True
                        },
                        timeout=60
                    )
                    
                    if response.status_code == 200:
                        summary = response.json()
                        
                        st.success("✅ Summary generated successfully!")
                        
                        # Executive Summary
                        st.markdown("#### 📋 Executive Summary")
                        st.info(summary['executive_summary'])
                        
                        # Key Clauses
                        st.markdown("#### 📑 Key Clauses")
                        for clause in summary['key_clauses']:
                            st.write(f"• {clause}")
                        
                        st.divider()
                        
                        # Risk Analysis
                        st.markdown("#### ⚠️ Risk Analysis")
                        risk_data = summary['risk_analysis']
                        
                        risk_class = f"risk-{risk_data['risk_level'].lower()}"
                        st.markdown(f"**Overall Risk Level:** <span class='{risk_class}'>{risk_data['risk_level']}</span>", unsafe_allow_html=True)
                        
                        st.markdown("**🚩 Risk Flags:**")
                        for flag in risk_data['risk_flags']:
                            st.warning(flag)
                        
                        # Download option
                        st.divider()
                        summary_text = f"""# Document Summary

## Executive Summary
{summary['executive_summary']}

## Key Clauses
{chr(10).join(['- ' + clause for clause in summary['key_clauses']])}

## Risk Analysis
**Risk Level:** {risk_data['risk_level']}

**Risk Flags:**
{chr(10).join(['- ' + flag for flag in risk_data['risk_flags']])}
"""
                        st.download_button(
                            label="📥 Download Summary",
                            data=summary_text,
                            file_name=f"summary_{st.session_state.document_filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                            mime="text/markdown"
                        )
                    else:
                        st.error(f"❌ Failed: {response.status_code}")
                        st.code(response.text)
                
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    # ========== TAB 3: CHAT ASSISTANT ==========
    with tab3:
        st.markdown("### 💬 Chat with Your Document")
        st.caption("Ask questions about your document and get instant answers with source citations")
        
        # Quick questions
        st.markdown("#### 💡 Quick Questions")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("What are the main risks?", key="q1"):
                st.session_state.pending_question = "What are the main risks in this document?"
        
        with col2:
            if st.button("Who are the parties?", key="q2"):
                st.session_state.pending_question = "Who are the parties involved in this document?"
        
        col3, col4 = st.columns(2)
        
        with col3:
            if st.button("What are payment terms?", key="q3"):
                st.session_state.pending_question = "What are the payment terms?"
        
        with col4:
            if st.button("Key obligations?", key="q4"):
                st.session_state.pending_question = "What are the key obligations?"
        
        st.divider()
        
        # Display chat history
        for msg in st.session_state.chat_history:
            if msg['role'] == 'user':
                st.markdown(f"**👤 You:** {msg['content']}")
            else:
                st.markdown(f"**🤖 AI:** {msg['content']}")
                if 'sources' in msg:
                    with st.expander("📚 Sources"):
                        for source in msg['sources']:
                            st.write(f"• {source}")
        
        # Chat input
        user_question = st.text_input(
            "Your question",
            placeholder="Ask anything about this document...",
            key="chat_input",
            value=st.session_state.get('pending_question', '')
        )
        
        if 'pending_question' in st.session_state:
            del st.session_state.pending_question
        
        if st.button("📤 Send", key="send_chat") and user_question:
            with st.spinner("Thinking..."):
                try:
                    # Prepare chat history for API
                    history = [
                        {"role": msg['role'], "content": msg['content']}
                        for msg in st.session_state.chat_history
                        if msg['role'] in ['user', 'assistant']
                    ]
                    
                    response = requests.post(
                        f"{API_URL}/api/v1/document/chat",
                        json={
                            "document_id": st.session_state.document_id,
                            "question": user_question,
                            "chat_history": history
                        },
                        timeout=60
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        # Add to chat history
                        st.session_state.chat_history.append({
                            "role": "user",
                            "content": user_question
                        })
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": result['answer'],
                            "sources": result['sources']
                        })
                        
                        st.rerun()
                    else:
                        st.error(f"❌ Failed: {response.status_code}")
                        st.code(response.text)
                
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

else:
    # No document loaded
    st.info("👆 Upload a document to begin analysis")
    
    with st.expander("ℹ️ About"):
        st.markdown("""
        **Supported formats:** PDF (single/multi-page), PNG, JPG
        
        **Features:**
        - **📋 Key Details:** Extract parties, dates, obligations, payment terms
        - **📊 Summary:** Executive summary with comprehensive risk analysis
        - **💬 Chat:** Ask questions about your document in natural language
        
        **What we analyze:**
        - Legal risks & liabilities
        - Financial risks & obligations
        - Compliance requirements
        - Red flags & concerns
        
        **Note:** This is AI-assisted analysis for informational purposes only.
        """)

st.markdown("---")
st.caption("Powered by OpenAI GPT-4o | Document Intelligence System")

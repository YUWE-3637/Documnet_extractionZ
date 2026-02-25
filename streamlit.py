import streamlit as st
import os
from datetime import datetime
import json
import io
import base64
from openai import OpenAI
import pdfplumber
from pdf2image import convert_from_bytes
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ========== OCR & TEXT EXTRACTION FUNCTIONS ==========
def is_scanned_pdf(pdf_bytes: bytes) -> bool:
    """Check if PDF is scanned or text-based"""
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            if len(pdf.pages) == 0:
                return True
            text = pdf.pages[0].extract_text()
            return text is None or len(text.strip()) < 50
    except:
        return True


def extract_text_from_pdf_fast(pdf_bytes: bytes) -> str:
    """Fast text extraction for text-based PDFs"""
    all_text = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            if text:
                if len(pdf.pages) > 1:
                    all_text.append(f"\n\n--- PAGE {page_num} ---\n\n{text}")
                else:
                    all_text.append(text)
    return "\n".join(all_text)


def extract_text_with_vision(image_bytes: bytes) -> str:
    """Use GPT-4o Vision for OCR"""
    base64_img = base64.b64encode(image_bytes).decode("utf-8")
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": "Extract ALL text from this document. Preserve structure, headings, and formatting."},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_img}"}}
            ]
        }],
        max_tokens=4000
    )
    return response.choices[0].message.content


def extract_text_from_document(file_bytes: bytes, filename: str) -> str:
    """Smart text extraction - fast path for text PDFs, OCR for scanned"""
    is_pdf = filename.lower().endswith('.pdf')
    
    if is_pdf:
        if not is_scanned_pdf(file_bytes):
            try:
                return extract_text_from_pdf_fast(file_bytes)
            except:
                pass
        
        # Scanned PDF - convert to images
        try:
            images = convert_from_bytes(file_bytes, dpi=200)
            all_text = []
            for idx, img in enumerate(images):
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')
                text = extract_text_with_vision(img_byte_arr.getvalue())
                if len(images) > 1:
                    all_text.append(f"\n\n--- PAGE {idx + 1} ---\n\n{text}")
                else:
                    all_text.append(text)
            return "\n".join(all_text)
        except Exception as e:
            raise Exception(f"Failed to process PDF: {str(e)}")
    else:
        # Image file
        return extract_text_with_vision(file_bytes)


# ========== LLM ANALYSIS FUNCTIONS ==========
def extract_key_details(document_text: str) -> dict:
    """Extract structured key details using JSON mode"""
    system_prompt = """You are a legal document analyzer specializing in Indian contract law. 
Extract key legal and business details from the document. Return ONLY valid JSON.

Expected JSON structure:
{
  "document_type": "string (e.g., Service Agreement, Rental Agreement, NDA)",
  "parties_involved": ["Party 1", "Party 2"],
  "issued_date": "YYYY-MM-DD or null if not found",
  "expiry_date": "YYYY-MM-DD or null if not found",
  "risk_level": "High/Medium/Low based on terms",
  "key_obligations": ["Obligation 1", "Obligation 2"],
  "payment_terms": "string describing payment structure"
}

RULES:
- Do not hallucinate missing values - use null if not present
- Be concise and accurate
- Focus on legally binding obligations
- Assess risk based on liability, penalties, and unclear terms"""
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analyze this document:\n\n{document_text[:8000]}"}
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
        max_tokens=1000
    )
    
    result = json.loads(response.choices[0].message.content)
    return {
        "document_type": result.get("document_type", "Unknown Document"),
        "parties_involved": result.get("parties_involved", []),
        "issued_date": result.get("issued_date"),
        "expiry_date": result.get("expiry_date"),
        "risk_level": result.get("risk_level", "Medium"),
        "key_obligations": result.get("key_obligations", []),
        "payment_terms": result.get("payment_terms", "Not specified")
    }


def generate_summary(document_text: str) -> dict:
    """Generate executive summary with risk analysis"""
    system_prompt = """You are a sharp, adaptive INDIAN AI Legal Analyst. Your goal is to provide insightful, clear, and concise risk assessments for common people's English.

Analyze the document and provide:
1. Executive Summary (2-3 sentences)
2. Key Clauses (list of important sections)
3. Risk Analysis (detailed risk assessment)

Return ONLY valid JSON with this structure:
{
  "executive_summary": "string",
  "key_clauses": ["Clause 1", "Clause 2"],
  "risk_analysis": {
    "risk_level": "High/Medium/Low",
    "risk_flags": ["Risk 1", "Risk 2"]
  }
}

Focus on:
- Legal risks (liability, jurisdiction, termination)
- Financial risks (payment terms, penalties, hidden costs)
- Compliance risks (regulatory requirements)
- Operational risks (obligations, deadlines)"""
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analyze this document:\n\n{document_text[:10000]}"}
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
        max_tokens=1500
    )
    
    result = json.loads(response.choices[0].message.content)
    return {
        "executive_summary": result.get("executive_summary", "Summary not available"),
        "key_clauses": result.get("key_clauses", []),
        "risk_analysis": {
            "risk_level": result.get("risk_analysis", {}).get("risk_level", "Medium"),
            "risk_flags": result.get("risk_analysis", {}).get("risk_flags", [])
        }
    }


def answer_question(document_text: str, question: str, chat_history: list = None) -> dict:
    """Answer user question based on document content"""
    system_prompt = """You are a helpful AI assistant that answers questions about legal documents.

CRITICAL RULES:
1. ONLY use information from the provided document - do not use external knowledge
2. Be specific and cite sections when possible
3. If the document doesn't contain the answer, say "This information is not present in the document"
4. Use clear, professional language suitable for Indian legal and business contexts
5. Be concise but thorough"""
    
    messages = [{"role": "system", "content": system_prompt}]
    
    if chat_history:
        messages.extend(chat_history)
    
    messages.append({
        "role": "user",
        "content": f"DOCUMENT CONTENT:\n{document_text[:6000]}\n\nQUESTION: {question}"
    })
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.3,
        max_tokens=800
    )
    
    answer = response.choices[0].message.content
    
    # Extract sources
    sources = []
    keywords = ["Section", "Clause", "Article", "Page", "Paragraph"]
    for keyword in keywords:
        if keyword in answer:
            lines = answer.split('.')
            for line in lines:
                if keyword in line:
                    sources.append(line.strip())
                    if len(sources) >= 3:
                        break
    
    if not sources:
        sources = ["General document content"]
    
    confidence = 0.95 if "not present" not in answer.lower() else 0.60
    
    return {
        "answer": answer,
        "sources": sources[:3],
        "confidence": confidence
    }


# ========== STREAMLIT UI ==========
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
if 'extracted_text' not in st.session_state:
    st.session_state.extracted_text = None
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
                    file_bytes = uploaded_file.getvalue()
                    extracted_text = extract_text_from_document(file_bytes, uploaded_file.name)
                    
                    if extracted_text and len(extracted_text.strip()) > 20:
                        st.session_state.extracted_text = extracted_text
                        st.session_state.document_filename = uploaded_file.name
                        st.session_state.chat_history = []
                        st.success(f"✅ Document processed! ({len(extracted_text):,} characters extracted)")
                        st.rerun()
                    else:
                        st.error("❌ Could not extract sufficient text from document")
                
                except Exception as e:
                    st.error(f"❌ Error processing document: {str(e)}")
    
    with col2:
        if st.session_state.extracted_text:
            if st.button("🗑️ Clear"):
                st.session_state.extracted_text = None
                st.session_state.document_filename = None
                st.session_state.chat_history = []
                st.rerun()

# ========== 3-TAB INTERFACE (ONLY IF DOCUMENT IS LOADED) ==========
if st.session_state.extracted_text:
    st.divider()
    st.markdown(f"### Analyzing: **{st.session_state.document_filename}**")
    st.caption(f"Extracted: {len(st.session_state.extracted_text):,} characters")
    
    tab1, tab2, tab3 = st.tabs(["📋 Key Details", "📊 Summary", "💬 Chat Assistant"])
    
    # ========== TAB 1: KEY DETAILS ==========
    with tab1:
        st.markdown("### 📋 Key Details Extraction")
        st.caption("Extract structured information: parties, dates, obligations, payment terms")
        
        if st.button("🔄 Extract Key Details", key="extract_details"):
            with st.spinner("Analyzing document structure..."):
                try:
                    details = extract_key_details(st.session_state.extracted_text)
                    
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
                
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    # ========== TAB 2: SUMMARY ==========
    with tab2:
        st.markdown("### 📊 Document Summary & Risk Analysis")
        st.caption("Executive summary with comprehensive risk assessment")
        
        if st.button("📝 Generate Summary", key="generate_summary"):
            with st.spinner("Analyzing risks and generating summary..."):
                try:
                    summary = generate_summary(st.session_state.extracted_text)
                        
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
                    # Prepare chat history
                    history = [
                        {"role": msg['role'], "content": msg['content']}
                        for msg in st.session_state.chat_history
                        if msg['role'] in ['user', 'assistant']
                    ]
                    
                    result = answer_question(
                        st.session_state.extracted_text,
                        user_question,
                        history
                    )
                    
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

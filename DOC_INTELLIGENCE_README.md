# 📄 Document Intelligence System

Enterprise-grade SaaS platform for legal document analysis with OCR, structured extraction, risk analysis, and AI chat.

## 🎯 System Overview

```
┌─────────────────────────────────────────────────────────┐
│                    STREAMLIT UI                         │
│  ┌──────────────┐  ┌────────────────────────────────┐  │
│  │   Sidebar    │  │      Main Content Area         │  │
│  │  Navigation  │  │  ┌──────────┬────────────────┐ │  │
│  │              │  │  │  Document│  Tabbed Insights│ │  │
│  │  - Home      │  │  │  Preview │  - Key Details │ │  │
│  │  - Documents │  │  │          │  - Summary     │ │  │
│  │  - Contracts │  │  │  (60%)   │  - Chat (40%)  │ │  │
│  │  - Reports   │  │  └──────────┴────────────────┘ │  │
│  │  - Settings  │  └────────────────────────────────┘  │
│  └──────────────┘                                      │
└─────────────────────────────────────────────────────────┘
                           ↓ API Calls
┌─────────────────────────────────────────────────────────┐
│              FASTAPI BACKEND (Port 8003)                │
│                                                         │
│  Routes:                Services:                       │
│  ├── /upload           ├── ocr_service.py              │
│  ├── /key-details      ├── llm_service.py              │
│  ├── /summary          ├── document_store.py           │
│  └── /chat             └── [OpenAI Integration]        │
└─────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
Document_extractor/
├── app/
│   ├── main.py                 # FastAPI app entry point
│   ├── models/
│   │   └── schemas.py          # Pydantic models
│   ├── routes/
│   │   ├── upload.py           # Document upload endpoint
│   │   ├── key_details.py      # Key details extraction
│   │   ├── summary.py          # Summary & risk analysis
│   │   └── chat.py             # Chat with document
│   ├── services/
│   │   ├── ocr_service.py      # Smart PDF/OCR processing
│   │   ├── llm_service.py      # OpenAI LLM integration
│   │   └── document_store.py   # Document storage
│   └── storage/                # JSON document storage
│
├── doc_intelligence_ui.py      # Professional Streamlit UI
├── requirements.txt
└── .env
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip3 install -r requirements.txt
```

### 2. Set Environment Variables

Create/update `.env`:
```
OPENAI_API_KEY=your_openai_api_key_here
DOC_INTELLIGENCE_API=http://localhost:8003
```

### 3. Start the Backend API

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
```

### 4. Start the Streamlit UI

```bash
streamlit run doc_intelligence_ui.py --server.port 8504
```

### 5. Access the System

- **API Documentation**: http://localhost:8003/docs
- **Streamlit Dashboard**: http://localhost:8504

## 📡 API Endpoints

### Base URL: `/api/v1/document`

### 1. Document Upload
```bash
POST /api/v1/document/upload

# Upload a document
curl -X POST http://localhost:8003/api/v1/document/upload \
  -F "file=@contract.pdf"

# Response
{
  "document_id": "doc_abc123",
  "filename": "contract.pdf",
  "pages": 4,
  "status": "processed",
  "extracted_text_length": 5420
}
```

### 2. Extract Key Details
```bash
POST /api/v1/document/key-details

# Request
{
  "document_id": "doc_abc123"
}

# Response
{
  "document_type": "Service Agreement",
  "parties_involved": ["Alpha Inc.", "Beta Group"],
  "issued_date": "2025-04-10",
  "expiry_date": "2026-04-20",
  "risk_level": "Medium",
  "key_obligations": [
    "Branding services",
    "Website development"
  ],
  "payment_terms": "Milestone-based payments"
}
```

### 3. Generate Summary
```bash
POST /api/v1/document/summary

# Request
{
  "document_id": "doc_abc123",
  "highlight_risks": true
}

# Response
{
  "executive_summary": "This is a service agreement...",
  "key_clauses": [
    "Scope of Work",
    "Payment Terms",
    "Termination"
  ],
  "risk_analysis": {
    "risk_level": "Medium",
    "risk_flags": [
      "No penalty clause",
      "Unclear liability limitation"
    ]
  }
}
```

### 4. Chat with Document
```bash
POST /api/v1/document/chat

# Request
{
  "document_id": "doc_abc123",
  "question": "What are the payment terms?",
  "chat_history": []
}

# Response
{
  "answer": "According to Section 4, payments are milestone-based...",
  "sources": [
    "Section 4: Payment Terms",
    "Schedule A: Milestones"
  ],
  "confidence": 0.91
}
```

## 🎨 UI Features

### Sidebar Navigation
- 🏠 Home
- 📁 Documents
- 📋 Contracts (Active)
- 📊 Reports
- ⚙️ Settings
- 📤 Upload section

### Main Content Area

**Left Panel (60%) - Document Preview**
- PDF/Image preview container
- Page indicator
- Extracted text viewer
- Download functionality

**Right Panel (40%) - AI Insights Tabs**

**Tab 1: Key Details**
- 📄 Document Type
- 👥 Parties Involved
- 📅 Issued Date
- ⏰ Expiry Date
- ⚠️ Risk Level (color-coded)
- 📌 Key Obligations
- 💰 Payment Terms

**Tab 2: Summary**
- 📋 Executive Summary
- 📑 Key Clauses
- ⚠️ Risk Analysis with flags
- Color-coded risk levels

**Tab 3: Chat Assistant**
- 💬 Chat interface (user right, AI left)
- Quick question buttons
- Chat history
- Source citations
- Confidence scores

## 🔧 Technical Details

### Smart OCR Processing
```python
# Automatic detection
if is_text_pdf(file):
    # Fast extraction with pdfplumber (5-10x faster)
    text = extract_text_from_pdf_fast(file)
else:
    # OCR with GPT-4o Vision
    text = extract_text_with_ocr(file)
```

### Structured LLM Prompts

**Key Details Extraction:**
- Uses JSON mode for structured output
- Indian legal context awareness
- Null handling for missing fields

**Summary Generation:**
- Executive summary + risk focus
- Adaptive to document type
- Highlights red flags

**Chat/RAG:**
- Grounded answers only from document
- Source attribution
- Context-aware responses

### Document Storage
- In-memory cache for fast access
- JSON persistence to disk
- Automatic cleanup on delete

## 🎯 Use Cases

### Legal Teams
- Contract review and risk assessment
- Quick extraction of key terms
- Q&A on legal documents

### Finance Teams
- Invoice analysis
- Payment term extraction
- Financial risk identification

### Compliance Teams
- Regulatory document review
- Obligation tracking
- Missing clause identification

## 📊 Performance

| Operation | Time |
|-----------|------|
| Text-based PDF upload | 2-5s |
| Scanned PDF upload | 15-30s |
| Key details extraction | 5-8s |
| Summary generation | 6-10s |
| Chat response | 3-6s |

## 🔐 Security Features

- Session-based document isolation
- No permanent storage (optional cleanup)
- API key protection via environment variables
- CORS configuration for secure frontend access

## 📚 API Integration Examples

### Python
```python
import requests

# Upload document
files = {"file": open("contract.pdf", "rb")}
response = requests.post("http://localhost:8003/api/v1/document/upload", files=files)
doc_id = response.json()["document_id"]

# Get key details
response = requests.post(
    "http://localhost:8003/api/v1/document/key-details",
    json={"document_id": doc_id}
)
details = response.json()
print(f"Risk Level: {details['risk_level']}")

# Chat
response = requests.post(
    "http://localhost:8003/api/v1/document/chat",
    json={
        "document_id": doc_id,
        "question": "What are the main risks?",
        "chat_history": []
    }
)
print(response.json()["answer"])
```

### JavaScript
```javascript
// Upload document
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const uploadResponse = await fetch('http://localhost:8003/api/v1/document/upload', {
    method: 'POST',
    body: formData
});

const { document_id } = await uploadResponse.json();

// Get summary
const summaryResponse = await fetch('http://localhost:8003/api/v1/document/summary', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
        document_id, 
        highlight_risks: true 
    })
});

const summary = await summaryResponse.json();
console.log(summary.risk_analysis);
```

## 🐛 Troubleshooting

### API Not Responding
```bash
# Check if running
curl http://localhost:8003/health

# Restart server
uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
```

### Document Upload Fails
- Check file size (< 10MB recommended)
- Ensure OPENAI_API_KEY is set
- Verify file format (PDF, PNG, JPG, TXT)

### OCR Timeout
- Large scanned PDFs may take 30+ seconds
- Consider splitting multi-page documents
- Increase timeout in requests: `timeout=180`

### Chat Gives Generic Answers
- Ensure document is uploaded and processed
- Check document_id is correct
- Verify extracted text length > 100 characters

## 🔄 Comparison with Previous Systems

| Feature | Risk Analyzer | RAG System | Doc Intelligence |
|---------|---------------|------------|------------------|
| Document Upload | ✅ | ✅ | ✅ |
| OCR Processing | ✅ | ❌ | ✅ Smart |
| Key Details | ❌ | ❌ | ✅ Structured |
| Risk Analysis | ✅ | ❌ | ✅ Enhanced |
| Document Chat | ❌ | ✅ | ✅ |
| Professional UI | Basic | Simple | ✅ Enterprise |
| Multi-document | ❌ | ✅ | ✅ |
| API Structure | Monolithic | Modular | ✅ Modular |

## 🚧 Future Enhancements

- [ ] Document comparison tool
- [ ] Batch processing
- [ ] Export to Word/PDF
- [ ] Custom risk templates
- [ ] Multi-language support
- [ ] Document versioning
- [ ] Collaboration features
- [ ] Advanced analytics dashboard

## 📞 Support

For issues:
1. Check API docs: http://localhost:8003/docs
2. Review logs in terminal
3. Verify environment variables in `.env`

---

**Built with ❤️ for Indian legal and business professionals**

*Powered by OpenAI GPT-4o, FastAPI, Streamlit*

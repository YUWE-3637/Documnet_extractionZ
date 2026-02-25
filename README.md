# 📄 Document Risk Analyzer

AI-powered document risk analysis system that extracts text from legal and financial documents and provides comprehensive risk assessments.

## 🌟 Features

- **Advanced OCR**: Extract text from PDFs, images, and scanned documents
- **Comprehensive Risk Analysis**: Identify legal, financial, compliance, and operational risks
- **AI-Powered**: Uses OpenAI GPT-4 for intelligent document understanding
- **Beautiful UI**: Modern Streamlit interface with real-time analysis
- **Detailed Reports**: Structured risk reports with actionable recommendations
- **Export Options**: Download reports in Markdown or JSON format

## 📋 What It Analyzes

### Legal Risks
- Unfavorable contract terms
- Liability exposure and indemnification
- Jurisdiction and dispute resolution
- Intellectual property concerns
- Non-compete and restrictive covenants

### Financial Risks
- Payment terms and conditions
- Penalty clauses and liquidated damages
- Hidden costs and escalation clauses
- Currency and exchange rate risks
- Financial guarantees and bonds

### Compliance Risks
- Regulatory compliance requirements
- Data protection and privacy obligations
- Industry-specific compliance
- Reporting and audit requirements

### Operational Risks
- Performance obligations and deadlines
- Service level agreements (SLAs)
- Termination clauses and exit conditions
- Force majeure and change control

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- OpenAI API key

### Installation

1. **Clone or navigate to the project directory**
   ```bash
   cd /Users/vakilsearch/Documents/Document_extractor
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   
   Update the `.env` file with your OpenAI API key:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   ```

### Running the Application

#### 1. Start the FastAPI Backend

Open a terminal and run:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: `http://localhost:8000`

API Documentation (Swagger UI): `http://localhost:8000/docs`

#### 2. Start the Streamlit Frontend

Open a **new terminal** and run:

```bash
streamlit run streamlit.py
```

The web interface will open automatically at: `http://localhost:8501`

## 📁 Project Structure

```
Document_extractor/
├── main.py              # FastAPI backend with risk analysis logic
├── streamlit.py         # Streamlit frontend interface
├── requirements.txt     # Python dependencies
├── .env                # Environment variables (API keys)
└── README.md           # This file
```

## 🔧 API Endpoints

### Health Check
```
GET /
```
Returns API status

### Analyze Document
```
POST /analyze-document
```

**Request:**
- Multipart form data with file upload
- Supported formats: PDF, PNG, JPG, JPEG

**Response:**
```json
{
  "success": true,
  "filename": "contract.pdf",
  "extracted_text_length": 5432,
  "extracted_text": "Document text preview...",
  "risk_analysis": "# DOCUMENT RISK ANALYSIS REPORT\n...",
  "metadata": {
    "analysis_timestamp": "2024-02-24T10:30:00",
    "chunks_analyzed": 2,
    "total_text_length": 5432
  }
}
```

## 💡 Usage Example

### Using the Web Interface

1. Open `http://localhost:8501` in your browser
2. Upload a document (PDF or image)
3. Click "Analyze Document"
4. View the comprehensive risk analysis
5. Download the report in Markdown or JSON format

### Using the API Directly

```python
import requests

url = "http://localhost:8000/analyze-document"
files = {"file": open("contract.pdf", "rb")}

response = requests.post(url, files=files)
result = response.json()

print(result["risk_analysis"])
```

### Using cURL

```bash
curl -X POST "http://localhost:8000/analyze-document" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@contract.pdf"
```

## 🎯 Supported Document Types

- Legal contracts and agreements
- Financial documents and invoices
- Bonds and securities
- Compliance documents
- Service level agreements (SLAs)
- Non-disclosure agreements (NDAs)
- Employment contracts
- Lease agreements
- Purchase orders
- Any business document requiring risk assessment

## ⚙️ Configuration

### Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `API_URL`: FastAPI backend URL (default: `http://localhost:8000`)

### Customization

You can customize the analysis by modifying the prompts in `main.py`:

- **Text Extraction Prompt** (line 52-66): Adjust OCR instructions
- **Risk Analysis Prompt** (line 109-145): Modify risk assessment criteria
- **Final Report Prompt** (line 159-196): Customize report structure

## 🔒 Security & Privacy

- Documents are processed in real-time and not stored permanently
- API keys are stored securely in environment variables
- CORS is enabled for development (configure for production)
- All communication happens over HTTPS in production

## 🐛 Troubleshooting

### API Connection Error

**Problem:** Frontend shows "API Offline"

**Solution:**
1. Ensure FastAPI backend is running: `uvicorn main:app --reload`
2. Check that port 8000 is not in use
3. Verify `API_URL` in environment or streamlit.py

### OpenAI API Error

**Problem:** "Invalid API key" or authentication errors

**Solution:**
1. Verify your OpenAI API key in `.env`
2. Ensure the key has proper permissions
3. Check your OpenAI account has available credits

### File Upload Error

**Problem:** Document upload fails

**Solution:**
1. Check file size (large files may timeout)
2. Verify file format is supported (PDF, PNG, JPG, JPEG)
3. Ensure file is not corrupted
4. Increase timeout in `streamlit.py` if needed

### Timeout Errors

**Problem:** Analysis times out for large documents

**Solution:**
1. Increase timeout in `streamlit.py` (line 171): `timeout=300`
2. Reduce chunk size in `main.py` (line 82): `chunk_size=6000`
3. Use smaller documents or split large documents

## 📊 Performance Tips

- **Large Documents**: May take 30-60 seconds to analyze
- **Chunk Size**: Adjust in `main.py` for optimal performance vs. accuracy
- **Model Selection**: Using `gpt-4.1-mini` for cost efficiency
- **Caching**: Consider implementing caching for repeated analyses

## 🔄 Development

### Running in Development Mode

```bash
# Backend with auto-reload
uvicorn main:app --reload

# Frontend with auto-reload (default)
streamlit run streamlit.py
```

### Testing the API

Use the built-in Swagger UI at `http://localhost:8000/docs` to test endpoints interactively.

## 📝 License

This project is for internal use. Ensure compliance with OpenAI's usage policies.

## ⚠️ Disclaimer

This tool provides AI-assisted analysis for informational purposes only. It should not replace professional legal or financial advice. Always consult with qualified professionals for important business decisions.

## 🤝 Support

For issues, questions, or feature requests, please contact your system administrator or development team.

---

**Built with:**
- FastAPI - Modern web framework for building APIs
- Streamlit - Fast way to build data apps
- OpenAI GPT-4 - Advanced language models
- Python - Programming language

**Powered by AI** 🤖

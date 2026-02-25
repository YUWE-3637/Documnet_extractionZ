# Production-Grade RAG System with FAISS

A scalable, multi-user Document AI RAG (Retrieval-Augmented Generation) application with automatic 3-day data retention.

## 🎯 Key Features

### 1. **Multi-User Isolation**
- Each user's documents are completely isolated
- Thread-safe concurrent uploads
- User-specific search results only

### 2. **Smart 3-Day Retention**
- Daily index sharding (one FAISS index per day)
- Automatic cleanup at 2 AM daily
- Simple file deletion (no complex pruning needed)

### 3. **Production Architecture**
```
┌─────────────────┐
│   User Upload   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│ DocumentManager │─────▶│  FAISS Index     │
│  (Thread-Safe)  │      │  (Daily Shards)  │
└────────┬────────┘      └──────────────────┘
         │
         ▼
┌─────────────────┐
│  SQLite DB      │
│  (Metadata)     │
│  - vector_id    │
│  - user_id      │
│  - page_content │
│  - shard_date   │
└─────────────────┘

Query Flow:
User Query → Embedding → Search (3 days) → Rerank → GPT-4o → Answer
```

### 4. **Technology Stack**
- **Vector Store**: FAISS (FlatL2 for exact search)
- **Metadata**: SQLite (thread-safe)
- **Embeddings**: OpenAI text-embedding-3-small
- **Generation**: GPT-4o-mini
- **Chunking**: LangChain RecursiveCharacterTextSplitter (600 chars, 60 overlap)
- **API**: FastAPI
- **UI**: Streamlit
- **Scheduler**: APScheduler (for daily cleanup)

## 📁 File Structure

```
Document_extractor/
├── database.py              # SQLite metadata manager
├── document_manager.py      # FAISS vector storage + thread safety
├── query_engine.py          # RAG retrieval and generation
├── rag_api.py              # FastAPI endpoints
├── rag_streamlit.py        # Streamlit UI
├── data/                   # Auto-created
│   ├── vector_metadata.db  # SQLite database
│   ├── index_20260224.faiss # Daily FAISS index
│   └── index_20260225.faiss
└── requirements.txt
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip3 install -r requirements.txt
```

### 2. Set Environment Variables

Create `.env` file:
```
OPENAI_API_KEY=your_openai_api_key_here
RAG_API_URL=http://localhost:8001
```

### 3. Start the RAG API Server

```bash
uvicorn rag_api:app --host 0.0.0.0 --port 8001 --reload
```

### 4. Start the Streamlit UI

```bash
streamlit run rag_streamlit.py --server.port 8502
```

### 5. Access the System

- **API Documentation**: http://localhost:8001/docs
- **Streamlit UI**: http://localhost:8502

## 📡 API Endpoints

### Upload Document
```bash
POST /upload-document
Headers: user_id: <your_user_id>
Body: multipart/form-data with file

curl -X POST http://localhost:8001/upload-document \
  -H "user_id: john_doe" \
  -F "file=@contract.pdf"
```

### Query Documents
```bash
POST /query
Headers: user_id: <your_user_id>
Body: {"query": "What are the payment terms?", "top_k": 5}

curl -X POST http://localhost:8001/query \
  -H "user_id: john_doe" \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the payment terms?", "top_k": 5}'
```

### Get User Statistics
```bash
GET /user-stats
Headers: user_id: <your_user_id>

curl -X GET http://localhost:8001/user-stats \
  -H "user_id: john_doe"
```

### Manual Cleanup
```bash
POST /cleanup?retention_days=3

curl -X POST http://localhost:8001/cleanup?retention_days=3
```

## 🔧 Architecture Details

### Thread Safety
```python
# All write operations use threading.Lock()
with self.lock:
    index.add(embeddings)
    self.metadata_db.add_vectors(user_id, shard_date, vectors_data)
    self._save_index(index, shard_date)
```

### Daily Sharding Strategy
```python
# Each day gets its own FAISS index
shard_date = datetime.now().strftime("%Y%m%d")  # e.g., "20260224"
index_path = f"data/index_{shard_date}.faiss"

# Search aggregates last 3 days
active_shards = [
    "data/index_20260224.faiss",
    "data/index_20260223.faiss",
    "data/index_20260222.faiss"
]
```

### Multi-User Filtering
```python
# SQLite metadata enforces user isolation
SELECT * FROM vector_metadata
WHERE user_id = 'john_doe'
  AND shard_date IN ('20260224', '20260223', '20260222')
  AND vector_id IN (search_results)
```

### Automatic Cleanup
```python
# Scheduled via APScheduler - runs daily at 2 AM
@scheduler.add_job('cron', hour=2, minute=0)
def cleanup_job():
    cutoff_date = (datetime.now() - timedelta(days=3)).strftime("%Y%m%d")
    
    # Delete metadata from SQLite
    DELETE FROM vector_metadata WHERE shard_date < cutoff_date
    
    # Delete FAISS index files
    os.remove(f"data/index_{old_date}.faiss")
```

## 📊 Performance Optimizations

### 1. Chunking Strategy
- **Size**: 600 characters (~150 tokens)
- **Overlap**: 60 characters (10%)
- **Rationale**: Smaller chunks = better retrieval precision

### 2. Reranking
- **Score**: 70% similarity + 30% recency
- **Ensures**: Recent documents get slight boost

### 3. Embedding Batching
```python
# Process all chunks in one API call
embeddings = client.embeddings.create(
    model="text-embedding-3-small",
    input=all_chunks  # Batch of 10-100 chunks
)
```

## 🔐 Security & Privacy

### User Isolation
- All operations require `user_id` header
- SQLite queries always filter by `user_id`
- Users can **never** access other users' documents

### Data Retention
- **Automatic**: Data > 3 days is deleted at 2 AM daily
- **Manual**: Can trigger cleanup anytime via API
- **Guaranteed**: No user data persists beyond retention window

## 📝 Source Attribution

Every answer includes exact citations:

```
Answer: According to Rental_Agreement.pdf, Page 3, 
the monthly rent is ₹25,000 due on the 1st of each month.

Sources:
1. Rental_Agreement.pdf, Page 3 - Relevance: 0.92
   "...monthly rent of ₹25,000 shall be paid on or 
   before the 1st day of each month..."
```

## 🧪 Testing

### Test Document Upload
```python
import requests

files = {"file": open("test.pdf", "rb")}
headers = {"user_id": "test_user"}
response = requests.post(
    "http://localhost:8001/upload-document",
    files=files,
    headers=headers
)
print(response.json())
```

### Test Query
```python
headers = {"user_id": "test_user"}
payload = {"query": "What are the key terms?", "top_k": 5}
response = requests.post(
    "http://localhost:8001/query",
    json=payload,
    headers=headers
)
print(response.json()["answer"])
```

## 🐛 Troubleshooting

### FAISS Index Not Found
- System creates indices on first upload per day
- Check `data/` directory exists and is writable

### No Results for Query
- Ensure you've uploaded documents for that `user_id`
- Check user stats: `GET /user-stats`

### Slow Searches
- FAISS FlatL2 is exact search (production-grade)
- For millions of vectors, consider IndexIVFFlat

### Cleanup Not Running
- Check APScheduler logs
- Trigger manual cleanup: `POST /cleanup`

## 📈 Scaling Considerations

### Current Setup (Good for):
- Up to 10,000 users
- Up to 100 documents per user
- Up to 1M total vectors

### For Larger Scale:
1. **Switch to IndexIVFFlat**:
   ```python
   quantizer = faiss.IndexFlatL2(dimension)
   index = faiss.IndexIVFFlat(quantizer, dimension, 100)
   ```

2. **Use PostgreSQL instead of SQLite**:
   - Better concurrency
   - Remote hosting

3. **Distributed Storage**:
   - Store FAISS indices in S3/GCS
   - Use Redis for metadata caching

## 🎓 Educational Notes

### Why Daily Sharding?
- **Performance**: Smaller indices = faster searches
- **Simplicity**: Delete old data = delete one file
- **Scalability**: Each day is independent

### Why SQLite + FAISS (not just FAISS)?
- FAISS stores **only vectors** (no text, no metadata)
- SQLite bridges vectors ↔ actual content
- This is the **gold standard** for local RAG

### Why Thread Safety Matters?
```python
# Without lock - RACE CONDITION:
# User A uploads → reads index (100 vectors)
# User B uploads → reads index (100 vectors)  
# User A adds vectors → saves (110 vectors)
# User B adds vectors → saves (105 vectors)  ❌ LOST DATA

# With lock - SAFE:
with self.lock:  # Only one user at a time
    index = load_index()
    index.add(new_vectors)
    save_index(index)
```

## 🤝 Integration with Existing System

This RAG system works alongside your existing Document Risk Analyzer:

```python
# In main.py, after extracting text:
from document_manager import DocumentManager

doc_manager = DocumentManager(openai_api_key=os.getenv("OPENAI_API_KEY"))

# Index the extracted text
doc_manager.add_document(
    user_id=user_id,
    document_text=extracted_text,
    document_name=file.filename
)
```

## 📞 Support

For issues or questions:
1. Check API docs: http://localhost:8001/docs
2. Review logs in terminal
3. Test with `/relevant-chunks` endpoint for debugging

---

**Built with ❤️ for Indian legal and business document analysis**

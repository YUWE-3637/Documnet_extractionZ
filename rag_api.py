"""
FastAPI Endpoints for Production RAG System
Multi-user document upload and query with 3-day retention
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os
from dotenv import load_dotenv
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler

from document_manager import DocumentManager
from query_engine import QueryEngine

# Load environment
load_dotenv()

# Initialize RAG system
doc_manager = DocumentManager(
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    data_dir="data"
)

query_engine = QueryEngine(
    document_manager=doc_manager,
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    generation_model="gpt-4o-mini"
)

# Initialize FastAPI
app = FastAPI(
    title="Production RAG System",
    description="Multi-user document Q&A with FAISS and 3-day retention",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5

class QueryResponse(BaseModel):
    success: bool
    answer: str
    sources: List[dict]
    query: str
    chunks_retrieved: int

# Background scheduler for daily cleanup
scheduler = BackgroundScheduler()

def cleanup_job():
    """Runs daily at 2 AM to delete data older than 3 days"""
    try:
        result = doc_manager.cleanup_stale_data(retention_days=3)
        print(f"✅ Cleanup completed: {result}")
    except Exception as e:
        print(f"❌ Cleanup failed: {str(e)}")

scheduler.add_job(cleanup_job, 'cron', hour=2, minute=0)
scheduler.start()

# ========== API Endpoints ==========

@app.get("/")
def health_check():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "Production RAG System",
        "retention_days": 3
    }

@app.post("/upload-document")
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Header(..., description="Unique user identifier")
):
    """
    Upload and index a document for a specific user
    
    Headers:
        user_id: Unique identifier for the user
    
    Body:
        file: PDF, TXT, or other text document
    """
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")
    
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id header required")
    
    try:
        # Read file content
        file_bytes = await file.read()
        
        # For this demo, assume it's text content
        # In production, you'd use the existing extract_text_from_document
        try:
            text_content = file_bytes.decode('utf-8')
        except:
            # If not UTF-8, try to extract from PDF
            from main import extract_text_from_document
            text_content = extract_text_from_document(file_bytes, file.filename)
        
        if not text_content or len(text_content.strip()) < 50:
            raise HTTPException(
                status_code=400,
                detail="Document is empty or too short"
            )
        
        # Add to vector store
        result = doc_manager.add_document(
            user_id=user_id,
            document_text=text_content,
            document_name=file.filename
        )
        
        return {
            "success": True,
            "message": f"Document '{file.filename}' indexed successfully",
            **result
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process document: {str(e)}"
        )

@app.post("/query", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    user_id: str = Header(..., description="Unique user identifier")
):
    """
    Query indexed documents for a specific user
    
    Headers:
        user_id: Unique identifier for the user
    
    Body:
        query: Natural language question
        top_k: Number of relevant chunks to retrieve (default: 5)
    """
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id header required")
    
    if not request.query or len(request.query.strip()) < 3:
        raise HTTPException(status_code=400, detail="Query is too short")
    
    try:
        result = query_engine.generate_response(
            query=request.query,
            user_id=user_id,
            top_k=request.top_k
        )
        
        return result
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Query failed: {str(e)}"
        )

@app.get("/user-stats")
async def get_user_stats(
    user_id: str = Header(..., description="Unique user identifier")
):
    """
    Get statistics for a user's indexed documents
    
    Headers:
        user_id: Unique identifier for the user
    """
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id header required")
    
    try:
        stats = doc_manager.get_user_stats(user_id)
        return {
            "success": True,
            **stats
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get stats: {str(e)}"
        )

@app.post("/cleanup")
async def manual_cleanup(retention_days: Optional[int] = 3):
    """
    Manually trigger cleanup of stale data
    
    Query params:
        retention_days: Number of days to retain (default: 3)
    """
    try:
        result = doc_manager.cleanup_stale_data(retention_days)
        return {
            "success": True,
            "message": "Cleanup completed",
            **result
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Cleanup failed: {str(e)}"
        )

@app.get("/relevant-chunks")
async def get_relevant_chunks(
    query: str,
    user_id: str = Header(..., description="Unique user identifier"),
    top_k: int = 5
):
    """
    Get relevant chunks without generation (for debugging)
    
    Headers:
        user_id: Unique identifier for the user
    
    Query params:
        query: Search query
        top_k: Number of chunks to return
    """
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id header required")
    
    try:
        chunks = query_engine.get_relevant_chunks(
            query=query,
            user_id=user_id,
            top_k=top_k
        )
        
        return {
            "success": True,
            "query": query,
            "chunks": chunks
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve chunks: {str(e)}"
        )

# Shutdown event
@app.on_event("shutdown")
def shutdown_event():
    """Clean up resources on shutdown"""
    scheduler.shutdown()

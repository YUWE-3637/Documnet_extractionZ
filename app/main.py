"""
Document Intelligence System - Main FastAPI Application
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.routes import upload, key_details, summary, chat

# Load environment
load_dotenv()

# Initialize FastAPI
app = FastAPI(
    title="Document Intelligence System",
    description="Enterprise-grade document analysis with OCR, key details extraction, risk summarization, and chat",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload.router, prefix="/api/v1/document", tags=["Document Upload"])
app.include_router(key_details.router, prefix="/api/v1/document", tags=["Key Details"])
app.include_router(summary.router, prefix="/api/v1/document", tags=["Summary"])
app.include_router(chat.router, prefix="/api/v1/document", tags=["Chat"])


@app.get("/")
def root():
    """Health check and API information"""
    return {
        "status": "running",
        "service": "Document Intelligence System",
        "version": "1.0.0",
        "endpoints": {
            "upload": "/api/v1/document/upload",
            "key_details": "/api/v1/document/key-details",
            "summary": "/api/v1/document/summary",
            "chat": "/api/v1/document/chat"
        }
    }


@app.get("/health")
def health_check():
    """Simple health check"""
    return {"status": "healthy"}

"""
Pydantic schemas for Document Intelligence System
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    pages: int
    status: str
    extracted_text_length: int


class KeyDetailsRequest(BaseModel):
    document_id: str


class KeyDetailsResponse(BaseModel):
    document_type: str
    parties_involved: List[str]
    issued_date: Optional[str]
    expiry_date: Optional[str]
    risk_level: str
    key_obligations: List[str]
    payment_terms: str


class SummaryRequest(BaseModel):
    document_id: str
    highlight_risks: bool = True


class RiskAnalysis(BaseModel):
    risk_level: str
    risk_flags: List[str]


class SummaryResponse(BaseModel):
    executive_summary: str
    key_clauses: List[str]
    risk_analysis: RiskAnalysis


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    document_id: str
    question: str
    chat_history: List[ChatMessage] = []


class ChatResponse(BaseModel):
    answer: str
    sources: List[str]
    confidence: float


class DocumentMetadata(BaseModel):
    document_id: str
    filename: str
    upload_date: datetime
    pages: int
    extracted_text: str
    embeddings: Optional[List[float]] = None

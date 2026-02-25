"""
Document Upload Route
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from datetime import datetime
import uuid

from app.models.schemas import DocumentUploadResponse, DocumentMetadata
from app.services.ocr_service import extract_text_from_document
from app.services.document_store import document_store

router = APIRouter()


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and process a document (PDF, Image, DOCX)
    Performs OCR and stores extracted text
    """
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Validate file type
    allowed_extensions = ['.pdf', '.png', '.jpg', '.jpeg', '.txt']
    if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    try:
        # Read file bytes
        file_bytes = await file.read()
        
        if len(file_bytes) == 0:
            raise HTTPException(status_code=400, detail="Empty file")
        
        # Extract text using OCR service
        extracted_text, page_count = extract_text_from_document(file_bytes, file.filename)
        
        if not extracted_text or len(extracted_text.strip()) < 20:
            raise HTTPException(
                status_code=400,
                detail="Could not extract sufficient text from document"
            )
        
        # Generate document ID
        document_id = f"doc_{uuid.uuid4().hex[:12]}"
        
        # Create metadata
        metadata = DocumentMetadata(
            document_id=document_id,
            filename=file.filename,
            upload_date=datetime.now(),
            pages=page_count,
            extracted_text=extracted_text
        )
        
        # Store document
        document_store.save_document(metadata)
        
        return DocumentUploadResponse(
            document_id=document_id,
            filename=file.filename,
            pages=page_count,
            status="processed",
            extracted_text_length=len(extracted_text)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process document: {str(e)}"
        )

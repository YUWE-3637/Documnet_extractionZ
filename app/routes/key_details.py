"""
Key Details Extraction Route
"""

from fastapi import APIRouter, HTTPException

from app.models.schemas import KeyDetailsRequest, KeyDetailsResponse
from app.services.document_store import document_store
from app.services.llm_service import extract_key_details

router = APIRouter()


@router.post("/key-details", response_model=KeyDetailsResponse)
async def get_key_details(request: KeyDetailsRequest):
    """
    Extract structured key details from document
    Returns: document type, parties, dates, risk level, obligations, payment terms
    """
    # Retrieve document
    document = document_store.get_document(request.document_id)
    
    if not document:
        raise HTTPException(
            status_code=404,
            detail=f"Document {request.document_id} not found"
        )
    
    try:
        # Extract key details using LLM
        details = extract_key_details(document.extracted_text)
        
        return KeyDetailsResponse(**details)
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract key details: {str(e)}"
        )

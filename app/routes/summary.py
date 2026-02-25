"""
Document Summary Route
"""

from fastapi import APIRouter, HTTPException

from app.models.schemas import SummaryRequest, SummaryResponse
from app.services.document_store import document_store
from app.services.llm_service import generate_summary

router = APIRouter()


@router.post("/summary", response_model=SummaryResponse)
async def get_summary(request: SummaryRequest):
    """
    Generate executive summary with risk analysis
    Returns: executive summary, key clauses, risk analysis
    """
    # Retrieve document
    document = document_store.get_document(request.document_id)
    
    if not document:
        raise HTTPException(
            status_code=404,
            detail=f"Document {request.document_id} not found"
        )
    
    try:
        # Generate summary using LLM
        summary_data = generate_summary(
            document.extracted_text,
            highlight_risks=request.highlight_risks
        )
        
        return SummaryResponse(**summary_data)
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate summary: {str(e)}"
        )

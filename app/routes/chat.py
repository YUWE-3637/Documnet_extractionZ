"""
Chat with Document Route (RAG)
"""

from fastapi import APIRouter, HTTPException

from app.models.schemas import ChatRequest, ChatResponse
from app.services.document_store import document_store
from app.services.llm_service import answer_question

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_with_document(request: ChatRequest):
    """
    Ask questions about the document (RAG-style)
    Returns: grounded answer based only on document content
    """
    # Retrieve document
    document = document_store.get_document(request.document_id)
    
    if not document:
        raise HTTPException(
            status_code=404,
            detail=f"Document {request.document_id} not found"
        )
    
    if not request.question or len(request.question.strip()) < 3:
        raise HTTPException(
            status_code=400,
            detail="Question is too short"
        )
    
    try:
        # Convert chat history to dict format
        chat_history = [
            {"role": msg.role, "content": msg.content}
            for msg in request.chat_history
        ]
        
        # Get answer using LLM
        result = answer_question(
            document.extracted_text,
            request.question,
            chat_history
        )
        
        return ChatResponse(**result)
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to answer question: {str(e)}"
        )

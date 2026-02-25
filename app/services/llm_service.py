"""
LLM Service - Structured extraction and analysis using OpenAI
"""

import os
import json
from typing import Dict, Any, List
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def extract_key_details(document_text: str) -> Dict[str, Any]:
    """
    Extract structured key details from document using LLM
    """
    system_prompt = """You are a legal document analyzer specializing in Indian contract law. 
Extract key legal and business details from the document. Return ONLY valid JSON.

Expected JSON structure:
{
  "document_type": "string (e.g., Service Agreement, Rental Agreement, NDA)",
  "parties_involved": ["Party 1", "Party 2"],
  "issued_date": "YYYY-MM-DD or null if not found",
  "expiry_date": "YYYY-MM-DD or null if not found",
  "risk_level": "High/Medium/Low based on terms",
  "key_obligations": ["Obligation 1", "Obligation 2"],
  "payment_terms": "string describing payment structure"
}

RULES:
- Do not hallucinate missing values - use null if not present
- Be concise and accurate
- Focus on legally binding obligations
- Assess risk based on liability, penalties, and unclear terms
"""
    
    user_prompt = f"""Analyze this document and extract key details:\n\n{document_text[:8000]}"""
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
        max_tokens=1000
    )
    
    result = json.loads(response.choices[0].message.content)
    
    # Ensure all required fields exist
    return {
        "document_type": result.get("document_type", "Unknown Document"),
        "parties_involved": result.get("parties_involved", []),
        "issued_date": result.get("issued_date"),
        "expiry_date": result.get("expiry_date"),
        "risk_level": result.get("risk_level", "Medium"),
        "key_obligations": result.get("key_obligations", []),
        "payment_terms": result.get("payment_terms", "Not specified")
    }


def generate_summary(document_text: str, highlight_risks: bool = True) -> Dict[str, Any]:
    """
    Generate executive summary with risk analysis
    """
    system_prompt = """You are a sharp, adaptive INDIAN AI Legal Analyst. Your goal is to provide insightful, clear, and concise risk assessments for common people's English.

Analyze the document and provide:
1. Executive Summary (2-3 sentences)
2. Key Clauses (list of important sections)
3. Risk Analysis (detailed risk assessment)

Return ONLY valid JSON with this structure:
{
  "executive_summary": "string",
  "key_clauses": ["Clause 1", "Clause 2"],
  "risk_analysis": {
    "risk_level": "High/Medium/Low",
    "risk_flags": ["Risk 1", "Risk 2"]
  }
}

Focus on:
- Legal risks (liability, jurisdiction, termination)
- Financial risks (payment terms, penalties, hidden costs)
- Compliance risks (regulatory requirements)
- Operational risks (obligations, deadlines)
"""
    
    user_prompt = f"""Analyze this document and provide summary with risk analysis:\n\n{document_text[:10000]}"""
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
        max_tokens=1500
    )
    
    result = json.loads(response.choices[0].message.content)
    
    return {
        "executive_summary": result.get("executive_summary", "Summary not available"),
        "key_clauses": result.get("key_clauses", []),
        "risk_analysis": {
            "risk_level": result.get("risk_analysis", {}).get("risk_level", "Medium"),
            "risk_flags": result.get("risk_analysis", {}).get("risk_flags", [])
        }
    }


def answer_question(document_text: str, question: str, chat_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Answer user question based on document content (RAG-style)
    """
    system_prompt = """You are a helpful AI assistant that answers questions about legal documents.

CRITICAL RULES:
1. ONLY use information from the provided document - do not use external knowledge
2. Be specific and cite sections when possible
3. If the document doesn't contain the answer, say "This information is not present in the document"
4. Use clear, professional language suitable for Indian legal and business contexts
5. Be concise but thorough

Provide your answer along with the specific sections/sources you used.
"""
    
    # Build context with chat history
    messages = [{"role": "system", "content": system_prompt}]
    
    if chat_history:
        messages.extend(chat_history)
    
    # Add current question with document context
    user_prompt = f"""DOCUMENT CONTENT:\n{document_text[:6000]}\n\nQUESTION: {question}"""
    messages.append({"role": "user", "content": user_prompt})
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.3,
        max_tokens=800
    )
    
    answer = response.choices[0].message.content
    
    # Extract potential sources (simple heuristic - look for section mentions)
    sources = []
    keywords = ["Section", "Clause", "Article", "Page", "Paragraph"]
    for keyword in keywords:
        if keyword in answer:
            # Extract mentions of sections
            lines = answer.split('.')
            for line in lines:
                if keyword in line:
                    sources.append(line.strip())
                    if len(sources) >= 3:
                        break
    
    if not sources:
        sources = ["General document content"]
    
    # Simple confidence heuristic
    confidence = 0.95 if "not present" not in answer.lower() else 0.60
    
    return {
        "answer": answer,
        "sources": sources[:3],
        "confidence": confidence
    }

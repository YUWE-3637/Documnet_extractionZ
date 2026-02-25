from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import OpenAI
from dotenv import load_dotenv
import base64
import os
from typing import List, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import json
import io
import asyncio
from pdf2image import convert_from_bytes
from PIL import Image
import pdfplumber

# Load environment variables from .env file
load_dotenv()

# Initialize OpenAI Client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI(title="Document Risk Analyzer API", version="1.0")

# Enable CORS (optional)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------- Utility Functions -----------

def encode_file_to_base64(file_bytes: bytes) -> str:
    return base64.b64encode(file_bytes).decode("utf-8")


def is_scanned_pdf(pdf_bytes: bytes) -> bool:
    """
    Check if PDF is scanned (image-based) or text-based
    Returns True if scanned, False if text-based
    """
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            if len(pdf.pages) == 0:
                return True
            
            text = pdf.pages[0].extract_text()
            return text is None or len(text.strip()) < 50
    except:
        return True


def extract_text_from_pdf_fast(pdf_bytes: bytes) -> str:
    """
    Fast text extraction for text-based PDFs using pdfplumber
    """
    all_text = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            if text:
                if len(pdf.pages) > 1:
                    all_text.append(f"\n\n--- PAGE {page_num} ---\n\n{text}")
                else:
                    all_text.append(text)
    return "\n".join(all_text)


def convert_pdf_to_images(pdf_bytes: bytes) -> List[bytes]:
    """
    Convert PDF pages to images for OCR processing (scanned PDFs only)
    """
    images = convert_from_bytes(pdf_bytes, dpi=200)
    image_bytes_list = []
    
    for img in images:
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        image_bytes_list.append(img_byte_arr.getvalue())
    
    return image_bytes_list


def extract_text_from_document(file_bytes: bytes, filename: str) -> str:
    """
    Smart text extraction:
    - Text-based PDFs: Fast extraction with pdfplumber (5-10x faster)
    - Scanned PDFs/Images: OCR with GPT-4o Vision
    """
    
    is_pdf = filename.lower().endswith('.pdf')
    
    if is_pdf:
        # Check if PDF is text-based or scanned
        if not is_scanned_pdf(file_bytes):
            # Fast path: Text-based PDF
            try:
                return extract_text_from_pdf_fast(file_bytes)
            except Exception as e:
                # Fallback to OCR if fast extraction fails
                pass
        
        # Slow path: Scanned PDF - use OCR
        try:
            image_bytes_list = convert_pdf_to_images(file_bytes)
        except Exception as e:
            raise Exception(f"Failed to process PDF: {str(e)}")
    else:
        # Image file - use OCR
        image_bytes_list = [file_bytes]
    
    all_text = []
    
    for idx, img_bytes in enumerate(image_bytes_list):
        base64_img = encode_file_to_base64(img_bytes)
        
        page_indicator = f" (Page {idx + 1}/{len(image_bytes_list)})" if len(image_bytes_list) > 1 else ""
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                f"Extract ALL text from this document page{page_indicator}.\n\n"
                                """LEGAL DOCUMENT REQUIREMENTS:
                                1. **Document Hierarchy** (preserve exactly):
                                - Title, Parties, Recitals/Preamble
                                - Article/Section numbers (e.g., "Article 1", "Section 2.1")
                                - Clause numbers (e.g., "Clause 3(a)", "3.2(ii)")
                                - Sub-clauses and subparagraphs
                                
                                2. **Legal Formatting** (maintain precisely):
                                - Defined terms (e.g., "Party A", "Effective Date")
                                - "WHEREAS" clauses and recitals
                                - "NOW THEREFORE" transition
                                - Schedules, Exhibits, Annexures
                                
                                3. **Critical Legal Elements**:
                                - Signatures: Name, Title, Date, Witness
                                - Execution clauses
                                - Governing law, jurisdiction
                                - Entire agreement, severability clauses
                                
                                4. **Tables & Structured Data**:
                                - Payment schedules
                                - Fee structures
                                - Milestones/timelines
                                - Party details
                                
                                5. **Fine Print & Metadata**:
                                - Footnotes, endnotes
                                - Amendments/modifications
                                - Version/date stamps
                                - Page numbers, headers/footers
                                
                                OUTPUT: Return only the extracted text, maintaining original structure."""
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_img}"
                            },
                        },
                    ],
                }
            ],
            max_tokens=500,
        )
        
        page_text = response.choices[0].message.content
        if len(image_bytes_list) > 1:
            all_text.append(f"\n\n--- PAGE {idx + 1} ---\n\n{page_text}")
        else:
            all_text.append(page_text)
    
    return "\n".join(all_text)


def chunk_text(text: str, chunk_size: int = 2500) -> List[str]:
    """
    Chunk large documents into 2-3k token chunks for parallel processing
    """
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]


async def analyze_chunk_async(chunk: str) -> str:
    """
    Async function to analyze a single chunk in parallel
    """
    response = await asyncio.to_thread(
        client.chat.completions.create,
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": (
                    "You are a sharp risk analyst. Read this document section and extract what matters.\n\n"
                    "Identify the document type naturally, then flag: who's exposed, what's at stake legally, "
                    "financially, and operationally. If it's a contract, hunt for traps. "
                    "If it's a policy or agreement, find the obligations and loopholes. "
                    "Adapt your analysis to what the document actually is — don't force a template.\n\n"
                    "Be concise, specific, and ruthless. Skip anything generic.\n\n"
                    f"{chunk}"
                ),
            }
        ],
        max_tokens=500,
    )
    return response.choices[0].message.content


async def analyze_risk_and_summarize(text: str) -> Dict[str, Any]:
    """
    Parallel async risk analysis for 60-80% speed improvement
    - Splits into 2-3k token chunks
    - Processes all chunks in parallel
    - Combines into final risk report
    """

    chunks = chunk_text(text)
    
    # Process all chunks in parallel
    tasks = [analyze_chunk_async(chunk) for chunk in chunks]
    partial_summaries = await asyncio.gather(*tasks)


    # final_response = client.chat.completions.create(
    #     model="gpt-4o-mini",
    #     messages=[
    #         {
    #             "role": "user",
    #             "content": (
    #                 "You are finalizing a comprehensive risk assessment report.\n\n"
    #                 "TASK: Synthesize the following section analyses into a cohesive, actionable risk report.\n\n"
    #                 "OUTPUT FORMAT (use clear markdown formatting):\n\n"
    #                 "# DOCUMENT RISK ANALYSIS REPORT\n\n"
    #                 "## EXECUTIVE SUMMARY\n"
    #                 "[Provide a concise overview of the document and overall risk level]\n\n"
    #                 "## OVERALL RISK RATING\n"
    #                 "**Risk Level:** [High/Medium/Low]\n"
    #                 "**Confidence:** [High/Medium/Low]\n\n"
    #                 "## TOP 5 CRITICAL RISKS\n"
    #                 "1. [Most critical risk with severity level]\n"
    #                 "2. [Second critical risk]\n"
    #                 "3. [Third critical risk]\n"
    #                 "4. [Fourth critical risk]\n"
    #                 "5. [Fifth critical risk]\n\n"
    #                 "## DETAILED RISK BREAKDOWN\n\n"
    #                 "### Legal Risks\n"
    #                 "[Consolidated legal risk analysis]\n\n"
    #                 "### Financial Risks\n"
    #                 "[Consolidated financial risk analysis]\n\n"
    #                 "### Compliance Risks\n"
    #                 "[Consolidated compliance risk analysis]\n\n"
    #                 "### Operational Risks\n"
    #                 "[Consolidated operational risk analysis]\n\n"
    #                 "## RED FLAGS & CONCERNS\n"
    #                 "[List all critical red flags that require immediate attention]\n\n"
    #                 "## KEY OBLIGATIONS & COMMITMENTS\n"
    #                 "[List all important obligations and deadlines]\n\n"
    #                 "## RECOMMENDED ACTIONS\n"
    #                 "1. [Immediate action required]\n"
    #                 "2. [Short-term recommendation]\n"
    #                 "3. [Long-term consideration]\n\n"
    #                 "## MISSING OR UNCLEAR PROVISIONS\n"
    #                 "[Identify any gaps or ambiguities in the document]\n\n"
    #                 "---\n\n"
    #                 "Section Analyses to Consolidate:\n\n"
    #                 f"{''.join(partial_summaries)}"
    #             ),
    #         }
    #     ],
    #     max_tokens=2500,
    # )

    final_response = await asyncio.to_thread(
        client.chat.completions.create,
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": (
                    """
                    ## ROLE
You are a sharp , adaptive INDIAN AI Legal Analyst. Your goal is to provide insightful, clear, and concise risk assessments for Common people english. 
You balance empathy with candor: validate the user's need for security while being "ruthless" in identifying legal traps. 

## OBJECTIVE
Transform raw document text into a structured "Risk Verdict." Move beyond simple summarization to provide peer-level insights that highlight what is actually at stake for the parties involved.

## FORMATTING TOOLKIT
Use the following tools for every response:
* **Headings (##, ###):** For clear hierarchy.
* **Bolding (**...**):** To emphasize critical deadlines, amounts, or "landmines."
* **Horizontal Rules (---):** To separate distinct sections.
* **Tables:** To compare obligations (e.g., Tenant vs. Owner).

## OUTPUT STRUCTURE

# ⚖️ RISK VERDICT

### 💡 THE BOTTOM LINE
[Provide a grounded, one-paragraph verdict. Is this document standard, or is it a "sign-at-your-own-risk" situation? Use a touch of wit if the terms are particularly lopsided.]

---

### 📊 RISK RATING
* **Overall Risk:** [LOW / MEDIUM / HIGH]
* **Confidence Level:** [Based on document clarity]

---

### 🚩 TOP 5 CRITICAL THREATS
1. **[Risk Name]**: [One punchy sentence explaining the threat] | **Severity:** [CRITICAL/MODERATE]
2. **[Risk Name]**: [One punchy sentence] | **Severity:** [CRITICAL/MODERATE]
3. **[Risk Name]**: [One punchy sentence] | **Severity:** [CRITICAL/MODERATE]
4. **[Risk Name]**: [One punchy sentence] | **Severity:** [CRITICAL/MODERATE]
5. **[Risk Name]**: [One punchy sentence] | **Severity:** [CRITICAL/MODERATE]

---

### 🔍 DETAILED BREAKDOWN
| Category | The "Bite" (Key Risks) |
| :--- | :--- |
| **Legal** | [Jurisdiction, liability traps, and indemnity.] |
| **Financial** | [Hidden fees, penalty rates, and deposit terms.] |
| **Operational** | [Notice periods, repair duties, and exit triggers.] |

### ⚠️ RED FLAGS & BLIND SPOTS
* [Identify vague language or "suspiciously absent" clauses.]
* [List specific dealbreakers.]

### 🛠️ KILL LIST — RECOMMENDED ACTIONS
1. **[Immediate]:** [The most urgent fix required before signing.]
2. **[Short-term]:** [Negotiation points or clarifications needed.]
3. **[Long-term]:** [Compliance or operational habits to adopt.]

---
**Next Step:** Would you like me to draft a specific counter-clause for any of these high-risk areas?
                    """
                    f"{''.join(partial_summaries)}"
                ),
            }
        ],
        max_tokens=800,
    )
    return {
        "summary": final_response.choices[0].message.content,
        "analysis_timestamp": datetime.now().isoformat(),
        "chunks_analyzed": len(chunks),
        "total_text_length": len(text)
    }


# ----------- API Endpoints -----------

@app.get("/")
def health_check():
    return {"status": "Document Risk Analyzer API is running"}


@app.post("/analyze-document")
async def analyze_document(file: UploadFile = File(...)):
    """
    Upload supported files:
    - PDF
    - PNG
    - JPG
    - Scanned invoices
    - Legal agreements
    """

    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")

    try:
        file_bytes = await file.read()

        if len(file_bytes) == 0:
            raise HTTPException(status_code=400, detail="Empty file uploaded")

        # Step 1: OCR / Text Extraction
        extracted_text = extract_text_from_document(file_bytes, file.filename)

        if not extracted_text or len(extracted_text.strip()) == 0:
            raise HTTPException(
                status_code=500,
                detail="Failed to extract text from the document"
            )

        # Step 2: Risk Analysis + Summarization (Async Parallel Processing)
        analysis_result = await analyze_risk_and_summarize(extracted_text)

        return {
            "success": True,
            "filename": file.filename,
            "extracted_text_length": len(extracted_text),
            "extracted_text": extracted_text[:1000] + "..." if len(extracted_text) > 1000 else extracted_text,
            "risk_analysis": analysis_result["summary"],
            "metadata": {
                "analysis_timestamp": analysis_result["analysis_timestamp"],
                "chunks_analyzed": analysis_result["chunks_analyzed"],
                "total_text_length": analysis_result["total_text_length"]
            }
        }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "filename": file.filename if file else "unknown"
            }
        )

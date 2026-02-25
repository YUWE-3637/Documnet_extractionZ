"""
OCR Service - Text extraction from documents
Reuses existing PDF processing logic from main.py
"""

import os
import io
from typing import Tuple
import pdfplumber
from pdf2image import convert_from_bytes
from PIL import Image
from openai import OpenAI
import base64
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def is_scanned_pdf(pdf_bytes: bytes) -> bool:
    """Check if PDF is scanned (image-based) or text-based"""
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            if len(pdf.pages) == 0:
                return True
            text = pdf.pages[0].extract_text()
            return text is None or len(text.strip()) < 50
    except:
        return True


def extract_text_from_pdf_fast(pdf_bytes: bytes) -> str:
    """Fast text extraction for text-based PDFs"""
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


def convert_pdf_to_images(pdf_bytes: bytes) -> list[bytes]:
    """Convert PDF pages to images for OCR"""
    images = convert_from_bytes(pdf_bytes, dpi=200)
    image_bytes_list = []
    
    for img in images:
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        image_bytes_list.append(img_byte_arr.getvalue())
    
    return image_bytes_list


def encode_image_to_base64(image_bytes: bytes) -> str:
    """Encode image bytes to base64"""
    return base64.b64encode(image_bytes).decode("utf-8")


def extract_text_with_ocr(image_bytes_list: list[bytes]) -> str:
    """Use GPT-4o Vision for OCR on scanned documents"""
    all_text = []
    
    for idx, img_bytes in enumerate(image_bytes_list):
        base64_img = encode_image_to_base64(img_bytes)
        page_indicator = f" (Page {idx + 1}/{len(image_bytes_list)})" if len(image_bytes_list) > 1 else ""
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Extract ALL text from this document page{page_indicator}. Preserve structure, headings, and formatting."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_img}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=4000
        )
        
        page_text = response.choices[0].message.content
        if len(image_bytes_list) > 1:
            all_text.append(f"\n\n--- PAGE {idx + 1} ---\n\n{page_text}")
        else:
            all_text.append(page_text)
    
    return "\n".join(all_text)


def extract_text_from_document(file_bytes: bytes, filename: str) -> Tuple[str, int]:
    """
    Smart text extraction - uses fast path for text PDFs, OCR for scanned
    
    Returns:
        Tuple of (extracted_text, page_count)
    """
    is_pdf = filename.lower().endswith('.pdf')
    
    if is_pdf:
        # Check if text-based or scanned
        if not is_scanned_pdf(file_bytes):
            # Fast path: Text-based PDF
            try:
                text = extract_text_from_pdf_fast(file_bytes)
                with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                    page_count = len(pdf.pages)
                return text, page_count
            except Exception:
                pass
        
        # Slow path: Scanned PDF - use OCR
        image_bytes_list = convert_pdf_to_images(file_bytes)
        text = extract_text_with_ocr(image_bytes_list)
        return text, len(image_bytes_list)
    else:
        # Image file - use OCR
        image_bytes_list = [file_bytes]
        text = extract_text_with_ocr(image_bytes_list)
        return text, 1

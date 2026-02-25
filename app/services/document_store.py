"""
Document Storage Service - In-memory store with optional persistence
"""

import json
import os
from typing import Dict, Optional
from datetime import datetime
from app.models.schemas import DocumentMetadata


class DocumentStore:
    """Simple in-memory document store with JSON persistence"""
    
    def __init__(self, storage_dir: str = "app/storage"):
        self.storage_dir = storage_dir
        self.documents: Dict[str, DocumentMetadata] = {}
        os.makedirs(storage_dir, exist_ok=True)
        self._load_from_disk()
    
    def _get_file_path(self, document_id: str) -> str:
        return os.path.join(self.storage_dir, f"{document_id}.json")
    
    def _load_from_disk(self):
        """Load existing documents from disk"""
        if not os.path.exists(self.storage_dir):
            return
        
        for filename in os.listdir(self.storage_dir):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join(self.storage_dir, filename), 'r') as f:
                        data = json.load(f)
                        doc_id = data['document_id']
                        self.documents[doc_id] = DocumentMetadata(**data)
                except Exception as e:
                    print(f"Error loading {filename}: {e}")
    
    def save_document(self, metadata: DocumentMetadata) -> str:
        """Save document metadata"""
        self.documents[metadata.document_id] = metadata
        
        # Persist to disk
        with open(self._get_file_path(metadata.document_id), 'w') as f:
            json.dump(metadata.model_dump(), f, default=str)
        
        return metadata.document_id
    
    def get_document(self, document_id: str) -> Optional[DocumentMetadata]:
        """Retrieve document metadata"""
        return self.documents.get(document_id)
    
    def delete_document(self, document_id: str) -> bool:
        """Delete document"""
        if document_id in self.documents:
            del self.documents[document_id]
            
            # Delete from disk
            file_path = self._get_file_path(document_id)
            if os.path.exists(file_path):
                os.remove(file_path)
            
            return True
        return False
    
    def list_documents(self) -> list[DocumentMetadata]:
        """List all documents"""
        return list(self.documents.values())


# Global store instance
document_store = DocumentStore()

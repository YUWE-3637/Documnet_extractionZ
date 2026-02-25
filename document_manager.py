"""
Production-Grade Document Manager with FAISS Vector Storage
Handles document ingestion, chunking, embedding, and daily sharding
"""

import faiss
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime
import threading
import os
import pickle
from openai import OpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from database import MetadataDB


class DocumentManager:
    """
    Thread-safe document processing and vector storage manager
    Implements daily sharding strategy for 3-day retention
    """
    
    def __init__(
        self,
        openai_api_key: str,
        data_dir: str = "data",
        embedding_model: str = "text-embedding-3-small",
        dimension: int = 1536
    ):
        self.client = OpenAI(api_key=openai_api_key)
        self.embedding_model = embedding_model
        self.dimension = dimension
        self.data_dir = data_dir
        
        # Thread safety
        self.lock = threading.Lock()
        
        # Metadata database
        self.metadata_db = MetadataDB(db_path=f"{data_dir}/vector_metadata.db")
        
        # Text splitter (chunk_size: 600, overlap: 60)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=600,
            chunk_overlap=60,
            length_function=len,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
        )
        
        # Create data directory
        os.makedirs(data_dir, exist_ok=True)
    
    def _get_shard_date(self) -> str:
        """Get current date in YYYYMMDD format for daily sharding"""
        return datetime.now().strftime("%Y%m%d")
    
    def _get_index_path(self, shard_date: str) -> str:
        """Get file path for a specific date shard"""
        return os.path.join(self.data_dir, f"index_{shard_date}.faiss")
    
    def _load_or_create_index(self, shard_date: str) -> tuple:
        """
        Load existing index or create new one for the shard date
        
        Returns:
            (faiss_index, current_vector_count)
        """
        index_path = self._get_index_path(shard_date)
        
        if os.path.exists(index_path):
            # Load existing index
            index = faiss.read_index(index_path)
            vector_count = index.ntotal
        else:
            # Create new FlatL2 index (exact search, production-ready)
            index = faiss.IndexFlatL2(self.dimension)
            vector_count = 0
            
            # Register in database
            self.metadata_db.register_shard(shard_date, index_path, 0)
        
        return index, vector_count
    
    def _save_index(self, index: faiss.Index, shard_date: str):
        """Save FAISS index to disk"""
        index_path = self._get_index_path(shard_date)
        faiss.write_index(index, index_path)
        
        # Update shard metadata
        self.metadata_db.register_shard(shard_date, index_path, index.ntotal)
    
    def _get_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings using OpenAI text-embedding-3-small
        
        Args:
            texts: List of text chunks to embed
        
        Returns:
            numpy array of embeddings (n_chunks, dimension)
        """
        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=texts
        )
        
        embeddings = np.array([
            item.embedding for item in response.data
        ], dtype=np.float32)
        
        return embeddings
    
    def add_document(
        self,
        user_id: str,
        document_text: str,
        document_name: str,
        page_numbers: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Process and index a document for a specific user
        
        Args:
            user_id: Unique user identifier
            document_text: Full text content
            document_name: Name/filename of the document
            page_numbers: Optional list of page numbers (aligned with text sections)
        
        Returns:
            Dict with processing statistics
        """
        with self.lock:
            # Split into chunks
            chunks = self.text_splitter.split_text(document_text)
            
            if not chunks:
                return {
                    "success": False,
                    "error": "No chunks created from document",
                    "chunks_processed": 0
                }
            
            # Generate embeddings
            embeddings = self._get_embeddings(chunks)
            
            # Get current shard date and index
            shard_date = self._get_shard_date()
            index, current_count = self._load_or_create_index(shard_date)
            
            # Add vectors to FAISS
            index.add(embeddings)
            
            # Prepare metadata for database
            vectors_data = []
            for idx, chunk in enumerate(chunks):
                page_num = page_numbers[idx] if page_numbers and idx < len(page_numbers) else 0
                
                vectors_data.append({
                    'vector_id': current_count + idx,
                    'document_name': document_name,
                    'page_number': page_num,
                    'chunk_index': idx,
                    'page_content': chunk
                })
            
            # Save metadata to database
            self.metadata_db.add_vectors(user_id, shard_date, vectors_data)
            
            # Save updated index
            self._save_index(index, shard_date)
            
            return {
                "success": True,
                "user_id": user_id,
                "document_name": document_name,
                "chunks_processed": len(chunks),
                "shard_date": shard_date,
                "total_vectors_in_shard": index.ntotal
            }
    
    def search_user_documents(
        self,
        user_id: str,
        query: str,
        top_k: int = 5,
        retention_days: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Search across user's documents within retention window
        
        Args:
            user_id: User identifier
            query: Search query text
            top_k: Number of results to return
            retention_days: Days of history to search (default: 3)
        
        Returns:
            List of search results with metadata and scores
        """
        with self.lock:
            # Get query embedding
            query_embedding = self._get_embeddings([query])[0].reshape(1, -1)
            
            # Get active shards
            active_shards = self.metadata_db.get_active_shards(retention_days)
            
            if not active_shards:
                return []
            
            # Search across all active shards
            all_results = []
            
            for shard in active_shards:
                shard_date = shard['shard_date']
                index_path = shard['index_path']
                
                if not os.path.exists(index_path):
                    continue
                
                # Load index
                index = faiss.read_index(index_path)
                
                # Search
                distances, indices = index.search(query_embedding, top_k * 3)  # Over-retrieve
                
                # Get metadata for results (filter by user_id)
                vector_ids = indices[0].tolist()
                metadata_list = self.metadata_db.get_vector_metadata(
                    user_id, vector_ids, shard_date
                )
                
                # Combine scores with metadata
                for meta in metadata_list:
                    vector_idx = vector_ids.index(meta['vector_id'])
                    distance = float(distances[0][vector_idx])
                    
                    all_results.append({
                        **meta,
                        'distance': distance,
                        'score': 1 / (1 + distance),  # Similarity score
                        'shard_date': shard_date
                    })
            
            # Sort by score and return top_k
            all_results.sort(key=lambda x: x['score'], reverse=True)
            
            return all_results[:top_k]
    
    def cleanup_stale_data(self, retention_days: int = 3) -> Dict[str, int]:
        """
        Delete all data older than retention_days
        Thread-safe cleanup of old shards
        
        Args:
            retention_days: Number of days to retain (default: 3)
        
        Returns:
            Statistics on deleted data
        """
        with self.lock:
            return self.metadata_db.delete_stale_data(retention_days)
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get statistics for a user's indexed documents"""
        total_chunks = self.metadata_db.get_user_document_count(user_id)
        active_shards = self.metadata_db.get_active_shards(3)
        
        return {
            "user_id": user_id,
            "total_chunks": total_chunks,
            "active_shards": len(active_shards),
            "retention_days": 3
        }

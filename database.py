"""
SQLite Database Manager for FAISS Metadata
Handles user-to-vector mapping, metadata storage, and 3-day retention tracking
"""

import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import threading
import os


class MetadataDB:
    """Thread-safe SQLite database for managing FAISS vector metadata"""
    
    def __init__(self, db_path: str = "data/vector_metadata.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._initialize_db()
    
    def _initialize_db(self):
        """Create tables if they don't exist"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Main metadata table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vector_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vector_id INTEGER NOT NULL,
                    user_id TEXT NOT NULL,
                    shard_date TEXT NOT NULL,
                    document_name TEXT NOT NULL,
                    page_number INTEGER,
                    chunk_index INTEGER,
                    page_content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_user_shard (user_id, shard_date),
                    INDEX idx_vector (vector_id, shard_date)
                )
            """)
            
            # Shard tracking table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS index_shards (
                    shard_date TEXT PRIMARY KEY,
                    index_path TEXT NOT NULL,
                    vector_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            conn.close()
    
    def add_vectors(
        self,
        user_id: str,
        shard_date: str,
        vectors_data: List[Dict[str, Any]]
    ) -> List[int]:
        """
        Add vector metadata for a batch of chunks
        
        Args:
            user_id: Unique user identifier
            shard_date: Date shard (YYYYMMDD format)
            vectors_data: List of dicts with keys: vector_id, document_name, 
                         page_number, chunk_index, page_content
        
        Returns:
            List of inserted row IDs
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            inserted_ids = []
            for data in vectors_data:
                cursor.execute("""
                    INSERT INTO vector_metadata 
                    (vector_id, user_id, shard_date, document_name, page_number, 
                     chunk_index, page_content)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    data['vector_id'],
                    user_id,
                    shard_date,
                    data['document_name'],
                    data.get('page_number', 0),
                    data.get('chunk_index', 0),
                    data['page_content']
                ))
                inserted_ids.append(cursor.lastrowid)
            
            conn.commit()
            conn.close()
            
            return inserted_ids
    
    def get_vector_metadata(
        self,
        user_id: str,
        vector_ids: List[int],
        shard_date: str
    ) -> List[Dict[str, Any]]:
        """
        Retrieve metadata for specific vectors belonging to a user
        
        Args:
            user_id: User identifier
            vector_ids: List of vector IDs to retrieve
            shard_date: Date shard to query
        
        Returns:
            List of metadata dictionaries
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            placeholders = ','.join('?' * len(vector_ids))
            cursor.execute(f"""
                SELECT vector_id, document_name, page_number, chunk_index, 
                       page_content, created_at
                FROM vector_metadata
                WHERE user_id = ? 
                  AND shard_date = ?
                  AND vector_id IN ({placeholders})
            """, [user_id, shard_date] + vector_ids)
            
            results = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return results
    
    def register_shard(self, shard_date: str, index_path: str, vector_count: int = 0):
        """Register a new FAISS index shard"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO index_shards (shard_date, index_path, vector_count)
                VALUES (?, ?, ?)
            """, (shard_date, index_path, vector_count))
            
            conn.commit()
            conn.close()
    
    def get_active_shards(self, retention_days: int = 3) -> List[Dict[str, Any]]:
        """Get all index shards within retention window"""
        cutoff_date = (datetime.now() - timedelta(days=retention_days)).strftime("%Y%m%d")
        
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT shard_date, index_path, vector_count
                FROM index_shards
                WHERE shard_date >= ?
                ORDER BY shard_date DESC
            """, (cutoff_date,))
            
            results = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return results
    
    def delete_stale_data(self, retention_days: int = 3) -> Dict[str, int]:
        """
        Delete all data older than retention_days
        
        Returns:
            Dict with counts of deleted records
        """
        cutoff_date = (datetime.now() - timedelta(days=retention_days)).strftime("%Y%m%d")
        
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get stale shards
            cursor.execute("""
                SELECT shard_date, index_path 
                FROM index_shards 
                WHERE shard_date < ?
            """, (cutoff_date,))
            stale_shards = cursor.fetchall()
            
            # Delete metadata
            cursor.execute("""
                DELETE FROM vector_metadata 
                WHERE shard_date < ?
            """, (cutoff_date,))
            deleted_vectors = cursor.rowcount
            
            # Delete shard records
            cursor.execute("""
                DELETE FROM index_shards 
                WHERE shard_date < ?
            """, (cutoff_date,))
            deleted_shards = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            # Delete actual FAISS index files
            for shard_date, index_path in stale_shards:
                if os.path.exists(index_path):
                    os.remove(index_path)
            
            return {
                "deleted_vectors": deleted_vectors,
                "deleted_shards": deleted_shards,
                "deleted_files": len(stale_shards)
            }
    
    def get_user_document_count(self, user_id: str) -> int:
        """Get total number of chunks for a user across all active shards"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) FROM vector_metadata
                WHERE user_id = ?
            """, (user_id,))
            
            count = cursor.fetchone()[0]
            conn.close()
            
            return count

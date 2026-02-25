"""
Production-Grade Query Engine for RAG
Handles retrieval, reranking, and generation with source attribution
"""

from typing import List, Dict, Any, Optional
from openai import OpenAI
from document_manager import DocumentManager


class QueryEngine:
    """
    RAG query engine with retrieval, reranking, and GPT-4o generation
    Provides clear source attribution for all responses
    """
    
    def __init__(
        self,
        document_manager: DocumentManager,
        openai_api_key: str,
        generation_model: str = "gpt-4o-mini"
    ):
        self.doc_manager = document_manager
        self.client = OpenAI(api_key=openai_api_key)
        self.generation_model = generation_model
    
    def _rerank_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Simple reranking based on score and recency
        
        Args:
            results: List of search results with scores
        
        Returns:
            Reranked results
        """
        # Weight: 70% similarity score + 30% recency
        for result in results:
            shard_date = result.get('shard_date', '20000101')
            recency_score = int(shard_date) / 20300101  # Normalize to 0-1 range
            
            result['final_score'] = (
                0.7 * result['score'] + 
                0.3 * recency_score
            )
        
        # Sort by final score
        results.sort(key=lambda x: x['final_score'], reverse=True)
        
        return results
    
    def _format_context(self, results: List[Dict[str, Any]]) -> str:
        """
        Format retrieved chunks into context string with citations
        
        Args:
            results: List of search results
        
        Returns:
            Formatted context string
        """
        if not results:
            return "No relevant context found."
        
        context_parts = []
        
        for idx, result in enumerate(results, 1):
            doc_name = result.get('document_name', 'Unknown')
            page_num = result.get('page_number', 0)
            content = result.get('page_content', '')
            
            citation = f"[Source {idx}: {doc_name}, Page {page_num}]"
            context_parts.append(f"{citation}\n{content}\n")
        
        return "\n---\n".join(context_parts)
    
    def generate_response(
        self,
        query: str,
        user_id: str,
        top_k: int = 5,
        include_sources: bool = True
    ) -> Dict[str, Any]:
        """
        Generate an answer to the user's query using RAG
        
        Args:
            query: User's question
            user_id: User identifier for multi-tenancy
            top_k: Number of chunks to retrieve
            include_sources: Whether to include source citations
        
        Returns:
            Dict with answer, sources, and metadata
        """
        # Step 1: Retrieve relevant chunks
        search_results = self.doc_manager.search_user_documents(
            user_id=user_id,
            query=query,
            top_k=top_k
        )
        
        if not search_results:
            return {
                "success": False,
                "answer": "I don't have any documents to search through. Please upload documents first.",
                "sources": [],
                "query": query
            }
        
        # Step 2: Rerank results
        reranked_results = self._rerank_results(search_results)
        
        # Step 3: Format context
        context = self._format_context(reranked_results)
        
        # Step 4: Generate response with GPT-4o
        system_prompt = """You are a helpful AI assistant that answers questions based on provided documents.

CRITICAL RULES:
1. **Only use information from the provided context** - Do not use external knowledge
2. **Always cite your sources** - Use the format "According to [Document Name], Page [X]..."
3. **Be specific and accurate** - Quote directly when possible
4. **If the context doesn't contain the answer** - Say "The provided documents don't contain information about this"
5. **Use clear, professional language** suitable for Indian legal and business contexts

Your answers should be:
- Factual and grounded in the documents
- Well-structured with clear citations
- Helpful and actionable
"""
        
        user_prompt = f"""Based on the following document excerpts, please answer the question.

QUESTION: {query}

DOCUMENT CONTEXT:
{context}

ANSWER:"""
        
        response = self.client.chat.completions.create(
            model=self.generation_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=800
        )
        
        answer = response.choices[0].message.content
        
        # Step 5: Format sources for output
        sources = []
        if include_sources:
            for idx, result in enumerate(reranked_results, 1):
                sources.append({
                    "source_number": idx,
                    "document_name": result.get('document_name', 'Unknown'),
                    "page_number": result.get('page_number', 0),
                    "chunk_preview": result.get('page_content', '')[:200] + "...",
                    "relevance_score": round(result.get('final_score', 0), 3)
                })
        
        return {
            "success": True,
            "answer": answer,
            "sources": sources,
            "query": query,
            "user_id": user_id,
            "chunks_retrieved": len(search_results)
        }
    
    def ask(self, query: str, user_id: str, **kwargs) -> str:
        """
        Simplified interface - returns just the answer text
        
        Args:
            query: User's question
            user_id: User identifier
            **kwargs: Additional arguments for generate_response
        
        Returns:
            Answer text
        """
        result = self.generate_response(query, user_id, **kwargs)
        return result.get("answer", "No answer generated")
    
    def get_relevant_chunks(
        self,
        query: str,
        user_id: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get relevant chunks without generation (for debugging/inspection)
        
        Args:
            query: Search query
            user_id: User identifier
            top_k: Number of chunks to return
        
        Returns:
            List of relevant chunks with metadata
        """
        results = self.doc_manager.search_user_documents(
            user_id=user_id,
            query=query,
            top_k=top_k
        )
        
        return self._rerank_results(results)

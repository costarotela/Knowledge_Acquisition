"""
Knowledge management module for RAG agent.
"""
from typing import List, Dict, Any, Optional
import logging

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor

from .schemas import KnowledgeFragment

logger = logging.getLogger(__name__)

class KnowledgeManager:
    """Manager for knowledge retrieval and storage."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._setup_stores()
    
    def _setup_stores(self):
        """Setup vector store and retriever."""
        self.embeddings = OpenAIEmbeddings()
        self.vector_store = Chroma(
            embedding_function=self.embeddings,
            persist_directory=self.config.get("vector_store_path")
        )
        
        # Setup base retriever
        self.base_retriever = self.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": self.config.get("max_documents", 5)}
        )
        
        # Setup contextual compression if enabled
        if self.config.get("use_contextual_compression", True):
            self.retriever = ContextualCompressionRetriever(
                base_compressor=LLMChainExtractor(),
                base_retriever=self.base_retriever
            )
        else:
            self.retriever = self.base_retriever
    
    async def retrieve_knowledge(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[KnowledgeFragment]:
        """Retrieve relevant knowledge for a query."""
        try:
            # Apply filters if provided
            search_kwargs = {"k": self.config.get("max_documents", 5)}
            if filters:
                search_kwargs["filter"] = filters
            
            # Retrieve documents
            docs = await self.retriever.aget_relevant_documents(
                query,
                **search_kwargs
            )
            
            # Convert to KnowledgeFragments
            fragments = []
            for doc in docs:
                fragment = KnowledgeFragment(
                    id=doc.metadata.get("id", ""),
                    content=doc.page_content,
                    metadata=doc.metadata,
                    confidence=doc.metadata.get("confidence", 0.8)
                )
                fragments.append(fragment)
            
            return fragments
            
        except Exception as e:
            logger.error(f"Error retrieving knowledge: {str(e)}")
            return []
    
    async def store_knowledge(
        self,
        fragments: List[KnowledgeFragment]
    ) -> bool:
        """Store new knowledge fragments."""
        try:
            # Convert fragments to documents
            texts = [f.content for f in fragments]
            metadatas = [f.metadata for f in fragments]
            
            # Store in vector store
            self.vector_store.add_texts(
                texts=texts,
                metadatas=metadatas
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error storing knowledge: {str(e)}")
            return False
    
    async def update_fragment(
        self,
        fragment_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update an existing knowledge fragment."""
        try:
            # Get existing fragment
            results = self.vector_store.get(
                where={"id": fragment_id}
            )
            
            if not results:
                logger.error(f"Fragment {fragment_id} not found")
                return False
            
            # Update fragment
            self.vector_store.update(
                ids=[fragment_id],
                documents=[updates.get("content", results[0])],
                metadatas=[{**results[0].metadata, **updates.get("metadata", {})}]
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating fragment: {str(e)}")
            return False
    
    def validate_fragment(self, fragment: KnowledgeFragment) -> bool:
        """Validate a knowledge fragment."""
        # Check required fields
        if not fragment.content or not fragment.id:
            return False
        
        # Check content length
        min_length = self.config.get("min_fragment_length", 10)
        if len(fragment.content.split()) < min_length:
            return False
        
        # Check confidence
        min_confidence = self.config.get("min_confidence", 0.5)
        if fragment.confidence < min_confidence:
            return False
        
        return True

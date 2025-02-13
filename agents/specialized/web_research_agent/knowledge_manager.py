"""
Knowledge management for Web Research Agent.
"""
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

from .schemas import (
    WebSource, ContentFragment, FactClaim,
    ResearchContext, ResearchFindings
)

logger = logging.getLogger(__name__)

class WebResearchKnowledgeManager:
    """Manager for web research knowledge."""
    
    def __init__(
        self,
        vector_store_path: str,
        embeddings: Optional[OpenAIEmbeddings] = None
    ):
        """Initialize knowledge manager."""
        self.embeddings = embeddings or OpenAIEmbeddings()
        self.vector_store = Chroma(
            persist_directory=vector_store_path,
            embedding_function=self.embeddings
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
    
    async def store_research_findings(
        self,
        findings: ResearchFindings,
        analysis_results: Dict[str, Any]
    ) -> bool:
        """Store research findings."""
        try:
            # Store sources and content
            await self._store_sources(findings.sources)
            await self._store_content_fragments(findings.key_fragments)
            
            # Store verified facts
            await self._store_facts(findings.verified_facts)
            
            # Store analysis results
            await self._store_analysis_results(findings, analysis_results)
            
            return True
            
        except Exception as e:
            logger.error(f"Error storing research findings: {str(e)}")
            return False
    
    async def _store_sources(self, sources: List[WebSource]):
        """Store web sources in vector store."""
        documents = []
        
        for source in sources:
            documents.append({
                "text": f"""
                Title: {source.title}
                Description: {source.description or 'No description'}
                Author: {source.author or 'Unknown'}
                Domain: {source.domain}
                """,
                "metadata": {
                    "url": str(source.url),
                    "domain": source.domain,
                    "trust_score": source.trust_score,
                    "published_date": source.published_date.isoformat() if source.published_date else None,
                    "type": "web_source"
                }
            })
        
        if documents:
            texts = [d["text"] for d in documents]
            metadatas = [d["metadata"] for d in documents]
            self.vector_store.add_texts(texts=texts, metadatas=metadatas)
    
    async def _store_content_fragments(self, fragments: List[ContentFragment]):
        """Store content fragments in vector store."""
        documents = []
        
        for fragment in fragments:
            # Split content into chunks
            chunks = self.text_splitter.split_text(fragment.content)
            
            # Create documents with metadata
            documents.extend([{
                "text": chunk,
                "metadata": {
                    "source_url": str(fragment.source_url),
                    "context": fragment.context,
                    "relevance_score": fragment.relevance_score,
                    "sentiment_score": fragment.sentiment_score,
                    "type": "content_fragment"
                }
            } for chunk in chunks])
        
        if documents:
            texts = [d["text"] for d in documents]
            metadatas = [d["metadata"] for d in documents]
            self.vector_store.add_texts(texts=texts, metadatas=metadatas)
    
    async def _store_facts(self, facts: List[FactClaim]):
        """Store verified facts in vector store."""
        documents = []
        
        for fact in facts:
            documents.append({
                "text": fact.statement,
                "metadata": {
                    "source_urls": [str(url) for url in fact.source_urls],
                    "confidence_score": fact.confidence_score,
                    "verification_status": fact.verification_status,
                    "domain_context": fact.domain_context,
                    "type": "fact_claim"
                }
            })
        
        if documents:
            texts = [d["text"] for d in documents]
            metadatas = [d["metadata"] for d in documents]
            self.vector_store.add_texts(texts=texts, metadatas=metadatas)
    
    async def _store_analysis_results(
        self,
        findings: ResearchFindings,
        results: Dict[str, Any]
    ):
        """Store analysis results."""
        documents = []
        
        # Store research context
        documents.append({
            "text": f"""
            Query: {findings.context.query}
            Objective: {findings.context.objective}
            Domain: {findings.context.domain or 'General'}
            """,
            "metadata": {
                "type": "research_context",
                "required_depth": findings.context.required_depth,
                "time_constraints": findings.context.time_constraints
            }
        })
        
        # Store key findings
        if "key_findings" in results:
            for finding in results["key_findings"]:
                documents.append({
                    "text": finding["finding"],
                    "metadata": {
                        "type": "key_finding",
                        "confidence": finding["confidence"],
                        "implications": finding["implications"]
                    }
                })
        
        # Store knowledge gaps
        if "knowledge_gaps" in results:
            for gap in results["knowledge_gaps"]:
                documents.append({
                    "text": gap["gap"],
                    "metadata": {
                        "type": "knowledge_gap",
                        "impact": gap["impact"],
                        "suggestions": gap["research_suggestions"]
                    }
                })
        
        if documents:
            texts = [d["text"] for d in documents]
            metadatas = [d["metadata"] for d in documents]
            self.vector_store.add_texts(texts=texts, metadatas=metadatas)
    
    async def query_knowledge(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Query stored knowledge."""
        try:
            results = self.vector_store.similarity_search(
                query,
                filter=filters,
                k=limit
            )
            
            return [{
                "content": doc.page_content,
                "metadata": doc.metadata,
                "similarity": doc.similarity
            } for doc in results]
            
        except Exception as e:
            logger.error(f"Error querying knowledge: {str(e)}")
            return []
    
    async def validate_fact(
        self,
        fact: FactClaim
    ) -> Dict[str, Any]:
        """Validate a fact claim."""
        try:
            # Query similar facts
            similar = await self.query_knowledge(
                fact.statement,
                filters={"type": "fact_claim"},
                limit=3
            )
            
            # Check for support and contradictions
            supporting = []
            contradicting = []
            
            for item in similar:
                if item["similarity"] > 0.8:
                    supporting.append(item)
                elif item["similarity"] > 0.5:
                    # Check for contradictions
                    if self._contradicts(fact.statement, item["content"]):
                        contradicting.append(item)
            
            # Calculate confidence
            confidence = fact.confidence_score
            if supporting:
                confidence = min(
                    confidence + len(supporting) * 0.1,
                    1.0
                )
            if contradicting:
                confidence = max(
                    confidence - len(contradicting) * 0.2,
                    0.1
                )
            
            return {
                "valid": len(contradicting) == 0,
                "confidence": confidence,
                "supporting_evidence": supporting,
                "contradicting_evidence": contradicting,
                "verification_status": (
                    "verified" if len(supporting) > 0 and len(contradicting) == 0
                    else "disputed" if len(contradicting) > 0
                    else "unverified"
                )
            }
            
        except Exception as e:
            logger.error(f"Error validating fact: {str(e)}")
            return {
                "valid": False,
                "confidence": 0.0,
                "error": str(e)
            }
    
    def _contradicts(self, statement1: str, statement2: str) -> bool:
        """Check if two statements contradict each other."""
        # Simple contradiction check
        # TODO: Implement more sophisticated contradiction detection
        negation_words = {"not", "no", "never", "false", "incorrect", "wrong"}
        
        has_negation1 = any(word in statement1.lower() for word in negation_words)
        has_negation2 = any(word in statement2.lower() for word in negation_words)
        
        return has_negation1 != has_negation2

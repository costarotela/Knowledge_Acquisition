"""
Knowledge management for GitHub Agent.
"""
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

from .schemas import (
    RepoContext, CodeFragment, IssueInfo,
    CommitInfo, RepositoryKnowledge
)

logger = logging.getLogger(__name__)

class GitHubKnowledgeManager:
    """Manager for GitHub repository knowledge."""
    
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
    
    async def store_repository_knowledge(
        self,
        knowledge: RepositoryKnowledge,
        analysis_results: Dict[str, Any]
    ) -> bool:
        """Store repository knowledge."""
        try:
            # Store code fragments
            await self._store_code_fragments(knowledge.key_files)
            
            # Store development insights
            await self._store_development_insights(
                knowledge.important_issues,
                knowledge.significant_commits
            )
            
            # Store analysis results
            await self._store_analysis_results(
                knowledge.context,
                analysis_results
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error storing repository knowledge: {str(e)}")
            return False
    
    async def _store_code_fragments(
        self,
        fragments: List[CodeFragment]
    ):
        """Store code fragments in vector store."""
        documents = []
        
        for fragment in fragments:
            # Split code into chunks
            chunks = self.text_splitter.split_text(fragment.content)
            
            # Create documents with metadata
            documents.extend([{
                "text": chunk,
                "metadata": {
                    "path": fragment.path,
                    "language": fragment.language,
                    "commit_hash": fragment.commit_hash,
                    "last_modified": fragment.last_modified.isoformat(),
                    "author": fragment.author,
                    "type": "code_fragment"
                }
            } for chunk in chunks])
        
        # Add to vector store
        if documents:
            texts = [d["text"] for d in documents]
            metadatas = [d["metadata"] for d in documents]
            self.vector_store.add_texts(texts=texts, metadatas=metadatas)
    
    async def _store_development_insights(
        self,
        issues: List[IssueInfo],
        commits: List[CommitInfo]
    ):
        """Store development insights."""
        documents = []
        
        # Process issues
        for issue in issues:
            documents.append({
                "text": f"Issue #{issue.number}: {issue.title}\n{issue.body}",
                "metadata": {
                    "type": "issue",
                    "number": issue.number,
                    "state": issue.state,
                    "author": issue.author,
                    "created_at": issue.created_at.isoformat(),
                    "labels": issue.labels
                }
            })
        
        # Process commits
        for commit in commits:
            documents.append({
                "text": commit.message,
                "metadata": {
                    "type": "commit",
                    "hash": commit.hash,
                    "author": commit.author,
                    "date": commit.date.isoformat(),
                    "files_changed": commit.files_changed
                }
            })
        
        # Add to vector store
        if documents:
            texts = [d["text"] for d in documents]
            metadatas = [d["metadata"] for d in documents]
            self.vector_store.add_texts(texts=texts, metadatas=metadatas)
    
    async def _store_analysis_results(
        self,
        context: RepoContext,
        results: Dict[str, Any]
    ):
        """Store analysis results."""
        # Create document for context
        context_doc = {
            "text": f"""
            Repository: {context.owner}/{context.name}
            Description: {context.description}
            Topics: {', '.join(context.topics)}
            Languages: {', '.join(context.languages.keys())}
            """,
            "metadata": {
                "type": "repo_context",
                "owner": context.owner,
                "name": context.name,
                "stars": context.stars,
                "forks": context.forks,
                "last_update": context.last_update.isoformat()
            }
        }
        
        # Create documents for analysis results
        analysis_docs = []
        
        # Process hypotheses
        if "hypotheses" in results:
            for h in results["hypotheses"]:
                analysis_docs.append({
                    "text": h["statement"],
                    "metadata": {
                        "type": "hypothesis",
                        "confidence": h["confidence"],
                        "evidence": h["evidence"]
                    }
                })
        
        # Process insights
        if "insights" in results:
            for i in results["insights"]:
                analysis_docs.append({
                    "text": i["content"],
                    "metadata": {
                        "type": "insight",
                        "category": i["category"],
                        "confidence": i["confidence"],
                        "evidence": i["supporting_evidence"]
                    }
                })
        
        # Add to vector store
        documents = [context_doc] + analysis_docs
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
            # Search vector store
            results = self.vector_store.similarity_search(
                query,
                filter=filters,
                k=limit
            )
            
            # Format results
            return [{
                "content": doc.page_content,
                "metadata": doc.metadata,
                "similarity": doc.similarity
            } for doc in results]
            
        except Exception as e:
            logger.error(f"Error querying knowledge: {str(e)}")
            return []
    
    async def validate_knowledge(
        self,
        knowledge_item: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate a knowledge item."""
        try:
            # Query similar items
            similar = await self.query_knowledge(
                knowledge_item["content"],
                filters={"type": knowledge_item["type"]},
                limit=3
            )
            
            # Check for contradictions
            contradictions = []
            supporting_evidence = []
            
            for item in similar:
                if item["similarity"] > 0.8:
                    supporting_evidence.append(item)
                elif item["similarity"] > 0.5:
                    # Check for potential contradictions
                    if self._contradicts(knowledge_item, item):
                        contradictions.append(item)
            
            return {
                "valid": len(contradictions) == 0,
                "confidence": min(
                    knowledge_item.get("confidence", 0.5),
                    len(supporting_evidence) * 0.2
                ),
                "contradictions": contradictions,
                "supporting_evidence": supporting_evidence
            }
            
        except Exception as e:
            logger.error(f"Error validating knowledge: {str(e)}")
            return {
                "valid": False,
                "confidence": 0.0,
                "error": str(e)
            }
    
    def _contradicts(
        self,
        item1: Dict[str, Any],
        item2: Dict[str, Any]
    ) -> bool:
        """Check if two knowledge items contradict each other."""
        # Simple contradiction check based on negation
        # TODO: Implement more sophisticated contradiction detection
        return any(
            neg in item2["content"].lower()
            for neg in ["not", "no", "never", "false"]
            if neg in item1["content"].lower()
        )

"""
Academic research agent for knowledge extraction from papers and journals.
"""
from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime
import arxiv
from scholarly import scholarly
import pandas as pd
from pydantic import BaseModel

from ..base import BaseAgent
from core_system.pipeline.schemas import ProcessingStage, DataType
from core_system.monitoring.monitor import MonitoringSystem

class PaperMetadata(BaseModel):
    """Metadata for academic paper."""
    title: str
    authors: List[str]
    abstract: str
    published: datetime
    doi: Optional[str] = None
    citations: Optional[int] = None
    references: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    venue: Optional[str] = None
    url: Optional[str] = None

class PaperContent(BaseModel):
    """Content extracted from paper."""
    metadata: PaperMetadata
    sections: Dict[str, str]
    figures: List[Dict[str, Any]]
    tables: List[Dict[str, Any]]
    equations: List[Dict[str, Any]]
    citations: List[Dict[str, Any]]

class AcademicAgent(BaseAgent):
    """Agent for processing academic papers and research."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize academic agent."""
        super().__init__(config)
        
        # Initialize metrics
        self.monitoring.register_metric(
            name="papers_processed",
            metric_type="counter",
            description="Number of papers processed"
        )
        
        self.monitoring.register_metric(
            name="citations_extracted",
            metric_type="counter",
            description="Number of citations extracted"
        )
    
    async def initialize(self):
        """Initialize agent resources."""
        await super().initialize()
        # Initialize any specific resources
    
    async def cleanup(self):
        """Cleanup agent resources."""
        await super().cleanup()
        # Cleanup specific resources
    
    async def _process_extraction(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process extraction task."""
        try:
            # Extract based on source type
            if task.get("source") == "arxiv":
                return await self._process_arxiv(task)
            elif task.get("source") == "scholar":
                return await self._process_scholar(task)
            else:
                raise ValueError(f"Unsupported source: {task.get('source')}")
            
        except Exception as e:
            self.logger.error("Extraction error", error=str(e))
            raise
    
    async def _process_arxiv(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process arXiv paper."""
        paper_id = task["paper_id"]
        
        # Search arXiv
        search = arxiv.Search(
            id_list=[paper_id],
            max_results=1
        )
        
        papers = list(search.results())
        if not papers:
            raise ValueError(f"Paper not found: {paper_id}")
        
        paper = papers[0]
        
        # Extract metadata
        metadata = PaperMetadata(
            title=paper.title,
            authors=[str(author) for author in paper.authors],
            abstract=paper.summary,
            published=paper.published,
            doi=paper.doi,
            url=paper.pdf_url
        )
        
        # Download and process PDF
        content = await self._process_pdf(paper.pdf_url)
        
        # Update metrics
        self.monitoring.record_metric(
            "papers_processed",
            1,
            {"source": "arxiv"}
        )
        
        if content.citations:
            self.monitoring.record_metric(
                "citations_extracted",
                len(content.citations),
                {"source": "arxiv"}
            )
        
        return {
            "metadata": metadata.dict(),
            "content": content.dict()
        }
    
    async def _process_scholar(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process Google Scholar paper."""
        query = task["query"]
        
        # Search Google Scholar
        search_query = scholarly.search_pubs(query)
        paper = next(search_query)
        
        # Extract metadata
        metadata = PaperMetadata(
            title=paper["bib"]["title"],
            authors=paper["bib"]["author"],
            abstract=paper.get("bib", {}).get("abstract", ""),
            published=datetime.strptime(
                paper["bib"]["pub_year"],
                "%Y"
            ),
            citations=paper.get("num_citations"),
            venue=paper["bib"].get("venue")
        )
        
        # Get citations if available
        citations = []
        if paper.get("num_citations", 0) > 0:
            try:
                paper.fill()
                citations = [
                    {
                        "title": cite["bib"]["title"],
                        "authors": cite["bib"]["author"],
                        "year": cite["bib"]["pub_year"]
                    }
                    for cite in paper.get_citedby()
                ]
            except Exception as e:
                self.logger.warning(
                    "Error fetching citations",
                    error=str(e)
                )
        
        # Process content if URL available
        content = None
        if paper.get("pub_url"):
            content = await self._process_pdf(paper["pub_url"])
        
        # Update metrics
        self.monitoring.record_metric(
            "papers_processed",
            1,
            {"source": "scholar"}
        )
        
        if citations:
            self.monitoring.record_metric(
                "citations_extracted",
                len(citations),
                {"source": "scholar"}
            )
        
        return {
            "metadata": metadata.dict(),
            "content": content.dict() if content else None,
            "citations": citations
        }
    
    async def _process_pdf(self, url: str) -> PaperContent:
        """Process PDF content."""
        # TODO: Implement PDF processing
        # This would include:
        # - PDF download
        # - Text extraction
        # - Section identification
        # - Figure/table extraction
        # - Equation parsing
        # - Citation extraction
        return PaperContent(
            metadata=PaperMetadata(
                title="",
                authors=[],
                abstract="",
                published=datetime.now()
            ),
            sections={},
            figures=[],
            tables=[],
            equations=[],
            citations=[]
        )
    
    async def _process_validation(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process validation task."""
        # Validate extracted content
        content = task["content"]
        
        # Basic validation
        if not content.get("metadata"):
            raise ValueError("Missing metadata")
        
        # Validate metadata
        metadata = PaperMetadata(**content["metadata"])
        
        # Additional validation logic
        # TODO: Implement more thorough validation
        
        return {
            "valid": True,
            "metadata": metadata.dict()
        }
    
    async def _process_storage(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process storage task."""
        # Store processed content
        content = task["content"]
        
        # Convert to structured format
        df = pd.DataFrame({
            "title": [content["metadata"]["title"]],
            "authors": [", ".join(content["metadata"]["authors"])],
            "abstract": [content["metadata"]["abstract"]],
            "published": [content["metadata"]["published"]],
            "citations": [content["metadata"].get("citations")],
            "venue": [content["metadata"].get("venue")],
            "processed_at": [datetime.now().isoformat()]
        })
        
        # Save to storage
        # TODO: Implement proper storage
        df.to_csv(
            f"data/processed/papers/{content['metadata']['title']}.csv",
            index=False
        )
        
        return {
            "stored": True,
            "location": f"data/processed/papers/{content['metadata']['title']}.csv"
        }

"""
Academic research implementation.
"""

import asyncio
from typing import Dict, List, Optional, Set
from datetime import datetime
import logging
import json
import re
from urllib.parse import quote_plus
import pandas as pd
import numpy as np
from scholarly import scholarly
import arxiv

from .base import (
    BaseResearcher,
    ResearchQuery,
    ResearchFinding,
    ResearchResult
)
from ...knowledge_base.models import ContentType

logger = logging.getLogger(__name__)


class AcademicResearcher(BaseResearcher):
    """
    Researcher that uses academic sources including:
    - Google Scholar
    - arXiv
    - Semantic Scholar
    - Research paper databases
    """
    
    def __init__(self, config: Optional[Dict] = None, **kwargs):
        super().__init__(config, **kwargs)
        
        # Default config
        self.config.update({
            "apis": {
                "semantic_scholar": {
                    "api_key": None,  # Set via env var
                    "endpoint": "https://api.semanticscholar.org/v1"
                }
            },
            "max_concurrent_downloads": 3,
            "min_citations": 1,
            "max_paper_age_years": 5,
            "fields_of_interest": set(),
            "language": "es"  # Spanish default
        })
        
        # Update with provided config
        if config:
            self.config.update(config)
        
        # Download semaphore
        self._download_semaphore = asyncio.Semaphore(
            self.config["max_concurrent_downloads"]
        )
        
        # Track processed papers to avoid duplicates
        self._processed_papers: Set[str] = set()
    
    async def research(self, query: ResearchQuery) -> ResearchResult:
        """Conduct academic research."""
        start_time = datetime.utcnow()
        
        try:
            # 1. Check cache
            cache_key = self._get_cache_key(query)
            cached = self._load_cache(cache_key)
            if cached:
                return ResearchResult(**cached)
            
            # 2. Search multiple sources
            search_tasks = [
                self._search_google_scholar(query),
                self._search_arxiv(query),
                self._search_semantic_scholar(query)
            ]
            
            results = await asyncio.gather(*search_tasks)
            
            # 3. Combine and deduplicate results
            all_papers = []
            for source_papers in results:
                all_papers.extend(source_papers)
            
            # 4. Process papers concurrently
            tasks = []
            for paper in all_papers:
                if paper["id"] not in self._processed_papers:
                    task = asyncio.create_task(
                        self._process_paper(paper)
                    )
                    tasks.append(task)
            
            findings = []
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, ResearchFinding):
                        findings.append(result)
                        self._processed_papers.add(result.metadata["id"])
            
            # 5. Create research result
            research_result = ResearchResult(
                query=query,
                findings=findings,
                total_findings=len(findings),
                processing_time=(
                    datetime.utcnow() - start_time
                ).total_seconds(),
                metadata={
                    "source": "academic",
                    "total_papers": len(all_papers),
                    "processed_papers": len(findings)
                }
            )
            
            # 6. Cache result
            self._save_cache(cache_key, research_result.dict())
            
            return research_result
        
        except Exception as e:
            logger.error(f"Error in academic research: {e}", exc_info=True)
            raise
    
    async def _search_google_scholar(
        self,
        query: ResearchQuery
    ) -> List[Dict]:
        """Search Google Scholar."""
        try:
            # Run in thread pool due to blocking API
            loop = asyncio.get_event_loop()
            search_query = scholarly.search_pubs(query.query)
            
            results = []
            async with self._download_semaphore:
                for _ in range(query.max_results):
                    try:
                        pub = await loop.run_in_executor(
                            None,
                            lambda: next(search_query)
                        )
                        
                        if self._is_valid_publication(pub):
                            results.append({
                                "id": f"scholar_{pub['scholar_id']}",
                                "title": pub["bib"].get("title", ""),
                                "abstract": pub["bib"].get("abstract", ""),
                                "authors": pub["bib"].get("author", []),
                                "year": pub["bib"].get("pub_year"),
                                "citations": pub.get("num_citations", 0),
                                "url": pub.get("pub_url"),
                                "source": "google_scholar"
                            })
                    
                    except StopIteration:
                        break
            
            return results
        
        except Exception as e:
            logger.error(f"Google Scholar search error: {e}")
            return []
    
    async def _search_arxiv(
        self,
        query: ResearchQuery
    ) -> List[Dict]:
        """Search arXiv."""
        try:
            # Run in thread pool due to blocking API
            loop = asyncio.get_event_loop()
            search = arxiv.Search(
                query=query.query,
                max_results=query.max_results,
                sort_by=arxiv.SortCriterion.Relevance
            )
            
            results = []
            async with self._download_semaphore:
                papers = await loop.run_in_executor(
                    None,
                    lambda: list(search.results())
                )
                
                for paper in papers:
                    if self._is_valid_publication({
                        "year": paper.published.year
                    }):
                        results.append({
                            "id": f"arxiv_{paper.get_short_id()}",
                            "title": paper.title,
                            "abstract": paper.summary,
                            "authors": [
                                str(author) for author in paper.authors
                            ],
                            "year": paper.published.year,
                            "url": paper.pdf_url,
                            "source": "arxiv"
                        })
            
            return results
        
        except Exception as e:
            logger.error(f"arXiv search error: {e}")
            return []
    
    async def _search_semantic_scholar(
        self,
        query: ResearchQuery
    ) -> List[Dict]:
        """Search Semantic Scholar."""
        try:
            config = self.config["apis"]["semantic_scholar"]
            if not config["api_key"]:
                return []
            
            params = {
                "query": query.query,
                "limit": query.max_results,
                "fields": "title,abstract,authors,year,citationCount,url"
            }
            
            headers = {"x-api-key": config["api_key"]}
            
            data = await self._make_request(
                f"{config['endpoint']}/paper/search",
                params=params,
                headers=headers
            )
            
            results = []
            for paper in data.get("data", []):
                if self._is_valid_publication(paper):
                    results.append({
                        "id": f"semantic_{paper['paperId']}",
                        "title": paper.get("title", ""),
                        "abstract": paper.get("abstract", ""),
                        "authors": [
                            author["name"]
                            for author in paper.get("authors", [])
                        ],
                        "year": paper.get("year"),
                        "citations": paper.get("citationCount", 0),
                        "url": paper.get("url"),
                        "source": "semantic_scholar"
                    })
            
            return results
        
        except Exception as e:
            logger.error(f"Semantic Scholar search error: {e}")
            return []
    
    def _is_valid_publication(self, pub: Dict) -> bool:
        """Check if publication meets criteria."""
        try:
            # Check year
            if "year" in pub:
                age = datetime.utcnow().year - int(pub["year"])
                if age > self.config["max_paper_age_years"]:
                    return False
            
            # Check citations
            if "citations" in pub:
                if pub["citations"] < self.config["min_citations"]:
                    return False
            
            # Check fields
            if self.config["fields_of_interest"]:
                fields = set(
                    field.lower()
                    for field in pub.get("fields", [])
                )
                if not fields & self.config["fields_of_interest"]:
                    return False
            
            return True
        
        except Exception:
            return False
    
    async def _process_paper(self, paper: Dict) -> Optional[ResearchFinding]:
        """Process a single paper."""
        try:
            # Extract main content
            content = self._extract_paper_content(paper)
            
            if not content:
                return None
            
            # Calculate confidence
            confidence = self._calculate_confidence(paper)
            
            if confidence < self.config.get("min_confidence", 0.0):
                return None
            
            return ResearchFinding(
                content=content,
                content_type=ContentType.TEXT,
                source="academic",
                source_url=paper.get("url"),
                confidence=confidence,
                metadata={
                    "id": paper["id"],
                    "title": paper["title"],
                    "authors": paper["authors"],
                    "year": paper["year"],
                    "citations": paper.get("citations", 0),
                    "source_db": paper["source"]
                },
                timestamp=datetime.utcnow()
            )
        
        except Exception as e:
            logger.error(f"Error processing paper {paper.get('id')}: {e}")
            return None
    
    def _extract_paper_content(self, paper: Dict) -> Optional[str]:
        """Extract clean content from paper."""
        try:
            content_parts = []
            
            # Add title
            if paper.get("title"):
                content_parts.append(f"Título: {paper['title']}")
            
            # Add authors
            if paper.get("authors"):
                authors = ", ".join(paper["authors"])
                content_parts.append(f"Autores: {authors}")
            
            # Add abstract
            if paper.get("abstract"):
                content_parts.append(f"Resumen: {paper['abstract']}")
            
            # Combine all parts
            if content_parts:
                return "\n\n".join(content_parts)
            
            return None
        
        except Exception as e:
            logger.error(f"Error extracting content: {e}")
            return None
    
    def _calculate_confidence(self, paper: Dict) -> float:
        """Calculate confidence score for paper."""
        score = 0.5  # Base score
        
        try:
            # Adjust based on various factors
            if paper.get("year"):
                age = datetime.utcnow().year - int(paper["year"])
                age_factor = max(
                    0,
                    1 - (age / self.config["max_paper_age_years"])
                )
                score += 0.1 * age_factor
            
            if paper.get("citations"):
                citations = int(paper["citations"])
                citation_factor = min(1, citations / 100)
                score += 0.2 * citation_factor
            
            if paper.get("abstract"):
                score += 0.1
            
            if paper.get("url"):
                score += 0.1
            
            # Add more factors as needed
            
            return min(score, 1.0)
        
        except Exception:
            return score

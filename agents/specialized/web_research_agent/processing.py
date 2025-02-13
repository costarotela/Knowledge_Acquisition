"""
Processing module for Web Research Agent.
"""
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import trafilatura
from newspaper import Article
import nltk

from .schemas import (
    WebSource, ContentFragment, FactClaim,
    ResearchContext, ResearchFindings
)

logger = logging.getLogger(__name__)

class WebResearchProcessor:
    """Processor for web research."""
    
    def __init__(self):
        """Initialize processor."""
        # Download required NLTK data
        try:
            nltk.download('punkt')
            nltk.download('averaged_perceptron_tagger')
            nltk.download('maxent_ne_chunker')
            nltk.download('words')
        except:
            logger.warning("Failed to download NLTK data")
    
    async def extract_content(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Extract content from URL."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}"
                        }
                    
                    html = await response.text()
                    
                    # Use trafilatura for main content extraction
                    content = trafilatura.extract(
                        html,
                        include_comments=False,
                        include_tables=True,
                        no_fallback=False
                    )
                    
                    if not content:
                        return {
                            "success": False,
                            "error": "No content extracted"
                        }
                    
                    # Use newspaper3k for metadata
                    article = Article(url)
                    article.download(input_html=html)
                    article.parse()
                    
                    # Use BeautifulSoup for additional parsing
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    return {
                        "success": True,
                        "content": content,
                        "title": article.title,
                        "authors": article.authors,
                        "publish_date": article.publish_date,
                        "meta_description": article.meta_description,
                        "meta_lang": article.meta_lang,
                        "meta_keywords": article.meta_keywords,
                        "canonical_link": article.canonical_link,
                        "top_image": article.top_image,
                        "meta_data": {
                            meta.get('name', meta.get('property', '')): meta.get('content', '')
                            for meta in soup.find_all('meta')
                            if meta.get('name') or meta.get('property')
                        }
                    }
                    
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def process_content(
        self,
        content: str,
        url: str,
        context: ResearchContext
    ) -> List[ContentFragment]:
        """Process extracted content into fragments."""
        try:
            # Split content into sentences
            sentences = nltk.sent_tokenize(content)
            
            # Group sentences into meaningful fragments
            fragments = []
            current_fragment = []
            current_context = ""
            
            for sentence in sentences:
                current_fragment.append(sentence)
                
                # Create new fragment every 3-5 sentences or at paragraph breaks
                if (len(current_fragment) >= 3 and
                    (len(current_fragment) >= 5 or
                     sentence.strip().endswith('.'))):
                    
                    fragment_text = ' '.join(current_fragment)
                    
                    # Extract named entities for context
                    tokens = nltk.word_tokenize(fragment_text)
                    pos_tags = nltk.pos_tag(tokens)
                    named_entities = nltk.ne_chunk(pos_tags)
                    
                    entities = []
                    for chunk in named_entities:
                        if hasattr(chunk, 'label'):
                            entity = ' '.join(c[0] for c in chunk)
                            entity_type = chunk.label()
                            entities.append(f"{entity_type}: {entity}")
                    
                    current_context = '; '.join(entities) if entities else "No named entities found"
                    
                    # Create fragment
                    fragments.append(ContentFragment(
                        source_url=url,
                        content=fragment_text,
                        context=current_context,
                        relevance_score=self._calculate_relevance(
                            fragment_text,
                            context.query,
                            context.objective
                        ),
                        extracted_entities=entities
                    ))
                    
                    current_fragment = []
            
            # Add any remaining sentences
            if current_fragment:
                fragment_text = ' '.join(current_fragment)
                fragments.append(ContentFragment(
                    source_url=url,
                    content=fragment_text,
                    context=current_context,
                    relevance_score=self._calculate_relevance(
                        fragment_text,
                        context.query,
                        context.objective
                    )
                ))
            
            return fragments
            
        except Exception as e:
            logger.error(f"Error processing content: {str(e)}")
            return []
    
    def _calculate_relevance(
        self,
        text: str,
        query: str,
        objective: str
    ) -> float:
        """Calculate relevance score for text."""
        try:
            # Simple relevance calculation based on term overlap
            text_terms = set(nltk.word_tokenize(text.lower()))
            query_terms = set(nltk.word_tokenize(query.lower()))
            objective_terms = set(nltk.word_tokenize(objective.lower()))
            
            query_overlap = len(text_terms & query_terms) / len(query_terms)
            objective_overlap = len(text_terms & objective_terms) / len(objective_terms)
            
            # Weight query match higher than objective match
            relevance = (0.7 * query_overlap) + (0.3 * objective_overlap)
            
            return min(max(relevance, 0.0), 1.0)
            
        except:
            return 0.5
    
    async def analyze_source_quality(
        self,
        url: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze quality and credibility of source."""
        try:
            from urllib.parse import urlparse
            
            # Parse domain
            parsed = urlparse(url)
            domain = parsed.netloc
            
            # Quality indicators
            indicators = {
                # Domain-based indicators
                "known_domain": self._is_known_domain(domain),
                "secure_connection": parsed.scheme == "https",
                
                # Metadata-based indicators
                "has_authors": bool(metadata.get("authors")),
                "has_date": bool(metadata.get("publish_date")),
                "has_meta_description": bool(metadata.get("meta_description")),
                "has_canonical": bool(metadata.get("canonical_link")),
                
                # Content-based indicators
                "content_length": len(metadata.get("content", "")),
                "has_structured_data": bool(metadata.get("meta_data")),
            }
            
            # Calculate trust score
            weights = {
                "known_domain": 0.3,
                "secure_connection": 0.1,
                "has_authors": 0.15,
                "has_date": 0.1,
                "has_meta_description": 0.05,
                "has_canonical": 0.05,
                "content_length": 0.15,
                "has_structured_data": 0.1
            }
            
            trust_score = sum(
                weights[key] * (1 if value else 0)
                for key, value in indicators.items()
                if key in weights
            )
            
            # Adjust for content length
            if indicators["content_length"] < 500:
                trust_score *= 0.8
            elif indicators["content_length"] > 5000:
                trust_score *= 1.2
                
            trust_score = min(max(trust_score, 0.1), 1.0)
            
            return {
                "trust_score": trust_score,
                "indicators": indicators,
                "domain": domain
            }
            
        except Exception as e:
            logger.error(f"Error analyzing source quality: {str(e)}")
            return {
                "trust_score": 0.5,
                "error": str(e)
            }
    
    def _is_known_domain(self, domain: str) -> bool:
        """Check if domain is known/reputable."""
        # TODO: Implement more sophisticated domain reputation checking
        known_domains = {
            "github.com",
            "wikipedia.org",
            "medium.com",
            "stackoverflow.com",
            "docs.python.org",
            "arxiv.org",
            "scholar.google.com",
            "ieee.org",
            "acm.org",
            "nature.com",
            "science.org",
            "springer.com",
            "sciencedirect.com"
        }
        
        return any(
            domain.endswith(known)
            for known in known_domains
        )

"""
Specialized agent for web research and knowledge extraction.
"""
from typing import Dict, Any, List, Optional
import logging
import aiohttp
import asyncio
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import trafilatura
from readability import Document
import json

from ..base_agents.knowledge_agent import KnowledgeAgent
from core_system.agent_orchestrator.base import Task, TaskResult

logger = logging.getLogger(__name__)

class WebResearchAgent(KnowledgeAgent):
    """Agent specialized in web research and content extraction."""
    
    def __init__(self, *args, **kwargs):
        """Initialize web research agent."""
        super().__init__(*args, **kwargs)
        
        # Web research settings
        self.max_depth = self.config.get("max_depth", 2)
        self.max_pages = self.config.get("max_pages", 10)
        self.follow_links = self.config.get("follow_links", True)
        self.excluded_domains = self.config.get("excluded_domains", [])
        self.request_delay = self.config.get("request_delay", 1.0)
        
        # Initialize session
        self.session = None
    
    async def initialize(self) -> bool:
        """Initialize agent resources."""
        try:
            # Create aiohttp session
            self.session = aiohttp.ClientSession(
                headers={"User-Agent": "Knowledge Acquisition Research Bot"}
            )
            return await super().initialize()
        except Exception as e:
            logger.error(f"Error initializing web research agent: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup agent resources."""
        if self.session:
            await self.session.close()
        await super().cleanup()
    
    async def _process_extraction(self, task: Task) -> TaskResult:
        """Process web content extraction."""
        try:
            url = task.input_data["source_url"]
            extraction_type = task.input_data["extraction_type"]
            
            # Extract content based on type
            if extraction_type == "single_page":
                knowledge = await self._extract_single_page(url)
            elif extraction_type == "recursive":
                knowledge = await self._extract_recursive(url)
            elif extraction_type == "focused":
                knowledge = await self._extract_focused(
                    url,
                    task.input_data.get("focus_keywords", [])
                )
            else:
                return TaskResult(
                    success=False,
                    error=f"Unsupported extraction type: {extraction_type}"
                )
            
            if not knowledge:
                return TaskResult(
                    success=False,
                    error="Failed to extract knowledge"
                )
            
            # Store knowledge
            success = await self._store_knowledge(
                knowledge["items"],
                knowledge["confidence_scores"]
            )
            
            if not success:
                return TaskResult(
                    success=False,
                    error="Failed to store knowledge"
                )
            
            return TaskResult(
                success=True,
                data=knowledge,
                metrics={
                    "pages_processed": knowledge["metadata"]["pages_processed"],
                    "total_content_length": knowledge["metadata"]["total_content_length"],
                    "avg_confidence": sum(knowledge["confidence_scores"].values()) / len(knowledge["confidence_scores"])
                }
            )
            
        except Exception as e:
            logger.error(f"Error in web extraction: {e}")
            return TaskResult(
                success=False,
                error=str(e)
            )
    
    async def _process_validation(self, task: Task) -> TaskResult:
        """Validate extracted web knowledge."""
        try:
            knowledge_id = task.input_data["knowledge_id"]
            validation_type = task.input_data["validation_type"]
            
            # Get knowledge to validate
            knowledge = await self.knowledge_store.get_knowledge(knowledge_id)
            if not knowledge:
                return TaskResult(
                    success=False,
                    error=f"Knowledge not found: {knowledge_id}"
                )
            
            # Perform validation
            if validation_type == "source_reliability":
                validation = await self._validate_source_reliability(knowledge)
            elif validation_type == "content_quality":
                validation = await self._validate_content_quality(knowledge)
            elif validation_type == "cross_reference":
                validation = await self._validate_cross_reference(knowledge)
            else:
                return TaskResult(
                    success=False,
                    error=f"Unsupported validation type: {validation_type}"
                )
            
            return TaskResult(
                success=True,
                data=validation,
                metrics={
                    "validation_score": validation["score"],
                    "issues_found": len(validation["issues"])
                }
            )
            
        except Exception as e:
            logger.error(f"Error in web validation: {e}")
            return TaskResult(
                success=False,
                error=str(e)
            )
    
    async def _extract_single_page(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract knowledge from a single webpage."""
        try:
            # Fetch and extract content
            async with self.session.get(url) as response:
                if response.status != 200:
                    return None
                
                html = await response.text()
            
            # Extract main content
            doc = Document(html)
            main_content = doc.summary()
            
            # Extract with trafilatura for better cleaning
            extracted = trafilatura.extract(
                html,
                include_comments=False,
                include_tables=True,
                output_format="json"
            )
            
            if not extracted:
                return None
            
            extracted_data = json.loads(extracted)
            
            # Create knowledge item
            item = {
                "type": "web_page",
                "url": url,
                "title": doc.title(),
                "main_content": main_content,
                "cleaned_text": extracted_data.get("text", ""),
                "metadata": {
                    "author": extracted_data.get("author"),
                    "date": extracted_data.get("date"),
                    "categories": extracted_data.get("categories", []),
                    "tags": extracted_data.get("tags", [])
                }
            }
            
            # Calculate confidence score
            confidence = self._calculate_content_confidence(item)
            
            return {
                "items": [item],
                "confidence_scores": {"item_0": confidence},
                "metadata": {
                    "pages_processed": 1,
                    "total_content_length": len(item["cleaned_text"])
                }
            }
            
        except Exception as e:
            logger.error(f"Error extracting single page: {e}")
            return None
    
    async def _extract_recursive(self, start_url: str) -> Optional[Dict[str, Any]]:
        """Extract knowledge recursively following links."""
        try:
            visited = set()
            queue = [(start_url, 0)]  # (url, depth)
            knowledge_items = []
            confidence_scores = {}
            total_length = 0
            
            while queue and len(visited) < self.max_pages:
                url, depth = queue.pop(0)
                
                if url in visited or depth > self.max_depth:
                    continue
                
                # Extract page content
                knowledge = await self._extract_single_page(url)
                if not knowledge:
                    continue
                
                # Add to results
                item_index = len(knowledge_items)
                knowledge_items.extend(knowledge["items"])
                confidence_scores.update({
                    f"item_{item_index + i}": score
                    for i, score in enumerate(knowledge["confidence_scores"].values())
                })
                
                total_length += knowledge["metadata"]["total_content_length"]
                visited.add(url)
                
                # Add links to queue if needed
                if self.follow_links and depth < self.max_depth:
                    await self._add_links_to_queue(url, depth + 1, queue, visited)
                
                # Respect rate limiting
                await asyncio.sleep(self.request_delay)
            
            return {
                "items": knowledge_items,
                "confidence_scores": confidence_scores,
                "metadata": {
                    "pages_processed": len(visited),
                    "total_content_length": total_length,
                    "max_depth_reached": max(d for _, d in queue) if queue else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error in recursive extraction: {e}")
            return None
    
    async def _extract_focused(
        self,
        start_url: str,
        focus_keywords: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Extract knowledge with focus on specific keywords."""
        try:
            # Modify recursive extraction to focus on relevant pages
            visited = set()
            queue = [(start_url, 0, 1.0)]  # (url, depth, relevance)
            knowledge_items = []
            confidence_scores = {}
            total_length = 0
            
            while queue and len(visited) < self.max_pages:
                # Sort queue by relevance
                queue.sort(key=lambda x: x[2], reverse=True)
                url, depth, relevance = queue.pop(0)
                
                if url in visited or depth > self.max_depth:
                    continue
                
                # Extract page content
                knowledge = await self._extract_single_page(url)
                if not knowledge:
                    continue
                
                # Calculate relevance score
                page_relevance = self._calculate_relevance(
                    knowledge["items"][0]["cleaned_text"],
                    focus_keywords
                )
                
                # Only keep relevant content
                if page_relevance >= 0.3:
                    item_index = len(knowledge_items)
                    knowledge_items.extend(knowledge["items"])
                    confidence_scores.update({
                        f"item_{item_index + i}": score * page_relevance
                        for i, score in enumerate(knowledge["confidence_scores"].values())
                    })
                    
                    total_length += knowledge["metadata"]["total_content_length"]
                
                visited.add(url)
                
                # Add relevant links to queue
                if self.follow_links and depth < self.max_depth:
                    await self._add_focused_links(
                        url,
                        depth + 1,
                        focus_keywords,
                        queue,
                        visited
                    )
                
                await asyncio.sleep(self.request_delay)
            
            return {
                "items": knowledge_items,
                "confidence_scores": confidence_scores,
                "metadata": {
                    "pages_processed": len(visited),
                    "total_content_length": total_length,
                    "focus_keywords": focus_keywords
                }
            }
            
        except Exception as e:
            logger.error(f"Error in focused extraction: {e}")
            return None
    
    async def _add_links_to_queue(
        self,
        url: str,
        depth: int,
        queue: List[tuple],
        visited: set
    ):
        """Add links from page to queue."""
        try:
            async with self.session.get(url) as response:
                html = await response.text()
            
            soup = BeautifulSoup(html, "html.parser")
            base_domain = urlparse(url).netloc
            
            for link in soup.find_all("a", href=True):
                href = link["href"]
                absolute_url = urljoin(url, href)
                
                # Filter URLs
                if self._should_follow_link(absolute_url, base_domain):
                    queue.append((absolute_url, depth))
                    
        except Exception as e:
            logger.error(f"Error adding links to queue: {e}")
    
    async def _add_focused_links(
        self,
        url: str,
        depth: int,
        focus_keywords: List[str],
        queue: List[tuple],
        visited: set
    ):
        """Add relevant links to queue based on keywords."""
        try:
            async with self.session.get(url) as response:
                html = await response.text()
            
            soup = BeautifulSoup(html, "html.parser")
            base_domain = urlparse(url).netloc
            
            for link in soup.find_all("a", href=True):
                href = link["href"]
                absolute_url = urljoin(url, href)
                
                if self._should_follow_link(absolute_url, base_domain):
                    # Calculate link relevance
                    link_text = link.get_text()
                    relevance = self._calculate_relevance(link_text, focus_keywords)
                    
                    if relevance > 0:
                        queue.append((absolute_url, depth, relevance))
                    
        except Exception as e:
            logger.error(f"Error adding focused links: {e}")
    
    def _should_follow_link(self, url: str, base_domain: str) -> bool:
        """Check if link should be followed."""
        try:
            parsed = urlparse(url)
            
            # Basic filters
            if not parsed.scheme in ["http", "https"]:
                return False
            
            # Check domain
            domain = parsed.netloc
            if not domain:
                return False
            
            # Stay on same domain or allowed domains
            if domain != base_domain and domain in self.excluded_domains:
                return False
            
            # Avoid common non-content paths
            excluded_paths = [
                "/login", "/signup", "/register",
                "/cart", "/checkout", "/search"
            ]
            if any(path in parsed.path.lower() for path in excluded_paths):
                return False
            
            return True
            
        except Exception:
            return False
    
    def _calculate_content_confidence(self, item: Dict[str, Any]) -> float:
        """Calculate confidence score for content."""
        score = 1.0
        
        # Check content length
        text_length = len(item["cleaned_text"])
        if text_length < 100:
            score *= 0.5
        elif text_length < 500:
            score *= 0.8
        
        # Check metadata presence
        if not item["metadata"]["author"]:
            score *= 0.9
        if not item["metadata"]["date"]:
            score *= 0.9
        
        # Check content quality
        if len(item["cleaned_text"].split()) < 50:
            score *= 0.7
        
        return max(0.1, min(1.0, score))
    
    def _calculate_relevance(self, text: str, keywords: List[str]) -> float:
        """Calculate relevance score based on keywords."""
        if not text or not keywords:
            return 0.0
        
        text_lower = text.lower()
        word_count = len(text_lower.split())
        
        if word_count == 0:
            return 0.0
        
        # Count keyword occurrences
        keyword_count = sum(
            text_lower.count(keyword.lower())
            for keyword in keywords
        )
        
        # Calculate density
        density = keyword_count / word_count
        
        return min(1.0, density * 10)
    
    async def _validate_source_reliability(
        self,
        knowledge: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate source reliability."""
        issues = []
        score = 1.0
        
        for item in knowledge.get("items", []):
            url = item.get("url")
            if not url:
                continue
            
            # Check domain reputation
            domain = urlparse(url).netloc
            if domain in self.excluded_domains:
                issues.append(f"Excluded domain: {domain}")
                score *= 0.5
            
            # Check HTTPS
            if not url.startswith("https"):
                issues.append(f"Non-HTTPS URL: {url}")
                score *= 0.9
            
            # Check metadata
            if not item["metadata"].get("author"):
                issues.append(f"Missing author for {url}")
                score *= 0.9
            
            if not item["metadata"].get("date"):
                issues.append(f"Missing date for {url}")
                score *= 0.9
        
        return {
            "score": score,
            "issues": issues,
            "validation_type": "source_reliability"
        }
    
    async def _validate_content_quality(
        self,
        knowledge: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate content quality."""
        issues = []
        score = 1.0
        
        for item in knowledge.get("items", []):
            text = item.get("cleaned_text", "")
            
            # Check length
            if len(text) < 100:
                issues.append("Content too short")
                score *= 0.7
            
            # Check formatting
            if text.isupper():
                issues.append("Text is all uppercase")
                score *= 0.8
            
            # Check sentence structure
            sentences = text.split(". ")
            if len(sentences) < 3:
                issues.append("Too few sentences")
                score *= 0.9
            
            # Check for common spam patterns
            spam_patterns = ["[click here]", "buy now", "limited time"]
            if any(pattern in text.lower() for pattern in spam_patterns):
                issues.append("Contains spam patterns")
                score *= 0.6
        
        return {
            "score": score,
            "issues": issues,
            "validation_type": "content_quality"
        }
    
    async def _validate_cross_reference(
        self,
        knowledge: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate through cross-referencing."""
        issues = []
        score = 1.0
        
        # Get related knowledge items
        related = await self.knowledge_store.find_similar(knowledge)
        
        if not related:
            return {
                "score": 0.5,
                "issues": ["No related items found for cross-reference"],
                "validation_type": "cross_reference"
            }
        
        for item in knowledge.get("items", []):
            # Compare with related items
            for related_item in related:
                similarity = self._calculate_similarity(
                    item.get("cleaned_text", ""),
                    related_item.get("cleaned_text", "")
                )
                
                if similarity < 0.3:
                    issues.append("Low similarity with related content")
                    score *= 0.8
                elif similarity > 0.9:
                    issues.append("Possible duplicate content")
                    score *= 0.7
        
        return {
            "score": score,
            "issues": issues,
            "validation_type": "cross_reference"
        }
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity score."""
        # Simple word overlap similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union)

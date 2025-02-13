"""
Document processor using Unstructured for parsing various document formats.
"""
from typing import List, Dict, Any, Optional
import logging
from pathlib import Path
from unstructured.partition.auto import partition
from unstructured.documents.elements import (
    Title, NarrativeText, ListItem, Table, Image
)

from ..base import BaseProcessor, DocumentContent, ProcessingResult

logger = logging.getLogger(__name__)

class UnstructuredProcessor(BaseProcessor):
    """Document processor using Unstructured for parsing."""
    
    SUPPORTED_FORMATS = {
        '.txt', '.pdf', '.docx', '.doc',
        '.pptx', '.ppt', '.xlsx', '.xls',
        '.html', '.htm', '.md', '.rst'
    }
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize Unstructured processor."""
        self.config = config or {}
        self.chunk_size = self.config.get("chunk_size", 1000)
        self.chunk_overlap = self.config.get("chunk_overlap", 200)
    
    async def validate_source(self, source: str) -> bool:
        """Validate if the source is a supported document."""
        try:
            extension = Path(source).suffix.lower()
            return extension in self.SUPPORTED_FORMATS
        except Exception:
            return False
    
    async def extract_content(self, source: str) -> DocumentContent:
        """Extract content from document source."""
        try:
            # Get basic file info
            file_path = Path(source)
            
            return DocumentContent(
                source_url=source,
                source_type="document",
                text="",  # Will be filled during processing
                format=file_path.suffix[1:],  # Remove leading dot
                metadata={
                    "filename": file_path.name,
                    "size": file_path.stat().st_size
                }
            )
        except Exception as e:
            logger.error(f"Error extracting content: {e}")
            raise
    
    def _chunk_text(self, text: str) -> List[str]:
        """Split text into chunks with overlap."""
        chunks = []
        start = 0
        
        while start < len(text):
            # Get chunk with potential overlap
            end = start + self.chunk_size
            
            # If not at the end, try to break at a sentence
            if end < len(text):
                # Look for sentence endings within overlap region
                overlap_start = end - self.chunk_overlap
                overlap_text = text[overlap_start:end]
                
                # Find last sentence ending in overlap region
                for sep in [". ", "! ", "? ", "\n\n"]:
                    last_sep = overlap_text.rfind(sep)
                    if last_sep != -1:
                        end = overlap_start + last_sep + len(sep)
                        break
            
            chunks.append(text[start:end].strip())
            start = end - self.chunk_overlap
        
        return chunks
    
    async def process_content(self, content: DocumentContent) -> ProcessingResult:
        """Process the document content."""
        try:
            # Parse document with Unstructured
            elements = partition(content.source_url)
            
            # Process different element types
            sections = []
            tables = []
            figures = []
            full_text = []
            
            current_section = {
                "title": "",
                "content": [],
                "type": "text"
            }
            
            for element in elements:
                if isinstance(element, Title):
                    # Save previous section if it exists
                    if current_section["content"]:
                        sections.append(current_section)
                        current_section = {
                            "title": str(element),
                            "content": [],
                            "type": "text"
                        }
                    else:
                        current_section["title"] = str(element)
                
                elif isinstance(element, NarrativeText):
                    text = str(element)
                    current_section["content"].append(text)
                    full_text.append(text)
                
                elif isinstance(element, ListItem):
                    current_section["content"].append(f"- {str(element)}")
                    full_text.append(str(element))
                
                elif isinstance(element, Table):
                    tables.append({
                        "position": len(sections),
                        "content": str(element)
                    })
                
                elif isinstance(element, Image):
                    figures.append({
                        "position": len(sections),
                        "caption": element.caption if hasattr(element, "caption") else None
                    })
            
            # Add last section
            if current_section["content"]:
                sections.append(current_section)
            
            # Update content
            content.text = "\n\n".join(full_text)
            content.sections = sections
            content.tables = tables
            content.figures = figures
            
            # Calculate simple confidence scores
            confidence_scores = {
                "structure": min(1.0, len(sections) / 5 * 0.4 +
                               len(tables) / 3 * 0.3 +
                               len(figures) / 2 * 0.3),
                "content": min(1.0, len(content.text) / 1000 * 0.6 +
                             (1 if content.text.strip() else 0) * 0.4)
            }
            confidence_scores["overall"] = sum(confidence_scores.values()) / len(confidence_scores)
            
            # Create chunks for better processing
            chunks = self._chunk_text(content.text)
            
            return ProcessingResult(
                content_type="document",
                raw_content=content,
                extracted_knowledge=[{
                    "chunks": chunks,
                    "sections": sections,
                    "tables": tables,
                    "figures": figures,
                    "metadata": content.metadata
                }],
                confidence_scores=confidence_scores,
                processing_metadata={
                    "processor": "unstructured",
                    "chunk_size": self.chunk_size,
                    "chunk_overlap": self.chunk_overlap,
                    "total_chunks": len(chunks),
                    "document_format": content.format
                }
            )
            
        except Exception as e:
            logger.error(f"Error in content processing: {e}")
            raise

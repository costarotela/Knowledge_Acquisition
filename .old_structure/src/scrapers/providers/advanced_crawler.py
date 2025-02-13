from typing import Any, Dict, List, Optional
import asyncio
from bs4 import BeautifulSoup
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pydantic import BaseModel
from datetime import datetime
from ..base_scraper import BaseScraper, ScrapedData, ScrapingConfig

class CrawledChunk(BaseModel):
    """Modelo para un chunk de contenido procesado."""
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None

class CrawledPage(ScrapedData):
    """Modelo para una página web procesada."""
    title: str
    summary: str
    chunks: List[CrawledChunk]
    parent_url: Optional[str] = None
    depth: int = 0

class AdvancedCrawler(BaseScraper):
    """Implementación avanzada de crawler con chunking inteligente."""
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        super().__init__(config)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=5000,
            chunk_overlap=500,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
    
    def _extract_text_with_context(self, soup: BeautifulSoup) -> str:
        """Extrae texto preservando bloques de código y estructura."""
        # Preservar bloques de código
        for pre in soup.find_all('pre'):
            pre.string = f"\n```\n{pre.get_text()}\n```\n"
        
        # Preservar enlaces con texto
        for a in soup.find_all('a'):
            if a.string:
                a.string = f"[{a.string}]({a.get('href', '')})"
        
        # Extraer texto manteniendo estructura
        lines = []
        for elem in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'pre']):
            if elem.name.startswith('h'):
                level = int(elem.name[1])
                lines.append(f"{'#' * level} {elem.get_text().strip()}\n")
            elif elem.name == 'li':
                lines.append(f"- {elem.get_text().strip()}\n")
            else:
                lines.append(f"{elem.get_text().strip()}\n\n")
        
        return "".join(lines)
    
    def _chunk_content(self, content: str) -> List[CrawledChunk]:
        """Divide el contenido en chunks inteligentes."""
        chunks = self.text_splitter.split_text(content)
        return [
            CrawledChunk(
                content=chunk,
                metadata={
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "timestamp": datetime.now().isoformat()
                }
            )
            for i, chunk in enumerate(chunks)
        ]
    
    async def _extract_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extrae metadatos de la página."""
        metadata = {}
        
        # Extraer metadatos de las etiquetas meta
        for meta in soup.find_all('meta'):
            name = meta.get('name') or meta.get('property')
            if name:
                metadata[name] = meta.get('content')
        
        # Extraer información de OpenGraph
        for meta in soup.find_all('meta', property=lambda x: x and x.startswith('og:')):
            metadata[meta['property']] = meta.get('content')
        
        return metadata
    
    async def scrape(self, url: str) -> CrawledPage:
        """Realiza el crawling de una página con procesamiento avanzado."""
        try:
            async with self._session() as session:
                async with session.get(
                    url,
                    headers=self.config.headers,
                    proxy=self.config.proxy,
                    ssl=self.config.verify_ssl,
                    timeout=self.config.timeout
                ) as response:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Extraer título y metadatos
                    title = soup.title.string if soup.title else ""
                    metadata = await self._extract_metadata(soup)
                    
                    # Procesar contenido
                    content = self._extract_text_with_context(soup)
                    chunks = self._chunk_content(content)
                    
                    # Generar resumen (esto podría mejorarse usando LLM)
                    summary = metadata.get('description', content[:200] + "...")
                    
                    return CrawledPage(
                        url=url,
                        timestamp=datetime.now().isoformat(),
                        title=title,
                        summary=summary,
                        chunks=chunks,
                        content=content,
                        metadata=metadata
                    )
        except Exception as e:
            raise Exception(f"Error crawling page: {str(e)}")
    
    async def scrape_multiple(self, urls: List[str]) -> List[CrawledPage]:
        """Realiza el crawling de múltiples páginas."""
        tasks = []
        async with self._session() as session:
            for url in urls:
                if await self.validate_url(url):
                    tasks.append(self.scrape(url))
                await asyncio.sleep(self.config.rate_limit)
            
            return await asyncio.gather(*tasks)
    
    async def validate_url(self, url: str) -> bool:
        """Valida si una URL es accesible y contiene contenido HTML."""
        try:
            async with self._session() as session:
                async with session.get(
                    url,
                    headers=self.config.headers,
                    proxy=self.config.proxy,
                    ssl=self.config.verify_ssl,
                    timeout=self.config.timeout
                ) as response:
                    return (
                        response.status == 200 and
                        'text/html' in response.headers.get('content-type', '').lower()
                    )
        except:
            return False
    
    async def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Nota: Esta función debería implementarse con un motor de búsqueda
        o un sistema de embeddings para búsqueda semántica.
        """
        raise NotImplementedError(
            "Search functionality requires integration with a search engine or embedding system"
        )
    
    async def extract_metadata(self, content: Any) -> Dict[str, Any]:
        """Extrae metadatos del contenido."""
        if not isinstance(content, str):
            raise ValueError("Invalid content format")
            
        soup = BeautifulSoup(content, 'html.parser')
        return await self._extract_metadata(soup)

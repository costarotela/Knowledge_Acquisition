"""
Procesador de contenido web (Wikipedia, GitHub, scraping general).
"""
from typing import Dict, Any, Optional
import logging
import aiohttp
from bs4 import BeautifulSoup
import wikipediaapi
from github import Github
from .base_processor import BaseProcessor

logger = logging.getLogger(__name__)

class WebProcessor(BaseProcessor):
    """Procesa contenido de diferentes fuentes web."""
    
    def __init__(self, config: Dict[str, Any]):
        """Inicializa el procesador web."""
        super().__init__(config)
        self.wiki = wikipediaapi.Wikipedia(
            language='es',
            extract_format=wikipediaapi.ExtractFormat.WIKI
        )
        self.github = Github(config.get('github_token'))
        self.session = aiohttp.ClientSession()
    
    async def validate_source(self, source: str) -> bool:
        """Valida si la URL es compatible."""
        return any([
            'wikipedia.org' in source,
            'github.com' in source,
            source.startswith('http://'),
            source.startswith('https://')
        ])
    
    async def extract_content(self, source: str) -> Dict[str, Any]:
        """Extrae contenido de la fuente web."""
        try:
            if 'wikipedia.org' in source:
                return await self._process_wikipedia(source)
            elif 'github.com' in source:
                return await self._process_github(source)
            else:
                return await self._process_webpage(source)
                
        except Exception as e:
            logger.error(f"Error procesando fuente web {source}: {str(e)}")
            raise
    
    async def process_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Procesa el contenido extraído."""
        try:
            # TODO: Implementar procesamiento específico según tipo de contenido
            return {
                "type": content["type"],
                "text": content["text"],
                "metadata": content["metadata"],
                "structured_data": content.get("structured_data", {})
            }
        except Exception as e:
            logger.error(f"Error procesando contenido: {str(e)}")
            raise
    
    async def _process_wikipedia(self, url: str) -> Dict[str, Any]:
        """Procesa artículo de Wikipedia."""
        try:
            # Extraer título del artículo de la URL
            title = url.split('/')[-1]
            page = self.wiki.page(title)
            
            if not page.exists():
                raise ValueError(f"Artículo no encontrado: {title}")
            
            return {
                "type": "wikipedia",
                "text": page.text,
                "metadata": {
                    "title": page.title,
                    "url": page.fullurl,
                    "summary": page.summary
                },
                "structured_data": {
                    "references": page.references,
                    "categories": page.categories,
                    "links": page.links
                }
            }
            
        except Exception as e:
            logger.error(f"Error procesando Wikipedia: {str(e)}")
            raise
    
    async def _process_github(self, url: str) -> Dict[str, Any]:
        """Procesa repositorio o archivo de GitHub."""
        try:
            # Extraer owner/repo de la URL
            parts = url.split('github.com/')[-1].split('/')
            owner, repo = parts[0], parts[1]
            
            repository = self.github.get_repo(f"{owner}/{repo}")
            
            return {
                "type": "github",
                "text": repository.description or "",
                "metadata": {
                    "name": repository.name,
                    "owner": repository.owner.login,
                    "stars": repository.stargazers_count,
                    "forks": repository.forks_count
                },
                "structured_data": {
                    "topics": repository.get_topics(),
                    "languages": repository.get_languages(),
                    "readme": repository.get_readme().decoded_content.decode()
                }
            }
            
        except Exception as e:
            logger.error(f"Error procesando GitHub: {str(e)}")
            raise
    
    async def _process_webpage(self, url: str) -> Dict[str, Any]:
        """Procesa página web general."""
        try:
            async with self.session.get(url) as response:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Eliminar scripts y estilos
                for script in soup(["script", "style"]):
                    script.decompose()
                
                text = soup.get_text()
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = ' '.join(chunk for chunk in chunks if chunk)
                
                return {
                    "type": "webpage",
                    "text": text,
                    "metadata": {
                        "title": soup.title.string if soup.title else "",
                        "url": url
                    },
                    "structured_data": {
                        "links": [a.get('href') for a in soup.find_all('a', href=True)],
                        "images": [img.get('src') for img in soup.find_all('img', src=True)]
                    }
                }
                
        except Exception as e:
            logger.error(f"Error procesando página web: {str(e)}")
            raise
    
    async def close(self):
        """Cierra la sesión HTTP."""
        await self.session.close()

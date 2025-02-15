"""
Browser Manager para extracción de datos usando browser-use.

Este módulo implementa un gestor avanzado de navegación web que:
1. Usa browser-use para automatización inteligente
2. Maneja extracción dinámica de datos
3. Procesa interacciones complejas
4. Gestiona caché eficientemente
5. Proporciona feedback detallado
"""

from typing import Dict, List, Optional, Union, Any, AsyncContextManager
import asyncio
import logging
from datetime import datetime
import json
from pathlib import Path
import hashlib
import os
from dataclasses import dataclass
from enum import Enum
from contextlib import asynccontextmanager

try:
    from browser_use import Agent, Browser, BrowserConfig, BrowserContextConfig
    from browser_use.browser.browser import BrowserContext
    from langchain_openai import ChatOpenAI
except ImportError as e:
    print(f"Error al importar módulos: {e}")
    raise ImportError(
        "browser-use no está instalado. Instálalo con: pip install browser-use"
    )

class InteractionType(Enum):
    """Tipos de interacción soportados."""
    CLICK = "click"
    TYPE = "type"
    SELECT = "select"
    SCROLL = "scroll"
    WAIT = "wait"
    CUSTOM = "custom"

@dataclass
class ExtractionResult:
    """Resultado de extracción de datos."""
    success: bool
    data: Dict[str, Any]
    errors: List[str]
    timestamp: datetime = datetime.now()

class BrowserManager:
    """Gestor avanzado de navegación web usando browser-use.
    
    Características:
    1. Navegación automatizada inteligente
    2. Extracción dinámica de datos
    3. Manejo de interacciones complejas
    4. Validación y limpieza de datos
    5. Gestión eficiente de caché
    6. Feedback detallado de operaciones
    """
    
    def __init__(
            self,
            llm_model: str = "gpt-4",
            cache_dir: Optional[str] = None,
            cache_ttl: int = 3600,  # 1 hora
            max_retries: int = 3,
            timeout: int = 30,
            headless: bool = True
        ):
        """Inicializar BrowserManager."""
        # Configuración de browser-use
        browser_config = BrowserConfig(
            headless=headless
        )
        
        self.browser = Browser(config=browser_config)
        self.agent = Agent(
            task="Initialize browser agent for web automation and data extraction",
            llm=ChatOpenAI(model=llm_model),
            browser=self.browser
        )
        
        self.cache_dir = Path(cache_dir or "data/browser_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl = cache_ttl
        self.max_retries = max_retries
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)

    @asynccontextmanager
    async def browser_context(self) -> AsyncContextManager[BrowserContext]:
        """Context manager para manejar el contexto del navegador."""
        context = await self.browser.new_context()
        try:
            yield context
        finally:
            await context.close()

    async def extract_dynamic_content(
            self,
            url: str,
            selectors: Dict[str, str],
            scroll: bool = True,
            wait_for: Optional[str] = None,
            data_patterns: Optional[Dict[str, str]] = None,
            use_cache: bool = True
        ) -> ExtractionResult:
        """Extraer contenido dinámico de una página."""
        if use_cache:
            cached = self._get_from_cache(url)
            if cached:
                return ExtractionResult(True, cached, [])

        errors = []
        try:
            async with self.browser_context() as context:
                page = await context.new_page()
                await page.goto(url)

                if wait_for:
                    try:
                        await page.wait_for_selector(wait_for, timeout=self.timeout * 1000)
                    except Exception as e:
                        errors.append(f"Error esperando elemento: {str(e)}")

                if scroll:
                    try:
                        await self.agent.scroll_to_bottom(page)
                    except Exception as e:
                        errors.append(f"Error en scroll: {str(e)}")

                data = {}
                for key, selector in selectors.items():
                    try:
                        value = await self.agent.extract_content(
                            page=page,
                            selector=selector,
                            use_llm=True
                        )

                        if data_patterns and key in data_patterns:
                            value = self._clean_data(value, data_patterns[key])

                        data[key] = value

                    except Exception as e:
                        errors.append(f"Error extrayendo {key}: {str(e)}")
                        data[key] = None

                if use_cache and data:
                    self._save_to_cache(url, data)

                return ExtractionResult(
                    success=bool(data),
                    data=data,
                    errors=errors
                )

        except Exception as e:
            errors.append(f"Error general: {str(e)}")
            return ExtractionResult(
                success=False,
                data={},
                errors=errors
            )

    async def interact_with_page(
            self,
            url: str,
            interactions: List[Dict],
            validation: Optional[Dict] = None,
            max_retries: Optional[int] = None
        ) -> bool:
        """Realizar interacciones complejas en una página."""
        retries = max_retries or self.max_retries

        for attempt in range(retries):
            try:
                async with self.browser_context() as context:
                    page = await context.new_page()
                    await page.goto(url)

                    for interaction in interactions:
                        action = InteractionType(interaction["action"])
                        target = interaction.get("target")
                        selector = interaction.get("selector")

                        try:
                            await page.wait_for_selector(
                                selector,
                                timeout=self.timeout * 1000
                            )
                        except Exception as e:
                            self.logger.warning(f"Elemento no disponible: {str(e)}")
                            continue

                        if action == InteractionType.CLICK:
                            await page.click(selector)
                        elif action == InteractionType.TYPE:
                            await page.type(selector, target)
                        elif action == InteractionType.SELECT:
                            await page.select_option(selector, target)
                        elif action == InteractionType.SCROLL:
                            await self.agent.scroll_to_bottom(page)
                        elif action == InteractionType.WAIT:
                            await asyncio.sleep(float(target))
                        elif action == InteractionType.CUSTOM:
                            await self.agent.execute_action(
                                page=page,
                                action=interaction["action"],
                                target=target
                            )

                        if validation and validation.get("after_step") == interaction:
                            if not await self._validate_step(validation, page):
                                continue

                    return True

            except Exception as e:
                self.logger.error(f"Error en intento {attempt + 1}: {str(e)}")
                if attempt == retries - 1:
                    return False

                await asyncio.sleep(1)  # Esperar antes de reintentar

        return False

    async def extract_data(
            self,
            url: str,
            selectors: Dict[str, str],
            data_patterns: Optional[Dict[str, str]] = None,
            use_cache: bool = True
        ) -> Dict[str, Any]:
        """Extraer datos de una página."""
        result = await self.extract_dynamic_content(
            url=url,
            selectors=selectors,
            scroll=False,
            data_patterns=data_patterns,
            use_cache=use_cache
        )
        return result.data

    async def extract_table_data(
            self,
            url: str,
            table_selector: str,
            column_map: Dict[str, str],
            use_cache: bool = True
        ) -> List[Dict[str, Any]]:
        """Extraer datos de una tabla HTML."""
        if use_cache:
            cached = self._get_from_cache(url)
            if cached:
                return cached

        try:
            async with self.browser_context() as context:
                page = await context.new_page()
                await page.goto(url)

                # Usar el agente para extraer la tabla
                data = await self.agent.extract_table(
                    page=page,
                    table_selector=table_selector,
                    column_mapping=column_map
                )

                if use_cache and data:
                    self._save_to_cache(url, data)

                return data

        except Exception as e:
            self.logger.error(f"Error extrayendo tabla: {str(e)}")
            return []

    async def extract_list_data(
            self,
            url: str,
            list_selector: str,
            item_selectors: Dict[str, str],
            use_cache: bool = True
        ) -> List[Dict[str, Any]]:
        """Extraer datos de una lista HTML."""
        if use_cache:
            cached = self._get_from_cache(url)
            if cached:
                return cached

        try:
            async with self.browser_context() as context:
                page = await context.new_page()
                await page.goto(url)

                # Usar el agente para extraer la lista
                data = await self.agent.extract_list(
                    page=page,
                    list_selector=list_selector,
                    item_selectors=item_selectors
                )

                if use_cache and data:
                    self._save_to_cache(url, data)

                return data

        except Exception as e:
            self.logger.error(f"Error extrayendo lista: {str(e)}")
            return []

    def _clean_data(self, value: str, pattern: str) -> str:
        """Limpiar datos usando regex."""
        import re
        try:
            match = re.search(pattern, value)
            return match.group(1) if match else value
        except:
            return value

    def _get_from_cache(self, url: str) -> Optional[Dict]:
        """Obtener datos de caché."""
        cache_file = self.cache_dir / self._get_cache_filename(url)
        if not cache_file.exists():
            return None

        # Verificar TTL
        if (datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)).seconds > self.cache_ttl:
            cache_file.unlink()
            return None

        try:
            with cache_file.open() as f:
                return json.load(f)
        except:
            return None

    def _save_to_cache(self, url: str, data: Dict) -> None:
        """Guardar datos en caché."""
        cache_file = self.cache_dir / self._get_cache_filename(url)
        try:
            with cache_file.open("w") as f:
                json.dump(data, f)
        except Exception as e:
            self.logger.error(f"Error guardando caché: {str(e)}")

    def _get_cache_filename(self, url: str) -> str:
        """Generar nombre de archivo seguro para caché."""
        return hashlib.md5(url.encode()).hexdigest() + ".json"

    def _cleanup_cache(self) -> None:
        """Limpiar archivos de caché expirados."""
        now = datetime.now()
        for file in self.cache_dir.glob("*.json"):
            if (now - datetime.fromtimestamp(file.stat().st_mtime)).seconds > self.cache_ttl:
                file.unlink()

    async def close(self):
        """Cerrar el navegador y limpiar recursos."""
        if hasattr(self, 'browser'):
            await self.browser.close()
        self._cleanup_cache()

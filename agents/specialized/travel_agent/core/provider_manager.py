"""
Gestor de proveedores basado en configuración JSON.
"""

import json
import os
from typing import List, Dict, Optional, Union
from datetime import datetime
import asyncio
import logging
from dataclasses import asdict
from .browser_manager import BrowserManager
from .schemas import TravelPackage, Accommodation, Activity
from .cache_manager import CacheManager

logger = logging.getLogger(__name__)

class ProviderError(Exception):
    """Error específico para problemas con proveedores."""
    pass

class DataValidationError(Exception):
    """Error para datos inválidos o malformados."""
    pass

class ProviderManager:
    """
    Gestor de proveedores que carga configuraciones desde JSON.
    
    Ventajas de este enfoque:
    1. Configuración externa al código
    2. Fácil agregar/quitar proveedores sin tocar código
    3. Modificación de selectores y patrones sin redeployment
    4. Separación clara entre lógica y configuración
    """
    
    def __init__(
        self,
        browser_manager: BrowserManager,
        config_dir: str,
        credentials: Optional[Dict] = None,
        max_retries: int = 3,
        retry_delay: int = 2,
        cache_ttl_minutes: int = 30
    ):
        self.browser_manager = browser_manager
        self.config_dir = config_dir
        self.credentials = credentials or {}
        self.providers = {}
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.cache_manager = CacheManager(ttl_minutes=cache_ttl_minutes)
        self._load_providers()
    
    def _load_providers(self):
        """Cargar todos los proveedores desde archivos JSON."""
        provider_dir = os.path.join(self.config_dir, "providers")
        for filename in os.listdir(provider_dir):
            if filename.endswith(".json"):
                provider_path = os.path.join(provider_dir, filename)
                with open(provider_path, 'r') as f:
                    config = json.load(f)
                    self.providers[config["name"]] = config
    
    async def _search_with_retry(
        self,
        provider_name: str,
        search_params: Dict
    ) -> List[TravelPackage]:
        """
        Ejecuta búsqueda con reintentos automáticos en caso de error.
        
        Args:
            provider_name: Nombre del proveedor
            search_params: Parámetros de búsqueda
            
        Returns:
            Lista de paquetes encontrados
            
        Raises:
            ProviderError: Si todos los intentos fallan
        """
        # Intentar obtener del caché primero
        cached_results = self.cache_manager.get(provider_name, search_params)
        if cached_results:
            logger.info(f"Resultados encontrados en caché para {provider_name}")
            return cached_results

        last_error = None
        for attempt in range(self.max_retries):
            try:
                packages = await self._execute_search(provider_name, search_params)
                if packages:  # Validar que obtuvimos resultados
                    valid_packages = self._validate_packages(packages)
                    # Guardar en caché si hay resultados válidos
                    if valid_packages:
                        self.cache_manager.set(provider_name, search_params, valid_packages)
                    return valid_packages
                logger.warning(f"No se encontraron paquetes en {provider_name}")
                return []
            except Exception as e:
                last_error = e
                logger.warning(
                    f"Intento {attempt + 1}/{self.max_retries} falló para {provider_name}: {str(e)}"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay ** attempt)
                    
        raise ProviderError(
            f"Todos los intentos fallaron para {provider_name}. Último error: {str(last_error)}"
        )
    
    def _validate_packages(self, packages: List[TravelPackage]) -> List[TravelPackage]:
        """
        Valida la integridad y formato de los paquetes extraídos.
        
        Args:
            packages: Lista de paquetes a validar
            
        Returns:
            Lista de paquetes válidos
            
        Raises:
            DataValidationError: Si hay problemas con el formato de los datos
        """
        valid_packages = []
        for package in packages:
            try:
                # Validar campos requeridos
                if not package.title or not package.price:
                    raise DataValidationError("Faltan campos requeridos")
                
                # Validar formato de precio
                if not isinstance(package.price, (int, float)) or package.price <= 0:
                    raise DataValidationError("Precio inválido")
                
                # Validar fechas si existen
                if package.start_date and package.end_date:
                    if package.start_date > package.end_date:
                        raise DataValidationError("Fechas inválidas")
                
                # Validar actividades
                if package.activities:
                    for activity in package.activities:
                        if not activity.title or not activity.description:
                            raise DataValidationError("Actividad inválida")
                
                # Validar alojamiento
                if package.accommodation:
                    if not package.accommodation.name or not package.accommodation.type:
                        raise DataValidationError("Alojamiento inválido")
                
                valid_packages.append(package)
            except Exception as e:
                logger.error(f"Error validando paquete: {str(e)}")
                logger.debug(f"Paquete inválido: {asdict(package)}")
                continue
                
        return valid_packages
    
    async def _execute_search(
        self,
        provider_name: str,
        search_params: Dict
    ) -> List[TravelPackage]:
        """
        Buscar paquetes en un proveedor específico.
        
        Args:
            provider_name: Nombre del proveedor
            search_params: Parámetros de búsqueda
            
        Returns:
            Lista de paquetes encontrados
        """
        if provider_name not in self.providers:
            raise ValueError(f"Provider {provider_name} not found")
            
        config = self.providers[provider_name]
        
        # Autenticación si es necesaria
        if config["requires_auth"]:
            if not await self._authenticate(provider_name):
                raise Exception(f"Authentication failed for {provider_name}")
        
        # Navegar a la página de búsqueda
        await self._navigate_to_search(config, search_params["destination"], search_params["dates"])
        
        # Extraer datos usando los selectores configurados
        raw_data = await self.browser_manager.extract_data(config["selectors"])
        
        # Procesar datos según el mapeo configurado
        packages = []
        for item in raw_data:
            try:
                package = self._process_package_data(item, config)
                packages.append(package)
            except Exception as e:
                print(f"Error processing package from {provider_name}: {str(e)}")
                continue
                
        return packages
    
    async def _authenticate(self, provider_name: str) -> bool:
        """Autenticar en el proveedor si es necesario."""
        config = self.providers[provider_name]
        if not config["requires_auth"]:
            return True
            
        auth_config = config["auth"]
        provider_creds = self.credentials.get(provider_name)
        if not provider_creds:
            raise ValueError(f"Credentials required for {provider_name}")
            
        try:
            # Ejecutar pasos de autenticación
            for step in auth_config["steps"]:
                if step["action"] == "input":
                    value = provider_creds[step["value_from"].split(".")[-1]]
                    await self.browser_manager.fill_input(step["selector"], value)
                elif step["action"] == "click":
                    await self.browser_manager.click(step["selector"])
                    
            # Verificar éxito
            success = await self.browser_manager.wait_for_selector(
                auth_config["success_check"]["selector"],
                timeout=auth_config["success_check"]["timeout"]
            )
            return success
            
        except Exception as e:
            print(f"Authentication error for {provider_name}: {str(e)}")
            return False
    
    async def _navigate_to_search(
        self,
        config: Dict,
        destination: str,
        dates: Optional[Dict]
    ):
        """Navegar a la página de búsqueda y configurar parámetros."""
        nav_config = config["navigation"]["search_page"]
        
        for step in nav_config["steps"]:
            if step["action"] == "navigate":
                await self.browser_manager.navigate(
                    f"{config['base_url']}{step['path']}"
                )
            elif step["action"] == "input":
                if step["target"] == "destination":
                    await self.browser_manager.fill_input(
                        step["selector"],
                        destination
                    )
            elif step["action"] == "date_range" and dates:
                for date_type, selector in step["selectors"].items():
                    if date_type in dates:
                        await self.browser_manager.fill_input(
                            selector,
                            dates[date_type]
                        )
    
    def _process_package_data(self, raw_data: Dict, config: Dict) -> TravelPackage:
        """Procesar datos según el mapeo configurado."""
        mapping = config["data_mapping"]
        
        # Extraer precio según configuración
        price_config = mapping["price"]
        price = self._extract_number(
            raw_data[price_config["selector"]],
            config["data_patterns"]["price"]
        )
        
        # Crear paquete
        return TravelPackage(
            title=raw_data[config["selectors"]["title"]],
            provider=config["name"],
            price=price,
            currency=price_config["currency"],
            duration=self._extract_number(
                raw_data[config["selectors"]["duration"]],
                config["data_patterns"]["duration"]
            ),
            included_services=[
                service.strip()
                for service in raw_data.get(config["selectors"]["included"], [])
            ],
            excluded_services=[
                service.strip()
                for service in raw_data.get(config["selectors"]["excluded"], [])
            ],
            accommodation=self._extract_accommodation(
                raw_data.get(config["selectors"]["accommodation"], {}),
                mapping["accommodation"]
            ),
            flight_info=self._extract_flight_info(
                raw_data.get(config["selectors"]["flight_info"], {}),
                mapping.get("flight_info", {})
            ) if "flight_info" in mapping else None
        )
    
    def _extract_number(self, text: str, pattern: str) -> float:
        """Extraer número usando patrón configurado."""
        import re
        if match := re.search(pattern, text):
            return float(match.group(1).replace(",", ""))
        return 0.0
    
    def _extract_accommodation(
        self,
        raw_data: Dict,
        mapping: Dict
    ) -> Accommodation:
        """Extraer información de alojamiento."""
        return Accommodation(
            name=raw_data.get(mapping["name"], ""),
            category=raw_data.get(mapping["category"], ""),
            room_type=raw_data.get(mapping["room_type"], ""),
            board_type=raw_data.get(mapping["board_type"], "")
        )
    
    def _extract_flight_info(self, raw_data: Dict, mapping: Dict) -> Dict:
        """Extraer información de vuelos."""
        result = {}
        for flight_type in ["outbound", "return"]:
            if flight_type in mapping:
                result[flight_type] = {
                    field: raw_data.get(selector, "")
                    for field, selector in mapping[flight_type].items()
                }
        return result
    
    async def search_packages(
        self,
        provider_name: str,
        destination: str,
        dates: Optional[Dict] = None,
        preferences: Optional[Dict] = None
    ) -> List[TravelPackage]:
        """
        Busca paquetes en un proveedor específico con reintentos automáticos.
        
        Args:
            provider_name: Nombre del proveedor
            destination: Destino del viaje
            dates: Fechas de viaje (opcional)
            preferences: Preferencias adicionales (opcional)
            
        Returns:
            Lista de paquetes encontrados
            
        Raises:
            ProviderError: Si hay problemas con el proveedor
        """
        if provider_name not in self.providers:
            raise ProviderError(f"Proveedor no encontrado: {provider_name}")
            
        search_params = {
            "destination": destination,
            "dates": dates or {},
            "preferences": preferences or {}
        }
        
        return await self._search_with_retry(provider_name, search_params)
    
    async def search_all_providers(
        self,
        destination: str,
        dates: Optional[Dict] = None,
        preferences: Optional[Dict] = None
    ) -> Dict[str, Union[List[TravelPackage], str]]:
        """
        Busca paquetes en todos los proveedores disponibles.
        
        Returns:
            Diccionario con resultados por proveedor o mensaje de error
        """
        results = {}
        tasks = []
        
        for provider in self.providers:
            task = asyncio.create_task(
                self.search_packages(provider, destination, dates, preferences)
            )
            tasks.append((provider, task))
        
        for provider, task in tasks:
            try:
                results[provider] = await task
            except Exception as e:
                logger.error(f"Error en proveedor {provider}: {str(e)}")
                results[provider] = str(e)
                
        return results

    def invalidate_cache(
        self,
        provider_name: Optional[str] = None,
        search_params: Optional[Dict] = None
    ):
        """
        Invalida entradas específicas del caché.
        
        Args:
            provider_name: Si se especifica, solo invalida este proveedor
            search_params: Si se especifica, solo invalida estas búsquedas
        """
        self.cache_manager.invalidate(provider_name, search_params)
        
    def get_cache_stats(self) -> Dict:
        """Retorna estadísticas del uso del caché."""
        return self.cache_manager.get_stats()

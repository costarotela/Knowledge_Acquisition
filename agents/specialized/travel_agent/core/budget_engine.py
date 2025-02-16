"""
Motor de generación de presupuestos con templates personalizables.

Características:
1. Templates en formato Jinja2
2. Personalización por tipo de cliente
3. Múltiples formatos de salida (HTML, PDF, texto plano)
4. Sistema de variables dinámicas
5. Internacionalización
"""

from typing import Dict, List, Optional, Union
from datetime import datetime
import json
import logging
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML
from babel.numbers import format_currency
from dataclasses import asdict

from .schemas import TravelPackage, Budget, CustomerProfile

logger = logging.getLogger(__name__)

class BudgetEngine:
    """
    Motor de generación de presupuestos personalizados.
    """
    
    def __init__(
        self,
        templates_dir: Optional[Path] = None,
        locale: str = "es_AR",
        currency: str = "USD"
    ):
        self.templates_dir = templates_dir or Path(__file__).parent.parent / "templates"
        self.locale = locale
        self.currency = currency
        
        # Configurar Jinja2
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Registrar filtros personalizados
        self.jinja_env.filters['format_currency'] = self._format_currency
        self.jinja_env.filters['format_date'] = self._format_date
        
        # Cargar perfiles de cliente
        self._load_customer_profiles()
        
    def _load_customer_profiles(self):
        """Carga perfiles de cliente desde configuración."""
        profiles_path = self.templates_dir / "profiles.json"
        try:
            with open(profiles_path, 'r', encoding='utf-8') as f:
                self.customer_profiles = json.load(f)
        except FileNotFoundError:
            logger.warning(f"No se encontró archivo de perfiles en {profiles_path}")
            self.customer_profiles = {}
            
    def _format_currency(self, value: float, currency: Optional[str] = None) -> str:
        """Formatea valores monetarios según la configuración regional."""
        return format_currency(
            value,
            currency or self.currency,
            locale=self.locale
        )
        
    def _format_date(self, date: datetime, format: str = "long") -> str:
        """Formatea fechas según la configuración regional."""
        if format == "long":
            return date.strftime("%d de %B de %Y")
        return date.strftime("%d/%m/%Y")
        
    def _prepare_template_data(
        self,
        packages: List[TravelPackage],
        customer_profile: CustomerProfile,
        extra_context: Optional[Dict] = None
    ) -> Dict:
        """
        Prepara los datos para el template.
        
        Args:
            packages: Lista de paquetes a incluir
            customer_profile: Perfil del cliente
            extra_context: Contexto adicional opcional
            
        Returns:
            Diccionario con todos los datos procesados
        """
        # Procesar paquetes
        processed_packages = []
        for pkg in packages:
            pkg_dict = asdict(pkg)
            # Agregar campos calculados
            pkg_dict['total_activities'] = len(pkg.activities)
            pkg_dict['price_per_day'] = (
                pkg.price / (pkg.end_date - pkg.start_date).days
                if pkg.end_date and pkg.start_date
                else pkg.price
            )
            processed_packages.append(pkg_dict)
            
        # Obtener estilo según perfil
        profile_config = self.customer_profiles.get(
            customer_profile.type,
            self.customer_profiles.get('default', {})
        )
        
        # Construir contexto
        context = {
            'packages': processed_packages,
            'customer': asdict(customer_profile),
            'style': profile_config.get('style', {}),
            'recommendations': profile_config.get('recommendations', []),
            'metadata': {
                'generated_at': datetime.now(),
                'valid_until': datetime.now() + profile_config.get(
                    'validity_days',
                    7
                ),
                'locale': self.locale,
                'currency': self.currency
            }
        }
        
        # Agregar contexto extra si existe
        if extra_context:
            context.update(extra_context)
            
        return context
        
    def generate_budget(
        self,
        packages: List[TravelPackage],
        customer_profile: CustomerProfile,
        template_name: str = "default.html",
        output_format: str = "html",
        extra_context: Optional[Dict] = None
    ) -> Union[str, bytes]:
        """
        Genera un presupuesto personalizado.
        
        Args:
            packages: Lista de paquetes a incluir
            customer_profile: Perfil del cliente
            template_name: Nombre del template a usar
            output_format: Formato de salida (html, pdf)
            extra_context: Contexto adicional opcional
            
        Returns:
            Presupuesto generado en el formato especificado
        """
        try:
            # Preparar datos
            context = self._prepare_template_data(
                packages,
                customer_profile,
                extra_context
            )
            
            # Obtener template
            template = self.jinja_env.get_template(template_name)
            
            # Generar HTML
            html_content = template.render(**context)
            
            # Convertir según formato solicitado
            if output_format == "pdf":
                return HTML(string=html_content).write_pdf()
            
            return html_content
            
        except Exception as e:
            logger.error(f"Error generando presupuesto: {str(e)}")
            raise

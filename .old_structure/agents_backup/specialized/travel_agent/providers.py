"""
Tourism provider management and data extraction.
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, HttpUrl, validator, field_validator
from datetime import datetime
import json
from .schemas import TravelPackage, Accommodation, Activity

class ExtractionRules(BaseModel):
    """Rules for extracting data from a specific provider."""
    
    selectors: Dict[str, str] = {
        "package_card": ".package-item",
        "title": ".package-title",
        "price": ".package-price",
        "duration": ".package-duration",
        "included": ".included-services",
        "excluded": ".excluded-services",
        "accommodation": ".accommodation-details",
        "activities": ".activities-list"
    }
    
    data_patterns: Dict[str, str] = {
        "price": r"\$\s*([\d,]+(?:\.\d{2})?)",
        "duration": r"(\d+)\s*(?:días|days)",
        "rating": r"([\d.]+)\s*\/\s*5"
    }
    
    navigation_steps: List[Dict[str, Any]] = [
        {
            "action": "navigate",
            "target": "search_page",
            "path": "/packages/search"
        },
        {
            "action": "input",
            "target": "destination",
            "selector": "#destination-input"
        },
        {
            "action": "click",
            "target": "search_button",
            "selector": "#search-packages"
        }
    ]

    class Config:
        arbitrary_types_allowed = True

class TourismProvider(BaseModel):
    """
    Represents a tourism service provider with methods for data extraction.
    """
    name: str
    base_url: HttpUrl
    supported_destinations: List[str]
    last_updated: datetime
    extraction_rules: ExtractionRules
    
    class Config:
        arbitrary_types_allowed = True

    @field_validator('extraction_rules', mode='before')
    def validate_extraction_rules(cls, v):
        """Validate extraction rules."""
        if isinstance(v, dict):
            return ExtractionRules(**v)
        return v

    async def extract_packages(
        self,
        destination: str,
        dates: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Extract package information from the provider's website.
        
        Args:
            destination: Target destination
            dates: Optional date range
            
        Returns:
            List of raw package data
        """
        # Validate destination
        if destination not in self.supported_destinations:
            raise ValueError(f"Destination {destination} not supported by {self.name}")
        
        # Return extraction rules for the browser manager
        return {
            "provider": self.name,
            "rules": self.extraction_rules.dict(),
            "context": {
                "destination": destination,
                "dates": dates or {}
            }
        }
        
    async def validate_package(
        self,
        package_data: Dict
    ) -> bool:
        """
        Validate extracted package data.
        
        Args:
            package_data: Raw package data
            
        Returns:
            True if valid, False otherwise
            
        Raises:
            ValueError: If package is invalid
        """
        required_fields = [
            "id", "provider", "destination", "title", "description",
            "price", "currency", "duration", "start_date", "end_date",
            "accommodation", "activities", "included_services", 
            "excluded_services", "booking_url", "terms_conditions"
        ]
        
        for field in required_fields:
            if field not in package_data:
                raise ValueError(f"Missing required field: {field}")
                
        # Validar fechas
        try:
            if not isinstance(package_data["start_date"], datetime):
                datetime.strptime(package_data["start_date"], "%Y-%m-%d")
            if not isinstance(package_data["end_date"], datetime):
                datetime.strptime(package_data["end_date"], "%Y-%m-%d")
        except ValueError:
            raise ValueError("Invalid date format. Use YYYY-MM-DD")
            
        # Validate price
        try:
            price = float(package_data['price'])
            if price <= 0:
                raise ValueError("Invalid price")
        except (ValueError, TypeError):
            raise ValueError("Invalid price")
            
        # Validate duration
        try:
            duration = int(package_data['duration'])
            if duration <= 0:
                raise ValueError("Invalid duration")
        except (ValueError, TypeError):
            raise ValueError("Invalid duration")
            
        return True

    async def search_packages(
        self,
        destination: str,
        start_date: str,
        end_date: str,
        **kwargs
    ) -> List[Dict]:
        """
        Search for travel packages in this provider.
        
        Args:
            destination: Target destination
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            **kwargs: Additional search parameters
            
        Returns:
            List of travel packages
        """
        # Base implementation returns a test package
        return [{
            "id": f"{self.name.lower()}-test-package-1",
            "provider": self.name,
            "destination": destination,
            "title": "Test Package",
            "description": "A test package for development",
            "price": 1000.0,
            "currency": "USD",
            "duration": 7,
            "start_date": datetime.strptime(start_date, "%Y-%m-%d"),
            "end_date": datetime.strptime(end_date, "%Y-%m-%d"),
            "accommodation": {
                "name": "Test Hotel",
                "type": "hotel",
                "location": "Downtown",
                "rating": 4.0,
                "amenities": ["wifi", "pool"],
                "room_types": ["double"]
            },
            "activities": [{
                "name": "Test Activity",
                "description": "A test activity",
                "duration": "2 hours",
                "price": 50.0,
                "included": ["guide"],
                "requirements": []
            }],
            "included_services": ["breakfast", "wifi", "airport transfer"],
            "excluded_services": ["lunch", "dinner", "tips"],
            "booking_url": f"{self.base_url}/book/test-package-1",
            "terms_conditions": "Standard terms and conditions apply"
        }]

    @classmethod
    def create_aero_provider(cls) -> 'TourismProvider':
        """
        Create a provider instance for Aero (example provider).
        """
        return cls(
            name="Aero",
            base_url=HttpUrl("https://aero.example.com"),
            supported_destinations=[
                "Buenos Aires", "Bariloche", "Mendoza",
                "Ushuaia", "Calafate", "Iguazu"
            ],
            last_updated=datetime.now(),
            extraction_rules=ExtractionRules(
                selectors={
                    "package_card": ".package-item",
                    "title": ".package-title",
                    "price": ".package-price",
                    "duration": ".package-duration",
                    "included": ".included-services",
                    "excluded": ".excluded-services",
                    "accommodation": ".accommodation-details",
                    "activities": ".activities-list"
                },
                data_patterns={
                    "price": r"\$\s*([\d,]+(?:\.\d{2})?)",
                    "duration": r"(\d+)\s*(?:días|days)",
                    "rating": r"([\d.]+)\s*\/\s*5"
                },
                navigation_steps=[
                    {
                        "action": "navigate",
                        "target": "search_page",
                        "path": "/packages/search"
                    },
                    {
                        "action": "input",
                        "target": "destination",
                        "selector": "#destination-input"
                    },
                    {
                        "action": "click",
                        "target": "search_button",
                        "selector": "#search-packages"
                    }
                ]
            )
        )

    @classmethod
    def create_ola_provider(cls) -> 'TourismProvider':
        """
        Create a provider instance for Ola (example provider).
        """
        return cls(
            name="Ola",
            base_url=HttpUrl("https://ola.example.com"),
            supported_destinations=[
                "Mar del Plata", "Villa Carlos Paz", "Córdoba",
                "Salta", "Jujuy", "San Juan"
            ],
            last_updated=datetime.now(),
            extraction_rules=ExtractionRules(
                selectors={
                    "package_card": ".tour-package",
                    "title": ".tour-title",
                    "price": ".tour-price",
                    "duration": ".tour-duration",
                    "included": ".included-list",
                    "excluded": ".not-included",
                    "accommodation": ".hotel-info",
                    "activities": ".activities"
                },
                data_patterns={
                    "price": r"ARS\s*([\d.]+)",
                    "duration": r"(\d+)\s*noches",
                    "rating": r"(\d+)\s*estrellas"
                },
                navigation_steps=[
                    {
                        "action": "navigate",
                        "target": "home",
                        "path": "/"
                    },
                    {
                        "action": "select",
                        "target": "destination_dropdown",
                        "selector": "#destino"
                    },
                    {
                        "action": "click",
                        "target": "buscar_button",
                        "selector": ".buscar-paquetes"
                    }
                ]
            )
        )

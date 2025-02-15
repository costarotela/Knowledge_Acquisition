"""Mock del módulo browser_use para pruebas."""

import asyncio

class BrowserAgent:
    """Mock de BrowserAgent."""
    
    def __init__(self, *args, **kwargs):
        """Inicializar el mock."""
        self.args = args
        self.kwargs = kwargs
    
    async def navigate(self, url: str) -> None:
        """Mock de navegación."""
        await asyncio.sleep(0)  # Simular operación async
    
    async def extract_data(self, rules: dict) -> dict:
        """Mock de extracción de datos."""
        await asyncio.sleep(0)  # Simular operación async
        
        if "name" in rules:  # Si estamos extrayendo datos del proveedor
            return {
                "name": "Example Provider",
                "destinations": ["Bariloche", "Mar del Plata", "Mendoza"],
                "packages": ["Economic", "Standard", "Premium"],
                "policies": "Standard cancellation policies apply",
                "contact": "info@example-provider.com"
            }
            
        # Si estamos extrayendo datos de paquetes
        return {
            "id": "test-package-1",
            "provider": "TestProvider",
            "destination": "Bariloche",
            "title": "Test Package",
            "description": "A test package",
            "price": 1000.0,
            "currency": "USD",
            "duration": 10,
            "dates": {
                "start": "2025-03-01",
                "end": "2025-03-10"
            },
            "accommodation": {
                "name": "Test Hotel",
                "type": "hotel",
                "location": "Bariloche",
                "rating": 4.5,
                "amenities": ["wifi", "pool"],
                "room_types": ["single", "double"]
            },
            "activities": [{
                "name": "City Tour",
                "description": "Tour por la ciudad",
                "duration": "4 hours",
                "price": 50.0,
                "included": ["guide", "transport"],
                "requirements": ["comfortable shoes"]
            }],
            "included_services": ["breakfast", "airport transfer"],
            "excluded_services": ["lunch", "dinner"],
            "booking_url": "https://example.com/booking",
            "terms_conditions": "Standard terms apply"
        }

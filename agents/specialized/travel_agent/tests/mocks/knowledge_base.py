"""Mock del módulo knowledge_base para pruebas."""

class MockKnowledgeBase:
    """Mock de KnowledgeBase."""
    
    def __init__(self):
        """Inicializar el mock."""
        pass
        
    async def get_response(self, *args, **kwargs):
        """Mock de get_response."""
        return "This is a mock response"
        
    async def analyze_text(self, *args, **kwargs):
        """Mock de analyze_text."""
        return {
            "sentiment": "positive",
            "topics": ["travel", "tourism"],
            "entities": ["Bariloche", "Argentina"]
        }
        
    async def extract_data(self, *args, **kwargs):
        """Mock de extract_data."""
        return {
            "name": "Example Provider",
            "destinations": ["Bariloche", "Mar del Plata", "Mendoza"],
            "packages": ["Economic", "Standard", "Premium"],
            "policies": "Standard cancellation policies apply",
            "contact": "info@example-provider.com"
        }

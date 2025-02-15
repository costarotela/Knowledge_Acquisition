"""Browser manager for travel agent."""

from typing import Dict, Any, Optional
from datetime import datetime

try:
    from browser_use.browser_agent import BrowserAgent
    from langchain.chat_models import ChatOpenAI
    from core_system.settings import get_settings
except ImportError:
    # Para pruebas, usamos los mocks
    from .tests.mocks.browser_use import BrowserAgent
    
    def get_settings():
        return {"openai_api_key": "test-key"}
    
    class ChatOpenAI:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

from .schemas import TravelPackage, Accommodation, Activity

class BrowserManager:
    """Browser manager for travel agent."""

    def __init__(self, llm_model: str = "gpt-4"):
        """
        Initialize the browser manager.

        Args:
            llm_model: Language model to use for browser automation
        """
        self.settings = get_settings()
        self.llm = ChatOpenAI(model=llm_model)
        self.browser = BrowserAgent()

    async def navigate(self, url: str) -> None:
        """Navigate to a URL."""
        await self.browser.navigate(url)

    async def extract_data(self, rules: dict) -> dict:
        """Extract data from current page using rules."""
        try:
            return await self.browser.extract_data(rules)
        except Exception as e:
            print(f"Error extracting data: {str(e)}")
            return {}

    async def extract_package_data(
        self,
        url: str,
        extraction_rules: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Extract package data from a given URL using provided extraction rules.

        Args:
            url: URL to extract data from
            extraction_rules: Rules for extracting data

        Returns:
            Extracted package data or None if extraction failed
        """
        try:
            await self.navigate(url)
            data = await self.extract_data(extraction_rules)
            
            if not data:
                print(f"No data extracted from {url}")
                return None

            return self._process_package_data(data)
        except Exception as e:
            print(f"Error extracting package data from {url}: {str(e)}")
            return None

    def _process_package_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process raw package data into a structured format.

        Args:
            data: Raw data extracted from the webpage

        Returns:
            Processed package data
        """
        processed_data = {
            "title": data.get("title", ""),
            "description": data.get("description", ""),
            "price": self._extract_price(data.get("price", "")),
            "currency": self._extract_currency(data.get("price", "")),
            "dates": self._process_dates(data.get("dates", {})),
            "accommodation": self._process_accommodation(data.get("accommodation", {})),
            "activities": self._process_activities(data.get("activities", [])),
            "included_services": data.get("included_services", []),
            "excluded_services": data.get("excluded_services", [])
        }
        return processed_data

    def _extract_price(self, price_str: str) -> float:
        """Extract numeric price from string."""
        try:
            # Remove currency symbols and convert to float
            price = float(''.join(filter(lambda x: x.isdigit() or x == '.', price_str)))
            return price
        except (ValueError, TypeError):
            return 0.0

    def _extract_currency(self, price_str: str) -> str:
        """Extract currency from price string."""
        # Implementar lógica para extraer moneda
        # Por ahora retornamos USD por defecto
        return "USD"

    def _process_dates(self, dates: Dict[str, Any]) -> Dict[str, str]:
        """Process package dates."""
        try:
            start_date = datetime.strptime(dates.get("start", ""), "%Y-%m-%d")
            end_date = datetime.strptime(dates.get("end", ""), "%Y-%m-%d")
            return {
                "start": start_date.strftime("%Y-%m-%d"),
                "end": end_date.strftime("%Y-%m-%d")
            }
        except ValueError:
            return {
                "start": "",
                "end": ""
            }

    def _process_accommodation(self, accommodation: Dict[str, Any]) -> Dict[str, Any]:
        """Process accommodation data."""
        return {
            "name": accommodation.get("name", ""),
            "type": accommodation.get("type", "hotel"),
            "location": accommodation.get("location", ""),
            "rating": float(accommodation.get("rating", 0)),
            "amenities": accommodation.get("amenities", []),
            "room_types": accommodation.get("room_types", [])
        }

    def _process_activities(self, activities: list) -> list:
        """Process activities data."""
        processed_activities = []
        for activity in activities:
            if isinstance(activity, dict):
                processed_activities.append({
                    "name": activity.get("name", ""),
                    "description": activity.get("description", ""),
                    "duration": activity.get("duration", ""),
                    "price": float(activity.get("price", 0)),
                    "included": activity.get("included", []),
                    "requirements": activity.get("requirements", [])
                })
        return processed_activities

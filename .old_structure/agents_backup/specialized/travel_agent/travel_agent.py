"""
Core implementation of the Travel Agent.
"""

from typing import List, Dict, Optional
from datetime import datetime
from langchain.tools import BaseTool
from langchain.agents import AgentExecutor

try:
    from ..core_system.knowledge_base import KnowledgeBase
except ImportError:
    # Para pruebas, usamos el mock
    from .tests.mocks.knowledge_base import MockKnowledgeBase as KnowledgeBase

from .providers import TourismProvider
from .schemas import TravelPackage, Accommodation, Activity
from .browser_manager import BrowserManager
from .tests.mocks.browser_use import BrowserAgent
from pydantic import HttpUrl
from .providers import ExtractionRules

class TravelAgent:
    """
    Specialized agent for processing travel and tourism information.
    
    This agent can:
    1. Search and extract information from tourism providers using browser-use
    2. Compare and analyze travel packages
    3. Maintain updated information about destinations
    4. Process and validate travel-related data
    """
    
    def __init__(
        self,
        knowledge_base: KnowledgeBase,
        providers: Optional[List[TourismProvider]] = None,
        browser_config: Optional[Dict] = None,
        llm_model: str = "gpt-4"
    ):
        self.knowledge_base = knowledge_base
        self.providers = providers or []
        self.browser_config = browser_config or {}
        self.browser_manager = BrowserManager(llm_model=llm_model)
        
    async def search_packages(
        self,
        destination: str,
        dates: Optional[Dict] = None,
        preferences: Optional[Dict] = None
    ) -> List[TravelPackage]:
        """
        Search for travel packages across all registered providers.
        
        Args:
            destination: Target destination
            dates: Optional date range for the trip
            preferences: Optional user preferences
            
        Returns:
            List of matching travel packages
        """
        all_packages = []
        dates = dates or {}
        
        # Search across all providers
        for provider in self.providers:
            try:
                # Use provider's search_packages method
                raw_packages = await provider.search_packages(
                    destination=destination,
                    start_date=dates.get("start", ""),
                    end_date=dates.get("end", ""),
                    preferences=preferences or {}
                )
                
                # Validate and process packages
                for package_data in raw_packages:
                    if await provider.validate_package(package_data):
                        package = TravelPackage(**package_data)
                        all_packages.append(package)
                        
            except Exception as e:
                # Log error but continue with other providers
                print(f"Error extracting data from {provider.name}: {str(e)}")
                
        return all_packages
        
    async def analyze_provider(
        self,
        provider_url: str
    ) -> TourismProvider:
        """
        Analyze a new tourism provider website and extract relevant information.
        
        Args:
            provider_url: URL of the tourism provider
            
        Returns:
            Processed provider information
        """
        # Use browser-use to analyze provider website
        task = f"""
        1. Navigate to {provider_url}
        2. Extract the following information:
           - Provider name
           - Available destinations
           - Types of packages offered
           - Booking policies
           - Contact information
        3. Return the data in JSON format
        """
        
        agent = BrowserAgent(
            task=task,
            llm=self.browser_manager.llm
        )
        
        await agent.navigate(provider_url)
        data = await agent.extract_data({
            "name": ".provider-name",
            "destinations": ".destinations-list",
            "packages": ".package-types",
            "policies": ".booking-policies",
            "contact": ".contact-info"
        })
        
        # Create and return provider instance
        provider = TourismProvider(
            name=data["name"],
            base_url=HttpUrl(provider_url),
            supported_destinations=data["destinations"],
            last_updated=datetime.now(),
            extraction_rules=ExtractionRules()
        )
        
        self.providers.append(provider)
        return provider
        
    async def compare_packages(
        self,
        packages: List[TravelPackage]
    ) -> Dict:
        """
        Compare multiple travel packages and provide analysis.
        
        Args:
            packages: List of packages to compare
            
        Returns:
            Comparison analysis including:
            - Price comparison
            - Value analysis
            - Feature comparison
            - Recommendations
        """
        if not packages:
            return {"error": "No packages to compare"}
            
        analysis = {
            "price_analysis": self._analyze_prices(packages),
            "features_comparison": self._compare_features(packages),
            "value_ranking": self._rank_by_value(packages),
            "recommendations": self._generate_recommendations(packages)
        }
        
        return analysis
        
    def _analyze_prices(self, packages: List[TravelPackage]) -> Dict:
        """Analyze price distribution and variations."""
        prices = [p.price for p in packages]
        return {
            "min_price": min(prices),
            "max_price": max(prices),
            "avg_price": sum(prices) / len(prices),
            "price_range": max(prices) - min(prices)
        }
        
    def _compare_features(self, packages: List[TravelPackage]) -> Dict:
        """Compare included features and services."""
        feature_comparison = {}
        for package in packages:
            features = {
                "accommodation": package.accommodation.type if package.accommodation else None,
                "activities": len(package.activities),
                "included_services": package.included_services,
                "duration": package.duration
            }
            feature_comparison[package.id] = features
        return feature_comparison
        
    def _rank_by_value(self, packages: List[TravelPackage]) -> List[Dict]:
        """Rank packages by value for money."""
        ranked = []
        for package in packages:
            value_score = self._calculate_value_score(package)
            ranked.append({
                "package_id": package.id,
                "value_score": value_score,
                "price": package.price
            })
        return sorted(ranked, key=lambda x: x["value_score"], reverse=True)
        
    def _calculate_value_score(self, package: TravelPackage) -> float:
        """Calculate a value score based on features and price."""
        base_score = 100
        
        # Add points for included features
        if package.accommodation:
            base_score += 20
        base_score += len(package.activities) * 5
        base_score += len(package.included_services) * 2
        
        # Normalize by price and duration
        value_score = base_score / (package.price / package.duration)
        return round(value_score, 2)
        
    def _generate_recommendations(self, packages: List[TravelPackage]) -> List[Dict]:
        """Generate personalized recommendations."""
        recommendations = []
        
        # Best value
        value_rankings = self._rank_by_value(packages)
        if value_rankings:
            best_value = next((p for p in packages if p.id == value_rankings[0]["package_id"]), None)
            if best_value:
                recommendations.append({
                    "category": "Best Value",
                    "package_id": best_value.id,
                    "reason": "Highest value for money based on included features and price"
                })
        
        # Most comprehensive
        most_activities = max(packages, key=lambda p: len(p.activities))
        recommendations.append({
            "category": "Most Comprehensive",
            "package_id": most_activities.id,
            "reason": f"Includes the most activities ({len(most_activities.activities)})"
        })
        
        return recommendations
        
    def _parse_provider_info(self, raw_data: Dict) -> Dict:
        """Parse and validate provider information."""
        # TODO: Implement provider info parsing
        return raw_data

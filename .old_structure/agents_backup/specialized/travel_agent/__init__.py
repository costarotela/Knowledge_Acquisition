"""
Travel Agent Module

This module implements a specialized agent for travel and tourism information processing.
It focuses on extracting, analyzing and comparing travel-related information from various
tourism providers.
"""

from .travel_agent import TravelAgent
from .providers import TourismProvider
from .schemas import TravelPackage, Accommodation, Activity

__all__ = ['TravelAgent', 'TourismProvider', 'TravelPackage', 'Accommodation', 'Activity']

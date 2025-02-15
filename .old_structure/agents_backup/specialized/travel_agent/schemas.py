"""
Schema definitions for travel packages.
"""

from datetime import datetime
from typing import List
from pydantic import BaseModel, Field, HttpUrl

class Accommodation(BaseModel):
    """Accommodation details."""
    
    name: str
    type: str
    location: str
    rating: float = Field(ge=0, le=5)
    amenities: List[str]
    room_types: List[str]

class Activity(BaseModel):
    """Activity details."""
    
    name: str
    description: str
    duration: str
    price: float
    included: List[str]
    requirements: List[str]

class TravelPackage(BaseModel):
    """Travel package details."""
    
    id: str
    provider: str
    destination: str
    title: str
    description: str
    price: float
    currency: str
    duration: int
    start_date: datetime
    end_date: datetime
    accommodation: Accommodation
    activities: List[Activity]
    included_services: List[str]
    excluded_services: List[str]
    booking_url: HttpUrl
    terms_conditions: str

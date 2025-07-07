# idealista_scraper/models.py

"""
Data structures (TypedDicts, Pydantic models, etc.) for the scraper.
"""

from typing import Optional
# Use typing_extensions for TypedDict for wider compatibility
from typing_extensions import TypedDict


class PropertyResult(TypedDict, total=False):
    """
    Represents the structure of scraped property data (viviendas).
    Matches the expected fields for parsing and database saving.
    """

    listing_id: Optional[int]
    url: str
    property_type: Optional[str]
    title: Optional[str]
    location: Optional[str]
    flat_floor_number: Optional[str]
    price: Optional[int]
    pricedown_price: Optional[float]
    size_sqm: Optional[int]
    description: Optional[str]
    num_bedrooms: Optional[int]
    advertiser_type: Optional[str]
    advertiser_name: Optional[str]



class RoomResult(TypedDict, total=False):
    """
    Represents the structure of scraped room data.
    Matches the expected fields for parsing and database saving.
    Based on scrap_habitacion.py.
    """
    room_id: Optional[int] 
    url: str  
    property_type: Optional[str]  
    title: Optional[str]
    location: Optional[str]
    flat_floor_number: Optional[str]
    price: Optional[int]
    pricedown_price: Optional[float]    
    available_from_date: Optional[str]  
    description: Optional[str]
    num_bedrooms: Optional[int]
    advertiser_type: Optional[str] 
    advertiser_name: Optional[str]


class Capitals(TypedDict, total=False):
    """
    Represents the structure of a capital city's geographical data.
    Matches the idealista_scrapper.capitals table definition.
    """
    id: Optional[int]
    province_code: str
    capital_name: str
    zona: str
    distrito: Optional[str]
    idealista_slug: str
    is_active: bool
    is_active: bool
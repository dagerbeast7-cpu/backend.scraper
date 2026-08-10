from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RawLead:
    """
    Common shape every scraper provider (Google Maps, Places API, directories)
    must normalize its output into before it hits dedup/enrichment/scoring.
    """

    business_name: str
    city: Optional[str] = None
    state: Optional[str] = None
    locality: Optional[str] = None  # neighbourhood/area within the city, e.g. "Bandra West"
    phone: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    industry: Optional[str] = None
    source: str = "unknown"
    source_url: Optional[str] = None
    google_maps_id: Optional[str] = None
    google_rating: Optional[float] = None
    review_count: Optional[int] = None
    business_description: Optional[str] = None
    extra: dict = field(default_factory=dict)


class ScraperProvider(ABC):
    """Interface every scraping backend implements."""

    name: str = "base"

    @abstractmethod
    def search(
        self, query: str, city: str, max_results: int, area: Optional[str] = None
    ) -> list[RawLead]:
        """
        Run one search query (e.g. 'real estate broker') in one city, or
        narrowed to one area/locality within that city (e.g. 'Bandra West'
        within 'Mumbai') when `area` is given.
        """
        raise NotImplementedError


def build_location_query(query: str, city: str, area: Optional[str] = None) -> str:
    """
    Single place that decides how area+city get combined into the free-text
    search string sent to Google -- e.g. "real estate broker in Bandra
    West, Mumbai" vs "real estate broker in Mumbai". Both the Places API
    and Maps-web search interpret this kind of locality-scoped text fine
    without needing separate geocoding.
    """
    location = f"{area}, {city}" if area else city
    return f"{query} in {location}"


# ICP search terms for Phase 1 (see project spec).
PHASE_1_ICP_QUERIES: list[str] = [
    "real estate broker",
    "property consultant",
    "real estate agency",
    "small builder",
    "real estate developer",
]

# Automated Nightly Scraping Target Matrix (8:00 PM - 6:00 AM IST)
NIGHTLY_SCHEDULE_TARGETS: dict[str, list[dict[str, str | None]]] = {
    "delhi_ncr": [
        {"city": "Gurgaon", "area": "Golf Course Road"},
        {"city": "Gurgaon", "area": "Cyber City"},
        {"city": "Noida", "area": "Sector 62"},
        {"city": "Noida", "area": "Sector 150"},
        {"city": "Greater Noida", "area": None},
        {"city": "Faridabad", "area": None},
        {"city": "Delhi", "area": "Dwarka"},
        {"city": "Delhi", "area": "Lajpat Nagar"},
    ],
    "mumbai": [
        {"city": "Mumbai", "area": "Mumbai Central"},
        {"city": "Mumbai", "area": "Bandra West"},
        {"city": "Mumbai", "area": "Andheri West"},
        {"city": "Thane", "area": "Thane West"},
        {"city": "Navi Mumbai", "area": "Vashi"},
    ],
    "bangalore": [
        {"city": "Bangalore", "area": "Indiranagar"},
        {"city": "Bangalore", "area": "Koramangala"},
        {"city": "Bangalore", "area": "Whitefield"},
        {"city": "Bangalore", "area": "HSR Layout"},
        {"city": "Bangalore", "area": "Electronic City"},
    ],
}


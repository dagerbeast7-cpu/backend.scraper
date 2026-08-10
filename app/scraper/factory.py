from app.config import settings
from app.scraper.base import ScraperProvider


def get_provider(provider_name: str | None = None) -> ScraperProvider:
    name = provider_name or settings.scraper_provider

    if name == "google_places":
        from app.scraper.google_places_api import GooglePlacesAPIProvider

        return GooglePlacesAPIProvider()

    if name == "playwright":
        from app.scraper.google_maps_playwright import GoogleMapsPlaywrightProvider

        return GoogleMapsPlaywrightProvider()

    raise ValueError(f"Unknown scraper provider: {name!r}")

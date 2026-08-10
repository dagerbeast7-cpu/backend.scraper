from __future__ import annotations

import logging
import time

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.scraper.base import RawLead, ScraperProvider, build_location_query

logger = logging.getLogger(__name__)

TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
PLACE_DETAILS_URL = "https://places.googleapis.com/v1/places/{place_id}"

# Fields kept intentionally narrow to control per-request cost.
SEARCH_FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.location",
        "places.rating",
        "places.userRatingCount",
        "places.websiteUri",
        "places.nationalPhoneNumber",
        "places.businessStatus",
        "places.primaryType",
    ]
)


class GooglePlacesAPIProvider(ScraperProvider):
    """
    Uses Google's official Places API (New) Text Search endpoint.
    Requires GOOGLE_PLACES_API_KEY. This is the ToS-compliant, non-fragile
    way to get Google Maps business data -- billed per request by Google,
    but it won't get your IP blocked and the schema is stable.
    """

    name = "google_places_api"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.google_places_api_key
        if not self.api_key:
            raise RuntimeError(
                "GOOGLE_PLACES_API_KEY is not set. Either set it in .env, or "
                "use SCRAPER_PROVIDER=playwright instead."
            )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _text_search(self, query: str, page_token: str | None = None) -> dict:
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": SEARCH_FIELD_MASK
            + (",nextPageToken" if not page_token else ""),
        }
        body: dict = {"textQuery": query, "pageSize": 20}
        if page_token:
            body["pageToken"] = page_token

        with httpx.Client(timeout=20) as client:
            resp = client.post(TEXT_SEARCH_URL, headers=headers, json=body)
            resp.raise_for_status()
            return resp.json()

    def search(
        self, query: str, city: str, max_results: int = 60, area: str | None = None
    ) -> list[RawLead]:
        full_query = build_location_query(query, city, area)
        leads: list[RawLead] = []
        page_token: str | None = None

        while len(leads) < max_results:
            data = self._text_search(full_query, page_token)
            places = data.get("places", [])
            if not places:
                break

            for place in places:
                leads.append(self._to_raw_lead(place, query, city, area))

            page_token = data.get("nextPageToken")
            if not page_token:
                break

            # Google requires a short delay before a page token becomes valid.
            time.sleep(settings.scraper_request_delay_seconds)

        logger.info("google_places_api: %s leads for %r", len(leads), full_query)
        return leads[:max_results]

    @staticmethod
    def _to_raw_lead(place: dict, query: str, city: str, area: str | None = None) -> RawLead:
        location = place.get("location", {})
        return RawLead(
            business_name=place.get("displayName", {}).get("text", "Unknown"),
            city=city,
            locality=area,
            phone=place.get("nationalPhoneNumber"),
            website=place.get("websiteUri"),
            address=place.get("formattedAddress"),
            latitude=location.get("latitude"),
            longitude=location.get("longitude"),
            industry=query,
            source="google_places_api",
            google_maps_id=place.get("id"),
            google_rating=place.get("rating"),
            review_count=place.get("userRatingCount"),
            extra={
                "business_status": place.get("businessStatus"),
                "primary_type": place.get("primaryType"),
            },
        )

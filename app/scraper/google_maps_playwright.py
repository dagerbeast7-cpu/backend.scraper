from __future__ import annotations

import logging
import re
import time

from playwright.sync_api import Page, sync_playwright

from app.config import settings
from app.scraper.base import RawLead, ScraperProvider, build_location_query

logger = logging.getLogger(__name__)

PHONE_RE = re.compile(r"[\+\d][\d\s\-\(\)]{7,}\d")


class GoogleMapsPlaywrightProvider(ScraperProvider):
    """
    Free, no-API-key scraper that drives a real browser against the
    Google Maps web UI.

    IMPORTANT: scraping Google Maps this way is against Google's Terms of
    Service, is fragile (breaks whenever Google changes its markup), and
    can get the source IP rate-limited or blocked. Use this only for
    low-volume prototyping. For anything production-grade, switch
    SCRAPER_PROVIDER to google_places (see google_places_api.py), which is
    the same underlying data via an official, ToS-compliant API.
    """

    name = "google_maps_playwright"

    def search(
        self, query: str, city: str, max_results: int = 60, area: str | None = None
    ) -> list[RawLead]:
        full_query = build_location_query(query, city, area)
        leads: list[RawLead] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=settings.scraper_headless)
            page = browser.new_page(locale="en-US")
            try:
                page.goto(
                    f"https://www.google.com/maps/search/{full_query.replace(' ', '+')}",
                    timeout=30000,
                )
                page.wait_for_timeout(3000)
                self._scroll_results(page, max_results)
                cards = page.locator("div.Nv2PK").all()

                for card in cards[:max_results]:
                    try:
                        lead = self._parse_card(card, query, city, area, full_query)
                        if lead:
                            leads.append(lead)
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("Failed to parse a result card: %s", exc)

                    time.sleep(settings.scraper_request_delay_seconds / 5)
            finally:
                browser.close()

        logger.info("google_maps_playwright: %s leads for %r", len(leads), full_query)
        return leads

    @staticmethod
    def _scroll_results(page: Page, target_count: int) -> None:
        feed = page.locator('div[role="feed"]')
        for _ in range(20):
            count = page.locator("div.Nv2PK").count()
            if count >= target_count:
                break
            feed.evaluate("(el) => el.scrollBy(0, 1200)")
            page.wait_for_timeout(1200)

    @staticmethod
    def _parse_card(
        card, query: str, city: str, area: str | None, full_query: str
    ) -> RawLead | None:
        name_el = card.locator(".qBF1Pd").first
        if not name_el.count():
            return None
        name = name_el.inner_text().strip()

        text = card.inner_text()
        phone_match = PHONE_RE.search(text)
        phone = phone_match.group(0).strip() if phone_match else None

        rating = None
        rating_el = card.locator(".MW4etd").first
        if rating_el.count():
            try:
                rating = float(rating_el.inner_text().strip())
            except ValueError:
                rating = None

        reviews = None
        reviews_el = card.locator(".UY7F9").first
        if reviews_el.count():
            digits = re.sub(r"[^\d]", "", reviews_el.inner_text())
            reviews = int(digits) if digits else None

        website = None
        website_el = card.locator('a[data-value="Website"]').first
        if website_el.count():
            website = website_el.get_attribute("href")

        # Extract address from the card's info divs.  Google Maps result
        # cards render multiple `.W4Efsd` elements; the address line is
        # typically inside a nested span within one of these.  We look
        # for the first span text that looks like an address (contains a
        # comma or the city name) and isn't just the category label.
        address = None
        try:
            info_spans = card.locator(".W4Efsd span").all()
            non_address_keywords = [
                "open", "closed", "closes", "opens", "review",
                "years in business", "rating", "star", "website",
                "directions", "call", "appointment"
            ]
            for span in info_spans:
                span_text = span.inner_text().strip()
                # Skip very short / category-like texts
                if len(span_text) < 8:
                    continue
                # Skip lines that are just numbers/ratings
                if span_text.replace(".", "").replace(",", "").isdigit():
                    continue
                # Skip status / operational metadata strings
                lower_text = span_text.lower()
                if any(kw in lower_text for kw in non_address_keywords):
                    continue
                # An address usually contains a comma or the city name
                if "," in span_text or (city and city.lower() in lower_text):
                    address = span_text
                    break
        except Exception:  # noqa: BLE001
            pass

        return RawLead(
            business_name=name,
            city=city,
            locality=area,
            phone=phone,
            website=website,
            address=address,
            industry=query,
            source="google_maps_playwright",
            source_url=full_query,
            google_rating=rating,
            review_count=reviews,
        )

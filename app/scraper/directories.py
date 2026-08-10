from __future__ import annotations

import logging

import httpx
from bs4 import BeautifulSoup

from app.scraper.base import RawLead, ScraperProvider

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


class DirectoryProvider(ScraperProvider):
    """
    Generic scraper for business-directory style sites (JustDial, IndiaMART,
    Sulekha, 99acres agent listings, etc). Each site has different markup,
    so this class takes a small "site profile" describing how to find
    listing cards and fields on the page, rather than hard-coding one site.

    NOTE: selectors below are placeholders/examples. Real directory sites
    change markup often and may block scraping via ToS -- verify each
    target site's terms before pointing this at it in production, and
    prefer sites that expose a partner/data API where available.
    """

    name = "directory"

    def __init__(self, site_name: str, search_url_template: str, selectors: dict):
        self.site_name = site_name
        self.search_url_template = search_url_template
        self.selectors = selectors

    def search(
        self, query: str, city: str, max_results: int = 60, area: str | None = None
    ) -> list[RawLead]:
        # Most directory search URLs are keyed on city, not sub-locality --
        # area (if given) is folded into the query text instead, then used
        # to tag results for downstream filtering.
        search_query = f"{query} {area}" if area else query
        url = self.search_url_template.format(
            query=search_query.replace(" ", "+"), city=city.replace(" ", "+")
        )
        leads: list[RawLead] = []

        with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=20, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            cards = soup.select(self.selectors["card"])
            for card in cards[:max_results]:
                name = self._text(card, self.selectors.get("name"))
                if not name:
                    continue
                leads.append(
                    RawLead(
                        business_name=name,
                        city=city,
                        locality=area,
                        phone=self._text(card, self.selectors.get("phone")),
                        website=self._attr(card, self.selectors.get("website"), "href"),
                        address=self._text(card, self.selectors.get("address")),
                        industry=query,
                        source=self.site_name,
                        source_url=url,
                        business_description=self._text(card, self.selectors.get("description")),
                    )
                )

        logger.info("%s: %s leads for %r in %r", self.site_name, len(leads), query, city)
        return leads

    @staticmethod
    def _text(card, selector: str | None) -> str | None:
        if not selector:
            return None
        el = card.select_one(selector)
        return el.get_text(strip=True) if el else None

    @staticmethod
    def _attr(card, selector: str | None, attr: str) -> str | None:
        if not selector:
            return None
        el = card.select_one(selector)
        return el.get(attr) if el else None


# Example site profiles -- update selectors after inspecting the live markup
# of each target directory before use.
SITE_PROFILES: dict[str, dict] = {
    "justdial": {
        "search_url_template": "https://www.justdial.com/{city}/{query}",
        "selectors": {
            "card": "li.cntanr",
            "name": "span.lng_cont_name",
            "phone": "span.tel_cont",
            "website": "a.website_link",
            "address": "span.cont_fl_addr",
            "description": None,
        },
    },
}

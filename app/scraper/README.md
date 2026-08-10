# 🕷️ Scraper Engine Module (`app/scraper/`)

This directory contains the core scraper interfaces and providers (Playwright browser automation & Google Places API).

---

## 📁 File Manifest & Responsibilities

### 1. `google_maps_playwright.py`
* **Purpose**: Free browser-automation scraper against Google Maps UI using Playwright.
* **Key Components**:
  * `GoogleMapsPlaywrightProvider.search()`: Launches headless Chromium, constructs query, scrolls result feed, and parses cards.
  * `_parse_card()`: Extracts name, phone, address (with status noise filtering), rating, reviews, and website URL. Returns `RawLead`.

### 2. `base.py`
* **Purpose**: Abstract base classes, common dataclasses, and query building logic.
* **Key Components**:
  * `RawLead`: Standardized dataclass output shape.
  * `ScraperProvider`: Abstract base class interface.
  * `build_location_query(query, city, area)`: Formats query string (e.g. `"real estate broker in Bandra West, Mumbai"`).
  * `PHASE_1_ICP_QUERIES`: Real estate search terms.
  * `NIGHTLY_SCHEDULE_TARGETS`: Target micro-markets matrix for Delhi NCR, Mumbai, and Bangalore.

### 3. `factory.py`
* **Purpose**: Factory pattern loader for selecting scraper backend (`playwright` vs `google_places`).

### 4. `google_places_api.py`
* **Purpose**: Official, ToS-compliant Google Places API (New) provider (used if `SCRAPER_PROVIDER=google_places`).

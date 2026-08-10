# 🚀 LeadZen Prospect Pipeline — Product & Architecture Overview

LeadZen Prospect Pipeline is an automated, zero-API-cost lead generation, enrichment, scoring, and cold calling management system tailored for Indian Real Estate businesses (Brokers, Property Consultants, Real Estate Agencies, Small Builders, and Real Estate Developers).

---

## 🏗️ System Architecture

```
                    ┌─────────────────────────────────────────┐
                    │          Google Maps (Free UI)          │
                    └────────────────────┬────────────────────┘
                                         │
                                         ▼
                     ┌──────────────────────────────────────┐
                     │ Playwright Browser Scraper           │
                     │ (Extracts Business, Phone, Address)  │
                     └───────────────────┬──────────────────┘
                                         │
                                         ▼
                     ┌──────────────────────────────────────┐
                     │ Deduplication Engine                 │
                     │ (Normalizes phone, cleans names,     │
                     │  prevents duplicate DB records)      │
                     └───────────────────┬──────────────────┘
                                         │
                                         ▼
                     ┌──────────────────────────────────────┐
                     │ Deep Website Enrichment Service      │
                     │ (Crawls website, extracts email/     │
                     │  WhatsApp, DNS MX check, AI Broker)  │
                     └───────────────────┬──────────────────┘
                                         │
                                         ▼
                     ┌──────────────────────────────────────┐
                     │ Lead Quality Scoring Engine (0-100)  │
                     └───────────────────┬──────────────────┘
                                         │
                                         ▼
                     ┌──────────────────────────────────────┐
                     │ PostgreSQL Database (600+ Leads)     │
                     └─────────┬──────────────────┬─────────┘
                               │                  │
                               ▼                  ▼
┌────────────────────────────────────────┐ ┌─────────────────────────────────────┐
│ Next.js Interactive Sales Dashboard    │ │ Hourly Excel Exporter & Importer    │
│ (http://localhost:3000)                │ │ (exports/leadzen_prospects.xlsx)    │
└────────────────────────────────────────┘ └─────────────────────────────────────┘
```

---

## ✨ Key Features & Capabilities

### 1. Free Google Maps Scraping (Playwright)
* **Zero API Cost**: Drives a headless Chromium browser using Playwright against Google Maps.
* **Rich Extractions**: Extracts Business Name, Phone Number, Full Address, Locality/Area, Google Rating, Review Count, and Website URL.
* **Micro-Market Locality Scoping**: Constructs area-specific searches (e.g. `"real estate broker in Bandra West, Mumbai"`) to zoom into specific neighborhoods rather than generic city results.

### 2. Smart Deduplication Engine (`DedupEngine`)
* Uses a 4-tier match strategy:
  1. **Phone Number**: Normalized to international E.164 format (`+91...`).
  2. **Website Domain**: Strips `www.`, subdomains, and URL schemes.
  3. **Fuzzy Business Name + City**: Token sort ratio > 93% paired with industry protection.
  4. **Google Maps Place ID**.
* Cleans SEO clutter from business names (e.g., `"Sharma Realty | Best Brokers in Delhi 🏆"` → `"Sharma Realty"`).

### 3. Website Crawling & AI Contact Name Enrichment (`EnrichmentService`)
* **Email Scraping & Verification**: Extracts `mailto:` links & regex matches, filters out junk/placeholder domains (`example.com`, `sentry.io`, `squarespace.com`), and validates domain mailboxes via live **DNS MX record checks**.
* **WhatsApp Detection**: Identifies confirmed `wa.me/` links on websites, or falls back to inferred WhatsApp on valid mobile numbers.
* **AI/LLM Contact Extraction**: Uses OpenRouter (NVIDIA Nemotron LLM) to read website text and extract:
  * **Contact / Broker Name** (Owner, Founder, Director name)
  * **Business Description** (Concise summary)
  * **Company Size Estimate** (`1-10`, `11-50`, `51-200`, `201+`)

### 4. Automated 8:00 PM – 6:00 AM IST Night Scraper
* **Non-Disruptive Workday**: Callers operate from 9:00 AM to 7:00 PM IST. During the day, no heavy scraping runs.
* **Night Schedule (Celery Beat)**:
  * **08:00 PM IST**: Delhi NCR (Gurgaon, Noida, Greater Noida, Faridabad, Delhi)
  * **11:30 PM IST**: Mumbai (Bandra West, Andheri West, Thane West, Navi Mumbai, Mumbai Central)
  * **02:30 AM IST**: Bangalore (Indiranagar, Koramangala, Whitefield, HSR Layout, Electronic City)
  * **06:00 AM IST**: Morning Excel export generated ready for 9:00 AM callers.

### 5. Interactive Excel Exporter & Importer
* **Native Excel Dropdowns**: The exported `.xlsx` file embeds Excel DataValidation dropdown menus in Column `K` (**Status**) for calling team options:
  * `NOT_CONTACTED` (Haven't called)
  * `MAYBE` (Needs convincing)
  * `CONVERTED` (Agreed to buy)
  * `LOST` (Cannot convert)
* **Two-Way Excel Import**: Callers can edit statuses or broker names in Excel and upload the sheet back to the dashboard via `📤 Import Excel` to sync all changes to PostgreSQL.

---

## 🎯 Lead Quality Scoring Rules (0 – 100 Points)

| Feature | Points | Description |
|---|:---:|---|
| **WhatsApp Available** | **+30 pts** | Direct messaging channel |
| **Verified Phone Number** | **+20 pts** | Valid E.164 phone line |
| **Email Address Present** | **+20 pts** | MX-verified email domain |
| **Website Available** | **+15 pts** | Digital presence confirmed |
| **Active Business Status** | **+15 pts** | Verified operational on Maps |
| **Recently Updated (< 30 days)** | **+10 pts** | Fresh data signal |

*(Clamped to maximum score of **100**)*

---

## 🛠️ Stack & Infrastructure

* **Backend**: Python 3.10, FastAPI, SQLAlchemy 2.0, Celery 5.4, OpenPyXL, RapidFuzz, Playwright
* **Database**: PostgreSQL 16 (Native UUIDs, indexes on phone/city/score/status)
* **Task Broker & Cache**: Redis 7
* **Frontend**: Next.js 14, TypeScript, Vanilla CSS
* **Orchestration**: Docker & Docker Compose

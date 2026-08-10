# 🌐 Website Enrichment & AI Module (`app/enrichment/`)

This directory contains deep web crawling logic, email MX verification, social link extraction, and OpenRouter AI integration for broker contact name extraction.

---

## 📁 File Manifest & Responsibilities

### 1. `service.py`
* **Purpose**: Defines `EnrichmentService` which visits business websites and enriches leads.
* **Key Operations**:
  * **Subpage Crawling**: Visits homepage, `/contact`, `/contact-us`, `/about`, and `/about-us`.
  * **Email Scraping**: Extracts `mailto:` links and email regex patterns.
  * **Junk Domain Filter (`_is_junk_email`)**: Filters out placeholder/template emails (`example.com`, `sentry.io`, `squarespace.com`, `godaddy.com`, `schema.org`).
  * **DNS MX Verification (`_has_mx_record`)**: Performs live DNS lookup to confirm the domain has active mail servers.
  * **WhatsApp Chat Extraction**: Scrapes `wa.me/` or `api.whatsapp.com` links to mark WhatsApp as `confirmed`.
  * **AI LLM Extraction (OpenRouter - NVIDIA Nemotron)**: Sends website text to OpenRouter AI to extract:
    * `contact_name`: Owner, founder, or main broker's full name.
    * `description`: Concise 1-2 sentence business description.
    * `company_size`: Employee range (`1-10`, `11-50`, `51-200`, `201+`).

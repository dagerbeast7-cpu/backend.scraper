# 🔍 Deduplication Engine (`app/dedup/`)

This directory contains lead normalization, business name cleaning, phone structure verification, and deduplication logic.

---

## 📁 File Manifest & Responsibilities

### 1. `engine.py`
* **Purpose**: Core deduplication class `DedupEngine` and normalization utility functions.
* **Key Functions & Classes**:
  * `DedupEngine.find_existing(lead)`: Searches database using 4-tier match strategy:
    1. Phone Number (`Prospect.phone == phone`)
    2. Website domain (`Prospect.website LIKE %domain%`)
    3. Fuzzy Business Name + City (`fuzz.token_sort_ratio >= 93%` paired with `_industries_conflict` guard)
    4. Google Maps Place ID (`Prospect.google_maps_id == id`)
  * `DedupEngine.upsert(lead)`: Updates existing records with new data (without clobbering existing good fields) or inserts a new `Prospect` entity.
  * `clean_business_name(raw)`: Strips emojis, dingbats, repeated punctuation ("BEST DEALS!!!"), and SEO tails after pipes (`Sharma Realty | Best Agent` → `Sharma Realty`).
  * `normalize_phone(raw, region="IN")`: Parses and validates phone numbers using Google's `phonenumbers` library into E.164 format (`+91...`).
  * `is_mobile_number(e164_phone)`: Checks if a phone line is mobile (plausible WhatsApp candidate).
  * `combine_verification(...)`: Rollup status logic for phone and email verification flags.

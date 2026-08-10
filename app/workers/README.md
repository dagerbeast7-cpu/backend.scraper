# ⚙️ Celery Workers & Exporter Module (`app/workers/`)

This directory manages background task processing, Celery Beat task scheduling, and Excel file generation/importing.

---

## 📁 File Manifest & Responsibilities

### 1. `celery_app.py`
* **Purpose**: Celery app instance configuration and Beat schedule definitions.
* **Beat Schedules (Asia/Kolkata timezone)**:
  * `nightly-delhi-ncr-scrape`: 8:00 PM IST daily (`run_nightly_region_scrape("delhi_ncr")`)
  * `nightly-mumbai-scrape`: 11:30 PM IST daily (`run_nightly_region_scrape("mumbai")`)
  * `nightly-bangalore-scrape`: 2:30 AM IST daily (`run_nightly_region_scrape("bangalore")`)
  * `morning-final-excel-export`: 6:00 AM IST daily (`export_prospects_to_excel()`)
  * `hourly-excel-export`: Every hour on the hour

### 2. `tasks.py`
* **Purpose**: Celery task definitions.
* **Key Tasks**:
  * `run_scrape_pipeline()`: End-to-end pipeline for a single city/area (scrape → dedup → enrich → score → DB commit). Wrapped with `session.rollback()` transaction safeguards.
  * `run_nightly_region_scrape()`: Executes batch scraping across target micro-market localities for a region.
  * `export_prospects_to_excel()`: Queries all prospects ordered by score descending, builds a styled `.xlsx` workbook in `/code/exports/leadzen_prospects.xlsx`, embeds openpyxl `DataValidation` dropdown list on Column K (`NOT_CONTACTED`, `MAYBE`, `CONVERTED`, `LOST`), and saves to disk.

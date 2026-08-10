# 🔌 API Module (`app/api/`)

This directory contains the FastAPI application setup, router declarations, schema models, and endpoint handlers.

---

## 📁 File Manifest & Responsibilities

### 1. `main.py`
* **Purpose**: Application entry point. Initializes FastAPI instance, configures CORS middleware (`CORSMiddleware`), hooks database table auto-creation on startup (`on_startup`), and mounts route handlers.
* **Key Components**:
  * `app = FastAPI(...)`
  * `/health` healthcheck endpoint.
  * Includes `prospects_router` and `stats_router`.

### 2. `routes_prospects.py`
* **Purpose**: Handlers for all `/prospects` endpoints.
* **Key Handlers**:
  * `list_prospects()`: Filtering by city, locality, status, score, industry, email/whatsapp/website flags.
  * `get_prospect()`: Fetch single prospect by UUID.
  * `update_status()`: Update status to `NOT_CONTACTED`, `MAYBE`, `CONVERTED`, `LOST`.
  * `trigger_scrape()`: Spawns background Celery task `run_scrape_pipeline.delay()`.
  * `trigger_export()`: Spawns background task `export_prospects_to_excel.delay()`.
  * `download_export()`: Serves `exports/leadzen_prospects.xlsx` (auto-generates if missing).
  * `import_excel()`: Parses uploaded `.xlsx` files and syncs statuses back to Postgres.

### 3. `routes_stats.py`
* **Purpose**: Aggregates statistical metrics for the dashboard KPI cards.
* **Key Handler**:
  * `get_stats()`: Computes total prospect count, status distribution, industry breakdown, city counts, average score, and coverage percentages (email, website, whatsapp).

### 4. `schemas.py`
* **Purpose**: Pydantic data models for request validation and response serialization.
* **Key Models**:
  * `ProspectOut`: Output schema for prospect API responses (includes `address`, `contact_name`, `score`, etc.).
  * `ProspectStatusUpdate`: Schema for updating status.
  * `ScrapeJobRequest` & `ScrapeJobResponse`: Trigger job parameters.
  * `StatsOut`: Statistical summary model.

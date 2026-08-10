# 📡 LeadZen Scraper API Documentation

Base URL: `http://localhost:8000` (or your production server domain)  
Interactive OpenAPI Docs: `http://localhost:8000/docs`

---

## 📑 Summary of Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Server health check endpoint |
| `GET` | `/stats` | Aggregated prospect pipeline statistics & coverage ratios |
| `GET` | `/prospects` | List & filter prospects with pagination |
| `GET` | `/prospects/{id}` | Get a single prospect by UUID |
| `PATCH` | `/prospects/{id}/status` | Update caller status (`NOT_CONTACTED`, `MAYBE`, `CONVERTED`, `LOST`) |
| `POST` | `/prospects/scrape` | Trigger an asynchronous background scrape job |
| `POST` | `/prospects/export` | Trigger an asynchronous Excel file export |
| `GET` | `/prospects/export/download` | Download latest Excel sheet (auto-generates if missing) |
| `POST` | `/prospects/import-excel` | Upload edited Excel sheet to sync status updates to DB |

---

## 🔍 Detailed Endpoint Documentation

### 1. `GET /health`
* **Description**: Simple health check to verify backend server availability.
* **Response `200 OK`**:
  ```json
  { "status": "ok" }
  ```

---

### 2. `GET /stats`
* **Description**: Returns overall pipeline statistics, industry breakdowns, city totals, score averages, and data quality coverage metrics (email %, website %, WhatsApp %).
* **Response `200 OK`**:
  ```json
  {
    "total_prospects": 607,
    "by_status": { "NOT_CONTACTED": 593, "MAYBE": 10, "CONVERTED": 4, "LOST": 0 },
    "by_industry": { "real estate broker": 180, "property consultant": 150, "small builder": 180 },
    "by_city": { "Delhi": 226, "mumbai": 191, "jaipur": 190 },
    "avg_score": 40.4,
    "high_quality_count": 10,
    "email_coverage_pct": 33.6,
    "website_coverage_pct": 65.6,
    "whatsapp_coverage_pct": 43.7,
    "whatsapp_confirmed_count": 0,
    "whatsapp_inferred_count": 13,
    "verification_breakdown": { "UNVERIFIED": 607 }
  }
  ```

---

### 3. `GET /prospects`
* **Description**: Query and filter the prospect list ordered by score descending.
* **Query Parameters**:
  * `city` (string, optional): Filter by city name (e.g. `Mumbai`)
  * `locality` (string, optional): Filter by area/locality (e.g. `Bandra West`)
  * `industry` (string, optional): Filter by industry keyword
  * `status` (string, optional): `NOT_CONTACTED`, `MAYBE`, `CONVERTED`, `LOST`
  * `min_score` (int, 0-100, optional): Minimum score threshold
  * `has_email` (bool, optional): `true`/`false`
  * `has_whatsapp` (bool, optional): `true`/`false`
  * `has_website` (bool, optional): `true`/`false`
  * `limit` (int, default 50, max 500)
  * `offset` (int, default 0)
* **Response `200 OK`**: Array of `ProspectOut` objects.

---

### 4. `GET /prospects/{prospect_id}`
* **Description**: Fetch details for a specific prospect UUID.
* **Response `200 OK`**: Single `ProspectOut` object.
* **Errors**: `404 Not Found` if UUID does not exist.

---

### 5. `PATCH /prospects/{prospect_id}/status`
* **Description**: Update the status of a prospect (used by callers on the dashboard).
* **Request Body**:
  ```json
  { "status": "MAYBE" }
  ```
  *(Valid values: `NOT_CONTACTED`, `MAYBE`, `CONVERTED`, `LOST`)*
* **Response `200 OK`**: Updated `ProspectOut` object.

---

### 6. `POST /prospects/scrape`
* **Description**: Queue an asynchronous Celery scraping job for a city and area.
* **Request Body**:
  ```json
  {
    "city": "Mumbai",
    "area": "Bandra West",
    "max_results_per_query": 40
  }
  ```
* **Response `202 Accepted`**:
  ```json
  {
    "task_id": "57e4e54c-d4d8-4f7f-b094-0a18743d0ffd",
    "city": "Mumbai",
    "area": "Bandra West",
    "queries": ["real estate broker", "property consultant", "real estate agency", "small builder", "real estate developer"]
  }
  ```

---

### 7. `POST /prospects/export`
* **Description**: Trigger an immediate background task to generate/refresh `exports/leadzen_prospects.xlsx`.
* **Response `202 Accepted`**:
  ```json
  {
    "task_id": "dadee51e-3346-4ce7-aa83-2f8d71263170",
    "message": "Excel export started"
  }
  ```

---

### 8. `GET /prospects/export/download`
* **Description**: Download the formatted Excel file (`leadzen_prospects.xlsx`). If the file doesn't exist, it automatically generates it on-the-fly.
* **Response `200 OK`**: Binary File stream (`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`).

---

### 9. `POST /prospects/import-excel`
* **Description**: Upload an edited Excel file from a caller to sync status updates and contact names back to the database.
* **Form Field**: `file` (Multipart file upload `.xlsx`)
* **Response `200 OK`**:
  ```json
  {
    "updated": 15,
    "message": "Successfully updated 15 prospect statuses from Excel"
  }
  ```

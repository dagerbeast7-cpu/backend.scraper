# LeadZen Internal Scraper

Internal growth-engine pipeline: scrape Phase 1 ICP businesses (real estate
brokers, property consultants, agencies, small builders) → dedupe → enrich →
score → serve through an API + dashboard, ready to feed LeadZen's outreach.

Architecture matches the project spec: Scraper Workers (Celery) → Postgres →
Dedup → Enrichment → Scoring → FastAPI → Next.js dashboard.

```
leadzen-scraper/
  app/
    scraper/       # Google Places API, Playwright (Maps), directory scrapers
    dedup/         # phone -> website -> name+city -> google_maps_id merge logic
    enrichment/    # website crawl for email / WhatsApp / socials
    scoring/       # 0-100 lead score
    api/           # FastAPI: /prospects, /stats, /prospects/scrape
    workers/       # Celery app + nightly beat schedule
    db/            # SQLAlchemy models (Prospects table)
  dashboard/       # Next.js + TS: prospect table, filters, stats
  docker-compose.yml
  Dockerfile
```

## 1. Quick start (Docker)

```bash
cp .env.example .env
# edit .env: set SCRAPER_PROVIDER and (if using Places) GOOGLE_PLACES_API_KEY

docker compose up --build
```

This starts Postgres, Redis, the FastAPI API (`:8000`), a Celery worker, and
a Celery beat scheduler (nightly scrape at 2am IST, see
`app/workers/celery_app.py`).

Trigger a scrape manually:

```bash
curl -X POST http://localhost:8000/prospects/scrape \
  -H "Content-Type: application/json" \
  -d '{"city": "Delhi"}'
```

Then browse results:

```bash
curl "http://localhost:8000/prospects?city=Delhi&min_score=50&has_whatsapp=true"
curl "http://localhost:8000/stats"
```

## 2. Dashboard

```bash
cd dashboard
cp .env.local.example .env.local
npm install
npm run dev
```

Open http://localhost:3000 — table of prospects with filters (city,
industry, status, min score, WhatsApp), summary stats, and a "trigger scrape"
box.

## 3. Choosing a scraper provider

Set `SCRAPER_PROVIDER` in `.env`:

- **`google_places`** (recommended for anything beyond prototyping): uses
  Google's official Places API. Costs money per request, but is reliable,
  ToS-compliant, and won't get you IP-blocked. Needs `GOOGLE_PLACES_API_KEY`
  from Google Cloud Console (enable "Places API (New)").
- **`playwright`** (default, free): drives a real Chromium browser against
  the Google Maps web UI. No API key needed, but this **violates Google's
  Terms of Service**, is fragile (breaks whenever Google changes its
  markup), and can get your IP rate-limited. Fine for a small first test
  batch; don't run this at scale or continuously.

`app/scraper/directories.py` has a generic framework plus a JustDial example
profile for pulling from business directories instead of / alongside Google
Maps — selectors are placeholders and need updating against the live site
before use.

## 4. Pipeline logic

- **Dedup** (`app/dedup/engine.py`): matches in priority order phone →
  website → business name+city (fuzzy, rapidfuzz) → google_maps_id, per the
  spec. Existing records are filled in, never overwritten with blanks.
- **Enrichment** (`app/enrichment/service.py`): crawls the business website
  (+ `/contact`, `/about`) for email, `wa.me` WhatsApp links, and social
  profiles.
- **Scoring** (`app/scoring/engine.py`): website +15, email +20, whatsapp
  +30, phone verified +20, active +15, recently updated +10, capped at 100.

## 5. Important: compliance before you send outreach

This scraper itself (collecting public business info) is common practice
for B2B lead gen. The parts that carry real legal risk are downstream, once
you start messaging these leads — worth checking before Phase 1's "mass
email / WhatsApp campaign" step goes live:

- **WhatsApp**: bulk/automated outreach to numbers that haven't opted in
  can get your WhatsApp Business number banned, and unsolicited commercial
  messages are regulated in India under TRAI's rules on Unsolicited
  Commercial Communication (UCC) and the DND registry.
- **Email**: India's IT Act and (for any EU contacts) GDPR, plus CAN-SPAM if
  you ever reach US businesses, all require a working unsubscribe and
  accurate sender info at minimum.
- **Scraping Google Maps directly** (the Playwright provider) is against
  Google's Terms of Service. It's a common gray-area practice, not
  something with clear case law establishing it as illegal, but it's a ToS
  violation, not a compliance-clean approach — the Places API path avoids
  this entirely.

None of this blocks building/running the scraper — just worth having sign-off
on the outreach side before Phase 1 fully goes live.

## 6. What's not built yet

- Alembic migrations (currently `Base.metadata.create_all` on startup —
  fine for now, switch to Alembic before your schema needs real migrations).
- Real firmographic enrichment (company size is a rough heuristic placeholder).
- Auth on the API/dashboard (currently open — add before deploying anywhere
  non-local).
- Directory scraper selectors are examples only; verify against live site
  markup.

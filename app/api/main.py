from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_prospects import router as prospects_router
from app.api.routes_stats import router as stats_router
from app.db.base import init_db

app = FastAPI(title="LeadZen Internal Scraper API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten before exposing beyond localhost
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(prospects_router)
app.include_router(stats_router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}

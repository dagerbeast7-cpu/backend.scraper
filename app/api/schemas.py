from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProspectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_name: str
    contact_name: Optional[str] = None
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    whatsapp_source: Optional[str] = None  # 'confirmed' (wa.me link) | 'inferred' (from phone)
    email: Optional[str] = None
    website: Optional[str] = None
    city: Optional[str] = None
    locality: Optional[str] = None
    address: Optional[str] = None
    state: Optional[str] = None
    industry: Optional[str] = None
    business_description: Optional[str] = None
    source: Optional[str] = None
    google_rating: Optional[float] = None
    review_count: Optional[int] = None
    status: str
    score: int
    verification_status: str
    created_at: datetime
    updated_at: datetime


class ProspectStatusUpdate(BaseModel):
    status: str


class ScrapeJobRequest(BaseModel):
    city: str
    area: Optional[str] = None  # narrow to a neighbourhood/locality within the city, e.g. "Bandra West"
    queries: Optional[list[str]] = None  # defaults to PHASE_1_ICP_QUERIES
    max_results_per_query: int = 60
    provider: Optional[str] = None  # overrides SCRAPER_PROVIDER for this job


class ScrapeJobResponse(BaseModel):
    task_id: str
    city: str
    area: Optional[str] = None
    queries: list[str]


class StatsOut(BaseModel):
    total_prospects: int
    by_status: dict[str, int]
    by_industry: dict[str, int]
    by_city: dict[str, int]
    avg_score: float
    high_quality_count: int  # score > 80

    # Data-quality signals -- so quality is measured every scrape, not
    # assumed. Coverage = % of prospects with that field populated.
    email_coverage_pct: float
    website_coverage_pct: float
    whatsapp_coverage_pct: float
    whatsapp_confirmed_count: int  # found via wa.me link on the site
    whatsapp_inferred_count: int  # guessed from the verified mobile number
    verification_breakdown: dict[str, int]

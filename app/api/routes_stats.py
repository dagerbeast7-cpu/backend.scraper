from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.routes_prospects import get_db
from app.api.schemas import StatsOut
from app.db.models import Prospect

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=StatsOut)
def get_stats(db: Session = Depends(get_db)):
    total = db.execute(select(func.count(Prospect.id))).scalar_one()

    by_status = dict(
        db.execute(select(Prospect.status, func.count(Prospect.id)).group_by(Prospect.status)).all()
    )
    by_status = {k.value if hasattr(k, "value") else k: v for k, v in by_status.items()}

    by_industry = dict(
        db.execute(
            select(Prospect.industry, func.count(Prospect.id))
            .where(Prospect.industry.isnot(None))
            .group_by(Prospect.industry)
        ).all()
    )

    by_city = dict(
        db.execute(
            select(Prospect.city, func.count(Prospect.id))
            .where(Prospect.city.isnot(None))
            .group_by(Prospect.city)
        ).all()
    )

    avg_score = db.execute(select(func.coalesce(func.avg(Prospect.score), 0))).scalar_one()
    high_quality = db.execute(
        select(func.count(Prospect.id)).where(Prospect.score > 80)
    ).scalar_one()

    def pct(count_stmt) -> float:
        if not total:
            return 0.0
        count = db.execute(count_stmt).scalar_one()
        return round(100 * count / total, 1)

    email_coverage = pct(select(func.count(Prospect.id)).where(Prospect.email.isnot(None)))
    website_coverage = pct(select(func.count(Prospect.id)).where(Prospect.website.isnot(None)))
    whatsapp_coverage = pct(select(func.count(Prospect.id)).where(Prospect.whatsapp.isnot(None)))

    whatsapp_confirmed = db.execute(
        select(func.count(Prospect.id)).where(Prospect.whatsapp_source == "confirmed")
    ).scalar_one()
    whatsapp_inferred = db.execute(
        select(func.count(Prospect.id)).where(Prospect.whatsapp_source == "inferred")
    ).scalar_one()

    verification_breakdown = dict(
        db.execute(
            select(Prospect.verification_status, func.count(Prospect.id)).group_by(
                Prospect.verification_status
            )
        ).all()
    )
    verification_breakdown = {
        k.value if hasattr(k, "value") else k: v for k, v in verification_breakdown.items()
    }

    return StatsOut(
        total_prospects=total,
        by_status=by_status,
        by_industry=by_industry,
        by_city=by_city,
        avg_score=round(float(avg_score), 1),
        high_quality_count=high_quality,
        email_coverage_pct=email_coverage,
        website_coverage_pct=website_coverage,
        whatsapp_coverage_pct=whatsapp_coverage,
        whatsapp_confirmed_count=whatsapp_confirmed,
        whatsapp_inferred_count=whatsapp_inferred,
        verification_breakdown=verification_breakdown,
    )

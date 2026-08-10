from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.db.models import Prospect

# Point values straight from the project spec.
POINTS = {
    "website": 15,
    "email": 20,
    "whatsapp": 30,
    "phone_verified": 20,
    "business_active": 15,
    "recently_updated": 10,
}
MAX_SCORE = sum(POINTS.values())  # 110 -> clamp to 100 below
RECENT_WINDOW_DAYS = 30


def score_prospect(prospect: Prospect) -> int:
    total = 0

    if prospect.website:
        total += POINTS["website"]
    if prospect.email:
        total += POINTS["email"]
    if prospect.whatsapp:
        total += POINTS["whatsapp"]
    if prospect.phone and prospect.verification_status.value in (
        "PHONE_VERIFIED",
        "FULLY_VERIFIED",
    ):
        total += POINTS["phone_verified"]
    if prospect.is_business_active:
        total += POINTS["business_active"]

    updated_at = prospect.updated_at
    if updated_at:
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - updated_at <= timedelta(days=RECENT_WINDOW_DAYS):
            total += POINTS["recently_updated"]

    return min(total, 100)


def apply_score(prospect: Prospect) -> Prospect:
    prospect.score = score_prospect(prospect)
    return prospect

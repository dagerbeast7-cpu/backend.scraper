"""
Smoke test for the data-quality fixes: name cleaning, dedup false-merge
guard, phone/email verification combining, junk-email filtering, and
whatsapp confirmed-vs-inferred tracking. Synthetic leads only (no network).

    DATABASE_URL=sqlite:////tmp/smoke.db python scripts/smoke_test.py
"""
import sys

sys.path.insert(0, ".")

from app.db.base import Base, engine, get_session, init_db  # noqa: E402
from app.db.models import VerificationStatus  # noqa: E402
from app.dedup.engine import (  # noqa: E402
    DedupEngine,
    clean_business_name,
    combine_verification,
    is_mobile_number,
)
from app.enrichment.service import EMAIL_RE, _is_junk_email  # noqa: E402
from app.scoring.engine import apply_score  # noqa: E402
from app.scraper.base import RawLead  # noqa: E402

failures = []


def check(label, condition):
    status = "OK" if condition else "FAIL"
    print(f"  [{status}] {label}")
    if not condition:
        failures.append(label)


# --- 1. Business name cleaning --------------------------------------------
print("\n1. clean_business_name")
messy = "★★★★★ Sharma Realty!!! | Best Real Estate Agents in Delhi 2026"
cleaned = clean_business_name(messy)
print(f"   {messy!r} -> {cleaned!r}")
check("strips star ratings/emoji", "★" not in cleaned)
check("strips SEO tail after pipe", "Best Real Estate Agents" not in cleaned)
check("keeps the real name", "Sharma Realty" in cleaned)
check("collapses repeated punctuation", "!!!" not in cleaned)

# --- 2. combine_verification -----------------------------------------------
print("\n2. combine_verification")
v1 = combine_verification(VerificationStatus.UNVERIFIED, phone_ok=True)
v2 = combine_verification(v1, email_ok=True)
check("phone alone -> PHONE_VERIFIED", v1 == VerificationStatus.PHONE_VERIFIED)
check("phone + email -> FULLY_VERIFIED", v2 == VerificationStatus.FULLY_VERIFIED)

# --- 3. Junk email filtering -------------------------------------------------
print("\n3. junk email filtering")
fake_html_text = "Contact us at info@sharmarealty.in or see our site built by webmaster@wixpress.com"
found = [e for e in EMAIL_RE.findall(fake_html_text) if not _is_junk_email(e)]
check("keeps the real business email", "info@sharmarealty.in" in found)
check("drops the website-builder email", "webmaster@wixpress.com" not in found)

# --- 4. Dedup: real duplicate still merges, false-merge guard blocks -------
print("\n4. dedup precision")
Base.metadata.drop_all(bind=engine)
init_db()

with get_session() as session:
    dedup = DedupEngine(session)

    # Same business, same phone, different formatting -> should merge.
    p1, c1 = dedup.upsert(RawLead(
        business_name="Sharma Real Estate Consultants",
        city="Delhi", phone="+91 98765 43210", industry="real estate broker",
        source="google_places_api",
    ))
    p2, c2 = dedup.upsert(RawLead(
        business_name="Sharma Real Estate",
        city="Delhi", phone="9876543210", industry="real estate broker",
        source="justdial",
    ))
    check("same phone -> merged into one record", c1 is True and c2 is False and p1.id == p2.id)

    # Similar name, same city, but a DIFFERENT industry and no phone to
    # disambiguate -> must NOT merge (this is the false-merge guard).
    p3, c3 = dedup.upsert(RawLead(
        business_name="Sharma Real Estate",
        city="Delhi", phone=None, industry="small builder",
        source="google_places_api",
    ))
    check("similar name + different industry -> kept separate", c3 is True and p3.id != p1.id)

# --- 5. WhatsApp confirmed vs inferred tracking (mirrors tasks.py) --------
print("\n5. whatsapp source tracking")
with get_session() as session:
    dedup = DedupEngine(session)
    prospect, _ = dedup.upsert(RawLead(
        business_name="Verma Builders",
        city="Mumbai", phone="+91 91234 56789", industry="small builder",
        source="google_places_api", extra={"business_status": "OPERATIONAL"},
    ))
    # No confirmed WhatsApp found by enrichment -> fallback to phone.
    if not prospect.whatsapp and is_mobile_number(prospect.phone):
        prospect.whatsapp = prospect.phone
        prospect.whatsapp_source = "inferred"
    apply_score(prospect)
    check("inferred whatsapp tagged correctly", prospect.whatsapp_source == "inferred")


# --- 6. Area/locality scoping ----------------------------------------------
print("\n6. area/locality scoping")
from app.scraper.base import build_location_query  # noqa: E402

q = build_location_query("real estate broker", "Mumbai", "Bandra West")
check("query embeds area+city", q == "real estate broker in Bandra West, Mumbai")
q_no_area = build_location_query("real estate broker", "Mumbai", None)
check("falls back to city-only when no area given", q_no_area == "real estate broker in Mumbai")

with get_session() as session:
    dedup = DedupEngine(session)
    prospect, _ = dedup.upsert(RawLead(
        business_name="Bandra Realty Hub",
        city="Mumbai", locality="Bandra West", phone="+91 90000 11111",
        industry="real estate broker", source="google_places_api",
    ))
    check("locality persisted on the prospect", prospect.locality == "Bandra West")

print(f"\n{'ALL SMOKE TESTS PASSED' if not failures else f'{len(failures)} CHECK(S) FAILED: ' + ', '.join(failures)}")
sys.exit(1 if failures else 0)

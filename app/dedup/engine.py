from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

import phonenumbers
from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Prospect, VerificationStatus
from app.scraper.base import RawLead

logger = logging.getLogger(__name__)

# Raised from 90 -> 93 and paired with an industry guard (see find_existing)
# after finding that name+city alone was too loose for cities the size of
# Delhi/Mumbai: two unrelated businesses with similar names were at real
# risk of getting merged into one record, silently losing a lead.
NAME_MATCH_THRESHOLD = 93  # rapidfuzz token_sort_ratio, 0-100

# Statuses Google's Places API returns for `businessStatus`.
_ACTIVE_BUSINESS_STATUSES = {"OPERATIONAL"}
_INACTIVE_BUSINESS_STATUSES = {"CLOSED_PERMANENTLY", "CLOSED_TEMPORARILY"}

_DECORATIVE_CHARS_RE = re.compile(
    "[☀-➿\U0001F300-\U0001FAFF⬀-⯿←-⇿]"  # emoji / dingbats / arrows
)
_REPEATED_PUNCT_RE = re.compile(r"([!?*.,\-])\1{1,}")
_WHITESPACE_RE = re.compile(r"\s+")


def clean_business_name(raw: str | None) -> str | None:
    """
    Strips the junk that commonly rides along with a scraped business name:
    star/emoji ratings, repeated punctuation ("BEST DEALS!!!"), and SEO
    tails after a pipe ("Sharma Realty | Best Agents in Delhi 2026").
    Deliberately does NOT touch hyphens/words mid-name (e.g. "A-One
    Builders") to avoid damaging real names.
    """
    if not raw:
        return raw
    name = _DECORATIVE_CHARS_RE.sub("", raw)
    name = name.split("|")[0]
    name = _REPEATED_PUNCT_RE.sub(r"\1", name)
    name = _WHITESPACE_RE.sub(" ", name).strip(" -–—.,!?*")
    return name or raw.strip()


def _industries_conflict(a: str | None, b: str | None) -> bool:
    """
    Soft guard against merging two different businesses that happen to
    share a similar name+city: if both sides have an industry tag and
    share no common word, treat them as different businesses rather than
    merging. Leads with no industry set on either side are never blocked.
    """
    if not a or not b:
        return False
    a_words = set(normalize_name(a).split())
    b_words = set(normalize_name(b).split())
    return a_words.isdisjoint(b_words)


def normalize_phone(raw: str | None, default_region: str = "IN") -> str | None:
    if not raw:
        return None
    try:
        parsed = phonenumbers.parse(raw, default_region)
        if not phonenumbers.is_valid_number(parsed):
            return None
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        return None


def is_mobile_number(e164_phone: str | None) -> bool:
    """
    True if the (already-normalized, E.164) number is a mobile line -- i.e.
    a plausible WhatsApp candidate. Landlines never carry WhatsApp.
    """
    if not e164_phone:
        return False
    try:
        parsed = phonenumbers.parse(e164_phone, None)
    except phonenumbers.NumberParseException:
        return False
    return phonenumbers.number_type(parsed) in (
        phonenumbers.PhoneNumberType.MOBILE,
        phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE,
    )


def business_active_from_status(business_status: str | None) -> bool | None:
    if business_status in _ACTIVE_BUSINESS_STATUSES:
        return True
    if business_status in _INACTIVE_BUSINESS_STATUSES:
        return False
    return None


def combine_verification(
    current: VerificationStatus, *, phone_ok: bool = False, email_ok: bool = False
) -> VerificationStatus:
    """
    Single source of truth for how phone/email verification signals
    (which get discovered at different pipeline stages -- phone in dedup,
    email in enrichment) roll up into one status per prospect.
    """
    has_phone = phone_ok or current in (
        VerificationStatus.PHONE_VERIFIED,
        VerificationStatus.FULLY_VERIFIED,
    )
    has_email = email_ok or current in (
        VerificationStatus.EMAIL_VERIFIED,
        VerificationStatus.FULLY_VERIFIED,
    )
    if has_phone and has_email:
        return VerificationStatus.FULLY_VERIFIED
    if has_phone:
        return VerificationStatus.PHONE_VERIFIED
    if has_email:
        return VerificationStatus.EMAIL_VERIFIED
    return VerificationStatus.UNVERIFIED


def normalize_website(raw: str | None) -> str | None:
    if not raw:
        return None
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    host = (parsed.netloc or parsed.path).lower()
    host = re.sub(r"^www\.", "", host)
    return host or None


def normalize_name(raw: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", raw.lower()).strip()


class DedupEngine:
    """
    Merges incoming RawLead records against existing Prospects using the
    priority order from the project spec:
        1. Phone number
        2. Website
        3. Business name + city (fuzzy)
        4. Google Maps place ID
    Returns the matching Prospect (if any) so the caller can update it in
    place instead of inserting a duplicate row.
    """

    def __init__(self, session: Session):
        self.session = session

    def find_existing(self, lead: RawLead) -> Prospect | None:
        phone = normalize_phone(lead.phone)
        if phone:
            match = self.session.execute(
                select(Prospect).where(Prospect.phone == phone)
            ).scalar_one_or_none()
            if match:
                return match

        website = normalize_website(lead.website)
        if website:
            match = self.session.execute(
                select(Prospect).where(Prospect.website.ilike(f"%{website}%"))
            ).scalar_one_or_none()
            if match:
                return match

        if lead.city:
            candidates = self.session.execute(
                select(Prospect).where(Prospect.city.ilike(lead.city))
            ).scalars().all()
            target_name = normalize_name(lead.business_name)
            for candidate in candidates:
                if _industries_conflict(lead.industry, candidate.industry):
                    continue
                score = fuzz.token_sort_ratio(target_name, normalize_name(candidate.business_name))
                if score >= NAME_MATCH_THRESHOLD:
                    return candidate

        if lead.google_maps_id:
            match = self.session.execute(
                select(Prospect).where(Prospect.google_maps_id == lead.google_maps_id)
            ).scalar_one_or_none()
            if match:
                return match

        return None

    def upsert(self, lead: RawLead) -> tuple[Prospect, bool]:
        """Returns (prospect, created)."""
        existing = self.find_existing(lead)
        phone = normalize_phone(lead.phone)
        website = normalize_website(lead.website)
        is_active = business_active_from_status(lead.extra.get("business_status"))

        clean_name = clean_business_name(lead.business_name)

        if existing:
            # Fill in any fields the existing record is missing; never
            # clobber good data with blanks from a lower-quality source.
            # Prefer replacing a messy existing name with a cleaner one of
            # the same underlying business (e.g. a Places API name replaces
            # a directory-scraped name loaded with SEO junk).
            if not existing.business_name or (
                clean_name and len(clean_name) < len(existing.business_name)
            ):
                existing.business_name = clean_name or existing.business_name
            existing.phone = existing.phone or phone
            existing.website = existing.website or website
            existing.city = existing.city or lead.city
            existing.locality = existing.locality or lead.locality
            existing.address = existing.address or lead.address
            existing.state = existing.state or lead.state
            existing.industry = existing.industry or lead.industry
            existing.google_maps_id = existing.google_maps_id or lead.google_maps_id
            existing.google_rating = existing.google_rating or lead.google_rating
            existing.review_count = existing.review_count or lead.review_count
            existing.business_description = existing.business_description or lead.business_description
            existing.latitude = existing.latitude or lead.latitude
            existing.longitude = existing.longitude or lead.longitude

            # The contact number is the primary, most reliable signal we
            # have -- a structurally valid number (checked via the
            # `phonenumbers` lib in normalize_phone) is enough to mark it
            # verified, since it came straight off a Maps/Places listing.
            existing.verification_status = combine_verification(
                existing.verification_status, phone_ok=bool(existing.phone)
            )
            if existing.is_business_active is None and is_active is not None:
                existing.is_business_active = is_active

            return existing, False

        prospect = Prospect(
            business_name=clean_name,
            phone=phone,
            website=website,
            city=lead.city,
            locality=lead.locality,
            address=lead.address,
            state=lead.state,
            industry=lead.industry,
            source=lead.source,
            google_maps_id=lead.google_maps_id,
            google_rating=lead.google_rating,
            review_count=lead.review_count,
            business_description=lead.business_description,
            latitude=lead.latitude,
            longitude=lead.longitude,
            is_business_active=is_active,
            verification_status=combine_verification(
                VerificationStatus.UNVERIFIED, phone_ok=bool(phone)
            ),
        )
        self.session.add(prospect)
        self.session.flush()
        return prospect, True

import enum
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from app.db.base import Base
from app.db.types import GUID


class LeadStatus(str, enum.Enum):
    NOT_CONTACTED = "NOT_CONTACTED"
    MAYBE = "MAYBE"
    CONVERTED = "CONVERTED"
    LOST = "LOST"
    NEW = "NEW"
    ENRICHING = "ENRICHING"
    READY = "READY"
    CONTACTED = "CONTACTED"
    RESPONDED = "RESPONDED"
    INTERESTED = "INTERESTED"
    DEMO_BOOKED = "DEMO_BOOKED"
    CUSTOMER = "CUSTOMER"


class VerificationStatus(str, enum.Enum):
    UNVERIFIED = "UNVERIFIED"
    PHONE_VERIFIED = "PHONE_VERIFIED"
    EMAIL_VERIFIED = "EMAIL_VERIFIED"
    FULLY_VERIFIED = "FULLY_VERIFIED"


class Prospect(Base):
    """
    Matches the "Prospects" schema from the project spec, plus the raw
    collected fields (whatsapp, description, rating, reviews, etc.) that
    feed the enrichment + scoring engines.
    """

    __tablename__ = "prospects"
    __table_args__ = (
        UniqueConstraint("phone", name="uq_prospects_phone"),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # Core identity
    business_name = Column(String(255), nullable=False, index=True)
    contact_name = Column(String(255), nullable=True)
    phone = Column(String(32), nullable=True, index=True)
    whatsapp = Column(String(32), nullable=True)
    # 'confirmed' (found a wa.me/api.whatsapp.com link on the business's own
    # site) vs 'inferred' (no explicit link found; fell back to the
    # verified mobile contact number). Lets the dashboard/sales team know
    # how much to trust the WhatsApp field before messaging it.
    whatsapp_source = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True, index=True)
    website = Column(String(500), nullable=True, index=True)

    # Location
    city = Column(String(120), nullable=True, index=True)
    locality = Column(String(120), nullable=True, index=True)  # neighbourhood/area within the city
    address = Column(Text, nullable=True)  # full street address from Google Maps
    state = Column(String(120), nullable=True, index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Classification
    industry = Column(String(120), nullable=True, index=True)  # e.g. real_estate_broker
    business_description = Column(Text, nullable=True)
    company_size_estimate = Column(String(50), nullable=True)

    # Source / provenance
    source = Column(String(120), nullable=True)  # google_maps, 99acres, housing_com, ...
    google_maps_id = Column(String(255), nullable=True, index=True)
    source_url = Column(String(1000), nullable=True)

    # Social
    social_profiles = Column(Text, nullable=True)  # JSON-encoded list

    # Quality signals
    google_rating = Column(Float, nullable=True)
    review_count = Column(Integer, nullable=True)
    is_business_active = Column(Boolean, nullable=True)

    # Pipeline
    status = Column(Enum(LeadStatus), nullable=False, default=LeadStatus.NEW, index=True)
    score = Column(Integer, nullable=False, default=0, index=True)
    verification_status = Column(
        Enum(VerificationStatus), nullable=False, default=VerificationStatus.UNVERIFIED
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_scraped_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Prospect {self.business_name!r} ({self.city}) score={self.score}>"

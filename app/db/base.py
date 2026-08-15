from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

Base = declarative_base()


@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _sync_schema():
    """
    Ensure all columns defined on the Prospect SQLAlchemy model exist in
    the PostgreSQL database table. Base.metadata.create_all() does not
    add missing columns to pre-existing tables.
    """
    if engine.dialect.name != "postgresql":
        return

    columns = [
        ("contact_name", "VARCHAR(255)"),
        ("phone", "VARCHAR(32)"),
        ("whatsapp", "VARCHAR(32)"),
        ("whatsapp_source", "VARCHAR(20)"),
        ("email", "VARCHAR(255)"),
        ("website", "VARCHAR(500)"),
        ("city", "VARCHAR(120)"),
        ("locality", "VARCHAR(120)"),
        ("address", "TEXT"),
        ("state", "VARCHAR(120)"),
        ("latitude", "DOUBLE PRECISION"),
        ("longitude", "DOUBLE PRECISION"),
        ("industry", "VARCHAR(120)"),
        ("business_description", "TEXT"),
        ("company_size_estimate", "VARCHAR(50)"),
        ("source", "VARCHAR(120)"),
        ("google_maps_id", "VARCHAR(255)"),
        ("source_url", "VARCHAR(1000)"),
        ("social_profiles", "TEXT"),
        ("google_rating", "DOUBLE PRECISION"),
        ("review_count", "INTEGER"),
        ("is_business_active", "BOOLEAN"),
        ("status", "VARCHAR(50) DEFAULT 'NEW'"),
        ("score", "INTEGER DEFAULT 0"),
        ("verification_status", "VARCHAR(50) DEFAULT 'UNVERIFIED'"),
        ("created_at", "TIMESTAMPTZ DEFAULT NOW()"),
        ("updated_at", "TIMESTAMPTZ DEFAULT NOW()"),
        ("last_scraped_at", "TIMESTAMPTZ"),
    ]

    with engine.begin() as conn:
        for col_name, col_type in columns:
            conn.execute(
                text(f"ALTER TABLE prospects ADD COLUMN IF NOT EXISTS {col_name} {col_type};")
            )


def init_db():
    """Create all tables and ensure schema is up to date."""
    from app.db import models  # noqa: F401  (ensures models are registered)

    Base.metadata.create_all(bind=engine)
    _sync_schema()


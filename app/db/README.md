# 🗄️ Database Module (`app/db/`)

This directory manages database connections, ORM models, session context handlers, and database custom types.

---

## 📁 File Manifest & Responsibilities

### 1. `models.py`
* **Purpose**: SQLAlchemy declarative models for the application.
* **Key Components**:
  * `LeadStatus`: Enum defining calling statuses (`NOT_CONTACTED`, `MAYBE`, `CONVERTED`, `LOST`) plus legacy aliases (`NEW`, `CUSTOMER`, `INTERESTED`).
  * `VerificationStatus`: Enum (`UNVERIFIED`, `PHONE_VERIFIED`, `EMAIL_VERIFIED`, `FULLY_VERIFIED`).
  * `Prospect`: Core database entity table `prospects`.
    * Columns: `id`, `business_name`, `contact_name`, `phone`, `whatsapp`, `whatsapp_source`, `email`, `website`, `city`, `locality`, `address`, `state`, `industry`, `business_description`, `score`, `status`, `created_at`, `updated_at`.
    * Unique constraint on `phone` (`uq_prospects_phone`).

### 2. `base.py`
* **Purpose**: Connection setup and session management.
* **Key Components**:
  * `engine`: SQLAlchemy engine bound to `DATABASE_URL`.
  * `SessionLocal`: Sessionmaker instance for creating DB sessions.
  * `get_session()`: Context manager for transaction management with automatic commit/rollback.
  * `init_db()`: Helper that creates all missing tables on startup.

### 3. `types.py`
* **Purpose**: Cross-platform database types.
* **Key Component**:
  * `GUID`: Custom SQLAlchemy type decorator that uses PostgreSQL's native `UUID` when connected to Postgres, and falls back to `CHAR(32)` when running on SQLite.

from urllib.parse import urlparse, urlunparse

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://leadzen:leadzen@postgres:5432/leadzen"

    redis_url: str = "redis://redis:6379/0"

    scraper_provider: str = "playwright"  # playwright | google_places
    google_places_api_key: str = ""
    openrouter_api_key: str = ""
    scraper_headless: bool = True
    scraper_max_results_per_query: int = 120
    scraper_request_delay_seconds: float = 2.5

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Supabase Storage (Shared persistent Excel workbook)
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_storage_bucket: str = "leadzen-exports"
    supabase_storage_object: str = "leadzen_prospects.xlsx"

    @property
    def effective_supabase_key(self) -> str:
        """
        Return explicitly configured SUPABASE_KEY or SUPABASE_SERVICE_ROLE_KEY.
        Never substitutes publishable/anon keys for privileged storage operations.
        """
        import os
        return self.supabase_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    @property
    def effective_supabase_url(self) -> str:
        """Return explicit supabase_url or derive project URL from database_url."""
        if self.supabase_url:
            return self.supabase_url.rstrip("/")
        # Try to infer project ref from database_url e.g. postgres.euvcqzmwezarbdgpfszq:...
        parsed = urlparse(self.database_url)
        username = parsed.username or ""
        if username.startswith("postgres.") and len(username.split(".")) > 1:
            ref = username.split(".")[1]
            return f"https://{ref}.supabase.co"
        if parsed.hostname and "supabase.co" in parsed.hostname:
            return f"https://{parsed.hostname.split('.')[0]}.supabase.co"
        return ""

    @property
    def _redis_base(self) -> str:
        """Base Redis URL (scheme + netloc) without path or db number."""
        parsed = urlparse(self.redis_url)
        return urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))

    @property
    def celery_broker_url(self) -> str:
        """Always derived from redis_url — immune to stale .env values."""
        return f"{self._redis_base}/0"

    @property
    def celery_result_backend(self) -> str:
        """Always derived from redis_url — immune to stale .env values."""
        return f"{self._redis_base}/1"

    def log_diagnostics(self) -> None:
        """Print safe startup diagnostics (hostnames and config presence only, no secrets)."""
        r = urlparse(self.redis_url)
        b = urlparse(self.celery_broker_url)
        k = urlparse(self.celery_result_backend)
        s = urlparse(self.effective_supabase_url) if self.effective_supabase_url else None
        print(f"REDIS_HOST={r.hostname}")
        print(f"CELERY_BROKER_HOST={b.hostname}")
        print(f"CELERY_BACKEND_HOST={k.hostname}")
        print(f"SUPABASE_HOST={s.hostname if s else None}")
        print(f"SUPABASE_KEY_CONFIGURED={bool(self.effective_supabase_key)}")
        print(f"STORAGE_BUCKET={self.supabase_storage_bucket}")
        print(f"STORAGE_OBJECT={self.supabase_storage_object}")


settings = Settings()
settings.log_diagnostics()



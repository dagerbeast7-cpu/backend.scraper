from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://leadzen:leadzen@postgres:5432/leadzen"

    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"

    scraper_provider: str = "playwright"  # playwright | google_places
    google_places_api_key: str = ""
    openrouter_api_key: str = ""
    scraper_headless: bool = True
    scraper_max_results_per_query: int = 120
    scraper_request_delay_seconds: float = 2.5

    api_host: str = "0.0.0.0"
    api_port: int = 8000


settings = Settings()

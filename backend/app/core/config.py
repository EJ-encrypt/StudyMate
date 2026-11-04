from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # "production" refuses to start without the settings a public deployment
    # needs (see app/main.py). Anything reachable by other people should set it.
    environment: str = "development"
    database_url: str = "postgresql+psycopg2://studymate:studymate@localhost:5432/studymate"
    cors_origins: str = "http://localhost:5173"
    # The public address of the app, used for links inside reminder emails and
    # push notifications, e.g. https://studymate.vercel.app
    app_url: str = "http://localhost:5173"

    # Supabase. Auth and file storage live there; the database is its Postgres.
    supabase_url: str = ""
    # Only needed for projects still on the legacy shared-secret JWTs. Newer
    # projects sign with asymmetric keys, verified against the JWKS endpoint.
    supabase_jwt_secret: str = ""
    # Server-side only: lets the API mint signed upload URLs and read files.
    # Never expose it to the browser.
    supabase_service_role_key: str = ""
    storage_bucket: str = "lecture-files"
    # Used when supabase_url is empty (local development and tests).
    storage_dir: str = "storage"

    # Shared secret the scheduler sends with every tick, so nobody else can
    # trigger reminder sends or job runs.
    cron_secret: str = ""

    # Web push (VAPID). Generate once with `python -m app.scripts.vapid`.
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_subject: str = "mailto:admin@example.com"

    # Email reminders over SMTP. A Gmail account with an app password works
    # and, unlike most free transactional services, can send to anyone.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    email_from: str = ""

    # Ordered, comma-separated. The first is used; the rest are fallbacks when
    # it fails for a transient reason, which on free tiers is common.
    ai_providers: str = "gemini"
    gemini_api_key: str = ""
    # Free "Experiment" plan key from console.mistral.ai; the backup provider.
    mistral_api_key: str = ""
    # Model lists are configuration, not code: providers retire models without
    # notice (gemini-2.5-flash was closed to new keys mid-project) and a wrong
    # name should be fixable without a deploy. Lite models only: measured in
    # November 2026, gemini-3.8-flash on the free tier answered 503/504 for
    # minutes at a time while the lite models answered, and each failed model
    # in the list costs up to a minute before the next is tried.
    gemini_models: str = "gemini-3.5-flash-lite,gemini-3.1-flash-lite"
    mistral_models: str = "mistral-small-latest,mistral-medium-latest"

    # AI work one student may ask for in any 24 hours (app/services/limits.py).
    # Generous for real revision, but stops one account, or a script using
    # it, from spending the whole free AI quota for everyone else.
    limit_generate_per_day: int = 30
    limit_documents_per_day: int = 40
    limit_reads_per_day: int = 15
    limit_grading_per_day: int = 60

    # Error reporting (Sentry). Off when empty.
    sentry_dsn: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @staticmethod
    def _csv(value: str) -> list[str]:
        return [item.strip() for item in value.split(",") if item.strip()]

    @property
    def ai_providers_list(self) -> list[str]:
        return self._csv(self.ai_providers)

    @property
    def gemini_models_list(self) -> list[str]:
        return self._csv(self.gemini_models)

    @property
    def mistral_models_list(self) -> list[str]:
        return self._csv(self.mistral_models)

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def uses_supabase_storage(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key)

    @property
    def push_enabled(self) -> bool:
        return bool(self.vapid_public_key and self.vapid_private_key)

    @property
    def email_enabled(self) -> bool:
        return bool(self.smtp_host and self.email_from)

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()

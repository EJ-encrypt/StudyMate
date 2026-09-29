from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_JWT_SECRET = "change-me-in-real-deployment"


class Settings(BaseSettings):
    # "production" refuses to start on insecure defaults. Anything reachable
    # by other people should set it.
    environment: str = "development"
    database_url: str = "postgresql+psycopg2://studymate:studymate@localhost:5432/studymate"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    cors_origins: str = "http://localhost:5173"
    # Ordered, comma-separated. The first is used; the rest are fallbacks when
    # it fails for a transient reason, which on free tiers is common.
    ai_providers: str = "gemini"
    gemini_api_key: str = ""
    openai_api_key: str = ""
    # Model lists are configuration, not code: providers retire models without
    # notice (gemini-2.5-flash was closed to new keys mid-project) and a wrong
    # name should be fixable without a deploy.
    gemini_models: str = "gemini-3.8-flash,gemini-3.5-flash-lite,gemini-3.1-flash-lite"
    openai_models: str = "gpt-4o-mini"
    storage_dir: str = "storage"
    # Where the built frontend lives. When present, the API serves it too, so
    # the whole app is reachable on one origin.
    frontend_dist: str = "frontend_dist"

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
    def openai_models_list(self) -> list[str]:
        return self._csv(self.openai_models)

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()

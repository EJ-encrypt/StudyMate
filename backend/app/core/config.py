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
    gemini_api_key: str = ""
    storage_dir: str = "storage"
    # Where the built frontend lives. When present, the API serves it too, so
    # the whole app is reachable on one origin.
    frontend_dist: str = "frontend_dist"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()

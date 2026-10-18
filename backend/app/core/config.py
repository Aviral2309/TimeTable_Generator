from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SGSITS Academic Timetable API"
    database_url: str = "sqlite:///./timetable.db"
    secret_key: str = "development-only-change-me"
    cors_origins: str = "http://localhost:5173"
    solver_time_limit_seconds: float = 30.0
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


import json
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "SaveCircle FinTech API"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"

    DATABASE_URL: str = "sqlite:///./savecircle.db"
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ORIGINS: list[str] = []
    AI_CONTAMINATION_RATE: float = 0.15

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, value):
        if isinstance(value, str):
            return json.loads(value)
        return value

    @property
    def allowed_origins(self) -> list[str]:
        return list(dict.fromkeys([self.FRONTEND_URL, *self.CORS_ORIGINS]))


settings = Settings()

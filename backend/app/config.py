import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "SaveCircle FinTech API"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    
    # Database configuration (SQLite local fallback, PostgreSQL production ready)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./savecircle.db")
    
    # JWT & Auth
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "savecircle_dev_secret_omnikon_hackathon_2026_secure_key")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "*"
    ]
    
    # AI Engine Sensitivity
    AI_CONTAMINATION_RATE: float = 0.15

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()

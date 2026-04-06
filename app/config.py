from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gemini_api_key: str = ""
    powens_client_id: Optional[str] = None
    powens_client_secret: Optional[str] = None
    powens_base_url: str = "https://demo.biapi.pro/2.0"  # sandbox Powens
    database_url: str = "sqlite:///./fintrack.db"
    api_budget_total: float = 100.0
    salary_amount: float = 3500.0
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    # Auth
    jwt_secret: str
    jwt_expire_hours: int = 24

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("JWT_SECRET must not be empty")
        return value

    class Config:
        env_file = ".env"


settings = Settings()

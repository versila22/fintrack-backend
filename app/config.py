import secrets
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gemini_api_key: str = ""
    powens_client_id: str = "71972119"
    powens_client_secret: str = "znKIZMEtTtXE6taN4VazZUXIlqiP5tjz"
    powens_base_url: str = "https://demo.biapi.pro/2.0"  # sandbox Powens
    database_url: str = "sqlite:///./fintrack.db"
    api_budget_total: float = 100.0
    salary_amount: float = 3500.0
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    # Auth
    jwt_secret: str = secrets.token_hex(32)  # override via JWT_SECRET env var in prod
    jwt_expire_days: int = 30

    class Config:
        env_file = ".env"


settings = Settings()

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, List
import secrets


class Settings(BaseSettings):
    # App
    app_name: str = "incident-responder"
    app_version: str = "1.1.0"
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = 8000

    # Security
    jwt_secret: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60 * 24 * 7  # 7 days

    # LLM
    llm_api_key: Optional[str] = None
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o"
    llm_provider: str = "openai"  # openai, anthropic, gemini, ollama

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/incidents.db"

    # Keycloak / OIDC
    oidc_enabled: bool = False
    oidc_issuer_url: Optional[str] = None
    oidc_client_id: Optional[str] = None
    oidc_client_secret: Optional[str] = None
    oidc_redirect_uri: Optional[str] = None

    # CORS
    cors_origins: List[str] = Field(default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"])

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
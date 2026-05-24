"""Application configuration loaded from environment variables."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings sourced from the .env file."""

    groq_api_key: str
    telegram_bot_token: str
    telegram_webhook_url: str
    brand_id: str
    brand_name: str
    db_path: str
    chroma_path: str
    max_compensation: int
    max_loop_count: int
    llm_model: str
    llm_temperature: float
    max_tokens: int
    log_level: str

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()

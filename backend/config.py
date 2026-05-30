from pathlib import Path
from pydantic_settings import BaseSettings

ENV_FILE = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    telegram_bot_token: str = ""
    database_url: str = "sqlite+aiosqlite:///./taskflow.db"
    secret_key: str = "change-me"
    base_url: str = "http://localhost:8000"

    # SMTP для email-уведомлений
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    class Config:
        env_file = str(ENV_FILE)


settings = Settings()

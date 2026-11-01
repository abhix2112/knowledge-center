from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str
    jwt_secret: SecretStr
    jwt_expire_minutes: int = 30
    upload_dir: Path = Path("storage/uploads")
    max_upload_mb: int = 10


settings = Settings()

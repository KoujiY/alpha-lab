"""應用設定，從環境變數讀取，預設值用於開發。"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ALPHA_LAB_", env_file=".env")

    database_url: str = "sqlite:///../data/alpha_lab.db"

    http_timeout_seconds: float = 30.0
    http_user_agent: str = "alpha-lab/0.1.0 (+https://github.com/local)"


def get_settings() -> Settings:
    return Settings()

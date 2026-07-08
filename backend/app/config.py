from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "changeme"

    sarvam_api_key: str = ""
    translate_api_url: str = ""
    translate_api_key: str = "1"
    deepseek_api_key: str = ""

    app_env: str = "dev"
    min_keywords_for_match: int = 1


settings = Settings()

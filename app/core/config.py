from typing import Literal

from pydantic import Field, PositiveInt, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: PostgresDsn
    REDIS_URL: RedisDsn

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: Literal["HS256"]

    ACCESS_TOKEN_EXPIRE_MINUTES: PositiveInt
    REFRESH_TOKEN_EXPIRE_DAYS: PositiveInt

    ASSET_TAG_COMPANY_PREFIX: str = Field(min_length=1, max_length=20)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()

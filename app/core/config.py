from typing import Literal

from pydantic import Field, PositiveInt, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DATABASE_URL: PostgresDsn
    REDIS_URL: RedisDsn

    JWT_SECRET_KEY: str = Field(min_length=32)
    JWT_ALGORITHM: Literal["HS256"]

    ACCESS_TOKEN_EXPIRE_MINUTES: PositiveInt
    REFRESH_TOKEN_EXPIRE_DAYS: PositiveInt

    ASSET_TAG_COMPANY_PREFIX: str = Field(min_length=1, max_length=20)

    SEED_USER_PASSWORD: str
    SEED_ADMIN_PASSWORD: str

    CORS_ORIGINS: str

    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str
    SMTP_PASSWORD: str

    MAIL_FROM_EMAIL: str
    MAIL_FROM_NAME: str = "Assets Management API"

    AWS_REGION: str
    S3_BUCKET_NAME: str
    S3_ENDPOINT_URL: str | None = None
    S3_PRESIGNED_URL_ENDPOINT: str | None = None
    S3_UPLOAD_CALLBACK_SECRET: str = Field(min_length=32)

    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()

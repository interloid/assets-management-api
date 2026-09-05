from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class TestSettings(BaseSettings):
    TEST_DATABASE_URL: PostgresDsn

    model_config = SettingsConfigDict(
        env_file=".env.test",
        env_file_encoding="utf-8",
    )


test_settings = TestSettings()

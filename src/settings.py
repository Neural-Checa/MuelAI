from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    google_api_key: str = Field(description="Google Gemini API Key")
    database_url: str = Field(
        default="sqlite:///./dental_clinic.db",
        description="Database connection URL",
    )
    gemini_model: str = Field(
        default="gemini-2.5-flash",
        description="Gemini model to use",
    )


def get_settings() -> Settings:
    return Settings()

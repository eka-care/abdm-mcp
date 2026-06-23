from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="ABDM_",
        extra="ignore"
    )

    gateway_base_url: str = Field(default="http://localhost:8080")
    gateway_timeout: int = Field(default=30)
    facility_id: str = Field(default="")
    gateway_api_key: str = Field(default="")


settings = Settings()

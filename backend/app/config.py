from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["local", "test", "staging", "production"]
OtpAdapterName = Literal["fake", "disabled"]


class Settings(BaseSettings):
    """Runtime configuration loaded only from explicit environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="MINGLI_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "FateRadar API"
    environment: Environment = "local"
    database_url: str = "postgresql+asyncpg://mingli:mingli-local@127.0.0.1:5432/mingli"
    cookie_secure: bool = False
    cookie_domain: str | None = None
    otp_adapter: OtpAdapterName = "fake"
    fake_otp_code: str = "246810"
    identity_hash_key: SecretStr = SecretStr("local-only-identity-hash-key-change-in-production")
    otp_ttl_seconds: int = 5 * 60
    otp_cooldown_seconds: int = 60
    otp_max_attempts: int = 5
    otp_rate_window_seconds: int = Field(default=10 * 60, ge=1)
    otp_guest_window_limit: int = Field(default=5, ge=1)
    otp_network_window_limit: int = Field(default=30, ge=1)
    trusted_proxy_cidrs: str = ""
    device_session_days: int = 30
    log_level: str = "INFO"

    @model_validator(mode="after")
    def enforce_production_safety(self) -> Self:
        if self.environment == "production" and not self.cookie_secure:
            raise ValueError("production requires secure cookies")
        if self.environment == "production" and self.otp_adapter == "fake":
            raise ValueError("Fake OTP adapter is forbidden in production")
        uses_local_hash_key = self.identity_hash_key.get_secret_value().startswith("local-only-")
        if self.environment == "production" and uses_local_hash_key:
            raise ValueError("production identity hash key must be injected")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

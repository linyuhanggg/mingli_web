import base64
import binascii
from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["local", "test", "staging", "production"]
OtpAdapterName = Literal["fake", "disabled"]
RuntimeAdapterName = Literal["fake", "one-shot"]
_LOCAL_CONTENT_KEY_B64 = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
_PRODUCTION_RUNTIME_LAUNCHER = Path("/opt/mingli-master/scripts/run_reading_transaction.sh")
_PRODUCTION_RUNTIME_PYTHON = Path("/opt/mingli-runtime/venv/bin/python")
_PRODUCTION_RUNTIME_RELEASE_ROOT = Path("/opt/mingli-master")
_PRODUCTION_RUNTIME_STATE_ROOT = Path("/var/lib/mingli")
_FROZEN_DESCRIBE_MANIFEST_DIGEST = (
    "7ddbc04a04cad101dc1ab4951982c60b3138ffbb1b09463c64df719c69940342"
)
_FROZEN_CAPABILITY_SHAPE_SHA256 = "8ce44f539004405dc174236612e7185547057b241d9e5fef042dffc958517f60"


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
    runtime_adapter: RuntimeAdapterName = "fake"
    runtime_launcher_path: Path | None = None
    runtime_python_path: Path | None = None
    runtime_release_root: Path | None = None
    runtime_state_root: Path | None = None
    runtime_expected_manifest_digest: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    runtime_expected_capability_shape_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    runtime_timeout_seconds: float = Field(default=30.0, gt=0)
    runtime_max_stdin_bytes: int = Field(default=2 * 1024 * 1024, ge=1)
    runtime_max_stdout_bytes: int = Field(default=2 * 1024 * 1024, ge=1)
    runtime_max_stderr_bytes: int = Field(default=64 * 1024, ge=1)
    fake_otp_code: str = "246810"
    identity_hash_key: SecretStr = SecretStr("local-only-identity-hash-key-change-in-production")
    content_encryption_key_b64: SecretStr = SecretStr(_LOCAL_CONTENT_KEY_B64)
    content_encryption_key_id: str = Field(default="local-only-content-v1", min_length=1)
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
        encoded_content_key = self.content_encryption_key_b64.get_secret_value()
        try:
            decoded_content_key = base64.b64decode(
                encoded_content_key,
                validate=True,
            )
        except (binascii.Error, ValueError) as error:
            raise ValueError(
                "content encryption key must be valid base64 for exactly 32 bytes"
            ) from error
        if len(decoded_content_key) != 32:
            raise ValueError("content encryption key must decode to exactly 32 bytes")
        uses_local_content_key = (
            encoded_content_key == _LOCAL_CONTENT_KEY_B64
            or self.content_encryption_key_id.startswith("local-only-")
        )
        if self.environment == "production" and uses_local_content_key:
            raise ValueError("production content encryption key must be injected")
        if encoded_content_key == self.identity_hash_key.get_secret_value():
            raise ValueError("content encryption key must not reuse identity_hash_key")
        if self.environment == "production" and self.runtime_adapter == "fake":
            raise ValueError("Fake Runtime adapter is forbidden in production")
        runtime_paths = (
            self.runtime_launcher_path,
            self.runtime_python_path,
            self.runtime_release_root,
            self.runtime_state_root,
        )
        if any(path is not None and not path.is_absolute() for path in runtime_paths):
            raise ValueError("Runtime launcher, Python, release and state paths must be absolute")
        if self.environment == "production":
            if self.runtime_launcher_path is None:
                raise ValueError("production Runtime launcher is required")
            if self.runtime_launcher_path != _PRODUCTION_RUNTIME_LAUNCHER:
                raise ValueError("production requires the fixed launcher path")
            if self.runtime_python_path != _PRODUCTION_RUNTIME_PYTHON:
                raise ValueError("production requires the fixed Runtime Python path")
            if self.runtime_release_root != _PRODUCTION_RUNTIME_RELEASE_ROOT:
                raise ValueError("production requires the fixed Runtime release root")
            if self.runtime_state_root is None:
                raise ValueError("production Runtime state root is required")
            if self.runtime_state_root != _PRODUCTION_RUNTIME_STATE_ROOT:
                raise ValueError("production requires the fixed Runtime state root")
            if self.runtime_expected_manifest_digest is None:
                raise ValueError("production expected Runtime manifest digest is required")
            if self.runtime_expected_manifest_digest != _FROZEN_DESCRIBE_MANIFEST_DIGEST:
                raise ValueError("production Runtime manifest digest is not the frozen release")
            if self.runtime_expected_capability_shape_sha256 is None:
                raise ValueError("production expected capability shape digest is required")
            if self.runtime_expected_capability_shape_sha256 != _FROZEN_CAPABILITY_SHAPE_SHA256:
                raise ValueError("production requires the frozen capability shape digest")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

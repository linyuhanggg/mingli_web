import base64
import binascii
import math
import os
import re
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, NotRequired, Self, TypedDict

from pydantic import Field, SecretStr, model_validator
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

from app.adapters.otp import OtpSecurityMode

Environment = Literal["local", "test", "staging", "production"]
OtpAdapterName = Literal["fake", "disabled", "smtp"]
RuntimeAdapterName = Literal["fake", "one-shot", "worker-v2"]
RuntimeReleaseProfile = Literal[
    "v51",
    "v51-extension-facts",
    "v52-relationship",
    "v53-time-check",
]
ModelAdapterName = Literal["fake", "deepseek"]
_LOCAL_CONTENT_KEY_B64 = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
_PRODUCTION_RUNTIME_LAUNCHER = Path("/opt/mingli-master/scripts/run_reading_transaction.sh")
_PRODUCTION_RUNTIME_PYTHON = Path("/opt/mingli-runtime/venv/bin/python")
_PRODUCTION_RUNTIME_RELEASE_ROOT = Path("/opt/mingli-master")
_PRODUCTION_RUNTIME_STATE_ROOT = Path("/var/lib/mingli")
_FROZEN_DESCRIBE_MANIFEST_DIGEST = (
    "7ddbc04a04cad101dc1ab4951982c60b3138ffbb1b09463c64df719c69940342"
)
_V52_RELATIONSHIP_DESCRIBE_MANIFEST_DIGEST = (
    "6118c5f525c87b9cbde95b4d51c945be18bfd18fff8e03306da9fa748b87d917"
)
_V53_TIME_CHECK_DESCRIBE_MANIFEST_DIGEST = (
    "2da3c62b250959a6f011434ee38fc3cf3851725a5fafb794ef78d978d9367b22"
)
_FROZEN_CAPABILITY_SHAPE_SHA256 = "8ce44f539004405dc174236612e7185547057b241d9e5fef042dffc958517f60"


class _RuntimeReleaseIdentity(TypedDict):
    manifest_digest: str
    capability_shape_sha256: str
    release_manifest_sha256: str
    release_name: str
    source_commit: str
    signed_file_count: int
    physical_file_count: int
    worker_sha256: NotRequired[str]
    worker_protocol: NotRequired[str]
    worker_turn_terminal: NotRequired[str]


_RUNTIME_RELEASE_PROFILES: dict[str, _RuntimeReleaseIdentity] = {
    "v51": {
        "manifest_digest": _FROZEN_DESCRIBE_MANIFEST_DIGEST,
        "capability_shape_sha256": _FROZEN_CAPABILITY_SHAPE_SHA256,
        "release_manifest_sha256": (
            "280145cddaaddb693f8256214381d75d8579e620ec731e9a9ce4ec10522bc51d"
        ),
        "release_name": "mingli-master-portable-core",
        "source_commit": "3f70b9025f828343759aaef22dab9ac5f2879a8c",
        "signed_file_count": 218,
        "physical_file_count": 219,
        "worker_sha256": (
            "b8d05ca1a4d6392598442e8fed80d73a2ce079b757c2d6bc059f5ff13b629e3e"
        ),
        "worker_protocol": "mingli-runtime-worker-v2",
        "worker_turn_terminal": "result-idle-v1",
    },
    "v51-extension-facts": {
        "manifest_digest": (
            "9b9852860336336420825d1bf845c2aa17deb9c450b69a8f59fe09303bbafb08"
        ),
        "capability_shape_sha256": _FROZEN_CAPABILITY_SHAPE_SHA256,
        "release_manifest_sha256": (
            "da5f8edb8a147417f3ba1fbb3136d64c7ccfbfab1e476421ef0dd50db7e39b05"
        ),
        "release_name": "mingli-master-portable-core-v51-extension-facts",
        "source_commit": "494ce0bba174a77800daf9b9c38ce9c9166d9a94",
        "signed_file_count": 218,
        "physical_file_count": 219,
    },
    "v52-relationship": {
        "manifest_digest": _V52_RELATIONSHIP_DESCRIBE_MANIFEST_DIGEST,
        "capability_shape_sha256": _FROZEN_CAPABILITY_SHAPE_SHA256,
        "release_manifest_sha256": (
            "bef3df256ce06a9796d5eaef999d1141873128fe75b06916922ddd7fe9ac5d50"
        ),
        "release_name": "mingli-master-portable-core-v52-relationship",
        "source_commit": "da46e7c0d565fe781e40a115acbb2874c400a195",
        "signed_file_count": 218,
        "physical_file_count": 219,
    },
    "v53-time-check": {
        "manifest_digest": _V53_TIME_CHECK_DESCRIBE_MANIFEST_DIGEST,
        "capability_shape_sha256": (
            "9b9193285622a183c06802713fbfb62fa4c76e9190b692d9d422261a418e63af"
        ),
        "release_manifest_sha256": (
            "f1deb17a9b4f39b09b2478c8942dcf0761d90bcba95dcbc44a15b8c84f79190b"
        ),
        "release_name": "mingli-master-portable-core",
        "source_commit": "6db9dd37d8e62cd425798be2c64ad1121c1c1649",
        "signed_file_count": 227,
        "physical_file_count": 228,
        "worker_sha256": (
            "e89df2c08df29e65ffc91c05e8e4e5be99f72f67e26b79c5b23a4eb2222ddc9c"
        ),
        "worker_protocol": "mingli-runtime-worker-v2",
        "worker_turn_terminal": "result-idle-v1",
    },
}
_P0_MODEL_PROVIDER = "deepseek"
_P0_MODEL_PROFILE_ID = "deepseek-v4-flash-p0-v1"
_P0_MODEL_ID = "deepseek-v4-flash"
_P0_MODEL_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
_P0_MODEL_BASE_URL_ALLOWLIST = frozenset(
    {
        "https://api.deepseek.com",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    }
)
_P0_MODEL_ENDPOINT_PATH = "/chat/completions"
_P0_MODEL_THINKING_MODE = "not-sent-p0-v1"
_SAFE_MODEL_METADATA = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


class _MappingSettingsSource(PydanticBaseSettingsSource):
    def __init__(
        self,
        settings_cls: type[BaseSettings],
        loader: Callable[[], dict[str, Any]],
    ) -> None:
        super().__init__(settings_cls)
        self._loader = loader

    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        del field
        return self._loader().get(field_name), field_name, False

    def __call__(self) -> dict[str, Any]:
        return self._loader()


class Settings(BaseSettings):
    """Runtime configuration loaded only from explicit environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="MINGLI_",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = "FateRadar API"
    environment: Environment = "local"
    database_url: str = "postgresql+asyncpg://mingli:mingli-local@127.0.0.1:5432/mingli"
    cookie_secure: bool = False
    cookie_domain: str | None = None
    otp_adapter: OtpAdapterName = "fake"
    smtp_host: str | None = None
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_security: OtpSecurityMode = "starttls"
    smtp_username: SecretStr | None = None
    smtp_password: SecretStr | None = None
    smtp_sender: str | None = None
    runtime_adapter: RuntimeAdapterName = "fake"
    runtime_release_profile: RuntimeReleaseProfile = "v51"
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
    chart_fast_path_timeout_seconds: float = Field(default=2.0, gt=0, le=2.0)
    runtime_max_stdin_bytes: int = Field(default=2 * 1024 * 1024, ge=1)
    runtime_max_stdout_bytes: int = Field(default=2 * 1024 * 1024, ge=1)
    runtime_max_stderr_bytes: int = Field(default=64 * 1024, ge=1)
    physiognomy_media_root: Path | None = None
    model_adapter: ModelAdapterName = "fake"
    model_provider: str = _P0_MODEL_PROVIDER
    model_profile_id: str = _P0_MODEL_PROFILE_ID
    model_id: str = _P0_MODEL_ID
    model_base_url: str = _P0_MODEL_BASE_URL
    model_endpoint_path: str = _P0_MODEL_ENDPOINT_PATH
    model_thinking_mode: str = _P0_MODEL_THINKING_MODE
    deepseek_api_key: SecretStr | None = Field(
        default=None,
        validation_alias="DEEPSEEK_API_KEY",
    )
    model_connect_timeout_seconds: float = 5.0
    model_read_timeout_seconds: float = 60.0
    model_overall_timeout_seconds: float = 75.0
    model_max_response_bytes: int = 256 * 1024
    model_temperature: float = 0.2
    model_max_output_tokens: int = 4096
    model_price_snapshot_version: str | None = None
    model_price_currency: str = "CNY"
    model_input_price_microunits_per_million_tokens: int | None = None
    model_output_price_microunits_per_million_tokens: int | None = None
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
    otp_destination_window_limit: int = Field(default=5, ge=1)
    guest_session_create_rate_limit: int = Field(default=10, ge=1)
    guest_session_create_rate_window_seconds: float = Field(default=600, gt=0)
    reading_write_rate_limit: int = Field(default=10, ge=1)
    reading_write_rate_window_seconds: int = Field(default=60, ge=1)
    profile_write_rate_limit: int = Field(default=10, ge=1)
    profile_write_rate_window_seconds: int = Field(default=60, ge=1)
    # Dogfood gates (off by default so unit tests and local fake stacks stay open).
    # Test server dogfood enables entitlement grants + daily ceilings via env.
    dogfood_entitlement_gates_enabled: bool = False
    dogfood_daily_reading_limit: int = Field(default=10, ge=1)
    dogfood_daily_paid_reading_limit: int = Field(default=6, ge=1)
    dogfood_daily_limit_window_seconds: float = Field(default=86_400.0, gt=0)
    trusted_proxy_cidrs: str = ""
    device_session_days: int = 30
    admin_session_hours: int = Field(default=8, ge=1, le=24)
    admin_bootstrap_email: str | None = None
    admin_bootstrap_password: SecretStr | None = None
    admin_login_rate_limit: int = Field(default=10, ge=1)
    admin_login_rate_window_seconds: float = Field(default=600, gt=0)
    log_level: str = "INFO"
    real_traffic_enabled: bool = False
    alert_sink_enabled: bool = False

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        def exact_deepseek_secret() -> dict[str, str]:
            value = os.environ.get("DEEPSEEK_API_KEY")
            return {} if value is None else {"DEEPSEEK_API_KEY": value}

        def without_deepseek_secret(
            source: PydanticBaseSettingsSource,
        ) -> dict[str, object]:
            values = dict(source())
            values.pop("DEEPSEEK_API_KEY", None)
            values.pop("deepseek_api_key", None)
            return values

        def filtered_environment() -> dict[str, object]:
            return without_deepseek_secret(env_settings)

        def filtered_dotenv() -> dict[str, object]:
            return without_deepseek_secret(dotenv_settings)

        def filtered_file_secrets() -> dict[str, object]:
            return without_deepseek_secret(file_secret_settings)

        return (
            init_settings,
            _MappingSettingsSource(settings_cls, exact_deepseek_secret),
            _MappingSettingsSource(settings_cls, filtered_environment),
            _MappingSettingsSource(settings_cls, filtered_dotenv),
            _MappingSettingsSource(settings_cls, filtered_file_secrets),
        )

    @model_validator(mode="before")
    @classmethod
    def apply_production_runtime_defaults(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if data.get("environment") != "production":
            return data
        updated = dict(data)
        if "runtime_adapter" not in updated:
            updated["runtime_adapter"] = "worker-v2"
        return updated

    @model_validator(mode="after")
    def enforce_production_safety(self) -> Self:
        if self.environment == "production" and not self.cookie_secure:
            raise ValueError("production requires secure cookies")
        if self.environment == "production" and self.otp_adapter == "fake":
            raise ValueError("Fake OTP adapter is forbidden in production")
        if self.otp_adapter == "smtp":
            missing = []
            if not self.smtp_host:
                missing.append("host")
            if self.smtp_username is None or not self.smtp_username.get_secret_value():
                missing.append("username")
            if self.smtp_password is None or not self.smtp_password.get_secret_value():
                missing.append("password")
            if not self.smtp_sender:
                missing.append("sender")
            if missing:
                raise ValueError(f"SMTP OTP adapter requires {', '.join(missing)}")
        if self.environment == "production" and self.otp_adapter == "smtp":
            raise ValueError(
                "SMTP OTP delivery requires a durable challenge store; unavailable in production"
            )
        uses_local_hash_key = self.identity_hash_key.get_secret_value().startswith("local-only-")
        if self.environment == "production" and uses_local_hash_key:
            raise ValueError("production identity hash key must be injected")
        if self.environment == "production" and (
            self.admin_bootstrap_email or self.admin_bootstrap_password is not None
        ):
            raise ValueError("production forbids admin bootstrap credentials")
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
        if self.environment == "production" and self.model_adapter == "fake":
            raise ValueError("Fake Model adapter is forbidden in production")
        if self.environment == "production" and self.dogfood_entitlement_gates_enabled:
            raise ValueError("dogfood entitlement gates are forbidden in production")
        if (
            self.dogfood_daily_paid_reading_limit > self.dogfood_daily_reading_limit
        ):
            raise ValueError(
                "dogfood_daily_paid_reading_limit cannot exceed dogfood_daily_reading_limit"
            )
        if self.model_provider != _P0_MODEL_PROVIDER:
            raise ValueError("P0 model provider is not approved")
        if self.model_profile_id != _P0_MODEL_PROFILE_ID:
            raise ValueError("P0 model profile is not approved")
        if self.model_id != _P0_MODEL_ID:
            raise ValueError("P0 model ID is not approved")
        if self.model_base_url not in _P0_MODEL_BASE_URL_ALLOWLIST:
            raise ValueError("P0 model base URL is not allowlisted")
        if self.model_endpoint_path != _P0_MODEL_ENDPOINT_PATH:
            raise ValueError("P0 model endpoint path is not allowlisted")
        if self.model_thinking_mode != _P0_MODEL_THINKING_MODE:
            raise ValueError("P0 model thinking mode is not approved")
        model_timeout_limits = (
            ("connect timeout", self.model_connect_timeout_seconds, 30.0),
            ("read timeout", self.model_read_timeout_seconds, 120.0),
            ("overall timeout", self.model_overall_timeout_seconds, 180.0),
        )
        for label, value, upper_bound in model_timeout_limits:
            if not math.isfinite(value) or not 0 < value <= upper_bound:
                raise ValueError(f"model {label} must be finite and bounded")
        if self.model_overall_timeout_seconds < max(
            self.model_connect_timeout_seconds,
            self.model_read_timeout_seconds,
        ):
            raise ValueError("model overall timeout must cover connect and read timeouts")
        if not 1 <= self.model_max_response_bytes <= 1024 * 1024:
            raise ValueError("model response body limit must be bounded")
        if not math.isfinite(self.model_temperature) or not 0 <= self.model_temperature <= 2:
            raise ValueError("model temperature must be finite and bounded")
        if not 1 <= self.model_max_output_tokens <= 8192:
            raise ValueError("model output tokens must be bounded")
        if self.model_adapter == "deepseek":
            if self.model_temperature != 0.2 or self.model_max_output_tokens != 4096:
                raise ValueError("P0 model profile generation settings are frozen")
            if (
                self.deepseek_api_key is None
                or not self.deepseek_api_key.get_secret_value().strip()
            ):
                raise ValueError("DeepSeek API key must be injected")
            if self.model_price_snapshot_version is None or not _SAFE_MODEL_METADATA.fullmatch(
                self.model_price_snapshot_version
            ):
                raise ValueError("model price snapshot version must be a safe injected identifier")
            token_prices = (
                self.model_input_price_microunits_per_million_tokens,
                self.model_output_price_microunits_per_million_tokens,
            )
            if any(value is None or not 0 <= value <= 10**12 for value in token_prices):
                raise ValueError("model token prices must be non-negative bounded integers")
            if self.model_price_currency != "CNY":
                raise ValueError("P0 model price currency must be CNY")
        runtime_paths = (
            self.runtime_launcher_path,
            self.runtime_python_path,
            self.runtime_release_root,
            self.runtime_state_root,
        )
        if any(path is not None and not path.is_absolute() for path in runtime_paths):
            raise ValueError("Runtime launcher, Python, release and state paths must be absolute")
        if self.environment == "production":
            if self.runtime_release_profile in {
                "v51-extension-facts",
                "v53-time-check",
            }:
                raise ValueError("selected Runtime release is local/test only")
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
            profile = _RUNTIME_RELEASE_PROFILES[self.runtime_release_profile]
            if self.runtime_expected_manifest_digest != profile["manifest_digest"]:
                raise ValueError("production Runtime manifest digest is not the admitted release")
            if self.runtime_expected_capability_shape_sha256 is None:
                raise ValueError("production expected capability shape digest is required")
            if self.runtime_expected_capability_shape_sha256 != profile["capability_shape_sha256"]:
                raise ValueError(
                    "production requires the frozen capability shape digest "
                    "for the admitted release"
                )
            if self.real_traffic_enabled and not self.alert_sink_enabled:
                raise ValueError(
                    "production real traffic requires alert_sink_enabled"
                )
            if self.real_traffic_enabled:
                raise ValueError(
                    "production real traffic remains disabled until Phase 0 gates are closed"
                )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

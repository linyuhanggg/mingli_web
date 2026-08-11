import importlib

import pytest
from pydantic import SecretStr, ValidationError


def settings_type():  # type: ignore[no-untyped-def]
    config = importlib.import_module("app.config")
    return config.Settings


def test_production_requires_secure_cookies() -> None:
    Settings = settings_type()

    with pytest.raises(ValidationError, match="secure cookies"):
        Settings(
            environment="production",
            cookie_secure=False,
            otp_adapter="disabled",
        )


def test_production_rejects_the_fake_otp_adapter() -> None:
    Settings = settings_type()

    with pytest.raises(ValidationError, match="Fake OTP"):
        Settings(
            environment="production",
            cookie_secure=True,
            otp_adapter="fake",
        )


def test_local_defaults_are_explicitly_non_production() -> None:
    Settings = settings_type()
    settings = Settings()

    assert settings.environment == "local"
    assert settings.cookie_secure is False
    assert settings.otp_adapter == "fake"


def test_smtp_adapter_requires_host_username_password_and_sender() -> None:
    Settings = settings_type()
    complete = {
        "smtp_host": "smtp.example.com",
        "smtp_username": "mailuser",
        "smtp_password": "mailpass",
        "smtp_sender": "no-reply@example.com",
    }

    for missing in complete:
        values = dict(complete)
        values.pop(missing)
        with pytest.raises(ValidationError, match="SMTP OTP adapter requires"):
            Settings(
                environment="staging",
                otp_adapter="smtp",
                **values,
            )


def test_smtp_credentials_are_secret_and_never_printed() -> None:
    Settings = settings_type()
    settings = Settings(
        environment="staging",
        otp_adapter="smtp",
        smtp_host="smtp.example.com",
        smtp_port=465,
        smtp_security="ssl",
        smtp_username="mailuser",
        smtp_password="s3cret-mail-password",
        smtp_sender="no-reply@example.com",
    )

    assert settings.smtp_host == "smtp.example.com"
    assert settings.smtp_port == 465
    assert settings.smtp_security == "ssl"
    assert isinstance(settings.smtp_username, SecretStr)
    assert isinstance(settings.smtp_password, SecretStr)
    assert settings.smtp_username.get_secret_value() == "mailuser"
    assert settings.smtp_password.get_secret_value() == "s3cret-mail-password"
    assert "s3cret-mail-password" not in repr(settings)


def test_production_rejects_the_smtp_otp_adapter_until_durable_store() -> None:
    Settings = settings_type()

    with pytest.raises(ValidationError, match="durable challenge store"):
        Settings(
            environment="production",
            cookie_secure=True,
            otp_adapter="smtp",
            smtp_host="smtp.example.com",
            smtp_username="mailuser",
            smtp_password="mailpass",
            smtp_sender="no-reply@example.com",
        )


def test_otp_destination_window_limit_defaults_to_five_per_window() -> None:
    Settings = settings_type()
    settings = Settings()

    assert settings.otp_destination_window_limit == 5
    assert settings.otp_rate_window_seconds == 10 * 60


def test_guest_session_creation_rate_limit_defaults() -> None:
    Settings = settings_type()
    settings = Settings()

    assert settings.guest_session_create_rate_limit == 10
    assert settings.guest_session_create_rate_window_seconds == 600


def test_real_traffic_defaults_disabled() -> None:
    Settings = settings_type()
    settings = Settings()
    assert settings.real_traffic_enabled is False
    assert settings.alert_sink_enabled is False


def test_production_rejects_real_traffic_until_phase0_gates_close() -> None:
    Settings = settings_type()
    import base64

    injected_key = base64.b64encode(b"p" * 32).decode()
    common = dict(
        environment="production",
        cookie_secure=True,
        otp_adapter="disabled",
        identity_hash_key="injected-identity-hash-key",
        content_encryption_key_b64=injected_key,
        content_encryption_key_id="kms-production-v1",
        runtime_adapter="one-shot",
        runtime_launcher_path="/opt/mingli-master/scripts/run_reading_transaction.sh",
        runtime_python_path="/opt/mingli-runtime/venv/bin/python",
        runtime_release_root="/opt/mingli-master",
        runtime_state_root="/var/lib/mingli",
        runtime_expected_manifest_digest=(
            "7ddbc04a04cad101dc1ab4951982c60b3138ffbb1b09463c64df719c69940342"
        ),
        runtime_expected_capability_shape_sha256=(
            "8ce44f539004405dc174236612e7185547057b241d9e5fef042dffc958517f60"
        ),
        model_adapter="deepseek",
        deepseek_api_key="test-only-obviously-not-a-real-key",
        model_price_snapshot_version="fixture-price-v1",
        model_input_price_microunits_per_million_tokens=1,
        model_output_price_microunits_per_million_tokens=1,
        alert_sink_enabled=True,
        real_traffic_enabled=True,
    )
    with pytest.raises(ValidationError, match="real traffic remains disabled"):
        Settings(**common)


def test_production_real_traffic_requires_alert_sink() -> None:
    Settings = settings_type()
    import base64

    injected_key = base64.b64encode(b"p" * 32).decode()
    with pytest.raises(ValidationError, match="alert_sink_enabled"):
        Settings(
            environment="production",
            cookie_secure=True,
            otp_adapter="disabled",
            identity_hash_key="injected-identity-hash-key",
            content_encryption_key_b64=injected_key,
            content_encryption_key_id="kms-production-v1",
            runtime_adapter="one-shot",
            runtime_launcher_path="/opt/mingli-master/scripts/run_reading_transaction.sh",
            runtime_python_path="/opt/mingli-runtime/venv/bin/python",
            runtime_release_root="/opt/mingli-master",
            runtime_state_root="/var/lib/mingli",
            runtime_expected_manifest_digest=(
                "7ddbc04a04cad101dc1ab4951982c60b3138ffbb1b09463c64df719c69940342"
            ),
            runtime_expected_capability_shape_sha256=(
                "8ce44f539004405dc174236612e7185547057b241d9e5fef042dffc958517f60"
            ),
            model_adapter="deepseek",
            deepseek_api_key="test-only-obviously-not-a-real-key",
            model_price_snapshot_version="fixture-price-v1",
            model_input_price_microunits_per_million_tokens=1,
            model_output_price_microunits_per_million_tokens=1,
            alert_sink_enabled=False,
            real_traffic_enabled=True,
        )

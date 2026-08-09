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

import importlib

import pytest
from pydantic import ValidationError


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

import base64
import importlib
from dataclasses import replace

import pytest
from pydantic import ValidationError


def test_envelope_cipher_uses_random_nonces_and_stable_fingerprints() -> None:
    envelope = importlib.import_module("app.security.envelope")
    cipher = envelope.EnvelopeCipher(key=b"k" * 32, key_id="test-key-v1")
    raw = "1994-04-30T05:55:00+08:00 福建省福州市"

    first = cipher.encrypt_text(raw, context="profile-version:test")
    second = cipher.encrypt_text(raw, context="profile-version:test")

    assert first.key_id == "test-key-v1"
    assert raw not in first.ciphertext
    assert first.nonce != second.nonce
    assert first.ciphertext != second.ciphertext
    assert first.fingerprint == second.fingerprint
    assert cipher.decrypt_text(first, context="profile-version:test") == raw
    with pytest.raises(envelope.EnvelopeDecryptionError):
        cipher.decrypt_text(first, context="reading-version:wrong")


def test_envelope_cipher_rejects_a_tampered_fingerprint() -> None:
    envelope = importlib.import_module("app.security.envelope")
    cipher = envelope.EnvelopeCipher(key=b"k" * 32, key_id="test-key-v1")
    payload = cipher.encrypt_text(
        "已经通过 AES-GCM 解密的正文",
        context="reading-version:test:accepted-copy",
    )
    replacement = "0" * 64 if payload.fingerprint != "0" * 64 else "1" * 64

    with pytest.raises(envelope.EnvelopeDecryptionError, match="fingerprint"):
        cipher.decrypt_text(
            replace(payload, fingerprint=replacement),
            context="reading-version:test:accepted-copy",
        )


def test_production_requires_an_explicit_256_bit_content_key() -> None:
    config = importlib.import_module("app.config")
    injected_key = base64.b64encode(b"p" * 32).decode()

    with pytest.raises(ValidationError, match="content encryption"):
        config.Settings(
            environment="production",
            cookie_secure=True,
            otp_adapter="disabled",
            identity_hash_key="injected-identity-hash-key",
        )

    settings = config.Settings(
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
    )
    assert settings.content_encryption_key_id == "kms-production-v1"


def test_content_encryption_key_must_decode_to_exactly_32_bytes() -> None:
    config = importlib.import_module("app.config")

    with pytest.raises(ValidationError, match="32 bytes"):
        config.Settings(
            environment="test",
            content_encryption_key_b64=base64.b64encode(b"short").decode(),
        )

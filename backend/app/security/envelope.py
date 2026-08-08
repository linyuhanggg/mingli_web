from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

if TYPE_CHECKING:
    from app.config import Settings


class EnvelopeDecryptionError(ValueError):
    """Ciphertext, context or key identity failed authenticated decryption."""


@dataclass(frozen=True, slots=True)
class EncryptedPayload:
    key_id: str
    nonce: str
    ciphertext: str
    fingerprint: str


class EnvelopeCipher:
    """AES-256-GCM with domain-separated HMAC fingerprints."""

    def __init__(self, *, key: bytes, key_id: str) -> None:
        if len(key) != 32:
            raise ValueError("EnvelopeCipher requires an exact 256-bit key")
        if not key_id.strip():
            raise ValueError("encryption key id must be non-empty")
        self._key = key
        self._key_id = key_id
        self._fingerprint_key = hmac.new(
            key,
            b"mingli-content-fingerprint-key-v1",
            hashlib.sha256,
        ).digest()

    @classmethod
    def from_settings(cls, settings: Settings) -> EnvelopeCipher:
        key = base64.b64decode(
            settings.content_encryption_key_b64.get_secret_value(),
            validate=True,
        )
        return cls(key=key, key_id=settings.content_encryption_key_id)

    def encrypt_text(self, plaintext: str, *, context: str) -> EncryptedPayload:
        if not context.strip():
            raise ValueError("encryption context must be non-empty")
        encoded = plaintext.encode("utf-8")
        nonce = os.urandom(12)
        aad = context.encode("utf-8")
        ciphertext = AESGCM(self._key).encrypt(nonce, encoded, aad)
        fingerprint = hmac.new(
            self._fingerprint_key,
            aad + b"\x00" + encoded,
            hashlib.sha256,
        ).hexdigest()
        return EncryptedPayload(
            key_id=self._key_id,
            nonce=base64.b64encode(nonce).decode("ascii"),
            ciphertext=base64.b64encode(ciphertext).decode("ascii"),
            fingerprint=fingerprint,
        )

    def decrypt_text(self, payload: EncryptedPayload, *, context: str) -> str:
        if payload.key_id != self._key_id:
            raise EnvelopeDecryptionError("ciphertext key id is unavailable")
        try:
            nonce = base64.b64decode(payload.nonce, validate=True)
            ciphertext = base64.b64decode(payload.ciphertext, validate=True)
            plaintext = AESGCM(self._key).decrypt(
                nonce,
                ciphertext,
                context.encode("utf-8"),
            )
        except (InvalidTag, binascii.Error, ValueError) as error:
            raise EnvelopeDecryptionError("authenticated payload decryption failed") from error
        return plaintext.decode("utf-8")

    def encrypt_json(
        self,
        payload: Mapping[str, object],
        *,
        context: str,
    ) -> EncryptedPayload:
        serialized = json.dumps(
            dict(payload),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return self.encrypt_text(serialized, context=context)

    def decrypt_json(
        self,
        payload: EncryptedPayload,
        *,
        context: str,
    ) -> dict[str, Any]:
        decoded = json.loads(self.decrypt_text(payload, context=context))
        if not isinstance(decoded, dict):
            raise EnvelopeDecryptionError("encrypted JSON payload is not an object")
        return cast(dict[str, Any], decoded)

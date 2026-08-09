from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Literal

from app.readings.narrative_contracts import NarrativeCandidate

_SAFE_METADATA = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_SAFE_ERROR_CODE = re.compile(r"^model_[a-z0-9_]{1,80}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def model_price_snapshot_digest(
    *,
    version: str,
    currency: str,
    input_microunits_per_million_tokens: int,
    output_microunits_per_million_tokens: int,
) -> str:
    payload = {
        "currency": currency,
        "input_microunits_per_million_tokens": input_microunits_per_million_tokens,
        "output_microunits_per_million_tokens": output_microunits_per_million_tokens,
        "version": version,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class ModelTokenUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int

    def __post_init__(self) -> None:
        if min(self.input_tokens, self.output_tokens, self.total_tokens) < 0:
            raise ValueError("model token usage cannot be negative")
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError("model total token usage must equal input plus output")


@dataclass(frozen=True, slots=True)
class ModelCost:
    currency: str
    microunits: int
    price_snapshot_version: str
    price_snapshot_digest: str
    input_microunits_per_million_tokens: int
    output_microunits_per_million_tokens: int

    def __post_init__(self) -> None:
        if self.currency != "CNY" or self.microunits < 0:
            raise ValueError("model cost must be a non-negative CNY microunit amount")
        if not _SAFE_METADATA.fullmatch(self.price_snapshot_version):
            raise ValueError("model price snapshot version must be a safe identifier")
        if not _SHA256.fullmatch(self.price_snapshot_digest):
            raise ValueError("model price snapshot digest must be SHA-256")
        if (
            min(
                self.input_microunits_per_million_tokens,
                self.output_microunits_per_million_tokens,
            )
            < 0
        ):
            raise ValueError("model price rates cannot be negative")


@dataclass(frozen=True, slots=True)
class ModelPriceReceipt:
    version: str
    currency: str
    snapshot_digest: str
    input_microunits_per_million_tokens: int
    output_microunits_per_million_tokens: int

    def __post_init__(self) -> None:
        if self.currency != "CNY":
            raise ValueError("P0 price receipt currency must be CNY")
        if not _SAFE_METADATA.fullmatch(self.version):
            raise ValueError("model price receipt version must be a safe identifier")
        if not _SHA256.fullmatch(self.snapshot_digest):
            raise ValueError("model price receipt digest must be SHA-256")
        if (
            min(
                self.input_microunits_per_million_tokens,
                self.output_microunits_per_million_tokens,
            )
            < 0
        ):
            raise ValueError("model price receipt rates cannot be negative")
        expected_digest = model_price_snapshot_digest(
            version=self.version,
            currency=self.currency,
            input_microunits_per_million_tokens=(self.input_microunits_per_million_tokens),
            output_microunits_per_million_tokens=(self.output_microunits_per_million_tokens),
        )
        if self.snapshot_digest != expected_digest:
            raise ValueError("model price receipt digest does not match its fields")

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "currency": self.currency,
            "snapshot_digest": self.snapshot_digest,
            "input_microunits_per_million_tokens": (self.input_microunits_per_million_tokens),
            "output_microunits_per_million_tokens": (self.output_microunits_per_million_tokens),
        }


@dataclass(frozen=True, slots=True)
class ModelCallReceipt:
    outcome: Literal["succeeded", "failed"]
    error_code: str | None
    model_profile_id: str
    model_profile_snapshot_digest: str
    provider: str
    provider_model_version: str | None
    provider_request_fingerprint: str | None
    request_fingerprint: str
    latency_ms: int
    narrative_policy_version: str
    output_contract_id: str
    price_snapshot: ModelPriceReceipt
    usage: ModelTokenUsage | None
    cost: ModelCost | None

    def __post_init__(self) -> None:
        if self.outcome == "succeeded" and self.error_code is not None:
            raise ValueError("successful model audit cannot carry an error")
        if self.outcome == "failed" and (
            self.error_code is None or not _SAFE_ERROR_CODE.fullmatch(self.error_code)
        ):
            raise ValueError("failed model audit requires a safe error code")
        if self.cost is not None and self.usage is None:
            raise ValueError("model cost requires known usage")
        if self.cost is not None and (
            self.cost.currency != self.price_snapshot.currency
            or self.cost.price_snapshot_version != self.price_snapshot.version
            or self.cost.price_snapshot_digest != self.price_snapshot.snapshot_digest
            or self.cost.input_microunits_per_million_tokens
            != self.price_snapshot.input_microunits_per_million_tokens
            or self.cost.output_microunits_per_million_tokens
            != self.price_snapshot.output_microunits_per_million_tokens
        ):
            raise ValueError("model cost must bind the exact price snapshot")
        if self.outcome == "succeeded" and (
            self.provider_model_version is None
            or self.provider_request_fingerprint is None
            or self.usage is None
            or self.cost is None
        ):
            raise ValueError("successful model audit requires complete provider metadata")
        for value in (self.model_profile_id, self.provider, self.narrative_policy_version):
            if not _SAFE_METADATA.fullmatch(value):
                raise ValueError("model audit metadata must be a safe identifier")
        if self.provider_model_version is not None and not _SAFE_METADATA.fullmatch(
            self.provider_model_version
        ):
            raise ValueError("provider audit metadata must be a safe identifier")
        if self.provider_request_fingerprint is not None and not _SHA256.fullmatch(
            self.provider_request_fingerprint
        ):
            raise ValueError("provider request fingerprint must be SHA-256")
        if not _SHA256.fullmatch(self.model_profile_snapshot_digest):
            raise ValueError("model profile snapshot digest must be SHA-256")
        if not _SHA256.fullmatch(self.request_fingerprint):
            raise ValueError("model request fingerprint must be SHA-256")
        if self.latency_ms < 0:
            raise ValueError("model latency cannot be negative")
        if not _SAFE_METADATA.fullmatch(self.output_contract_id):
            raise ValueError("output contract ID must be a safe identifier")
        if self.cost is not None and self.usage is not None:
            numerator = (
                self.usage.input_tokens * self.cost.input_microunits_per_million_tokens
                + self.usage.output_tokens * self.cost.output_microunits_per_million_tokens
            )
            expected_microunits = (numerator + 500_000) // 1_000_000
            if self.cost.microunits != expected_microunits:
                raise ValueError("computed model cost does not match usage and rates")

    def to_dict(self) -> dict[str, object]:
        return {
            "event": "standalone_model_call",
            "outcome": self.outcome,
            "error_code": self.error_code,
            "model_profile_id": self.model_profile_id,
            "model_profile_snapshot_digest": self.model_profile_snapshot_digest,
            "provider": self.provider,
            "provider_model_version": self.provider_model_version,
            "provider_request_fingerprint": self.provider_request_fingerprint,
            "request_fingerprint": self.request_fingerprint,
            "latency_ms": self.latency_ms,
            "narrative_policy_version": self.narrative_policy_version,
            "output_contract_id": self.output_contract_id,
            "price_snapshot": self.price_snapshot.to_dict(),
            "usage_known": self.usage_known,
            "cost_known": self.cost_known,
            "cost_unknown_reason": self.cost_unknown_reason,
            "usage": (
                None
                if self.usage is None
                else {
                    "input_tokens": self.usage.input_tokens,
                    "output_tokens": self.usage.output_tokens,
                    "total_tokens": self.usage.total_tokens,
                }
            ),
            "cost": (
                None
                if self.cost is None
                else {
                    "currency": self.cost.currency,
                    "microunits": self.cost.microunits,
                    "price_snapshot_version": self.cost.price_snapshot_version,
                    "price_snapshot_digest": self.cost.price_snapshot_digest,
                    "input_microunits_per_million_tokens": (
                        self.cost.input_microunits_per_million_tokens
                    ),
                    "output_microunits_per_million_tokens": (
                        self.cost.output_microunits_per_million_tokens
                    ),
                }
            ),
        }

    @property
    def usage_known(self) -> bool:
        return self.usage is not None

    @property
    def cost_known(self) -> bool:
        return self.cost is not None

    @property
    def cost_unknown_reason(self) -> str | None:
        if self.cost is not None:
            return None
        if self.usage is None:
            return "usage_unavailable"
        return "price_snapshot_model_mismatch"


@dataclass(frozen=True, slots=True)
class ModelGenerationResult:
    candidate: NarrativeCandidate
    receipt: ModelCallReceipt

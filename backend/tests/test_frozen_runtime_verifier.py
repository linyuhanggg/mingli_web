from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from types import ModuleType

import pytest
from app.adapters.runtime import (
    V53_TIME_CHECK_RELEASE_FILE_COUNT,
    V53_TIME_CHECK_RELEASE_PHYSICAL_FILE_COUNT,
)
from app.config import _RUNTIME_RELEASE_PROFILES

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VERIFIER_PATH = PROJECT_ROOT / "scripts" / "verify_frozen_runtime_release.py"
LEGACY_SOURCE_COMMIT = "9c615a70f08d5609af09ead100d2b5d90e558fe8"
LEGACY_MANIFEST_SHA256 = (
    "d1b49d5842feb5d4143330d1d250af625f42644a930f7d9d9c344c5d0363b090"
)
LEGACY_WORKER_SHA256 = (
    "3512987322ef18bb91c4798e77d7ef982d2e7e31ae9e2ddd321d78aa90261b50"
)
LEGACY_VERIFIER_SOURCE_COMMIT = "663543e65ae037843b03dca1dec9486293affc9d"
LEGACY_VERIFIER_MANIFEST_SHA256 = (
    "c451de5e4390c2a264a49aed972057081c61cb74ada160df308ac7a2af993c4b"
)


def _load_verifier() -> ModuleType:
    spec = importlib.util.spec_from_file_location("frozen_runtime_verifier", VERIFIER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_frozen_verifier_and_backend_share_the_exact_v53_identity() -> None:
    verifier = _load_verifier()
    profile = _RUNTIME_RELEASE_PROFILES["v53-time-check"]

    assert profile["source_commit"] == verifier.FROZEN_SOURCE_COMMIT
    assert profile["release_manifest_sha256"] == verifier.FROZEN_MANIFEST_SHA256
    assert profile["worker_sha256"] == verifier.FROZEN_WORKER_SHA256
    assert profile["manifest_digest"] == verifier.FROZEN_DESCRIBE_MANIFEST_DIGEST
    assert (
        profile["capability_shape_sha256"]
        == verifier.FROZEN_CAPABILITY_SHAPE_SHA256
    )
    assert profile["signed_file_count"] == verifier.EXPECTED_SIGNED_FILE_COUNT
    assert profile["physical_file_count"] == verifier.EXPECTED_PHYSICAL_FILE_COUNT
    assert profile["signed_file_count"] == V53_TIME_CHECK_RELEASE_FILE_COUNT
    assert profile["physical_file_count"] == V53_TIME_CHECK_RELEASE_PHYSICAL_FILE_COUNT
    assert profile["source_commit"] not in {
        LEGACY_SOURCE_COMMIT,
        LEGACY_VERIFIER_SOURCE_COMMIT,
    }
    assert profile["release_manifest_sha256"] not in {
        LEGACY_MANIFEST_SHA256,
        LEGACY_VERIFIER_MANIFEST_SHA256,
    }
    assert profile["worker_sha256"] != LEGACY_WORKER_SHA256


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("FROZEN_SOURCE_COMMIT", LEGACY_SOURCE_COMMIT, "release identity mismatch"),
        ("FROZEN_MANIFEST_SHA256", LEGACY_MANIFEST_SHA256, "manifest sha mismatch"),
        ("FROZEN_WORKER_SHA256", LEGACY_WORKER_SHA256, "worker digest mismatch"),
        ("EXPECTED_SIGNED_FILE_COUNT", 226, "signed file count mismatch"),
        ("EXPECTED_PHYSICAL_FILE_COUNT", 227, "physical file count mismatch"),
        ("FROZEN_DESCRIBE_MANIFEST_DIGEST", "0" * 64, "describe manifest"),
        ("FROZEN_CAPABILITY_SHAPE_SHA256", "0" * 64, "capability shape"),
    ),
)
def test_frozen_verifier_rejects_each_identity_field_drift(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: object,
    message: str,
) -> None:
    raw_release_root = os.environ.get("MINGLI_V53_RELEASE_ROOT")
    if not raw_release_root:
        pytest.skip("MINGLI_V53_RELEASE_ROOT is not configured")
    release_root = Path(raw_release_root)
    if not (release_root / ".mingli-release-manifest.json").is_file():
        pytest.skip("the controlled V53 release is not installed")
    verifier = _load_verifier()
    monkeypatch.setattr(verifier, field, value)

    with pytest.raises(verifier.VerificationError, match=message):
        verifier.verify_release(release_root)

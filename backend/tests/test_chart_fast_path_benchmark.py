from __future__ import annotations

import argparse
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import chart_fast_path_benchmark as benchmark
import pytest
from app.adapters.runtime import OneShotMingliRuntimeAdapter
from app.config import _RUNTIME_RELEASE_PROFILES
from app.readings.runtime_contracts import Described


@pytest.mark.parametrize(
    ("selected_flag", "relative_path", "expected_sha256"),
    (
        (
            "overlay_bazi_calc",
            benchmark._BAZI_CALC_RELATIVE,
            benchmark.QA_LOCKED_BAZI_CALC_SHA256,
        ),
        (
            "overlay_liuren_calc",
            benchmark._LIUREN_CALC_RELATIVE,
            benchmark.QA_LOCKED_LIUREN_CALC_SHA256,
        ),
    ),
)
def test_v53_overlay_paths_pin_signed_and_physical_file_counts(
    tmp_path: Path,
    selected_flag: str,
    relative_path: str,
    expected_sha256: str,
) -> None:
    overlay_path = tmp_path / relative_path.rsplit("/", 1)[-1]
    args = argparse.Namespace(overlay_bazi_calc=None, overlay_liuren_calc=None)
    setattr(args, selected_flag, overlay_path)

    assert benchmark._selected_overlays(args) == [
        (relative_path, overlay_path, expected_sha256)
    ]

    described = cast(
        Described,
        SimpleNamespace(manifest_digest="describe-digest", capabilities=[]),
    )
    gate = benchmark._build_overlay_runtime_startup_gate(
        runtime=cast(OneShotMingliRuntimeAdapter, object()),
        release_root=tmp_path,
        profile=_RUNTIME_RELEASE_PROFILES["v53-time-check"],
        expected_release_manifest_sha256="release-manifest-digest",
        described=described,
    )

    assert gate.expected_release_file_count == 227
    assert gate.expected_physical_file_count == 228
    assert gate.release_inspector.expected_release_file_count == 227
    assert gate.release_inspector.expected_physical_file_count == 228

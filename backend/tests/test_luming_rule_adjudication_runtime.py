from __future__ import annotations

import os
import subprocess
import textwrap
from pathlib import Path

import pytest
from mingli_paths import MINGLI_CORE_SCRIPTS

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_PYTHON = Path(
    os.environ.get(
        "MINGLI_RUNTIME_TEST_PYTHON",
        str(Path.home() / ".local/share/mingli-master/venv/bin/python"),
    )
)

pytestmark = pytest.mark.skipif(
    not RUNTIME_PYTHON.is_file() or not MINGLI_CORE_SCRIPTS.is_dir(),
    reason="the Mingli core source or dedicated Runtime Python is not installed",
)


def _run_runtime_assertions(source: str) -> None:
    result = subprocess.run(
        [str(RUNTIME_PYTHON), "-c", textwrap.dedent(source)],
        cwd=ROOT,
        env={
            **os.environ,
            "PYTHONPATH": str(MINGLI_CORE_SCRIPTS),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPYCACHEPREFIX": "/dev/null",
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_every_active_luming_rule_is_verified_and_source_bound() -> None:
    _run_runtime_assertions(
        """
        from collections import Counter
        from reading_engine.evidence_rules import production_evidence_rules

        rules = [
            item
            for item in production_evidence_rules()
            if item.system == "luming-nayin" and item.runtime_active
        ]

        assert len(rules) == 59
        assert Counter(item.evidence_role for item in rules) == {
            "issue_specific_judgment_rule": 56,
            "methodology_rule": 3,
        }
        assert all(
            item.classical_binding_status == "verified"
            and item.classical_binding_digest
            for item in rules
        )
        """
    )


def test_matched_luming_rule_receives_source_bound_applicability_adjudication() -> None:
    _run_runtime_assertions(
        """
        from reading_engine.luming import build_fact_layer

        snapshot = build_fact_layer(["庚辰", "壬午", "甲子", "乙丑"])
        pattern = next(
            item
            for item in snapshot["output"]["source_conditioned_patterns"]
            if item["local_rule_id"] == "LX-01-17"
        )

        assert pattern["status"] == "predicate_matched_not_verdict"
        assert pattern["applicability_adjudication"] == {
            "status": "adjudicated_rule_applicability",
            "decision_scope": "luming_nayin_source_rule_applicability",
            "rule_id": "luming-nayin/li-xuzhong-mingshu#LX-01-17",
            "local_rule_id": "LX-01-17",
            "rule_title": "LX-01-17 庚辰（禄暗会）",
            "evidence_role": "issue_specific_judgment_rule",
            "hard_verdict": None,
            "life_verdict": None,
            "source_ref": {
                "pack": "luming-nayin/li-xuzhong-mingshu",
                "rule_id": "LX-01-17",
                "source_anchor": (
                    "references/books/luming-nayin/li-xuzhong-mingshu/"
                    "rules.md#LX-01-17"
                ),
                "verification_status": "verified",
                "binding_digest": (
                    "12683b2c9a4b48519f306a2966c18a51"
                    "c134779aa90d569a7e33aefe0d93fc3f"
                ),
            },
            "unresolved_checks": [
                "多条规则的并见、冲突、依赖与例外",
                "胎元、禄马贵与四柱纳音的整体权衡",
                "现实人生结论、吉凶等级与时限",
            ],
        }
        assert "verdict" not in pattern
        """
    )


def test_luming_validator_rejects_tampered_rule_adjudication() -> None:
    _run_runtime_assertions(
        """
        from reading_engine.luming import build_fact_layer, validate_facts

        snapshot = build_fact_layer(["庚辰", "壬午", "甲子", "乙丑"])
        snapshot["output"]["source_conditioned_patterns"][0][
            "applicability_adjudication"
        ]["life_verdict"] = "富贵"
        snapshot["natal_fact_digest"] = "tampered"

        report = validate_facts(snapshot)

        assert report["ok"] is False
        assert "luming_invalid_source_pattern" in report["codes"]
        assert "luming_output_mismatch" in report["codes"]
        """
    )

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


def test_every_taiyi_predicate_definition_has_one_verified_runtime_rule() -> None:
    _run_runtime_assertions(
        """
        from reading_engine.evidence_rules import production_evidence_rules
        from reading_engine.taiyi import source_table

        table_ids = {
            item["id"]
            for item in source_table()["board_predicate_contracts"]
        }
        verified = {
            item.local_rule_id: item
            for item in production_evidence_rules()
            if item.system == "taiyi"
            and item.local_rule_id.startswith("TY-P")
            and item.runtime_active
            and item.classical_binding_status == "verified"
        }

        assert len(table_ids) == 10
        assert set(verified) == table_ids
        assert all(item.classical_binding_digest for item in verified.values())
        """
    )


def test_detected_taiyi_patterns_receive_source_bound_identity_adjudication() -> None:
    _run_runtime_assertions(
        """
        from reading_engine.taiyi import build_annual_board

        board = build_annual_board(2026)
        predicates = {
            item["id"]: item
            for item in board["board_predicates"]
        }

        assert set(predicates) == {"TY-P01", "TY-P07"}
        p01 = predicates["TY-P01"]
        assert p01["status"] == "predicate_matched_not_verdict"
        assert p01["identity_adjudication"] == {
            "status": "adjudicated_pattern_identity",
            "decision_scope": "taiyi_board_pattern_identity",
            "pattern_id": "TY-P01",
            "pattern_name": "掩",
            "hard_verdict": None,
            "event_verdict": None,
            "source_ref": {
                "pack": "san-shi/taiyi-shenshu",
                "rule_id": "TY-P01",
                "source_anchor": (
                    "references/books/san-shi/taiyi-shenshu/"
                    "rules.md#TY-P01"
                ),
                "verification_status": "verified",
                "binding_digest": (
                    "b649915dd2b4545f338afa447e5028c3"
                    "d157035b2a8578ba2aa2cf522f91e6da"
                ),
            },
            "unresolved_checks": [
                "并见格局、制化与主客关系",
                "宏观事项范围及盘面取用",
                "现实成败、吉凶与应期",
            ],
        }
        assert predicates["TY-P07"]["identity_adjudication"]["source_ref"] == {
            "pack": "san-shi/taiyi-shenshu",
            "rule_id": "TY-P07",
            "source_anchor": (
                "references/books/san-shi/taiyi-shenshu/rules.md#TY-P07"
            ),
            "verification_status": "verified",
            "binding_digest": (
                "4b5759e36717a118e260174593043d01f"
                "ba6e15a95639b60ebd220d42436958f"
            ),
        }
        assert all(
            item["identity_adjudication"]["hard_verdict"] is None
            and item["identity_adjudication"]["event_verdict"] is None
            for item in predicates.values()
        )
        """
    )


def test_taiyi_validator_rejects_tampered_pattern_adjudication() -> None:
    _run_runtime_assertions(
        """
        from reading_engine.calendar_core import normalize_calendar
        from reading_engine.taiyi import build_fact_layer, validate_fact_layer

        calendar = normalize_calendar(
            "2026-08-14T10:00:00+08:00",
            timezone_name="Asia/Shanghai",
            location="synthetic-calendar-fixture",
        )
        snapshot = build_fact_layer(calendar)
        snapshot["output"]["board_predicates"][0]["identity_adjudication"][
            "event_verdict"
        ] = "吉"

        findings = validate_fact_layer(snapshot)

        assert findings["ok"] is False
        assert "taiyi_board_facts_mismatch" in findings["codes"]
        assert "taiyi_invalid_predicate_fact" in findings["codes"]
        """
    )

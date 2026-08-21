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


def test_every_qimen_pattern_definition_has_one_verified_runtime_rule() -> None:
    _run_runtime_assertions(
        """
        from reading_engine.evidence_rules import production_evidence_rules
        from reading_engine.qimen import source_table

        table_ids = {
            item["id"]
            for item in source_table()["named_pattern_predicates"]
        }
        verified = {
            item.local_rule_id: item
            for item in production_evidence_rules()
            if item.system == "qimen"
            and item.runtime_active
            and item.classical_binding_status == "verified"
        }

        assert len(table_ids) == 40
        assert set(verified) == table_ids
        assert all(item.classical_binding_digest for item in verified.values())
        """
    )


def test_detected_qimen_patterns_receive_source_bound_identity_adjudication() -> None:
    _run_runtime_assertions(
        """
        from reading_engine.calendar_core import normalize_calendar
        from reading_engine.qimen import build_fact_layer

        calendar = normalize_calendar(
            "2026-08-14T10:00:00+08:00",
            timezone_name="Asia/Shanghai",
            location="synthetic-calendar-fixture",
        )
        snapshot = build_fact_layer(calendar)
        patterns = {
            item["id"]: item
            for item in snapshot["output"]["named_patterns"]
        }

        assert {"QM-P16", "QM-P17"} <= set(patterns)
        p16 = patterns["QM-P16"]
        assert p16["status"] == "predicate_matched_not_verdict"
        assert p16["identity_adjudication"] == {
            "status": "adjudicated_pattern_identity",
            "decision_scope": "qimen_named_pattern_identity",
            "pattern_id": "QM-P16",
            "pattern_name": "三奇入墓",
            "palace": p16["palace"],
            "hard_verdict": None,
            "event_verdict": None,
            "source_ref": {
                "pack": "san-shi/qimen-dunjia-tongzhi",
                "rule_id": "QM-P16",
                "source_anchor": (
                    "references/books/san-shi/qimen-dunjia-tongzhi/"
                    "rules.md#QM-P16"
                ),
                "verification_status": "verified",
                "binding_digest": (
                    "b82a437343c32de96825d3a85196599a77f53d9d54123b5417d3fd6e6700c067"
                ),
            },
            "unresolved_checks": [
                "格局强弱、制化与并见关系",
                "事项用神及宫位关系",
                "事件成败、吉凶与应期",
            ],
        }
        assert patterns["QM-P17"]["identity_adjudication"]["source_ref"] == {
            "pack": "san-shi/qimen-dunjia-tongzhi",
            "rule_id": "QM-P17",
            "source_anchor": (
                "references/books/san-shi/qimen-dunjia-tongzhi/"
                "rules.md#QM-P17"
            ),
            "verification_status": "verified",
            "binding_digest": (
                "362e95978a73823de4a2f2d38763dc6a8618ef42db7656541753fc6f7e55863d"
            ),
        }
        assert all(
            item["identity_adjudication"]["hard_verdict"] is None
            and item["identity_adjudication"]["event_verdict"] is None
            for item in patterns.values()
        )
        """
    )


def test_qimen_validator_rejects_tampered_pattern_adjudication() -> None:
    _run_runtime_assertions(
        """
        from reading_engine.calendar_core import normalize_calendar
        from reading_engine.qimen import build_fact_layer, validate_fact_layer

        calendar = normalize_calendar(
            "2026-08-14T10:00:00+08:00",
            timezone_name="Asia/Shanghai",
            location="synthetic-calendar-fixture",
        )
        snapshot = build_fact_layer(calendar)
        snapshot["output"]["named_patterns"][0]["identity_adjudication"][
            "event_verdict"
        ] = "吉"

        findings = validate_fact_layer(snapshot)

        assert findings["ok"] is False
        assert "qimen_board_facts_mismatch" in findings["codes"]
        assert "qimen_invalid_pattern_fact" in findings["codes"]
        """
    )

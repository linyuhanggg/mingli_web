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


def test_meihua_body_use_rules_are_active_and_source_verified() -> None:
    _run_runtime_assertions(
        """
        from reading_engine.evidence_rules import production_evidence_rules

        rules = {
            item.local_rule_id: item
            for item in production_evidence_rules()
            if item.system == "divination"
            and item.local_rule_id in {"MR-04-01", "MR-04-02", "MR-04-04"}
        }

        assert set(rules) == {"MR-04-01", "MR-04-02", "MR-04-04"}
        assert all(
            item.runtime_active
            and item.classical_binding_status == "verified"
            and item.classical_binding_digest
            for item in rules.values()
        )
        """
    )


def test_meihua_relations_receive_source_bound_polarity_adjudication() -> None:
    _run_runtime_assertions(
        """
        from reading_engine.calendar_core import normalize_calendar
        from reading_engine.meihua import build_from_method

        calendar = normalize_calendar(
            "2026-08-14T10:00:00+08:00",
            timezone_name="Asia/Shanghai",
            location="synthetic-calendar-fixture",
        )
        snapshot = build_from_method(
            {
                "casting_method": "supplied_number",
                "number": 17,
                "provenance": {"kind": "synthetic_test"},
            },
            calendar_facts=calendar,
        )
        adjudicated = snapshot["output"]["interpretive_candidates"]

        assert adjudicated["status"] == "source_adjudicated_relations"
        assert adjudicated["verification_status"] == "verified"
        assert adjudicated["hard_verdict"] is None
        assert adjudicated["requires_classical_adjudication"] is False
        assert adjudicated["requires_synthesis_adjudication"] is True
        assert len(adjudicated["relation_candidates"]) == 5
        expected_polarity = {
            "use_generates_body": "supportive",
            "actor_generates_body": "supportive",
            "body_generates_use": "depleting",
            "body_generates_actor": "depleting",
            "use_controls_body": "adverse",
            "actor_controls_body": "adverse",
            "body_controls_use": "favorable",
            "body_controls_actor": "favorable",
            "same_element": "harmonious",
        }
        for candidate in adjudicated["relation_candidates"]:
            relation = candidate["relation_adjudication"]
            assert candidate["status"] == "relation_adjudicated_not_event_verdict"
            assert candidate["verification_status"] == "verified"
            assert relation["status"] == "adjudicated_relation_polarity"
            assert relation["source_polarity"] == expected_polarity[
                candidate["relation_key"]
            ]
            assert relation["hard_verdict"] is None
            assert relation["event_verdict"] is None
            assert relation["source_refs"][0]["rule_id"] == "MR-04-02"
            assert all(
                source["verification_status"] == "verified"
                and len(source["binding_digest"]) == 64
                for source in relation["source_refs"]
            )
        """
    )


def test_meihua_validator_rejects_tampered_relation_adjudication() -> None:
    _run_runtime_assertions(
        """
        from reading_engine.calendar_core import normalize_calendar
        from reading_engine.meihua import build_from_method, validate_fact_layer

        calendar = normalize_calendar(
            "2026-08-14T10:00:00+08:00",
            timezone_name="Asia/Shanghai",
            location="synthetic-calendar-fixture",
        )
        snapshot = build_from_method(
            {
                "casting_method": "supplied_number",
                "number": 17,
                "provenance": {"kind": "synthetic_test"},
            },
            calendar_facts=calendar,
        )
        snapshot["output"]["interpretive_candidates"]["relation_candidates"][0][
            "relation_adjudication"
        ]["event_verdict"] = "吉"

        report = validate_fact_layer(snapshot)

        assert report["ok"] is False
        assert "meihua_invalid_relation_adjudication" in report["codes"]
        assert "meihua_output_mismatch" in report["codes"]
        """
    )

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


def test_finance_question_adjudicates_the_unique_visible_wealth_line() -> None:
    _run_runtime_assertions(
        """
        from reading_engine.calendar_core import normalize_calendar
        from reading_engine.liuyao import build_fact_layer

        calendar = normalize_calendar(
            "2026-08-17T12:00:00+08:00",
            timezone_name="Asia/Shanghai",
            location="synthetic-calendar-fixture",
        )
        snapshot = build_fact_layer(
            (6, 7, 8, 9, 6, 7),
            calendar_facts=calendar,
            casting={
                "method": "supplied_complete_cast",
                "provenance": {"kind": "synthetic_test"},
            },
            requested_useful_spirit_relatives=("妻财", "子孙"),
            question_class="finance",
        )
        adjudication = snapshot["output"]["useful_spirit_selection"][
            "role_adjudication"
        ]

        assert adjudication == {
            "status": "adjudicated_question_role_set",
            "decision_scope": "finance_useful_spirit_role_set",
            "question_class": "finance",
            "primary_relative": "妻财",
            "supporting_relatives": ["子孙"],
            "obstacle_attention_relatives": ["兄弟", "官鬼", "父母"],
            "specific_line_selection": 4,
            "specific_line_adjudication": {
                "status": "adjudicated_unique_visible_line",
                "decision_scope": "finance_primary_relative_line_identity",
                "primary_relative": "妻财",
                "visible_candidate_count": 1,
                "visible_candidate_lines": [4],
                "moving_visible_candidate_count": 1,
                "moving_visible_candidate_lines": [4],
                "specific_line_selection": 4,
                "derivation_basis": (
                    "verified_role_plus_runtime_unique_visible_candidate"
                ),
                "selection_source_ref": {
                    "pack": "divination/huangjin-ce",
                    "rule_id": "HJC-R009",
                    "source_anchor": (
                        "references/books/divination/huangjin-ce/"
                        "rules.md#HJC-R009"
                    ),
                    "verification_status": "verified",
                    "binding_digest": (
                        "2b46bab3c084a2adbdc56de6ee3ea29e9890712767a43c5cd1e68a845c23cbdc"
                    ),
                },
                "hard_verdict": None,
            },
            "hard_verdict": None,
            "source_ref": {
                "pack": "divination/huangjin-ce",
                "rule_id": "HJC-R009",
                "source_anchor": (
                    "references/books/divination/huangjin-ce/"
                    "rules.md#HJC-R009"
                ),
                "verification_status": "verified",
                "binding_digest": (
                    "2b46bab3c084a2adbdc56de6ee3ea29e9890712767a43c5cd1e68a845c23cbdc"
                ),
            },
            "unresolved_checks": [
                "月日旺衰与空破冲合",
                "动变生克与救应",
                "成败、应期与事件结果",
            ],
        }
        """
    )


def test_unclassified_question_does_not_create_a_finance_role_verdict() -> None:
    _run_runtime_assertions(
        """
        from reading_engine.calendar_core import normalize_calendar
        from reading_engine.liuyao import build_fact_layer

        calendar = normalize_calendar(
            "2026-08-17T12:00:00+08:00",
            timezone_name="Asia/Shanghai",
            location="synthetic-calendar-fixture",
        )
        snapshot = build_fact_layer(
            (6, 7, 8, 9, 6, 7),
            calendar_facts=calendar,
            casting={
                "method": "supplied_complete_cast",
                "provenance": {"kind": "synthetic_test"},
            },
        )

        selection = snapshot["output"]["useful_spirit_selection"]
        assert selection["role_adjudication"] == {
            "status": "not_requested",
            "decision_scope": None,
            "question_class": None,
            "primary_relative": None,
            "supporting_relatives": [],
            "obstacle_attention_relatives": [],
            "specific_line_selection": None,
            "hard_verdict": None,
            "source_ref": None,
            "unresolved_checks": ["需要显式结构化问题类别"],
        }
        assert all(
            item["local_rule_id"] != "HJC-R009"
            for item in snapshot["output"]["source_conditioned_patterns"]
        )
        """
    )


def test_finance_question_selects_the_only_moving_line_when_wealth_appears_twice() -> None:
    _run_runtime_assertions(
        """
        from reading_engine.calendar_core import normalize_calendar
        from reading_engine.liuyao import build_fact_layer

        calendar = normalize_calendar(
            "2026-08-17T12:00:00+08:00",
            timezone_name="Asia/Shanghai",
            location="synthetic-calendar-fixture",
        )
        snapshot = build_fact_layer(
            (6, 6, 6, 6, 6, 7),
            calendar_facts=calendar,
            casting={
                "method": "supplied_complete_cast",
                "provenance": {"kind": "synthetic_test"},
            },
            requested_useful_spirit_relatives=("妻财", "子孙"),
            question_class="finance",
        )
        adjudication = snapshot["output"]["useful_spirit_selection"][
            "role_adjudication"
        ]

        assert adjudication["specific_line_selection"] == 3
        line_adjudication = adjudication["specific_line_adjudication"]
        assert line_adjudication == {
            "status": "adjudicated_single_moving_visible_line",
            "decision_scope": "finance_primary_relative_line_identity",
            "primary_relative": "妻财",
            "visible_candidate_count": 2,
            "visible_candidate_lines": [3, 6],
            "moving_visible_candidate_count": 1,
            "moving_visible_candidate_lines": [3],
            "specific_line_selection": 3,
            "derivation_basis": (
                "verified_two_present_rule_plus_runtime_single_moving_candidate"
            ),
            "selection_source_ref": line_adjudication["selection_source_ref"],
            "hard_verdict": None,
        }
        assert line_adjudication["selection_source_ref"]["pack"] == (
            "divination/zengshan-buyi"
        )
        assert line_adjudication["selection_source_ref"]["rule_id"] == "ZR-04-04"
        assert line_adjudication["selection_source_ref"]["verification_status"] == (
            "verified"
        )
        assert len(line_adjudication["selection_source_ref"]["binding_digest"]) == 64
        assert adjudication["unresolved_checks"][0] == "月日旺衰与空破冲合"
        """
    )


def test_finance_question_keeps_two_static_visible_wealth_lines_unresolved() -> None:
    _run_runtime_assertions(
        """
        from reading_engine.calendar_core import normalize_calendar
        from reading_engine.liuyao import build_fact_layer

        calendar = normalize_calendar(
            "2026-08-17T12:00:00+08:00",
            timezone_name="Asia/Shanghai",
            location="synthetic-calendar-fixture",
        )
        snapshot = build_fact_layer(
            (6, 6, 7, 7, 6, 7),
            calendar_facts=calendar,
            casting={
                "method": "supplied_complete_cast",
                "provenance": {"kind": "synthetic_test"},
            },
            requested_useful_spirit_relatives=("妻财", "子孙"),
            question_class="finance",
        )
        adjudication = snapshot["output"]["useful_spirit_selection"][
            "role_adjudication"
        ]

        assert adjudication["specific_line_selection"] is None
        assert adjudication["specific_line_adjudication"] == {
            "status": "unresolved_multiple_visible_lines",
            "decision_scope": "finance_primary_relative_line_identity",
            "primary_relative": "妻财",
            "visible_candidate_count": 2,
            "visible_candidate_lines": [3, 4],
            "moving_visible_candidate_count": 0,
            "moving_visible_candidate_lines": [],
            "specific_line_selection": None,
            "derivation_basis": (
                "verified_role_plus_runtime_multiple_visible_candidates"
            ),
            "selection_source_ref": None,
            "hard_verdict": None,
        }
        assert adjudication["unresolved_checks"][0] == (
            "两个可见妻财爻同动静，须结合完整旺衰取舍"
        )
        """
    )


def test_finance_strength_candidates_carry_verified_seasonal_adjudication() -> None:
    _run_runtime_assertions(
        """
        from reading_engine.calendar_core import normalize_calendar
        from reading_engine.liuyao import build_fact_layer

        calendar = normalize_calendar(
            "2026-08-17T12:00:00+08:00",
            timezone_name="Asia/Shanghai",
            location="synthetic-calendar-fixture",
        )
        snapshot = build_fact_layer(
            (6, 7, 8, 9, 6, 7),
            calendar_facts=calendar,
            casting={
                "method": "supplied_complete_cast",
                "provenance": {"kind": "synthetic_test"},
            },
            requested_useful_spirit_relatives=("妻财", "子孙"),
            question_class="finance",
        )
        strength = snapshot["output"]["useful_spirit_selection"][
            "strength_evidence"
        ]

        source_rule = strength["source_rules"][0]
        assert source_rule["rule_id"] == "ZR-05-05"
        assert source_rule["verification_status"] == "verified"
        assert len(source_rule["binding_digest"]) == 64
        wealth = strength["by_relative"]["妻财"]["candidates"]
        assert len(wealth) == 1
        adjudication = wealth[0]["seasonal_adjudication"]
        assert adjudication["status"] == "adjudicated_seasonal_strength_band"
        assert adjudication["decision_scope"] == (
            "liuyao_candidate_month_order_strength_band"
        )
        assert adjudication["line"] == 4
        assert adjudication["seasonal_state"] == "旺"
        assert adjudication["strength_band"] == "旺相"
        assert adjudication["whole_candidate_strength_verdict"] is None
        assert adjudication["outcome_verdict"] is None
        assert adjudication["source_ref"]["rule_id"] == "ZR-05-05"
        assert adjudication["source_ref"]["verification_status"] == "verified"
        assert all(
            candidate["seasonal_adjudication"]["strength_band"] == "休囚"
            for candidate in strength["by_relative"]["子孙"]["candidates"]
        )
        assert "ZR-05-05" in {
            item["local_rule_id"]
            for item in snapshot["output"]["source_conditioned_patterns"]
        }
        assert strength["hard_verdict"] is None
        """
    )


def test_finance_question_does_not_promote_changed_wealth_without_visible_line() -> None:
    _run_runtime_assertions(
        """
        from reading_engine.calendar_core import normalize_calendar
        from reading_engine.liuyao import build_fact_layer

        calendar = normalize_calendar(
            "2026-08-17T12:00:00+08:00",
            timezone_name="Asia/Shanghai",
            location="synthetic-calendar-fixture",
        )
        snapshot = build_fact_layer(
            (6, 6, 7, 6, 6, 6),
            calendar_facts=calendar,
            casting={
                "method": "supplied_complete_cast",
                "provenance": {"kind": "synthetic_test"},
            },
            requested_useful_spirit_relatives=("妻财", "子孙"),
            question_class="finance",
        )
        adjudication = snapshot["output"]["useful_spirit_selection"][
            "role_adjudication"
        ]

        assert adjudication["specific_line_selection"] is None
        assert adjudication["specific_line_adjudication"] == {
            "status": "unresolved_no_visible_line",
            "decision_scope": "finance_primary_relative_line_identity",
            "primary_relative": "妻财",
            "visible_candidate_count": 0,
            "visible_candidate_lines": [],
            "moving_visible_candidate_count": 0,
            "moving_visible_candidate_lines": [],
            "specific_line_selection": None,
            "derivation_basis": (
                "verified_role_plus_runtime_no_visible_candidate"
            ),
            "selection_source_ref": None,
            "hard_verdict": None,
        }
        assert adjudication["unresolved_checks"][0] == "妻财伏神或变爻的取用"
        """
    )


def test_liuyao_validator_rejects_a_tampered_role_adjudication() -> None:
    _run_runtime_assertions(
        """
        from reading_engine.calendar_core import normalize_calendar
        from reading_engine.liuyao import build_fact_layer, validate_fact_layer

        calendar = normalize_calendar(
            "2026-08-17T12:00:00+08:00",
            timezone_name="Asia/Shanghai",
            location="synthetic-calendar-fixture",
        )
        snapshot = build_fact_layer(
            (6, 7, 8, 9, 6, 7),
            calendar_facts=calendar,
            casting={
                "method": "supplied_complete_cast",
                "provenance": {"kind": "synthetic_test"},
            },
            requested_useful_spirit_relatives=("妻财", "子孙"),
            question_class="finance",
        )
        snapshot["output"]["useful_spirit_selection"]["role_adjudication"][
            "specific_line_selection"
        ] = 2

        findings = validate_fact_layer(snapshot)

        assert findings["ok"] is False
        assert "liuyao_output_mismatch" in findings["codes"]
        """
    )

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


def test_time_check_uses_branch_intersections_and_correct_representatives() -> None:
    _run_runtime_assertions(
        """
        from reading_engine.providers import TimeCheckProvider

        candidates = TimeCheckProvider._candidate_datetimes(
            date_value="1994-04-30",
            timezone_name="Asia/Shanghai",
            range_start="05:30",
            range_end="05:45",
        )
        assert [item[0] for item in candidates] == list("子丑寅卯辰巳午未申酉戌亥")
        assert [item[1].strftime("%H:%M") for item in candidates] == [
            "00:00", "02:00", "04:00", "06:00", "08:00", "10:00",
            "12:00", "14:00", "16:00", "18:00", "20:00", "22:00",
        ]
        # The window intersects 卯 even though its representative is 15
        # minutes outside the window.  It must not be decided by the sample
        # instant alone.
        assert [item[0] for item in candidates if item[2]] == ["卯"]

        midnight = TimeCheckProvider._candidate_datetimes(
            date_value="1994-04-30",
            timezone_name="Asia/Shanghai",
            range_start="23:30",
            range_end="00:30",
        )
        assert [item[0] for item in midnight if item[2]] == ["子"]
        """
    )


def test_calendar_contract_records_applied_true_solar_time() -> None:
    _run_runtime_assertions(
        """
        from reading_engine.calendar_core import normalize_calendar

        calendar = normalize_calendar(
            "1994-04-30T05:55:00+08:00",
            timezone_name="Asia/Shanghai",
            location="synthetic-calendar-fixture",
            longitude=120.0,
            latitude=30.0,
            coordinate_source="synthetic-fixture",
            time_basis_policy="local_apparent_solar-v1",
            zi_hour_policy="midnight",
        )

        assert calendar["time_basis"]["policy"] == "local_apparent_solar-v1"
        assert calendar["true_solar_time"]["status"] == "apparent_solar_applied"
        assert calendar["time_basis"]["total_correction_seconds"] != 0
        assert calendar["effective_datetime"] != calendar["civil_datetime"]
        assert calendar["ganzhi"] == {
            "year": "甲戌",
            "month": "戊辰",
            "day": "丙戌",
            "hour": "辛卯",
        }
        """
    )


def test_bazi_source_rule_uses_current_four_pillar_fact_path() -> None:
    _run_runtime_assertions(
        """
        from bazi_fact_adapter import _source_conditioned_patterns

        patterns = _source_conditioned_patterns(
            {
                "four_pillars": {
                    "year": "庚辰",
                    "month": "丙戌",
                    "day": "己酉",
                    "hour": "丁卯",
                },
                "hidden_stems": {
                    "year": [{"stem": "戊", "residual": 1.0}],
                    "month": [{"stem": "戊", "residual": 1.0}],
                    "day": [{"stem": "辛", "residual": 1.0}],
                    "hour": [{"stem": "乙", "residual": 1.0}],
                },
            }
        )

        matched = next(
            item
            for item in patterns
            if item["local_rule_id"] == "DR-01-01"
        )
        assert matched["status"] == "predicate_matched_not_verdict"
        assert "verdict" not in matched
        assert any("/four_pillars/" in path for path in matched["fact_paths"])
        assert any("/hidden_stems/" in path for path in matched["fact_paths"])
        assert not any(
            "/calendar_normalization/ganzhi" in path
            for path in matched["fact_paths"]
        )
        """
    )


def test_time_check_evidence_keeps_positive_and_negative_signals() -> None:
    _run_runtime_assertions(
        """
        from reading_engine.providers import TimeCheckProvider

        negative = TimeCheckProvider._event_evidence(
            {
                "four_pillars": {
                    "year": "甲子",
                    "month": "甲辰",
                    "day": "甲辰",
                    "hour": "甲辰",
                },
                "day_master": {"stem": "丙"},
            },
            {
                "event_id": "negative-only",
                "domain": "career",
                "year_pillar": "丙午",
            },
        )
        assert negative["evidence_score"] == -2
        assert negative["matched"] is False
        assert negative["reasons"] == ["negative_branch_relation"]

        mixed = TimeCheckProvider._event_evidence(
            {
                "four_pillars": {
                    "year": "甲丑",
                    "month": "甲午",
                    "day": "甲辰",
                    "hour": "甲辰",
                },
                "day_master": {"stem": "丙"},
            },
            {
                "event_id": "mixed",
                "domain": "career",
                "year_pillar": "丙子",
            },
        )
        # 丑子 is 六合 while 午子 is 六冲; both signals survive and cancel
        # deterministically rather than depending on pillar iteration order.
        assert mixed["evidence_score"] == 0
        assert mixed["matched"] is False
        assert mixed["reasons"] == [
            "positive_branch_relation",
            "negative_branch_relation",
        ]
        """
    )


def test_time_check_evidence_names_a_zero_signal_event() -> None:
    _run_runtime_assertions(
        """
        from reading_engine.providers import TimeCheckProvider

        neutral = TimeCheckProvider._event_evidence(
            {
                "four_pillars": {
                    "year": "甲子",
                    "month": "甲子",
                    "day": "甲子",
                    "hour": "甲子",
                },
                "day_master": {"stem": "丙"},
            },
            {
                "event_id": "neutral-only",
                "domain": "location",
                "year_pillar": "甲巳",
            },
        )
        assert neutral["evidence_score"] == 0
        assert neutral["matched"] is False
        assert neutral["reasons"] == ["no_supporting_or_opposing_signal"]
        """
    )


def test_time_check_does_not_match_events_to_eliminated_candidates() -> None:
    _run_runtime_assertions(
        """
        from reading_engine.providers import TimeCheckProvider

        rows, matches = TimeCheckProvider._rank_candidates(
            [
                {
                    "candidate_id": "hour-outside",
                    "hour_branch": "子",
                    "within_known_time_range": False,
                    "four_pillars": {
                        "year": "甲子",
                        "month": "甲辰",
                        "day": "甲辰",
                        "hour": "甲辰",
                    },
                    "day_master": {"stem": "丙"},
                },
                {
                    "candidate_id": "hour-inside",
                    "hour_branch": "丑",
                    "within_known_time_range": True,
                    "four_pillars": {
                        "year": "甲丑",
                        "month": "甲辰",
                        "day": "甲辰",
                        "hour": "甲辰",
                    },
                    "day_master": {"stem": "丙"},
                },
            ],
            (
                {
                    "event_id": "event",
                    "domain": "career",
                    "occurred_at": "2026-01-01T12:00:00+08:00",
                "year_pillar": "丙子",
                },
            ),
        )
        outside = next(row for row in rows if row["candidate_id"] == "hour-outside")
        assert outside["elimination_reasons"] == ["outside_known_time_range"]
        assert outside["matched_event_ids"] == []
        assert matches[0]["matched_candidate_ids"] == ["hour-inside"]
        """
    )


def test_liuren_location_direction_stays_a_structural_candidate() -> None:
    _run_runtime_assertions(
        """
        from liuren_calc import _stage_branch_directions

        rows = _stage_branch_directions(
            [
                {"stage": "initial", "branch": "子"},
                {"stage": "middle", "branch": "卯"},
                {"stage": "final", "branch": "酉"},
            ]
        )
        assert [row["direction_chinese"] for row in rows] == ["正北", "正东", "正西"]
        for row in rows:
            assert row["scope"] == "symbolic_direction_candidate_only"
            assert row["source_binding_status"] == "unverified_source_excerpt_not_in_release"
            assert "source_rule" not in row
        """
    )


def test_liuren_money_does_not_activate_unverified_or_unbound_rules() -> None:
    _run_runtime_assertions(
        """
        from liuren_calc import _activated_dimension_rule_ids, _liuren_rule_evidence

        projected = {
            "wealth_presence": True,
            "wealth_stage_strength": [
                {
                    "stage": "initial",
                    "branch": "午",
                    "six_relative": "妻财",
                    "season_strength": "旺",
                }
            ],
            "wealth_void_status": [],
            "wealth_general_modifier": [],
        }
        evidence = _liuren_rule_evidence(
            "money",
            projected=projected,
            transmissions=[{"stage": "initial", "branch": "午", "is_xunkong": False}],
        )
        assert [row["rule_id"] for row in evidence["matched"]] == ["LM-R20"]
        assert all(row["rule_id"] != "LR-15" for row in evidence["matched"])
        assert _activated_dimension_rule_ids(
            canonical="money",
            eligible_rule_ids=["LM-R20", "LR-15", "LR-19"],
            projected=projected,
            output={},
            transmissions_to_day=[],
            initial_final={},
            stage_flow=[],
        ) == ["LM-R20"]
        """
    )


def test_liuren_work_target_contract_activates_only_verified_rule() -> None:
    _run_runtime_assertions(
        """
        from liuren_calc import _activated_dimension_rule_ids, _liuren_rule_evidence

        bound = {
            "target_relative": "官鬼",
            "target_contract_status": "bound",
            "target_presence": True,
            "target_strength": [
                {
                    "stage": "initial",
                    "branch": "午",
                    "six_relative": "官鬼",
                    "season_strength": "旺",
                    "is_xunkong": False,
                }
            ],
            "target_general_modifier": [],
        }
        evidence = _liuren_rule_evidence(
            "work",
            projected=bound,
            transmissions=[{"stage": "initial", "branch": "午", "is_xunkong": False}],
        )
        assert [row["rule_id"] for row in evidence["matched"]] == ["LR-19"]
        assert _activated_dimension_rule_ids(
            canonical="work",
            eligible_rule_ids=["LM-R09", "LM-R15", "LM-R22", "LR-19"],
            projected=bound,
            output={},
            transmissions_to_day=[],
            initial_final={},
            stage_flow=[],
        ) == ["LR-19"]

        missing = {
            **bound,
            "target_relative": None,
            "target_contract_status": "missing_target_relative",
            "target_presence": False,
            "target_strength": [],
        }
        missing_evidence = _liuren_rule_evidence(
            "work",
            projected=missing,
            transmissions=[],
        )
        assert missing_evidence["matched"] == []
        assert missing_evidence["scope_boundaries"] == []
        assert missing_evidence["not_evaluated"][0]["rule_id"] == "LR-19"
        """
    )


def test_liuren_calculator_and_fact_adapter_share_the_source_table_contract() -> None:
    _run_runtime_assertions(
        """
        import liuren_calc
        import liuren_fact_adapter

        assert (
            liuren_calc.LIUREN_SOURCE_TABLE_SHA256
            == liuren_fact_adapter.SOURCE_TABLE_SHA256
        )
        liuren_calc._liuren_source_tables.cache_clear()
        liuren_fact_adapter._source_table.cache_clear()
        liuren_calc._liuren_source_tables()
        liuren_fact_adapter._source_table()
        """
    )

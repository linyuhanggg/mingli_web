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


def test_verified_ziping_rule_adjudicates_only_the_month_pattern_entry() -> None:
    _run_runtime_assertions(
        """
        from bazi_fact_adapter import build_from_pillars

        snapshot = build_from_pillars(
            ["甲戌", "戊辰", "丙戌", "辛卯"],
            gender="female",
            source="text",
            source_ref="synthetic-test",
        )
        tool = snapshot["output"]["interpretive_candidates"]["reasoning_tools"][
            "ziping_month_pattern_adjudication"
        ]
        output = tool["output"]

        assert tool["tool_id"] == "bazi.tool.ziping_month_pattern_adjudication"
        assert tool["source_refs"] == [
            {
                "pack": "bazi/ziping-zhenquan",
                "rule_id": "ZPR-01",
                "source_anchor": "references/books/bazi/ziping-zhenquan/rules.md#ZPR-01",
                "verification_status": "verified",
                "binding_digest": (
                    "03453f3b83f4c78c254bfbaa0d7a064e57ed6aad17b4efe5c386d3919b95c33e"
                ),
            }
        ]
        assert output["status"] == "adjudicated_pattern_entry"
        assert output["decision_scope"] == "ziping_month_command_pattern_entry"
        assert output["month_main_qi_ten_god"] == "食神"
        assert output["pattern_entry"] == "食神"
        assert output["pattern_label"] == "食神格入口"
        assert output["exception_branch"] is None
        assert output["hard_verdict"] is None
        assert "格局成败与救应" in output["unresolved_checks"]
        """
    )


def test_ziping_same_element_month_enters_jianlu_yuejie_exception() -> None:
    _run_runtime_assertions(
        """
        from bazi_fact_adapter import build_from_pillars

        snapshot = build_from_pillars(
            ["甲子", "丙寅", "甲子", "甲子"],
            gender="male",
            source="text",
            source_ref="synthetic-test",
        )
        output = snapshot["output"]["interpretive_candidates"]["reasoning_tools"][
            "ziping_month_pattern_adjudication"
        ]["output"]

        assert output["month_main_qi_ten_god"] == "比肩"
        assert output["status"] == "exception_requires_external_selection"
        assert output["pattern_entry"] is None
        assert output["pattern_label"] == "建禄月劫分支"
        assert output["exception_branch"] == "建禄月劫另取财官煞食"
        assert output["hard_verdict"] is None
        assert "透干会支另取财官煞食" in output["unresolved_checks"]
        """
    )


def test_bazi_fact_contract_rejects_a_missing_pattern_adjudication() -> None:
    _run_runtime_assertions(
        """
        from bazi_fact_adapter import build_from_pillars
        from fact_contracts.bazi import BaziFactContract

        snapshot = build_from_pillars(
            ["甲戌", "戊辰", "丙戌", "辛卯"],
            gender="female",
            source="text",
            source_ref="synthetic-test",
        )
        del snapshot["output"]["interpretive_candidates"]["reasoning_tools"][
            "ziping_month_pattern_adjudication"
        ]

        findings = BaziFactContract().validate_output(
            snapshot,
            snapshot["output"],
        )

        assert any(
            item["code"] == "bazi_pattern_adjudication_missing"
            for item in findings
        )
        """
    )


def test_tiaohou_candidate_reports_each_rules_real_binding_status() -> None:
    _run_runtime_assertions(
        """
        from bazi_fact_adapter import build_from_pillars

        verified = build_from_pillars(
            ["甲戌", "戊辰", "丙戌", "辛卯"],
            gender="female",
            source="text",
            source_ref="synthetic-test",
        )["output"]["interpretive_candidates"]["reasoning_tools"][
            "tiaohou_candidates"
        ]
        inactive = build_from_pillars(
            ["甲子", "乙亥", "甲子", "甲子"],
            gender="male",
            source="text",
            source_ref="synthetic-test",
        )["output"]["interpretive_candidates"]["reasoning_tools"][
            "tiaohou_candidates"
        ]

        assert verified["output"]["rule_id"] == "QR-02-01"
        assert verified["output"]["verification_status"] == "verified"
        assert verified["output"]["status"] == "adjudicated_seasonal_priority"
        assert verified["output"]["hard_verdict"] is None
        assert verified["output"]["priority_stems"]
        assert verified["source_refs"][0]["binding_digest"]
        assert verified["confidence_bucket"] == "medium"

        assert inactive["output"]["rule_id"] == "QR-01-04"
        assert inactive["output"]["verification_status"] == "inactive_unverified"
        assert inactive["confidence_bucket"] == "low"
        assert inactive["output"]["status"] == "unavailable_unverified_rule"
        assert inactive["output"]["priority_stems"] == []
        assert inactive["output"]["matches"] == []
        assert inactive["output"]["hard_verdict"] is None
        """
    )


def test_bazi_fact_contract_rejects_unverified_tiaohou_output() -> None:
    _run_runtime_assertions(
        """
        from bazi_fact_adapter import build_from_pillars
        from fact_contracts.bazi import BaziFactContract

        snapshot = build_from_pillars(
            ["甲子", "乙亥", "甲子", "甲子"],
            gender="male",
            source="text",
            source_ref="synthetic-test",
        )
        tool = snapshot["output"]["interpretive_candidates"]["reasoning_tools"][
            "tiaohou_candidates"
        ]
        tool["output"]["priority_stems"] = ["丙"]

        findings = BaziFactContract().validate_output(
            snapshot,
            snapshot["output"],
        )

        assert any(
            item["code"] == "bazi_tiaohou_adjudication_invalid"
            for item in findings
        )
        """
    )


def test_verified_month_order_rule_adjudicates_only_the_seasonal_state() -> None:
    _run_runtime_assertions(
        """
        from bazi_fact_adapter import build_from_pillars

        strength = build_from_pillars(
            ["庚辰", "丙戌", "丙戌", "辛卯"],
            gender="male",
            source="text",
            source_ref="synthetic-test",
        )["output"]["interpretive_candidates"]["strength"]
        adjudication = strength["month_order_adjudication"]

        assert strength["seasonal_state"] == "休"
        assert adjudication["status"] == "adjudicated_month_order_state"
        assert adjudication["decision_scope"] == "bazi_month_order_seasonal_state"
        assert adjudication["day_master_element"] == "火"
        assert adjudication["month_command_element"] == "土"
        assert adjudication["seasonal_state"] == "休"
        assert adjudication["whole_chart_strength_verdict"] is None
        assert adjudication["useful_god_verdict"] is None
        assert adjudication["source_ref"] == {
            "pack": "bazi/sanming-tonghui",
            "rule_id": "R-02-04",
            "source_anchor": (
                "references/books/bazi/sanming-tonghui/rules.md#R-02-04"
            ),
            "verification_status": "verified",
            "binding_digest": (
                "77b387e17e65b50c7cbcdba3cc8ef5b170499c6d5c07461856b710d5aa50759e"
            ),
        }
        assert "全局根气、生扶、克泄与合化" in adjudication["unresolved_checks"]
        """
    )


def test_bazi_fact_contract_rejects_a_forged_month_order_adjudication() -> None:
    _run_runtime_assertions(
        """
        from bazi_fact_adapter import build_from_pillars
        from fact_contracts.bazi import BaziFactContract

        snapshot = build_from_pillars(
            ["庚辰", "丙戌", "丙戌", "辛卯"],
            gender="male",
            source="text",
            source_ref="synthetic-test",
        )
        snapshot["output"]["interpretive_candidates"]["strength"][
            "month_order_adjudication"
        ]["seasonal_state"] = "旺"

        findings = BaziFactContract().validate_output(
            snapshot,
            snapshot["output"],
        )

        assert any(
            item["code"] == "bazi_month_order_adjudication_invalid"
            for item in findings
        )
        """
    )

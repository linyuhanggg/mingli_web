#!/usr/bin/env python3
"""Independent-review regressions for the Task 7J Taiyi release gate."""

from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

import audit_taiyi_provider
import reading_evidence_bundle
import reading_source_plan
from reading_engine import taiyi
from reading_engine.contracts import CalculationResult
from reading_engine.fact_index import build_fact_index
from reading_engine.providers import TaiyiProvider


ROOT = Path(__file__).resolve().parents[1]
RAW_EXTERNAL_FIXTURE = ROOT / "references/fixtures/kintaiyi-taiyi-v51.yaml"


def _calculation(bureau: int) -> CalculationResult:
    output = taiyi.build_annual_board_from_accumulated_year(bureau)
    return CalculationResult.create(
        system="taiyi",
        provider_id=TaiyiProvider.provider_id,
        provider_version=TaiyiProvider.provider_version,
        input_payload={"bureau": bureau},
        facts={"chart_facts": {"output": output}},
    )


class TaiyiEvidenceIsolationTests(unittest.TestCase):
    def test_all_ten_predicate_identities_are_semantic_terms_from_current_facts(self) -> None:
        for identifier in taiyi.BOARD_PREDICATE_IDS:
            bureau = next(
                bureau
                for bureau in range(1, 73)
                if identifier
                in {
                    row["id"]
                    for row in taiyi.build_annual_board_from_accumulated_year(
                        bureau
                    )["board_predicates"]
                }
            )
            calculation = _calculation(bureau)
            fact_index = build_fact_index(
                calculation,
                reading_id=identifier.lower().replace("-", "") * 6,
                version=1,
            )
            terms = reading_evidence_bundle._semantic_terms(
                {"evidence_questions": ["核对当前年局的确定性关系"]},
                {"question_dimensions": ["state"]},
                fact_index,
                counter=False,
            )
            predicate = next(
                row
                for row in calculation.facts["chart_facts"]["output"][
                    "board_predicates"
                ]
                if row["id"] == identifier
            )
            with self.subTest(predicate=identifier):
                self.assertIn(identifier, terms)
                self.assertIn(predicate["name"], terms)

    def test_real_bundle_returns_each_exact_clean_predicate_rule(self) -> None:
        contracts = {
            row["id"]: row
            for row in taiyi.source_table()["board_predicate_contracts"]
        }
        for identifier, contract in contracts.items():
            bureau = next(
                bureau
                for bureau in range(1, 73)
                if identifier
                in {
                    row["id"]
                    for row in taiyi.build_annual_board_from_accumulated_year(
                        bureau
                    )["board_predicates"]
                }
            )
            calculation = _calculation(bureau)
            reading_id = (identifier.lower().replace("-", "") * 6)[:32]
            goal = {
                "source_packs": ["san-shi/taiyi-shenshu"],
                "calculation_object": "macro_historical",
                "question_dimensions": ["state"],
                "evidence_questions": [
                    f"核对当前年局的 {identifier} {contract['name']} 关系"
                ],
            }
            plan = reading_source_plan.compile_source_plan(
                "taiyi", goal, calculation.facts
            )
            fact_index = build_fact_index(
                calculation, reading_id=reading_id, version=1
            )
            bundle = reading_evidence_bundle.compile_evidence_bundle(
                goal,
                calculation.facts,
                plan,
                fact_index=fact_index,
                reading_id=reading_id,
                version=1,
            )
            nodes = {node.rule_id: node for node in bundle.evidence}
            rule_id = f"san-shi/taiyi-shenshu#{identifier}"
            with self.subTest(predicate=identifier, bureau=bureau):
                self.assertIn(rule_id, nodes)
                node = nodes[rule_id]
                self.assertEqual(
                    node.anchor,
                    f"fulltext.md {contract['source_anchor']}",
                )
                self.assertNotIn("|", node.assertion)
                self.assertNotIn("---", node.assertion)
                self.assertNotIn("source manifest", node.assertion.casefold())
                self.assertLess(len(node.assertion), 160)


class TaiyiIndependentOracleTests(unittest.TestCase):
    def test_raw_upstream_projection_is_hash_bound_and_replayed(self) -> None:
        self.assertTrue(RAW_EXTERNAL_FIXTURE.is_file())
        payload = yaml.safe_load(RAW_EXTERNAL_FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema_version"], "kintaiyi-taiyi-raw-v1")
        self.assertEqual(len(payload["raw_cases"]), 72)
        self.assertEqual(
            payload["source"]["commit"],
            "68892c6bfe3a9635ff4a19a5f14559fff1adf4ab",
        )
        self.assertEqual(
            payload["projection_contract"]["projection_kind"],
            "static source projection with literal tables and labelled derivations; not pan() output",
        )
        self.assertIn(
            "config.find_cal yangcal",
            payload["projection_contract"]["upstream_origins"][
                "host_count_literal"
            ],
        )
        self.assertIn(
            "jigod_map",
            payload["projection_contract"]["upstream_origins"][
                "jishen_mapping"
            ],
        )
        report = audit_taiyi_provider.audit_taiyi_provider()
        self.assertTrue(report["provider_ready"], report)
        self.assertEqual(report["counts"]["external_raw_boards"], 72)
        self.assertEqual(report["counts"]["external_raw_mismatches"], 0)

    def test_audit_rejects_raw_projection_mutation(self) -> None:
        payload = yaml.safe_load(RAW_EXTERNAL_FIXTURE.read_text(encoding="utf-8"))
        payload["raw_cases"][0]["raw"]["taiyi_palace_literal"] = "巽"
        with tempfile.TemporaryDirectory() as temporary:
            mutated = Path(temporary) / RAW_EXTERNAL_FIXTURE.name
            mutated.write_text(
                yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            report = audit_taiyi_provider.audit_taiyi_provider(
                raw_external_fixture_path=mutated
            )
        self.assertFalse(report["provider_ready"], report)
        self.assertIn(
            "Taiyi raw external fixture artifact hash mismatch",
            report["findings"],
        )

    def test_all_ten_long_cycle_deities_match_independent_year_oracle(self) -> None:
        report = audit_taiyi_provider.audit_taiyi_provider()
        self.assertTrue(report["provider_ready"], report)
        self.assertEqual(report["counts"]["long_cycle_years"], 360)
        self.assertEqual(report["counts"]["long_cycle_comparisons"], 3600)

    def test_all_72_predicate_sets_and_fact_paths_match_independent_oracle(self) -> None:
        report = audit_taiyi_provider.audit_taiyi_provider()
        self.assertTrue(report["provider_ready"], report)
        self.assertEqual(report["counts"]["predicate_boards"], 72)
        self.assertEqual(report["counts"]["predicate_mismatches"], 0)

    def test_audit_rejects_constant_wrong_wufu(self) -> None:
        original = taiyi._long_cycle_deities

        def wrong(lunar_year: int) -> dict:
            result = copy.deepcopy(original(lunar_year))
            result["wufu"]["position"] = "中"
            return result

        with mock.patch.object(taiyi, "_long_cycle_deities", wrong):
            report = audit_taiyi_provider.audit_taiyi_provider()
        self.assertFalse(report["provider_ready"], report)
        self.assertGreater(report["counts"]["long_cycle_mismatches"], 0)

    def test_audit_rejects_shifted_four_deity_positions(self) -> None:
        original = taiyi._long_cycle_deities
        order = (1, 2, 3, 4, 5, 6, 7, 8, 9, "絳", "明", "玉")

        def wrong(lunar_year: int) -> dict:
            result = copy.deepcopy(original(lunar_year))
            for name in ("sishen", "tianyi", "diyi", "zhifu"):
                position = result[name]["position"]
                result[name]["position"] = order[(order.index(position) + 1) % 12]
            return result

        with mock.patch.object(taiyi, "_long_cycle_deities", wrong):
            report = audit_taiyi_provider.audit_taiyi_provider()
        self.assertFalse(report["provider_ready"], report)
        self.assertGreater(report["counts"]["long_cycle_mismatches"], 0)

    def test_audit_rejects_swapped_predicate_ids(self) -> None:
        original = taiyi._board_predicates

        def wrong(core: dict) -> list[dict]:
            result = copy.deepcopy(original(core))
            for row in result:
                if row["id"] == "TY-P05":
                    row["id"] = "TY-P06"
                elif row["id"] == "TY-P06":
                    row["id"] = "TY-P05"
            return result

        with mock.patch.object(taiyi, "_board_predicates", wrong):
            report = audit_taiyi_provider.audit_taiyi_provider()
        self.assertFalse(report["provider_ready"], report)
        self.assertGreater(report["counts"]["predicate_mismatches"], 0)


if __name__ == "__main__":
    unittest.main()

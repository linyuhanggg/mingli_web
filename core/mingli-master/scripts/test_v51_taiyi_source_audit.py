#!/usr/bin/env python3
"""Pre-implementation source audit for the selected Taiyi annual profile."""

from __future__ import annotations

import hashlib
import json
import os
import unittest
from pathlib import Path

import yaml

from reading_engine import calendar_core


ROOT = Path(__file__).resolve().parents[1]
SOURCE_TABLE_PATH = ROOT / "references/matrices/taiyi-source-tables-v1.yaml"
FIXTURE_PATH = ROOT / "references/fixtures/taiyi-v51.yaml"
RAW_EXTERNAL_PATH = ROOT / "references/fixtures/kintaiyi-taiyi-v51.yaml"
RAW_GENERATOR_PATH = ROOT / "scripts/fixtures/kintaiyi_taiyi_fixture_generator.py"
MATRIX_PATH = ROOT / "references/matrices/algorithm-source-dependencies.yaml"
FULLTEXT_PATH = (
    Path(
        os.environ.get(
            "MINGLI_RESEARCH_ROOT",
            ROOT / "__missing_external_research__",
        )
    ).resolve()
    / "references/fulltext/san-shi/taiyi-shenshu/fulltext.md"
)
SOURCE_TABLE_SHA256 = "a5ade0bfb7bcdf89aeb0862d5992fd6fb340d640ab1a593c6381cd480df5c393"
FIXTURE_SHA256 = "fb736b6a4f8908bd0d4602952df347f99248ba1162cd17c93720de5b3aa3c5b7"
FULLTEXT_SHA256 = "ecacc021ea180803b10b3b97a42ce602ea50bc342c73d30883012629cabc111c"
EXTERNAL_CASES_SHA256 = "15051753ab6a63e7656e0665f853e4b501376ff91233eb4100855ef5eb113c6d"
RAW_EXTERNAL_SHA256 = "502a1178442a008bd5d900f9e1461f8fd5f5e23da00e61525ecac25a119b6e0f"
RAW_GENERATOR_SHA256 = "067ca9e107116d9e1ef2e2a4999371c5287f1d18a5ef37d7de8fc0c522b32598"
RAW_CASES_SHA256 = "a128b4de6ca06d8374d5acfb87a534c9c3ff89d8c4a9237e35946ecb6ccc7b54"
REQUIRED_DEPENDENCIES = {
    "taiyi.calendar.annual-epoch-and-scope",
    "taiyi.cycle.six-ji-five-zi-yuan",
    "taiyi.plate.taiyi-tianmu-jishen-shiji",
    "taiyi.plate.host-guest-counts-and-generals",
    "taiyi.deities.independent-long-cycle-epochs",
    "taiyi.evidence.board-predicates-and-scope",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _table() -> dict:
    return yaml.safe_load(SOURCE_TABLE_PATH.read_text(encoding="utf-8"))


def _fixture() -> dict:
    return yaml.safe_load(FIXTURE_PATH.read_text(encoding="utf-8"))


def _raw_external() -> dict:
    return yaml.safe_load(RAW_EXTERNAL_PATH.read_text(encoding="utf-8"))


def _raw_to_canonical(raw: dict) -> dict:
    host = int(raw["host_count_literal"])
    guest = int(raw["guest_count_literal"])
    host_general = host // 10 if host % 10 == 0 else host % 10
    guest_general = guest // 10 if guest % 10 == 0 else guest % 10
    return {
        "taiyi": raw["taiyi_palace_literal"],
        "tianmu_position": raw["wenchang_position_literal"],
        "host_count": host,
        "host_general": host_general,
        "host_assistant": (host_general * 3) % 10 or 5,
        "shiji": raw["shiji_position_literal"],
        "guest_count": guest,
        "guest_general": guest_general,
        "guest_assistant": (guest_general * 3) % 10 or 5,
        "jishen": raw["jishen_mapping"],
    }


def _one_based_mod(value: int, modulus: int) -> int:
    return (value - 1) % modulus + 1


def _count_from_eye(
    eye: str,
    taiyi: str,
    *,
    ring: list[str],
    main: dict[str, int],
) -> int:
    if eye == taiyi:
        return main[eye]
    total = main.get(eye, 1)
    index = (ring.index(eye) + 1) % len(ring)
    while ring[index] != taiyi:
        total += main.get(ring[index], 0)
        index = (index + 1) % len(ring)
    return total


class TaiyiSourceAuditTests(unittest.TestCase):
    def test_all_source_artifacts_are_hash_bound(self) -> None:
        self.assertEqual(_sha256(SOURCE_TABLE_PATH), SOURCE_TABLE_SHA256)
        self.assertEqual(_sha256(FIXTURE_PATH), FIXTURE_SHA256)
        self.assertEqual(_sha256(FULLTEXT_PATH), FULLTEXT_SHA256)
        self.assertEqual(_sha256(RAW_EXTERNAL_PATH), RAW_EXTERNAL_SHA256)
        self.assertEqual(_sha256(RAW_GENERATOR_PATH), RAW_GENERATOR_SHA256)

    def test_primary_text_contains_each_selected_formula_and_table_anchor(self) -> None:
        text = FULLTEXT_PATH.read_text(encoding="utf-8")
        for excerpt in (
            "積得一百九十三萬七千二百八十一筭",
            "以周紀法三百六十去之不盡以紀法六十去之",
            "以元法七十二去之又不盡以太乙小周法二十四除之",
            "命起武徳順行十六神遇隂徳大武重留一筭",
            "以計神加和徳宫求文昌所臨宫",
            "若天目在正宫則按本數若天目間神則加一數而行筭至太乙宫止",
            "陽局天目地目計神主客大小將立成",
            "推君基太乙法",
            "四神三元五紀立成",
        ):
            with self.subTest(excerpt=excerpt):
                self.assertIn(excerpt, text)

    def test_algorithm_matrix_declares_every_taiyi_dependency_before_code(self) -> None:
        matrix = yaml.safe_load(MATRIX_PATH.read_text(encoding="utf-8"))
        profile = matrix["providers"]["taiyi"]
        ids = {row["id"] for row in profile["dependencies"]}
        self.assertEqual(ids, REQUIRED_DEPENDENCIES)
        self.assertEqual(profile["source_audit_status"], "source_verified")
        for dependency in profile["dependencies"]:
            self.assertEqual(dependency["status"], "verified")
            artifact = dependency["source_artifact"]
            self.assertEqual(artifact["sha256"], SOURCE_TABLE_SHA256)
            self.assertEqual(
                artifact["schema_version"],
                "mingli-taiyi-source-tables-v1",
            )

    def test_epoch_translation_is_one_based_and_does_not_mix_profiles(self) -> None:
        table = _table()
        epochs = table["epoch_profiles"]
        self.assertEqual(len(epochs), 4)
        annual = epochs["jinjing-annual-tang-jiazi-v1"]
        self.assertEqual(
            annual["anchor_lunar_year_ce"] + annual["derived_ce_offset"],
            annual["anchor_accumulated_year"],
        )
        self.assertEqual(annual["anchor_accumulated_year"], 1_937_281)
        self.assertEqual(
            {row["epoch_profile"] for row in table["long_cycle_deities"].values()},
            {
                "upper-jiayin-long-cycle-v1",
                "wufu-dayou-long-cycle-v1",
                "xiaoyou-four-deity-v1",
            },
        )

    def test_complete_360_year_cycle_has_six_ji_five_yuan_and_72_bureaus(self) -> None:
        states = []
        for accumulated_year in range(1, 361):
            position = _one_based_mod(accumulated_year, 360)
            states.append(
                (
                    (position - 1) // 60 + 1,
                    (position - 1) // 72 + 1,
                    _one_based_mod(accumulated_year, 72),
                    _one_based_mod(accumulated_year, 3),
                )
            )
        self.assertEqual({row[0] for row in states}, set(range(1, 7)))
        self.assertEqual({row[1] for row in states}, set(range(1, 6)))
        self.assertEqual({row[2] for row in states}, set(range(1, 73)))
        self.assertEqual({row[3] for row in states}, {1, 2, 3})

    def test_all_72_primary_rows_recompute_from_independent_formula(self) -> None:
        table = _table()
        positions = table["positions"]
        ring = list(positions["sixteen_ring_forward"])
        main = {
            str(position): int(number)
            for position, number in positions["main_palaces"].items()
        }
        taiyi_order = list(positions["taiyi_forward_order"])
        tianmu_cycle = list(positions["tianmu_expanded_cycle"])
        branches = list("子丑寅卯辰巳午未申酉戌亥")
        rows = table["annual_yang_72_source_rows"]
        self.assertEqual([row["bureau"] for row in rows], list(range(1, 73)))
        for row in rows:
            with self.subTest(bureau=row["bureau"]):
                bureau = int(row["bureau"])
                taiyi = taiyi_order[(_one_based_mod(bureau, 24) - 1) // 3]
                tianmu = tianmu_cycle[_one_based_mod(bureau, 18) - 1]
                jishen = branches[(2 - (bureau - 1)) % 12]
                shiji = ring[
                    (
                        ring.index(str(tianmu["position"]))
                        + ring.index("艮")
                        - ring.index(jishen)
                    )
                    % 16
                ]
                host = _count_from_eye(
                    str(tianmu["position"]), taiyi, ring=ring, main=main
                )
                guest = _count_from_eye(shiji, taiyi, ring=ring, main=main)
                host_general = host // 10 if host % 10 == 0 else host % 10
                guest_general = guest // 10 if guest % 10 == 0 else guest % 10
                self.assertEqual(
                    {
                        "taiyi": taiyi,
                        "tianmu": tianmu["name"],
                        "tianmu_position": tianmu["position"],
                        "host_count": host,
                        "host_general": host_general,
                        "host_assistant": (host_general * 3) % 10 or 5,
                        "shiji": shiji,
                        "guest_count": guest,
                        "guest_general": guest_general,
                        "guest_assistant": (guest_general * 3) % 10 or 5,
                        "jishen": jishen,
                    },
                    {key: row[key] for key in row if key != "bureau"},
                )

    def test_exact_board_predicates_are_source_anchored_before_activation(self) -> None:
        predicates = _table()["board_predicate_contracts"]
        self.assertEqual(
            [row["id"] for row in predicates],
            [f"TY-P{index:02d}" for index in range(1, 11)],
        )
        self.assertEqual(
            {row["relation"] for row in predicates},
            {
                "same_position",
                "opposite_position",
                "same_palace",
                "opposite_palace",
            },
        )
        for row in predicates:
            self.assertRegex(row["source_anchor"], r"^L(?:430|442|450|454)$")
            self.assertTrue(row["left_fact_path"].startswith("/"))
            self.assertTrue(row["right_fact_path"].startswith("/"))
            self.assertEqual(row["evidence_policy"], "matched_fact_only_no_verdict")

    def test_thirty_external_cases_are_independently_frozen(self) -> None:
        fixture = _fixture()
        raw_projection = _raw_external()
        cases = fixture["external_reference_cases"]
        canonical = json.dumps(
            cases,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        self.assertEqual(len(cases), 30)
        self.assertEqual(hashlib.sha256(canonical).hexdigest(), EXTERNAL_CASES_SHA256)
        raw_cases = raw_projection["raw_cases"]
        self.assertEqual(len(raw_cases), 72)
        self.assertEqual(
            hashlib.sha256(
                json.dumps(
                    raw_cases,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest(),
            RAW_CASES_SHA256,
        )
        raw_by_year = {
            int(row["input"]["lunar_year"]): _raw_to_canonical(row["raw"])
            for row in raw_cases
        }
        for case in cases:
            with self.subTest(case=case["id"]):
                self.assertEqual(
                    _one_based_mod(case["lunar_year"] + 1_936_557, 72),
                    case["bureau"],
                )
                self.assertEqual(
                    raw_by_year[case["lunar_year"]],
                    {
                        key: case["expected"][key]
                        for key in raw_by_year[case["lunar_year"]]
                    },
                )

    def test_known_external_differences_are_never_promoted_over_primary(self) -> None:
        fixture = _fixture()
        included = {row["bureau"] for row in fixture["external_reference_cases"]}
        differences = fixture["known_comparator_difference_cases"]
        self.assertEqual({row["bureau"] for row in differences}, {30, 44, 66})
        self.assertTrue(included.isdisjoint({30, 44, 66}))
        raw_by_bureau = {
            int(row["raw"]["bureau"]): _raw_to_canonical(row["raw"])
            for row in _raw_external()["raw_cases"]
        }
        rows = {
            row["bureau"]: row
            for row in _table()["annual_yang_72_source_rows"]
        }
        for difference in differences:
            self.assertEqual(
                rows[difference["bureau"]][difference["field"]],
                difference["primary_expected"],
            )
            self.assertNotEqual(
                difference["primary_expected"],
                difference["comparator_value"],
            )
            self.assertEqual(
                raw_by_bureau[difference["bureau"]][difference["field"]],
                difference["comparator_value"],
            )

    def test_calendar_boundaries_use_lunar_year_and_preserve_other_boundaries(self) -> None:
        for case in _fixture()["calendar_boundary_cases"]:
            with self.subTest(case=case["id"]):
                calendar = calendar_core.normalize_calendar(
                    case["datetime"],
                    timezone_name=case["timezone"],
                    location=case["location"],
                )
                lunar = calendar["lunar_date"]
                self.assertEqual(lunar["year"], case["expected_lunar_year"])
                self.assertEqual(
                    _one_based_mod(lunar["year"] + 1_936_557, 72),
                    case["expected_bureau"],
                )
                if "expected_lunar_month" in case:
                    self.assertEqual(lunar["month"], case["expected_lunar_month"])
                    self.assertEqual(
                        lunar["is_leap_month"], case["expected_leap"]
                    )

    def test_four_deity_180_year_cycle_is_complete(self) -> None:
        cycle = _table()["long_cycle_deities"]["four_deity_cycle"]
        order = list(cycle["place_order"])
        for deity, starts in cycle["upper_middle_lower_starts"].items():
            observed = []
            for accumulated_year in range(1, 181):
                yuan = (accumulated_year - 1) // 60
                within_yuan = (accumulated_year - 1) % 60
                start = order.index(starts[yuan])
                observed.append(order[(start + within_yuan // 3) % len(order)])
            with self.subTest(deity=deity):
                self.assertEqual(set(observed), set(order))
                self.assertEqual(len(observed), 180)


if __name__ == "__main__":
    unittest.main()

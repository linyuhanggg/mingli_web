"""Task 7I regressions for the deterministic Qimen Dunjia provider."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock

import yaml

import adapter_validate
import audit_qimen_provider
import reading_evidence_bundle
import reading_source_plan
from reading_engine import calendar_core, qimen
from reading_engine.contracts import CalculationResult, ReadingRequest
from reading_engine.evidence_rules import match_rule, production_evidence_rules
from reading_engine.factory import build_production_engine
from reading_engine.fact_index import build_fact_index
from reading_engine.providers import QimenProvider, STRUCTURED_SYSTEMS
from reading_engine.providers import PROVIDER_CAPABILITIES, missing_required_inputs


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "references" / "fixtures" / "qimen-v51.yaml"


def _mutated_contract_value(value: object) -> object:
    """Return a type-compatible value that cannot equal the frozen contract."""

    if isinstance(value, str):
        return f"{value}-mutated"
    if isinstance(value, int):
        return value + 10
    if isinstance(value, list):
        return [*copy.deepcopy(value), "__mutated__"]
    if isinstance(value, dict):
        mutated = copy.deepcopy(value)
        first_key = next(iter(mutated))
        mutated[first_key] = _mutated_contract_value(mutated[first_key])
        return mutated
    raise TypeError(f"unsupported Qimen contract value: {value!r}")


def _fixture() -> dict:
    return yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))


def _intent() -> dict:
    return {
        "subject_refs": ["event"],
        "calculation_object": "concrete_event",
        "question_dimensions": ["outcome", "state", "timing"],
        "horizon": {"kind": "instant"},
        "requested_method": "qimen",
        "requested_granularity": "instant",
        "continuity": {
            "reading_id": None,
            "same_subject": False,
            "same_event": False,
        },
        "facts_present": ["event_datetime", "timezone", "location"],
        "facts_corrected": [],
        "evidence_questions": ["此局的盘面结构和古籍条件如何"],
    }


def _request(**changes: object) -> ReadingRequest:
    payload = {
        "query": "按时家转盘奇门核对这件事",
        "action": "new",
        "system": "qimen",
        "intent": _intent(),
        "event_datetime": "2024-06-21T04:51:00",
        "timezone": "Asia/Shanghai",
        "location": "上海",
    }
    payload.update(changes)
    return ReadingRequest(**payload)


class QimenFixtureContractTests(unittest.TestCase):
    def test_machine_readable_completeness_audit_passes_before_activation(self) -> None:
        report = audit_qimen_provider.audit_qimen_provider()

        self.assertTrue(report["provider_ready"], report)
        self.assertGreaterEqual(report["counts"]["source_rule_boards"], 30)
        self.assertEqual(report["counts"]["solar_terms"], 24)
        self.assertEqual(report["counts"]["yuan_profiles"], 3)
        self.assertEqual(report["counts"]["dun_profiles"], 2)
        self.assertEqual(report["counts"]["xun_profiles"], 6)
        self.assertGreaterEqual(report["counts"]["calendar_boundaries"], 8)
        self.assertEqual(report["counts"]["palaces"], 9)
        self.assertEqual(report["counts"]["stars"], 9)
        self.assertEqual(report["counts"]["doors"], 8)
        self.assertEqual(report["counts"]["deities"], 8)
        self.assertEqual(report["counts"]["algorithm_dependencies"], 5)
        self.assertEqual(report["counts"]["named_pattern_predicates"], 40)
        self.assertEqual(report["counts"]["independent_pattern_contracts"], 40)
        self.assertEqual(report["counts"]["source_bound_evidence_rules"], 40)
        self.assertEqual(report["counts"]["named_pattern_coverage"], 40)
        self.assertGreaterEqual(report["counts"]["pattern_activation_boards"], 3)
        self.assertEqual(report["counts"]["calendar_pattern_witnesses"], 2)
        self.assertEqual(report["counts"]["independent_reference_boards"], 37)
        self.assertEqual(report["counts"]["independent_oracle_mismatches"], 0)
        self.assertEqual(report["counts"]["external_reference_boards"], 30)
        self.assertEqual(report["counts"]["external_reference_mismatches"], 0)
        self.assertEqual(report["findings"], [])

    def test_fixtures_cover_all_terms_yuan_dun_and_xun(self) -> None:
        cases = _fixture()["source_rule_boards"]

        self.assertGreaterEqual(len(cases), 30)
        self.assertEqual(len(cases), len({case["id"] for case in cases}))
        self.assertEqual(len({case["input"]["active_term"] for case in cases}), 24)
        self.assertEqual({case["expected"]["yuan"] for case in cases}, {"upper", "middle", "lower"})
        self.assertEqual({case["expected"]["dun"] for case in cases}, {"yang", "yin"})
        self.assertEqual(
            {case["expected"]["xun"] for case in cases},
            {"甲子", "甲戌", "甲申", "甲午", "甲辰", "甲寅"},
        )

    def test_all_source_rule_boards_reproduce_complete_plate_signatures(self) -> None:
        for case in _fixture()["source_rule_boards"]:
            with self.subTest(case=case["id"]):
                board = qimen.build_board(**case["input"])
                expected = case["expected"]
                actual = {
                    "dun": board["dun"],
                    "yuan": board["yuan"],
                    "symbol_head": board["symbol_head"],
                    "ju": board["ju"]["number"],
                    "xun": board["xunkong"]["xun"],
                    "hidden_instrument": board["chief"]["hidden_instrument"],
                    "chief": board["chief"]["star"],
                    "chief_palace": board["chief"]["destination_palace"],
                    "director": board["director"]["door"],
                    "director_palace": board["director"]["destination_palace"],
                    "void_branches": board["xunkong"]["branches"],
                    "void_palaces": board["xunkong"]["palaces"],
                    "horse_branch": board["horse"]["branch"],
                    "horse_palace": board["horse"]["palace"],
                    "signature": qimen.board_signature(board),
                }
                self.assertEqual(actual, expected)

    def test_audit_rejects_mutated_expected_plate(self) -> None:
        fixture = copy.deepcopy(_fixture())
        fixture["source_rule_boards"][0]["expected"]["chief_palace"] = 9
        with tempfile.TemporaryDirectory() as temporary:
            mutated = Path(temporary) / "qimen-mutated.yaml"
            mutated.write_text(
                yaml.safe_dump(fixture, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            report = audit_qimen_provider.audit_qimen_provider(
                fixture_path=mutated
            )

        self.assertFalse(report["provider_ready"])
        self.assertIn(
            "fixture board mismatch: qimen-source-01",
            report["findings"],
        )

    def test_audit_rejects_deletion_of_each_required_source_dependency(self) -> None:
        source_matrix = yaml.safe_load(
            audit_qimen_provider.MATRIX.read_text(encoding="utf-8")
        )
        dependency_rows = source_matrix["providers"]["qimen"]["dependencies"]
        self.assertEqual(
            [row["id"] for row in dependency_rows],
            list(qimen.SOURCE_DEPENDENCIES),
        )
        for deleted_id in qimen.SOURCE_DEPENDENCIES:
            with self.subTest(deleted_id=deleted_id), tempfile.TemporaryDirectory() as temporary:
                mutated = copy.deepcopy(source_matrix)
                mutated["providers"]["qimen"]["dependencies"] = [
                    row for row in dependency_rows if row["id"] != deleted_id
                ]
                matrix_path = Path(temporary) / "algorithm-source-dependencies.yaml"
                matrix_path.write_text(
                    yaml.safe_dump(mutated, allow_unicode=True, sort_keys=False),
                    encoding="utf-8",
                )

                report = audit_qimen_provider.audit_qimen_provider(
                    matrix_path=matrix_path
                )

                self.assertFalse(report["provider_ready"])
                self.assertIn(
                    "Qimen dependency IDs do not match the provider contract",
                    report["findings"],
                )

    def test_audit_reads_term_ju_rules_from_normalized_source(self) -> None:
        report = audit_qimen_provider.audit_qimen_provider()

        self.assertTrue(report["source_checks"]["term_ju_table_parsed"])
        self.assertTrue(report["source_checks"]["plate_orders_parsed"])
        self.assertTrue(report["source_checks"]["chief_director_rules_present"])
        self.assertTrue(report["source_checks"]["center_hosting_rule_present"])
        self.assertTrue(report["source_checks"]["named_pattern_anchors_verified"])
        self.assertTrue(report["source_checks"]["declared_tongzong_identity_verified"])
        self.assertTrue(report["source_checks"]["structured_pattern_contract_verified"])
        self.assertTrue(report["source_checks"]["pattern_source_identity_contract_verified"])
        self.assertTrue(report["source_checks"]["evidence_source_identity_bridge_verified"])
        self.assertTrue(report["source_checks"]["evidence_quote_source_text_verified"])
        self.assertTrue(report["source_checks"]["pattern_conflicts_versioned"])
        self.assertEqual(report["source_checks"]["source_sha256"], _fixture()["source"]["sha256"])

    def test_audit_rejects_every_structured_field_of_all_forty_pattern_formulas(self) -> None:
        source_table = yaml.safe_load(
            audit_qimen_provider.SOURCE_TABLE.read_text(encoding="utf-8")
        )
        profiles = source_table["named_pattern_predicates"]
        self.assertEqual(len(profiles), 40)
        with tempfile.TemporaryDirectory() as temporary:
            mutated_path = Path(temporary) / "qimen-source-tables-v1.yaml"
            for profile_index, profile in enumerate(profiles):
                contract_fields = [
                    key
                    for key in audit_qimen_provider.PATTERN_CONTRACT_FIELDS
                    if key in profile
                ]
                self.assertGreaterEqual(len(contract_fields), 2, profile["id"])
                for field in contract_fields:
                    with self.subTest(pattern=profile["id"], field=field):
                        mutated = copy.deepcopy(source_table)
                        old_value = mutated["named_pattern_predicates"][profile_index][field]
                        mutated["named_pattern_predicates"][profile_index][field] = (
                            _mutated_contract_value(old_value)
                        )
                        mutated_path.write_text(
                            yaml.safe_dump(mutated, allow_unicode=True, sort_keys=False),
                            encoding="utf-8",
                        )
                        report = audit_qimen_provider.audit_qimen_provider(
                            source_table_path=mutated_path
                        )

                        self.assertFalse(report["provider_ready"])
                        self.assertIn(
                            "Qimen structured pattern contract mismatch",
                            report["findings"],
                        )

    def test_audit_rejects_pattern_source_identity_and_declared_source_hash_drift(self) -> None:
        source_table = yaml.safe_load(
            audit_qimen_provider.SOURCE_TABLE.read_text(encoding="utf-8")
        )
        mutations = {}
        wrong_identity = copy.deepcopy(source_table)
        pattern = next(
            row
            for row in wrong_identity["named_pattern_predicates"]
            if row["id"] == "QM-P26"
        )
        pattern["source_profile"] = "qimen_tongzong"
        mutations["pattern_source_identity"] = (
            wrong_identity,
            "Qimen pattern source identity contract mismatch",
        )
        wrong_hash = copy.deepcopy(source_table)
        wrong_hash["source_profiles"]["qimen_faqiao"]["sha256"] = "0" * 64
        mutations["declared_source_hash"] = (
            wrong_hash,
            "Qimen declared source hash mismatch: qimen_faqiao",
        )

        with tempfile.TemporaryDirectory() as temporary:
            mutated_path = Path(temporary) / "qimen-source-tables-v1.yaml"
            for name, (mutated, expected_finding) in mutations.items():
                with self.subTest(mutation=name):
                    mutated_path.write_text(
                        yaml.safe_dump(mutated, allow_unicode=True, sort_keys=False),
                        encoding="utf-8",
                    )
                    report = audit_qimen_provider.audit_qimen_provider(
                        source_table_path=mutated_path
                    )

                    self.assertFalse(report["provider_ready"])
                    self.assertIn(expected_finding, report["findings"])

    def test_audit_rejects_a_mutated_external_raw_palace_projection(self) -> None:
        external = yaml.safe_load(
            audit_qimen_provider.EXTERNAL_FIXTURE.read_text(encoding="utf-8")
        )
        external["cases"][0]["raw_projection"][0]["earth"] = "甲"
        with tempfile.TemporaryDirectory() as temporary:
            mutated_path = Path(temporary) / "qimen-go-v51.yaml"
            mutated_path.write_text(
                yaml.safe_dump(external, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            report = audit_qimen_provider.audit_qimen_provider(
                external_fixture_path=mutated_path
            )

        self.assertFalse(report["provider_ready"])
        self.assertIn(
            "external reference raw signature mismatch: qimen-go-01",
            report["findings"],
        )

    def test_audit_rejects_evidence_quote_or_anchor_detached_from_source_identity(self) -> None:
        records = [
            json.loads(line)
            for line in audit_qimen_provider.EVIDENCE_INDEX.read_text(
                encoding="utf-8"
            ).splitlines()
            if line.strip()
        ]
        target = next(
            row
            for row in records
            if row.get("system") == "qimen" and row.get("local_rule_id") == "QM-P26"
        )
        target["quote"] = "detached evidence quote"
        target["source_anchor"] = "detached anchor"
        with tempfile.TemporaryDirectory() as temporary:
            mutated_path = Path(temporary) / "evidence-rules.jsonl"
            mutated_path.write_text(
                "\n".join(
                    json.dumps(row, ensure_ascii=False, sort_keys=True)
                    for row in records
                )
                + "\n",
                encoding="utf-8",
            )
            report = audit_qimen_provider.audit_qimen_provider(
                evidence_index_path=mutated_path
            )

        self.assertFalse(report["provider_ready"])
        self.assertIn(
            "Qimen evidence/source identity bridge mismatch",
            report["findings"],
        )

    def test_reference_oracle_does_not_reuse_production_signature_logic(self) -> None:
        with mock.patch.object(
            qimen,
            "board_signature",
            side_effect=AssertionError("production signature leaked into oracle"),
        ):
            report = audit_qimen_provider.audit_qimen_provider()

        self.assertTrue(report["provider_ready"], report)
        self.assertEqual(report["counts"]["independent_oracle_mismatches"], 0)

    def test_classical_worked_board_is_reproduced_from_its_exact_source_row(self) -> None:
        case = _fixture()["classical_cases"][0]
        board = qimen.build_board(**case["input"])
        expected = case["expected"]
        director_row = next(
            row
            for row in board["palaces"]
            if row["palace"] == board["director"]["destination_palace"]
        )

        self.assertEqual(board["dun"], expected["dun"])
        self.assertEqual(board["yuan"], expected["yuan"])
        self.assertEqual(board["ju"]["number"], expected["ju"])
        self.assertEqual(board["xunkong"]["xun"], expected["xun"])
        self.assertEqual(board["chief"]["star"], expected["chief"])
        self.assertEqual(board["chief"]["destination_palace"], expected["chief_palace"])
        self.assertEqual(board["director"]["door"], expected["director"])
        self.assertEqual(board["director"]["destination_palace"], expected["director_palace"])
        self.assertEqual(director_row["deity"], expected["director_deity"])
        self.assertEqual(qimen.board_signature(board), expected["signature"])

    def test_tongzong_exact_dingmao_row_is_frozen_as_an_incompatible_plate(self) -> None:
        case = _fixture()["classical_door_map_cases"][0]
        board = qimen.build_board(**case["input"])
        observed = {
            row["door"]: row["palace"]
            for row in board["palaces"]
            if row["door"]
        }

        self.assertNotEqual(observed, case["expected"])
        alternatives = qimen.source_table()["selected_convention"]["incompatible_alternatives"]
        self.assertIn(
            "tongzong-numeric-outer-door-rotation",
            {row["id"] for row in alternatives},
        )
        report = audit_qimen_provider.audit_qimen_provider()
        self.assertTrue(
            report["source_checks"]["tongzong_numeric_door_conflict_verified"],
            report,
        )


class QimenCalendarAndBoardTests(unittest.TestCase):
    def test_exact_solar_term_and_day_boundaries_are_honoured(self) -> None:
        categories = Counter(
            case["category"] for case in _fixture()["calendar_boundaries"]
        )
        self.assertGreaterEqual(categories["solar_term_boundary"], 6)
        self.assertGreaterEqual(categories["day_rollover"], 2)
        for case in _fixture()["calendar_boundaries"]:
            with self.subTest(case=case["id"]):
                calendar = calendar_core.normalize_calendar(
                    case["datetime"],
                    timezone_name=case["timezone"],
                    location=case["location"],
                )
                facts = qimen.build_fact_layer(calendar)
                self.assertEqual(
                    facts["output"]["active_solar_term"],
                    case["expected_active_term"],
                )
                if "expected_day" in case:
                    self.assertEqual(
                        facts["output"]["day_hour"]["day_ganzhi"],
                        case["expected_day"],
                    )

    def test_leap_month_calendar_fixture_preserves_a_deterministic_board(self) -> None:
        cases = [
            case
            for case in _fixture()["calendar_boundaries"]
            if case["category"] == "lunar_leap_month"
        ]
        self.assertGreaterEqual(len(cases), 1)
        for case in cases:
            with self.subTest(case=case["id"]):
                calendar = calendar_core.normalize_calendar(
                    case["datetime"],
                    timezone_name=case["timezone"],
                    location=case["location"],
                )
                first = qimen.build_fact_layer(calendar)
                second = qimen.build_fact_layer(copy.deepcopy(calendar))
                self.assertTrue(calendar["lunar_date"]["is_leap_month"])
                self.assertEqual(calendar["lunar_date"]["month"], case["expected_lunar_month"])
                self.assertEqual(first["output"]["active_solar_term"], case["expected_active_term"])
                self.assertEqual(first["output"], second["output"])
                self.assertEqual(first["fact_digest"], second["fact_digest"])

    def test_yang_and_yin_earth_plate_directions_are_opposite(self) -> None:
        yang = qimen.build_board("冬至", "甲子", "甲子")
        yin = qimen.build_board("夏至", "甲子", "甲子")
        yang_stems = {row["palace"]: row["earth_stem"] for row in yang["palaces"]}
        yin_stems = {row["palace"]: row["earth_stem"] for row in yin["palaces"]}

        self.assertEqual(
            [yang_stems[1], yang_stems[2], yang_stems[3]],
            ["戊", "己", "庚"],
        )
        self.assertEqual([yin_stems[9], yin_stems[8], yin_stems[7]], ["戊", "己", "庚"])

    def test_each_board_has_nine_unique_complete_palaces(self) -> None:
        for case in _fixture()["source_rule_boards"]:
            board = qimen.build_board(**case["input"])
            palaces = board["palaces"]
            self.assertEqual(len(palaces), 9)
            self.assertEqual({row["palace"] for row in palaces}, set(range(1, 10)))
            self.assertEqual(len([row for row in palaces if row["door"]]), 8)
            self.assertEqual(len([row for row in palaces if row["deity"]]), 8)
            self.assertEqual(
                sum(len(row["stars"]) for row in palaces),
                9,
            )

    def test_tianqin_and_center_instrument_always_travel_with_tianrui(self) -> None:
        for case in _fixture()["source_rule_boards"]:
            with self.subTest(case=case["id"]):
                board = qimen.build_board(**case["input"])
                tianqin = next(
                    row for row in board["palaces"] if "天禽" in row["stars"]
                )
                tianrui = next(
                    row for row in board["palaces"] if "天芮" in row["stars"]
                )
                center_stem = next(
                    row["earth_stem"]
                    for row in board["palaces"]
                    if row["palace"] == 5
                )

                self.assertEqual(tianqin["palace"], tianrui["palace"])
                self.assertIn(center_stem, tianrui["heaven_stems"])

    def test_xunkong_and_horse_are_mechanical_hour_facts(self) -> None:
        board = qimen.build_board("冬至", "甲子", "甲子")
        self.assertEqual(board["xunkong"]["branches"], ["戌", "亥"])
        self.assertEqual(board["xunkong"]["palaces"], [6])
        self.assertEqual(board["horse"], {
            "hour_branch": "子", "branch": "寅", "palace": 8,
            "source_dependency_id": "qimen.markers.xunkong-horse",
        })

    def test_three_wonders_and_six_instruments_are_explicitly_typed(self) -> None:
        board = qimen.build_board("冬至", "丁卯", "甲辰")
        tokens = board["instruments_wonders"]

        self.assertEqual(tokens["three_wonders"], ["乙", "丙", "丁"])
        self.assertEqual(tokens["six_instruments"], ["戊", "己", "庚", "辛", "壬", "癸"])
        self.assertEqual(len(tokens["earth_plate"]), 9)
        self.assertEqual(len(tokens["heaven_plate"]), 9)
        self.assertEqual(
            {row["kind"] for row in tokens["earth_plate"]},
            {"three_wonder", "six_instrument"},
        )
        self.assertEqual(
            tokens["hidden_jia"],
            {"xun": "甲辰", "instrument": "壬"},
        )

    def test_named_patterns_are_exact_predicate_matches_without_verdicts(self) -> None:
        board = qimen.build_board("冬至", "甲子", "甲子")
        matches = qimen.detect_named_patterns(board)

        self.assertEqual(matches, board["named_patterns"])
        self.assertTrue(all(item["status"] == "predicate_matched_not_verdict" for item in matches))
        self.assertTrue(all("source_anchor" in item for item in matches))
        self.assertTrue(all("verdict" not in item for item in matches))
        with self.assertRaises(TypeError):
            qimen.detect_named_patterns(board, query="请找吉格")

    def test_named_pattern_registry_covers_the_complete_declared_forty_patterns(self) -> None:
        expected_names = {
            "青龙回首", "飞鸟跌穴", "青龙逃走", "白虎猖狂", "腾蛇妖矫",
            "朱雀投江", "大格", "刑格", "小格", "天遁", "地遁", "人遁",
            "五不遇时", "伏吟", "反吟", "三奇入墓", "六仪击刑", "门迫",
            "云遁", "风遁", "龙遁", "虎遁", "神遁", "鬼遁", "三奇得使",
            "玉女守门", "岁格", "月格", "日格", "时格", "伏宫", "伏干",
            "飞干格", "太白入荧", "火入金乡", "时墓", "六仪受制",
            "地罗遮蔽", "天网四张", "尺寸高低",
        }
        profiles = qimen.source_table()["named_pattern_predicates"]

        self.assertEqual([row["id"] for row in profiles], [f"QM-P{i:02d}" for i in range(1, 41)])
        self.assertEqual({row["name"] for row in profiles}, expected_names)
        self.assertTrue(all(row.get("source_anchor") for row in profiles))
        self.assertTrue(all(row.get("source_phrase") for row in profiles))
        self.assertTrue(all(row.get("definition_version") for row in profiles))
        self.assertEqual(
            qimen.source_table()["named_pattern_calendar_jia_policy"],
            "no_match_without_source_declared_hidden-instrument_mapping",
        )

        board = qimen.build_board("冬至", "甲子", "甲子")
        self.assertEqual(
            board["profile"]["board_type"],
            qimen.source_table()["selected_convention"]["board_type"],
        )

    def test_time_grid_requires_a_three_wonder_hour_stem(self) -> None:
        profile = next(
            row
            for row in qimen.source_table()["named_pattern_predicates"]
            if row["id"] == "QM-P30"
        )
        self.assertEqual(profile["lower_stems"], ["乙", "丙", "丁"])

        non_wonder_hour = qimen.build_board("冬至", "丙寅", "戊子")
        self.assertNotIn(
            "QM-P30",
            {row["id"] for row in non_wonder_hour["named_patterns"]},
        )

    def test_calendar_jia_grid_patterns_fail_closed_without_a_declared_mapping(self) -> None:
        board = qimen.build_board(
            "冬至",
            "戊辰",
            "乙卯",
            year_ganzhi="甲子",
            month_ganzhi="甲子",
        )
        pattern_ids = {row["id"] for row in board["named_patterns"]}

        self.assertIn("QM-P31", pattern_ids)
        self.assertNotIn("QM-P27", pattern_ids)
        self.assertNotIn("QM-P28", pattern_ids)

    def test_time_net_and_height_are_the_same_palace_with_explicit_low_high_class(self) -> None:
        cases = (
            (("冬至", "戊辰", "乙卯"), 9, "high"),
            (("冬至", "戊辰", "戊午"), 1, "low"),
        )
        for args, expected_palace, expected_height in cases:
            with self.subTest(args=args):
                board = qimen.build_board(*args)
                matches = {
                    row["id"]: row
                    for row in board["named_patterns"]
                    if row["id"] in {"QM-P39", "QM-P40"}
                }
                self.assertEqual(set(matches), {"QM-P39", "QM-P40"})
                self.assertEqual(matches["QM-P39"]["palace"], expected_palace)
                self.assertEqual(matches["QM-P40"]["palace"], expected_palace)
                self.assertEqual(
                    matches["QM-P40"]["details"]["height_class"],
                    expected_height,
                )

        for case in _fixture()["pattern_coverage_cases"]:
            board = qimen.build_board(**case["input"])
            pattern_ids = {row["id"] for row in board["named_patterns"]}
            self.assertEqual("QM-P39" in pattern_ids, "QM-P40" in pattern_ids)

    def test_frozen_boards_activate_every_source_bound_pattern_predicate(self) -> None:
        fixture = _fixture()
        cases = [
            *fixture["source_rule_boards"],
            *fixture["pattern_coverage_cases"],
            *fixture["named_pattern_cases"],
        ]
        activated: set[str] = set()
        for case in cases:
            board = qimen.build_board(**case["input"])
            pattern_ids = {item["id"] for item in board["named_patterns"]}
            activated.update(pattern_ids)
            if "expected_pattern_ids" in case:
                self.assertEqual(
                    pattern_ids,
                    set(case["expected_pattern_ids"]),
                    case["id"],
                )

        self.assertEqual(activated, {f"QM-P{index:02d}" for index in range(1, 41)})

    def test_all_forty_pattern_predicates_have_frozen_fixture_coverage(self) -> None:
        observed: set[str] = set()
        for case in _fixture()["pattern_coverage_cases"]:
            board = qimen.build_board(**case["input"])
            identifiers = {row["id"] for row in board["named_patterns"]}
            self.assertIn(case["expected_rule_id"], identifiers)
            observed.add(case["expected_rule_id"])

        self.assertEqual(
            observed,
            {f"QM-P{number:02d}" for number in range(1, 41)},
        )

    def test_year_and_month_grid_witnesses_reproduce_from_real_calendar_instants(self) -> None:
        witnesses = _fixture()["calendar_pattern_witnesses"]
        self.assertEqual({row["expected_rule_id"] for row in witnesses}, {"QM-P27", "QM-P28"})
        for witness in witnesses:
            with self.subTest(witness=witness["id"]):
                calendar = calendar_core.normalize_calendar(
                    witness["datetime"],
                    timezone_name=witness["timezone"],
                    location=witness["location"],
                )
                board = qimen.build_fact_layer(calendar)["output"]
                self.assertEqual(calendar["ganzhi"], witness["expected_pillars"])
                self.assertEqual(
                    calendar["solar_terms"]["previous"]["name"],
                    witness["expected_active_term"],
                )
                self.assertIn(
                    witness["expected_rule_id"],
                    {row["id"] for row in board["named_patterns"]},
                )

    def test_calendar_fact_layer_exposes_all_four_pillars_needed_by_pattern_rules(self) -> None:
        calendar = calendar_core.normalize_calendar(
            "2024-06-21T04:51:00",
            timezone_name="Asia/Shanghai",
            location="上海",
        )
        facts = qimen.build_fact_layer(calendar)

        self.assertEqual(
            facts["output"]["calendar_pillars"],
            {
                key: calendar["ganzhi"][key]
                for key in ("year", "month", "day", "hour")
            },
        )

    def test_every_pattern_fixture_uses_a_calendar_possible_hour_pillar(self) -> None:
        starting_hour_stem = {
            "甲": 0, "己": 0,
            "乙": 2, "庚": 2,
            "丙": 4, "辛": 4,
            "丁": 6, "壬": 6,
            "戊": 8, "癸": 8,
        }
        stems = "甲乙丙丁戊己庚辛壬癸"
        branches = "子丑寅卯辰巳午未申酉戌亥"
        fixture = _fixture()
        for case in [
            *fixture["source_rule_boards"],
            *fixture["pattern_coverage_cases"],
            *fixture["named_pattern_cases"],
            *fixture["classical_cases"],
        ]:
            with self.subTest(case=case["id"]):
                day = case["input"]["day_ganzhi"]
                hour = case["input"]["hour_ganzhi"]
                expected_stem = stems[
                    (starting_hour_stem[day[0]] + branches.index(hour[1])) % 10
                ]
                self.assertEqual(hour[0], expected_stem)

    def test_same_input_has_identical_fact_digest(self) -> None:
        calendar = calendar_core.normalize_calendar(
            "2024-06-21T04:51:00",
            timezone_name="Asia/Shanghai",
            location="上海",
        )
        first = qimen.build_fact_layer(calendar)
        second = qimen.build_fact_layer(copy.deepcopy(calendar))

        self.assertEqual(first["fact_digest"], second["fact_digest"])
        self.assertEqual(first["output"], second["output"])
        self.assertTrue(qimen.validate_fact_layer(first)["ok"])

    def test_board_digest_rejects_substitution_and_deletion(self) -> None:
        calendar = calendar_core.normalize_calendar(
            "2024-06-21T04:51:00",
            timezone_name="Asia/Shanghai",
            location="上海",
        )
        facts = qimen.build_fact_layer(calendar)
        for mutation in ("replace", "delete"):
            with self.subTest(mutation=mutation):
                tampered = copy.deepcopy(facts)
                if mutation == "replace":
                    tampered["output"]["board_digest"] = "0" * 64
                else:
                    del tampered["output"]["board_digest"]
                tampered["fact_digest"] = qimen._digest(
                    qimen._fact_identity(tampered)
                )

                report = qimen.validate_fact_layer(tampered)

                self.assertFalse(report["ok"])
                self.assertIn("qimen_board_digest_mismatch", report["codes"])

    def test_validation_rebuilds_board_and_rejects_evidence_or_calendar_drift(self) -> None:
        calendar = calendar_core.normalize_calendar(
            "2024-12-21T17:20:19.592285",
            timezone_name="Asia/Shanghai",
            location="上海",
        )
        facts = qimen.build_fact_layer(calendar)

        mutations = {}
        removed = copy.deepcopy(facts)
        removed["output"]["named_patterns"] = []
        mutations["pattern_deleted"] = removed

        injected = copy.deepcopy(facts)
        injected["output"]["named_patterns"].append({
            "id": "QM-P15",
            "name": "反吟",
            "predicate": "all_rotating_stars_on_opposite_palaces",
            "status": "predicate_matched_not_verdict",
            "source_anchor": "qimen-tongzong L155",
            "source_dependency_id": "qimen.patterns.board-predicates",
        })
        mutations["pattern_injected"] = injected

        duplicate_drift = copy.deepcopy(facts)
        duplicate_drift["output"]["stars_doors_deities"][0]["stars"] = ["天英"]
        mutations["derived_duplicate_drift"] = duplicate_drift

        calendar_drift = copy.deepcopy(facts)
        replacement_calendar = calendar_core.normalize_calendar(
            "2024-06-21T04:50:45.887375",
            timezone_name="Asia/Shanghai",
            location="上海",
        )
        calendar_drift["calendar_normalization"] = replacement_calendar
        calendar_drift["calendar_digest"] = calendar_core.validate_calendar_digest(
            replacement_calendar
        )
        mutations["calendar_board_drift"] = calendar_drift

        for name, tampered in mutations.items():
            with self.subTest(mutation=name):
                board_identity = copy.deepcopy(tampered["output"])
                board_identity.pop("board_digest", None)
                tampered["output"]["board_digest"] = qimen._digest(board_identity)
                tampered["fact_digest"] = qimen._digest(
                    qimen._fact_identity(tampered)
                )

                report = qimen.validate_fact_layer(tampered)

                self.assertFalse(report["ok"])
                self.assertIn("qimen_board_facts_mismatch", report["codes"])

    def test_validation_rejects_provenance_envelope_substitution(self) -> None:
        calendar = calendar_core.normalize_calendar(
            "2024-06-21T04:51:00",
            timezone_name="Asia/Shanghai",
            location="上海",
        )
        facts = qimen.build_fact_layer(calendar)
        mutations = {
            "system": ("system", "liuren"),
            "schema": ("schema_version", "mingli-qimen-facts-v0"),
            "scope": ("fact_layer_scope", "generic_chart"),
            "adapter_name": ("adapter.name", "replacement.qimen"),
            "adapter_version": ("adapter.version", "999"),
            "adapter_profile": ("adapter.rule_profile", "other-profile"),
            "source_path": ("source_table.path", "other.yaml"),
            "source_hash": ("source_table.sha256", "0" * 64),
            "source_schema": ("source_table.schema_version", "other-schema"),
        }
        for name, (path, value) in mutations.items():
            with self.subTest(mutation=name):
                tampered = copy.deepcopy(facts)
                cursor = tampered
                parts = path.split(".")
                for part in parts[:-1]:
                    cursor = cursor[part]
                cursor[parts[-1]] = value
                tampered["fact_digest"] = qimen._digest(
                    qimen._fact_identity(tampered)
                )

                report = qimen.validate_fact_layer(tampered)

                self.assertFalse(report["ok"])
                self.assertIn("qimen_provenance_mismatch", report["codes"])


class QimenProviderActivationTests(unittest.TestCase):
    def test_qimen_is_calculation_capability_not_validated_chart(self) -> None:
        capability = PROVIDER_CAPABILITIES["qimen"]

        self.assertEqual(capability.mode, "calculation")
        self.assertEqual(
            capability.required_inputs,
            ("event_datetime", "timezone", "location"),
        )
        self.assertNotIn("qimen", STRUCTURED_SYSTEMS)

    def test_required_inputs_do_not_accept_supplied_chart_as_substitute(self) -> None:
        empty = _request(event_datetime=None, timezone=None, location=None)
        supplied = _request(
            event_datetime=None,
            timezone=None,
            location=None,
            chart_data={"ju": "阳遁一局", "palaces": [{"palace": 1}]},
        )

        self.assertEqual(
            missing_required_inputs("qimen", empty),
            ("event_datetime", "timezone", "location"),
        )
        self.assertEqual(missing_required_inputs("qimen", supplied), missing_required_inputs("qimen", empty))

    def test_literal_now_is_not_accepted_as_a_persisted_event_instant(self) -> None:
        request = _request(event_datetime=None, reference_datetime="now")

        self.assertEqual(
            missing_required_inputs("qimen", request),
            ("event_datetime",),
        )
        with self.assertRaisesRegex(ValueError, "exact event datetime"):
            QimenProvider(ROOT).calculate(request)

    def test_provider_calculates_without_chart_data_and_ignores_fake_chart(self) -> None:
        provider = QimenProvider(ROOT)
        calculated = provider.calculate(_request())
        fake = provider.calculate(_request(chart_data={"ju": "阴遁九局"}))

        self.assertEqual(calculated.provider_id, "mingli-master.qimen.v1")
        self.assertEqual(calculated.facts["chart_digest"], fake.facts["chart_digest"])
        self.assertNotIn("validated_user_provided_chart", calculated.diagnostics)
        self.assertEqual(
            calculated.facts["chart_facts"]["fact_layer_status"],
            "deterministic_qimen_chart",
        )

    def test_factory_registers_the_deterministic_provider(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            engine = build_production_engine(
                skill_dir=ROOT,
                store_root=temporary,
            )

        self.assertIsInstance(engine.providers["qimen"], QimenProvider)

    def test_refine_reuses_board_but_rebinds_the_new_question(self) -> None:
        provider = QimenProvider(ROOT)
        first = provider.calculate(_request())
        refined = provider.refine(
            _request(query="只追问盘中空间事实", action="continue"),
            first,
        )

        self.assertEqual(refined.facts["chart_digest"], first.facts["chart_digest"])
        self.assertEqual(refined.facts["calendar_digest"], first.facts["calendar_digest"])
        self.assertNotEqual(refined.result_hash, first.result_hash)
        self.assertIn("qimen_plate_reused_without_recast", refined.diagnostics)

    def test_instant_extensions_expose_board_facts_without_predictions(self) -> None:
        provider = QimenProvider(ROOT)
        base = provider.calculate(_request())
        result = provider.extend(
            base,
            ("outcome", "state", "timing", "location"),
            {"kind": "instant"},
        )

        self.assertEqual(result.fact_extension.status, "complete")
        facts = result.fact_extension.facts
        self.assertEqual(facts["status"], "calculated_board_scope_not_verdict")
        self.assertIn("palaces", facts)
        self.assertIn("named_patterns", facts)
        self.assertNotIn("prediction", facts)
        self.assertTrue(all("verdict" not in row for row in facts["named_patterns"]))

    def test_noninstant_exact_timing_is_truthfully_unsupported(self) -> None:
        provider = QimenProvider(ROOT)
        base = provider.calculate(_request())
        result = provider.extend(base, ("timing",), {"kind": "month"})

        self.assertEqual(result.fact_extension.status, "unsupported")
        self.assertEqual(result.fact_extension.unsupported_dimensions, ("timing",))

    def test_adapter_validator_rejects_incomplete_deterministic_plate(self) -> None:
        provider = QimenProvider(ROOT)
        facts = provider.calculate(_request()).facts["chart_facts"]
        self.assertTrue(adapter_validate.validate_payload("qimen", facts)["ok"])
        broken = copy.deepcopy(facts)
        broken["output"]["palaces"].pop()

        report = adapter_validate.validate_payload("qimen", broken)
        self.assertFalse(report["ok"])
        self.assertIn("qimen_invalid_palaces", report["codes"])


class QimenEvidenceActivationTests(unittest.TestCase):
    def test_all_qimen_evidence_rules_require_a_calculated_pattern_id(self) -> None:
        qimen_packs = {
            "san-shi/qimen-dunjia-tongzhi",
            "san-shi/qimen-faqiao",
        }
        rules = [
            rule
            for rule in production_evidence_rules()
            if rule.source_pack in qimen_packs
        ]

        self.assertEqual(len(rules), 40)
        self.assertEqual({rule.local_rule_id for rule in rules}, {
            f"QM-P{index:02d}" for index in range(1, 41)
        })
        counts = Counter(rule.source_pack for rule in rules)
        self.assertEqual(counts["san-shi/qimen-dunjia-tongzhi"], 38)
        self.assertEqual(counts["san-shi/qimen-faqiao"], 2)
        self.assertEqual(
            {
                rule.local_rule_id
                for rule in rules
                if rule.source_pack == "san-shi/qimen-faqiao"
            },
            {"QM-P26", "QM-P36"},
        )
        profiles = {
            row["id"]: row
            for row in qimen.source_table()["named_pattern_predicates"]
        }
        for rule in rules:
            with self.subTest(rule=rule.local_rule_id):
                profile = profiles[rule.local_rule_id]
                expected_pack = (
                    "san-shi/qimen-faqiao"
                    if profile.get("source_profile") == "qimen_faqiao"
                    else "san-shi/qimen-dunjia-tongzhi"
                )
                self.assertEqual(rule.source_pack, expected_pack)
                self.assertEqual(rule.quote, profile["evidence_quote"])
                self.assertEqual(rule.source_anchor, profile["evidence_anchor"])
                self.assertEqual(len(rule.required_fact_predicates), 1)
                predicate = rule.required_fact_predicates[0]
                self.assertEqual(predicate.path_suffix, "/named_patterns")
                self.assertEqual(predicate.operator, "descendant_eq")
                self.assertEqual(predicate.value, rule.local_rule_id)

        default_plan = reading_source_plan.compile_source_plan(
            "qimen",
            {"evidence_questions": ["核对盘面格局条件"]},
            {},
        )
        self.assertEqual(set(default_plan["required_packs"]), qimen_packs)

    def test_evidence_bundle_activates_only_the_pattern_on_the_board(self) -> None:
        board = qimen.build_board("冬至", "甲子", "甲子")
        calculation = CalculationResult.create(
            system="qimen",
            provider_id=QimenProvider.provider_id,
            provider_version=QimenProvider.provider_version,
            input_payload={"fixture": "fuyin"},
            facts={"chart_facts": {"output": board}},
        )
        goal = {
            "source_packs": ["san-shi/qimen-dunjia-tongzhi"],
            "evidence_questions": ["此盘的伏吟或反吟条件是否成立"],
        }
        plan = reading_source_plan.compile_source_plan(
            "qimen", goal, calculation.facts
        )
        fact_index = build_fact_index(
            calculation,
            reading_id="q" * 32,
            version=1,
        )
        bundle = reading_evidence_bundle.compile_evidence_bundle(
            goal,
            calculation.facts,
            plan,
            fact_index=fact_index,
            reading_id="q" * 32,
            version=1,
        )

        self.assertTrue(any("QM-P14" in node.rule_id for node in bundle.evidence))
        self.assertFalse(any("QM-P15" in node.rule_id for node in bundle.evidence))
        self.assertTrue(all(node.fact_refs for node in bundle.evidence))

    def test_faqiao_evidence_activates_only_for_its_two_calculated_patterns(self) -> None:
        cases = (
            (("冬至", "甲子", "庚午"), "QM-P26", "QM-P36"),
            (("冬至", "乙丑", "丁丑"), "QM-P36", "QM-P26"),
        )
        for index, (args, expected, rejected) in enumerate(cases, start=1):
            with self.subTest(expected=expected):
                board = qimen.build_board(*args)
                calculation = CalculationResult.create(
                    system="qimen",
                    provider_id=QimenProvider.provider_id,
                    provider_version=QimenProvider.provider_version,
                    input_payload={"fixture": expected},
                    facts={"chart_facts": {"output": board}},
                )
                goal = {
                    "source_packs": ["san-shi/qimen-faqiao"],
                    "evidence_questions": ["核对法窍盘面条件"],
                }
                plan = reading_source_plan.compile_source_plan(
                    "qimen", goal, calculation.facts
                )
                fact_index = build_fact_index(
                    calculation,
                    reading_id=str(index) * 32,
                    version=1,
                )
                bundle = reading_evidence_bundle.compile_evidence_bundle(
                    goal,
                    calculation.facts,
                    plan,
                    fact_index=fact_index,
                    reading_id=str(index) * 32,
                    version=1,
                )

                self.assertTrue(
                    any(expected in node.rule_id for node in bundle.evidence)
                )
                self.assertFalse(
                    any(rejected in node.rule_id for node in bundle.evidence)
                )
                self.assertTrue(all(node.fact_refs for node in bundle.evidence))

    def test_descendant_pattern_rule_anchors_only_its_matching_pattern(self) -> None:
        board = qimen.build_board("冬至", "辛未", "壬辰")
        calculation = CalculationResult.create(
            system="qimen",
            provider_id=QimenProvider.provider_id,
            provider_version=QimenProvider.provider_version,
            input_payload={"fixture": "multiple-patterns"},
            facts={"chart_facts": {"output": board}},
        )
        facts = build_fact_index(
            calculation,
            reading_id="r" * 32,
            version=1,
        )
        rule = next(
            rule
            for rule in production_evidence_rules()
            if rule.local_rule_id == "QM-P03"
        )

        matched, fact_ids, _ = match_rule(rule, facts)
        refs = [item for item in facts if item.fact_id in fact_ids]

        self.assertTrue(matched)
        self.assertTrue(refs)
        self.assertTrue(all("/named_patterns/0/" in item.path for item in refs))
        self.assertEqual(
            {item.value for item in refs if item.path.endswith("/id")},
            {"QM-P03"},
        )


if __name__ == "__main__":
    unittest.main()

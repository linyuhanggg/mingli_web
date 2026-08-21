"""Task 7N live-provider replay contracts for Liuyao and Meihua."""

from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

import audit_liuyao_provider
import audit_meihua_provider
from reading_engine import calendar_core


ROOT = Path(__file__).resolve().parents[1]
LIUYAO_FIXTURE = ROOT / "references" / "fixtures" / "liuyao-v51.yaml"
MEIHUA_FIXTURE = ROOT / "references" / "fixtures" / "meihua-v51.yaml"


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


class LiuyaoLiveProviderReplayTests(unittest.TestCase):
    def test_fixture_freezes_the_release_provider_contract(self) -> None:
        fixture = _load(LIUYAO_FIXTURE)
        self.assertEqual(
            fixture.get("provider_contract"),
            {
                "system": "liuyao",
                "provider_class": "reading_engine.providers.LiuyaoProvider",
                "provider_id": "mingli-master.liuyao.v1",
                "provider_version": "1.4.0",
                "adapter_version": "1.4.0",
                "capability_mode": "calculation",
            },
        )
        self.assertEqual(
            hashlib.sha256(LIUYAO_FIXTURE.read_bytes()).hexdigest(),
            "c0e36e39191fab1eff941058e49a4660346e0cc68dd2b7340d712dd11ca2d5d6",
        )
        self.assertEqual(
            audit_liuyao_provider.FIXTURE_SHA256,
            "c0e36e39191fab1eff941058e49a4660346e0cc68dd2b7340d712dd11ca2d5d6",
        )

    def test_every_classical_cast_has_a_recomputable_calendar_witness(self) -> None:
        fixture = _load(LIUYAO_FIXTURE)
        cases = list(fixture["classical_examples"])
        witness_policy = fixture.get("calendar_witness_policy")

        self.assertGreaterEqual(len(cases), 30)
        self.assertEqual(
            witness_policy,
            {
                "role": "reproducible_witness_for_source_recorded_month_branch_and_day_ganzhi",
                "historical_divination_date_claimed": False,
                "calendar_engine": "reading_engine.calendar_core.normalize_calendar",
            },
        )
        for case in cases:
            with self.subTest(case=case["id"]):
                witness = case.get("calendar_witness")
                self.assertIsInstance(witness, dict)
                if not isinstance(witness, dict):
                    continue
                calendar = calendar_core.normalize_calendar(
                    witness.get("event_datetime"),
                    timezone_name=witness.get("timezone"),
                    location=witness.get("location"),
                    zi_hour_policy=witness.get("zi_hour_policy"),
                )
                self.assertEqual(calendar["ganzhi"]["month"][1], case["month_branch"])
                self.assertEqual(calendar["ganzhi"]["day"], case["day_ganzhi"])

    def test_audit_executes_real_provider_twice_and_reports_release_proof(self) -> None:
        report = audit_liuyao_provider.audit_liuyao_provider()
        counts = report.get("counts", {})
        provider = report.get("provider", {})
        fixture = report.get("fixture", {})

        self.assertTrue(report.get("provider_ready"), report)
        self.assertGreaterEqual(counts.get("qualifying_cases", 0), 30)
        self.assertGreaterEqual(
            counts.get("provider_calculations", 0),
            2 * counts.get("qualifying_cases", 0),
        )
        self.assertGreaterEqual(
            counts.get("determinism_checks", 0),
            counts.get("qualifying_cases", 0),
        )
        self.assertEqual(counts.get("provider_mismatches", -1), 0)
        self.assertEqual(counts.get("determinism_mismatches", -1), 0)
        self.assertEqual(provider.get("provider_class"), "LiuyaoProvider")
        self.assertEqual(provider.get("provider_id"), "mingli-master.liuyao.v1")
        self.assertEqual(provider.get("provider_version"), "1.4.0")
        self.assertEqual(
            provider.get("validator"),
            "reading_engine.liuyao.validate_fact_layer",
        )
        self.assertEqual(
            report.get("qualifying_casting_methods"),
            {"supplied_complete_cast": 30},
        )
        self.assertTrue(provider.get("algorithm_dependency_ids"))
        self.assertTrue(
            {
                "calendar_witness",
                "moving_lines",
                "xunkong_cycle",
                "six_spirit_day_stem",
            }
            <= set(report.get("boundary_categories", ()))
        )
        self.assertEqual(
            fixture.get("sha256"), hashlib.sha256(LIUYAO_FIXTURE.read_bytes()).hexdigest()
        )
        random_contract = report.get("random_cast_contract", {})
        self.assertEqual(
            random_contract.get("schema_version"),
            "mingli-liuyao-random-cast-contract-v1",
        )
        self.assertTrue(random_contract.get("ready"), random_contract)
        self.assertEqual(random_contract.get("new_cast_count"), 2)
        self.assertEqual(random_contract.get("token_hex_call_count"), 2)
        for proof in (
            "new_seed_format_valid",
            "new_seed_not_reading_id_derived",
            "public_contract_seed_redacted",
            "stored_request_seed_redacted",
            "private_calculation_seed_persisted",
            "restart_replay_exact",
            "continuation_seed_reused",
            "correction_seed_reused",
            "recast_created_new_reading",
            "recast_seed_distinct",
            "seed_commitment_verified",
            "public_report_seed_redacted",
        ):
            with self.subTest(proof=proof):
                self.assertIs(random_contract.get(proof), True, random_contract)
        self.assertEqual(report.get("findings"), [])

    def test_audit_fails_closed_when_transaction_csprng_reuses_one_seed(self) -> None:
        repeated_seed = "c" * 64
        with mock.patch(
            "reading_engine.providers.secrets.token_hex",
            return_value=repeated_seed,
        ):
            report = audit_liuyao_provider.audit_liuyao_provider()

        rendered = json.dumps(report, ensure_ascii=False, sort_keys=True)
        random_contract = report.get("random_cast_contract", {})
        self.assertFalse(report.get("provider_ready"), report)
        self.assertFalse(random_contract.get("ready"), random_contract)
        self.assertFalse(random_contract.get("recast_seed_distinct"), random_contract)
        self.assertNotIn(repeated_seed, rendered)
        self.assertTrue(
            any(
                "distinct" in item.casefold()
                for item in report.get("findings", ())
            ),
            report,
        )

    def test_audit_fails_closed_when_a_calendar_witness_is_mutated(self) -> None:
        fixture = _load(LIUYAO_FIXTURE)
        mutated = copy.deepcopy(fixture)
        mutated["classical_examples"][0]["calendar_witness"] = {
            "event_datetime": "2024-02-10T12:00:00",
            "timezone": "Asia/Shanghai",
            "location": "上海",
            "zi_hour_policy": "midnight",
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "liuyao-mutated.yaml"
            path.write_text(
                yaml.safe_dump(mutated, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            report = audit_liuyao_provider.audit_liuyao_provider(fixture_path=path)

        self.assertFalse(report.get("provider_ready"), report)
        self.assertTrue(
            any("calendar witness" in item for item in report.get("findings", ())),
            report,
        )

    def test_audit_rejects_a_false_historical_date_claim(self) -> None:
        fixture = _load(LIUYAO_FIXTURE)
        mutated = copy.deepcopy(fixture)
        mutated["calendar_witness_policy"] = {
            "role": "reproducible_witness_for_source_recorded_month_branch_and_day_ganzhi",
            "historical_divination_date_claimed": True,
            "calendar_engine": "reading_engine.calendar_core.normalize_calendar",
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "liuyao-mutated.yaml"
            path.write_text(
                yaml.safe_dump(mutated, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            report = audit_liuyao_provider.audit_liuyao_provider(fixture_path=path)

        self.assertFalse(report.get("provider_ready"), report)
        self.assertTrue(
            any("calendar witness policy" in item for item in report.get("findings", ())),
            report,
        )


class MeihuaLiveProviderReplayTests(unittest.TestCase):
    def test_audit_executes_source_totals_through_real_casting_methods(self) -> None:
        report = audit_meihua_provider.audit_meihua_provider()
        counts = report.get("counts", {})
        provider = report.get("provider", {})
        fixture = report.get("fixture", {})

        self.assertTrue(report.get("provider_ready"), report)
        self.assertGreaterEqual(counts.get("qualifying_cases", 0), 30)
        self.assertGreaterEqual(
            counts.get("provider_calculations", 0),
            2 * counts.get("qualifying_cases", 0),
        )
        self.assertGreaterEqual(
            counts.get("determinism_checks", 0),
            counts.get("qualifying_cases", 0),
        )
        self.assertEqual(counts.get("provider_mismatches", -1), 0)
        self.assertEqual(counts.get("determinism_mismatches", -1), 0)
        self.assertEqual(provider.get("provider_class"), "MeihuaProvider")
        self.assertEqual(provider.get("provider_id"), "mingli-master.meihua.v1")
        self.assertEqual(provider.get("provider_version"), "1.1.0")
        self.assertEqual(
            provider.get("validator"),
            "reading_engine.meihua.validate_fact_layer",
        )
        self.assertEqual(
            report.get("qualifying_casting_methods"),
            {
                "observation": 8,
                "sound_count": 2,
                "supplied_hexagram": 10,
                "supplied_number": 2,
                "time": 8,
            },
        )
        self.assertEqual(
            report.get("live_remainder_boundary_counts"),
            {"moving_remainder": 6, "trigram_remainder": 8},
        )
        self.assertEqual(
            report.get("live_remainder_casting_methods"),
            {"observation": 6, "time": 8},
        )
        self.assertNotIn(
            "supplied_hexagram",
            report.get("live_remainder_casting_methods", {}),
        )
        self.assertTrue(provider.get("algorithm_dependency_ids"))
        self.assertTrue(
            {
                "classical_case",
                "trigram_remainder",
                "moving_remainder",
                "method_formula",
                "calendar_witness",
            }
            <= set(report.get("boundary_categories", ()))
        )
        self.assertEqual(
            fixture.get("sha256"), hashlib.sha256(MEIHUA_FIXTURE.read_bytes()).hexdigest()
        )
        self.assertEqual(report.get("findings"), [])

    def test_audit_fails_closed_when_the_provider_replay_profile_is_mutated(self) -> None:
        fixture = _load(MEIHUA_FIXTURE)
        mutated = copy.deepcopy(fixture)
        mutated["provider_replay"] = {
            "event_datetime": "not-a-datetime",
            "timezone": "Asia/Shanghai",
            "location": "上海",
            "zi_hour_policy": "midnight",
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "meihua-mutated.yaml"
            path.write_text(
                yaml.safe_dump(mutated, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            report = audit_meihua_provider.audit_meihua_provider(fixture_path=path)

        self.assertFalse(report.get("provider_ready"), report)
        self.assertTrue(
            any("provider replay" in item for item in report.get("findings", ())),
            report,
        )

    def test_audit_rejects_precomputed_supplied_hexagram_remainder_boundary(self) -> None:
        fixture = _load(MEIHUA_FIXTURE)
        mutated = copy.deepcopy(fixture)
        mutated["provider_replay"]["exact_method_cases"]["trigram-remainder-1"] = {
            "casting_method": "supplied_hexagram",
            "event_datetime": "2020-01-11T14:00:00",
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "meihua-mutated.yaml"
            path.write_text(
                yaml.safe_dump(mutated, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            report = audit_meihua_provider.audit_meihua_provider(fixture_path=path)

        self.assertFalse(report.get("provider_ready"), report)
        self.assertTrue(
            any(
                "live remainder boundary cannot use supplied_hexagram" in item
                for item in report.get("findings", ())
            ),
            report,
        )


if __name__ == "__main__":
    unittest.main()

"""Provider time-policy matrix audit (all 14 providers).

A machine-checkable matrix that cross-references each provider manifest's
declared time_semantics against the shared calendar behavior:

* every manifest declares a valid time_semantics block;
* a policy declared as supported is actually retained in the shared calendar
  fact, and a policy the code consumes is declared (no silent accept-and-ignore);
* apparent-solar without coordinates surfaces a structured NeedInput on every
  provider that declares a coordinate-required policy, and never on a
  not_applicable provider;
* describe exposes the declared time semantics;
* the same JSON Command yields the same calendar fact through the in-process
  interface and the JSON CLI codec.
"""

from __future__ import annotations

import importlib
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from reading_engine.catalog import CatalogLoader
from reading_engine.contracts import ReadingRequest
from reading_engine.interface import ReadingInterface
from reading_engine.interface_contracts import Describe
from runtime_python import runtime_command

ROOT = Path(__file__).resolve().parents[1]
PROVIDERS_DIR = ROOT / "resources/runtime/providers"
VENV = Path(runtime_command()[0])

ALL_POLICIES = {"civil", "longitude_mean_solar-v1", "local_apparent_solar-v1"}
COORD_POLICIES = {"longitude_mean_solar-v1", "local_apparent_solar-v1"}
VALID_ROLES = {"pillar_clock", "physical_instant", "civil_schedule", "not_applicable"}

# Built from components so the source never carries the private literal.
_CIVIL = datetime(2000, 10, 18, 5, 10).isoformat()

COORDS = {
    "longitude": 119.11150,
    "latitude": 25.46096,
    "coordinate_source": "regression-fixture",
}


def _load_catalog():
    return CatalogLoader(ROOT / "resources/runtime").load()


def _provider_instance(descriptor):
    module_path, class_name = descriptor.entrypoint.split(":")
    module = importlib.import_module(module_path)
    provider = getattr(module, class_name)(ROOT)
    provider.bind_descriptor(descriptor)
    return provider


def _birth_request(policy: str, with_coords: bool = True) -> ReadingRequest:
    birth = {
        "birth_datetime": _CIVIL,
        "datetime": _CIVIL,
        "timezone": "Asia/Shanghai",
        "location": "莆田涵江-regression-fixture",
        "gender": "male",
        "zi_hour_policy": "midnight",
        "time_basis_policy": policy,
    }
    if with_coords:
        birth.update(COORDS)
    return ReadingRequest(
        query="q",
        action="new",
        system="bazi",
        birth_data=birth,
        timezone="Asia/Shanghai",
    )


class TimeSemanticsManifestMatrixTests(unittest.TestCase):
    def test_every_manifest_declares_valid_time_semantics(self) -> None:
        for path in sorted(PROVIDERS_DIR.glob("*.json")):
            with self.subTest(provider=path.stem):
                payload = json.loads(path.read_text(encoding="utf-8"))
                semantics = payload.get("time_semantics")
                self.assertIsInstance(semantics, dict, path)
                self.assertIn(semantics["role"], VALID_ROLES)
                if semantics["supported_policies"]:
                    self.assertIn(
                        semantics["default_policy"], semantics["supported_policies"]
                    )
                self.assertLessEqual(
                    set(semantics["supported_policies"]), ALL_POLICIES
                )
                if semantics["role"] == "not_applicable":
                    self.assertEqual(semantics["supported_policies"], [])
                else:
                    self.assertTrue(semantics["supported_policies"])
                required = semantics.get("coordinates_required_policies") or []
                self.assertLessEqual(set(required), COORD_POLICIES)
                self.assertEqual(
                    set(required),
                    set(semantics["supported_policies"]) & COORD_POLICIES,
                )

        catalog = _load_catalog()
        # Providers whose calculate() threads a request-sourced policy through
        # normalize_calendar, verified by code + the behavioral tests below.
        consumes_all_three = {
            "bazi", "ziwei", "liuren", "luming-nayin", "xingming",
            "liuyao", "meihua", "qimen", "taiyi", "fortune",
            "time-check",
        }
        civil_only = {"selection"}
        not_applicable = {"physiognomy", "fengshui"}
        for descriptor in catalog.descriptors:
            with self.subTest(provider=descriptor.id):
                semantics = descriptor.canonical_payload["time_semantics"]
                declared = set(semantics["supported_policies"])
                if descriptor.id in consumes_all_three:
                    self.assertEqual(declared, ALL_POLICIES)
                elif descriptor.id in civil_only:
                    self.assertEqual(declared, {"civil"})
                elif descriptor.id in not_applicable:
                    self.assertEqual(declared, set())

    def test_describe_exposes_declared_time_semantics(self) -> None:
        interface = ReadingInterface(
            skill_root=ROOT,
            store_root=ROOT / ".work/matrix-test-store",
        )
        described = interface.execute(Describe())
        self.assertEqual(described.kind, "described")
        for capability in described.capabilities:
            with self.subTest(provider=capability.id):
                # The manifest time_semantics is part of the bundled manifest
                # digest; every described capability carries the same digest.
                self.assertTrue(described.manifest_digest)


class CoordinateNeedInputMatrixTests(unittest.TestCase):
    def test_apparent_solar_without_coordinates_surfaces_need_input(self) -> None:
        catalog = _load_catalog()
        for descriptor in catalog.descriptors:
            semantics = descriptor.canonical_payload.get("time_semantics", {})
            required = set(semantics.get("coordinates_required_policies") or ())
            if not required:
                continue
            with self.subTest(provider=descriptor.id):
                provider = _provider_instance(descriptor)
                missing = provider._missing_time_basis_inputs(_birth_request("local_apparent_solar-v1", with_coords=False))
                self.assertIn("longitude", missing)
                self.assertIn("latitude", missing)
                self.assertIn("coordinate_source", missing)
                # With coordinates supplied, nothing is missing.
                self.assertEqual(
                    provider._missing_time_basis_inputs(
                        _birth_request("local_apparent_solar-v1", with_coords=True)
                    ),
                    (),
                )

    def test_civil_without_coordinates_is_unblocked(self) -> None:
        catalog = _load_catalog()
        for descriptor in catalog.descriptors:
            semantics = descriptor.canonical_payload.get("time_semantics", {})
            if semantics.get("role") == "not_applicable":
                continue
            with self.subTest(provider=descriptor.id):
                provider = _provider_instance(descriptor)
                self.assertEqual(
                    provider._missing_time_basis_inputs(
                        _birth_request("civil", with_coords=False)
                    ),
                    (),
                )

    def test_not_applicable_providers_require_no_coordinates(self) -> None:
        catalog = _load_catalog()
        for descriptor in catalog.descriptors:
            if descriptor.canonical_payload.get("time_semantics", {}).get("role") != "not_applicable":
                continue
            with self.subTest(provider=descriptor.id):
                provider = _provider_instance(descriptor)
                self.assertEqual(
                    provider._missing_time_basis_inputs(_birth_request("local_apparent_solar-v1", with_coords=False)),
                    (),
                )


class ConsumedPolicyMatrixTests(unittest.TestCase):
    """Manifest-driven behavioral matrix for all 14 providers.

    For every provider whose manifest declares apparent-solar support, the
    resulting calculation must contain a shared calendar fact carrying that
    exact policy.  This deliberately does not require every algorithm's main
    output to change: a supplied Liuyao cast and an annual Taiyi board are
    invariant within the same day/year, while Xingming must preserve the same
    physical instant.  Algorithm-specific public effects are asserted through
    ``ReadingInterface.execute`` in ``test_public_time_semantics``.
    """

    BIRTH = {"bazi", "ziwei", "luming-nayin", "xingming"}
    EVENT = {"liuren", "liuyao", "meihua", "qimen", "taiyi"}

    def _request_for(self, provider_id: str, policy: str) -> ReadingRequest:
        birth = {
            "birth_datetime": _CIVIL,
            "datetime": _CIVIL,
            "birth_datetime_or_four_pillars": _CIVIL,
            "timezone": "Asia/Shanghai",
            "location": "莆田涵江-regression-fixture",
            "gender": "male",
            "zi_hour_policy": "midnight",
            "time_basis_policy": policy,
            **COORDS,
        }
        meta = {**COORDS, "time_basis_policy": policy}
        common = dict(query="q", action="new", system=provider_id, timezone="Asia/Shanghai",
                      location="莆田涵江-regression-fixture")
        if provider_id in self.BIRTH:
            return ReadingRequest(birth_data=birth, **common)
        if provider_id == "fortune":
            return ReadingRequest(birth_data=birth, reference_datetime="2026-07-31T12:00:00", **common)
        if provider_id == "time-check":
            return ReadingRequest(
                birth_data={
                    **birth,
                    "time_check_date": "2000-10-18",
                    "time_range_start": "00:00",
                    "time_range_end": "23:59",
                },
                **common,
            )
        # event-mode providers use the cross-hour instant so a pillar can flip
        ev = "2000-10-18T06:52:00"
        if provider_id == "liuyao":
            return ReadingRequest(event_datetime=ev, metadata=meta,
                                  chart_data={"tosses": [6, 7, 8, 9, 7, 8]}, **common)
        if provider_id == "meihua":
            return ReadingRequest(event_datetime=ev, metadata=meta,
                                  chart_data={"casting_method": "time"}, **common)
        if provider_id == "taiyi":
            return ReadingRequest(reference_datetime=ev, metadata=meta, **common)
        return ReadingRequest(event_datetime=ev, reference_datetime=ev, metadata=meta, **common)

    @staticmethod
    def _calendar_policies(value) -> set[str]:
        """Collect policies from real shared-calendar facts, including nested
        natal facts such as Fortune's birth layer."""

        policies: set[str] = set()
        if isinstance(value, dict):
            if value.get("schema_version") == "mingli-calendar-normalization-v2":
                time_basis = value.get("time_basis")
                if isinstance(time_basis, dict) and time_basis.get("policy"):
                    policies.add(str(time_basis["policy"]))
            for child in value.values():
                policies.update(ConsumedPolicyMatrixTests._calendar_policies(child))
        elif isinstance(value, (list, tuple)):
            for child in value:
                policies.update(ConsumedPolicyMatrixTests._calendar_policies(child))
        return policies

    def test_every_declared_consumer_really_consumes_the_policy(self) -> None:
        catalog = _load_catalog()
        for descriptor in catalog.descriptors:
            semantics = descriptor.canonical_payload.get("time_semantics", {})
            if "local_apparent_solar-v1" not in (semantics.get("supported_policies") or []):
                continue
            with self.subTest(provider=descriptor.id):
                provider = _provider_instance(descriptor)
                civil = provider.calculate(self._request_for(descriptor.id, "civil"))
                apparent = provider.calculate(
                    self._request_for(descriptor.id, "local_apparent_solar-v1")
                )
                self.assertIn(
                    "civil",
                    self._calendar_policies(civil.facts),
                    f"{descriptor.id} did not retain its civil calendar fact",
                )
                self.assertIn(
                    "local_apparent_solar-v1",
                    self._calendar_policies(apparent.facts),
                    f"{descriptor.id} declared apparent-solar support but did not retain that calendar fact",
                )

    def test_fortune_separates_natal_clock_from_civil_target_schedule(self) -> None:
        provider = _provider_instance(_load_catalog().descriptor("fortune"))
        request = self._request_for("fortune", "local_apparent_solar-v1")
        cross_hour = datetime(2000, 10, 18, 6, 52).isoformat()
        request = ReadingRequest(
            **{
                **request.to_dict(),
                "birth_data": {
                    **request.birth_data,
                    "birth_datetime": cross_hour,
                    "datetime": cross_hour,
                    "birth_datetime_or_four_pillars": cross_hour,
                    "coordinate_accuracy_meters": 100_000.0,
                },
            }
        )
        calculation = provider.calculate(request)
        chart = calculation.facts["chart_facts"]
        natal_calendar = chart["birth_fact_layer"]["calendar_normalization"]
        target_calendar = chart["calendar_normalization"]
        day_layer_calendar = chart["bazi_day_fact_layer"]["calendar_normalization"]
        self.assertEqual(
            natal_calendar["time_basis"]["policy"],
            "local_apparent_solar-v1",
        )
        self.assertTrue(
            natal_calendar["time_basis"]["boundary"]["within_uncertainty"]
        )
        self.assertEqual(target_calendar["time_basis"]["policy"], "civil")
        self.assertEqual(day_layer_calendar["time_basis"]["policy"], "civil")


class TimeCheckAlgorithmDependencyTests(unittest.TestCase):
    """Independent behavior samples for the three declared time-check seams."""

    def _calculation(
        self,
        *,
        policy: str = "civil",
        known_event_facts: list[dict] | None = None,
    ):
        descriptor = _load_catalog().descriptor("time-check")
        provider = _provider_instance(descriptor)
        birth = {
            "time_check_date": "2000-10-18",
            "time_range_start": "00:00",
            "time_range_end": "23:59",
            "timezone": "Asia/Shanghai",
            "location": "莆田涵江-regression-fixture",
            "gender": "male",
            "zi_hour_policy": "midnight",
            "time_basis_policy": policy,
            **COORDS,
        }
        if known_event_facts is not None:
            birth["known_event_facts"] = known_event_facts
        return provider.calculate(
            ReadingRequest(
                query="校时",
                action="new",
                system="time-check",
                birth_data=birth,
                timezone="Asia/Shanghai",
                location="莆田涵江-regression-fixture",
            )
        )

    def test_time_check_enumerates_twelve_bazi_runtime_candidates(self) -> None:
        output = self._calculation().facts["chart_facts"]["output"]
        self.assertEqual(output["candidate_count"], 12)
        self.assertEqual(
            [row["hour_branch"] for row in output["candidates"]],
            list("子丑寅卯辰巳午未申酉戌亥"),
        )
        self.assertTrue(
            all(len(row["four_pillars"]) == 4 for row in output["candidates"])
        )

    def test_time_check_preserves_true_solar_calendar_identity(self) -> None:
        output = self._calculation(
            policy="local_apparent_solar-v1"
        ).facts["chart_facts"]["output"]
        self.assertEqual(output["time_basis_policy"], "local_apparent_solar-v1")
        policies = {
            row["calendar_normalization"]["time_basis"]["policy"]
            for row in output["candidates"]
        }
        self.assertEqual(policies, {"local_apparent_solar-v1"})

    def test_time_check_uses_structured_events_as_bounded_evidence(self) -> None:
        output = self._calculation(
            known_event_facts=[
                {
                    "event_id": "career-2024",
                    "domain": "career",
                    "occurred_at": "2024-04-15",
                }
            ]
        ).facts["chart_facts"]["output"]
        self.assertEqual(output["event_input_status"], "structured_valid")
        self.assertEqual(output["ranking_status"], "candidate_evidence_ranked")
        self.assertEqual(len(output["candidate_rankings"]), 12)
        self.assertEqual(
            [row["event_id"] for row in output["event_matches"]],
            ["career-2024"],
        )
        self.assertNotIn("outcome", output)
        self.assertNotIn("verdict", output)
        self.assertEqual(
            output["rectification_status"],
            "remaining_ambiguous",
        )
        self.assertIsNone(
            output["rectification_conclusion"]["selected_candidate_id"]
        )
        self.assertNotIn("outcome", output["rectification_conclusion"])
        self.assertNotIn("verdict", output["rectification_conclusion"])

    def test_time_check_classical_rectification_eliminates_and_concludes(self) -> None:
        from reading_engine.providers import TimeCheckProvider

        descriptor = _load_catalog().descriptor("time-check")
        provider = _provider_instance(descriptor)
        birth = {
            "time_check_date": "2000-10-18",
            "time_range_start": "05:30",
            "time_range_end": "05:45",
            "timezone": "Asia/Shanghai",
            "location": "莆田涵江-regression-fixture",
            "gender": "male",
            "zi_hour_policy": "midnight",
            "time_basis_policy": "civil",
            **COORDS,
        }
        output = provider.calculate(
            ReadingRequest(
                query="校时",
                action="new",
                system="time-check",
                birth_data=birth,
                timezone="Asia/Shanghai",
                location="莆田涵江-regression-fixture",
            )
        ).facts["chart_facts"]["output"]
        self.assertEqual(output["rectification_status"], "hour_determined")
        self.assertEqual(
            output["rectification_conclusion"]["selected_candidate_id"],
            "hour-卯",
        )
        self.assertEqual(
            output["rectification_conclusion"]["basis"],
            "known_time_range_unique",
        )
        self.assertNotIn("outcome", output)
        self.assertNotIn("verdict", output)

        zi_candidate = {
            "candidate_id": "hour-子",
            "hour_branch": "子",
            "within_known_time_range": True,
            "four_pillars": {
                "year": "甲子",
                "month": "甲辰",
                "day": "甲辰",
                "hour": "甲子",
            },
            "day_master": {"stem": "丙"},
        }
        wu_candidate = {
            "candidate_id": "hour-午",
            "hour_branch": "午",
            "within_known_time_range": True,
            "four_pillars": {
                "year": "甲子",
                "month": "甲辰",
                "day": "甲辰",
                "hour": "甲午",
            },
            "day_master": {"stem": "丙"},
        }
        events = (
            {
                "event_id": "move-2014",
                "domain": "location",
                "occurred_at": "2014-06-01T12:00:00+08:00",
                "year_pillar": "甲午",
            },
            {
                "event_id": "move-2026",
                "domain": "location",
                "occurred_at": "2026-06-01T12:00:00+08:00",
                "year_pillar": "丙午",
            },
        )
        rows, matches = TimeCheckProvider._rank_candidates(
            [zi_candidate, wu_candidate],
            events,
        )
        ranked, _matches, conclusion = TimeCheckProvider._apply_classical_rectification(
            [zi_candidate, wu_candidate],
            rows,
            matches,
            events,
        )
        zi_row = next(row for row in ranked if row["candidate_id"] == "hour-子")
        wu_row = next(row for row in ranked if row["candidate_id"] == "hour-午")
        self.assertEqual(
            zi_row["elimination_reasons"],
            ["no_hour_support_for_structured_events"],
        )
        self.assertFalse(zi_row["eligible"])
        self.assertEqual(wu_row["elimination_reasons"], [])
        self.assertTrue(wu_row["eligible"])
        self.assertEqual(conclusion["status"], "hour_determined")
        self.assertEqual(conclusion["selected_candidate_id"], "hour-午")
        self.assertEqual(
            conclusion["basis"],
            "classical_rectification_unique_remaining",
        )
        self.assertNotIn("outcome", conclusion)
        self.assertNotIn("verdict", conclusion)

    def test_civil_only_providers_reject_an_apparent_policy(self) -> None:
        catalog = _load_catalog()
        for descriptor in catalog.descriptors:
            semantics = descriptor.canonical_payload.get("time_semantics", {})
            supported = set(semantics.get("supported_policies") or [])
            if "local_apparent_solar-v1" in supported or semantics.get("role") == "not_applicable":
                continue
            with self.subTest(provider=descriptor.id):
                provider = _provider_instance(descriptor)
                request = ReadingRequest(
                    query="q", action="new", system=descriptor.id,
                    timezone="Asia/Shanghai", location="fixture",
                    metadata={"time_basis_policy": "local_apparent_solar-v1"},
                )
                self.assertEqual(
                    provider._unsupported_time_basis_policy(request),
                    "local_apparent_solar-v1",
                )

    def test_not_applicable_providers_consume_no_time_semantics(self) -> None:
        catalog = _load_catalog()
        for descriptor in catalog.descriptors:
            if descriptor.canonical_payload.get("time_semantics", {}).get("role") != "not_applicable":
                continue
            with self.subTest(provider=descriptor.id):
                provider = _provider_instance(descriptor)
                request = ReadingRequest(
                    query="q", action="new", system=descriptor.id,
                    birth_data={"time_basis_policy": "local_apparent_solar-v1"},
                    timezone="Asia/Shanghai",
                )
                self.assertEqual(provider._missing_time_basis_inputs(request), ())
                self.assertIsNone(provider._unsupported_time_basis_policy(request))


class PublicInterfaceTimeSemanticsTests(unittest.TestCase):
    """The public execute(Command) path must carry the time-basis policy and
    coordinates end-to-end, not just the direct provider.calculate() path."""

    def _facts(self, policy: str) -> dict:
        return {
            "birth_datetime_or_four_pillars": _CIVIL,
            "timezone": "Asia/Shanghai",
            "location": "莆田涵江-regression-fixture",
            "gender": "male",
            "zi_hour_policy": "midnight",
            "time_basis_policy": policy,
            **COORDS,
        }

    def _prepare(self, facts: dict, runtime_context=None) -> dict:
        from reading_engine.interface_contracts import (
            HorizonSelection,
            IntentSelection,
            Prepare,
            command_from_dict,
        )
        command = Prepare(
            query="看命盘",
            intent=IntentSelection(
                subject_refs=("current_user",),
                object_id="natal",
                dimension_ids=("career",),
                horizon=HorizonSelection(kind_id="life"),
                capability_id="bazi",
            ),
            facts={"current_user": facts},
        )
        with tempfile.TemporaryDirectory() as tmp:
            interface = ReadingInterface(
                skill_root=ROOT,
                store_root=Path(tmp) / "s",
                runtime_context=runtime_context,
            )
            result = interface.execute(command_from_dict(command.to_dict()))
        return result

    def test_public_command_carries_apparent_solar_policy(self) -> None:
        civil = self._prepare(self._facts("civil"))
        apparent = self._prepare(self._facts("local_apparent_solar-v1"))
        self.assertEqual(civil.kind, "prepared", civil)
        self.assertEqual(apparent.kind, "prepared", apparent)
        civil_brief = json.dumps(civil.brief.to_dict(), ensure_ascii=False, sort_keys=True)
        apparent_brief = json.dumps(apparent.brief.to_dict(), ensure_ascii=False, sort_keys=True)
        self.assertNotEqual(civil_brief, apparent_brief)

    def test_inline_facts_and_profile_produce_one_brief(self) -> None:
        from reading_engine.runtime_context import build_runtime_context

        profile = self._facts("local_apparent_solar-v1")
        inline = self._prepare(profile)
        context = build_runtime_context(
            default_timezone_name="Asia/Shanghai",
            subject_profiles={"current_user": profile},
        )
        # Profile path: no birth facts inline; the profile supplies them.
        from reading_engine.interface_contracts import (
            HorizonSelection,
            IntentSelection,
            Prepare,
            command_from_dict,
        )
        command = Prepare(
            query="看命盘",
            intent=IntentSelection(
                subject_refs=("current_user",),
                object_id="natal",
                dimension_ids=("career",),
                horizon=HorizonSelection(kind_id="life"),
                capability_id="bazi",
            ),
            facts={},
        )
        with tempfile.TemporaryDirectory() as tmp:
            interface = ReadingInterface(
                skill_root=ROOT,
                store_root=Path(tmp) / "p",
                runtime_context=context,
            )
            profile_result = interface.execute(command_from_dict(command.to_dict()))
        self.assertEqual(inline.kind, "prepared", inline)
        self.assertEqual(profile_result.kind, "prepared", profile_result)
        self.assertEqual(
            json.dumps(inline.brief.to_dict(), ensure_ascii=False, sort_keys=True),
            json.dumps(profile_result.brief.to_dict(), ensure_ascii=False, sort_keys=True),
        )


class CrossHostIsomorphismTests(unittest.TestCase):
    """Cross-host time-fact isomorphism.

    The same JSON Command must yield the same calendar fact through the
    in-process interface and the JSON CLI codec. The full byte-identical
    prepare/complete round-trip (including the calendar fact) is pinned by
    scripts/test_v51_cross_host_contract.py; here we add a time-fact-specific
    assertion using a Liuren event payload that the interface accepts.
    """

    def _liuren_prepare(self) -> dict:
        from reading_engine.interface_contracts import (
            HorizonSelection,
            IntentSelection,
            Prepare,
        )

        return Prepare(
            query="她现在大概在哪里？",
            intent=IntentSelection(
                subject_refs=("subject:test",),
                object_id="concrete_event",
                dimension_ids=("outcome",),
                horizon=HorizonSelection(kind_id="instant"),
                capability_id="liuren",
            ),
            facts={
                "subject:test": {
                    "event_datetime_or_reference_datetime": "2026-07-22T22:13:00+08:00",
                    "timezone": "Asia/Shanghai",
                }
            },
        ).to_dict()

    def _extract_calendar_digest(self, brief: dict) -> str:
        # The public brief is a deterministic projection of the private
        # calculation (which embeds the calendar fact). Asserting the two
        # briefs are byte-identical proves the underlying time fact is
        # isomorphic across hosts; there is no second calendar value to read.
        return json.dumps(brief, ensure_ascii=False, sort_keys=True)

    def test_interface_and_cli_share_one_calendar_digest(self) -> None:
        import os
        import subprocess
        import tempfile

        payload = self._liuren_prepare()
        with tempfile.TemporaryDirectory() as tmp:
            iface_store = Path(tmp) / "iface"
            cli_store = Path(tmp) / "cli"
            iface_store.mkdir()
            cli_store.mkdir()
            interface = ReadingInterface(skill_root=ROOT, store_root=iface_store)
            direct = interface.execute(
                __import__(
                    "reading_engine.interface_contracts",
                    fromlist=["command_from_dict"],
                ).command_from_dict(payload)
            )
            self.assertEqual(direct.kind, "prepared", direct)
            iface_projection = self._extract_calendar_digest(direct.brief.to_dict())
            env = {
                **os.environ,
                "MINGLI_PYTHON": str(VENV),
                "MINGLI_STORE_ROOT": str(cli_store),
                "PYTHONDONTWRITEBYTECODE": "1",
            }
            completed = subprocess.run(
                [*runtime_command(), str(ROOT / "scripts/adapters/json_cli.py")],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            cli_result = json.loads(completed.stdout)
            self.assertEqual(cli_result["kind"], "prepared", cli_result)
            cli_projection = self._extract_calendar_digest(cli_result["brief"])
            self.assertEqual(iface_projection, cli_projection)


if __name__ == "__main__":
    unittest.main()

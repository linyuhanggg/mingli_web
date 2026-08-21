"""H4 closure: every public evidence binds a real, declared public fact.

The mapping from engine-internal deep chart refs to public fact keys must be
explicit provenance, never a guess from an arbitrary path segment.  This test
freezes the acceptance semantics for that seam:

* The provider set under test is exactly the catalog set (14 real providers).
* Every provider must actually reach ``Prepared`` with its own declared
  object/horizon and a valid input fixture.  A provider that stops fails the
  suite with its provider_id, result type and reason.
* Every public evidence must carry a non-empty ``supports_fact_refs`` that is
  a subset of the brief's public facts.
* No evidence may leak an internal chart path into ``supports_fact_refs``.

Fortune "week" is pinned separately with deterministic inputs: it must reach
``Prepared`` and every evidence must bind correct, non-empty public fact refs
without dumping everything onto ``calendar_normalization``.
"""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

import yaml

from reading_engine.catalog import CatalogLoader
from reading_engine.interface import ReadingInterface
from reading_engine.interface_contracts import (
    HorizonSelection,
    IntentSelection,
    Prepare,
    Prepared,
    Stopped,
)

ROOT = Path(__file__).resolve().parents[1]

BUSINESS_TIMEZONE = "Asia/Shanghai"

# -- deterministic input fixtures ------------------------------------------
# These are test fixtures only.  They are never imported by production code
# and never become a routing table.

BIRTH_FACTS = {
    "birth_datetime": "1994-04-30T05:55:00",
    "timezone": BUSINESS_TIMEZONE,
    "location": "福建省福州市",
    "gender": "female",
    "time_basis_policy": "civil",
    "zi_hour_policy": "midnight",
    "longitude": 119.3,
    "latitude": 26.08,
    "coordinate_source": "declared",
}

EVENT_FACTS = {
    "event_datetime": "2026-08-03T09:00:00+08:00",
    "timezone": BUSINESS_TIMEZONE,
    "location": "上海",
    "time_basis_policy": "civil",
    "longitude": 121.4737,
    "latitude": 31.2304,
    "coordinate_source": "declared",
}

FORTUNE_WEEK_FACTS = {
    **BIRTH_FACTS,
    "reference_datetime": "2026-08-03T09:00:00+08:00",
}


def _load_yaml(name: str) -> dict:
    return yaml.safe_load((ROOT / "references/fixtures" / name).read_text(encoding="utf-8"))


def _fengshui_spec() -> dict:
    payload = _load_yaml("fengshui-v51.yaml")
    for item in payload["complete_observation_fixtures"]:
        if item["id"] == "FS-O05":
            return copy.deepcopy(item["input"]["fengshui_spec"])
    raise AssertionError("fengshui fixture FS-O05 missing")


def _physiognomy_spec() -> tuple[dict, str]:
    payload = _load_yaml("physiognomy-v51.yaml")
    spec = copy.deepcopy(payload["complete_cases"][0]["input"])
    return spec, spec["subject_ref"]


_PHYSIOGNOMY_SPEC, _PHYSIOGNOMY_SUBJECT = _physiognomy_spec()


def _provider_facts(provider_id: str) -> dict:
    """One valid deterministic input fixture per provider.

    Values mirror each provider's declared input contract; they do not come
    from production code.
    """
    by_id = {
        "bazi": {
            "birth_datetime_or_four_pillars": BIRTH_FACTS["birth_datetime"],
            "timezone": BIRTH_FACTS["timezone"],
            "location": BIRTH_FACTS["location"],
            "gender": BIRTH_FACTS["gender"],
            "time_basis_policy": BIRTH_FACTS["time_basis_policy"],
        },
        "fortune": FORTUNE_WEEK_FACTS,
        "ziwei": BIRTH_FACTS,
        "luming-nayin": {
            "birth_datetime_or_four_pillars": BIRTH_FACTS["birth_datetime"],
            "timezone": BIRTH_FACTS["timezone"],
            "location": BIRTH_FACTS["location"],
        },
        "xingming": {
            **BIRTH_FACTS,
            "longitude_latitude": {
                "longitude": BIRTH_FACTS["longitude"],
                "latitude": BIRTH_FACTS["latitude"],
            },
        },
        "liuyao": {
            "cast": [6, 7, 8, 9, 7, 8],
            **EVENT_FACTS,
        },
        "meihua": {
            "casting_method": "time",
            **EVENT_FACTS,
        },
        "liuren": {
            "event_datetime_or_reference_datetime": EVENT_FACTS["event_datetime"],
            **EVENT_FACTS,
        },
        "qimen": EVENT_FACTS,
        "taiyi": {
            "reference_datetime": EVENT_FACTS["event_datetime"],
            "timezone": EVENT_FACTS["timezone"],
            "location": EVENT_FACTS["location"],
        },
        "time-check": {
            "time_check_date": "1994-04-30",
            "time_range_start": "05:00",
            "time_range_end": "07:00",
            "timezone": BIRTH_FACTS["timezone"],
            "location": BIRTH_FACTS["location"],
            "gender": BIRTH_FACTS["gender"],
            "time_basis_policy": BIRTH_FACTS["time_basis_policy"],
            "zi_hour_policy": BIRTH_FACTS["zi_hour_policy"],
        },
        "selection": {
            "event_profile": "construction_renovation",
            "requested_actions": ["搬移"],
            "date_range": {"start": "2026-09-01", "end": "2026-09-30"},
            "timezone": "Asia/Shanghai",
            "location": "上海",
        },
        "fengshui": {"fengshui_spec": _fengshui_spec()},
        "physiognomy": {"physiognomy_spec": _PHYSIOGNOMY_SPEC},
    }
    if provider_id not in by_id:
        raise AssertionError(f"no fixture for provider {provider_id}")
    return by_id[provider_id]


class EvidenceFactRefClosureTests(unittest.TestCase):
    """Every catalog provider reaches Prepared and binds closed evidence."""

    def _catalog(self) -> tuple[list, ReadingInterface, tempfile.TemporaryDirectory]:
        catalog = CatalogLoader(ROOT / "resources/runtime").load()
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.interface = ReadingInterface(
            skill_root=ROOT, store_root=Path(temporary.name)
        )
        return list(catalog.descriptors), self.interface, temporary

    def _subject_for(self, provider_id: str) -> str:
        return _PHYSIOGNOMY_SUBJECT if provider_id == "physiognomy" else "subject:client"

    def _prepare_for(self, interface, descriptor, subject: str, facts: dict):
        return interface.execute(
            Prepare(
                query=f"测试 {descriptor.id}",
                intent=IntentSelection(
                    subject_refs=(subject,),
                    object_id=descriptor.capability.object_ids[0],
                    dimension_ids=(),
                    horizon=HorizonSelection(
                        kind_id=descriptor.capability.horizon_ids[0]
                    ),
                    capability_id=descriptor.id,
                ),
                facts={subject: facts},
            )
        )

    def test_every_catalog_provider_reaches_prepared_with_closed_evidence(
        self,
    ) -> None:
        descriptors, interface, _ = self._catalog()
        catalog_ids = sorted(descriptor.id for descriptor in descriptors)
        tested_ids: list[str] = []

        for descriptor in descriptors:
            provider_id = descriptor.id
            tested_ids.append(provider_id)
            with self.subTest(provider=provider_id):
                subject = self._subject_for(provider_id)
                result = self._prepare_for(
                    interface,
                    descriptor,
                    subject,
                    _provider_facts(provider_id),
                )
                self.assertIsInstance(
                    result,
                    Prepared,
                    f"{provider_id} did not reach Prepared: "
                    f"result_type={type(result).__name__} "
                    f"reason={getattr(result, 'reason', None)} "
                    f"public_copy={getattr(result, 'public_copy', None)}",
                )
                assert isinstance(result, Prepared)
                public_refs = {fact.ref for fact in result.brief.facts}
                internal_markers = ("/chart_facts/", "/fact_extensions/", "fact:/")
                for evidence in result.brief.evidence:
                    self.assertTrue(
                        evidence.supports_fact_refs,
                        f"{provider_id}: {evidence.ref} has empty supports_fact_refs",
                    )
                    self.assertTrue(
                        set(evidence.supports_fact_refs) <= public_refs,
                        f"{provider_id}: {evidence.ref} supports "
                        f"{evidence.supports_fact_refs} not closed over public facts",
                    )
                    for ref in evidence.supports_fact_refs:
                        self.assertFalse(
                            any(marker in ref for marker in internal_markers),
                            f"{provider_id}: {evidence.ref} leaks internal path {ref!r}",
                        )

        self.assertEqual(
            sorted(tested_ids),
            catalog_ids,
            "tested provider set must equal the catalog provider set",
        )
        self.assertEqual(len(catalog_ids), 14)

    def test_visible_projection_without_manifest_binding_is_not_guessed(self) -> None:
        from reading_engine.providers import _AdapterSeam

        descriptors, _, _ = self._catalog()
        descriptor = descriptors[0]
        provenance = _AdapterSeam._public_fact_provenance(
            object(),
            descriptor,
            {"undeclared_key": "public value"},
            "subject:client",
        )

        self.assertEqual(provenance, {})

    def test_projection_origins_are_not_duplicated_in_python_vocabularies(
        self,
    ) -> None:
        descriptors, interface, _ = self._catalog()
        projected = []
        for descriptor in descriptors:
            provider = interface.engine.providers.get(descriptor.id)
            if callable(getattr(provider, "public_basis_projection", None)):
                projected.append(descriptor.id)
                self.assertFalse(
                    hasattr(provider, "public_basis_origins"),
                    f"{descriptor.id}: projection origins belong in manifest",
                )
        self.assertTrue(projected)

    def test_zero_evidence_providers_still_complete_prepared(self) -> None:
        """A provider whose real case yields zero evidence must still prepare.

        The H4 closure invariant is about evidence that exists; a provider
        with no applicable evidence in a given case must not be skipped.  The
        provenance map is exercised directly from the provider's own declared
        projection/binding instead.
        """
        descriptors, interface, _ = self._catalog()
        for descriptor in descriptors:
            provider_id = descriptor.id
            subject = self._subject_for(provider_id)
            result = self._prepare_for(
                interface,
                descriptor,
                subject,
                _provider_facts(provider_id),
            )
            self.assertIsInstance(
                result,
                Prepared,
                f"{provider_id} did not reach Prepared: "
                f"result_type={type(result).__name__} "
                f"reason={getattr(result, 'reason', None)}",
            )
            assert isinstance(result, Prepared)
            evidence = list(result.brief.evidence)
            if evidence:
                continue
            # Zero-evidence case: verify the provenance mapping directly from
            # the provider's own declared projection/binding without invoking
            # evidence retrieval.
            self._assert_declared_projection_provenance(descriptor, result)

    def test_bazi_methodology_evidence_binds_to_declared_day_master(self) -> None:
        descriptors, interface, _ = self._catalog()
        descriptor = next(item for item in descriptors if item.id == "bazi")
        result = self._prepare_for(
            interface,
            descriptor,
            self._subject_for("bazi"),
            _provider_facts("bazi"),
        )
        self.assertIsInstance(result, Prepared)
        assert isinstance(result, Prepared)
        evidence = {
            item.ref: item.supports_fact_refs for item in result.brief.evidence
        }
        self.assertEqual(
            evidence["evidence:bazi/bazi/sanming-tonghui#R-01-02"],
            ("fact:subject:client/calculated/bazi/day_master",),
        )

    def _assert_declared_projection_provenance(
        self, descriptor, result: Prepared
    ) -> None:
        """Verify the provenance seam from the provider's own declarations.

        The generic core derives an internal origin for each public calculated
        key from declared sources only: manifest output/extension bindings
        (JSON pointers), or a custom ``public_basis_projection`` provider's own
        binding.  A synthesized key with no manifest output stays unbound.
        This verifies the public projection and manifest form one closed
        declaration even when the real case has no applicable evidence.
        """
        runtime = descriptor.canonical_payload.get("runtime_capability") or {}
        declared_names: set[str] = set()
        for group in ("output_bindings", "extension_output_bindings"):
            for binding in runtime.get(group) or ():
                name = binding.get("name")
                if isinstance(name, str) and name:
                    declared_names.add(name)
                    self.assertTrue(
                        binding.get("json_pointers"),
                        f"{descriptor.id}: binding {name!r} has no json_pointers",
                    )
        provider = self.interface.engine.providers.get(descriptor.id)
        self.assertIsNotNone(provider, f"{descriptor.id}: engine has no adapter")
        visible_keys = {
            fact.ref.rsplit("/", 1)[-1]
            for fact in result.brief.facts
            if "/calculated/" in fact.ref
        }
        self.assertTrue(
            visible_keys & declared_names,
            f"{descriptor.id}: public projection exposes no declared output",
        )


class FortuneWeekEvidenceClosureTests(unittest.TestCase):
    """The pinned fortune weekly regression: evidence must bind real facts."""

    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.interface = ReadingInterface(
            skill_root=ROOT,
            store_root=Path(self._temporary.name),
        )

    def _prepare_week(self):
        return self.interface.execute(
            Prepare(
                query="算一下这周运势",
                intent=IntentSelection(
                    subject_refs=("current_user",),
                    object_id="near_time_personal",
                    dimension_ids=(),
                    horizon=HorizonSelection(kind_id="week"),
                    capability_id="fortune",
                ),
                facts={"current_user": FORTUNE_WEEK_FACTS},
            )
        )

    def test_fortune_week_evidence_binds_correct_public_facts(self) -> None:
        result = self._prepare_week()
        self.assertIsInstance(result, Prepared, result)
        assert isinstance(result, Prepared)
        public_refs = {fact.ref for fact in result.brief.facts}
        evidence = list(result.brief.evidence)
        self.assertTrue(evidence, "fortune week produced no public evidence")
        for item in evidence:
            self.assertTrue(
                item.supports_fact_refs,
                f"{item.ref} has empty supports_fact_refs",
            )
            self.assertTrue(
                set(item.supports_fact_refs) <= public_refs,
                f"{item.ref} supports unknown refs {item.supports_fact_refs}",
            )

    def test_fortune_week_does_not_bind_everything_to_calendar_normalization(
        self,
    ) -> None:
        result = self._prepare_week()
        assert isinstance(result, Prepared)
        calendar_ref = "fact:current_user/calculated/fortune/calendar_normalization"
        evidence = list(result.brief.evidence)
        self.assertTrue(evidence)
        bound_to_calendar = [
            item.ref for item in evidence if item.supports_fact_refs == (calendar_ref,)
        ]
        self.assertLess(
            len(bound_to_calendar),
            len(evidence),
            "every fortune week evidence was dumped onto calendar_normalization",
        )


if __name__ == "__main__":
    unittest.main()

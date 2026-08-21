"""Conversation-facing contract: structured follow-up without a resume API."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

from reading_engine.catalog import CatalogLoader
from reading_engine.interface import ReadingInterface
from reading_engine.interface_contracts import (
    Describe,
    HorizonSelection,
    InputFieldView,
    InputRequest,
    InputRequirement,
    IntentSelection,
    Prepare,
    Prepared,
    RequestView,
    Stopped,
    result_from_dict,
)
from reading_engine.provider_protocol import ProviderNeedInput
from reading_engine.runtime_context import RuntimeContext
from test_reading_engine_v2 import StaticProvider, build_engine


ROOT = Path(__file__).resolve().parents[1]


def _intent() -> IntentSelection:
    return IntentSelection(
        subject_refs=("subject:test",),
        object_id="concrete_event",
        dimension_ids=("outcome",),
        horizon=HorizonSelection(kind_id="instant"),
        capability_id="liuren",
    )


def _interface(root: Path, provider: StaticProvider | None = None) -> ReadingInterface:
    return ReadingInterface(
        skill_root=ROOT,
        engine=build_engine(root, provider or StaticProvider()),
    )


class AlternativeInputProvider(StaticProvider):
    """Fixture that proves an any-of group survives the deep-module seam."""

    def prepare(self, request, context):  # type: ignore[no-untyped-def]
        del request, context
        return ProviderNeedInput(
            missing_input_groups=(
                (
                    "event_datetime_or_reference_datetime",
                    "timezone",
                ),
            )
        )


class StructuredNeedInputContractTests(unittest.TestCase):
    def test_input_request_round_trips_with_manifest_field_views(self) -> None:
        request = InputRequest(
            requirements=(
                InputRequirement(
                    any_of=(
                        InputFieldView(
                            id="input.alpha",
                            label="字段甲",
                            type_id="string",
                            description="说明甲",
                        ),
                        InputFieldView(
                            id="input.beta",
                            label="字段乙",
                            type_id="datetime",
                            description=None,
                        ),
                    )
                ),
            )
        )
        stopped = Stopped(
            reason="need_input",
            public_copy="请补充资料。",
            state_token="opaque-token",
            input_request=request,
        )
        self.assertEqual(result_from_dict(stopped.to_dict()), stopped)

    def test_need_input_exposes_field_schema_and_preserves_token(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            interface = _interface(Path(temporary))
            result = interface.execute(
                Prepare(query="请看一下", intent=_intent(), facts={})
            )

        self.assertIsInstance(result, Stopped, result)
        self.assertEqual(result.reason, "need_input")
        self.assertTrue(result.public_copy.strip())
        self.assertTrue(result.state_token)
        self.assertIsNotNone(result.input_request)
        assert result.input_request is not None
        field_ids = {
            view.id
            for requirement in result.input_request.requirements
            for view in requirement.any_of
        }
        self.assertEqual(
            field_ids,
            {"event_datetime_or_reference_datetime", "timezone"},
        )
        self.assertTrue(
            all(
                view.label.strip()
                for requirement in result.input_request.requirements
                for view in requirement.any_of
            )
        )
        self.assertNotIn("event_datetime", result.public_copy)

    def test_alternative_requirement_is_not_flattened_to_a_sentence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            interface = _interface(
                Path(temporary), AlternativeInputProvider()
            )
            result = interface.execute(
                Prepare(query="请看一下", intent=_intent(), facts={})
            )

        self.assertIsInstance(result, Stopped, result)
        self.assertIsNotNone(result.input_request)
        assert result.input_request is not None
        self.assertEqual(len(result.input_request.requirements), 1)
        self.assertEqual(
            tuple(
                field.id
                for field in result.input_request.requirements[0].any_of
            ),
            ("event_datetime_or_reference_datetime", "timezone"),
        )

    def test_same_token_completes_after_structured_follow_up(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            interface = _interface(Path(temporary))
            pending = interface.execute(
                Prepare(query="请看一下", intent=_intent(), facts={})
            )
            self.assertIsInstance(pending, Stopped, pending)
            self.assertEqual(pending.reason, "need_input")
            self.assertTrue(pending.state_token)
            resumed = interface.execute(
                Prepare(
                    query="请看一下",
                    intent=_intent(),
                    facts={
                        "subject:test": {
                            "event_datetime_or_reference_datetime": (
                                "2026-07-30T13:00:00+08:00"
                            ),
                            "timezone": "Asia/Shanghai",
                        }
                    },
                    state_token=pending.state_token,
                )
            )

        self.assertIsInstance(resumed, Prepared, resumed)

    def test_prepared_brief_exposes_only_the_structured_requested_scope(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            interface = _interface(Path(temporary))
            result = interface.execute(
                Prepare(
                    query="请看一下",
                    intent=_intent(),
                    facts={
                        "subject:test": {
                            "event_datetime_or_reference_datetime": (
                                "2026-07-30T13:00:00+08:00"
                            ),
                            "timezone": "Asia/Shanghai",
                        }
                    },
                )
            )

        self.assertIsInstance(result, Prepared, result)
        self.assertEqual(
            result.brief.request_view,
            RequestView(
                subject_refs=("subject:test",),
                capability_ids=("liuren",),
                object_id="concrete_event",
                dimension_ids=("outcome",),
                horizon=HorizonSelection(kind_id="instant"),
            ),
        )


class CompactPreparedViewTests(unittest.TestCase):
    def test_invalid_optional_finding_declaration_does_not_block_prepare(self) -> None:
        """A stale display projection must not discard deterministic facts."""

        catalog = CatalogLoader(ROOT / "resources/runtime").load()
        original = catalog.descriptor("liuren")
        payload = copy.deepcopy(dict(original.canonical_payload))
        runtime = payload["runtime_capability"]
        runtime["finding_bindings"] = [{"id": "broken"}]
        replacement = replace(original, canonical_payload=payload)
        altered_catalog = replace(
            catalog,
            descriptors=tuple(
                replacement if item.id == replacement.id else item
                for item in catalog.descriptors
            ),
        )

        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch(
                "reading_engine.factory.CatalogLoader.load",
                return_value=altered_catalog,
            ):
                interface = ReadingInterface(
                    skill_root=ROOT,
                    store_root=Path(temporary),
                    catalog=altered_catalog,
                )
                result = interface.execute(
                    Prepare(
                        query="请看一下",
                        intent=_intent(),
                        facts={
                            "subject:test": {
                                "event_datetime_or_reference_datetime": (
                                    "2026-07-30T13:00:00+08:00"
                                ),
                                "timezone": "Asia/Shanghai",
                            }
                        },
                    )
                )

        self.assertIsInstance(result, Prepared, result)
        self.assertFalse(result.brief.findings)

    def test_weekly_view_uses_compact_provider_markers_not_full_private_layers(
        self,
    ) -> None:
        context = RuntimeContext(
            now_iso="2026-07-29T10:00:00+08:00",
            default_timezone_name="Asia/Shanghai",
            subject_profiles={
                "current_user": {
                    "birth_datetime": "1994-04-30T05:55:00",
                    "timezone": "Asia/Shanghai",
                    "location": "福建省福州市",
                    "gender": "female",
                }
            },
        )
        with tempfile.TemporaryDirectory() as temporary:
            interface = ReadingInterface(
                skill_root=ROOT,
                store_root=Path(temporary),
                runtime_context=context,
            )
            result = interface.execute(
                Prepare(
                    query="算一下这周运势",
                    intent=IntentSelection(
                        subject_refs=("current_user",),
                        object_id="near_time_personal",
                        dimension_ids=(),
                        horizon=HorizonSelection(
                            kind_id="week",
                            start="2026-07-27",
                            end="2026-08-02",
                        ),
                        capability_id="fortune",
                    ),
                    facts={},
                )
            )

        self.assertIsInstance(result, Prepared, result)
        rendered = json.dumps(result.brief.to_dict(), ensure_ascii=False)
        self.assertLess(len(rendered), 40_000)
        by_suffix = {
            fact.ref.rsplit("/", 1)[-1]: fact for fact in result.brief.facts
        }
        self.assertIn("period_markers", by_suffix)
        self.assertNotIn("target_period_facts", by_suffix)
        markers = by_suffix["period_markers"].value
        self.assertIsInstance(markers, list)
        self.assertEqual(len(markers), 7)
        self.assertTrue(all("date" in marker for marker in markers))
        marker_findings = [
            finding
            for finding in result.brief.findings
            if finding.kind_id == "finding.period_markers"
        ]
        self.assertEqual(len(marker_findings), 1)
        finding = marker_findings[0]
        self.assertEqual(finding.data, markers)
        self.assertEqual(finding.dimension_ids, result.brief.request_view.dimension_ids)
        self.assertEqual(finding.support_mode, "exact")
        self.assertEqual(
            set(finding.fact_refs),
            {"fact:current_user/calculated/fortune/period_markers"},
        )
        self.assertFalse(finding.evidence_refs)
        self.assertTrue(all("unresolved_boundaries" in marker for marker in markers))


class StructuredMethodChoiceTests(unittest.TestCase):
    def test_describe_exposes_provider_owned_method_choices(self) -> None:
        interface = ReadingInterface(skill_root=ROOT)
        described = interface.execute(Describe())
        self.assertEqual(result_from_dict(described.to_dict()), described)
        method = next(
            field
            for capability in described.capabilities
            if capability.id == "meihua"
            for field in capability.input_fields
            if field.id == "casting_method"
        )
        self.assertEqual(
            tuple(choice.id for choice in method.choices),
            (
                "time",
                "supplied_number",
                "sound_count",
                "observation",
                "supplied_hexagram",
            ),
        )
        self.assertTrue(all(choice.label.strip() for choice in method.choices))

    def test_known_unsupported_method_stops_without_replacing_it(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            interface = ReadingInterface(
                skill_root=ROOT,
                store_root=Path(temporary),
            )
            result = interface.execute(
                Prepare(
                    query="按时间起",
                    intent=IntentSelection(
                        subject_refs=("subject:test",),
                        object_id="concrete_event",
                        dimension_ids=("outcome",),
                        horizon=HorizonSelection(kind_id="instant"),
                        capability_id="liuyao",
                    ),
                    facts={
                        "subject:test": {
                            "cast": "time",
                            "event_datetime": "2026-07-30T12:00:00+08:00",
                            "timezone": "Asia/Shanghai",
                            "location": "上海",
                        }
                    },
                )
            )

        self.assertIsInstance(result, Stopped, result)
        self.assertEqual(result.reason, "unsupported")
        self.assertTrue(result.public_copy.strip())
        self.assertIsNone(result.state_token)

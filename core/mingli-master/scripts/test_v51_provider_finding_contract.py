"""Provider-owned finding and boundary projections in the portable brief."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from reading_engine.interface import ReadingInterface
from reading_engine.interface_contracts import (
    HorizonSelection,
    IntentSelection,
    Prepare,
    Prepared,
)


ROOT = Path(__file__).resolve().parents[1]


class ProviderFindingContractTests(unittest.TestCase):
    def test_supporting_evidence_does_not_publish_a_false_zero_source_limit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            interface = ReadingInterface(
                skill_root=ROOT,
                store_root=Path(temporary),
            )
            result = interface.execute(
                Prepare(
                    query="这件事能不能推进？",
                    intent=IntentSelection(
                        subject_refs=("subject:test",),
                        object_id="concrete_event",
                        dimension_ids=("outcome",),
                        horizon=HorizonSelection(kind_id="instant"),
                        capability_id="liuren",
                    ),
                    facts={
                        "subject:test": {
                            "event_datetime_or_reference_datetime": (
                                "2026-07-30T12:00:00+08:00"
                            ),
                            "timezone": "Asia/Shanghai",
                        }
                    },
                )
            )

        self.assertIsInstance(result, Prepared, result)
        self.assertTrue(result.brief.evidence, result.brief.to_dict())
        self.assertNotIn(
            "limit.source_gap",
            {limit.kind_id for limit in result.brief.limits},
            result.brief.to_dict(),
        )

    def test_unbounded_timing_is_explicit_material_not_a_fake_date(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            interface = ReadingInterface(
                skill_root=ROOT,
                store_root=Path(temporary),
            )
            result = interface.execute(
                Prepare(
                    query="什么时候能搬进去？",
                    intent=IntentSelection(
                        subject_refs=("subject:test",),
                        object_id="concrete_event",
                        dimension_ids=("timing",),
                        horizon=HorizonSelection(kind_id="instant"),
                        capability_id="liuren",
                    ),
                    facts={
                        "subject:test": {
                            "event_datetime_or_reference_datetime": (
                                "2026-07-30T12:00:00+08:00"
                            ),
                            "timezone": "Asia/Shanghai",
                        }
                    },
                )
            )

        self.assertIsInstance(result, Prepared, result)
        timing = next(
            finding
            for finding in result.brief.findings
            if finding.kind_id == "finding.timing_candidates"
        )
        self.assertEqual(timing.data["status"], "unbounded_horizon_no_exact_date")
        self.assertEqual(timing.data["candidates"], [])
        self.assertIn("limit.horizon_boundary", {
            limit.kind_id for limit in result.brief.limits
        })

    def test_time_based_method_stays_deterministic_where_declared(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            interface = ReadingInterface(
                skill_root=ROOT,
                store_root=Path(temporary),
            )
            result = interface.execute(
                Prepare(
                    query="按时间起卦看这件事",
                    intent=IntentSelection(
                        subject_refs=("subject:test",),
                        object_id="concrete_event",
                        dimension_ids=("outcome",),
                        horizon=HorizonSelection(kind_id="instant"),
                        capability_id="meihua",
                    ),
                    facts={
                        "subject:test": {
                            "casting_method": "time",
                            "event_datetime": "2026-07-30T12:00:00+08:00",
                            "timezone": "Asia/Shanghai",
                            "location": "上海",
                        }
                    },
                )
            )

        self.assertIsInstance(result, Prepared, result)
        body_use = next(
            finding
            for finding in result.brief.findings
            if finding.kind_id == "finding.body_use"
        )
        self.assertEqual(
            body_use.data["status"], "calculated_relation_not_verdict"
        )

    def test_bazi_salience_signals_reach_the_brief_through_existing_findings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            interface = ReadingInterface(
                skill_root=ROOT,
                store_root=Path(temporary),
            )
            result = interface.execute(
                Prepare(
                    query="整体看看这个八字的大方向",
                    intent=IntentSelection(
                        subject_refs=("subject:test",),
                        object_id="natal",
                        dimension_ids=(),
                        horizon=HorizonSelection(kind_id="year"),
                        capability_id="bazi",
                    ),
                    facts={
                        "subject:test": {
                            "birth_datetime_or_four_pillars": [
                                "乙酉",
                                "辛巳",
                                "丙午",
                                "癸巳",
                            ],
                            "gender": "male",
                        }
                    },
                )
            )

        self.assertIsInstance(result, Prepared, result)
        candidates = next(
            finding
            for finding in result.brief.findings
            if finding.kind_id == "finding.interpretive_candidates"
        )
        signals = candidates.data["salience_signals"]
        self.assertTrue(signals)
        for item in signals:
            self.assertEqual(item["status"], "mechanical_candidate")
            self.assertIsNone(item["hard_verdict"])
            self.assertTrue(item["basis"])
        fact_refs = {fact.ref for fact in result.brief.facts}
        evidence_refs = {item.ref for item in result.brief.evidence}
        limit_kind_ids = {limit.kind_id for limit in result.brief.limits}
        self.assertTrue(set(candidates.fact_refs) <= fact_refs)
        self.assertTrue(set(candidates.evidence_refs) <= evidence_refs)
        self.assertTrue(set(candidates.limit_kind_ids) <= limit_kind_ids)
        luck_fact = next(
            fact
            for fact in result.brief.facts
            if fact.ref.endswith("/calculated/bazi/luck_cycles")
        )
        self.assertEqual(luck_fact.value["status"], "sequence_only")
        self.assertEqual(
            set(result.brief.to_dict()),
            {
                "question",
                "vocabulary",
                "facts",
                "evidence",
                "findings",
                "claim_scopes",
                "limits",
                "prior_answer",
                "request_view",
            },
        )

    def test_partial_luck_boundaries_reach_prepared_limits(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            interface = ReadingInterface(
                skill_root=ROOT,
                store_root=Path(temporary),
            )
            result = interface.execute(
                Prepare(
                    query="整体看看这个八字的大方向",
                    intent=IntentSelection(
                        subject_refs=("subject:test",),
                        object_id="natal",
                        dimension_ids=("state",),
                        horizon=HorizonSelection(kind_id="year"),
                        capability_id="bazi",
                    ),
                    facts={
                        "subject:test": {
                            "birth_datetime_or_four_pillars": [
                                "乙酉",
                                "辛巳",
                                "丙午",
                                "癸巳",
                            ],
                            "gender": "male",
                        }
                    },
                )
            )

        self.assertIsInstance(result, Prepared, result)
        timing_limits = [
            limit
            for limit in result.brief.limits
            if limit.kind_id == "limit.partial_luck_timing"
        ]
        self.assertEqual(len(timing_limits), 1, result.brief.to_dict())
        self.assertEqual(
            set(timing_limits[0].detail_ids),
            {
                "start_age",
                "calendar_year_mapping",
                "active_cycle",
                "precise_timing",
            },
        )
        self.assertTrue(timing_limits[0].public_text.strip())
        self.assertNotEqual(
            timing_limits[0].public_text, "limit.partial_luck_timing"
        )
        vocabulary_ids = {term.id for term in result.brief.vocabulary}
        self.assertIn("limit.partial_luck_timing", vocabulary_ids)

    def test_genderless_partial_luck_declares_its_boundary_limit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            interface = ReadingInterface(
                skill_root=ROOT,
                store_root=Path(temporary),
            )
            result = interface.execute(
                Prepare(
                    query="整体看看这个八字的大方向",
                    intent=IntentSelection(
                        subject_refs=("subject:test",),
                        object_id="natal",
                        dimension_ids=("state",),
                        horizon=HorizonSelection(kind_id="year"),
                        capability_id="bazi",
                    ),
                    facts={
                        "subject:test": {
                            "birth_datetime_or_four_pillars": [
                                "乙酉",
                                "辛巳",
                                "丙午",
                                "癸巳",
                            ]
                        }
                    },
                )
            )

        self.assertIsInstance(result, Prepared, result)
        kinds = {limit.kind_id for limit in result.brief.limits}
        self.assertIn("limit.partial_luck_no_gender", kinds, result.brief.to_dict())
        self.assertNotIn("limit.partial_luck_timing", kinds)

    def test_full_birth_brief_carries_no_partial_luck_limit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            interface = ReadingInterface(
                skill_root=ROOT,
                store_root=Path(temporary),
            )
            result = interface.execute(
                Prepare(
                    query="看一下这个八字",
                    intent=IntentSelection(
                        subject_refs=("subject:client",),
                        object_id="natal",
                        dimension_ids=("career",),
                        horizon=HorizonSelection(kind_id="year"),
                        capability_id="bazi",
                    ),
                    facts={
                        "subject:client": {
                            "birth_datetime_or_four_pillars": "1994-04-30T05:55:00",
                            "timezone": "Asia/Shanghai",
                            "location": "福建省福州市",
                            "gender": "female",
                            "time_basis_policy": "civil",
                        }
                    },
                )
            )

        self.assertIsInstance(result, Prepared, result)
        kinds = {limit.kind_id for limit in result.brief.limits}
        self.assertNotIn("limit.partial_luck_timing", kinds)
        self.assertNotIn("limit.partial_luck_no_gender", kinds)

    def test_broad_overview_stays_a_single_overview_dimension(self) -> None:
        seven_defaults = {
            "career",
            "health",
            "location",
            "outcome",
            "relationship",
            "state",
            "timing",
        }
        with tempfile.TemporaryDirectory() as temporary:
            interface = ReadingInterface(
                skill_root=ROOT,
                store_root=Path(temporary),
            )
            result = interface.execute(
                Prepare(
                    query="只有四柱和性别，帮我整体看看这个八字的大方向。",
                    intent=IntentSelection(
                        subject_refs=("subject:test",),
                        object_id="natal",
                        dimension_ids=("overview",),
                        horizon=HorizonSelection(kind_id="year"),
                        capability_id="bazi",
                    ),
                    facts={
                        "subject:test": {
                            "birth_datetime_or_four_pillars": [
                                "乙酉",
                                "辛巳",
                                "丙午",
                                "癸巳",
                            ],
                            "gender": "male",
                        }
                    },
                )
            )

        self.assertIsInstance(result, Prepared, result)
        assert result.brief.request_view is not None
        self.assertEqual(
            tuple(result.brief.request_view.dimension_ids), ("overview",)
        )
        scoped = {scope.dimension_id for scope in result.brief.claim_scopes}
        self.assertEqual(scoped, {"overview"}, result.brief.to_dict())
        self.assertFalse(scoped & seven_defaults)
        finding_dimensions = {
            dimension
            for finding in result.brief.findings
            for dimension in finding.dimension_ids
        }
        self.assertEqual(finding_dimensions, {"overview"})
        vocabulary = {
            term.id: term for term in result.brief.vocabulary
        }
        self.assertIn("overview", vocabulary)
        self.assertTrue(vocabulary["overview"].label.strip())
        self.assertNotEqual(vocabulary["overview"].label, "overview")


if __name__ == "__main__":
    unittest.main()

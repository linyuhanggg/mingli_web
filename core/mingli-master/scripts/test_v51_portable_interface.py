"""Behavioral contract for the portable describe/prepare/complete interface."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from reading_engine.interface_contracts import (
    Accepted,
    CapabilityView,
    ClaimScope,
    Complete,
    ComparisonSelection,
    Describe,
    Described,
    HorizonSelection,
    InputFieldView,
    IntentSelection,
    Prepare,
    Prepared,
    PublicEvidence,
    PublicFact,
    PublicFinding,
    PublicLimit,
    PublicTerm,
    ReadingBrief,
    RuntimeFailure,
    Stopped,
    command_from_dict,
    result_from_dict,
    runtime_failure,
)

ROOT = Path(__file__).resolve().parents[1]


def _term(suffix: str) -> PublicTerm:
    return PublicTerm(
        id=f"term.{suffix}",
        label=f"label {suffix}",
        description=f"description {suffix}",
    )


def _brief() -> ReadingBrief:
    return ReadingBrief(
        question="example question",
        vocabulary=(_term("one"), _term("two")),
        facts=(
            PublicFact(
                ref="fact.one",
                subject_ref="subject.self",
                kind_id="kind.one",
                value={"nested": ["a", 1]},
                display_text="fact one text",
            ),
        ),
        evidence=(
            PublicEvidence(
                ref="evidence.one",
                source_title="source title",
                locator="section 1",
                excerpt="excerpt text",
                supports_fact_refs=("fact.one",),
            ),
        ),
        claim_scopes=(
            ClaimScope(
                subject_ref="subject.self",
                dimension_id="dimension.one",
                allowed_kind_ids=("kind.one",),
                certainty_ceiling_id="certainty.low",
                fact_refs=("fact.one",),
                evidence_refs=("evidence.one",),
            ),
        ),
        limits=(
            PublicLimit(
                kind_id="limit.one",
                public_text="limit text",
                scope_refs=("fact.one",),
            ),
        ),
        findings=(
            PublicFinding(
                ref="finding.one",
                subject_ref="subject.self",
                dimension_ids=("dimension.one",),
                kind_id="finding.one",
                data={"candidate": "value"},
                fact_refs=("fact.one",),
                evidence_refs=("evidence.one",),
                limit_kind_ids=("limit.one",),
            ),
        ),
        prior_answer="prior answer text",
    )


def _capability_view() -> CapabilityView:
    return CapabilityView(
        id="capability.alpha",
        label="capability label",
        description="capability description",
        objects=(_term("object"),),
        horizons=(_term("horizon"),),
        dimensions=(_term("dimension"),),
        default_dimension_ids=("term.dimension",),
        input_fields=(
            InputFieldView(
                id="input.one",
                label="input label",
                type_id="string",
                description="input description",
            ),
        ),
        required_input_groups=(("input.one",),),
    )


class PortableInterfaceTests(unittest.TestCase):
    def all_terminal_results(self) -> tuple[object, ...]:
        return (
            Accepted(state_token="token-accept", public_copy="final answer"),
            Stopped(reason="need_input", public_copy="missing data question"),
            Stopped(reason="unsupported", public_copy="unsupported reason"),
            Stopped(
                reason="conflict",
                public_copy="conflict explanation",
                state_token="token-conflict",
            ),
            Stopped(reason="error", public_copy="safe failure text"),
        )

    def describe_prepare_complete_examples(self) -> tuple[object, ...]:
        return (
            Describe(),
            Prepare(
                query="broad question",
                intent=IntentSelection(
                    subject_refs=("subject.self",),
                    object_id="object.one",
                    dimension_ids=(),
                    horizon=HorizonSelection(kind_id="horizon.one"),
                ),
                facts={"subject.self": {"input.one": "value"}},
            ),
            Prepare(
                query="follow-up question",
                intent=IntentSelection(
                    subject_refs=("subject.self", "subject.other"),
                    object_id="object.one",
                    dimension_ids=("dimension.one",),
                    horizon=HorizonSelection(
                        kind_id="horizon.range",
                        start="2026-07-01",
                        end="2026-07-07",
                    ),
                    capability_id="capability.alpha",
                    comparisons=(
                        ComparisonSelection(
                            capability_id="capability.beta",
                            requirement="required",
                        ),
                    ),
                ),
                facts={
                    "subject.self": {"input.one": "value"},
                    "subject.other": {"input.two": 3},
                },
                state_token="token-prior",
                transition="correct",
            ),
            Complete(state_token="token-prepared", public_copy="drafted answer"),
        )

    def all_results(self) -> tuple[object, ...]:
        return (
            Described(
                protocol_version="v51-portable-1",
                manifest_digest="digest-value",
                capabilities=(_capability_view(),),
            ),
            Prepared(state_token="token-prepared", brief=_brief()),
        ) + self.all_terminal_results()

    def test_terminal_results_are_never_empty(self) -> None:
        for result in self.all_terminal_results():
            self.assertTrue(result.public_copy.strip())

    def test_terminal_results_reject_blank_public_copy(self) -> None:
        with self.assertRaises(ValueError):
            Accepted(state_token="token", public_copy="   ")
        with self.assertRaises(ValueError):
            Stopped(reason="error", public_copy="")

    def test_stopped_rejects_unknown_reason(self) -> None:
        with self.assertRaises(ValueError):
            Stopped(reason="not-a-reason", public_copy="text")

    def test_stopped_error_has_a_versioned_pii_free_failure(self) -> None:
        result = Stopped(reason="error", public_copy="safe failure text")

        self.assertEqual(
            result.failure,
            RuntimeFailure(
                schema_version="mingli-runtime-failure/v1",
                code="runtime.internal_error",
                category="runtime_internal",
                retryable=False,
            ),
        )
        assert result.failure is not None
        self.assertEqual(
            set(result.failure.to_dict()),
            {"schema_version", "code", "category", "retryable"},
        )

    def test_failure_code_registry_is_closed_and_reason_scoped(self) -> None:
        with self.assertRaises(ValueError):
            runtime_failure("runtime.user-submitted-value")
        with self.assertRaises(ValueError):
            RuntimeFailure(
                code="transient.timeout",
                category="runtime_internal",
                retryable=False,
            )
        with self.assertRaises(ValueError):
            Stopped(
                reason="unsupported",
                public_copy="unsupported",
                failure=runtime_failure("runtime.internal_error"),
            )

    def test_failure_decoder_rejects_extra_diagnostic_fields(self) -> None:
        payload = Stopped(
            reason="error",
            public_copy="safe failure text",
        ).to_dict()
        assert isinstance(payload["failure"], dict)
        payload["failure"]["exception"] = "private path or caller data"

        with self.assertRaises(ValueError):
            result_from_dict(payload)

    def test_each_public_command_round_trips(self) -> None:
        for command in self.describe_prepare_complete_examples():
            self.assertEqual(command_from_dict(command.to_dict()), command)

    def test_each_result_round_trips(self) -> None:
        for result in self.all_results():
            self.assertEqual(result_from_dict(result.to_dict()), result)

    def test_commands_and_results_are_immutable(self) -> None:
        describe = Describe()
        with self.assertRaises(Exception):
            describe.kind = "other"  # type: ignore[misc]
        accepted = Accepted(state_token="token", public_copy="text")
        with self.assertRaises(Exception):
            accepted.public_copy = "rewritten"  # type: ignore[misc]

    def test_contracts_do_not_import_providers_or_transaction(self) -> None:
        import subprocess
        import sys

        probe = (
            "import sys;"
            "import reading_engine.interface_contracts;"
            "banned = ['reading_engine.factory', 'reading_engine.transaction',"
            " 'reading_engine.providers'];"
            "loaded = [name for name in banned if name in sys.modules];"
            "print(','.join(loaded))"
        )
        completed = subprocess.run(
            [sys.executable, "-B", "-c", probe],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            env={"PYTHONPATH": str(ROOT / "scripts"), "PATH": "/usr/bin:/bin"},
            check=True,
        )
        self.assertEqual(completed.stdout.strip(), "")


class DescribeExecutionTests(unittest.TestCase):
    """`describe` is a cacheable capability snapshot of the loaded artifact."""

    @classmethod
    def setUpClass(cls) -> None:
        from reading_engine.interface import ReadingInterface

        cls.interface = ReadingInterface(skill_root=ROOT)

    def test_describe_returns_manifest_backed_capabilities(self) -> None:
        from reading_engine.catalog import CatalogLoader

        result = self.interface.execute(Describe())
        self.assertIsInstance(result, Described)
        catalog = CatalogLoader(ROOT / "resources/runtime").load()
        self.assertEqual(result.manifest_digest, catalog.manifest_digest)
        self.assertEqual(
            {view.id for view in result.capabilities},
            {descriptor.id for descriptor in catalog.descriptors},
        )
        for view in result.capabilities:
            with self.subTest(capability=view.id):
                self.assertTrue(view.label.strip())
                self.assertTrue(view.description.strip())
                self.assertTrue(view.dimensions)
                self.assertTrue(view.default_dimension_ids)
                self.assertTrue(
                    set(view.default_dimension_ids)
                    <= {term.id for term in view.dimensions}
                )

    def test_describe_is_self_describing_for_every_declared_id(self) -> None:
        result = self.interface.execute(Describe())
        for view in result.capabilities:
            declared = {term.id for term in view.objects}
            declared |= {term.id for term in view.horizons}
            declared |= {term.id for term in view.dimensions}
            for term in (*view.objects, *view.horizons, *view.dimensions):
                self.assertTrue(term.label.strip(), term.id)
            for field in view.input_fields:
                self.assertTrue(field.label.strip(), field.id)
            for group in view.required_input_groups:
                self.assertTrue(
                    set(group) <= {field.id for field in view.input_fields}
                )

    def test_describe_never_leaks_entrypoints_or_paths(self) -> None:
        result = self.interface.execute(Describe())
        rendered = json.dumps(result.to_dict(), ensure_ascii=False)
        for private in ("entrypoint", "reading_engine.", "scripts/", "/Users/"):
            self.assertNotIn(private, rendered)

    def test_describe_is_stable_for_one_loaded_module(self) -> None:
        first = self.interface.execute(Describe())
        second = self.interface.execute(Describe())
        self.assertEqual(first.to_dict(), second.to_dict())

    def test_unknown_command_object_stops_with_public_text(self) -> None:
        result = self.interface.execute(object())  # type: ignore[arg-type]
        self.assertIsInstance(result, Stopped)
        self.assertEqual(result.reason, "error")
        self.assertTrue(result.public_copy.strip())



class ProductionFlowTests(unittest.TestCase):
    """The one production chain: adapters -> preparation -> brief -> commit."""

    def _interface(self, **context_values):
        import tempfile

        from reading_engine.interface import ReadingInterface
        from reading_engine.runtime_context import build_runtime_context

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return ReadingInterface(
            skill_root=ROOT,
            store_root=Path(tmp.name),
            runtime_context=build_runtime_context(**context_values),
        )

    @staticmethod
    def _default_profile() -> dict:
        return {
            "birth_datetime": "1994-04-30T05:55:00",
            "timezone": "Asia/Shanghai",
            "location": "福建省福州市",
            "gender": "female",
        }

    def test_broad_weekly_question_prepares_with_default_dimensions(self) -> None:
        interface = self._interface(
            now_iso="2026-07-29T10:00:00+08:00",
            default_timezone_name="Asia/Shanghai",
            subject_profiles={"current_user": self._default_profile()},
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
        token = interface.engine.token_store.resolve(result.state_token)
        self.assertIsNotNone(token)
        staged = interface.engine.store.load_prepared(token.reading_id)
        self.assertEqual(
            {(item.subject_ref, item.capability_id) for item in staged.artifacts},
            {("current_user", "fortune")},
        )
        scope_dimensions = {
            scope.dimension_id for scope in result.brief.claim_scopes
        }
        self.assertTrue(scope_dimensions)
        calculated = [
            fact
            for fact in result.brief.facts
            if fact.ref.startswith("fact:current_user/calculated/")
        ]
        self.assertTrue(calculated, result.brief.to_dict())
        periods = [
            fact.value
            for fact in calculated
            if fact.ref.endswith("/available_periods")
        ]
        self.assertEqual(
            periods,
            [[
                "2026-07-27",
                "2026-07-28",
                "2026-07-29",
                "2026-07-30",
                "2026-07-31",
                "2026-08-01",
                "2026-08-02",
            ]],
        )
        findings = [
            finding
            for finding in result.brief.findings
            if finding.kind_id == "finding.period_markers"
        ]
        self.assertEqual(len(findings), 1)
        self.assertEqual(len(findings[0].data), 7)

    def test_default_week_publishes_its_effective_calculated_range(self) -> None:
        interface = self._interface(
            now_iso="2026-07-29T10:00:00+08:00",
            default_timezone_name="Asia/Shanghai",
            subject_profiles={"current_user": self._default_profile()},
        )
        result = interface.execute(
            Prepare(
                query="算一下这周运势",
                intent=IntentSelection(
                    subject_refs=("current_user",),
                    object_id="near_time_personal",
                    dimension_ids=(),
                    horizon=HorizonSelection(kind_id="week"),
                    capability_id="fortune",
                ),
                facts={},
            )
        )

        self.assertIsInstance(result, Prepared, result)
        assert result.brief.request_view is not None
        self.assertEqual(
            result.brief.request_view.horizon,
            HorizonSelection(
                kind_id="week",
                start="2026-07-27",
                end="2026-08-02",
            ),
        )

    def test_full_structured_chart_prepares_with_clean_brief(self) -> None:
        import re as _re

        interface = self._interface(default_timezone_name="Asia/Shanghai")
        result = interface.execute(
            Prepare(
                query="看一下这个八字",
                intent=IntentSelection(
                    subject_refs=("subject:client",),
                    object_id="natal",
                    dimension_ids=(),
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
        rendered = json.dumps(result.brief.to_dict(), ensure_ascii=False)
        self.assertNotIn("chart_facts", rendered)
        self.assertNotIn("fact_extensions", rendered)
        self.assertNotIn("/Users/", rendered)
        self.assertNotIn("prepared_digest", rendered)
        self.assertIsNone(_re.search(r"[0-9a-f]{64}", rendered), rendered[:2000])
        candidates = [
            finding
            for finding in result.brief.findings
            if finding.kind_id == "finding.interpretive_candidates"
        ]
        self.assertEqual(len(candidates), 1)
        candidate_data = candidates[0].data
        self.assertTrue(candidate_data)
        self.assertTrue(
            all(
                row.get("hard_verdict") is None
                for row in candidate_data.values()
                if isinstance(row, dict)
            )
        )

    def test_multi_subjects_each_get_calculated_facts_and_isolated_scopes(self) -> None:
        interface = self._interface(default_timezone_name="Asia/Shanghai")
        result = interface.execute(
            Prepare(
                query="看一下这两个人的八字",
                intent=IntentSelection(
                    subject_refs=("subject:a", "subject:b"),
                    object_id="natal",
                    dimension_ids=(),
                    horizon=HorizonSelection(kind_id="year"),
                    capability_id="bazi",
                ),
                facts={
                    "subject:a": {
                        "birth_datetime_or_four_pillars": "1994-04-30T05:55:00",
                        "timezone": "Asia/Shanghai",
                        "location": "福建省福州市",
                        "gender": "female",
                        "time_basis_policy": "civil",
                    },
                    "subject:b": {
                        "birth_datetime_or_four_pillars": "1992-08-17T14:30:00",
                        "timezone": "Asia/Shanghai",
                        "location": "上海市",
                        "gender": "male",
                        "time_basis_policy": "civil",
                    },
                },
            )
        )
        self.assertIsInstance(result, Prepared, result)
        token = interface.engine.token_store.resolve(result.state_token)
        self.assertIsNotNone(token)
        staged = interface.engine.store.load_prepared(token.reading_id)
        self.assertEqual(
            {(item.subject_ref, item.capability_id) for item in staged.artifacts},
            {("subject:a", "bazi"), ("subject:b", "bazi")},
        )
        rendered = json.dumps(result.brief.to_dict(), ensure_ascii=False)
        self.assertNotIn("other_subjects", rendered)
        for subject_ref in ("subject:a", "subject:b"):
            calculated = [
                fact
                for fact in result.brief.facts
                if fact.subject_ref == subject_ref
                and "/calculated/" in fact.ref
            ]
            self.assertTrue(calculated, subject_ref)
            scopes = [
                scope
                for scope in result.brief.claim_scopes
                if scope.subject_ref == subject_ref
            ]
            self.assertTrue(scopes, subject_ref)
            for scope in scopes:
                self.assertTrue(scope.fact_refs, scope)
                self.assertTrue(
                    all(
                        ref.startswith(f"fact:{subject_ref}/")
                        for ref in scope.fact_refs
                    ),
                    scope,
                )

    def test_dual_system_prepare_then_any_nonempty_complete_is_accepted(self) -> None:
        interface = self._interface(default_timezone_name="Asia/Shanghai")
        prepared = interface.execute(
            Prepare(
                query="用八字和紫微一起看",
                intent=IntentSelection(
                    subject_refs=("subject:client",),
                    object_id="natal",
                    dimension_ids=(),
                    horizon=HorizonSelection(kind_id="year"),
                    capability_id="bazi",
                    comparisons=(
                        ComparisonSelection(
                            capability_id="ziwei",
                            requirement="required",
                        ),
                    ),
                ),
                facts={
                    "subject:client": {
                        "birth_datetime_or_four_pillars": "1994-04-30T05:55:00",
                        "birth_datetime": "1994-04-30T05:55:00",
                        "timezone": "Asia/Shanghai",
                        "location": "福建省福州市",
                        "gender": "female",
                        "time_basis_policy": "civil",
                    }
                },
            )
        )
        self.assertIsInstance(prepared, Prepared, prepared)
        token = interface.engine.token_store.resolve(prepared.state_token)
        self.assertIsNotNone(token)
        staged = interface.engine.store.load_prepared(token.reading_id)
        self.assertEqual(
            {(item.subject_ref, item.capability_id) for item in staged.artifacts},
            {("subject:client", "bazi"), ("subject:client", "ziwei")},
        )
        fact_refs = {fact.ref for fact in prepared.brief.facts}
        self.assertTrue(
            any("/calculated/bazi/" in ref for ref in fact_refs),
            fact_refs,
        )
        self.assertTrue(
            any("/calculated/ziwei/" in ref for ref in fact_refs),
            fact_refs,
        )
        scope_refs = {scope.subject_ref for scope in prepared.brief.claim_scopes}
        self.assertEqual(scope_refs, {"subject:client"})
        copy_text = "两个体系的事实层都取齐之后，先从格局主线讲起，再补充流年侧重点。"
        completed = interface.execute(
            Complete(state_token=prepared.state_token, public_copy=copy_text)
        )
        self.assertIsInstance(completed, Accepted, completed)
        self.assertEqual(completed.public_copy, copy_text)

    def test_complete_replays_are_byte_identical(self) -> None:
        import threading

        interface = self._interface(default_timezone_name="Asia/Shanghai")
        prepared = interface.execute(
            Prepare(
                query="看一下这个八字",
                intent=IntentSelection(
                    subject_refs=("subject:client",),
                    object_id="natal",
                    dimension_ids=(),
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
        self.assertIsInstance(prepared, Prepared, prepared)
        first = interface.execute(
            Complete(state_token=prepared.state_token, public_copy="第一稿正文。")
        )
        self.assertIsInstance(first, Accepted, first)
        replay = interface.execute(
            Complete(state_token=prepared.state_token, public_copy="第二稿正文。")
        )
        self.assertIsInstance(replay, Accepted, replay)
        self.assertEqual(replay.public_copy, first.public_copy)

        results: list = []
        prepared_two = interface.execute(
            Prepare(
                query="换个角度再看这个八字",
                intent=IntentSelection(
                    subject_refs=("subject:client",),
                    object_id="natal",
                    dimension_ids=(),
                    horizon=HorizonSelection(kind_id="year"),
                    capability_id="bazi",
                ),
                facts={
                    "subject:client": {
                        "birth_datetime_or_four_pillars": "1992-08-17T14:30:00",
                        "timezone": "Asia/Shanghai",
                        "location": "上海市",
                        "gender": "male",
                        "time_basis_policy": "civil",
                    }
                },
            )
        )
        self.assertIsInstance(prepared_two, Prepared, prepared_two)

        def _submit(text: str) -> None:
            results.append(
                interface.execute(
                    Complete(
                        state_token=prepared_two.state_token,
                        public_copy=text,
                    )
                )
            )

        threads = [
            threading.Thread(target=_submit, args=(f"并发正文{index}。",))
            for index in range(4)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(len(results), 4)
        for item in results:
            self.assertIsInstance(item, Accepted, item)
        distinct = {item.public_copy for item in results}
        self.assertEqual(len(distinct), 1, distinct)

    def test_real_provider_continuation_keeps_reading_and_advances_version(self) -> None:
        interface = self._interface(default_timezone_name="Asia/Shanghai")
        intent = IntentSelection(
            subject_refs=("subject:client",),
            object_id="natal",
            dimension_ids=(),
            horizon=HorizonSelection(kind_id="year"),
            capability_id="bazi",
        )
        facts = {
            "subject:client": {
                "birth_datetime_or_four_pillars": "1994-04-30T05:55:00",
                "timezone": "Asia/Shanghai",
                "location": "福建省福州市",
                "gender": "female",
                "time_basis_policy": "civil",
            }
        }
        first = interface.execute(
            Prepare(query="先看整体", intent=intent, facts=facts)
        )
        self.assertIsInstance(first, Prepared, first)
        first_token = interface.engine.token_store.resolve(first.state_token)
        accepted = interface.execute(
            Complete(state_token=first.state_token, public_copy="第一轮正文。")
        )
        self.assertIsInstance(accepted, Accepted, accepted)

        follow = interface.execute(
            Prepare(
                query="再看下一层影响",
                intent=intent,
                facts=facts,
                state_token=first.state_token,
            )
        )
        self.assertIsInstance(follow, Prepared, follow)
        follow_token = interface.engine.token_store.resolve(follow.state_token)
        self.assertEqual(follow_token.reading_id, first_token.reading_id)
        self.assertEqual(follow_token.version, 2)
        self.assertEqual(follow.brief.prior_answer, "第一轮正文。")


if __name__ == "__main__":
    unittest.main()

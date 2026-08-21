"""Closed-world ReadingBrief: self-contained, ambient-memory-proof."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from reading_engine.interface_contracts import (
    Accepted,
    Complete,
    Describe,
    Prepare,
    Prepared,
    HorizonSelection,
    IntentSelection,
    Stopped,
)
from test_reading_engine_v2 import (
    StaticProvider,
    accept_prepared,
    build_engine,
)

ROOT = Path(__file__).resolve().parents[1]


def _interface(root: Path):
    from reading_engine.interface import ReadingInterface

    engine = build_engine(root, StaticProvider())
    return ReadingInterface(skill_root=ROOT, engine=engine)


def _prepare_command(query: str = "她现在大概在哪里？") -> Prepare:
    return Prepare(
        query=query,
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
                    "2026-07-22T22:13:00+08:00"
                ),
                "timezone": "Asia/Shanghai",
            }
        },
    )


class ClosedWorldBriefTests(unittest.TestCase):
    def _prepared(self, root: Path, command: Prepare | None = None):
        interface = _interface(root)
        result = interface.execute(command or _prepare_command())
        self.assertIsInstance(result, Prepared, result)
        return interface, result

    def test_ambient_host_memory_cannot_change_the_brief(self) -> None:
        with tempfile.TemporaryDirectory() as first_root:
            _, clean = self._prepared(Path(first_root))
        polluted_environment = {
            **os.environ,
            "HOST_AMBIENT_MEMORY": "订单 回款 对账 催款 报价 供应商项目",
        }
        with mock.patch.dict(os.environ, polluted_environment, clear=True):
            with tempfile.TemporaryDirectory() as second_root:
                _, polluted = self._prepared(Path(second_root))
        self.assertEqual(
            json.dumps(clean.brief.to_dict(), ensure_ascii=False, sort_keys=True),
            json.dumps(
                polluted.brief.to_dict(), ensure_ascii=False, sort_keys=True
            ),
        )
        rendered = json.dumps(polluted.brief.to_dict(), ensure_ascii=False)
        self.assertNotIn("订单", rendered)
        self.assertNotIn("回款", rendered)

    def test_brief_is_a_closed_referentially_intact_set(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            _, prepared = self._prepared(Path(root))
        brief = prepared.brief
        fact_refs = {fact.ref for fact in brief.facts}
        evidence_refs = {item.ref for item in brief.evidence}
        for scope in brief.claim_scopes:
            self.assertTrue(set(scope.fact_refs) <= fact_refs, scope)
            self.assertTrue(set(scope.evidence_refs) <= evidence_refs, scope)
        limit_kind_ids = {limit.kind_id for limit in brief.limits}
        for finding in brief.findings:
            self.assertTrue(set(finding.fact_refs) <= fact_refs, finding)
            self.assertTrue(set(finding.evidence_refs) <= evidence_refs, finding)
            self.assertTrue(
                set(finding.limit_kind_ids) <= limit_kind_ids,
                finding,
            )
        vocabulary_ids = [term.id for term in brief.vocabulary]
        self.assertEqual(len(vocabulary_ids), len(set(vocabulary_ids)))
        referenced = set()
        for scope in brief.claim_scopes:
            referenced.add(scope.dimension_id)
            referenced.update(scope.allowed_kind_ids)
            referenced.add(scope.certainty_ceiling_id)
        for limit in brief.limits:
            referenced.add(limit.kind_id)
        for finding in brief.findings:
            referenced.add(finding.kind_id)
        self.assertTrue(referenced <= set(vocabulary_ids), referenced)
        for term in brief.vocabulary:
            self.assertTrue(term.label.strip(), term.id)

    def test_brief_never_leaks_ids_paths_or_digests(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            interface, prepared = self._prepared(Path(root))
            reading_id = interface.engine.token_store.resolve(
                prepared.state_token
            ).reading_id
        rendered = json.dumps(prepared.brief.to_dict(), ensure_ascii=False)
        self.assertNotIn(reading_id, rendered)
        for private in ("prepared_digest", "/Users/", "pending.json", "store"):
            self.assertNotIn(private, rendered)

    def test_every_scope_limit_id_has_exactly_one_public_term(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            _, prepared = self._prepared(Path(root))
        brief = prepared.brief
        by_id: dict[str, int] = {}
        for term in brief.vocabulary:
            by_id[term.id] = by_id.get(term.id, 0) + 1
        self.assertTrue(all(count == 1 for count in by_id.values()), by_id)

    def test_continue_carries_prior_answer_but_correct_does_not(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            interface, prepared = self._prepared(Path(root))
            engine = interface.engine
            record = engine.token_store.resolve(prepared.state_token)
            staged = engine.store.load_prepared(record.reading_id)
            accept_prepared(engine, staged.public_contract())
            engine.token_store.mark_accepted(
                prepared.state_token, commit_ref=staged.prepared_digest
            )
            follow = interface.execute(
                Prepare(
                    query="那她会主动联系吗？",
                    intent=_prepare_command().intent,
                    facts=_prepare_command().facts,
                    state_token=prepared.state_token,
                )
            )
            self.assertIsInstance(follow, Prepared, follow)
            self.assertTrue(follow.brief.prior_answer)
            corrected = interface.execute(
                Prepare(
                    query="时间改成晚上九点",
                    intent=_prepare_command().intent,
                    facts={
                        "subject:test": {
                            "event_datetime_or_reference_datetime": (
                                "2026-07-22T21:00:00+08:00"
                            ),
                            "timezone": "Asia/Shanghai",
                        }
                    },
                    state_token=prepared.state_token,
                    transition="correct",
                )
            )
            # the follow-up already advanced this lineage, so a late correct
            # on the stale parent must stop as a conflict, never overwrite
            self.assertIsInstance(corrected, Stopped)
            self.assertEqual(corrected.reason, "conflict")
            self.assertTrue(corrected.public_copy.strip())

    def test_missing_required_input_stops_with_field_labels(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            interface = _interface(Path(root))
            command = Prepare(
                query="她现在大概在哪里？",
                intent=_prepare_command().intent,
                facts={"subject:test": {"timezone": "Asia/Shanghai"}},
            )
            result = interface.execute(command)
        self.assertIsInstance(result, Stopped, result)
        self.assertEqual(result.reason, "need_input")
        self.assertIsNotNone(result.state_token)
        self.assertTrue(result.public_copy.strip())
        # public question shows field labels, not internal field ids
        self.assertNotIn("event_datetime", result.public_copy)
        self.assertIn("事件时间", result.public_copy)


class CompleteCommitTests(unittest.TestCase):
    """`complete` is one mechanical, atomic, first-commit-wins operation."""

    def _prepared(self, root: Path):
        interface = _interface(root)
        result = interface.execute(_prepare_command())
        self.assertIsInstance(result, Prepared, result)
        return interface, result

    def test_complete_commits_and_replays_byte_identical_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            interface, prepared = self._prepared(Path(root))
            first = interface.execute(
                Complete(
                    state_token=prepared.state_token,
                    public_copy="事实已列明。\n候应偏向仍在熟悉场所。",
                )
            )
            self.assertIsInstance(first, Accepted, first)
            replay = interface.execute(
                Complete(
                    state_token=prepared.state_token,
                    public_copy="完全不同的第二份草稿。",
                )
            )
            self.assertIsInstance(replay, Accepted, replay)
            self.assertEqual(replay.public_copy, first.public_copy)

    def test_empty_draft_stops_without_consuming_the_prepared_state(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            interface, prepared = self._prepared(Path(root))
            rejected = interface.execute(
                Complete(state_token=prepared.state_token, public_copy="   ")
            )
            self.assertIsInstance(rejected, Stopped)
            self.assertEqual(rejected.reason, "error")
            self.assertTrue(rejected.public_copy.strip())
            retried = interface.execute(
                Complete(
                    state_token=prepared.state_token,
                    public_copy="事实已列明。\n重试后成稿。",
                )
            )
            self.assertIsInstance(retried, Accepted, retried)

    def test_unknown_token_stops_with_public_text(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            interface = _interface(Path(root))
            result = interface.execute(
                Complete(state_token="never-issued", public_copy="文本")
            )
        self.assertIsInstance(result, Stopped)
        self.assertTrue(result.public_copy.strip())

    def test_store_commit_failure_stops_and_stays_retryable(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            interface, prepared = self._prepared(Path(root))
            with mock.patch.object(
                interface.engine.store,
                "commit",
                side_effect=OSError("injected commit crash"),
            ):
                failed = interface.execute(
                    Complete(
                        state_token=prepared.state_token,
                        public_copy="事实已列明。\n首次提交。",
                    )
                )
            self.assertIsInstance(failed, Stopped)
            self.assertEqual(failed.reason, "error")
            self.assertTrue(failed.public_copy.strip())
            recovered = interface.execute(
                Complete(
                    state_token=prepared.state_token,
                    public_copy="事实已列明。\n首次提交。",
                )
            )
            self.assertIsInstance(recovered, Accepted, recovered)

    def test_pending_question_token_cannot_complete(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            interface = _interface(Path(root))
            pending = interface.execute(
                Prepare(
                    query="她现在大概在哪里？",
                    intent=_prepare_command().intent,
                    facts={"subject:test": {"timezone": "Asia/Shanghai"}},
                )
            )
            self.assertIsInstance(pending, Stopped)
            self.assertEqual(pending.reason, "need_input")
            result = interface.execute(
                Complete(state_token=pending.state_token, public_copy="文本")
            )
        self.assertIsInstance(result, Stopped)
        self.assertEqual(result.reason, "error")
        self.assertTrue(result.public_copy.strip())



class ProviderProjectionBriefTests(unittest.TestCase):
    """The brief consumes only provider public projections."""

    def _production_prepared(self):
        import tempfile

        from reading_engine.interface import ReadingInterface
        from reading_engine.interface_contracts import (
            HorizonSelection,
            IntentSelection,
            Prepare,
            Prepared,
        )

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        interface = ReadingInterface(skill_root=ROOT, store_root=Path(tmp.name))
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
        return interface, result

    def test_facts_are_projected_not_internal_paths(self) -> None:
        _, result = self._production_prepared()
        for fact in result.brief.facts:
            with self.subTest(ref=fact.ref):
                self.assertFalse(
                    fact.display_text.startswith("chart_facts"),
                    fact.display_text,
                )
                self.assertNotIn("fact_extensions", fact.display_text)
                self.assertNotIn("/", fact.display_text.split("：")[0])

    def test_claim_scopes_reference_only_published_refs(self) -> None:
        _, result = self._production_prepared()
        fact_refs = {fact.ref for fact in result.brief.facts}
        evidence_refs = {item.ref for item in result.brief.evidence}
        vocabulary_ids = {term.id for term in result.brief.vocabulary}
        self.assertTrue(result.brief.claim_scopes)
        for scope in result.brief.claim_scopes:
            with self.subTest(dimension=scope.dimension_id):
                self.assertTrue(set(scope.fact_refs) <= fact_refs)
                self.assertTrue(set(scope.evidence_refs) <= evidence_refs)
                for kind_id in scope.allowed_kind_ids:
                    self.assertIn(kind_id, vocabulary_ids)
                self.assertIn(scope.certainty_ceiling_id, vocabulary_ids)

    def test_claim_policy_comes_from_the_provider_descriptor(self) -> None:
        interface, result = self._production_prepared()
        descriptor = interface.catalog.descriptor("bazi")
        policy = descriptor.claim_policy
        self.assertTrue(policy["allowed_kind_ids"])
        for scope in result.brief.claim_scopes:
            self.assertEqual(
                tuple(scope.allowed_kind_ids),
                tuple(policy["allowed_kind_ids"]),
            )
            self.assertEqual(
                scope.certainty_ceiling_id,
                policy["certainty_ceiling_id"],
            )

    def test_ambient_host_memory_never_reaches_the_brief(self) -> None:
        import json as _json
        import os

        _, first = self._production_prepared()
        ambient = {
            "HERMES_SESSION_MEMORY": "用户其实最担心事业和金钱问题",
            "HOST_AMBIENT_NOTES": "上次说过感情不稳定",
        }
        previous = {key: os.environ.get(key) for key in ambient}
        os.environ.update(ambient)
        try:
            _, second = self._production_prepared()
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        self.assertEqual(
            _json.dumps(first.brief.to_dict(), ensure_ascii=False, sort_keys=True),
            _json.dumps(second.brief.to_dict(), ensure_ascii=False, sort_keys=True),
        )


if __name__ == "__main__":
    unittest.main()

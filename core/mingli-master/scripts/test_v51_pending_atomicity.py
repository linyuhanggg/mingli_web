"""Pending intake atomicity and scope binding.

H1: a pending token must atomically transition to exactly one prepared
     result.  The same pending token resumed twice (a lost response, a
     double-submit, or two concurrent hosts) must converge on the same
     prepared token; it must never mint sibling prepared tokens that leave
     one permanently un-completable.

H3: resuming a pending token must keep the original intake scope.  A
     supplement that names a different subject or object must surface as
     Stopped.conflict, never silently rewrite the pending request.
"""

from __future__ import annotations

import shutil
import tempfile
import unittest

from reading_engine.interface_contracts import (
    Complete,
    Prepare,
    Prepared,
    Stopped,
)
from reading_engine.state_token import StateTokenStore
from test_v51_model_selection_fallback import _build_fixture, _intent


def _alpha_fixture():
    return _build_fixture(alpha_needs=("field.one",))


class PendingAtomicTransitionTests(unittest.TestCase):
    """H1: double-resume converges on one prepared token, one commit."""

    def setUp(self) -> None:
        self.fixture = _alpha_fixture()
        self.addCleanup(self.fixture.cleanup)
        self.interface = self.fixture.interface()

    def _pending_token(self) -> str:
        first = self.interface.execute(
            Prepare(
                query="中性问句",
                intent=_intent(capability_id="capability.alpha"),
                facts={},
            )
        )
        self.assertIsInstance(first, Stopped, first)
        self.assertEqual(first.reason, "need_input", first)
        self.assertIsNotNone(first.state_token)
        return first.state_token

    def _resume(self, token: str) -> Prepared:
        result = self.interface.execute(
            Prepare(
                query="中性问句（补资料）",
                intent=_intent(capability_id="capability.alpha"),
                facts={"subject:test": {"field.one": "已提供"}},
                state_token=token,
            )
        )
        self.assertIsInstance(result, Prepared, result)
        return result

    def test_double_resume_returns_the_same_prepared_token(self) -> None:
        pending = self._pending_token()
        first = self._resume(pending)
        second = self._resume(pending)
        # The same canonical supplement must converge on the same token.
        self.assertEqual(first.state_token, second.state_token)

    def test_double_resume_replays_the_same_brief(self) -> None:
        pending = self._pending_token()
        first = self._resume(pending)
        second = self._resume(pending)
        self.assertEqual(
            first.brief.to_dict(), second.brief.to_dict()
        )

    def test_one_prepared_token_completes_and_replay_is_idempotent(self) -> None:
        pending = self._pending_token()
        prepared = self._resume(pending)
        # Complete the promoted token; a replay of the same complete returns
        # the original committed bytes (first-commit-wins).
        done = self.interface.execute(
            Complete(state_token=prepared.state_token, public_copy="正文")
        )
        self.assertEqual(done.kind, "accepted")
        again = self.interface.execute(
            Complete(state_token=prepared.state_token, public_copy="正文改")
        )
        self.assertEqual(again.kind, "accepted")
        self.assertEqual(again.public_copy, "正文")
        # After completion the same token starts a *new* continue version,
        # never a sibling of the old prepared record.
        followed = self._resume(pending)
        self.assertIsInstance(followed, Prepared)

    def test_no_sibling_prepared_tokens_after_double_resume(self) -> None:
        pending = self._pending_token()
        first = self._resume(pending)
        second = self._resume(pending)
        # Both tokens are the same string; completing once leaves no second
        # sibling waiting for a commit that can never arrive.
        done = self.interface.execute(
            Complete(state_token=first.state_token, public_copy="正文")
        )
        self.assertEqual(done.kind, "accepted")


class PendingCrashRecoveryTests(unittest.TestCase):
    """H1 crash recovery: the derived index must survive log-only rebuild.

    A process crash between the authoritative log append and the derived
    index write (or an index loss) must rebuild the promoted prepared phase
    from the log; otherwise a completed-token advance silently regresses to
    pending and the later complete fails.
    """

    def test_promoted_token_survives_index_rebuild(self) -> None:
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temporary:
            store = StateTokenStore(Path(temporary))
            token = store.issue(
                reading_id="reading-1",
                version=1,
                phase="pending_input",
                intake_id="intake-1",
                request_digest="pending-digest",
            )
            store.promote_to_prepared(
                token,
                reading_id="reading-1",
                version=1,
                request_digest="prepared-digest",
            )
            self.assertEqual(store.resolve(token).phase, "prepared")
            # Simulate a crash that lost the derived index; only the
            # authoritative log remains.
            shutil.rmtree(Path(temporary) / "index")
            store.rebuild_index()
            record = store.resolve(token)
            self.assertEqual(record.phase, "prepared")
            self.assertEqual(record.request_digest, "prepared-digest")
            self.assertEqual(record.reading_id, "reading-1")

    def test_accepted_token_survives_index_rebuild(self) -> None:
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temporary:
            store = StateTokenStore(Path(temporary))
            token = store.issue(
                reading_id="reading-2",
                version=1,
                phase="prepared",
                request_digest="prepared-digest",
            )
            store.mark_accepted(token, commit_ref="commit-ref")
            self.assertEqual(store.resolve(token).phase, "accepted")
            shutil.rmtree(Path(temporary) / "index")
            store.rebuild_index()
            record = store.resolve(token)
            self.assertEqual(record.phase, "accepted")
            self.assertEqual(record.commit_ref, "commit-ref")

    def test_rebuild_then_complete_promoted_reading(self) -> None:
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temporary:
            store = StateTokenStore(Path(temporary))
            token = store.issue(
                reading_id="reading-3",
                version=1,
                phase="pending_input",
                intake_id="intake-3",
                request_digest="pending-digest",
            )
            store.promote_to_prepared(
                token,
                reading_id="reading-3",
                version=1,
                request_digest="prepared-digest",
            )
            # Crash + rebuild: the token must still be a committable prepared.
            shutil.rmtree(Path(temporary) / "index")
            store.rebuild_index()
            record = store.resolve(token)
            self.assertEqual(record.phase, "prepared")
            # mark_accepted must succeed on the rebuilt record.
            store.mark_accepted(token, commit_ref="commit-3")
            self.assertEqual(store.resolve(token).phase, "accepted")

    def test_token_files_are_private_and_lineage_rebuild_keeps_mode(self) -> None:
        import stat
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = StateTokenStore(root)
            parent = store.issue(
                reading_id="reading-4",
                version=1,
                phase="prepared",
                request_digest="parent-digest",
            )
            child = store.issue(
                reading_id="reading-5",
                version=1,
                phase="prepared",
                request_digest="child-digest",
                parent_token=parent,
            )
            store.claim_lineage(
                parent, child, request_digest="child-digest", child_reading_id="reading-5"
            )
            self.assertEqual(stat.S_IMODE(root.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE((root / "index").stat().st_mode), 0o700)
            self.assertEqual(
                stat.S_IMODE((root / "token-log.jsonl").stat().st_mode), 0o600
            )
            lineage_files = list((root / "index").glob("lineage-*.json"))
            self.assertEqual(len(lineage_files), 1)
            self.assertEqual(stat.S_IMODE(lineage_files[0].stat().st_mode), 0o600)
            # A lineage rebuild through the derived-index repair keeps 0600.
            shutil.rmtree(root / "index")
            store.rebuild_index()
            rebuilt = list((root / "index").glob("lineage-*.json"))
            self.assertEqual(len(rebuilt), 1)
            self.assertEqual(stat.S_IMODE(rebuilt[0].stat().st_mode), 0o600)
            self.assertIsNotNone(store.lineage_claim(parent))

    def test_preplaced_index_symlink_is_rejected(self) -> None:
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = StateTokenStore(root)
            victim = Path(temporary) / "victim.txt"
            victim.write_text("do-not-touch")
            token = store.issue(
                reading_id="reading-6",
                version=1,
                phase="prepared",
                request_digest="digest-6",
            )
            record = store.resolve(token)
            index_path = root / "index" / f"{record.token_hash}.json"
            index_path.unlink()
            index_path.symlink_to(victim)
            with self.assertRaises(ValueError):
                store.mark_accepted(token, commit_ref="commit-6")
            self.assertEqual(victim.read_text(), "do-not-touch")


class PendingScopeBindingTests(unittest.TestCase):
    """H3: resume must not silently change the intake scope."""

    def setUp(self) -> None:
        self.fixture = _alpha_fixture()
        self.addCleanup(self.fixture.cleanup)
        self.interface = self.fixture.interface()

    def _pending_token(self, subject: str = "subject:test") -> str:
        first = self.interface.execute(
            Prepare(
                query="中性问句",
                intent=_intent(
                    subject=subject, capability_id="capability.alpha"
                ),
                facts={},
            )
        )
        self.assertIsInstance(first, Stopped, first)
        return first.state_token

    def test_resume_with_different_subject_returns_conflict(self) -> None:
        pending = self._pending_token(subject="subject:test")
        result = self.interface.execute(
            Prepare(
                query="中性问句（补资料）",
                intent=_intent(
                    subject="subject:other", capability_id="capability.alpha"
                ),
                facts={"subject:other": {"field.one": "已提供"}},
                state_token=pending,
            )
        )
        self.assertIsInstance(result, Stopped, result)
        self.assertEqual(result.reason, "conflict", result)

    def test_resume_with_different_object_returns_conflict(self) -> None:
        pending = self._pending_token()
        result = self.interface.execute(
            Prepare(
                query="中性问句（补资料）",
                intent=_intent(
                    object_id="object.two", capability_id="capability.alpha"
                ),
                facts={"subject:test": {"field.one": "已提供"}},
                state_token=pending,
            )
        )
        self.assertIsInstance(result, Stopped, result)
        self.assertEqual(result.reason, "conflict", result)

    def test_resume_with_same_scope_still_prepares(self) -> None:
        pending = self._pending_token()
        result = self.interface.execute(
            Prepare(
                query="中性问句（补资料）",
                intent=_intent(capability_id="capability.alpha"),
                facts={"subject:test": {"field.one": "已提供"}},
                state_token=pending,
            )
        )
        self.assertIsInstance(result, Prepared, result)


if __name__ == "__main__":
    unittest.main()

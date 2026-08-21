"""One opaque state token; hashes on disk; derived index is repairable."""

from __future__ import annotations

import hashlib
import os
import shutil
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from reading_engine import state_token
from reading_engine.state_token import StateTokenStore, TokenConflict


class StateTokenTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.store = StateTokenStore(self.root)

    def test_token_is_opaque_and_high_entropy(self) -> None:
        reading_id = "a" * 32
        generated = ("3" + "x" * 42, "y" * 43)
        with mock.patch.object(
            state_token.secrets,
            "token_urlsafe",
            side_effect=generated,
        ) as token_urlsafe:
            first = self.store.issue(
                reading_id=reading_id, version=3, phase="prepared"
            )
            second = self.store.issue(
                reading_id=reading_id, version=3, phase="prepared"
            )

        self.assertEqual((first, second), generated)
        self.assertEqual(
            token_urlsafe.call_args_list,
            [mock.call(32), mock.call(32)],
        )
        self.assertNotEqual(first, second)
        self.assertNotIn(reading_id, first)
        self.assertNotIn("/", first)
        self.assertGreaterEqual(len(first), 32)

    def test_raw_token_never_touches_disk_only_its_hash_does(self) -> None:
        token = self.store.issue(
            reading_id="b" * 32, version=1, phase="prepared"
        )
        digest = hashlib.sha256(token.encode("ascii")).hexdigest()
        rendered_files = [
            path.read_text(encoding="utf-8")
            for path in self.root.rglob("*")
            if path.is_file()
        ]
        joined = "\n".join(rendered_files)
        self.assertNotIn(token, joined)
        self.assertIn(digest, joined)

    def test_resolution_replays_the_same_record(self) -> None:
        token = self.store.issue(
            reading_id="c" * 32, version=2, phase="prepared"
        )
        first = self.store.resolve(token)
        second = self.store.resolve(token)
        self.assertIsNotNone(first)
        self.assertEqual(first, second)
        self.assertEqual(first.reading_id, "c" * 32)
        self.assertEqual(first.version, 2)
        self.assertEqual(first.phase, "prepared")

    def test_unknown_token_resolves_to_none_without_guessing(self) -> None:
        self.store.issue(reading_id="d" * 32, version=1, phase="prepared")
        self.assertIsNone(self.store.resolve("not-a-known-token"))

    def test_accept_commit_is_first_write_wins_and_byte_stable(self) -> None:
        token = self.store.issue(
            reading_id="e" * 32, version=1, phase="prepared"
        )
        first = self.store.mark_accepted(token, commit_ref="digest-one")
        replay = self.store.mark_accepted(token, commit_ref="digest-two")
        self.assertEqual(first, "digest-one")
        self.assertEqual(replay, "digest-one")
        record = self.store.resolve(token)
        self.assertEqual(record.phase, "accepted")
        self.assertEqual(record.commit_ref, "digest-one")

    def test_stale_parent_and_second_child_conflict(self) -> None:
        parent = self.store.issue(
            reading_id="f" * 32, version=1, phase="accepted"
        )
        first_child = self.store.issue(
            reading_id="f" * 32,
            version=2,
            phase="prepared",
            parent_token=parent,
        )
        self.assertEqual(
            self.store.claim_lineage(parent, first_child), "won"
        )
        # replaying the exact same child is idempotent
        self.assertEqual(
            self.store.claim_lineage(parent, first_child), "replay"
        )
        second_child = self.store.issue(
            reading_id="f" * 32,
            version=2,
            phase="prepared",
            parent_token=parent,
        )
        with self.assertRaises(TokenConflict):
            self.store.claim_lineage(parent, second_child)

    def test_derived_index_loss_repairs_from_authoritative_log(self) -> None:
        token = self.store.issue(
            reading_id="1234" * 8, version=1, phase="prepared"
        )
        for path in (self.root / "index").rglob("*.json"):
            path.unlink()
        reopened = StateTokenStore(self.root)
        record = reopened.resolve(token)
        self.assertIsNotNone(record)
        self.assertEqual(record.reading_id, "1234" * 8)

    def test_crash_between_log_and_index_still_resolves_after_reopen(self) -> None:
        # Inject a failure at the derived-index write seam; the authoritative
        # log has already been written, so a reopened store must recover.
        with mock.patch.object(
            state_token,
            "_write_index_entry",
            side_effect=OSError("injected crash"),
        ):
            with self.assertRaises(OSError):
                self.store.issue(
                    reading_id="ab" * 16, version=1, phase="prepared"
                )
        reopened = StateTokenStore(self.root)
        reopened.rebuild_index()
        tokens = list((self.root / "index").rglob("*.json"))
        self.assertTrue(tokens)

    def test_log_write_failure_leaves_no_derived_entry(self) -> None:
        with mock.patch.object(
            state_token,
            "_append_log_line",
            side_effect=OSError("injected crash"),
        ):
            with self.assertRaises(OSError):
                self.store.issue(
                    reading_id="cd" * 16, version=1, phase="prepared"
                )
        index_entries = list((self.root / "index").rglob("*.json"))
        self.assertEqual(index_entries, [])


class StateTokenSecurityBoundaryTests(unittest.TestCase):
    """Frozen private-store boundaries: symlinks and umask."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def test_broken_log_symlink_is_rejected_and_victim_is_not_created(
        self,
    ) -> None:
        """3.1: a broken ``token-log.jsonl`` symlink must be refused.

        ``Path.exists()`` is False for a broken symlink, so a plain
        ``open(..., "a")`` would follow it and create the external victim.
        The append path must open with ``O_NOFOLLOW`` and verify the fd is a
        regular file owned by the current user.
        """
        external_dir = self.root / "external"
        external_dir.mkdir()
        victim = external_dir / "victim-log.jsonl"
        store = StateTokenStore(self.root)
        (self.root / "token-log.jsonl").unlink(missing_ok=True)
        (self.root / "token-log.jsonl").symlink_to(
            victim, target_is_directory=False
        )
        with self.assertRaises((ValueError, OSError)):
            store.issue(
                reading_id="aa" * 16, version=1, phase="prepared"
            )
        self.assertFalse(victim.exists(), "external victim was created")
        self.assertFalse(
            (external_dir / "token-log.jsonl").exists(),
            "external target was created through the symlink",
        )

    def test_broken_log_symlink_does_not_modify_existing_victim(self) -> None:
        """3.1: a broken symlink pointing at an existing victim stays intact."""
        external_dir = self.root / "external"
        external_dir.mkdir()
        victim = external_dir / "victim-log.jsonl"
        victim.write_text("original content\n", encoding="utf-8")
        store = StateTokenStore(self.root)
        (self.root / "token-log.jsonl").unlink(missing_ok=True)
        (self.root / "token-log.jsonl").symlink_to(
            victim, target_is_directory=False
        )
        with self.assertRaises((ValueError, OSError)):
            store.issue(
                reading_id="bb" * 16, version=1, phase="prepared"
            )
        self.assertEqual(
            victim.read_text(encoding="utf-8"),
            "original content\n",
            "existing victim was modified through the broken symlink",
        )

    def test_index_directory_symlink_is_rejected_on_rebuild(self) -> None:
        """3.2: ``index`` swapped for an external symlink must be refused.

        Neither the per-hash entries nor lineage files may be written through
        the index symlink into the external directory.
        """
        external = self.root / "external-index-target"
        external.mkdir()
        store = StateTokenStore(self.root)
        token = store.issue(
            reading_id="cc" * 16, version=1, phase="prepared"
        )
        store.mark_accepted(token, commit_ref="commit-1")
        # Replace the whole index directory with a symlink to external.
        shutil.rmtree(self.root / "index")
        (self.root / "index").symlink_to(external, target_is_directory=True)
        with self.assertRaises((ValueError, OSError, RuntimeError)):
            store.rebuild_index()
        self.assertEqual(
            list(external.iterdir()),
            [],
            "rebuild wrote index/lineage files through the index symlink",
        )

    def test_index_directory_symlink_is_rejected_on_issue(self) -> None:
        """3.2: a pre-placed index symlink must be refused at write time."""
        external = self.root / "external-index-target"
        external.mkdir()
        # The store constructor already created a real index directory; replace
        # it with a symlink before issuing.
        StateTokenStore(self.root)
        shutil.rmtree(self.root / "index")
        (self.root / "index").symlink_to(external, target_is_directory=True)
        with self.assertRaises((ValueError, OSError, RuntimeError)):
            store = StateTokenStore(self.root)
            store.issue(
                reading_id="dd" * 16, version=1, phase="prepared"
            )
        self.assertEqual(
            list(external.iterdir()),
            [],
            "issue wrote through the index symlink into external",
        )

    def test_rebuild_keeps_0700_index_under_umask_022(self) -> None:
        """3.3: rebuild must not leave a umask-0755 index directory."""
        previous = os.umask(0o022)
        try:
            store = StateTokenStore(self.root)
            token = store.issue(
                reading_id="ee" * 16, version=1, phase="prepared"
            )
            store.mark_accepted(token, commit_ref="commit-1")
            shutil.rmtree(self.root / "index")
            store.rebuild_index()
            self.assertEqual(
                stat.S_IMODE((self.root / "index").stat().st_mode),
                0o700,
                "rebuilt index directory must be 0700 regardless of umask",
            )
            self.assertEqual(
                stat.S_IMODE(self.root.stat().st_mode),
                0o700,
                "store root must stay 0700",
            )
            self.assertEqual(
                stat.S_IMODE((self.root / "token-log.jsonl").stat().st_mode),
                0o600,
                "log file must stay 0600",
            )
            for path in (self.root / "index").glob("*.json"):
                self.assertEqual(
                    stat.S_IMODE(path.stat().st_mode),
                    0o600,
                    f"index file {path.name} must be 0600",
                )
        finally:
            os.umask(previous)

    def test_normal_lifecycle_still_passes_after_secure_writes(self) -> None:
        """issue -> resolve -> promote -> accept -> rebuild still works."""
        store = StateTokenStore(self.root)
        token = store.issue(
            reading_id="ff" * 16, version=1, phase="pending_input"
        )
        self.assertIsNotNone(store.resolve(token))
        store.promote_to_prepared(
            token,
            reading_id="ff" * 16,
            version=1,
            request_digest="request-digest",
        )
        store.mark_accepted(token, commit_ref="commit-final")
        store.rebuild_index()
        record = store.resolve(token)
        self.assertIsNotNone(record)
        self.assertEqual(record.phase, "accepted")
        self.assertEqual(record.commit_ref, "commit-final")

    def test_resolve_rejects_a_symlinked_index_record(self) -> None:
        store = StateTokenStore(self.root)
        token = store.issue(
            reading_id="12" * 16, version=1, phase="prepared"
        )
        digest = hashlib.sha256(token.encode("ascii")).hexdigest()
        entry = self.root / "index" / f"{digest}.json"
        victim = self.root / "external-index-record.json"
        victim.write_text(entry.read_text(encoding="utf-8"), encoding="utf-8")
        entry.unlink()
        entry.symlink_to(victim)

        with self.assertRaises((ValueError, OSError, RuntimeError)):
            store.resolve(token)

    def test_corrupt_derived_index_repairs_from_authoritative_log(self) -> None:
        store = StateTokenStore(self.root)
        token = store.issue(
            reading_id="17" * 16, version=1, phase="prepared"
        )
        digest = hashlib.sha256(token.encode("ascii")).hexdigest()
        entry = self.root / "index" / f"{digest}.json"
        entry.write_text("{broken derived json", encoding="utf-8")

        record = store.resolve(token)

        self.assertIsNotNone(record)
        self.assertEqual(record.reading_id, "17" * 16)
        self.assertEqual(record.phase, "prepared")

    def test_lineage_read_rejects_a_symlinked_claim(self) -> None:
        store = StateTokenStore(self.root)
        parent = store.issue(
            reading_id="13" * 16, version=1, phase="accepted"
        )
        child = store.issue(
            reading_id="14" * 16, version=1, phase="prepared"
        )
        store.claim_lineage(parent, child, request_digest="request-one")
        parent_hash = hashlib.sha256(parent.encode("ascii")).hexdigest()
        claim = self.root / "index" / f"lineage-{parent_hash}.json"
        victim = self.root / "external-lineage.json"
        victim.write_text(claim.read_text(encoding="utf-8"), encoding="utf-8")
        claim.unlink()
        claim.symlink_to(victim)

        with self.assertRaises((ValueError, OSError, RuntimeError)):
            store.lineage_claim(parent)

    def test_claim_lineage_rejects_a_symlinked_existing_claim(self) -> None:
        store = StateTokenStore(self.root)
        parent = store.issue(
            reading_id="18" * 16, version=1, phase="accepted"
        )
        child = store.issue(
            reading_id="19" * 16, version=1, phase="prepared"
        )
        parent_hash = hashlib.sha256(parent.encode("ascii")).hexdigest()
        child_hash = hashlib.sha256(child.encode("ascii")).hexdigest()
        claim = self.root / "index" / f"lineage-{parent_hash}.json"
        victim = self.root / "external-existing-lineage.json"
        victim_content = f'{{"child_token_hash": "{child_hash}"}}'
        victim.write_text(victim_content, encoding="utf-8")
        claim.symlink_to(victim)

        with self.assertRaises((ValueError, OSError, RuntimeError)):
            store.claim_lineage(parent, child, request_digest="request-two")

        self.assertEqual(
            victim.read_text(encoding="utf-8"),
            victim_content,
        )

    def test_rebuild_rejects_a_symlinked_log(self) -> None:
        store = StateTokenStore(self.root)
        store.issue(reading_id="15" * 16, version=1, phase="prepared")
        log = self.root / "token-log.jsonl"
        victim = self.root / "external-log.jsonl"
        victim.write_text(log.read_text(encoding="utf-8"), encoding="utf-8")
        log.unlink()
        log.symlink_to(victim)

        with self.assertRaises((ValueError, OSError, RuntimeError)):
            store.rebuild_index()

    def test_advance_lock_rejects_a_symlink_without_chmodding_victim(self) -> None:
        store = StateTokenStore(self.root)
        parent = store.issue(
            reading_id="16" * 16, version=1, phase="accepted"
        )
        parent_hash = hashlib.sha256(parent.encode("ascii")).hexdigest()
        victim = self.root / "external-lock"
        victim.write_text("unchanged", encoding="utf-8")
        victim.chmod(0o644)
        lock = self.root / "index" / f".advance-{parent_hash}.lock"
        lock.symlink_to(victim)

        with self.assertRaises((ValueError, OSError, RuntimeError)):
            with store.advance_lock(parent):
                pass
        self.assertEqual(victim.read_text(encoding="utf-8"), "unchanged")
        self.assertEqual(stat.S_IMODE(victim.stat().st_mode), 0o644)


class ConcurrentLineageTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.store = StateTokenStore(Path(self._tmp.name))

    def test_concurrent_children_yield_exactly_one_winner(self) -> None:
        import threading

        parent = self.store.issue(
            reading_id="a" * 32, version=1, phase="accepted"
        )
        outcomes: list[str] = []
        lock = threading.Lock()
        barrier = threading.Barrier(2)

        def claim(child_reading: str, digest: str) -> None:
            child = self.store.issue(
                reading_id=child_reading, version=1, phase="prepared"
            )
            barrier.wait()
            try:
                self.store.claim_lineage(
                    parent,
                    child,
                    request_digest=digest,
                    child_reading_id=child_reading,
                )
                with lock:
                    outcomes.append("won")
            except TokenConflict:
                with lock:
                    outcomes.append("conflict")

        threads = [
            threading.Thread(target=claim, args=("b" * 32, "digest-one")),
            threading.Thread(target=claim, args=("c" * 32, "digest-two")),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sorted(outcomes), ["conflict", "won"], outcomes)

    def test_same_canonical_turn_replays_idempotently(self) -> None:
        parent = self.store.issue(
            reading_id="a" * 32, version=1, phase="accepted"
        )
        first_child = self.store.issue(
            reading_id="b" * 32, version=1, phase="prepared"
        )
        self.store.claim_lineage(
            parent,
            first_child,
            request_digest="same-turn",
            child_reading_id="b" * 32,
        )
        second_child = self.store.issue(
            reading_id="b" * 32, version=1, phase="prepared"
        )
        outcome = self.store.claim_lineage(
            parent,
            second_child,
            request_digest="same-turn",
            child_reading_id="b" * 32,
        )
        self.assertIn(outcome, {"replay", "rotated"})


if __name__ == "__main__":
    unittest.main()

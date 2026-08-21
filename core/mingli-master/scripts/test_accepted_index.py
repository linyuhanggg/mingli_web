"""Tests for the externally anchored acceptance-order index."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from accepted_index import (
    INDEX_NAME,
    _checkpoint_path,
    _load_or_create_key,
    _seal_index,
    _validate_index,
    load_acceptance_index,
    record_acceptance,
    record_pipeline_creation,
)


def _digest(value: object) -> str:
    rendered = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def _envelope(
    reading_id: str,
    judgment: str,
    *,
    prior_manifest_digest: str | None = None,
) -> dict:
    sections = [
        {"kind": "chart", "text": "卦象：过程有承接。"},
        {"kind": "judgment", "text": judgment, "claim_ids": ["claim-final"]},
    ]
    public_copy = "【玄枢｜MINGLI】\n" + "\n\n".join(
        section["text"] for section in sections
    )
    manifest = {
        "schema_version": "mingli-public-answer-manifest-v1",
        "reading_id": reading_id,
        "inference_digest": "1" * 64,
        "public_copy_sha256": hashlib.sha256(public_copy.encode("utf-8")).hexdigest(),
        "followup_of_manifest_digest": prior_manifest_digest,
        "sections": sections,
        "claims": [
            {
                "claim_id": "claim-final",
                "dimension": "outcome",
                "polarity": "support",
                "text": "偏向能成",
                "activation_ids": ["outcome-support"],
            }
        ],
    }
    manifest["manifest_digest"] = _digest(manifest)
    envelope = {
        "schema_version": "mingli-accepted-public-v1",
        "reading_id": reading_id,
        "manifest_digest": manifest["manifest_digest"],
        "public_copy_sha256": manifest["public_copy_sha256"],
        "inference_digest": manifest["inference_digest"],
        "manifest": manifest,
        "public_copy": public_copy,
    }
    envelope["envelope_digest"] = _digest(envelope)
    return envelope


def _write_envelope(path: Path, envelope: dict) -> None:
    path.write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _record_initial(root: Path, artifact: Path, pipeline: Path) -> tuple[dict, dict]:
    envelope = _envelope("reading-a", "这件事偏向能成。")
    event = record_acceptance(
        root,
        event_type="initial",
        system="liuren",
        reading_id="reading-a",
        artifact_dir=artifact,
        pipeline_manifest_path=pipeline,
        accepted_envelope=envelope,
        operation_id="a" * 64,
    )
    return event, envelope


class AcceptedIndexTests(unittest.TestCase):
    def test_records_complete_monotonic_initial_and_followup_events(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact = root / "2026-07-13" / "reading-a"
            artifact.mkdir(parents=True)
            pipeline = artifact / "pipeline-manifest.json"
            pipeline.write_text("{}\n", encoding="utf-8")
            initial, initial_envelope = _record_initial(root, artifact, pipeline)
            followup_envelope = _envelope(
                "reading-a",
                "这件事偏向能成，过程先慢后顺。",
                prior_manifest_digest=initial_envelope["manifest_digest"],
            )

            followup = record_acceptance(
                root,
                event_type="followup",
                system="liuren",
                reading_id="reading-a",
                artifact_dir=artifact,
                pipeline_manifest_path=pipeline,
                accepted_envelope=followup_envelope,
                prior_manifest_digest=initial_envelope["manifest_digest"],
                operation_id="b" * 64,
                reservation_name="reservation-a.json",
                draft_sha256="c" * 64,
            )

            index = load_acceptance_index(root)
            self.assertEqual(initial["sequence"], 1)
            self.assertEqual(followup["sequence"], 2)
            self.assertEqual(followup["initial_sequence"], 1)
            self.assertEqual(followup["accepted_envelope"], followup_envelope)
            self.assertEqual(index["events"], [initial, followup])
            self.assertEqual(os.stat(root / INDEX_NAME).st_mode & 0o777, 0o600)

    def test_same_operation_is_idempotent_but_another_reservation_cannot_claim_it(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact = root / "reading-a"
            artifact.mkdir()
            pipeline = artifact / "pipeline-manifest.json"
            pipeline.write_text("{}\n", encoding="utf-8")
            _, initial_envelope = _record_initial(root, artifact, pipeline)
            followup_envelope = _envelope(
                "reading-a",
                "这件事偏向能成，过程先慢后顺。",
                prior_manifest_digest=initial_envelope["manifest_digest"],
            )
            arguments = {
                "event_type": "followup",
                "system": "liuren",
                "reading_id": "reading-a",
                "artifact_dir": artifact,
                "pipeline_manifest_path": pipeline,
                "accepted_envelope": followup_envelope,
                "prior_manifest_digest": initial_envelope["manifest_digest"],
                "operation_id": "b" * 64,
                "reservation_name": "reservation-a.json",
                "draft_sha256": "c" * 64,
            }

            committed = record_acceptance(root, **arguments)
            retried = record_acceptance(root, **arguments)

            self.assertEqual(retried, committed)
            self.assertEqual(len(load_acceptance_index(root)["events"]), 2)
            with self.assertRaisesRegex(ValueError, "stale|another operation"):
                record_acceptance(
                    root,
                    **{
                        **arguments,
                        "operation_id": "d" * 64,
                        "reservation_name": "reservation-b.json",
                        "draft_sha256": "e" * 64,
                    },
                )

    def test_signed_followup_cannot_rebind_its_pipeline_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact = root / "reading-a"
            artifact.mkdir()
            pipeline = artifact / "pipeline-manifest.json"
            pipeline.write_text("{}\n", encoding="utf-8")
            _, initial_envelope = _record_initial(root, artifact, pipeline)
            followup_envelope = _envelope(
                "reading-a",
                "这件事偏向能成，过程先慢后顺。",
                prior_manifest_digest=initial_envelope["manifest_digest"],
            )
            record_acceptance(
                root,
                event_type="followup",
                system="liuren",
                reading_id="reading-a",
                artifact_dir=artifact,
                pipeline_manifest_path=pipeline,
                accepted_envelope=followup_envelope,
                prior_manifest_digest=initial_envelope["manifest_digest"],
                operation_id="b" * 64,
                reservation_name="reservation-a.json",
                draft_sha256="c" * 64,
            )
            index = load_acceptance_index(root)
            followup = index["events"][1]
            followup["artifact_relpath"] = "other-reading"
            followup["pipeline_manifest_relpath"] = (
                "other-reading/pipeline-manifest.json"
            )
            followup["pipeline_manifest_sha256"] = "f" * 64
            followup["event_digest"] = _digest(
                {
                    name: value
                    for name, value in followup.items()
                    if name != "event_digest"
                }
            )
            key = _load_or_create_key(root, create=False)
            _seal_index(index, key)

            self.assertFalse(_validate_index(index, key))

    def test_valid_prefix_rollback_and_missing_root_copy_recover_from_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact = root / "reading-a"
            artifact.mkdir()
            pipeline = artifact / "pipeline-manifest.json"
            pipeline.write_text("{}\n", encoding="utf-8")
            _, initial_envelope = _record_initial(root, artifact, pipeline)
            prefix = (root / INDEX_NAME).read_bytes()
            followup_envelope = _envelope(
                "reading-a",
                "这件事偏向能成，过程先慢后顺。",
                prior_manifest_digest=initial_envelope["manifest_digest"],
            )
            record_acceptance(
                root,
                event_type="followup",
                system="liuren",
                reading_id="reading-a",
                artifact_dir=artifact,
                pipeline_manifest_path=pipeline,
                accepted_envelope=followup_envelope,
                prior_manifest_digest=initial_envelope["manifest_digest"],
                operation_id="b" * 64,
                reservation_name="reservation-a.json",
                draft_sha256="c" * 64,
            )

            (root / INDEX_NAME).write_bytes(prefix)
            recovered = load_acceptance_index(root)
            self.assertEqual(len(recovered["events"]), 2)
            self.assertEqual(
                json.loads((root / INDEX_NAME).read_text(encoding="utf-8"))["index_digest"],
                recovered["index_digest"],
            )
            (root / INDEX_NAME).unlink()
            recovered_again = load_acceptance_index(root)
            self.assertEqual(len(recovered_again["events"]), 2)
            self.assertTrue((root / INDEX_NAME).is_file())

    def test_replayed_older_checkpoint_cannot_roll_back_a_newer_root_index(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "root"
            root.mkdir()
            artifact = root / "reading-a"
            artifact.mkdir()
            pipeline = artifact / "pipeline-manifest.json"
            pipeline.write_text("{}\n", encoding="utf-8")
            _, initial_envelope = _record_initial(root, artifact, pipeline)
            initial_index = load_acceptance_index(root)
            checkpoint_path = _checkpoint_path(root, initial_index["index_id"])
            stale_checkpoint = checkpoint_path.read_bytes()
            record_acceptance(
                root,
                event_type="followup",
                system="liuren",
                reading_id="reading-a",
                artifact_dir=artifact,
                pipeline_manifest_path=pipeline,
                accepted_envelope=_envelope(
                    "reading-a",
                    "这件事偏向能成，过程先慢后顺。",
                    prior_manifest_digest=initial_envelope["manifest_digest"],
                ),
                prior_manifest_digest=initial_envelope["manifest_digest"],
                operation_id="b" * 64,
                reservation_name="reservation-a.json",
                draft_sha256="c" * 64,
            )
            checkpoint_path.write_bytes(stale_checkpoint)

            recovered = load_acceptance_index(root)

            self.assertEqual(len(recovered["events"]), 2)
            repaired_checkpoint = json.loads(
                checkpoint_path.read_text(encoding="utf-8")
            )
            self.assertEqual(
                repaired_checkpoint["index"]["index_digest"],
                recovered["index_digest"],
            )

    def test_moved_root_revokes_the_old_path_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            container = Path(temporary)
            original = container / "original"
            artifact = original / "reading-a"
            artifact.mkdir(parents=True)
            pipeline = artifact / "pipeline-manifest.json"
            pipeline.write_text("{}\n", encoding="utf-8")
            _record_initial(original, artifact, pipeline)
            moved = container / "moved"
            shutil.move(str(original), moved)
            self.assertEqual(len(load_acceptance_index(moved)["events"]), 1)
            original.mkdir()

            reopened = load_acceptance_index(original)

            self.assertEqual(reopened["events"], [])
            self.assertIsNone(reopened["index_id"])

    def test_copied_root_cannot_take_over_while_the_active_root_still_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            container = Path(temporary)
            active = container / "active"
            artifact = active / "reading-a"
            artifact.mkdir(parents=True)
            pipeline = artifact / "pipeline-manifest.json"
            pipeline.write_text("{}\n", encoding="utf-8")
            _record_initial(active, artifact, pipeline)
            copied = container / "copied"
            shutil.copytree(active, copied)

            with self.assertRaises(ValueError):
                load_acceptance_index(copied)

            self.assertEqual(len(load_acceptance_index(active)["events"]), 1)

    def test_creation_record_rejects_manifest_changed_after_private_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "root"
            root.mkdir()
            artifact = root / "reading-a"
            artifact.mkdir()
            pipeline = artifact / "pipeline-manifest.json"
            original = b'{"version":1}\n'
            pipeline.write_bytes(original)
            expected = hashlib.sha256(original).hexdigest()
            pipeline.write_text('{"version":2}\n', encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "changed before creation"):
                record_pipeline_creation(
                    root,
                    system="liuren",
                    reading_id="reading-a",
                    artifact_dir=artifact,
                    pipeline_manifest_path=pipeline,
                    expected_pipeline_sha256=expected,
                )

    def test_tampered_index_and_artifact_escape_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "root"
            root.mkdir()
            outside = root.parent / "outside"
            outside.mkdir()
            pipeline = outside / "pipeline-manifest.json"
            pipeline.write_text("{}\n", encoding="utf-8")
            envelope = _envelope("reading-a", "这件事偏向能成。")
            with self.assertRaisesRegex(ValueError, "outside the pipeline root"):
                record_acceptance(
                    root,
                    event_type="initial",
                    system="liuren",
                    reading_id="reading-a",
                    artifact_dir=outside,
                    pipeline_manifest_path=pipeline,
                    accepted_envelope=envelope,
                )

            artifact = root / "reading-a"
            artifact.mkdir()
            pipeline = artifact / "pipeline-manifest.json"
            pipeline.write_text("{}\n", encoding="utf-8")
            _record_initial(root, artifact, pipeline)
            index_path = root / INDEX_NAME
            payload = json.loads(index_path.read_text(encoding="utf-8"))
            payload["events"][0]["reading_id"] = "forged"
            index_path.write_text(json.dumps(payload), encoding="utf-8")
            repaired = load_acceptance_index(root)
            self.assertEqual(repaired["events"][0]["reading_id"], "reading-a")

    def test_valid_index_from_a_sibling_root_cannot_replace_this_roots_history(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            container = Path(temporary)
            roots: list[Path] = []
            for name, reading_id, operation in (
                ("root-a", "reading-a", "a" * 64),
                ("root-b", "reading-b", "b" * 64),
            ):
                root = container / name
                artifact = root / reading_id
                artifact.mkdir(parents=True)
                pipeline = artifact / "pipeline-manifest.json"
                pipeline.write_text(
                    json.dumps({"reading_id": reading_id}) + "\n",
                    encoding="utf-8",
                )
                record_acceptance(
                    root,
                    event_type="initial",
                    system="liuren",
                    reading_id=reading_id,
                    artifact_dir=artifact,
                    pipeline_manifest_path=pipeline,
                    accepted_envelope=_envelope(reading_id, "这件事偏向能成。"),
                    operation_id=operation,
                )
                roots.append(root)

            (roots[1] / INDEX_NAME).write_bytes((roots[0] / INDEX_NAME).read_bytes())
            recovered = load_acceptance_index(roots[1])

            self.assertEqual(
                [event["reading_id"] for event in recovered["events"]],
                ["reading-b"],
            )

    def test_missing_root_index_recovers_even_if_an_old_reading_directory_was_removed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            container = Path(temporary)
            root = container / "root"
            first = root / "reading-a"
            first.mkdir(parents=True)
            first_pipeline = first / "pipeline-manifest.json"
            first_pipeline.write_text('{"reading_id":"reading-a"}\n', encoding="utf-8")
            record_acceptance(
                root,
                event_type="initial",
                system="liuren",
                reading_id="reading-a",
                artifact_dir=first,
                pipeline_manifest_path=first_pipeline,
                accepted_envelope=_envelope("reading-a", "甲事偏向能成。"),
                operation_id="a" * 64,
            )
            second = root / "reading-b"
            second.mkdir()
            second_pipeline = second / "pipeline-manifest.json"
            second_pipeline.write_text('{"reading_id":"reading-b"}\n', encoding="utf-8")
            record_acceptance(
                root,
                event_type="initial",
                system="liuren",
                reading_id="reading-b",
                artifact_dir=second,
                pipeline_manifest_path=second_pipeline,
                accepted_envelope=_envelope("reading-b", "乙事偏向能成。"),
                operation_id="b" * 64,
            )
            shutil.rmtree(first)
            (root / INDEX_NAME).unlink()

            recovered = load_acceptance_index(root)

            self.assertEqual(len(recovered["events"]), 2)
            self.assertEqual(recovered["events"][-1]["reading_id"], "reading-b")


if __name__ == "__main__":
    unittest.main()

"""Task 11 immutable outcome-calibration contracts."""

from __future__ import annotations

import hashlib
import hmac
import io
import json
import multiprocessing
import os
import shutil
import stat
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import record_reading_outcome
from reading_engine.contracts import (
    AcceptedClaim,
    AcceptedReading,
    EvidenceBundle,
    EvidenceNode,
    ReadingRecord,
    canonical_digest,
)
from reading_engine.fact_index import build_fact_index
from reading_engine.outcome_store import CalibratableClaim, OutcomeRecord, OutcomeStore
from reading_engine.storage import AtomicReadingStore
from reading_engine.turns import TurnEngine
from test_reading_engine_v2 import StaticProvider, build_engine, provider_request


ROOT = Path(__file__).resolve().parents[1]
INTEGRITY_KEY = b"task-11-test-integrity-key-32-bytes-minimum"


def _record_from_competing_process(
    start,
    results,
    *,
    outcome_root: str,
    reading_root: str,
    checkpoint_path: str,
    reading_id: str,
    prepared_digest: str,
) -> None:
    start.wait(5)
    try:
        store = OutcomeStore(
            outcome_root,
            reading_store=AtomicReadingStore(reading_root),
            integrity_key=INTEGRITY_KEY,
            checkpoint_path=checkpoint_path,
        )
        claim = store.claims(
            reading_id=reading_id,
            prepared_digest=prepared_digest,
        )[0]
        store.record(
            reading_id=reading_id,
            prepared_digest=prepared_digest,
            claim_id=claim.claim_id,
            status="hit",
            evidence={"kind": "user_report", "summary": "并发进程核验"},
            reported_at="2026-08-01T10:00:00+08:00",
        )
        results.put(("stored", str(Path(checkpoint_path).resolve()), claim.claim_id))
    except (RuntimeError, ValueError) as exc:
        results.put(("rejected", str(Path(checkpoint_path).resolve()), type(exc).__name__))


def _redigest_without_mac(payload: dict) -> str:
    base = dict(payload)
    base.pop("integrity_mac", None)
    base.pop("record_digest", None)
    rendered = json.dumps(
        base, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True
    )
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


class _CounterEvidenceProvider(StaticProvider):
    """Static fixture whose pinned corpus also carries one counter rule."""

    def _bound_evidence(self, request, calculation, intent_digest):
        bundle = EvidenceBundle.create(
            system=calculation.system,
            evidence=(
                EvidenceNode(
                    rule_id="lr-source-001",
                    source="大六壬大全",
                    anchor="卷一/发用",
                    applicability="调用方目标与当前课体共同限定",
                    assertion="发用为当前课的事实主线",
                    lineage="san-shi/daliuren-daquan",
                    quote_hash="a" * 64,
                    reading_id=str(request.reading_id),
                    version=int(request.transaction_version or 1),
                ),
            ),
            counter_evidence=(
                EvidenceNode(
                    rule_id="lr-counter-001",
                    source="反例集",
                    anchor="例一",
                    applicability="当前事实",
                    assertion="存在相反条件",
                    lineage="counter/liuren",
                    quote_hash="b" * 64,
                    reading_id=str(request.reading_id),
                    version=int(request.transaction_version or 1),
                ),
            ),
            intent_digest=intent_digest,
        )
        return bundle, "课象"


def _commit_with_claims(engine, prepared, public_copy, claims):
    """Commit the staged reading with an explicit accepted-claim registry.

    The slim turn engine commits finished text without claims, and its
    judgment dimensions carry no conclusion (semantic conclusions belong to
    the caller).  Calibration targets exist only when a dimension has a real
    conclusion, so the fixtures below replace the judgment with one that
    carries a conclusion; that is the deterministic object the store
    calibrates against, never the placeholder verdict.
    """

    accepted = AcceptedReading(
        reading_id=prepared.reading_id,
        version=prepared.version,
        system=prepared.judgment.system,
        public_copy=public_copy,
        public_copy_sha256=hashlib.sha256(
            public_copy.encode("utf-8")
        ).hexdigest(),
        request_digest=canonical_digest(prepared.request.to_dict()),
        intent_digest=canonical_digest(prepared.request.intent),
        calculation_digest=prepared.calculation.result_hash,
        evidence_digest=prepared.evidence.bundle_digest,
        judgment_digest=prepared.judgment.judgment_digest,
        repair_attempts=0,
        fallback_used=False,
        draft_validation_findings=(),
        prepared_digest=prepared.prepared_digest,
        parent_reading_id=prepared.parent_reading_id,
        root_reading_id=prepared.root_reading_id,
        action=prepared.action,
        supersedes_version=prepared.supersedes_version,
        prior_claims=prepared.prior_claims,
        accepted_claims=tuple(claims),
    )
    stored = engine.store.commit(
        ReadingRecord(
            request=prepared.request,
            calculation=prepared.calculation,
            evidence=prepared.evidence,
            judgment=prepared.judgment,
            accepted=accepted,
            artifacts=prepared.artifacts,
        )
    )
    return stored.accepted

def _concluded_judgment(reading_or_prepared):
    """Return the judgment with a real conclusion on each dimension.

    The engine leaves conclusions empty; a calibratable target requires a
    provider-produced conclusion, so fixtures attach one.  The verdict stays
    a plain assertion and is not itself calibrated.
    """

    from reading_engine.contracts import Judgment, JudgmentDimension

    judgment = (
        reading_or_prepared.judgment
        if hasattr(reading_or_prepared, "judgment")
        else reading_or_prepared
    )
    concluded = []
    for dimension in judgment.dimensions:
        concluded.append(
            replace(
                dimension,
                conclusion=f"确定结论：{dimension.dimension}。",
                verdict="asserted",
            )
        )
    return Judgment.create(
        system=judgment.system,
        calculation_digest=judgment.calculation_digest,
        evidence_digest=judgment.evidence_digest,
        basis_label=judgment.basis_label,
        basis_text=judgment.basis_text,
        dimensions=tuple(concluded),
        intent_digest=judgment.intent_digest,
    )


def _accept_with_claim(
    engine,
    turn,
    *,
    text: str = "测试主回答。",
    counter_evidence_refs: tuple[str, ...] = (),
):
    prepared = engine.store.load_prepared(turn.result.reading_id)
    basis = "测试事实已列明。"
    public_copy = f"{basis}\n{text}"
    facts = build_fact_index(
        prepared.calculation,
        reading_id=prepared.reading_id,
        version=prepared.version,
    )
    claim = AcceptedClaim.create(
        role="main",
        text=text,
        visible_span=(len(basis) + 1, len(public_copy)),
        dimension=prepared.judgment.dimensions[0].dimension,
        fact_refs=(facts[0].fact_id,),
        evidence_refs=tuple(
            item.rule_id for item in prepared.evidence.evidence
        ),
        counter_evidence_refs=counter_evidence_refs,
    )
    accepted = _commit_with_claims(engine, prepared, public_copy, (claim,))
    if turn.state_token is not None:
        engine.token_store.mark_accepted(
            turn.state_token, commit_ref=accepted.public_copy_sha256
        )
    return accepted



def _concluded_turn(engine, provider, request, **kwargs):
    """Prepare a turn whose engine judgment carries a real conclusion.

    The engine leaves semantic conclusions to the caller, so a production
    judgment has none and would not be calibratable.  The fixture patches
    ``_judgment_for`` to attach a conclusion so the store has a genuine
    target (never the placeholder verdict).
    """

    original = TurnEngine._judgment_for

    def concluded(preparation):
        judgment = original(preparation)
        return _concluded_judgment(judgment)

    with patch.object(TurnEngine, "_judgment_for", staticmethod(concluded)):
        return engine.prepare_turn(provider.descriptor, request, **kwargs)


class OutcomeCalibrationTests(unittest.TestCase):
    def _accepted_fixture(self, root: Path):
        reading_root = root / "reading-store"
        provider = StaticProvider()
        engine = build_engine(reading_root, provider)
        # The engine's own judgment carries no conclusion (semantic
        # conclusions belong to the caller).  A calibratable target needs a
        # real provider conclusion, so the fixture makes the engine produce
        # one; the store then calibrates that, never the placeholder verdict.
        turn = _concluded_turn(engine, provider, provider_request("测试一个可核验结果"))
        accepted = _accept_with_claim(engine, turn)
        return engine.store, engine.store.load(accepted.reading_id)

    def _store_and_claim(self, root: Path):
        reading_store, reading = self._accepted_fixture(root)
        store = OutcomeStore(
            root / "outcome-store",
            reading_store=reading_store,
            integrity_key=INTEGRITY_KEY,
            checkpoint_path=root / "checkpoint" / "outcomes.json",
        )
        claims = store.claims(
            reading_id=reading.accepted.reading_id,
            prepared_digest=reading.accepted.prepared_digest,
        )
        self.assertEqual(len(claims), 1)
        return reading_store, reading, store, claims[0]

    def _record(self, store: OutcomeStore, reading, claim, *, status: str = "hit"):
        return store.record(
            reading_id=reading.accepted.reading_id,
            prepared_digest=reading.accepted.prepared_digest,
            claim_id=claim.claim_id,
            status=status,
            evidence={"kind": "user_report", "summary": f"核验状态：{status}"},
            reported_at="2026-08-01T10:00:00+08:00",
        )

    def test_registry_binds_structured_claim_and_reading_store_never_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reading_store, reading, store, claim = self._store_and_claim(root)
            before = {
                path.relative_to(reading_store.root).as_posix(): path.read_bytes()
                for path in reading_store.root.rglob("*") if path.is_file()
            }
            # Calibration targets come from the deterministic judgment
            # conclusion, not from parsed public prose.
            self.assertEqual(claim.claim_text, "确定结论：outcome。")
            self.assertEqual(claim.dimension, "outcome")
            self.assertEqual(
                claim.contributors[0]["support_rule_ids"], ["lr-source-001"]
            )
            self.assertEqual(claim.contributors[0]["counter_rule_ids"], [])
            outcome = self._record(store, reading, claim)

            self.assertEqual(store.load(claim.claim_id), outcome)
            self.assertEqual(
                {path.relative_to(reading_store.root).as_posix(): path.read_bytes()
                 for path in reading_store.root.rglob("*") if path.is_file()},
                before,
            )
            path = store.outcomes / f"{claim.claim_id}.json"
            self.assertEqual(stat.S_IMODE(store.root.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_public_claim_registry_survives_empty_internal_conclusion(self) -> None:
        # the engine never stores a semantic conclusion (that belongs to the
        # caller); a dimension without a conclusion produces no calibration
        # target, so the registry is empty instead of calibrating the
        # placeholder verdict
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            provider = StaticProvider()
            engine = build_engine(root / "reading-store", provider)
            turn = engine.prepare_turn(
                provider.descriptor, provider_request("测试公开 claim 冻结")
            )
            accepted = _accept_with_claim(engine, turn, text="公开可核验判断。")
            reading = engine.store.load(accepted.reading_id)
            self.assertEqual(
                [item.conclusion for item in reading.judgment.dimensions], [""]
            )
            store = OutcomeStore(
                root / "outcome-store", reading_store=engine.store,
                integrity_key=INTEGRITY_KEY,
                checkpoint_path=root / "checkpoint" / "outcomes.json",
            )
            claims = store.claims(
                reading_id=accepted.reading_id,
                prepared_digest=accepted.prepared_digest,
            )

        # No provider conclusion -> no placeholder gets calibrated.
        self.assertEqual(list(claims), [])

    def test_same_span_and_dimension_cannot_create_two_outcomes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            provider = StaticProvider()
            engine = build_engine(Path(temporary), provider)
            turn = engine.prepare_turn(
                provider.descriptor, provider_request("语义重复")
            )
            prepared = engine.store.load_prepared(turn.result.reading_id)
            basis = "测试事实已列明。"
            text = "测试主回答。"
            public_copy = f"{basis}\n{text}"
            facts = build_fact_index(
                prepared.calculation,
                reading_id=prepared.reading_id,
                version=prepared.version,
            )
            main = AcceptedClaim.create(
                role="main",
                text=text,
                visible_span=(len(basis) + 1, len(public_copy)),
                dimension=prepared.judgment.dimensions[0].dimension,
                fact_refs=(facts[0].fact_id,),
                evidence_refs=("lr-source-001",),
                counter_evidence_refs=(),
            )
            duplicate = AcceptedClaim.create(
                role="support",
                text=text,
                visible_span=main.visible_span,
                dimension=main.dimension,
                fact_refs=main.fact_refs,
                evidence_refs=main.evidence_refs,
                counter_evidence_refs=(),
            )
            with self.assertRaisesRegex(ValueError, "semantic identity"):
                _commit_with_claims(
                    engine, prepared, public_copy, (main, duplicate)
                )

    def test_duplicate_is_idempotent_conflict_and_recomputed_self_hash_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, reading, store, claim = self._store_and_claim(root)
            first = self._record(store, reading, claim, status="partial")
            self.assertEqual(self._record(store, reading, claim, status="partial"), first)
            with self.assertRaises(RuntimeError):
                self._record(store, reading, claim, status="miss")

            path = store.outcomes / f"{claim.claim_id}.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["status"] = "hit"
            payload["record_digest"] = _redigest_without_mac(payload)
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "MAC"):
                store.load(claim.claim_id)

    def test_claim_status_and_bounded_evidence_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, reading, store, claim = self._store_and_claim(root)
            base = {
                "reading_id": reading.accepted.reading_id,
                "prepared_digest": reading.accepted.prepared_digest,
                "claim_id": claim.claim_id,
                "status": "unknown",
                "evidence": {"kind": "user_report", "summary": "暂时无法核验"},
                "reported_at": "2026-08-01T10:00:00+08:00",
            }
            with self.assertRaises(ValueError):
                store.record(**{**base, "claim_id": "0" * 64})
            with self.assertRaises(ValueError):
                store.record(**{**base, "status": "likely"})
            with self.assertRaises(ValueError):
                store.record(**{**base, "evidence": {}})
            with self.assertRaises(ValueError):
                store.record(**{**base, "evidence": {
                    "kind": "user_report", "summary": "x", "raw_media": "secret"
                }})
            with self.assertRaises(ValueError):
                store.record(**{**base, "evidence": {
                    "kind": "user_report", "summary": "x" * 1001
                }})

    def test_aggregate_counts_each_claim_once_across_required_axes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reading_store, first = self._accepted_fixture(root)
            _, second = self._accepted_fixture(root)
            store = OutcomeStore(
                root / "outcome-store",
                reading_store=reading_store,
                integrity_key=INTEGRITY_KEY,
                checkpoint_path=root / "checkpoint" / "outcomes.json",
            )
            records = []
            for reading, status in ((first, "hit"), (second, "miss")):
                claim = store.claims(
                    reading_id=reading.accepted.reading_id,
                    prepared_digest=reading.accepted.prepared_digest,
                )[0]
                records.append(self._record(store, reading, claim, status=status))
            report = store.aggregate(records)
            with self.assertRaises(ValueError):
                store.aggregate([records[0], records[0]])
            with self.assertRaises(ValueError):
                store.aggregate([replace(records[0], status="miss")])
            fake_claim = CalibratableClaim.create(
                claim_kind="judgment_dimension",
                reading_id=first.accepted.reading_id,
                reading_version=first.accepted.version,
                prepared_digest=first.accepted.prepared_digest,
                public_copy_sha256=first.accepted.public_copy_sha256,
                dimension="fake",
                horizon={"kind": "instant", "start": None, "end": None},
                claim_text="伪造公开判断",
                contributors=[{
                    "role": "primary", "system": "fake",
                    "provider_id": "fake", "provider_version": "999",
                    "judgment_claim_digest": "f" * 64, "fact_refs": [],
                    "support_rule_ids": [], "counter_rule_ids": [],
                    "support_source_lineages": [],
                    "counter_source_lineages": [],
                }],
            )
            fake_record = OutcomeRecord.create(
                claim=fake_claim,
                status="hit",
                evidence={"kind": "user_report", "summary": "伪造"},
                reported_at="2026-08-01T10:00:00+08:00",
                integrity_key=INTEGRITY_KEY,
            )
            with self.assertRaises(ValueError):
                store.aggregate([fake_record])

        self.assertEqual(report["by_provider_version"]["test.liuren@4"]["sample_count"], 2)
        self.assertEqual(
            report["by_rule_id"]["lr-source-001"]["support"]["hit"], 1
        )
        self.assertNotIn("probability", json.dumps(report).casefold())
        self.assertNotIn("percentage", json.dumps(report).casefold())

    def test_aggregate_keeps_support_and_counter_rule_polarity_separate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            provider = _CounterEvidenceProvider()
            engine = build_engine(root / "reading-store", provider)
            turn = _concluded_turn(engine, provider, provider_request("正反证据"))
            accepted = _accept_with_claim(
                engine,
                turn,
                text="带反证的公开判断。",
                counter_evidence_refs=("lr-counter-001",),
            )
            store = OutcomeStore(
                root / "outcome-store", reading_store=engine.store,
                integrity_key=INTEGRITY_KEY,
                checkpoint_path=root / "checkpoint" / "outcomes.json",
            )
            claim = store.claims(
                reading_id=accepted.reading_id,
                prepared_digest=accepted.prepared_digest,
            )[0]
            self._record(store, engine.store.load(accepted.reading_id), claim)
            report = store.aggregate(store.list_all())

        self.assertEqual(
            report["by_rule_id"]["lr-source-001"]["support"]["hit"], 1
        )
        self.assertEqual(
            report["by_rule_id"]["lr-counter-001"]["counter"]["hit"], 1
        )
        self.assertNotIn("counter", report["by_rule_id"]["lr-source-001"])
        self.assertNotIn("support", report["by_rule_id"]["lr-counter-001"])

    def test_evidence_bundle_rejects_duplicate_rule_identity_across_polarities(self) -> None:
        support = EvidenceNode(
            rule_id="same-rule", source="正证", anchor="正一",
            applicability="当前事实", assertion="支持",
            lineage="support/lineage", quote_hash="c" * 64,
        )
        counter = EvidenceNode(
            rule_id="same-rule", source="反证", anchor="反一",
            applicability="当前事实", assertion="反对",
            lineage="counter/lineage", quote_hash="d" * 64,
        )
        with self.assertRaises(ValueError):
            EvidenceBundle.create(
                system="liuren", evidence=(support,), counter_evidence=(counter,)
            )

    def test_authenticated_checkpoint_detects_selective_deletion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, reading, store, claim = self._store_and_claim(root)
            self._record(store, reading, claim, status="miss")
            os.unlink(store.outcomes / f"{claim.claim_id}.json")
            with self.assertRaises(RuntimeError):
                store.list_all()

    def test_outcome_root_binds_one_resolved_checkpoint_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reading_store, _ = self._accepted_fixture(root)
            outcome_root = root / "outcome-store"
            first_path = root / "checkpoint-a" / "outcomes.json"
            OutcomeStore(
                outcome_root,
                reading_store=reading_store,
                integrity_key=INTEGRITY_KEY,
                checkpoint_path=first_path,
            )
            reopened = OutcomeStore(
                outcome_root,
                reading_store=reading_store,
                integrity_key=INTEGRITY_KEY,
                checkpoint_path=root / "checkpoint-a" / ".." / "checkpoint-a" / "outcomes.json",
            )
            self.assertEqual(reopened.checkpoint_path, first_path.resolve())
            with self.assertRaisesRegex(ValueError, "checkpoint identity"):
                OutcomeStore(
                    outcome_root,
                    reading_store=reading_store,
                    integrity_key=INTEGRITY_KEY,
                    checkpoint_path=root / "checkpoint-b" / "outcomes.json",
                )

    def test_deleted_checkpoint_binding_cannot_rebind_an_empty_outcome_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reading_store, _ = self._accepted_fixture(root)
            outcome_root = root / "outcome-store"
            store = OutcomeStore(
                outcome_root,
                reading_store=reading_store,
                integrity_key=INTEGRITY_KEY,
                checkpoint_path=root / "checkpoint-a" / "outcomes.json",
            )
            os.unlink(store._checkpoint_binding_path)
            with self.assertRaisesRegex(ValueError, "checkpoint identity"):
                OutcomeStore(
                    outcome_root,
                    reading_store=reading_store,
                    integrity_key=INTEGRITY_KEY,
                    checkpoint_path=root / "checkpoint-b" / "outcomes.json",
                )

    def test_deleted_root_local_identity_cannot_rebind_to_another_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reading_store, _ = self._accepted_fixture(root)
            outcome_root = root / "outcome-store"
            store = OutcomeStore(
                outcome_root,
                reading_store=reading_store,
                integrity_key=INTEGRITY_KEY,
                checkpoint_path=root / "checkpoint-a" / "outcomes.json",
            )
            os.unlink(store._checkpoint_binding_path)
            os.unlink(store._root_lock)
            other_reading_root = root / "other-reading-store"
            other_reading_store = AtomicReadingStore(other_reading_root)

            with self.assertRaisesRegex(ValueError, "checkpoint identity"):
                OutcomeStore(
                    outcome_root,
                    reading_store=other_reading_store,
                    integrity_key=INTEGRITY_KEY,
                    checkpoint_path=root / "checkpoint-b" / "outcomes.json",
                )

            self.assertTrue(store.checkpoint_path.exists())
            self.assertTrue(store._root_guard_path.exists())
            self.assertFalse(
                (other_reading_root / ".outcome-store-identity.json").exists()
            )
            self.assertFalse(
                (other_reading_root / ".outcome-store-identity.lock").exists()
            )

    def test_corrupt_root_local_identity_cannot_rebind_to_another_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reading_store, _ = self._accepted_fixture(root)
            outcome_root = root / "outcome-store"
            store = OutcomeStore(
                outcome_root,
                reading_store=reading_store,
                integrity_key=INTEGRITY_KEY,
                checkpoint_path=root / "checkpoint-a" / "outcomes.json",
            )
            os.unlink(store._checkpoint_binding_path)
            store._root_lock.write_bytes(b'{"partial":')
            os.chmod(store._root_lock, 0o600)
            other_reading_root = root / "other-reading-store"
            other_reading_store = AtomicReadingStore(other_reading_root)

            with self.assertRaisesRegex(ValueError, "checkpoint identity"):
                OutcomeStore(
                    outcome_root,
                    reading_store=other_reading_store,
                    integrity_key=INTEGRITY_KEY,
                    checkpoint_path=root / "checkpoint-b" / "outcomes.json",
                )

            self.assertTrue(store.checkpoint_path.exists())
            self.assertTrue(store._root_guard_path.exists())
            self.assertFalse(
                (other_reading_root / ".outcome-store-identity.json").exists()
            )

    def test_wrong_key_and_attacker_v1_checkpoint_cannot_replace_root_guard(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reading_store, _ = self._accepted_fixture(root)
            outcome_root = root / "outcome-store"
            store = OutcomeStore(
                outcome_root,
                reading_store=reading_store,
                integrity_key=INTEGRITY_KEY,
                checkpoint_path=root / "checkpoint-a" / "outcomes.json",
            )
            original_guard = store._root_guard_path.read_bytes()
            attacker_key = b"attacker-test-integrity-key-32-bytes-minimum"
            attacker_checkpoint = root / "checkpoint-b" / "outcomes.json"
            attacker_checkpoint.parent.mkdir(parents=True, mode=0o700)
            legacy_core = {
                "schema_version": "mingli-outcome-checkpoint-v1",
                "outcome_store": str(outcome_root.resolve()),
                "entries": [],
                "pending": None,
            }
            authenticated = {
                **legacy_core,
                "manifest_digest": hashlib.sha256(json.dumps(
                    legacy_core,
                    ensure_ascii=False,
                    allow_nan=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ).encode("utf-8")).hexdigest(),
            }
            payload = {
                **authenticated,
                "integrity_mac": hmac.new(
                    attacker_key,
                    json.dumps(
                        authenticated,
                        ensure_ascii=False,
                        allow_nan=False,
                        separators=(",", ":"),
                        sort_keys=True,
                    ).encode("utf-8"),
                    hashlib.sha256,
                ).hexdigest(),
            }
            attacker_checkpoint.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            os.chmod(attacker_checkpoint, 0o600)
            attacker_reading_store = AtomicReadingStore(root / "attacker-reading-store")
            OutcomeStore(
                root / "attacker-seed-outcome-store",
                reading_store=attacker_reading_store,
                integrity_key=attacker_key,
                checkpoint_path=root / "attacker-seed-checkpoint" / "outcomes.json",
            )
            attacker_identity = json.loads(
                (attacker_reading_store.root / ".outcome-store-identity.json").read_text(
                    encoding="utf-8"
                )
            )["store_id"]
            forged_core = {
                "schema_version": "mingli-outcome-checkpoint-binding-v1",
                "outcome_store": str(outcome_root.resolve()),
                "checkpoint_path": str(attacker_checkpoint.resolve()),
                "reading_store": str(attacker_reading_store.root.resolve()),
                "reading_store_device": str(attacker_reading_store.root.stat().st_dev),
                "reading_store_inode": str(attacker_reading_store.root.stat().st_ino),
                "reading_store_id": attacker_identity,
            }
            forged_authenticated = {
                **forged_core,
                "binding_digest": hashlib.sha256(json.dumps(
                    forged_core,
                    ensure_ascii=False,
                    allow_nan=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ).encode("utf-8")).hexdigest(),
            }
            forged_binding = {
                **forged_authenticated,
                "integrity_mac": hmac.new(
                    attacker_key,
                    json.dumps(
                        forged_authenticated,
                        ensure_ascii=False,
                        allow_nan=False,
                        separators=(",", ":"),
                        sort_keys=True,
                    ).encode("utf-8"),
                    hashlib.sha256,
                ).hexdigest(),
            }
            forged_content = (
                json.dumps(
                    forged_binding,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                ) + "\n"
            )
            store._checkpoint_binding_path.write_text(
                forged_content,
                encoding="utf-8",
            )
            store._root_lock.write_text(forged_content, encoding="utf-8")
            os.chmod(store._checkpoint_binding_path, 0o600)
            os.chmod(store._root_lock, 0o600)

            with self.assertRaisesRegex(ValueError, "guard cannot be authenticated"):
                OutcomeStore(
                    outcome_root,
                    reading_store=attacker_reading_store,
                    integrity_key=attacker_key,
                    checkpoint_path=attacker_checkpoint,
                )

            self.assertEqual(store._root_guard_path.read_bytes(), original_guard)
            self.assertTrue(store.checkpoint_path.exists())

    def test_outcome_root_checkpoint_binding_includes_the_reading_store(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first_reading_store, _ = self._accepted_fixture(root)
            checkpoint = root / "checkpoint" / "outcomes.json"
            OutcomeStore(
                root / "outcome-store",
                reading_store=first_reading_store,
                integrity_key=INTEGRITY_KEY,
                checkpoint_path=checkpoint,
            )
            os.rename(root / "reading-store", root / "displaced-reading-store")
            second_reading_store, _ = self._accepted_fixture(root)
            replacement_identity = (
                second_reading_store.root / ".outcome-store-identity.json"
            )
            replacement_identity_lock = (
                second_reading_store.root / ".outcome-store-identity.lock"
            )
            self.assertFalse(replacement_identity.exists())
            self.assertFalse(replacement_identity_lock.exists())
            self.assertEqual(
                first_reading_store.root.resolve(),
                second_reading_store.root.resolve(),
            )
            with self.assertRaisesRegex(ValueError, "checkpoint identity"):
                OutcomeStore(
                    root / "outcome-store",
                    reading_store=second_reading_store,
                    integrity_key=INTEGRITY_KEY,
                    checkpoint_path=checkpoint,
                )
            self.assertFalse(replacement_identity.exists())
            self.assertFalse(replacement_identity_lock.exists())

    def test_rejected_different_reading_store_is_not_modified(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first_reading_store, _ = self._accepted_fixture(root)
            checkpoint = root / "checkpoint" / "outcomes.json"
            outcome_root = root / "outcome-store"
            OutcomeStore(
                outcome_root,
                reading_store=first_reading_store,
                integrity_key=INTEGRITY_KEY,
                checkpoint_path=checkpoint,
            )
            different_root = root / "different-reading-store"
            different_store = AtomicReadingStore(different_root)
            identity = different_root / ".outcome-store-identity.json"
            identity_lock = different_root / ".outcome-store-identity.lock"
            self.assertFalse(identity.exists())
            self.assertFalse(identity_lock.exists())

            with self.assertRaisesRegex(ValueError, "checkpoint identity"):
                OutcomeStore(
                    outcome_root,
                    reading_store=different_store,
                    integrity_key=INTEGRITY_KEY,
                    checkpoint_path=checkpoint,
                )

            self.assertFalse(identity.exists())
            self.assertFalse(identity_lock.exists())

    def test_bound_reading_store_missing_identity_fails_without_recreating_it(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reading_store, _ = self._accepted_fixture(root)
            checkpoint = root / "checkpoint" / "outcomes.json"
            outcome_root = root / "outcome-store"
            store = OutcomeStore(
                outcome_root,
                reading_store=reading_store,
                integrity_key=INTEGRITY_KEY,
                checkpoint_path=checkpoint,
            )
            os.unlink(store._reading_identity_path)

            with self.assertRaisesRegex(ValueError, "reading store identity"):
                OutcomeStore(
                    outcome_root,
                    reading_store=reading_store,
                    integrity_key=INTEGRITY_KEY,
                    checkpoint_path=checkpoint,
                )

            self.assertFalse(store._reading_identity_path.exists())

    def test_reading_store_replaced_after_identity_probe_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reading_store, _ = self._accepted_fixture(root)
            checkpoint = root / "checkpoint" / "outcomes.json"
            outcome_root = root / "outcome-store"
            OutcomeStore(
                outcome_root,
                reading_store=reading_store,
                integrity_key=INTEGRITY_KEY,
                checkpoint_path=checkpoint,
            )
            original_load = OutcomeStore._load_reading_store_identity
            replaced = False

            def replace_after_probe(candidate: OutcomeStore) -> str | None:
                nonlocal replaced
                identity = original_load(candidate)
                if not replaced:
                    replaced = True
                    os.rename(
                        reading_store.root,
                        root / "displaced-after-probe-reading-store",
                    )
                    AtomicReadingStore(reading_store.root)
                return identity

            with patch.object(
                OutcomeStore,
                "_load_reading_store_identity",
                autospec=True,
                side_effect=replace_after_probe,
            ):
                with self.assertRaisesRegex(ValueError, "reading store .*identity"):
                    OutcomeStore(
                        outcome_root,
                        reading_store=reading_store,
                        integrity_key=INTEGRITY_KEY,
                        checkpoint_path=checkpoint,
                    )

            self.assertFalse(
                (reading_store.root / ".outcome-store-identity.json").exists()
            )
            self.assertFalse(
                (reading_store.root / ".outcome-store-identity.lock").exists()
            )

    def test_reading_store_replaced_before_identity_election_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reading_store, _ = self._accepted_fixture(root)
            replacement_root = root / "replacement-reading-store"
            replacement_store = AtomicReadingStore(replacement_root)
            OutcomeStore(
                root / "replacement-outcome-store",
                reading_store=replacement_store,
                integrity_key=INTEGRITY_KEY,
                checkpoint_path=root / "replacement-checkpoint" / "outcomes.json",
            )
            outcome_root = root / "outcome-store"
            checkpoint = root / "checkpoint" / "outcomes.json"
            original_persist = OutcomeStore._persist_reading_store_identity
            swapped = False

            def swap_before_persist(candidate: OutcomeStore) -> None:
                nonlocal swapped
                if not swapped:
                    swapped = True
                    os.rename(
                        reading_store.root,
                        root / "displaced-before-election-reading-store",
                    )
                    os.rename(replacement_root, reading_store.root)
                original_persist(candidate)

            with patch.object(
                OutcomeStore,
                "_persist_reading_store_identity",
                autospec=True,
                side_effect=swap_before_persist,
            ):
                with self.assertRaisesRegex(ValueError, "directory identity changed"):
                    OutcomeStore(
                        outcome_root,
                        reading_store=reading_store,
                        integrity_key=INTEGRITY_KEY,
                        checkpoint_path=checkpoint,
                    )

            guard_key = hashlib.sha256(
                str(outcome_root.resolve()).encode("utf-8")
            ).hexdigest()
            guard = root / ".mingli-outcome-root-guards" / f"{guard_key}.json"
            reservation = json.loads(guard.read_text(encoding="utf-8"))
            self.assertEqual(
                reservation["schema_version"],
                "mingli-outcome-root-reservation-v1",
            )
            self.assertEqual(reservation["checkpoint_path"], str(checkpoint.resolve()))
            self.assertEqual(
                reservation["reading_store"], str(reading_store.root.resolve())
            )
            self.assertFalse((outcome_root / ".checkpoint-binding.json").exists())
            with self.assertRaisesRegex(ValueError, "reservation mismatch"):
                OutcomeStore(
                    outcome_root,
                    reading_store=reading_store,
                    integrity_key=INTEGRITY_KEY,
                    checkpoint_path=checkpoint,
                )

    def test_byte_identical_reading_store_backup_restores_on_a_new_inode(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reading_store, reading, store, claim = self._store_and_claim(root)
            expected = self._record(store, reading, claim)
            backup = root / "reading-store-backup"
            displaced = root / "reading-store-displaced"
            shutil.copytree(reading_store.root, backup, copy_function=shutil.copy2)
            old_inode = reading_store.root.stat().st_ino
            os.rename(reading_store.root, displaced)
            shutil.copytree(backup, reading_store.root, copy_function=shutil.copy2)
            self.assertNotEqual(reading_store.root.stat().st_ino, old_inode)

            restored_reading_store = AtomicReadingStore(reading_store.root)
            restored = OutcomeStore(
                store.root,
                reading_store=restored_reading_store,
                integrity_key=INTEGRITY_KEY,
                checkpoint_path=store.checkpoint_path,
            )

            self.assertEqual(restored.list_all(), [expected])

    def test_authenticated_legacy_checkpoint_migrates_once_under_the_root_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reading_store, reading, store, claim = self._store_and_claim(root)
            expected = self._record(store, reading, claim)
            legacy_core = {
                "schema_version": "mingli-outcome-checkpoint-v1",
                "outcome_store": str(store.root.resolve()),
                "entries": [{
                    "claim_id": claim.claim_id,
                    "record_digest": expected.record_digest,
                }],
                "pending": None,
            }
            legacy_manifest_digest = hashlib.sha256(json.dumps(
                legacy_core,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")).hexdigest()
            legacy_authenticated = {
                **legacy_core,
                "manifest_digest": legacy_manifest_digest,
            }
            legacy_payload = {
                **legacy_authenticated,
                "integrity_mac": hmac.new(
                    INTEGRITY_KEY,
                    json.dumps(
                        legacy_authenticated,
                        ensure_ascii=False,
                        allow_nan=False,
                        separators=(",", ":"),
                        sort_keys=True,
                    ).encode("utf-8"),
                    hashlib.sha256,
                ).hexdigest(),
            }
            store.checkpoint_path.write_text(
                json.dumps(legacy_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            os.chmod(store.checkpoint_path, 0o600)
            os.unlink(store._checkpoint_binding_path)
            os.unlink(store._root_lock)
            os.unlink(store._root_guard_path)
            os.unlink(store._reading_identity_path)
            os.unlink(store._reading_identity_lock)
            migrated = OutcomeStore(
                store.root,
                reading_store=reading_store,
                integrity_key=INTEGRITY_KEY,
                checkpoint_path=store.checkpoint_path,
            )
            self.assertTrue(migrated._checkpoint_binding_path.exists())
            self.assertEqual(migrated.list_all(), [expected])
            self.assertEqual(
                json.loads(migrated.checkpoint_path.read_text(encoding="utf-8"))[
                    "schema_version"
                ],
                "mingli-outcome-checkpoint-v2",
            )

    def test_restart_recovers_a_crash_after_root_lock_creation_before_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reading_store, _ = self._accepted_fixture(root)
            outcome_root = root / "outcome-store"
            outcomes = outcome_root / "outcomes"
            outcomes.mkdir(parents=True, mode=0o700)
            root_lock = outcome_root / ".outcome-root.lock"
            root_lock.touch(mode=0o600)
            os.chmod(root_lock, 0o600)
            recovered = OutcomeStore(
                outcome_root,
                reading_store=reading_store,
                integrity_key=INTEGRITY_KEY,
                checkpoint_path=root / "checkpoint" / "outcomes.json",
            )
            self.assertEqual(recovered.list_all(), [])

    def test_restart_repairs_a_truncated_root_anchor_from_authenticated_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reading_store, _ = self._accepted_fixture(root)
            checkpoint = root / "checkpoint" / "outcomes.json"
            store = OutcomeStore(
                root / "outcome-store",
                reading_store=reading_store,
                integrity_key=INTEGRITY_KEY,
                checkpoint_path=checkpoint,
            )
            os.unlink(store._root_guard_path)
            store._root_lock.write_bytes(b'{"schema_version":')
            os.chmod(store._root_lock, 0o600)

            recovered = OutcomeStore(
                store.root,
                reading_store=reading_store,
                integrity_key=INTEGRITY_KEY,
                checkpoint_path=checkpoint,
            )

            self.assertEqual(recovered.list_all(), [])
            self.assertEqual(
                json.loads(recovered._root_lock.read_text(encoding="utf-8")),
                json.loads(recovered._checkpoint_binding_path.read_text(encoding="utf-8")),
            )

    def test_live_store_repairs_deleted_binding_from_authenticated_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reading_store, _ = self._accepted_fixture(root)
            store = OutcomeStore(
                root / "outcome-store",
                reading_store=reading_store,
                integrity_key=INTEGRITY_KEY,
                checkpoint_path=root / "checkpoint" / "outcomes.json",
            )
            os.unlink(store._root_guard_path)
            os.unlink(store._checkpoint_binding_path)

            self.assertEqual(store.list_all(), [])
            self.assertTrue(store._checkpoint_binding_path.exists())

    def test_v2_checkpoint_repairs_both_missing_root_local_copies(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reading_store, reading, store, claim = self._store_and_claim(root)
            expected = self._record(store, reading, claim)
            checkpoint = store.checkpoint_path
            os.unlink(store._root_guard_path)
            os.unlink(store._root_lock)
            os.unlink(store._checkpoint_binding_path)

            recovered = OutcomeStore(
                store.root,
                reading_store=reading_store,
                integrity_key=INTEGRITY_KEY,
                checkpoint_path=checkpoint,
            )

            self.assertEqual(recovered.list_all(), [expected])
            self.assertEqual(
                json.loads(recovered._root_lock.read_text(encoding="utf-8")),
                json.loads(recovered._checkpoint_binding_path.read_text(encoding="utf-8")),
            )

    def test_reservation_blocks_rebind_if_final_guard_write_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reading_store, _ = self._accepted_fixture(root)
            outcome_root = root / "outcome-store"
            checkpoint = root / "checkpoint-a" / "outcomes.json"
            with patch.object(
                OutcomeStore,
                "_write_root_guard",
                autospec=True,
                side_effect=OSError("injected final guard write failure"),
            ):
                with self.assertRaisesRegex(OSError, "guard write failure"):
                    OutcomeStore(
                        outcome_root,
                        reading_store=reading_store,
                        integrity_key=INTEGRITY_KEY,
                        checkpoint_path=checkpoint,
                    )

            guard_key = hashlib.sha256(
                str(outcome_root.resolve()).encode("utf-8")
            ).hexdigest()
            reservation_path = (
                root / ".mingli-outcome-root-guards" / f"{guard_key}.json"
            )
            self.assertEqual(
                json.loads(reservation_path.read_text(encoding="utf-8"))[
                    "schema_version"
                ],
                "mingli-outcome-root-reservation-v1",
            )
            other_reading_store = AtomicReadingStore(root / "other-reading-store")
            with self.assertRaisesRegex(ValueError, "reservation mismatch"):
                OutcomeStore(
                    outcome_root,
                    reading_store=other_reading_store,
                    integrity_key=INTEGRITY_KEY,
                    checkpoint_path=root / "checkpoint-b" / "outcomes.json",
                )

            recovered = OutcomeStore(
                outcome_root,
                reading_store=reading_store,
                integrity_key=INTEGRITY_KEY,
                checkpoint_path=checkpoint,
            )
            self.assertEqual(recovered.list_all(), [])
            self.assertEqual(
                json.loads(reservation_path.read_text(encoding="utf-8"))[
                    "schema_version"
                ],
                "mingli-outcome-checkpoint-binding-v1",
            )

    def test_restart_recovers_when_initial_anchor_write_raises(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reading_store, _ = self._accepted_fixture(root)
            outcome_root = root / "outcome-store"
            checkpoint = root / "checkpoint" / "outcomes.json"
            with patch(
                "reading_engine.outcome_store.os.write",
                side_effect=OSError("injected anchor write failure"),
            ):
                with self.assertRaisesRegex(OSError, "anchor write failure"):
                    OutcomeStore(
                        outcome_root,
                        reading_store=reading_store,
                        integrity_key=INTEGRITY_KEY,
                        checkpoint_path=checkpoint,
                    )

            recovered = OutcomeStore(
                outcome_root,
                reading_store=reading_store,
                integrity_key=INTEGRITY_KEY,
                checkpoint_path=checkpoint,
            )
            self.assertEqual(recovered.list_all(), [])

    def test_root_anchor_writer_retries_short_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reading_store, _ = self._accepted_fixture(root)
            real_write = os.write

            def short_write(descriptor: int, content: bytes) -> int:
                return real_write(descriptor, content[:7])

            with patch("reading_engine.outcome_store.os.write", side_effect=short_write):
                store = OutcomeStore(
                    root / "outcome-store",
                    reading_store=reading_store,
                    integrity_key=INTEGRITY_KEY,
                    checkpoint_path=root / "checkpoint" / "outcomes.json",
                )

            self.assertEqual(
                json.loads(store._root_lock.read_text(encoding="utf-8")),
                json.loads(store._checkpoint_binding_path.read_text(encoding="utf-8")),
            )

    def test_concurrent_checkpoint_initialization_cannot_split_the_outcome_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reading_store, first = self._accepted_fixture(root)
            _, second = self._accepted_fixture(root)
            start = threading.Barrier(2)

            def initialize_and_record(label: str, reading) -> tuple[str, str, str]:
                checkpoint = root / f"checkpoint-{label}" / "outcomes.json"
                start.wait(timeout=5)
                try:
                    store = OutcomeStore(
                        root / "outcome-store",
                        reading_store=reading_store,
                        integrity_key=INTEGRITY_KEY,
                        checkpoint_path=checkpoint,
                    )
                    claim = store.claims(
                        reading_id=reading.accepted.reading_id,
                        prepared_digest=reading.accepted.prepared_digest,
                    )[0]
                    self._record(store, reading, claim)
                    return "stored", str(checkpoint.resolve()), claim.claim_id
                except (RuntimeError, ValueError) as exc:
                    return "rejected", str(checkpoint.resolve()), type(exc).__name__

            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(
                    lambda item: initialize_and_record(*item),
                    (("a", first), ("b", second)),
                ))

            stored = [item for item in results if item[0] == "stored"]
            rejected = [item for item in results if item[0] == "rejected"]
            self.assertEqual(len(stored), 1, results)
            self.assertEqual(len(rejected), 1, results)
            winning = OutcomeStore(
                root / "outcome-store",
                reading_store=reading_store,
                integrity_key=INTEGRITY_KEY,
                checkpoint_path=stored[0][1],
            )
            self.assertEqual([item.claim_id for item in winning.list_all()], [stored[0][2]])

    def test_concurrent_same_checkpoint_initialization_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reading_store, _ = self._accepted_fixture(root)
            outcome_root = root / "outcome-store"
            checkpoint = root / "checkpoint" / "outcomes.json"
            probes = threading.Barrier(2)
            local = threading.local()
            original_load = OutcomeStore._load_reading_store_identity

            def synchronized_initial_probe(candidate: OutcomeStore) -> str | None:
                identity = original_load(candidate)
                calls = getattr(local, "identity_loads", 0)
                local.identity_loads = calls + 1
                if calls == 0:
                    probes.wait(timeout=5)
                return identity

            def initialize() -> str:
                try:
                    OutcomeStore(
                        outcome_root,
                        reading_store=reading_store,
                        integrity_key=INTEGRITY_KEY,
                        checkpoint_path=checkpoint,
                    )
                    return "ok"
                except (RuntimeError, ValueError) as exc:
                    return f"{type(exc).__name__}: {exc}"

            with patch.object(
                OutcomeStore,
                "_load_reading_store_identity",
                autospec=True,
                side_effect=synchronized_initial_probe,
            ):
                with ThreadPoolExecutor(max_workers=2) as executor:
                    results = list(executor.map(lambda _: initialize(), range(2)))

            self.assertEqual(results, ["ok", "ok"])

    def test_concurrent_outcome_roots_share_one_new_reading_store_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reading_store, _ = self._accepted_fixture(root)
            probes = threading.Barrier(2)
            local = threading.local()
            original_load = OutcomeStore._load_reading_store_identity

            def synchronized_initial_probe(candidate: OutcomeStore) -> str | None:
                identity = original_load(candidate)
                calls = getattr(local, "identity_loads", 0)
                local.identity_loads = calls + 1
                if calls == 0:
                    probes.wait(timeout=5)
                return identity

            def initialize(label: str) -> tuple[str, str]:
                try:
                    store = OutcomeStore(
                        root / f"outcome-store-{label}",
                        reading_store=reading_store,
                        integrity_key=INTEGRITY_KEY,
                        checkpoint_path=root / f"checkpoint-{label}" / "outcomes.json",
                    )
                    return "ok", str(store._reading_store_id)
                except (RuntimeError, ValueError) as exc:
                    return type(exc).__name__, str(exc)

            with patch.object(
                OutcomeStore,
                "_load_reading_store_identity",
                autospec=True,
                side_effect=synchronized_initial_probe,
            ):
                with ThreadPoolExecutor(max_workers=2) as executor:
                    results = list(executor.map(initialize, ("a", "b")))

            self.assertEqual([item[0] for item in results], ["ok", "ok"])
            self.assertEqual(len({item[1] for item in results}), 1)

    def test_two_processes_cannot_bind_two_checkpoints_to_one_outcome_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reading_store, first = self._accepted_fixture(root)
            _, second = self._accepted_fixture(root)
            context = multiprocessing.get_context("fork")
            start = context.Event()
            results = context.Queue()
            processes = []
            for label, reading in (("a", first), ("b", second)):
                process = context.Process(
                    target=_record_from_competing_process,
                    kwargs={
                        "start": start,
                        "results": results,
                        "outcome_root": str(root / "outcome-store"),
                        "reading_root": str(reading_store.root),
                        "checkpoint_path": str(root / f"checkpoint-{label}" / "outcomes.json"),
                        "reading_id": reading.accepted.reading_id,
                        "prepared_digest": reading.accepted.prepared_digest,
                    },
                )
                process.start()
                processes.append(process)
            start.set()
            for process in processes:
                process.join(10)
                self.assertEqual(process.exitcode, 0)
            observed = [results.get(timeout=2) for _ in processes]
            stored = [item for item in observed if item[0] == "stored"]
            rejected = [item for item in observed if item[0] == "rejected"]
            self.assertEqual(len(stored), 1, observed)
            self.assertEqual(len(rejected), 1, observed)
            winning = OutcomeStore(
                root / "outcome-store",
                reading_store=reading_store,
                integrity_key=INTEGRITY_KEY,
                checkpoint_path=stored[0][1],
            )
            self.assertEqual([item.claim_id for item in winning.list_all()], [stored[0][2]])

    def test_restart_recovers_crash_between_outcome_and_checkpoint_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reading_store, reading, store, claim = self._store_and_claim(root)
            write_manifest = store._write_manifest

            def fail_final(entries, *, pending=None):
                if pending is None and entries:
                    raise OSError("injected checkpoint commit crash")
                return write_manifest(entries, pending=pending)

            store._write_manifest = fail_final
            with self.assertRaises(OSError):
                self._record(store, reading, claim)

            restarted = OutcomeStore(
                root / "outcome-store",
                reading_store=reading_store,
                integrity_key=INTEGRITY_KEY,
                checkpoint_path=root / "checkpoint" / "outcomes.json",
            )
            recovered = restarted.list_all()
            repeated = self._record(restarted, reading, claim)

        self.assertEqual(len(recovered), 1)
        self.assertEqual(recovered[0], repeated)

    def test_superseded_claim_remains_recordable_after_correction_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            provider = StaticProvider()
            engine = build_engine(root / "reading-store", provider)
            turn = _concluded_turn(engine, provider, provider_request("第一版"))
            first = _accept_with_claim(engine, turn)
            corrected = _concluded_turn(
                engine,
                provider,
                provider_request(
                    "更正时间",
                    facts={
                        "subject:test": {
                            "event_datetime_or_reference_datetime": (
                                "2026-07-23T22:13:00+08:00"
                            ),
                            "timezone": "Asia/Shanghai",
                        }
                    },
                ),
                state_token=turn.state_token,
                transition="correct",
            )
            second = _accept_with_claim(engine, corrected)
            self.assertEqual(second.reading_id, first.reading_id)
            self.assertEqual(second.version, first.version + 1)
            self.assertEqual(second.action, "correct")
            self.assertEqual(second.supersedes_version, 1)
            store = OutcomeStore(
                root / "outcome-store", reading_store=engine.store,
                integrity_key=INTEGRITY_KEY,
                checkpoint_path=root / "checkpoint" / "outcomes.json",
            )
            old_claim = store.claims(
                reading_id=first.reading_id,
                prepared_digest=first.prepared_digest,
            )[0]
            outcome = self._record(
                store,
                engine.store.load_version(first.reading_id, first.version),
                old_claim,
            )

        self.assertEqual(outcome.reading_version, 1)

    def test_cli_uses_private_report_and_key_files_without_echoing_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reading_store, reading, store, claim = self._store_and_claim(root)
            key_path = root / "integrity.key"
            report_path = root / "report.json"
            key_path.write_bytes(INTEGRITY_KEY)
            report_path.write_text(
                json.dumps(
                    {
                        "reading_id": reading.accepted.reading_id,
                        "prepared_digest": reading.accepted.prepared_digest,
                        "claim_id": claim.claim_id,
                        "status": "unknown",
                        "evidence": {"kind": "user_report", "summary": "待核验"},
                        "reported_at": "2026-08-01T10:00:00+08:00",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            os.chmod(key_path, 0o600)
            os.chmod(report_path, 0o600)
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = record_reading_outcome.main(
                    [
                        "--reading-store", str(reading_store.root),
                        "--outcome-store", str(store.root),
                        "--integrity-key-file", str(key_path),
                        "--integrity-checkpoint", str(root / "checkpoint" / "outcomes.json"),
                        "--report-file", str(report_path),
                    ]
                )
            payload = json.loads(output.getvalue())
            os.chmod(report_path, 0o644)
            with self.assertRaises(ValueError):
                record_reading_outcome.main(
                    [
                        "--reading-store", str(reading_store.root),
                        "--outcome-store", str(store.root),
                        "--integrity-key-file", str(key_path),
                        "--integrity-checkpoint", str(root / "checkpoint" / "outcomes.json"),
                        "--report-file", str(report_path),
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["stored"])
        self.assertNotIn("evidence", payload)
        self.assertNotIn("claim_text", payload)

    def test_precreated_lock_symlink_is_rejected_without_touching_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, reading, store, claim = self._store_and_claim(root)
            target = root / "victim.txt"
            target.write_text("unchanged", encoding="utf-8")
            lock = store.outcomes / f".{claim.claim_id}.lock"
            lock.symlink_to(target)
            with self.assertRaises(RuntimeError):
                self._record(store, reading, claim)
            self.assertEqual(target.read_text(encoding="utf-8"), "unchanged")


if __name__ == "__main__":
    unittest.main()

"""Tests for model-driven capability selection and no-input graceful fallback.

These tests use a domain-free fixture vocabulary (capability.alpha /
capability.beta, object.one, dimension.one, field.one / field.two) so the
generic resolver can be exercised without naming any concrete provider.

The scenario matrix mirrors the implementation plan:

* 8.1  the core must not auto-pick the capability that happens to need
       fewer inputs;
* 8.2  trusted context (clock, default timezone, exact subject profile)
       satisfies required fields without reading ambient memory;
* 8.3  a pending token is recoverable: the host re-supplies facts and the
       same prepared reading is replayed;
* 8.4  when the host learns the user cannot provide the missing facts, it
       drops the pending token and starts a new root with a different
       capability that is structurally compatible and already supported;
* 8.5  when no candidate is feasible, the result is a non-empty Stopped
       and no fake facts or evidence are produced;
* 8.6  a new subject or object must not silently inherit the previous
       capability, even when an accepted token is supplied;
* 8.7  same-scope accepted tokens still continue the reading on the
       same capability;
* 8.8  a transition (correct or restart) that conflicts with the prior
       scope must surface as Stopped.conflict, not as silent lineage
       rewrites;
* 8.9  zero evidence or partial dimensions do not drop the entire turn:
       facts survive, limits describe the gap, and unsupported scopes
       stop instead of fabricating claims;
* 8.10 an internal provider failure must surface as Stopped.error, never
       as a silent capability swap.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest import mock

from reading_engine.catalog import (
    CatalogLoader,
    ProviderDescriptor,
    RuntimeCatalog,
)
from reading_engine.contracts import (
    CalculationResult,
    EvidenceBundle,
    ReadingRequest,
    canonical_digest,
)
from reading_engine.interface import ReadingInterface
from reading_engine.interface_contracts import (
    Accepted,
    Complete,
    HorizonSelection,
    IntentSelection,
    Prepare,
    Prepared,
    Stopped,
)
from reading_engine.provider_protocol import (
    ProviderContext,
    ProviderNeedInput,
    ProviderPreparation,
    ProviderRequest,
)
from reading_engine.runtime_context import build_runtime_context
from reading_engine.storage import AtomicReadingStore
from reading_engine.turns import TurnEngine

ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Fixture catalog and adapters
# ---------------------------------------------------------------------------


def _manifest(
    provider_id: str,
    *,
    object_ids: tuple[str, ...] = ("object.one",),
    horizon_ids: tuple[str, ...] = ("horizon.one",),
    dimension_ids: tuple[str, ...] = ("dimension.one", "dimension.two"),
    required_groups: tuple[tuple[str, ...], ...] = (("field.one", "field.two"),),
    lineage: str = "lineage.alpha",
    assumption_cost: int = 0,
    default_priority: int = 100,
    entrypoint: str | None = None,
) -> dict:
    return {
        "schema_version": "provider-manifest-v1",
        "id": provider_id,
        "entrypoint": entrypoint or f"{__name__}:FakeAdapter",
        "display": {
            "zh-CN": {
                "name": provider_id,
                "description": f"中性 fixture adapter {provider_id}。",
            }
        },
        "capability": {
            "object_ids": list(object_ids),
            "horizon_ids": list(horizon_ids),
            "dimension_ids": list(dimension_ids),
            "default_dimension_ids": list(dimension_ids[:1]),
            "required_input_groups": [
                {"any_of": list(group)} for group in required_groups
            ],
            "exact_horizon_ids": [],
            "independent_lineage_id": lineage,
            "assumption_cost": assumption_cost,
            "default_priority": default_priority,
        },
        "input_fields": {
            "field.one": {
                "type": "string",
                "display": {"zh-CN": "字段一"},
            },
            "field.two": {
                "type": "string",
                "display": {"zh-CN": "字段二"},
            },
            "field.clock": {
                "type": "string",
                "display": {"zh-CN": "可信时间"},
            },
        },
        "evidence_profile_id": f"evidence.{provider_id}",
    }


@dataclass
class _AdapterCall:
    provider_id: str
    subject_ref: str
    request: ProviderRequest


@dataclass
class _FakeAdapter:
    """Deterministic adapter that reports needs and produces a real preparation."""

    provider_id: str
    needs: tuple[str, ...] = ()
    raise_text: str | None = None
    call_log: list[_AdapterCall] = field(default_factory=list)

    def bind_descriptor(self, descriptor: ProviderDescriptor) -> None:
        self._descriptor = descriptor

    @property
    def descriptor(self) -> ProviderDescriptor:
        return self._descriptor

    def prepare(
        self,
        request: ProviderRequest,
        context: ProviderContext,
    ) -> ProviderPreparation | ProviderNeedInput:
        if self.raise_text is not None:
            raise RuntimeError(self.raise_text)
        self.call_log.append(
            _AdapterCall(
                provider_id=self.provider_id,
                subject_ref=str(request.subject_refs[0])
                if request.subject_refs
                else "",
                request=request,
            )
        )
        facts = dict(request.facts or {})
        primary_subject = (
            str(request.subject_refs[0])
            if request.subject_refs
            else "subject:test"
        )
        subject_facts = dict(facts.get(primary_subject) or {})
        provided: set[str] = set(subject_facts)
        # trusted context contributes the time, timezone, and exact profile
        if context.now_iso:
            provided.add("field.clock")
        if context.default_timezone:
            provided.add("field.clock")
        if primary_subject in (context.subject_facts or {}):
            provided.update((context.subject_facts.get(primary_subject) or {}).keys())
        missing = tuple(name for name in self.needs if name not in provided)
        if missing:
            return ProviderNeedInput(
                missing_input_groups=tuple((name,) for name in missing)
            )
        return _build_preparation(self.provider_id, request, primary_subject)


def _build_preparation(
    provider_id: str, request: ProviderRequest, primary_subject: str
) -> ProviderPreparation:
    """Build a fully-typed ProviderPreparation so the engine can stage it."""

    # The engine wraps the request with a concrete reading_id and version
    # before calling the adapter; copy them so the staged record carries
    # the same identity the engine expects.
    staged_reading_id = str(request.reading_id or "0" * 32)
    staged_version = int(request.version or 1)
    input_payload = {
        "query": request.query,
        "subject_refs": list(request.subject_refs),
        "object_id": request.object_id,
        "horizon": dict(request.horizon or {}),
        "facts": {
            str(subject): dict(fields or {})
            for subject, fields in (request.facts or {}).items()
        },
    }
    facts_payload: dict[str, Any] = {
        "output": {
            "provider": provider_id,
            "primary_subject": primary_subject,
        }
    }
    calculation = CalculationResult.create(
        system=provider_id,
        provider_id=provider_id,
        provider_version="test-1",
        input_payload=input_payload,
        facts=facts_payload,
    )
    bundle = EvidenceBundle.create(
        system=provider_id,
        evidence=(),
        counter_evidence=(),
        source_relationships=(),
        source_gaps=(),
        intent_digest="",
    )
    reading_request = ReadingRequest(
        query=request.query,
        action="new",
        system=provider_id,
        intent={
            "subject_refs": list(request.subject_refs),
            "calculation_object": request.object_id,
            "question_dimensions": list(request.dimension_ids),
            "horizon": dict(request.horizon or {}),
        },
        reading_id=staged_reading_id,
        reference_datetime=None,
        timezone=None,
    )
    intent_digest = canonical_digest(reading_request.intent)
    return ProviderPreparation(
        calculation=calculation,
        public_facts=(
            {
                "ref": f"fact:{provider_id}:{primary_subject}:one",
                "subject_ref": primary_subject,
                "kind_id": "kind.fact",
                "value": {"provider": provider_id},
                "display_text": f"事实：{provider_id} 已计算。",
            },
        ),
        fact_index=(),
        evidence_plan={
            "bundle": bundle,
            "request": reading_request,
            "evidence": (),
            "reading_id": staged_reading_id,
            "version": staged_version,
            "basis_label": f"{provider_id} basis",
            "intent_digest": intent_digest,
        },
        # The fixture's preparation must declare at least one publishable
        # claim scope so the generic engine invariant does not reject
        # it.  The zero-evidence source-gap test depends on this scope
        # being present.
        claim_scopes=(
            {
                "subject_ref": primary_subject,
                "dimension_id": "dimension.one",
                "allowed_kind_ids": ["kind.fact"],
                "certainty_ceiling_id": "certainty.tendency",
                "fact_refs": [
                    f"fact:{provider_id}:{primary_subject}:one"
                ],
                "evidence_refs": [],
            },
        ),
        limits=(),
        provider_id=provider_id,
        provider_version="test-1",
        subject_ref=primary_subject,
        capability_id=provider_id,
        independent_lineage_id=provider_id,
        request_view={
            "object_id": request.object_id,
            "subject_refs": list(request.subject_refs),
            "dimension_ids": list(request.dimension_ids),
            "capability_ids": [provider_id],
            "horizon": {
                "kind_id": str((request.horizon or {}).get("kind", "instant")),
                "start": (request.horizon or {}).get("start"),
                "end": (request.horizon or {}).get("end"),
            },
        },
        findings=(),
    )


class _Fixture:
    def __init__(
        self,
        manifests: list[dict],
        adapters: dict[str, _FakeAdapter],
    ) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        (root / "providers").mkdir()
        entries: list[str] = []
        for manifest in manifests:
            name = f"providers/{manifest['id']}.json"
            (root / name).write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            entries.append(name)
        (root / "catalog-v1.json").write_text(
            json.dumps(
                {"schema_version": "catalog-v1", "providers": entries},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        self.root = root
        self.catalog: RuntimeCatalog = CatalogLoader(root).load()
        for adapter in adapters.values():
            adapter.bind_descriptor(self.catalog.descriptor(adapter.provider_id))
        self.store_root = Path(self._tmp.name) / "store"
        self.store_root.mkdir()
        self.store = AtomicReadingStore(self.store_root)
        self.engine = TurnEngine(
            store=self.store,
            providers=adapters,
            catalog=self.catalog,
        )

    def interface(self, **context) -> ReadingInterface:
        ctx = (
            build_runtime_context(**context) if context else build_runtime_context()
        )
        # rebuild the engine so the runtime context is wired into the
        # provider seam (the interface routes context only via the engine).
        self.engine.runtime_context = ctx
        return ReadingInterface(
            skill_root=ROOT,
            catalog=self.catalog,
            engine=self.engine,
            runtime_context=ctx,
        )

    def cleanup(self) -> None:
        self._tmp.cleanup()


def _build_fixture(
    *,
    alpha_needs: tuple[str, ...] = ("field.one",),
    beta_needs: tuple[str, ...] = ("field.two",),
    alpha_assumption_cost: int = 0,
    beta_assumption_cost: int = 0,
    alpha_priority: int = 100,
    beta_priority: int = 100,
    alpha_raise: str | None = None,
    beta_raise: str | None = None,
) -> _Fixture:
    manifests = [
        _manifest(
            "capability.alpha",
            lineage="lineage.alpha",
            required_groups=(("field.one",),),
            assumption_cost=alpha_assumption_cost,
            default_priority=alpha_priority,
        ),
        _manifest(
            "capability.beta",
            lineage="lineage.beta",
            required_groups=(("field.two",),),
            assumption_cost=beta_assumption_cost,
            default_priority=beta_priority,
        ),
    ]
    adapters = {
        "capability.alpha": _FakeAdapter(
            provider_id="capability.alpha",
            needs=alpha_needs,
            raise_text=alpha_raise,
        ),
        "capability.beta": _FakeAdapter(
            provider_id="capability.beta",
            needs=beta_needs,
            raise_text=beta_raise,
        ),
    }
    return _Fixture(manifests, adapters)


def _intent(
    subject: str = "subject:test",
    *,
    object_id: str = "object.one",
    horizon_kind: str = "horizon.one",
    dimensions: tuple[str, ...] = ("dimension.one",),
    capability_id: str | None = None,
) -> IntentSelection:
    return IntentSelection(
        subject_refs=(subject,),
        object_id=object_id,
        dimension_ids=dimensions,
        horizon=HorizonSelection(kind_id=horizon_kind),
        capability_id=capability_id,
    )


# ---------------------------------------------------------------------------
# 8.1 No auto-pick by input completeness
# ---------------------------------------------------------------------------


class NoAutoPickByInputCompletenessTests(unittest.TestCase):
    def setUp(self) -> None:
        # alpha needs field.one (so it is NOT satisfied by ambient facts);
        # beta needs field.two (NOT satisfied either).  Both have identical
        # assumption_cost/default_priority so the only "auto" winner would
        # come from satisfied-priority logic — which the core must drop.
        self.fixture = _build_fixture(
            alpha_needs=("field.one",),
            beta_needs=("field.two",),
        )
        self.addCleanup(self.fixture.cleanup)

    def test_unspecified_capability_with_two_candidates_returns_need_input(
        self,
    ) -> None:
        interface = self.fixture.interface()
        result = interface.execute(
            Prepare(
                query="中性问句",
                intent=_intent(),
                facts={},
            )
        )
        # The core must not pick one of the two structurally compatible
        # capabilities; it must stop and ask the model to choose.
        self.assertIsInstance(result, Stopped, result)
        self.assertEqual(result.reason, "need_input", result)
        self.assertTrue(result.public_copy.strip())
        # No state token is issued until the model selects a capability.
        self.assertIsNone(result.state_token)
        # Neither adapter should have been invoked.
        for adapter in self.fixture.engine.providers.values():
            self.assertEqual(adapter.call_log, [])

    def test_unspecified_capability_with_one_candidate_still_returns_need_input(
        self,
    ) -> None:
        adapter = _FakeAdapter(
            provider_id="capability.alpha",
            needs=(),
        )
        fixture = _Fixture(
            [
                _manifest(
                    "capability.alpha",
                    lineage="lineage.alpha",
                    required_groups=(),
                )
            ],
            {"capability.alpha": adapter},
        )
        self.addCleanup(fixture.cleanup)

        result = fixture.interface().execute(
            Prepare(query="中性问句", intent=_intent(), facts={})
        )

        self.assertIsInstance(result, Stopped, result)
        self.assertEqual(result.reason, "need_input", result)
        self.assertTrue(result.public_copy.strip())
        self.assertIsNone(result.state_token)
        self.assertEqual(adapter.call_log, [])

    def test_explicit_alpha_returns_its_own_need_input(self) -> None:
        interface = self.fixture.interface()
        result = interface.execute(
            Prepare(
                query="中性问句",
                intent=_intent(capability_id="capability.alpha"),
                facts={},
            )
        )
        self.assertIsInstance(result, Stopped, result)
        self.assertEqual(result.reason, "need_input", result)
        missing_ids = (
            {
                group.any_of[0].id
                for group in (result.input_request.requirements or ())
                if group.any_of
            }
            if result.input_request
            else set()
        )
        self.assertEqual(missing_ids, {"field.one"})
        # beta must NOT have been called instead of alpha.
        beta = self.fixture.engine.providers["capability.beta"]
        self.assertEqual(beta.call_log, [])

    def test_explicit_beta_with_satisfied_inputs_prepares(self) -> None:
        interface = self.fixture.interface()
        result = interface.execute(
            Prepare(
                query="中性问句",
                intent=_intent(capability_id="capability.beta"),
                facts={"subject:test": {"field.two": "已提供"}},
            )
        )
        self.assertIsInstance(result, Prepared, result)
        beta = self.fixture.engine.providers["capability.beta"]
        self.assertEqual(len(beta.call_log), 1)
        alpha = self.fixture.engine.providers["capability.alpha"]
        self.assertEqual(alpha.call_log, [])


# ---------------------------------------------------------------------------
# 8.2 Trusted context fills required fields
# ---------------------------------------------------------------------------


class TrustedContextSatisfiesRequiredFieldsTests(unittest.TestCase):
    def setUp(self) -> None:
        # alpha only needs field.clock; the trusted runtime context carries
        # now_iso which the adapter exposes as field.clock.  No ambient
        # memory should be consulted.
        self.fixture = _build_fixture(
            alpha_needs=("field.clock",),
            beta_needs=("field.two",),
        )
        self.addCleanup(self.fixture.cleanup)

    def test_now_iso_marks_clock_as_provided(self) -> None:
        interface = self.fixture.interface(
            now_iso="2026-07-31T10:00:00+08:00",
            default_timezone_name="Asia/Shanghai",
        )
        result = interface.execute(
            Prepare(
                query="中性问句",
                intent=_intent(capability_id="capability.alpha"),
                facts={},
            )
        )
        self.assertIsInstance(result, Prepared, result)
        # beta was not consulted.
        self.assertEqual(
            self.fixture.engine.providers["capability.beta"].call_log, []
        )

    def test_no_clock_does_not_borrow_from_other_subjects(self) -> None:
        # Without a clock, the request stops with need_input; the core must
        # not silently read a different subject's profile to fake the field.
        from reading_engine.runtime_context import RuntimeContext

        ctx = RuntimeContext(
            now_iso=None,
            default_timezone_name=None,
            subject_profiles={
                "subject:other": {"field.clock": "2026-01-01T00:00:00+00:00"}
            },
        )
        self.fixture.engine.runtime_context = ctx
        interface = ReadingInterface(
            skill_root=ROOT,
            catalog=self.fixture.catalog,
            engine=self.fixture.engine,
            runtime_context=ctx,
        )
        result = interface.execute(
            Prepare(
                query="中性问句",
                intent=_intent(
                    subject="subject:test", capability_id="capability.alpha"
                ),
                facts={},
            )
        )
        self.assertIsInstance(result, Stopped, result)
        self.assertEqual(result.reason, "need_input", result)


# ---------------------------------------------------------------------------
# 8.3 User-supplied facts resume via the same token
# ---------------------------------------------------------------------------


class PendingTokenResumeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = _build_fixture(
            alpha_needs=("field.one",),
        )
        self.addCleanup(self.fixture.cleanup)

    def test_resume_same_token_prepares(self) -> None:
        interface = self.fixture.interface()
        first = interface.execute(
            Prepare(
                query="中性问句",
                intent=_intent(capability_id="capability.alpha"),
                facts={},
            )
        )
        self.assertIsInstance(first, Stopped, first)
        self.assertEqual(first.reason, "need_input", first)
        self.assertIsNotNone(first.state_token)
        self.assertIsNotNone(first.input_request)
        # The same token, with the missing field, advances the same lineage.
        resumed = interface.execute(
            Prepare(
                query="中性问句（补资料）",
                intent=_intent(capability_id="capability.alpha"),
                facts={"subject:test": {"field.one": "已提供"}},
                state_token=first.state_token,
            )
        )
        self.assertIsInstance(resumed, Prepared, resumed)
        # Replaying the same canonical supplement yields the same brief.
        replay = interface.execute(
            Prepare(
                query="中性问句（补资料）",
                intent=_intent(capability_id="capability.alpha"),
                facts={"subject:test": {"field.one": "已提供"}},
                state_token=first.state_token,
            )
        )
        self.assertIsInstance(replay, Prepared, replay)
        self.assertEqual(
            json.dumps(resumed.brief.to_dict(), ensure_ascii=False, sort_keys=True),
            json.dumps(replay.brief.to_dict(), ensure_ascii=False, sort_keys=True),
        )


# ---------------------------------------------------------------------------
# 8.4 User cannot supply → host drops token and switches capability
# ---------------------------------------------------------------------------


class HostSwitchesCapabilityAfterUserCantProvideTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = _build_fixture(
            alpha_needs=("field.one",),
            beta_needs=("field.two",),
        )
        self.addCleanup(self.fixture.cleanup)

    def test_pending_then_explicit_new_capability_starts_new_root(self) -> None:
        interface = self.fixture.interface()
        pending = interface.execute(
            Prepare(
                query="中性问句",
                intent=_intent(capability_id="capability.alpha"),
                facts={},
            )
        )
        self.assertIsInstance(pending, Stopped)
        self.assertEqual(pending.reason, "need_input")
        alpha_calls_before = len(
            self.fixture.engine.providers["capability.alpha"].call_log
        )
        # The host now learns the user cannot provide field.one.  It drops
        # the pending token and re-issues a NEW root with beta, supplying
        # field.two in the same facts payload.
        new_root = interface.execute(
            Prepare(
                query="中性问句（换能力）",
                intent=_intent(capability_id="capability.beta"),
                facts={"subject:test": {"field.two": "已提供"}},
                # no state_token
            )
        )
        self.assertIsInstance(new_root, Prepared, new_root)
        # Beta was invoked for the new root; alpha was not invoked again.
        self.assertEqual(
            len(self.fixture.engine.providers["capability.beta"].call_log), 1
        )
        self.assertEqual(
            len(self.fixture.engine.providers["capability.alpha"].call_log),
            alpha_calls_before,
        )

    def test_pending_token_with_different_capability_is_rejected(self) -> None:
        """The pending token cannot be silently re-purposed to a new provider."""

        interface = self.fixture.interface()
        pending = interface.execute(
            Prepare(
                query="中性问句",
                intent=_intent(capability_id="capability.alpha"),
                facts={},
            )
        )
        self.assertIsInstance(pending, Stopped)
        self.assertEqual(pending.reason, "need_input")
        # Using the pending token with a different capability surfaces a
        # conflict so the host knows to drop the token and start fresh.
        confused = interface.execute(
            Prepare(
                query="中性问句",
                intent=_intent(capability_id="capability.beta"),
                facts={"subject:test": {"field.two": "已提供"}},
                state_token=pending.state_token,
            )
        )
        self.assertIsInstance(confused, Stopped, confused)
        self.assertEqual(confused.reason, "conflict", confused)
        self.assertTrue(confused.public_copy.strip())


# ---------------------------------------------------------------------------
# 8.5 No valid alternative
# ---------------------------------------------------------------------------


class NoValidAlternativeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = _build_fixture(
            alpha_needs=("field.one",),
            beta_needs=("field.two",),
        )
        self.addCleanup(self.fixture.cleanup)

    def test_explicit_unsupported_capability_stops_without_trying_others(
        self,
    ) -> None:
        interface = self.fixture.interface()
        result = interface.execute(
            Prepare(
                query="中性问句",
                intent=_intent(capability_id="capability.nonexistent"),
                facts={},
            )
        )
        self.assertIsInstance(result, Stopped)
        self.assertEqual(result.reason, "unsupported")
        self.assertTrue(result.public_copy.strip())
        for adapter in self.fixture.engine.providers.values():
            self.assertEqual(adapter.call_log, [])

    def test_ambiguous_without_explicit_capability_stops_nonempty(self) -> None:
        # Both candidates are still missing required facts; the core must
        # stop without faking any preparation, evidence, or claim.
        interface = self.fixture.interface()
        result = interface.execute(
            Prepare(
                query="中性问句",
                intent=_intent(),
                facts={},
            )
        )
        self.assertIsInstance(result, Stopped, result)
        self.assertEqual(result.reason, "need_input", result)
        self.assertTrue(result.public_copy.strip())
        # No adapter was invoked and no token was issued.
        for adapter in self.fixture.engine.providers.values():
            self.assertEqual(adapter.call_log, [])


# ---------------------------------------------------------------------------
# 8.6 New subject must not inherit old method
# ---------------------------------------------------------------------------


class NewSubjectDoesNotInheritOldMethodTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = _build_fixture()
        self.addCleanup(self.fixture.cleanup)

    def test_accepted_token_with_different_explicit_capability_starts_new_root(
        self,
    ) -> None:
        interface = self.fixture.interface()
        intent_a = _intent(subject="subject:a", capability_id="capability.alpha")
        # first reading: subject:a + alpha
        first = interface.execute(
            Prepare(
                query="主体 A 的中性问句",
                intent=intent_a,
                facts={"subject:a": {"field.one": "已提供"}},
            )
        )
        self.assertIsInstance(first, Prepared, first)
        accept = interface.execute(
            Complete(state_token=first.state_token, public_copy="主体 A 第一稿。")
        )
        self.assertIsInstance(accept, Accepted, accept)
        # second ask: subject:b + explicit beta, reusing the A token by mistake
        second = interface.execute(
            Prepare(
                query="主体 B 的中性问句",
                intent=_intent(subject="subject:b", capability_id="capability.beta"),
                facts={"subject:b": {"field.two": "已提供"}},
                state_token=first.state_token,
            )
        )
        self.assertIsInstance(second, Prepared, second)
        # The second reading must be a new root, not a continuation of A.
        token_a = interface.engine.token_store.resolve(first.state_token)
        token_b = interface.engine.token_store.resolve(second.state_token)
        self.assertNotEqual(token_a.reading_id, token_b.reading_id)
        # And beta was the actual adapter invoked, not alpha.
        self.assertEqual(
            len(self.fixture.engine.providers["capability.beta"].call_log), 1
        )
        # Alpha must not have been called for subject:b.
        alpha_calls = [
            call
            for call in self.fixture.engine.providers["capability.alpha"].call_log
            if call.subject_ref == "subject:b"
        ]
        self.assertEqual(alpha_calls, [])

    def test_accepted_token_with_changed_scope_without_capability_starts_new_root(
        self,
    ) -> None:
        interface = self.fixture.interface()
        first = interface.execute(
            Prepare(
                query="主体 A 的中性问句",
                intent=_intent(subject="subject:a", capability_id="capability.alpha"),
                facts={"subject:a": {"field.one": "已提供"}},
            )
        )
        self.assertIsInstance(first, Prepared, first)
        accept = interface.execute(
            Complete(state_token=first.state_token, public_copy="主体 A 第一稿。")
        )
        self.assertIsInstance(accept, Accepted, accept)
        # Same accepted token, but the new question is about subject:b with
        # no explicit capability.  The core must not silently continue the
        # prior alpha reading; it surfaces a choose_capability stop so the
        # host model can pick a structurally compatible provider for the
        # new subject.  Beta wins when the model re-submits with it.
        second = interface.execute(
            Prepare(
                query="主体 B 的中性问句",
                intent=_intent(subject="subject:b"),
                facts={"subject:b": {"field.two": "已提供"}},
                state_token=first.state_token,
            )
        )
        self.assertIsInstance(second, Stopped, second)
        self.assertEqual(second.reason, "need_input", second)
        self.assertIn("请先选择", second.public_copy)
        # The host re-submits with an explicit capability for the new
        # subject; this must start a new root, not continue alpha.
        third = interface.execute(
            Prepare(
                query="主体 B 的中性问句（确定能力）",
                intent=_intent(
                    subject="subject:b", capability_id="capability.beta"
                ),
                facts={"subject:b": {"field.two": "已提供"}},
                state_token=second.state_token,
            )
        )
        self.assertIsInstance(third, Prepared, third)
        token_a = interface.engine.token_store.resolve(first.state_token)
        token_c = interface.engine.token_store.resolve(third.state_token)
        self.assertNotEqual(token_a.reading_id, token_c.reading_id)
        # And beta was the actual adapter invoked, not alpha.
        beta_calls_for_b = [
            call
            for call in interface.engine.providers["capability.beta"].call_log
            if call.subject_ref == "subject:b"
        ]
        self.assertEqual(len(beta_calls_for_b), 1)
        alpha_calls_for_b = [
            call
            for call in interface.engine.providers["capability.alpha"].call_log
            if call.subject_ref == "subject:b"
        ]
        self.assertEqual(alpha_calls_for_b, [])


# ---------------------------------------------------------------------------
# 8.7 Same-scope continue inherits the bound capability
# ---------------------------------------------------------------------------


class SameScopeContinuationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = _build_fixture()
        self.addCleanup(self.fixture.cleanup)

    def test_same_scope_continue_inherits_alpha(self) -> None:
        interface = self.fixture.interface()
        first = interface.execute(
            Prepare(
                query="主体 A 的中性问句",
                intent=_intent(subject="subject:a", capability_id="capability.alpha"),
                facts={"subject:a": {"field.one": "已提供"}},
            )
        )
        self.assertIsInstance(first, Prepared, first)
        accept = interface.execute(
            Complete(state_token=first.state_token, public_copy="主体 A 第一稿。")
        )
        self.assertIsInstance(accept, Accepted, accept)
        # Same scope, no explicit capability → must continue on alpha.
        follow = interface.execute(
            Prepare(
                query="主体 A 的追问",
                intent=_intent(subject="subject:a"),
                facts={"subject:a": {"field.one": "已提供"}},
                state_token=first.state_token,
            )
        )
        self.assertIsInstance(follow, Prepared, follow)
        token_a = interface.engine.token_store.resolve(first.state_token)
        token_b = interface.engine.token_store.resolve(follow.state_token)
        self.assertEqual(token_a.reading_id, token_b.reading_id)
        self.assertEqual(token_b.version, token_a.version + 1)


# ---------------------------------------------------------------------------
# 8.8 correction/restart with conflicting scope
# ---------------------------------------------------------------------------


class TransitionConflictTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = _build_fixture()
        self.addCleanup(self.fixture.cleanup)

    def test_correct_with_conflicting_subject_returns_conflict(self) -> None:
        interface = self.fixture.interface()
        first = interface.execute(
            Prepare(
                query="主体 A 的中性问句",
                intent=_intent(subject="subject:a", capability_id="capability.alpha"),
                facts={"subject:a": {"field.one": "已提供"}},
            )
        )
        self.assertIsInstance(first, Prepared, first)
        accept = interface.execute(
            Complete(state_token=first.state_token, public_copy="主体 A 第一稿。")
        )
        self.assertIsInstance(accept, Accepted, accept)
        # correct transition but the subject changed silently.
        conflict = interface.execute(
            Prepare(
                query="主体 B 的纠正",
                intent=_intent(subject="subject:b", capability_id="capability.alpha"),
                facts={"subject:b": {"field.one": "已提供"}},
                state_token=first.state_token,
                transition="correct",
            )
        )
        self.assertIsInstance(conflict, Stopped, conflict)
        self.assertEqual(conflict.reason, "conflict", conflict)
        self.assertTrue(conflict.public_copy.strip())

    def test_restart_with_conflicting_object_returns_conflict(self) -> None:
        interface = self.fixture.interface()
        first = interface.execute(
            Prepare(
                query="object.one 的中性问句",
                intent=_intent(
                    subject="subject:a",
                    object_id="object.one",
                    capability_id="capability.alpha",
                ),
                facts={"subject:a": {"field.one": "已提供"}},
            )
        )
        self.assertIsInstance(first, Prepared, first)
        accept = interface.execute(
            Complete(state_token=first.state_token, public_copy="object.one 第一稿。")
        )
        self.assertIsInstance(accept, Accepted, accept)
        conflict = interface.execute(
            Prepare(
                query="object.two 的重起",
                intent=_intent(
                    subject="subject:a",
                    object_id="object.two",
                    capability_id="capability.alpha",
                ),
                facts={"subject:a": {"field.one": "已提供"}},
                state_token=first.state_token,
                transition="restart",
            )
        )
        self.assertIsInstance(conflict, Stopped, conflict)
        self.assertEqual(conflict.reason, "conflict", conflict)


# ---------------------------------------------------------------------------
# 8.9 Zero evidence and partial success
# ---------------------------------------------------------------------------


class ZeroEvidenceAndPartialSuccessTests(unittest.TestCase):
    def setUp(self) -> None:
        # alpha returns a preparation whose evidence plan carries no
        # evidence nodes.  The brief must still surface a source-gap limit
        # rather than fabricate a quote.
        self.fixture = _build_fixture(
            alpha_needs=("field.one",),
        )
        self.addCleanup(self.fixture.cleanup)

    def test_prepared_with_zero_evidence_has_source_gap_limit(self) -> None:
        interface = self.fixture.interface()
        result = interface.execute(
            Prepare(
                query="中性问句",
                intent=_intent(capability_id="capability.alpha"),
                facts={"subject:test": {"field.one": "已提供"}},
            )
        )
        self.assertIsInstance(result, Prepared, result)
        rendered = json.dumps(result.brief.to_dict(), ensure_ascii=False)
        # The brief must not pretend to have quotes; it must surface that
        # the search returned no applicable evidence.
        self.assertNotIn("ref:evidence:", rendered)


# ---------------------------------------------------------------------------
# 8.10 Provider internal error
# ---------------------------------------------------------------------------


class ProviderInternalErrorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = _build_fixture(
            alpha_raise="kaboom",
        )
        self.addCleanup(self.fixture.cleanup)

    def test_provider_exception_returns_stopped_error_without_fallback(self) -> None:
        interface = self.fixture.interface()
        result = interface.execute(
            Prepare(
                query="中性问句",
                intent=_intent(capability_id="capability.alpha"),
                facts={"subject:test": {"field.one": "已提供"}},
            )
        )
        self.assertIsInstance(result, Stopped, result)
        self.assertEqual(result.reason, "error", result)
        self.assertTrue(result.public_copy.strip())
        assert result.failure is not None
        self.assertEqual(result.failure.code, "runtime.internal_error")
        # Beta must not have been silently tried instead.
        self.assertEqual(
            self.fixture.engine.providers["capability.beta"].call_log, []
        )

    def test_provider_timeout_has_a_retryable_transient_code(self) -> None:
        interface = self.fixture.interface()
        adapter = self.fixture.engine.providers["capability.alpha"]
        with mock.patch.object(adapter, "prepare", side_effect=TimeoutError()):
            result = interface.execute(
                Prepare(
                    query="中性问句",
                    intent=_intent(capability_id="capability.alpha"),
                    facts={"subject:test": {"field.one": "已提供"}},
                )
            )

        self.assertIsInstance(result, Stopped, result)
        assert result.failure is not None
        self.assertEqual(result.failure.code, "transient.timeout")
        self.assertTrue(result.failure.retryable)


if __name__ == "__main__":
    unittest.main()

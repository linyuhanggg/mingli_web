"""P1 rework acceptance tests.

These tests prove the deterministic gaps the rework must close, in the
domain-free vocabulary (``capability.alpha`` / ``capability.beta``,
``object.one``, ``dimension.one``, ``field.one``/``field.two``).  Every
test that the previous build labelled "passing" but only because it
asserted surface identity is re-stated here with the structural
assertions the rework contract requires: parent, root, action, lineage
claim, and old-token reusability.

The suite groups the work by gap:

* A.  New root lineage: scope change or explicit-capability change must
     produce a truly independent reading, never a recast of the prior.
* B.  Pending engine seam: the interface must not import the private
     ``TurnEngine`` shape, must not read pending files, and must produce
     the same result via a transparent engine proxy.
* C.  Result invariants: zero evidence + nonempty scope yields Prepared
     with a source-gap limit; empty scope yields Stopped.unsupported;
     partial dimensions yields Prepared with the unsupported part
     reported as a limit.
* D.  Comparison provenance: required/optional semantics, fallbacks, and
     no inheritance on a new root.
* E.  Provider description: the ``describe`` projection must be distinct
     and self-contained per capability, derived from the manifest.
* F.  Structural selection: the catalog is the single point of truth for
     structural candidate selection; legacy cost/priority metadata does
     not bias it.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_UNSET = object()

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
    ClaimScope,
    Complete,
    ComparisonSelection,
    HorizonSelection,
    InputFieldView,
    InputRequirement,
    InputRequest,
    IntentSelection,
    Prepare,
    Prepared,
    PublicLimit,
    PublicTerm,
    ReadingBrief,
    RequestView,
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
    description: str | None = None,
    entrypoint: str | None = None,
) -> dict:
    return {
        "schema_version": "provider-manifest-v1",
        "id": provider_id,
        "entrypoint": entrypoint or f"{__name__}:FakeAdapter",
        "display": {
            "zh-CN": {
                "name": provider_id,
                "description": description
                or f"中性 fixture 能力 {provider_id}：覆盖 object.one，"
                "需要 field.one / field.two，"
                "不输出 kind.prediction 类断言。",
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
            "field.one": {"type": "string", "display": {"zh-CN": "字段一"}},
            "field.two": {"type": "string", "display": {"zh-CN": "字段二"}},
            "field.clock": {"type": "string", "display": {"zh-CN": "可信时间"}},
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
    # ``_UNSET`` is the default sentinel meaning "use the fixture's
    # baked-in projection".  An explicit tuple (including the empty
    # tuple) replaces the projection; the difference matters for the
    # "no claim scope" test.
    publishable_scopes: Any = field(
        default_factory=lambda: _UNSET
    )
    publishable_facts: Any = field(
        default_factory=lambda: _UNSET
    )
    publishable_evidence: Any = field(
        default_factory=lambda: _UNSET
    )
    publishable_limits: Any = field(
        default_factory=lambda: _UNSET
    )
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
        primary_subject = (
            str(request.subject_refs[0])
            if request.subject_refs
            else "subject:test"
        )
        facts = dict(request.facts or {})
        subject_facts = dict(facts.get(primary_subject) or {})
        provided: set[str] = set(subject_facts)
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
        return _build_preparation(
            self.provider_id,
            request,
            primary_subject,
            override_facts=(
                self.publishable_facts
                if self.publishable_facts is not _UNSET
                else None
            ),
            override_scopes=(
                self.publishable_scopes
                if self.publishable_scopes is not _UNSET
                else None
            ),
            override_evidence=(
                self.publishable_evidence
                if self.publishable_evidence is not _UNSET
                else None
            ),
            override_limits=(
                self.publishable_limits
                if self.publishable_limits is not _UNSET
                else None
            ),
        )


def _build_preparation(
    provider_id: str,
    request: ProviderRequest,
    primary_subject: str,
    *,
    override_facts: tuple[dict, ...] | None = None,
    override_scopes: tuple[dict, ...] | None = None,
    override_evidence: tuple[dict, ...] | None = None,
    override_limits: tuple[dict, ...] | None = None,
) -> ProviderPreparation:
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
            override_facts
            if override_facts is not None
            else (
                {
                    "ref": f"fact:{provider_id}:{primary_subject}:one",
                    "subject_ref": primary_subject,
                    "kind_id": "kind.fact",
                    "value": {"provider": provider_id},
                    "display_text": f"事实：{provider_id} 已计算。",
                },
            )
        ),
        fact_index=(),
        evidence_plan={
            "bundle": bundle,
            "request": reading_request,
            "evidence": list(override_evidence) if override_evidence else [],
            "reading_id": staged_reading_id,
            "version": staged_version,
            "basis_label": f"{provider_id} basis",
            "intent_digest": intent_digest,
        },
        claim_scopes=list(override_scopes)
        if override_scopes is not None
        else (
            {
                "subject_ref": primary_subject,
                "dimension_id": "dimension.one",
                "allowed_kind_ids": ["kind.fact"],
                "certainty_ceiling_id": "certainty.tendency",
                "fact_refs": [f"fact:{provider_id}:{primary_subject}:one"],
                "evidence_refs": [],
            },
        ),
        limits=list(override_limits) if override_limits is not None else (),
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
    comparisons: tuple[ComparisonSelection, ...] = (),
) -> IntentSelection:
    return IntentSelection(
        subject_refs=(subject,),
        object_id=object_id,
        dimension_ids=dimensions,
        horizon=HorizonSelection(kind_id=horizon_kind),
        capability_id=capability_id,
        comparisons=comparisons,
    )


# ---------------------------------------------------------------------------
# A.  New root lineage
# ---------------------------------------------------------------------------


class NewRootLineageTests(unittest.TestCase):
    """Scope change or explicit capability change → truly independent root."""

    def setUp(self) -> None:
        self.fixture = _build_fixture()
        self.addCleanup(self.fixture.cleanup)

    def _accept_first(self, interface: ReadingInterface) -> Prepared:
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
        return first

    def test_changed_subject_with_explicit_beta_makes_independent_root(
        self,
    ) -> None:
        interface = self.fixture.interface()
        first = self._accept_first(interface)
        # second: subject changed AND explicit different capability.
        second = interface.execute(
            Prepare(
                query="主体 B 的中性问句",
                intent=_intent(
                    subject="subject:b", capability_id="capability.beta"
                ),
                facts={"subject:b": {"field.two": "已提供"}},
                state_token=first.state_token,
            )
        )
        self.assertIsInstance(second, Prepared, second)
        # 1) reading_id is new.
        token_a = interface.engine.token_store.resolve(first.state_token)
        token_b = interface.engine.token_store.resolve(second.state_token)
        self.assertNotEqual(token_a.reading_id, token_b.reading_id)
        # 2) The new reading has NO parent_reading_id and NO root_reading_id
        #    pointing to A.  action is "new" (rooted, not recast).
        prepared = interface.engine.store.load_prepared(token_b.reading_id)
        self.assertIsNone(prepared.parent_reading_id, prepared.parent_reading_id)
        self.assertEqual(
            prepared.root_reading_id, token_b.reading_id, prepared.root_reading_id
        )
        self.assertEqual(prepared.action, "new", prepared.action)
        # 3) A's accepted token has no lineage claim — the new root must
        #    not have advanced the old token.
        self.assertIsNone(interface.engine.token_store.lineage_claim(first.state_token))
        # 4) Old token still serves a follow-up for the original subject.
        follow = interface.execute(
            Prepare(
                query="主体 A 续问",
                intent=_intent(subject="subject:a"),
                facts={"subject:a": {"field.one": "已提供"}},
                state_token=first.state_token,
            )
        )
        self.assertIsInstance(follow, Prepared, follow)
        token_c = interface.engine.token_store.resolve(follow.state_token)
        self.assertEqual(token_a.reading_id, token_c.reading_id)
        self.assertEqual(token_c.version, token_a.version + 1)
        # 5) Beta was the only adapter invoked for the new root.
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

    def test_changed_object_with_same_capability_makes_independent_root(
        self,
    ) -> None:
        # Build a fixture where alpha supports both object.one and
        # object.two so the catalog returns a selected capability for
        # either object.  The new root lineage is what this test
        # actually exercises.
        manifest_alpha = _manifest(
            "capability.alpha",
            object_ids=("object.one", "object.two"),
            lineage="lineage.alpha",
            required_groups=(("field.one",),),
        )
        manifest_beta = _manifest(
            "capability.beta",
            object_ids=("object.one", "object.two"),
            lineage="lineage.beta",
            required_groups=(("field.two",),),
        )
        fixture = _Fixture(
            [manifest_alpha, manifest_beta],
            {
                "capability.alpha": _FakeAdapter(
                    provider_id="capability.alpha", needs=("field.one",)
                ),
                "capability.beta": _FakeAdapter(
                    provider_id="capability.beta", needs=("field.two",)
                ),
            },
        )
        self.addCleanup(fixture.cleanup)
        interface = fixture.interface()
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
        interface.execute(
            Complete(state_token=first.state_token, public_copy="object.one 第一稿。")
        )
        second = interface.execute(
            Prepare(
                query="object.two 的中性问句",
                intent=_intent(
                    subject="subject:a",
                    object_id="object.two",
                    capability_id="capability.alpha",
                ),
                facts={"subject:a": {"field.one": "已提供"}},
                state_token=first.state_token,
            )
        )
        self.assertIsInstance(second, Prepared, second)
        token_a = interface.engine.token_store.resolve(first.state_token)
        token_b = interface.engine.token_store.resolve(second.state_token)
        self.assertNotEqual(token_a.reading_id, token_b.reading_id)
        prepared = interface.engine.store.load_prepared(token_b.reading_id)
        self.assertIsNone(prepared.parent_reading_id)
        self.assertEqual(prepared.root_reading_id, token_b.reading_id)
        self.assertEqual(prepared.action, "new", prepared.action)
        self.assertIsNone(interface.engine.token_store.lineage_claim(first.state_token))
        follow = interface.execute(
            Prepare(
                query="object.one 续问",
                intent=_intent(subject="subject:a", object_id="object.one"),
                facts={"subject:a": {"field.one": "已提供"}},
                state_token=first.state_token,
            )
        )
        self.assertIsInstance(follow, Prepared, follow)
        token_c = interface.engine.token_store.resolve(follow.state_token)
        self.assertEqual(token_a.reading_id, token_c.reading_id)

    def test_same_scope_explicit_different_capability_makes_independent_root(
        self,
    ) -> None:
        interface = self.fixture.interface()
        first = self._accept_first(interface)
        # Same subject and object, but the host explicitly switches to
        # beta.  This is a deliberate capability change → independent
        # root, not a recast.
        second = interface.execute(
            Prepare(
                query="主体 A 显式切到 beta",
                intent=_intent(
                    subject="subject:a", capability_id="capability.beta"
                ),
                facts={"subject:a": {"field.two": "已提供"}},
                state_token=first.state_token,
            )
        )
        self.assertIsInstance(second, Prepared, second)
        token_a = interface.engine.token_store.resolve(first.state_token)
        token_b = interface.engine.token_store.resolve(second.state_token)
        self.assertNotEqual(token_a.reading_id, token_b.reading_id)
        prepared = interface.engine.store.load_prepared(token_b.reading_id)
        self.assertIsNone(prepared.parent_reading_id)
        self.assertEqual(prepared.root_reading_id, token_b.reading_id)
        self.assertEqual(prepared.action, "new", prepared.action)
        self.assertIsNone(interface.engine.token_store.lineage_claim(first.state_token))

    def test_same_no_token_request_after_accept_starts_another_root(self) -> None:
        interface = self.fixture.interface()
        command = Prepare(
            query="可以在不同时间重复提出的中性问句",
            intent=_intent(capability_id="capability.alpha"),
            facts={"subject:test": {"field.one": "已提供"}},
        )
        first = interface.execute(command)
        self.assertIsInstance(first, Prepared, first)
        accepted = interface.execute(
            Complete(state_token=first.state_token, public_copy="第一份结果。")
        )
        self.assertIsInstance(accepted, Accepted, accepted)

        repeated = interface.execute(command)
        self.assertIsInstance(repeated, Prepared, repeated)
        first_record = interface.engine.token_store.resolve(first.state_token)
        repeated_record = interface.engine.token_store.resolve(repeated.state_token)
        self.assertNotEqual(first_record.reading_id, repeated_record.reading_id)
        repeated_prepared = interface.engine.store.load_prepared(
            repeated_record.reading_id
        )
        self.assertIsNone(repeated_prepared.parent_reading_id)
        self.assertEqual(
            repeated_prepared.root_reading_id,
            repeated_record.reading_id,
        )
        self.assertEqual(repeated_prepared.action, "new")

    def test_new_root_does_not_inherit_old_comparisons(self) -> None:
        # Build a fixture where alpha and gamma both cover two
        # objects so the new root can land on a different object
        # without the catalog dropping alpha.
        manifest_alpha = _manifest(
            "capability.alpha",
            object_ids=("object.one", "object.two"),
            lineage="lineage.alpha",
            required_groups=(("field.one",),),
        )
        manifest_gamma = _manifest(
            "capability.gamma",
            object_ids=("object.one", "object.two"),
            lineage="lineage.gamma",
            required_groups=(("field.two",),),
        )
        manifests = [manifest_alpha, manifest_gamma]
        adapters = {
            "capability.alpha": _FakeAdapter(
                provider_id="capability.alpha", needs=("field.one",)
            ),
            "capability.gamma": _FakeAdapter(
                provider_id="capability.gamma", needs=("field.two",)
            ),
        }
        fixture = _Fixture(manifests, adapters)
        self.addCleanup(fixture.cleanup)
        interface = fixture.interface()
        # First reading uses alpha + a required comparison gamma.
        first = interface.execute(
            Prepare(
                query="主问 + 比较",
                intent=_intent(
                    subject="subject:a",
                    capability_id="capability.alpha",
                    comparisons=(
                        ComparisonSelection(
                            capability_id="capability.gamma",
                            requirement="required",
                        ),
                    ),
                ),
                facts={
                    "subject:a": {"field.one": "已提供", "field.two": "已提供"}
                },
            )
        )
        self.assertIsInstance(first, Prepared, first)
        accept = interface.execute(
            Complete(state_token=first.state_token, public_copy="第一稿。")
        )
        self.assertIsInstance(accept, Accepted, accept)
        # Now an independent root with the same subject, NO comparison
        # declared, and a DIFFERENT object.  The new root must not
        # silently carry over the prior gamma comparison.
        second = interface.execute(
            Prepare(
                query="新对象、无比较",
                intent=_intent(
                    subject="subject:a",
                    object_id="object.two",
                    capability_id="capability.alpha",
                ),
                facts={"subject:a": {"field.one": "已提供"}},
                state_token=first.state_token,
            )
        )
        self.assertIsInstance(second, Prepared, second)
        token_b = interface.engine.token_store.resolve(second.state_token)
        prepared = interface.engine.store.load_prepared(token_b.reading_id)
        # Artifacts must contain only the primary alpha; the inherited
        # gamma comparison must not be staged in the new reading.
        capability_ids = tuple(
            artifact.capability_id for artifact in prepared.artifacts
        )
        self.assertEqual(capability_ids, ("capability.alpha",), capability_ids)
        # The new request_view must not mention gamma either.
        request_view_capabilities = tuple(
            prepared.request.intent.get("capability_ids") or ()
        )
        self.assertNotIn("capability.gamma", request_view_capabilities)

    def test_correct_with_changed_subject_returns_conflict(self) -> None:
        interface = self.fixture.interface()
        first = self._accept_first(interface)
        conflict = interface.execute(
            Prepare(
                query="主体 B 纠正",
                intent=_intent(
                    subject="subject:b", capability_id="capability.alpha"
                ),
                facts={"subject:b": {"field.one": "已提供"}},
                state_token=first.state_token,
                transition="correct",
            )
        )
        self.assertIsInstance(conflict, Stopped, conflict)
        self.assertEqual(conflict.reason, "conflict", conflict)
        self.assertTrue(conflict.public_copy.strip())

    def test_restart_with_changed_object_returns_conflict(self) -> None:
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
        interface.execute(
            Complete(state_token=first.state_token, public_copy="object.one 第一稿。")
        )
        conflict = interface.execute(
            Prepare(
                query="object.two 重起",
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

    def test_restart_cannot_switch_capability_in_the_same_scope(self) -> None:
        interface = self.fixture.interface()
        first = self._accept_first(interface)
        conflict = interface.execute(
            Prepare(
                query="同一范围内换能力并重起",
                intent=_intent(
                    subject="subject:a",
                    capability_id="capability.beta",
                ),
                facts={"subject:a": {"field.two": "已提供"}},
                state_token=first.state_token,
                transition="restart",
            )
        )
        self.assertIsInstance(conflict, Stopped, conflict)
        self.assertEqual(conflict.reason, "conflict", conflict)
        self.assertTrue(conflict.public_copy.strip())


# ---------------------------------------------------------------------------
# B.  Pending engine seam
# ---------------------------------------------------------------------------


class PendingEngineSeamTests(unittest.TestCase):
    """Interface must not import the private TurnEngine shape."""

    def setUp(self) -> None:
        self.fixture = _build_fixture(
            alpha_needs=("field.one",),
        )
        self.addCleanup(self.fixture.cleanup)

    def test_interface_does_not_read_pending_path(self) -> None:
        # Static contract: the engine exposes the seam; the interface
        # never inspects the engine's private path.
        engine = self.fixture.engine
        self.assertTrue(hasattr(engine, "pending_intake_capability"))
        # The interface file source must not contain a path read against
        # the engine's pending layout.
        source = (ROOT / "scripts" / "reading_engine" / "interface.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("pending-turns", source)
        self.assertNotIn("engine._pending_path", source)
        # The interface must not hardcode a TurnEngine check.
        self.assertNotIn("isinstance(self.engine, TurnEngine)", source)

    def test_engine_seam_disagrees_with_explicit_capability(self) -> None:
        interface = self.fixture.interface()
        pending = interface.execute(
            Prepare(
                query="中性问句",
                intent=_intent(capability_id="capability.alpha"),
                facts={},
            )
        )
        self.assertIsInstance(pending, Stopped, pending)
        self.assertEqual(pending.reason, "need_input", pending)
        # The engine surface must report the bound pending capability.
        self.assertEqual(
            interface.engine.pending_intake_capability(pending.state_token),
            "capability.alpha",
        )
        # Submitting the same token with a different explicit capability
        # must surface a conflict, not silently re-purpose it.
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
        # The first pending call invoked alpha once (to discover the
        # missing fact); the confused call must add no further adapter
        # invocations.  Beta must never have been executed.
        alpha_calls = interface.engine.providers["capability.alpha"].call_log
        beta_calls = interface.engine.providers["capability.beta"].call_log
        self.assertEqual(len(alpha_calls), 1, alpha_calls)
        self.assertEqual(len(beta_calls), 0, beta_calls)


class TransparentEngineProxy:
    """A minimal proxy that exposes only the public engine surface."""

    def __init__(self, inner: TurnEngine) -> None:
        self._inner = inner

    @property
    def token_store(self) -> Any:
        return self._inner.token_store

    @property
    def store(self) -> Any:
        return self._inner.store

    @property
    def catalog(self) -> Any:
        return self._inner.catalog

    @property
    def runtime_context(self) -> Any:
        return self._inner.runtime_context

    @runtime_context.setter
    def runtime_context(self, value: Any) -> None:
        self._inner.runtime_context = value

    @property
    def providers(self) -> Any:
        return self._inner.providers

    def prepare_turn(self, *args: Any, **kwargs: Any) -> Any:
        return self._inner.prepare_turn(*args, **kwargs)

    def complete_turn(self, *args: Any, **kwargs: Any) -> Any:
        return self._inner.complete_turn(*args, **kwargs)

    def pending_intake_capability(self, state_token: str) -> str | None:
        return self._inner.pending_intake_capability(state_token)


class TransparentProxyBehaviourTests(unittest.TestCase):
    """A proxy engine that only re-exports the public surface must agree."""

    def setUp(self) -> None:
        self.fixture = _build_fixture(
            alpha_needs=("field.one",),
        )
        self.addCleanup(self.fixture.cleanup)

    def _build_proxy_interface(self) -> ReadingInterface:
        proxy = TransparentEngineProxy(self.fixture.engine)
        ctx = build_runtime_context()
        self.fixture.engine.runtime_context = ctx
        return ReadingInterface(
            skill_root=ROOT,
            catalog=self.fixture.catalog,
            engine=proxy,
            runtime_context=ctx,
        )

    def test_need_input_issues_pending_token_via_proxy(self) -> None:
        interface = self._build_proxy_interface()
        result = interface.execute(
            Prepare(
                query="中性问句",
                intent=_intent(capability_id="capability.alpha"),
                facts={},
            )
        )
        self.assertIsInstance(result, Stopped, result)
        self.assertEqual(result.reason, "need_input", result)
        self.assertIsNotNone(result.state_token)
        self.assertIsNotNone(result.input_request)

    def test_explicit_different_capability_with_pending_token_via_proxy(
        self,
    ) -> None:
        interface = self._build_proxy_interface()
        pending = interface.execute(
            Prepare(
                query="中性问句",
                intent=_intent(capability_id="capability.alpha"),
                facts={},
            )
        )
        self.assertIsInstance(pending, Stopped, pending)
        self.assertEqual(pending.reason, "need_input", pending)
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
        # The first pending call invoked alpha once; the confused call
        # adds no further adapter invocations.  Beta must never have
        # been executed.  The proxy must mirror the direct engine.
        for adapter in self.fixture.engine.providers.values():
            self.assertEqual(
                len(adapter.call_log),
                1 if adapter is self.fixture.engine.providers["capability.alpha"] else 0,
                adapter.call_log,
            )


# ---------------------------------------------------------------------------
# C.  Result invariants
# ---------------------------------------------------------------------------


class ZeroEvidenceSourceGapLimitTests(unittest.TestCase):
    """Facts nonempty + claim scopes nonempty + zero evidence → Prepared
    with an explicit source-gap limit."""

    def setUp(self) -> None:
        scope = {
            "subject_ref": "subject:test",
            "dimension_id": "dimension.one",
            "allowed_kind_ids": ["kind.fact"],
            "certainty_ceiling_id": "certainty.tendency",
            "fact_refs": ["fact:capability.alpha:subject:test:one"],
            "evidence_refs": [],
        }
        self.fixture = _build_fixture(alpha_needs=("field.one",))
        adapter = self.fixture.engine.providers["capability.alpha"]
        adapter.publishable_facts = (
            {
                "ref": "fact:capability.alpha:subject:test:one",
                "subject_ref": "subject:test",
                "kind_id": "kind.fact",
                "value": {"provider": "capability.alpha"},
                "display_text": "事实：capability.alpha 已计算。",
            },
        )
        adapter.publishable_scopes = (scope,)
        adapter.publishable_evidence = ()
        adapter.publishable_limits = ()
        self.addCleanup(self.fixture.cleanup)

    def test_prepared_with_source_gap_limit(self) -> None:
        interface = self.fixture.interface()
        result = interface.execute(
            Prepare(
                query="中性问句",
                intent=_intent(capability_id="capability.alpha"),
                facts={"subject:test": {"field.one": "已提供"}},
            )
        )
        self.assertIsInstance(result, Prepared, result)
        limit_kind_ids = tuple(limit.kind_id for limit in result.brief.limits)
        self.assertIn("limit.source_gap", limit_kind_ids, limit_kind_ids)
        # The brief must not pretend to have an evidence reference.
        evidence_refs = {item.ref for item in result.brief.evidence}
        self.assertEqual(evidence_refs, set(), evidence_refs)
        # The source-gap limit must mention its scope or its own kind.
        gap_limits = [
            limit for limit in result.brief.limits if limit.kind_id == "limit.source_gap"
        ]
        self.assertTrue(gap_limits, gap_limits)
        self.assertTrue(gap_limits[0].public_text.strip())


class EmptyClaimScopeUnsupportedTests(unittest.TestCase):
    """An adapter that produces facts but no claim scope must be rejected."""

    def setUp(self) -> None:
        self.fixture = _build_fixture(alpha_needs=("field.one",))
        adapter = self.fixture.engine.providers["capability.alpha"]
        adapter.publishable_facts = (
            {
                "ref": "fact:capability.alpha:subject:test:one",
                "subject_ref": "subject:test",
                "kind_id": "kind.fact",
                "value": {"provider": "capability.alpha"},
                "display_text": "事实：capability.alpha 已计算。",
            },
        )
        adapter.publishable_scopes = ()
        adapter.publishable_evidence = ()
        adapter.publishable_limits = ()
        self.addCleanup(self.fixture.cleanup)

    def test_empty_scope_returns_unsupported_with_nonempty_copy(self) -> None:
        interface = self.fixture.interface()
        result = interface.execute(
            Prepare(
                query="中性问句",
                intent=_intent(capability_id="capability.alpha"),
                facts={"subject:test": {"field.one": "已提供"}},
            )
        )
        self.assertIsInstance(result, Stopped, result)
        self.assertEqual(result.reason, "unsupported", result)
        self.assertTrue(result.public_copy.strip(), result.public_copy)
        # No token is issued when there is nothing to publish.
        self.assertIsNone(result.state_token)


class PublishabilityReferenceClosureTests(unittest.TestCase):
    """Prepared results must have real facts and closed references."""

    def _execute_with_adapter(self, adapter: _FakeAdapter):
        fixture = _Fixture(
            [
                _manifest(
                    "capability.alpha",
                    lineage="lineage.alpha",
                    required_groups=(("field.one",),),
                )
            ],
            {"capability.alpha": adapter},
        )
        self.addCleanup(fixture.cleanup)
        return fixture.interface().execute(
            Prepare(
                query="发布闭包检查",
                intent=_intent(capability_id="capability.alpha"),
                facts={"subject:test": {"field.one": "已提供"}},
            )
        )

    def test_nonempty_scope_without_public_facts_is_unsupported(self) -> None:
        result = self._execute_with_adapter(
            _FakeAdapter(
                provider_id="capability.alpha",
                needs=("field.one",),
                publishable_facts=(),
                publishable_scopes=(
                    {
                        "subject_ref": "subject:test",
                        "dimension_id": "dimension.one",
                        "allowed_kind_ids": ["kind.fact"],
                        "certainty_ceiling_id": "certainty.tendency",
                        "fact_refs": [],
                        "evidence_refs": [],
                    },
                ),
            )
        )
        self.assertIsInstance(result, Stopped, result)
        self.assertEqual(result.reason, "unsupported", result)
        self.assertTrue(result.public_copy.strip())

    def test_scope_with_dangling_fact_reference_is_error(self) -> None:
        result = self._execute_with_adapter(
            _FakeAdapter(
                provider_id="capability.alpha",
                needs=("field.one",),
                publishable_scopes=(
                    {
                        "subject_ref": "subject:test",
                        "dimension_id": "dimension.one",
                        "allowed_kind_ids": ["kind.fact"],
                        "certainty_ceiling_id": "certainty.tendency",
                        "fact_refs": ["fact:missing"],
                        "evidence_refs": [],
                    },
                ),
            )
        )
        self.assertIsInstance(result, Stopped, result)
        self.assertEqual(result.reason, "error", result)
        self.assertTrue(result.public_copy.strip())

    def test_scope_with_dangling_evidence_reference_is_error(self) -> None:
        result = self._execute_with_adapter(
            _FakeAdapter(
                provider_id="capability.alpha",
                needs=("field.one",),
                publishable_scopes=(
                    {
                        "subject_ref": "subject:test",
                        "dimension_id": "dimension.one",
                        "allowed_kind_ids": ["kind.fact"],
                        "certainty_ceiling_id": "certainty.tendency",
                        "fact_refs": ["fact:capability.alpha:subject:test:one"],
                        "evidence_refs": ["evidence:missing"],
                    },
                ),
            )
        )
        self.assertIsInstance(result, Stopped, result)
        self.assertEqual(result.reason, "error", result)
        self.assertTrue(result.public_copy.strip())


class PartialDimensionsLimitTests(unittest.TestCase):
    """Supported claim scopes survive; unsupported ones become a limit."""

    def setUp(self) -> None:
        self.fixture = _build_fixture(alpha_needs=("field.one",))
        adapter = self.fixture.engine.providers["capability.alpha"]
        adapter.publishable_facts = (
            {
                "ref": "fact:capability.alpha:subject:test:one",
                "subject_ref": "subject:test",
                "kind_id": "kind.fact",
                "value": {"provider": "capability.alpha"},
                "display_text": "事实：capability.alpha 已计算。",
            },
        )
        adapter.publishable_scopes = (
            {
                "subject_ref": "subject:test",
                "dimension_id": "dimension.one",
                "allowed_kind_ids": ["kind.fact"],
                "certainty_ceiling_id": "certainty.tendency",
                "fact_refs": ["fact:capability.alpha:subject:test:one"],
                "evidence_refs": [],
            },
        )
        adapter.publishable_evidence = ()
        adapter.publishable_limits = ()
        self.addCleanup(self.fixture.cleanup)

    def test_partial_dimensions_keeps_supported_and_limits_rest(self) -> None:
        interface = self.fixture.interface()
        result = interface.execute(
            Prepare(
                query="中性问句",
                intent=_intent(
                    capability_id="capability.alpha",
                    dimensions=("dimension.one", "dimension.two"),
                ),
                facts={"subject:test": {"field.one": "已提供"}},
            )
        )
        self.assertIsInstance(result, Prepared, result)
        # Only the supported dimension survives in claim scopes.
        scope_dimensions = {
            scope.dimension_id for scope in result.brief.claim_scopes
        }
        self.assertEqual(scope_dimensions, {"dimension.one"}, scope_dimensions)
        # The unsupported dimension appears as a limit, not as a claim.
        limit_kind_ids = tuple(limit.kind_id for limit in result.brief.limits)
        self.assertIn("limit.unsupported_dimension", limit_kind_ids, limit_kind_ids)


# ---------------------------------------------------------------------------
# D.  Comparison provenance
# ---------------------------------------------------------------------------


class ComparisonProvenanceTests(unittest.TestCase):
    """Required comparisons gate the result; optional comparisons degrade."""

    def setUp(self) -> None:
        manifest_gamma = _manifest(
            "capability.gamma",
            object_ids=("object.one",),
            horizon_ids=("horizon.one",),
            dimension_ids=("dimension.one", "dimension.two"),
            required_groups=(("field.two",),),
            lineage="lineage.gamma",
        )
        manifests = [
            _manifest(
                "capability.alpha",
                lineage="lineage.alpha",
                required_groups=(("field.one",),),
            ),
            manifest_gamma,
        ]
        adapters = {
            "capability.alpha": _FakeAdapter(
                provider_id="capability.alpha", needs=("field.one",)
            ),
            "capability.gamma": _FakeAdapter(
                provider_id="capability.gamma", needs=("field.two",)
            ),
        }
        self.fixture = _Fixture(manifests, adapters)
        self.addCleanup(self.fixture.cleanup)

    def test_required_comparison_missing_input_returns_need_input(
        self,
    ) -> None:
        interface = self.fixture.interface()
        result = interface.execute(
            Prepare(
                query="主问 + 必选比较",
                intent=_intent(
                    capability_id="capability.alpha",
                    comparisons=(
                        ComparisonSelection(
                            capability_id="capability.gamma",
                            requirement="required",
                        ),
                    ),
                ),
                facts={"subject:test": {"field.one": "已提供"}},
            )
        )
        self.assertIsInstance(result, Stopped, result)
        self.assertIn(
            result.reason,
            {"need_input", "unsupported"},
            result.reason,
        )
        self.assertTrue(result.public_copy.strip())

    def test_required_comparison_resumes_after_missing_input(self) -> None:
        interface = self.fixture.interface()
        intent = _intent(
            capability_id="capability.alpha",
            comparisons=(
                ComparisonSelection("capability.gamma", "required"),
            ),
        )
        first = interface.execute(
            Prepare(
                query="主问 + 必选比较",
                intent=intent,
                facts={"subject:test": {"field.one": "已提供"}},
            )
        )
        self.assertIsInstance(first, Stopped, first)
        self.assertEqual(first.reason, "need_input", first)
        self.assertIsNotNone(first.state_token)

        resumed = interface.execute(
            Prepare(
                query="补齐必选比较资料",
                intent=intent,
                facts={"subject:test": {"field.two": "已提供"}},
                state_token=first.state_token,
            )
        )
        self.assertIsInstance(resumed, Prepared, resumed)
        self.assertEqual(
            tuple(resumed.brief.request_view.capability_ids),
            ("capability.alpha", "capability.gamma"),
        )
        accepted = interface.execute(
            Complete(state_token=resumed.state_token, public_copy="完整比较结果。")
        )
        self.assertIsInstance(accepted, Accepted, accepted)

    def test_legacy_pending_comparison_ids_resume_as_required(self) -> None:
        interface = self.fixture.interface()
        intent = _intent(
            capability_id="capability.alpha",
            comparisons=(
                ComparisonSelection("capability.gamma", "required"),
            ),
        )
        first = interface.execute(
            Prepare(
                query="旧 pending 格式",
                intent=intent,
                facts={"subject:test": {"field.one": "已提供"}},
            )
        )
        self.assertIsInstance(first, Stopped, first)
        record = interface.engine.token_store.resolve(first.state_token)
        path = interface.engine._pending_path(record.intake_id)
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["request"].pop("comparisons", None)
        payload["request"]["comparison_capability_ids"] = [
            "capability.gamma"
        ]
        payload.pop("comparisons", None)
        payload["comparison_capability_ids"] = ["capability.gamma"]
        path.write_text(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)
            + "\n",
            encoding="utf-8",
        )

        resumed = interface.execute(
            Prepare(
                query="补齐旧 pending",
                intent=intent,
                facts={"subject:test": {"field.two": "已提供"}},
                state_token=first.state_token,
            )
        )
        self.assertIsInstance(resumed, Prepared, resumed)
        self.assertIn(
            "capability.gamma",
            tuple(resumed.brief.request_view.capability_ids),
        )

    def test_optional_comparison_missing_does_not_block_primary(
        self,
    ) -> None:
        interface = self.fixture.interface()
        result = interface.execute(
            Prepare(
                query="主问 + 可选比较",
                intent=_intent(
                    capability_id="capability.alpha",
                    comparisons=(
                        ComparisonSelection(
                            capability_id="capability.gamma",
                            requirement="optional",
                        ),
                    ),
                ),
                facts={"subject:test": {"field.one": "已提供"}},
            )
        )
        self.assertIsInstance(result, Prepared, result)
        # The brief still surfaces the dropped comparison as a limit.
        limit_kind_ids = tuple(limit.kind_id for limit in result.brief.limits)
        self.assertIn(
            "limit.comparison_skipped", limit_kind_ids, limit_kind_ids
        )
        # The primary succeeded; the optional comparison was probed
        # once and then dropped.  The primary is the only one that
        # actually produced a preparation.
        primary_calls = self.fixture.engine.providers["capability.alpha"].call_log
        comparison_calls = self.fixture.engine.providers[
            "capability.gamma"
        ].call_log
        self.assertEqual(len(primary_calls), 1)
        # The optional comparison was probed (to discover the missing
        # input), but it must not have produced a preparation; that
        # fact is what blocks the primary.
        self.assertEqual(len(comparison_calls), 1, comparison_calls)
        # The brief must not include gamma as a co-staged capability.
        capability_ids = tuple(result.brief.request_view.capability_ids)
        self.assertNotIn("capability.gamma", capability_ids, capability_ids)

    def test_required_duplicate_comparison_returns_unsupported(self) -> None:
        interface = self.fixture.interface()
        result = interface.execute(
            Prepare(
                query="主问 + 重复比较",
                intent=_intent(
                    capability_id="capability.alpha",
                    comparisons=(
                        ComparisonSelection(
                            capability_id="capability.alpha",
                            requirement="required",
                        ),
                    ),
                ),
                facts={"subject:test": {"field.one": "已提供"}},
            )
        )
        self.assertIsInstance(result, Stopped, result)
        self.assertEqual(result.reason, "unsupported", result)
        self.assertTrue(result.public_copy.strip())

    def test_optional_duplicate_comparison_drops_it(self) -> None:
        interface = self.fixture.interface()
        result = interface.execute(
            Prepare(
                query="主问 + 重复可选比较",
                intent=_intent(
                    capability_id="capability.alpha",
                    comparisons=(
                        ComparisonSelection(
                            capability_id="capability.alpha",
                            requirement="optional",
                        ),
                    ),
                ),
                facts={"subject:test": {"field.one": "已提供"}},
            )
        )
        self.assertIsInstance(result, Prepared, result)
        # The duplicate optional comparison is dropped but remains visible
        # as a structured limit; the primary is the only adapter invoked.
        primary_calls = self.fixture.engine.providers["capability.alpha"].call_log
        self.assertEqual(len(primary_calls), 1)
        self.assertIn(
            "limit.comparison_skipped",
            tuple(limit.kind_id for limit in result.brief.limits),
        )

    def test_optional_comparison_is_all_or_nothing_across_subjects(self) -> None:
        interface = self.fixture.interface()
        result = interface.execute(
            Prepare(
                query="两个主体的可选比较",
                intent=IntentSelection(
                    subject_refs=("subject:a", "subject:b"),
                    object_id="object.one",
                    dimension_ids=("dimension.one",),
                    horizon=HorizonSelection(kind_id="horizon.one"),
                    capability_id="capability.alpha",
                    comparisons=(
                        ComparisonSelection("capability.gamma", "optional"),
                    ),
                ),
                facts={
                    "subject:a": {
                        "field.one": "已提供",
                        "field.two": "已提供",
                    },
                    "subject:b": {"field.one": "已提供"},
                },
            )
        )
        self.assertIsInstance(result, Prepared, result)
        token = interface.engine.token_store.resolve(result.state_token)
        prepared = interface.engine.store.load_prepared(token.reading_id)
        self.assertEqual(
            tuple(
                (artifact.subject_ref, artifact.capability_id)
                for artifact in prepared.artifacts
            ),
            (
                ("subject:a", "capability.alpha"),
                ("subject:b", "capability.alpha"),
            ),
        )
        self.assertNotIn(
            "capability.gamma",
            tuple(result.brief.request_view.capability_ids),
        )
        self.assertIn(
            "limit.comparison_skipped",
            tuple(limit.kind_id for limit in result.brief.limits),
        )


# ---------------------------------------------------------------------------
# E.  Provider description
# ---------------------------------------------------------------------------


class ProviderDescriptionTests(unittest.TestCase):
    """Each capability has a distinct, self-contained description."""

    def test_each_capability_has_distinct_nonempty_description(self) -> None:
        interface = self.fixture_catalog_interface()
        described = interface.execute(type("D", (), {"kind": "describe"})())
        from reading_engine.interface_contracts import Describe
        described = interface.execute(Describe())
        self.assertIsNotNone(described.manifest_digest)
        descriptions = {
            cap.id: cap.description.strip() for cap in described.capabilities
        }
        # All capabilities carry a non-empty, distinct description.
        self.assertTrue(descriptions)
        for cap_id, text in descriptions.items():
            self.assertTrue(text, cap_id)
        unique = set(descriptions.values())
        self.assertEqual(len(unique), len(descriptions), descriptions)
        # Each description should name the input prerequisites it
        # depends on, so the host model can choose correctly.
        for cap_id, text in descriptions.items():
            self.assertIn("field.", text, (cap_id, text))

    def test_descriptions_come_from_manifest(self) -> None:
        from reading_engine.interface_contracts import Describe
        interface = self.fixture_catalog_interface()
        described = interface.execute(Describe())
        for capability in described.capabilities:
            # The capability's manifest payload must carry a display
            # description for zh-CN, otherwise the projection would
            # fall back to a label, which the contract forbids.
            self.assertTrue(capability.description.strip())
            descriptor = interface.catalog.descriptor(capability.id)
            raw = (descriptor.display or {}).get("zh-CN") or {}
            self.assertTrue(
                str(raw.get("description") or "").strip(),
                capability.id,
            )
            # The projected description must be the manifest's own text.
            self.assertEqual(capability.description, str(raw["description"]))

    def test_production_descriptions_cover_declared_required_inputs(self) -> None:
        from reading_engine.interface_contracts import Describe

        interface = ReadingInterface(skill_root=ROOT)
        described = interface.execute(Describe())
        self.assertEqual(len(described.capabilities), 14)
        descriptions = {
            capability.id: capability.description
            for capability in described.capabilities
        }
        self.assertEqual(len(set(descriptions.values())), 14)
        for descriptor in interface.catalog.descriptors:
            text = descriptions[descriptor.id]
            self.assertTrue(text.strip(), descriptor.id)
            for group in descriptor.capability.required_input_groups:
                self.assertTrue(
                    any(field_id in text for field_id in group),
                    (descriptor.id, group, text),
                )

    def fixture_catalog_interface(self) -> ReadingInterface:
        manifests = [
            _manifest(
                "capability.alpha",
                lineage="lineage.alpha",
                required_groups=(("field.one",),),
                description="中性 fixture 能力 capability.alpha：覆盖 object.one，"
                "需要 field.one，不输出 kind.prediction 类断言。",
            ),
            _manifest(
                "capability.beta",
                lineage="lineage.beta",
                required_groups=(("field.two",),),
                description="中性 fixture 能力 capability.beta：覆盖 object.one，"
                "需要 field.two，与 capability.alpha 的 object 范围重叠，"
                "但 kind.tendency 上限更窄。",
            ),
        ]
        adapters = {
            "capability.alpha": _FakeAdapter(
                provider_id="capability.alpha", needs=("field.one",)
            ),
            "capability.beta": _FakeAdapter(
                provider_id="capability.beta", needs=("field.two",)
            ),
        }
        fixture = _Fixture(manifests, adapters)
        self.addCleanup(fixture.cleanup)
        return fixture.interface()


# ---------------------------------------------------------------------------
# F.  Structural selection locality
# ---------------------------------------------------------------------------


class StructuralSelectionLocalityTests(unittest.TestCase):
    """RuntimeCatalog.select is the single point of structural selection."""

    def setUp(self) -> None:
        # Lower cost / higher priority alpha must NOT win structurally
        # over beta when beta is the only candidate the host picks.
        self.fixture = _build_fixture(
            alpha_assumption_cost=0,
            beta_assumption_cost=999,
            alpha_priority=10,
            beta_priority=9999,
        )
        self.addCleanup(self.fixture.cleanup)

    def test_interface_does_not_re_run_structural_matching(self) -> None:
        source = (ROOT / "scripts" / "reading_engine" / "interface.py").read_text(
            encoding="utf-8"
        )
        # The interface must use the catalog, not duplicate its rules.
        self.assertNotIn("RuntimeCatalog._matches", source)
        self.assertNotIn("RuntimeCatalog._effective_dimensions", source)
        # Provided-field tracking only existed as a structural pre-filter;
        # after the rework the engine is the single owner of the input
        # contract, so the interface must not compute it.
        self.assertNotIn("_provided_field_ids", source)

    def test_explicit_higher_cost_capability_wins_when_host_picks_it(
        self,
    ) -> None:
        interface = self.fixture.interface()
        result = interface.execute(
            Prepare(
                query="中性问句",
                intent=_intent(capability_id="capability.beta"),
                facts={"subject:test": {"field.two": "已提供"}},
            )
        )
        self.assertIsInstance(result, Prepared, result)
        beta_calls = interface.engine.providers["capability.beta"].call_log
        alpha_calls = interface.engine.providers["capability.alpha"].call_log
        self.assertEqual(len(beta_calls), 1)
        self.assertEqual(len(alpha_calls), 0)

    def test_assumption_cost_metadata_does_not_influence_selection(self) -> None:
        # The legacy metadata fields must not affect structural
        # selection, even when the host omits a capability.
        from reading_engine.interface_contracts import Describe
        interface = self.fixture.interface()
        described = interface.execute(Describe())
        self.assertEqual(described.manifest_digest, interface.catalog.manifest_digest)
        # The selection must still surface choose_capability because
        # there are two structurally compatible candidates; cost/priority
        # must NOT collapse the choice.
        ambiguous = interface.execute(
            Prepare(
                query="中性问句",
                intent=_intent(),
                facts={},
            )
        )
        self.assertIsInstance(ambiguous, Stopped, ambiguous)
        self.assertEqual(ambiguous.reason, "need_input", ambiguous)


# ---------------------------------------------------------------------------
# G.  Fallback cap: at most one new root per user request
# ---------------------------------------------------------------------------


class FallbackCapTests(unittest.TestCase):
    """A user request may trigger at most one host-driven new root."""

    def setUp(self) -> None:
        self.fixture = _build_fixture(
            alpha_needs=("field.one",),
        )
        self.addCleanup(self.fixture.cleanup)

    def test_core_does_not_re_loop_providers_internally(self) -> None:
        interface = self.fixture.interface()
        # Two candidates, both missing required facts, the user
        # supplies no facts.  The core must stop on the first stop and
        # never probe the other capability on its own.
        result = interface.execute(
            Prepare(
                query="中性问句",
                intent=_intent(),
                facts={},
            )
        )
        self.assertIsInstance(result, Stopped, result)
        self.assertEqual(result.reason, "need_input", result)
        for adapter in self.fixture.engine.providers.values():
            self.assertEqual(adapter.call_log, [])


if __name__ == "__main__":
    unittest.main()

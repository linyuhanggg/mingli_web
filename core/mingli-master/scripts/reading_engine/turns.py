"""Slim token-driven turn engine over provider adapters.

One production chain only: a descriptor-resolved adapter prepares a turn,
the engine stages the private record, hands the caller an opaque token,
and later commits exactly one non-empty answer per prepared state.  No
domain word appears here; every provider-specific behaviour lives behind
``ProviderAdapter.prepare``.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping

from .contracts import (
    AcceptedReading,
    EvidenceBundle,
    InternalFailure,
    Judgment,
    JudgmentDimension,
    NeedUserFact,
    PreparedArtifact,
    PreparedReadingRecord,
    ReadingRecord,
    canonical_digest,
)
from .provider_protocol import (
    ProviderActionError,
    ProviderContext,
    ProviderNeedInput,
    ProviderPreparation,
    ProviderRequest,
    ProviderUnsupported,
    ResolvedComparison,
)
from .state_token import StateTokenStore, TokenConflict
from .storage import AtomicReadingStore, _atomic_replace

# Retained type alias: legacy tests referenced the draft generator type even
# though the runtime never invokes a model.  The engine has no drafting hook.
DraftGenerator = Any

_SAFE_FAILURE = "The V4 transaction did not produce a complete result."


@dataclass(frozen=True)
class TurnOutcome:
    """One prepare turn: the engine outcome plus the caller's next token."""

    result: Any
    state_token: str | None
    preparation: ProviderPreparation | None = None
    prior_answer: str | None = None
    missing_fields: tuple[str, ...] = ()
    missing_input_groups: tuple[tuple[str, ...], ...] = ()
    missing_descriptor_id: str | None = None


@dataclass(frozen=True)
class _UnsupportedTurn:
    reason_id: str
    status: str = "unsupported_dimension"


class TurnEngine:
    """Prepare/complete state machine with atomic first-commit-wins."""

    def __init__(
        self,
        *,
        store: AtomicReadingStore,
        providers: Mapping[str, Any],
        token_store: StateTokenStore | None = None,
        catalog: Any | None = None,
        runtime_context: Any | None = None,
    ) -> None:
        self.store = store
        self.providers = dict(providers)
        self.token_store = token_store or StateTokenStore(
            Path(self.store.root) / "state-tokens"
        )
        self.catalog = catalog
        self.runtime_context = runtime_context
        self._projections = Path(self.store.root) / "projections"

    # -- prepare ------------------------------------------------------------

    def prepare_turn(
        self,
        descriptor: Any,
        provider_request: ProviderRequest,
        *,
        state_token: str | None = None,
        transition: str | None = None,
        comparison_descriptors: tuple[ResolvedComparison, ...] = (),
    ) -> TurnOutcome:
        try:
            token_record = (
                self.token_store.resolve(state_token)
                if state_token is not None
                else None
            )
            if token_record is not None and token_record.phase in (
                "accepted",
                "pending_input",
            ):
                with self.token_store.advance_lock(state_token):
                    return self._prepare_turn(
                        descriptor,
                        provider_request,
                        state_token=state_token,
                        transition=transition,
                        comparison_descriptors=comparison_descriptors,
                    )
            return self._prepare_turn(
                descriptor,
                provider_request,
                state_token=state_token,
                transition=transition,
                comparison_descriptors=comparison_descriptors,
            )
        except TokenConflict as exc:
            return TurnOutcome(
                result=InternalFailure(
                    code="token_conflict", safe_message=str(exc)
                ),
                state_token=state_token,
            )
        except ProviderActionError as exc:
            # Provider-declared action rules surface verbatim: their code
            # and message are already public-safe by protocol contract.
            return TurnOutcome(
                result=InternalFailure(
                    code=exc.code, safe_message=str(exc)
                ),
                state_token=state_token,
            )
        except (OSError, RuntimeError, TypeError, ValueError, KeyError) as exc:
            return TurnOutcome(
                result=InternalFailure(
                    code=type(exc).__name__, safe_message=_SAFE_FAILURE
                ),
                state_token=state_token,
            )

    def _prepare_turn(
        self,
        descriptor: Any,
        request: ProviderRequest,
        *,
        state_token: str | None,
        transition: str | None,
        comparison_descriptors: tuple[ResolvedComparison, ...],
    ) -> TurnOutcome:
        if transition not in (None, "correct", "restart"):
            return TurnOutcome(
                result=InternalFailure(
                    code="invalid_transition",
                    safe_message="transition must be correct or restart",
                ),
                state_token=state_token,
            )
        turn_digest = self._turn_digest(
            descriptor,
            request,
            comparison_descriptors,
        )
        if state_token is None:
            if transition is not None:
                return TurnOutcome(
                    result=InternalFailure(
                        code="invalid_transition",
                        safe_message="a transition requires the latest state token",
                    ),
                    state_token=None,
                )
            return self._run_prepare(
                descriptor,
                request,
                parent_token=None,
                turn_digest=turn_digest,
                lineage=None,
                comparison_descriptors=comparison_descriptors,
            )
        record = self.token_store.resolve(state_token)
        if record is None:
            return TurnOutcome(
                result=InternalFailure(
                    code="unknown_state_token",
                    safe_message="the supplied state token is not recognized",
                ),
                state_token=None,
            )
        if record.phase == "pending_input":
            if transition is not None:
                return TurnOutcome(
                    result=InternalFailure(
                        code="invalid_transition",
                        safe_message="a pending question only accepts more facts",
                    ),
                    state_token=state_token,
                )
            scope_conflict = self._pending_scope_conflict(
                str(record.intake_id), request
            )
            if scope_conflict is not None:
                return scope_conflict
            merged = self._merge_pending(str(record.intake_id), request)
            return self._run_prepare(
                merged["descriptor"],
                merged["request"],
                parent_token=state_token,
                turn_digest=turn_digest,
                lineage=merged["lineage"],
                comparison_descriptors=merged["comparison_descriptors"],
                promote_token=state_token,
            )
        if record.phase == "prepared":
            if record.request_digest and turn_digest == record.request_digest:
                staged = self.store.load_prepared(record.reading_id)
                return TurnOutcome(
                    result=staged.public_contract(),
                    state_token=state_token,
                    preparation=self._load_projection(record.reading_id),
                )
            raise TokenConflict("this prepared reading is awaiting completion")
        # accepted token: implicit continue, explicit correct, or restart
        existing_claim = self.token_store.lineage_claim(state_token)
        if existing_claim is not None:
            same_turn = (
                existing_claim.get("request_digest") == turn_digest
                and existing_claim.get("child_reading_id")
            )
            if not same_turn:
                raise TokenConflict(
                    "this reading already advanced to a newer version"
                )
            staged = self.store.load_prepared(
                str(existing_claim["child_reading_id"])
            )
            token = self.token_store.issue(
                reading_id=str(staged.reading_id),
                version=int(staged.version),
                phase="prepared",
                parent_token=state_token,
                request_digest=turn_digest,
            )
            self.token_store.claim_lineage(
                state_token,
                token,
                request_digest=turn_digest,
                child_reading_id=str(staged.reading_id),
            )
            return TurnOutcome(
                result=staged.public_contract(),
                state_token=token,
                preparation=self._load_projection(str(staged.reading_id)),
                prior_answer=self._prior_answer(record.reading_id, transition),
            )
        action = {None: "continue", "correct": "correct", "restart": "recast"}[
            transition
        ]
        lineage = self._lineage_for(record.reading_id, action)
        return self._run_prepare(
            descriptor,
            request,
            parent_token=state_token,
            turn_digest=turn_digest,
            lineage=lineage,
            comparison_descriptors=comparison_descriptors,
        )

    def _run_prepare(
        self,
        descriptor: Any,
        request: ProviderRequest,
        *,
        parent_token: str | None,
        turn_digest: str,
        lineage: Mapping[str, Any] | None,
        comparison_descriptors: tuple[ResolvedComparison, ...],
        promote_token: str | None = None,
    ) -> TurnOutcome:
        reading_id, version = self._reading_identity(
            request,
            lineage,
            turn_digest,
        )
        bound_request = replace(
            request,
            reading_id=reading_id,
            version=version,
        )
        preparations: list[ProviderPreparation] = []
        outcome: Any = None
        failed_comparison_limits: list[dict[str, Any]] = []
        failure_descriptor_id = str(descriptor.id)
        members: tuple[tuple[Any | None, str, str], ...] = (
            (descriptor, "required", str(descriptor.id)),
            *tuple(
                (
                    comparison.descriptor,
                    comparison.requirement,
                    comparison.capability_id,
                )
                for comparison in comparison_descriptors
            ),
        )
        for offset, (member_descriptor, requirement, capability_id) in enumerate(
            members
        ):
            is_primary = offset == 0
            if member_descriptor is None:
                failed_comparison_limits.append(
                    {
                        "kind_id": "limit.comparison_skipped",
                        "public_text": "附加比较本轮未完成。",
                        "scope_refs": [],
                        "detail_ids": [str(capability_id)],
                    }
                )
                continue
            adapter = self.providers.get(str(member_descriptor.id))
            if adapter is None:
                if not is_primary and requirement == "optional":
                    failed_comparison_limits.append(
                        {
                            "kind_id": "limit.comparison_skipped",
                            "public_text": "附加比较本轮未完成。",
                            "scope_refs": [],
                            "detail_ids": [str(capability_id)],
                        }
                    )
                    continue
                return TurnOutcome(
                    result=_UnsupportedTurn(reason_id="capability_unavailable"),
                    state_token=None,
                )
            member_outcome: Any = None
            member_preparations: list[ProviderPreparation] = []
            for subject_ref in bound_request.subject_refs:
                member_request = replace(
                    bound_request,
                    subject_refs=(str(subject_ref),),
                    facts={
                        str(subject_ref): dict(
                            bound_request.facts.get(str(subject_ref)) or {}
                        )
                    },
                )
                member_lineage = dict(lineage or {})
                prior_artifacts = member_lineage.get("prior_artifacts")
                if isinstance(prior_artifacts, Mapping):
                    prior = prior_artifacts.get(
                        (str(subject_ref), str(member_descriptor.id))
                    )
                    if prior is not None:
                        member_lineage["prior_calculation"] = prior
                member_outcome = adapter.prepare(
                    member_request,
                    self._provider_context(member_lineage or None),
                )
                if isinstance(member_outcome, ProviderPreparation):
                    member_preparations.append(member_outcome)
                    continue
                break
            if (
                len(member_preparations) == len(bound_request.subject_refs)
                and isinstance(member_outcome, ProviderPreparation)
            ):
                preparations.extend(member_preparations)
                outcome = member_outcome
                continue
            # Optional comparisons are atomic across all subjects.  A need or
            # an unsupported result drops the whole comparison and records one
            # limit; partial preparations never enter the combined result.
            if (
                not is_primary
                and requirement == "optional"
                and isinstance(
                    member_outcome,
                    (ProviderNeedInput, ProviderUnsupported),
                )
            ):
                details = [str(capability_id)]
                if isinstance(member_outcome, ProviderNeedInput):
                    details.extend(
                        str(field)
                        for group in member_outcome.missing_input_groups
                        for field in group
                    )
                failed_comparison_limits.append(
                    {
                        "kind_id": "limit.comparison_skipped",
                        "public_text": "附加比较本轮未完成。",
                        "scope_refs": [],
                        "detail_ids": list(dict.fromkeys(details)),
                    }
                )
                outcome = preparations[-1] if preparations else member_outcome
                continue
            outcome = member_outcome
            failure_descriptor_id = str(member_descriptor.id)
            break
        # A required comparison (or the primary) demanded more input →
        # the turn goes pending.  Optional comparisons never force
        # pending on the host; they have already been recorded as
        # limits and the primary preparation (if any) is allowed to
        # continue.
        if isinstance(outcome, ProviderNeedInput):
            missing_groups = tuple(
                tuple(str(field_id) for field_id in group)
                for group in outcome.missing_input_groups
                if group
            )
            missing = tuple(
                dict.fromkeys(
                    field_id
                    for group in missing_groups
                    for field_id in group
                )
            )
            intake_id = self._save_pending(
                descriptor,
                bound_request,
                missing,
                missing_groups,
                lineage,
                comparison_descriptors,
            )
            token = self.token_store.issue(
                reading_id="",
                version=0,
                phase="pending_input",
                parent_token=parent_token,
                intake_id=intake_id,
                request_digest=turn_digest,
            )
            return TurnOutcome(
                result=NeedUserFact(
                    system=str(descriptor.id),
                    missing_facts=missing,
                    known_facts={},
                    intake_id=intake_id,
                    request_digest=turn_digest,
                ),
                state_token=token,
                missing_fields=missing,
                missing_input_groups=missing_groups,
                missing_descriptor_id=failure_descriptor_id,
            )
        if isinstance(outcome, ProviderUnsupported):
            return TurnOutcome(
                result=_UnsupportedTurn(reason_id=outcome.reason_id),
                state_token=None,
            )
        if not isinstance(outcome, ProviderPreparation):
            return TurnOutcome(
                result=InternalFailure(
                    code="invalid_preparation",
                    safe_message=_SAFE_FAILURE,
                ),
                state_token=None,
            )
        combined = self._combine_preparations(preparations)
        if failed_comparison_limits:
            from dataclasses import replace as _dc_replace

            combined = _dc_replace(
                combined,
                limits=tuple(list(combined.limits or ()) + failed_comparison_limits),
            )
        combined, publish_error = self._enforce_publishability(
            combined, requested_dimensions=bound_request.dimension_ids
        )
        if publish_error is not None:
            error_code, safe_message = publish_error
            return TurnOutcome(
                result=InternalFailure(
                    code=error_code,
                    safe_message=safe_message,
                ),
                state_token=None,
            )
        staged = self._stage(combined, lineage)
        self._save_projection(staged.reading_id, combined)
        parent_record = (
            self.token_store.resolve(parent_token) if parent_token else None
        )
        if promote_token is not None:
            # A pending supplement converges on the very token the host
            # already holds: promote it to prepared in place so a second
            # resume of the same pending token reuses the same identity and
            # can never mint a sibling prepared token.
            token = self.token_store.promote_to_prepared(
                promote_token,
                reading_id=str(staged.reading_id),
                version=int(staged.version),
                request_digest=turn_digest,
            )
        else:
            token = self.token_store.issue(
                reading_id=str(staged.reading_id),
                version=int(staged.version),
                phase="prepared",
                parent_token=parent_token,
                request_digest=turn_digest,
            )
        prior_answer: str | None = None
        if parent_record is not None and parent_record.phase == "accepted":
            self.token_store.claim_lineage(
                parent_token,
                token,
                request_digest=turn_digest,
                child_reading_id=str(staged.reading_id),
            )
            if lineage is not None and lineage.get("action") == "continue":
                prior_answer = lineage.get("prior_answer")
        return TurnOutcome(
            result=staged.public_contract(),
            state_token=token,
            preparation=combined,
            prior_answer=prior_answer,
        )

    def _reading_identity(
        self,
        request: ProviderRequest,
        lineage: Mapping[str, Any] | None,
        turn_digest: str,
    ) -> tuple[str, int]:
        if request.reading_id:
            return str(request.reading_id), int(request.version)
        if lineage is not None and lineage.get("action") in {"continue", "correct"}:
            reading_id = str(lineage["parent_reading_id"])
            current = self.store.load(reading_id)
            return reading_id, int(current.accepted.version) + 1
        if lineage is not None and lineage.get("action") == "recast":
            identity = canonical_digest(
                {
                    "parent_reading_id": str(lineage["parent_reading_id"]),
                    "parent_version": int(lineage["parent_version"]),
                    "request_digest": turn_digest,
                    "action": "recast",
                }
            )
            return identity[:32], 1
        # No token means a new request, even when its content is identical to
        # an earlier accepted request.  Token replay provides transaction
        # idempotency; content-addressing fresh roots would collapse distinct
        # user turns and collide with already committed storage.
        return uuid.uuid4().hex, 1

    @staticmethod
    def _combine_preparations(
        members: list[ProviderPreparation],
    ) -> ProviderPreparation:
        if not members:
            raise ValueError("a prepared turn requires at least one artifact")
        primary = members[0]

        def unique(items: list[Mapping[str, Any]], key: str) -> tuple[dict[str, Any], ...]:
            selected: dict[str, dict[str, Any]] = {}
            for item in items:
                value = str(item.get(key) or "")
                if not value:
                    raise ValueError(f"public projection is missing {key}")
                selected.setdefault(value, dict(item))
            return tuple(selected.values())

        facts = unique(
            [dict(item) for member in members for item in member.public_facts],
            "ref",
        )
        evidence = unique(
            [
                dict(item)
                for member in members
                for item in member.evidence_plan.get("evidence") or ()
            ],
            "ref",
        )
        scopes = tuple(
            dict(item) for member in members for item in member.claim_scopes
        )
        findings = unique(
            [dict(item) for member in members for item in member.findings],
            "ref",
        )
        limits_by_value: dict[str, dict[str, Any]] = {}
        for member in members:
            for limit in member.limits:
                normalized = dict(limit)
                identity = json.dumps(
                    normalized,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                limits_by_value.setdefault(identity, normalized)
        plan = dict(primary.evidence_plan)
        plan["evidence"] = evidence
        request_view = dict(primary.request_view or {})
        request_view["subject_refs"] = tuple(
            dict.fromkeys(
                str(subject_ref)
                for member in members
                for subject_ref in (
                    dict(member.request_view or {}).get("subject_refs") or ()
                )
            )
        )
        request_view["dimension_ids"] = tuple(
            dict.fromkeys(
                str(dimension_id)
                for member in members
                for dimension_id in (
                    dict(member.request_view or {}).get("dimension_ids") or ()
                )
            )
        )
        request_view["capability_ids"] = tuple(
            dict.fromkeys(
                str(member.capability_id)
                for member in members
                if member.capability_id
            )
        )
        return ProviderPreparation(
            calculation=primary.calculation,
            public_facts=facts,
            fact_index=primary.fact_index,
            evidence_plan=plan,
            claim_scopes=scopes,
            limits=tuple(limits_by_value.values()),
            provider_id=primary.provider_id,
            provider_version=primary.provider_version,
            subject_ref=primary.subject_ref,
            capability_id=primary.capability_id,
            independent_lineage_id=primary.independent_lineage_id,
            request_view=request_view,
            findings=findings,
            members=tuple(members),
        )

    @staticmethod
    def _judgment_for(preparation: ProviderPreparation) -> Judgment:
        plan = preparation.evidence_plan
        bundle: EvidenceBundle = plan["bundle"]
        extension = preparation.calculation.fact_extension
        unsupported = set(
            extension.unsupported_dimensions if extension is not None else ()
        )
        evidence_ids = tuple(item.rule_id for item in bundle.evidence)
        counter_ids = tuple(item.rule_id for item in bundle.counter_evidence)
        dimension_ids = tuple(
            dict.fromkeys(
                str(scope["dimension_id"])
                for scope in preparation.claim_scopes
            )
        )
        dimensions = tuple(
            JudgmentDimension(
                dimension=dimension,
                verdict=(
                    "unsupported"
                    if dimension in unsupported
                    else "caller_review_required"
                ),
                confidence="unassessed",
                conclusion="",
                evidence_ids=evidence_ids,
                counter_evidence_ids=counter_ids,
                uncertainty="semantic conclusion belongs to the current caller review",
            )
            for dimension in dimension_ids
        )
        basis_text = json.dumps(
            [
                {
                    "ref": f"public:{index}",
                    "display_text": str(fact.get("display_text") or ""),
                    "value": fact.get("value"),
                }
                for index, fact in enumerate(preparation.public_facts)
            ],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return Judgment.create(
            system=preparation.calculation.system,
            calculation_digest=preparation.calculation.result_hash,
            evidence_digest=bundle.bundle_digest,
            basis_label=str(plan["basis_label"]),
            basis_text=basis_text,
            dimensions=dimensions,
            intent_digest=str(plan["intent_digest"]),
        )

    def _stage(
        self,
        preparation: ProviderPreparation,
        lineage: Mapping[str, Any] | None,
    ) -> PreparedReadingRecord:
        plan = preparation.evidence_plan
        request = plan["request"]
        reading_id = str(plan["reading_id"])
        version = int(plan.get("version") or 1)
        members = preparation.members or (preparation,)
        artifacts = tuple(
            PreparedArtifact.create(
                subject_ref=member.subject_ref,
                capability_id=member.capability_id,
                independent_lineage_id=member.independent_lineage_id,
                calculation=member.calculation,
                evidence=member.evidence_plan["bundle"],
                judgment=self._judgment_for(member),
            )
            for member in members
        )
        primary = artifacts[0]
        if lineage is not None:
            parent_reading_id = str(lineage.get("parent_reading_id")) or None
            root_reading_id = (
                str(lineage.get("root_reading_id") or parent_reading_id)
                or reading_id
            )
            action = str(lineage.get("action") or "new")
            supersedes_version = lineage.get("supersedes_version")
            supersedes_version = (
                int(supersedes_version)
                if supersedes_version is not None
                else None
            )
        else:
            # No parent lineage → fresh independent root.  Storage
            # validation requires ``action`` in {new, resume} and
            # ``root_reading_id == reading_id`` for a valid root.
            parent_reading_id = None
            root_reading_id = reading_id
            action = "new"
            supersedes_version = None
        record = PreparedReadingRecord.create(
            reading_id=reading_id,
            version=version,
            request=request,
            calculation=primary.calculation,
            evidence=primary.evidence,
            judgment=primary.judgment,
            parent_reading_id=parent_reading_id,
            root_reading_id=root_reading_id,
            action=action,
            supersedes_version=supersedes_version,
            artifacts=artifacts,
        )
        self.store.stage(record)
        return record

    # -- deep seam: pending capability, publishability, identity -------

    def pending_intake_capability(self, state_token: str) -> str | None:
        """Return the capability already bound to a pending intake token.

        The interface never inspects the engine's private persistence
        layout; it asks the engine, which owns the pending JSON.
        ``None`` is returned when the token is unknown, not in the
        pending phase, or its intake record cannot be read.
        """

        if not isinstance(state_token, str) or not state_token:
            return None
        try:
            record = self.token_store.resolve(state_token)
        except (OSError, ValueError, KeyError, TypeError):
            return None
        if record is None or record.phase != "pending_input":
            return None
        intake_id = record.intake_id
        if not intake_id:
            return None
        try:
            payload = json.loads(self._pending_path(str(intake_id)).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return None
        capability_id = payload.get("capability_id")
        return str(capability_id) if capability_id else None

    def _enforce_publishability(
        self,
        preparation: ProviderPreparation,
        *,
        requested_dimensions: tuple[str, ...],
    ) -> tuple[ProviderPreparation, tuple[str, str] | None]:
        """Validate facts/claim-scopes/evidence invariants on the
        generic boundary.  Returns the (possibly-augmented) preparation
        plus ``(code, safe_message)`` when the result cannot be published.
        Absence of publishable content is ``unsupported``; broken internal
        references are an ``invalid_preparation`` error.
        """

        from dataclasses import replace as _dc_replace

        facts = [
            dict(item)
            for item in preparation.public_facts or ()
            if isinstance(item, Mapping)
        ]
        scopes = [
            dict(item)
            for item in preparation.claim_scopes or ()
            if isinstance(item, Mapping)
        ]
        evidence = [
            dict(item)
            for item in preparation.evidence_plan.get("evidence") or ()
            if isinstance(item, Mapping)
        ]
        limits = list(preparation.limits or ())
        existing_limit_kinds = {
            str(limit.get("kind_id")) for limit in limits if isinstance(limit, Mapping)
        }
        scope_dimensions = {
            str(scope.get("dimension_id"))
            for scope in scopes
        }
        new_limits: list[dict[str, Any]] = []
        # 1) Facts and claim scopes are the minimum publishable surface.
        if not facts or not scopes:
            return (
                preparation,
                (
                    "unsupported",
                    "当前能力本轮没有可发布的判断范围；请重新说明或换一个能力。",
                ),
            )
        fact_refs = {str(item.get("ref") or "") for item in facts}
        evidence_refs = {str(item.get("ref") or "") for item in evidence}
        if "" in fact_refs or "" in evidence_refs:
            return (
                preparation,
                ("invalid_preparation", _SAFE_FAILURE),
            )
        request_view = dict(preparation.request_view or {})
        allowed_subjects = {
            str(item) for item in request_view.get("subject_refs") or ()
        }
        allowed_dimensions = {
            str(item) for item in request_view.get("dimension_ids") or ()
        }
        for fact in facts:
            subject_ref = str(fact.get("subject_ref") or "")
            if not subject_ref or (
                allowed_subjects and subject_ref not in allowed_subjects
            ):
                return (
                    preparation,
                    ("invalid_preparation", _SAFE_FAILURE),
                )
        for item in evidence:
            if not set(str(ref) for ref in item.get("supports_fact_refs") or ()) <= fact_refs:
                return (
                    preparation,
                    ("invalid_preparation", _SAFE_FAILURE),
                )
        for scope in scopes:
            subject_ref = str(scope.get("subject_ref") or "")
            dimension_id = str(scope.get("dimension_id") or "")
            scope_fact_refs = {
                str(ref) for ref in scope.get("fact_refs") or ()
            }
            scope_evidence_refs = {
                str(ref) for ref in scope.get("evidence_refs") or ()
            }
            structurally_valid = (
                bool(subject_ref)
                and bool(dimension_id)
                and bool(scope.get("allowed_kind_ids"))
                and bool(str(scope.get("certainty_ceiling_id") or ""))
                and bool(scope_fact_refs or scope_evidence_refs)
                and scope_fact_refs <= fact_refs
                and scope_evidence_refs <= evidence_refs
                and (
                    not allowed_subjects or subject_ref in allowed_subjects
                )
                and (
                    not allowed_dimensions or dimension_id in allowed_dimensions
                )
            )
            if not structurally_valid:
                return (
                    preparation,
                    ("invalid_preparation", _SAFE_FAILURE),
                )
        limit_kind_ids = {
            str(limit.get("kind_id") or "")
            for limit in limits
            if isinstance(limit, Mapping)
        }
        for finding in preparation.findings or ():
            if not isinstance(finding, Mapping):
                return (
                    preparation,
                    ("invalid_preparation", _SAFE_FAILURE),
                )
            if not set(str(ref) for ref in finding.get("fact_refs") or ()) <= fact_refs:
                return (
                    preparation,
                    ("invalid_preparation", _SAFE_FAILURE),
                )
            if not set(str(ref) for ref in finding.get("evidence_refs") or ()) <= evidence_refs:
                return (
                    preparation,
                    ("invalid_preparation", _SAFE_FAILURE),
                )
            if not set(
                str(kind_id) for kind_id in finding.get("limit_kind_ids") or ()
            ) <= limit_kind_ids:
                return (
                    preparation,
                    ("invalid_preparation", _SAFE_FAILURE),
                )
        # 2) Zero evidence + at least one claim scope → explicit source
        #    gap.  The brief must surface it instead of pretending the
        #    preparation quotes anything.
        if not evidence and "limit.source_gap" not in existing_limit_kinds:
            new_limits.append(
                {
                    "kind_id": "limit.source_gap",
                    "public_text": "本轮没有适用的文献出处，只能基于事实层表达。",
                    "scope_refs": [],
                    "detail_ids": [],
                }
            )
        # 3) Requested dimensions that have no claim scope → limit per
        #    dimension.  The supported dimensions are kept as-is.
        for dimension in requested_dimensions:
            if dimension in scope_dimensions:
                continue
            if any(
                isinstance(limit, Mapping)
                and str(limit.get("kind_id")) == "limit.unsupported_dimension"
                and dimension in (limit.get("detail_ids") or [])
                for limit in limits
            ):
                continue
            new_limits.append(
                {
                    "kind_id": "limit.unsupported_dimension",
                    "public_text": (
                        f"维度 {dimension} 在本轮未被覆盖。"
                    ),
                    "scope_refs": [],
                    "detail_ids": [dimension],
                }
            )
        if not new_limits:
            return (preparation, None)
        augmented_plan = dict(preparation.evidence_plan)
        augmented_plan["evidence"] = evidence
        return (
            _dc_replace(
                preparation,
                limits=tuple(list(limits) + new_limits),
                evidence_plan=augmented_plan,
            ),
            None,
        )

    # -- complete -----------------------------------------------------------

    def complete_turn(
        self,
        state_token: str,
        public_copy: str,
    ) -> AcceptedReading | InternalFailure:
        try:
            return self._complete_turn(state_token, public_copy)
        except (OSError, RuntimeError, TypeError, ValueError, KeyError) as exc:
            return InternalFailure(
                code=type(exc).__name__,
                safe_message="The answer was not committed.",
            )

    def _complete_turn(
        self,
        state_token: str,
        public_copy: str,
    ) -> AcceptedReading | InternalFailure:
        record = self.token_store.resolve(state_token)
        if record is None:
            return InternalFailure(
                code="unknown_state_token",
                safe_message="the supplied state token is not recognized",
            )
        if record.phase == "accepted":
            committed = self.store.load_version(
                record.reading_id, int(record.version)
            )
            return committed.accepted
        if record.phase != "prepared":
            return InternalFailure(
                code="not_prepared",
                safe_message="this state token has no prepared reading",
            )
        prepared = self.store.load_prepared(record.reading_id)
        accepted = self.commit_prepared(
            record.reading_id, prepared.prepared_digest, public_copy
        )
        if isinstance(accepted, AcceptedReading):
            self.token_store.mark_accepted(
                state_token,
                commit_ref=accepted.public_copy_sha256,
            )
        return accepted

    def commit_prepared(
        self,
        reading_id: str,
        prepared_digest: str,
        public_copy: str,
    ) -> AcceptedReading | InternalFailure:
        """Atomic first-commit-wins: replay returns the first bytes."""

        if not isinstance(public_copy, str) or not public_copy.strip():
            return InternalFailure(
                code="empty_public_copy",
                safe_message="the completed answer text must not be empty",
            )
        committed = self.store.load_committed(reading_id, prepared_digest)
        if committed is not None:
            return committed.accepted
        prepared = self.store.load_prepared(reading_id)
        if prepared.prepared_digest != prepared_digest:
            raise ValueError("prepared digest mismatch")
        accepted = AcceptedReading(
            reading_id=reading_id,
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
            accepted_claims=(),
        )
        stored = self.store.commit(
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

    # -- private helpers ------------------------------------------------------

    def _provider_context(
        self, lineage: Mapping[str, Any] | None
    ) -> ProviderContext:
        context = self.runtime_context
        return ProviderContext(
            now_iso=getattr(context, "now_iso", None),
            default_timezone=getattr(context, "default_timezone_name", None),
            subject_facts=dict(getattr(context, "subject_profiles", None) or {}),
            prior_lineage=dict(lineage) if lineage else None,
        )

    def _lineage_for(
        self, parent_reading_id: str, action: str
    ) -> dict[str, Any]:
        parent = self.store.load(parent_reading_id)
        accepted = parent.accepted
        lineage: dict[str, Any] = {
            "action": action,
            "parent_reading_id": parent_reading_id,
            "parent_version": int(accepted.version),
            "root_reading_id": accepted.root_reading_id or parent_reading_id,
            "prior_answer": accepted.public_copy,
        }
        if action in ("continue", "correct"):
            # Continuations stay bound to the parent's private calculation so
            # adapters can preserve turn-scoped state; a restart deliberately
            # starts from nothing.
            lineage["prior_calculation"] = parent.calculation
            lineage["prior_artifacts"] = {
                (item.subject_ref, item.capability_id): (
                    parent.calculation if index == 0 else item.calculation
                )
                for index, item in enumerate(parent.artifacts)
            }
        if action == "correct":
            lineage["supersedes_version"] = int(accepted.version)
        return lineage

    def _prior_answer(
        self, parent_reading_id: str, transition: str | None
    ) -> str | None:
        if transition is not None:
            return None
        try:
            return self.store.load(parent_reading_id).accepted.public_copy
        except (OSError, ValueError, KeyError):
            return None

    @staticmethod
    def _turn_digest(
        descriptor: Any,
        request: ProviderRequest,
        comparison_descriptors: tuple[ResolvedComparison, ...] = (),
    ) -> str:
        return canonical_digest(
            {
                "capability_id": str(descriptor.id) if descriptor else "",
                "comparisons": [
                    {
                        "capability_id": str(item.capability_id),
                        "requirement": str(item.requirement),
                    }
                    for item in comparison_descriptors
                ],
                "query": request.query,
                "subject_refs": list(request.subject_refs),
                "object_id": request.object_id,
                "dimension_ids": list(request.dimension_ids),
                "horizon": dict(request.horizon or {}),
                "facts": {
                    str(subject): dict(fields)
                    for subject, fields in request.facts.items()
                },
            }
        )

    # -- pending-input persistence -------------------------------------------

    def _save_pending(
        self,
        descriptor: Any,
        request: ProviderRequest,
        missing: tuple[str, ...],
        missing_input_groups: tuple[tuple[str, ...], ...],
        lineage: Mapping[str, Any] | None,
        comparison_descriptors: tuple[ResolvedComparison, ...],
    ) -> str:
        intake_id = uuid.uuid4().hex
        payload = {
            "intake_id": intake_id,
            "capability_id": str(descriptor.id),
            "comparisons": [
                {
                    "capability_id": str(item.capability_id),
                    "requirement": str(item.requirement),
                }
                for item in comparison_descriptors
            ],
            "request": {
                "query": request.query,
                "subject_refs": list(request.subject_refs),
                "object_id": request.object_id,
                "dimension_ids": list(request.dimension_ids),
                "horizon": dict(request.horizon or {}),
                "facts": {
                    str(subject): dict(fields)
                    for subject, fields in request.facts.items()
                },
                "reading_id": request.reading_id,
                "version": request.version,
                "scope_subject_refs": list(request.scope_subject_refs),
                "comparisons": [dict(item) for item in request.comparisons],
            },
            "missing_facts": list(missing),
            "missing_input_groups": [
                list(group) for group in missing_input_groups
            ],
        }
        if lineage is not None:
            # Only the durable anchor survives the intake pause; the full
            # lineage (including private state) is rebuilt on resume.
            payload["lineage"] = {
                "action": str(lineage.get("action") or ""),
                "parent_reading_id": str(
                    lineage.get("parent_reading_id") or ""
                ),
            }
        path = self._pending_path(intake_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_replace(
            path,
            json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)
            + "\n",
        )
        return intake_id

    def _pending_scope_conflict(
        self, intake_id: str, supplement: ProviderRequest
    ) -> TurnOutcome | None:
        """Reject a supplement whose subject or object leaves the pending scope.

        A pending token is bound to one intake request.  The supplement may
        add facts for that same subject and object, but a different subject
        or object is a scope change that must surface as ``Stopped.conflict``
        instead of silently rewriting (or absorbing facts into) the original
        request.
        """

        try:
            payload = json.loads(
                self._pending_path(intake_id).read_text(encoding="utf-8")
            )
        except (OSError, ValueError, KeyError):
            return None
        stored = payload.get("request") or {}
        stored_subjects = tuple(
            str(item) for item in stored.get("scope_subject_refs") or ()
        ) or tuple(str(item) for item in stored.get("subject_refs") or ())
        stored_object = str(stored.get("object_id") or "")
        supplement_subjects = tuple(str(item) for item in supplement.scope_subject_refs) or tuple(
            str(item) for item in supplement.subject_refs
        )
        scope_mismatch = bool(stored_subjects and stored_subjects != supplement_subjects) or bool(
            stored_object and stored_object != supplement.object_id
        )
        if not scope_mismatch:
            return None
        return TurnOutcome(
            result=InternalFailure(
                code="scope_conflict",
                safe_message="the supplement changes the pending intake scope",
            ),
            state_token=None,
        )

    def _merge_pending(
        self, intake_id: str, supplement: ProviderRequest
    ) -> dict[str, Any]:
        payload = json.loads(
            self._pending_path(intake_id).read_text(encoding="utf-8")
        )
        stored = payload["request"]
        facts: dict[str, dict[str, Any]] = {
            str(subject): dict(fields)
            for subject, fields in (stored.get("facts") or {}).items()
        }
        for subject, fields in supplement.facts.items():
            merged = facts.setdefault(str(subject), {})
            merged.update(dict(fields))
        raw_comparisons: Any
        if "comparisons" in stored:
            raw_comparisons = stored.get("comparisons") or ()
        elif "comparison_capability_ids" in stored:
            raw_comparisons = stored.get("comparison_capability_ids") or ()
        elif "comparisons" in payload:
            raw_comparisons = payload.get("comparisons") or ()
        else:
            raw_comparisons = payload.get("comparison_capability_ids") or ()
        stored_comparisons: list[dict[str, Any]] = []
        for item in raw_comparisons:
            if isinstance(item, Mapping):
                stored_comparisons.append(dict(item))
            else:
                # Legacy flat-id form: treat as required.
                stored_comparisons.append(
                    {"capability_id": str(item), "requirement": "required"}
                )
        request = ProviderRequest(
            query=str(supplement.query or stored.get("query") or ""),
            subject_refs=tuple(
                str(item) for item in stored.get("subject_refs") or ()
            )
            or tuple(supplement.subject_refs),
            object_id=str(stored.get("object_id") or supplement.object_id),
            dimension_ids=tuple(
                str(item) for item in stored.get("dimension_ids") or ()
            ),
            horizon=dict(stored.get("horizon") or {}),
            facts=facts,
            reading_id=stored.get("reading_id"),
            version=int(stored.get("version") or 1),
            scope_subject_refs=tuple(
                str(item) for item in stored.get("scope_subject_refs") or ()
            ),
            comparisons=tuple(stored_comparisons),
        )
        capability_id = str(payload["capability_id"])
        adapter = self.providers.get(capability_id)
        if adapter is None:
            raise KeyError(f"pending capability is unavailable: {capability_id}")
        lineage: Mapping[str, Any] | None = None
        anchor = payload.get("lineage")
        if isinstance(anchor, Mapping) and anchor.get("parent_reading_id"):
            lineage = self._lineage_for(
                str(anchor["parent_reading_id"]), str(anchor.get("action"))
            )
        comparison_descriptors: list[ResolvedComparison] = []
        for item in stored_comparisons:
            comparison_id = str(item.get("capability_id") or "")
            requirement = str(item.get("requirement") or "required")
            try:
                comparison_descriptor = self.catalog.descriptor(comparison_id)
            except (AttributeError, KeyError, ValueError):
                comparison_descriptor = None
            if comparison_descriptor is None and requirement == "required":
                raise KeyError(
                    f"pending comparison is unavailable: {comparison_id}"
                )
            comparison_descriptors.append(
                ResolvedComparison(
                    capability_id=comparison_id,
                    requirement=requirement,
                    descriptor=comparison_descriptor,
                    unavailable_reason=(
                        None
                        if comparison_descriptor is not None
                        else "capability_unavailable"
                    ),
                )
            )
        return {
            "descriptor": adapter.descriptor,
            "request": request,
            "lineage": lineage,
            "comparison_descriptors": tuple(comparison_descriptors),
        }

    def _pending_path(self, intake_id: str) -> Path:
        return Path(self.store.root) / "pending-turns" / f"{intake_id}.json"

    # -- public projection persistence ----------------------------------------

    def _save_projection(
        self, reading_id: str, preparation: ProviderPreparation
    ) -> None:
        plan = preparation.evidence_plan
        payload = {
            "public_facts": [dict(fact) for fact in preparation.public_facts],
            "evidence": [dict(item) for item in plan.get("evidence") or ()],
            "claim_scopes": [
                {
                    key: list(value) if isinstance(value, tuple) else value
                    for key, value in dict(scope).items()
                }
                for scope in preparation.claim_scopes
            ],
            "limits": [dict(limit) for limit in preparation.limits],
            "findings": [dict(finding) for finding in preparation.findings],
            "provider_id": preparation.provider_id,
            "provider_version": preparation.provider_version,
            "basis_label": str(plan.get("basis_label") or ""),
            "request_view": dict(preparation.request_view or {}),
        }
        self._projections.mkdir(parents=True, exist_ok=True)
        path = self._projections / f"{reading_id}.json"
        path.write_text(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)
            + "\n",
            encoding="utf-8",
        )

    def _load_projection(self, reading_id: str) -> ProviderPreparation | None:
        path = self._projections / f"{reading_id}.json"
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return ProviderPreparation(
            calculation=None,
            public_facts=tuple(payload.get("public_facts") or ()),
            fact_index=(),
            evidence_plan={
                "evidence": tuple(payload.get("evidence") or ()),
                "reading_id": reading_id,
                "basis_label": str(payload.get("basis_label") or ""),
            },
            claim_scopes=tuple(
                {
                    key: tuple(value) if isinstance(value, list) else value
                    for key, value in dict(scope).items()
                }
                for scope in payload.get("claim_scopes") or ()
            ),
            limits=tuple(payload.get("limits") or ()),
            provider_id=str(payload.get("provider_id") or ""),
            provider_version=str(payload.get("provider_version") or ""),
            request_view=dict(payload.get("request_view") or {}),
            findings=tuple(payload.get("findings") or ()),
        )


__all__ = ["DraftGenerator", "TurnEngine", "TurnOutcome"]

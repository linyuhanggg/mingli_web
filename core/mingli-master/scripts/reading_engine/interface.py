"""The one portable external interface: ``execute(Command) -> Result``.

This module never imports a concrete provider, never parses natural
language, and never returns an empty terminal result. ``describe`` is a
cacheable projection of the bundled capability manifests; real readings go
through ``prepare`` and ``complete`` only.
"""

from __future__ import annotations

import errno
import json
import subprocess
from pathlib import Path
from typing import Any, Mapping

from .brief import compile_brief
from .catalog import CatalogLoader, ProviderDescriptor, RuntimeCatalog
from .interface_contracts import (
    PROTOCOL_VERSION,
    Accepted,
    CapabilityView,
    Command,
    Complete,
    Describe,
    Described,
    InputFieldView,
    InputRequest,
    InputRequirement,
    IntentSelection,
    Prepare,
    Prepared,
    PublicTerm,
    Result,
    RuntimeFailure,
    Stopped,
    TimeSemanticsView,
    runtime_failure,
)
from .provider_protocol import ResolvedComparison

_DEFAULT_LOCALE = "zh-CN"

# Human-readable, domain-free fallback used when even the message catalog
# cannot be consulted. Never empty.
FALLBACK_ERROR_TEXT = "本次处理未完成，请稍后重试。"

_TRANSIENT_ERRNOS = frozenset(
    {
        errno.EAGAIN,
        errno.EINTR,
        errno.EMFILE,
        errno.ENFILE,
        errno.ENOMEM,
        errno.ETIMEDOUT,
    }
)


def _failure_for_exception(error: BaseException) -> RuntimeFailure:
    if isinstance(error, (TimeoutError, subprocess.TimeoutExpired)):
        return runtime_failure("transient.timeout")
    if isinstance(error, MemoryError):
        return runtime_failure("transient.resource_unavailable")
    if isinstance(error, OSError) and error.errno in _TRANSIENT_ERRNOS:
        return runtime_failure("transient.resource_unavailable")
    if isinstance(error, (KeyError, TypeError, ValueError)):
        return runtime_failure("input_contract.invalid_payload")
    return runtime_failure("runtime.internal_error")


def _failure_for_internal_code(code: str) -> RuntimeFailure:
    if code in {"TimeoutError", "TimeoutExpired"}:
        return runtime_failure("transient.timeout")
    if code in {
        "BlockingIOError",
        "InterruptedError",
        "MemoryError",
    }:
        return runtime_failure("transient.resource_unavailable")
    if code == "unknown_state_token":
        return runtime_failure("input_contract.invalid_state_token")
    if code in {
        "empty_public_copy",
        "invalid_transition",
        "not_prepared",
    }:
        return runtime_failure("input_contract.invalid_payload")
    return runtime_failure("runtime.internal_error")


def _localized(display: Mapping[str, Any], locale: str = _DEFAULT_LOCALE) -> Any:
    if not isinstance(display, Mapping) or not display:
        return None
    if locale in display:
        return display[locale]
    return next(iter(display.values()))


def _term_view(descriptor: ProviderDescriptor, term_id: str) -> PublicTerm:
    terms = descriptor.canonical_payload.get("terms")
    label = term_id
    description = None
    if isinstance(terms, Mapping):
        spec = terms.get(term_id)
        if isinstance(spec, Mapping):
            localized = _localized(spec.get("display") or {})
            if isinstance(localized, str) and localized.strip():
                label = localized
            elif isinstance(localized, Mapping):
                label = str(localized.get("name") or term_id)
                description = localized.get("description")
    return PublicTerm(id=term_id, label=str(label), description=description)


def _input_field_view(descriptor: ProviderDescriptor, field_id: str) -> InputFieldView:
    for field in descriptor.input_fields:
        if field.id == field_id:
            localized = _localized(field.display)
            label = (
                str(localized)
                if isinstance(localized, str) and localized.strip()
                else field_id
            )
            return InputFieldView(
                id=field_id,
                label=label,
                type_id=field.type_id,
                description=(
                    str(description)
                    if isinstance(
                        description := _localized(field.description), str
                    ) and description.strip()
                    else None
                ),
                choices=tuple(
                    PublicTerm(
                        id=choice.id,
                        label=(
                            str(localized)
                            if isinstance(
                                localized := _localized(choice.display), str
                            ) and localized.strip()
                            else choice.id
                        ),
                        description=(
                            str(localized_description)
                            if isinstance(
                                localized_description := _localized(
                                    choice.description
                                ),
                                str,
                            ) and localized_description.strip()
                            else None
                        ),
                    )
                    for choice in field.choices
                ),
            )
    return InputFieldView(id=field_id, label=field_id, type_id="string")


def _time_semantics_view(descriptor: ProviderDescriptor) -> TimeSemanticsView | None:
    raw = descriptor.canonical_payload.get("time_semantics")
    if not isinstance(raw, Mapping):
        return None
    role = str(raw.get("role") or "")
    if not role:
        return None
    return TimeSemanticsView(
        role_id=role,
        supported_policy_ids=tuple(str(p) for p in (raw.get("supported_policies") or ())),
        default_policy_id=str(raw.get("default_policy") or "civil"),
        coordinate_required_policy_ids=tuple(
            str(p) for p in (raw.get("coordinates_required_policies") or ())
        ),
        unsupported_behavior_id=str(raw.get("unsupported_fallback") or "need_input"),
    )


def _capability_view(descriptor: ProviderDescriptor) -> CapabilityView:
    display = _localized(descriptor.display) or {}
    label = str(display.get("name") or descriptor.id)
    description = str(display.get("description") or label)
    capability = descriptor.capability
    return CapabilityView(
        id=descriptor.id,
        label=label,
        description=description,
        objects=tuple(
            _term_view(descriptor, term) for term in capability.object_ids
        ),
        horizons=tuple(
            _term_view(descriptor, term) for term in capability.horizon_ids
        ),
        dimensions=tuple(
            _term_view(descriptor, term) for term in capability.dimension_ids
        ),
        default_dimension_ids=tuple(capability.default_dimension_ids or ()),
        input_fields=tuple(
            _input_field_view(descriptor, field.id)
            for field in descriptor.input_fields
        ),
        required_input_groups=capability.required_input_groups,
        time_semantics=_time_semantics_view(descriptor),
    )


class ReadingInterface:
    """Deep-module entrypoint; hosts only ever call :meth:`execute`."""

    def __init__(
        self,
        *,
        skill_root: str | Path,
        store_root: str | Path | None = None,
        runtime_context: Any | None = None,
        catalog: RuntimeCatalog | None = None,
        engine: Any | None = None,
    ) -> None:
        self._skill_root = Path(skill_root).resolve()
        self._store_root = Path(store_root).resolve() if store_root else None
        self._runtime_context = runtime_context
        self._catalog = catalog or CatalogLoader(
            self._skill_root / "resources/runtime"
        ).load()
        self._described: Described | None = None
        self._engine = engine
        self._messages = self._load_messages()

    @property
    def catalog(self) -> RuntimeCatalog:
        return self._catalog

    @property
    def engine(self) -> Any:
        if self._engine is None:
            if self._store_root is None:
                raise ValueError("a store_root is required for prepare/complete")
            from .factory import build_production_engine

            self._engine = build_production_engine(
                skill_dir=self._skill_root,
                store_root=self._store_root,
                runtime_context=self._runtime_context,
            )
        return self._engine

    def _load_messages(self) -> dict[str, Any]:
        path = self._skill_root / "resources/runtime/messages/zh-CN.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                return payload
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            pass
        return {}

    def _reason_text(self, reason_id: str, **values: str) -> str:
        reasons = self._messages.get("reasons")
        template = (
            reasons.get(reason_id) if isinstance(reasons, Mapping) else None
        )
        if not isinstance(template, str) or not template.strip():
            return FALLBACK_ERROR_TEXT
        try:
            rendered = template.format(**values)
        except (KeyError, IndexError):
            rendered = template
        return rendered.strip() or FALLBACK_ERROR_TEXT

    def _protocol_term(self, term_id: str) -> PublicTerm:
        terms = self._messages.get("terms")
        spec = terms.get(term_id) if isinstance(terms, Mapping) else None
        if isinstance(spec, Mapping):
            label = str(spec.get("label") or term_id)
            description = spec.get("description")
            return PublicTerm(
                id=term_id,
                label=label,
                description=(
                    str(description) if description is not None else None
                ),
            )
        return PublicTerm(id=term_id, label=term_id)

    def execute(self, command: Command) -> Result:
        try:
            if isinstance(command, Describe):
                return self._describe()
            if isinstance(command, Prepare):
                return self._prepare(command)
            if isinstance(command, Complete):
                return self._complete(command)
            return Stopped(
                reason="error",
                public_copy=FALLBACK_ERROR_TEXT,
                failure=runtime_failure("input_contract.invalid_command"),
            )
        except Exception as error:  # noqa: BLE001 - never leak internals
            return Stopped(
                reason="error",
                public_copy=FALLBACK_ERROR_TEXT,
                failure=_failure_for_exception(error),
            )

    # -- complete ----------------------------------------------------------

    def _complete(self, command: Complete) -> Result:
        result = self.engine.complete_turn(
            command.state_token, command.public_copy
        )
        if hasattr(result, "public_copy_sha256"):
            return Accepted(
                state_token=command.state_token,
                public_copy=result.public_copy,
            )
        code = str(getattr(result, "code", ""))
        return Stopped(
            reason="error",
            public_copy=self._reason_text("error"),
            state_token=command.state_token,
            failure=_failure_for_internal_code(code),
        )

    # -- prepare -----------------------------------------------------------

    def _prepare(self, command: Prepare) -> Result:
        from .provider_protocol import ProviderRequest

        intent = command.intent
        subject_refs = tuple(intent.subject_refs) or ("current_user",)
        descriptor: ProviderDescriptor | None = None
        resume_pending = False
        effective_state_token: str | None = command.state_token
        bound_capability: str | None = None

        if command.state_token is not None:
            record = self.engine.token_store.resolve(command.state_token)
            if record is None:
                return Stopped(
                    reason="error",
                    public_copy=self._reason_text("error"),
                    failure=runtime_failure(
                        "input_contract.invalid_state_token"
                    ),
                )
            if record.phase == "accepted" and record.reading_id:
                prior = self.engine.store.load(record.reading_id)
                prior_scope = self._scope_of(prior)
                bound_capability = str(prior.accepted.system)
                explicit_capability = intent.capability_id
                scope_changed = not self._scope_matches(intent, prior_scope)
                capability_changed = (
                    explicit_capability is not None
                    and explicit_capability != bound_capability
                )
                if command.transition in ("correct", "restart") and (
                    scope_changed or capability_changed
                ):
                    return Stopped(
                        reason="conflict",
                        public_copy=self._reason_text("conflict"),
                        state_token=command.state_token,
                    )
                if scope_changed or capability_changed:
                    # A scope change or an explicit capability switch
                    # demands a brand-new independent root.  The engine
                    # must NOT see the old state token: the old token
                    # remains valid for the original scope, and the
                    # lineage must be parent=None, root=self, action=new.
                    effective_state_token = None
                    if intent.capability_id is not None:
                        chosen = self._descriptor_for_explicit(
                            command, intent.capability_id
                        )
                        if isinstance(chosen, Stopped):
                            return chosen
                        descriptor = chosen
                    else:
                        # No explicit capability: ask the model to pick.
                        chosen = self._choose_descriptor(command)
                        if isinstance(chosen, Stopped):
                            return chosen
                        descriptor = chosen
                else:
                    descriptor = self._descriptor_or_none(bound_capability)
            elif record.phase == "pending_input":
                # The pending token only supplements the same pending
                # request.  The engine owns the capability binding and
                # the interface never reads the pending file directly.
                if intent.capability_id is not None:
                    bound = self.engine.pending_intake_capability(command.state_token)
                    if bound is not None and intent.capability_id != bound:
                        return Stopped(
                            reason="conflict",
                            public_copy=self._reason_text("conflict"),
                            state_token=command.state_token,
                        )
                resume_pending = True
            elif record.phase == "prepared":
                # The pending token was promoted to prepared: the same
                # supplement replays the same staged brief (engine-side
                # idempotency), and any other request conflicts.  The host
                # must not re-derive a descriptor here -- the engine's
                # prepared branch compares the incoming turn digest against
                # the one stored at promotion time.
                resume_pending = True

        if descriptor is None and not resume_pending:
            chosen = self._choose_descriptor(command)
            if isinstance(chosen, Stopped):
                return chosen
            descriptor = chosen

        # The engine owns comparison provenance.  Pass the host's
        # declared list verbatim; the engine's structural selection and
        # adapter invocation will drop or reject comparisons based on
        # their requirement tag.
        comparison_descriptors, comparison_error = self._resolve_comparisons(
            command=command,
            primary=descriptor,
        )
        if comparison_error is not None:
            return comparison_error

        request = ProviderRequest(
            query=command.query,
            subject_refs=subject_refs,
            object_id=intent.object_id,
            dimension_ids=tuple(intent.dimension_ids),
            horizon={
                "kind": intent.horizon.kind_id,
                "start": intent.horizon.start,
                "end": intent.horizon.end,
            },
            facts={
                str(subject): dict(fields or {})
                for subject, fields in (command.facts or {}).items()
            },
            transition=command.transition,
            scope_subject_refs=subject_refs,
            comparisons=tuple(
                {
                    "capability_id": str(item.capability_id),
                    "requirement": str(item.requirement),
                }
                for item in intent.comparisons
            ),
        )
        turn = self.engine.prepare_turn(
            descriptor,
            request,
            state_token=effective_state_token,
            transition=command.transition,
            comparison_descriptors=tuple(comparison_descriptors),
        )
        return self._turn_to_result(
            turn,
            descriptor=descriptor,
            question=command.query,
        )

    def _descriptor_for_explicit(
        self, command: Prepare, capability_id: str
    ) -> ProviderDescriptor | Stopped:
        """Resolve one explicit capability and surface a Stopped on mismatch."""

        intent = command.intent
        selection = self._catalog.select(
            object_id=intent.object_id,
            horizon_kind_id=intent.horizon.kind_id,
            dimension_ids=tuple(intent.dimension_ids),
            capability_id=capability_id,
        )
        if selection.kind == "selected" and selection.descriptor is not None:
            return selection.descriptor
        if selection.kind == "need_focus":
            return Stopped(
                reason="need_input",
                public_copy=self._reason_text("need_focus"),
            )
        return Stopped(
            reason="unsupported",
            public_copy=self._reason_text("unsupported"),
        )

    @staticmethod
    def _scope_of(prior: Any) -> tuple[tuple[str, ...], str]:
        intent = getattr(prior.request, "intent", {}) or {}
        subjects = tuple(
            str(item) for item in intent.get("subject_refs") or ()
        )
        if not subjects:
            subjects = ("current_user",)
        object_id = str(intent.get("calculation_object") or "")
        return (subjects, object_id)

    @staticmethod
    def _scope_matches(
        intent: IntentSelection, prior_scope: tuple[tuple[str, ...], str]
    ) -> bool:
        prior_subjects, prior_object = prior_scope
        new_subjects = tuple(intent.subject_refs) or ("current_user",)
        return new_subjects == prior_subjects and intent.object_id == prior_object

    def _choose_descriptor(
        self, command: Prepare
    ) -> ProviderDescriptor | Stopped:
        """Structural capability routing only: no input-completeness shortcut.

        The core only does structural matching.  When the host did not pick
        a capability, one or more structurally compatible providers always
        surface a non-empty ``Stopped.need_input`` whose
        ``public_copy`` uses the ``choose_capability`` template so the
        host model can look at the cached ``describe`` and re-submit
        with an explicit ``capability_id``.  The core never picks the
        "cheapest" or "highest priority" candidate as a stand-in for
        the model's semantic choice.  Structural routing is delegated
        entirely to ``RuntimeCatalog``; this method only maps the
        catalog result to a Result.
        """

        intent = command.intent
        if intent.capability_id is not None:
            return self._descriptor_for_explicit(command, intent.capability_id)
        selection = self._catalog.select(
            object_id=intent.object_id,
            horizon_kind_id=intent.horizon.kind_id,
            dimension_ids=tuple(intent.dimension_ids),
            capability_id=None,
        )
        if selection.kind == "selected" and selection.descriptor is not None:
            candidates = (selection.descriptor,)
        elif selection.kind in {"ambiguous", "need_focus"}:
            candidates = selection.candidates or tuple(
                descriptor
                for descriptor in self._catalog.descriptors
                if self._catalog.select(
                    object_id=intent.object_id,
                    horizon_kind_id=intent.horizon.kind_id,
                    dimension_ids=tuple(intent.dimension_ids),
                    capability_id=descriptor.id,
                ).kind
                == "selected"
            )
        else:
            candidates = ()
        if candidates:
            labels = "、".join(
                self._capability_label(item) for item in candidates
            )
            return Stopped(
                reason="need_input",
                public_copy=self._reason_text("choose_capability", labels=labels),
            )
        return Stopped(
            reason="unsupported",
            public_copy=self._reason_text("unsupported"),
        )

    def _resolve_comparisons(
        self,
        *,
        command: Prepare,
        primary: ProviderDescriptor | None,
    ) -> tuple[tuple[ResolvedComparison, ...], Stopped | None]:
        """Resolve every declared comparison against the catalog.

        Every result is a per-call immutable value; catalog descriptors stay
        frozen and shareable.  Required structural failures stop here.
        Optional structural failures are forwarded without a descriptor so
        the engine can add a visible limit without invoking a provider.
        """

        intent = command.intent
        comparisons = tuple(intent.comparisons)
        if not comparisons or primary is None:
            return ((), None)
        primary_id = str(primary.id)
        primary_lineage = str(
            getattr(primary.capability, "independent_lineage_id", primary_id)
        )
        resolved: list[ResolvedComparison] = []
        seen_lineages: set[str] = {primary_lineage}
        for item in comparisons:
            requirement = str(item.requirement)
            selection = self._catalog.select(
                object_id=intent.object_id,
                horizon_kind_id=intent.horizon.kind_id,
                dimension_ids=tuple(intent.dimension_ids),
                capability_id=str(item.capability_id),
            )
            candidate = selection.descriptor
            valid = (
                selection.kind == "selected"
                and candidate is not None
                and candidate.id != primary_id
                and str(
                    getattr(
                        candidate.capability,
                        "independent_lineage_id",
                        candidate.id,
                    )
                )
                not in seen_lineages
            )
            if not valid:
                if requirement == "required":
                    return (
                        (),
                        Stopped(
                            reason="unsupported",
                            public_copy=self._reason_text("unsupported"),
                        ),
                    )
                resolved.append(
                    ResolvedComparison(
                        capability_id=str(item.capability_id),
                        requirement="optional",
                        descriptor=None,
                        unavailable_reason="structurally_unavailable",
                    )
                )
                continue
            seen_lineages.add(
                str(
                    getattr(
                        candidate.capability,
                        "independent_lineage_id",
                        candidate.id,
                    )
                )
            )
            resolved.append(
                ResolvedComparison(
                    capability_id=str(candidate.id),
                    requirement=requirement,
                    descriptor=candidate,
                )
            )
        return (tuple(resolved), None)

    def _descriptor_or_none(self, system: str) -> ProviderDescriptor | None:
        try:
            return self._catalog.descriptor(str(system))
        except Exception:  # noqa: BLE001 - unknown prior systems stay generic
            return None

    def _capability_label(self, descriptor: ProviderDescriptor) -> str:
        display = _localized(descriptor.display) or {}
        return str(display.get("name") or descriptor.id)

    def _input_label(
        self, descriptor: ProviderDescriptor | None, field_id: str
    ) -> str:
        if descriptor is not None:
            view = _input_field_view(descriptor, field_id)
            if view.label.strip() and view.label != field_id:
                return view.label
            if view.label.strip():
                return view.label
        return field_id

    def _input_request(
        self,
        descriptor: ProviderDescriptor | None,
        groups: tuple[tuple[str, ...], ...],
    ) -> InputRequest | None:
        """Project provider-owned missing groups without exposing intake state."""

        if descriptor is None:
            return None
        requirements = tuple(
            InputRequirement(
                any_of=tuple(
                    _input_field_view(descriptor, str(field_id))
                    for field_id in group
                )
            )
            for group in groups
            if group
        )
        return InputRequest(requirements=requirements) if requirements else None

    def _turn_to_result(
        self,
        turn: Any,
        *,
        descriptor: ProviderDescriptor | None,
        question: str,
    ) -> Result:
        outcome = turn.result
        status = getattr(outcome, "status", None)
        if status == "prepared":
            preparation = turn.preparation
            if preparation is None:
                return Stopped(
                    reason="error",
                    public_copy=self._reason_text("error"),
                    state_token=turn.state_token,
                )
            reading_descriptor = (
                self._descriptor_or_none(str(preparation.provider_id))
                or descriptor
            )

            def resolve_term(term_id: str) -> PublicTerm:
                if reading_descriptor is not None:
                    view = _term_view(reading_descriptor, term_id)
                    if view.label != term_id:
                        return view
                return self._protocol_term(term_id)

            brief = compile_brief(
                preparation,
                question=question,
                term_resolver=resolve_term,
                prior_answer=turn.prior_answer,
            )
            return Prepared(state_token=str(turn.state_token), brief=brief)
        if status == "need_user_fact":
            asked_descriptor = (
                self._descriptor_or_none(
                    str(
                        getattr(turn, "missing_descriptor_id", None)
                        or getattr(outcome, "system", "")
                    )
                )
                or descriptor
            )
            groups = tuple(
                tuple(str(field_id) for field_id in group)
                for group in getattr(turn, "missing_input_groups", ())
                if group
            )
            if not groups:
                groups = tuple(
                    (str(field_id),)
                    for field_id in getattr(outcome, "missing_facts", ())
                )
            input_request = self._input_request(asked_descriptor, groups)
            labels = "、".join(
                self._input_label(asked_descriptor, str(field))
                for group in groups
                for field in group
            )
            return Stopped(
                reason="need_input",
                public_copy=self._reason_text("need_input", labels=labels),
                state_token=turn.state_token,
                input_request=input_request,
            )
        if status == "unsupported_dimension":
            return Stopped(
                reason="unsupported",
                public_copy=self._reason_text("unsupported"),
                state_token=turn.state_token,
            )
        if status == "internal_failure":
            code = str(getattr(outcome, "code", ""))
            if code == "token_conflict":
                return Stopped(
                    reason="conflict",
                    public_copy=self._reason_text("conflict"),
                    state_token=turn.state_token,
                )
            if code == "scope_conflict":
                # The supplement left the pending intake scope: the host must
                # surface a real conflict, never silently continue a different
                # subject/object under the original request.
                return Stopped(
                    reason="conflict",
                    public_copy=self._reason_text("conflict"),
                    state_token=turn.state_token,
                )
            if code == "unsupported":
                # Publishability invariant: facts/scopes/evidence don't
                # form a publishable result.  Surface a real Stopped so
                # the host knows the brief is not committable.
                return Stopped(
                    reason="unsupported",
                    public_copy=self._reason_text("unsupported"),
                    state_token=turn.state_token,
                )
            return Stopped(
                reason="error",
                public_copy=self._reason_text("error"),
                state_token=turn.state_token,
                failure=_failure_for_internal_code(code),
            )
        return Stopped(
            reason="error",
            public_copy=FALLBACK_ERROR_TEXT,
            failure=runtime_failure("runtime.internal_error"),
        )

    def _describe(self) -> Described:
        if self._described is None:
            self._described = Described(
                protocol_version=PROTOCOL_VERSION,
                manifest_digest=self._catalog.manifest_digest,
                capabilities=tuple(
                    _capability_view(descriptor)
                    for descriptor in self._catalog.descriptors
                ),
            )
        return self._described


__all__ = ["FALLBACK_ERROR_TEXT", "ReadingInterface"]

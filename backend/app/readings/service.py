from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.profiles.service import OwnerProtocol, ProfileService, owner_ids
from app.readings.api_schemas import (
    ReadingResultResponse,
    ReadingStartResponse,
    ReadingVerificationSummary,
    ReadingVersionSummary,
)
from app.readings.output_contracts import PREVIEW_V1
from app.readings.public_fact_panel import project_public_fact_panel
from app.readings.repository import READING_HISTORY_LIMIT, SqlReadingRepository
from app.readings.request_compiler import (
    ConfirmedProfileVersion,
    compile_bazi_prepare,
    compile_fortune_prepare,
    compile_liuyao_prepare,
)
from app.readings.runtime_contracts import Prepare
from app.readings.status import ReadingStatus
from app.security.envelope import EnvelopeCipher

NARRATIVE_POLICY_VERSION = "policy-v1"
DEFAULT_QUERIES = {
    "profile_preview": "请预览我的本命格局。",
    "today": "请看看我今天的运势。",
    "near_seven": "请看看我这一周的运势。",
    "liuyao_one_question": "请为这个问题起一卦。",
}


class ReadingServiceError(RuntimeError):
    """Base class for explicit Phase 2 API service failures."""


class ReadingNotFoundError(ReadingServiceError):
    """A Reading Version is missing or belongs to another owner."""


class ReadingNotWaitingInputError(ReadingServiceError):
    """The Reading Version is not in the waiting_input state."""


class ReadingAlreadyQueuedError(ReadingServiceError):
    """A concurrent input submission already queued this Reading Version."""


class ReadingNotAcceptedError(ReadingServiceError):
    """The Reading Version has no Accepted Copy to follow up or verify."""


class RuntimeReleaseUnavailableError(ReadingServiceError):
    """No Runtime Release is registered for a new Reading Version."""


class InvalidReadingInputError(ReadingServiceError):
    """Supplied values do not satisfy the runtime input request."""


class ProfileVersionNotOwnedError(ReadingServiceError):
    """The requested Profile Version is missing or belongs to another owner."""


class IdempotencyConflictError(ReadingServiceError):
    """An Idempotency-Key was reused for a different action or payload."""


@dataclass(frozen=True, slots=True)
class IdempotencyContext:
    key_hash: str
    action: str
    request_fingerprint: str


@dataclass(frozen=True, slots=True)
class InputFieldPolicy:
    target: str
    type_ids: frozenset[str]
    minimum: int | float | None = None
    maximum: int | float | None = None


_INPUT_FIELD_POLICIES: dict[str, InputFieldPolicy] = {
    **{
        f"cast_{index}": InputFieldPolicy(
            target="cast",
            type_ids=frozenset({"integer"}),
            minimum=6,
            maximum=9,
        )
        for index in range(1, 7)
    },
    "zi_policy": InputFieldPolicy(
        target="zi_hour_policy",
        type_ids=frozenset({"choice"}),
    ),
    "fixture_input": InputFieldPolicy(
        target="fixture_input",
        type_ids=frozenset({"text", "textarea"}),
    ),
}


class ReadingService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.repository = SqlReadingRepository(
            session,
            EnvelopeCipher.from_settings(settings),
        )
        self.profiles = ProfileService(session, settings)
        self._idempotency_secret = settings.identity_hash_key.get_secret_value().encode(
            "utf-8"
        )

    async def start_preview(
        self,
        owner: OwnerProtocol,
        *,
        profile_version_id: UUID,
        query: str | None,
        dimension_ids: list[str] | None,
        idempotency_key: str | None,
    ) -> tuple[ReadingStartResponse, bool]:
        resolved_query = query or DEFAULT_QUERIES["profile_preview"]
        resolved_dimensions = list(dimension_ids or ("career",))
        idempotency = self._idempotency_context(
            idempotency_key,
            action="profile_preview",
            payload={
                "profile_version_id": str(profile_version_id),
                "query": resolved_query,
                "dimension_ids": resolved_dimensions,
            },
        )
        replayed = await self._replay_idempotency(owner, idempotency)
        if replayed is not None:
            return replayed, False
        profile = await self._owned_confirmed_profile(owner, profile_version_id)
        prepare = compile_bazi_prepare(
            action="profile_preview",
            query=resolved_query,
            profile=profile,
            dimension_ids=tuple(resolved_dimensions),
        )
        return await self._persist_start(
            owner,
            prepare,
            capability_id="bazi",
            profile_version_id=profile_version_id,
            idempotency=idempotency,
        )

    async def start_fortune(
        self,
        owner: OwnerProtocol,
        *,
        action: str,
        profile_version_id: UUID,
        query: str | None,
        idempotency_key: str | None,
    ) -> tuple[ReadingStartResponse, bool]:
        if action not in {"today", "near_seven"}:
            raise ReadingServiceError(f"unsupported fortune action: {action!r}")
        resolved_query = query or DEFAULT_QUERIES[action]
        idempotency = self._idempotency_context(
            idempotency_key,
            action=action,
            payload={
                "profile_version_id": str(profile_version_id),
                "query": resolved_query,
            },
        )
        replayed = await self._replay_idempotency(owner, idempotency)
        if replayed is not None:
            return replayed, False
        profile = await self._owned_confirmed_profile(owner, profile_version_id)
        prepare = compile_fortune_prepare(
            action=action,
            query=resolved_query,
            profile=profile,
            server_reference_datetime=datetime.now(UTC),
            dimension_ids=("career",),
        )
        return await self._persist_start(
            owner,
            prepare,
            capability_id="fortune",
            profile_version_id=profile_version_id,
            idempotency=idempotency,
        )

    async def start_liuyao(
        self,
        owner: OwnerProtocol,
        *,
        cast: tuple[int, ...] | str,
        event_datetime: datetime,
        timezone: str,
        location: str,
        subject_ref: str | None,
        query: str | None,
        dimension_ids: list[str] | None,
        idempotency_key: str | None,
    ) -> tuple[ReadingStartResponse, bool]:
        resolved_query = query or DEFAULT_QUERIES["liuyao_one_question"]
        resolved_dimensions = list(dimension_ids or ("career",))
        idempotency = self._idempotency_context(
            idempotency_key,
            action="liuyao_one_question",
            payload={
                "cast": list(cast) if isinstance(cast, tuple) else cast,
                "event_datetime": event_datetime.isoformat(),
                "timezone": timezone,
                "location": location,
                "subject_ref": subject_ref,
                "query": resolved_query,
                "dimension_ids": resolved_dimensions,
            },
        )
        replayed = await self._replay_idempotency(owner, idempotency)
        if replayed is not None:
            return replayed, False
        resolved_subject_ref = subject_ref or f"liuyao:{uuid4().hex}"
        prepare = compile_liuyao_prepare(
            action="liuyao_one_question",
            query=resolved_query,
            subject_ref=resolved_subject_ref,
            cast=cast,
            event_datetime=event_datetime,
            confirmed_timezone=timezone,
            location=location,
            dimension_ids=tuple(resolved_dimensions),
        )
        return await self._persist_start(
            owner,
            prepare,
            capability_id="liuyao",
            profile_version_id=None,
            idempotency=idempotency,
        )

    async def supply_input(
        self,
        owner: OwnerProtocol,
        *,
        version_id: UUID,
        values: Mapping[str, Any],
    ) -> ReadingStartResponse:
        _root, version = await self._load_owned_version(
            owner,
            version_id,
        )
        if version.status != ReadingStatus.WAITING_INPUT.value:
            raise ReadingNotWaitingInputError("Reading is not waiting for input")
        stopped = await self.repository.load_waiting_input(version_id)
        if stopped is None or stopped.input_request is None:
            raise ReadingNotWaitingInputError("Reading is not waiting for input")
        mapped_values = self._validate_input_values(stopped.input_request, values)
        prepare = await self.repository.load_prepare(version_id)
        state_token = await self.repository.load_state_token(version_id)
        new_prepare = Prepare(
            query=prepare.query,
            intent=prepare.intent,
            facts=_apply_runtime_inputs(prepare.facts, mapped_values),
            state_token=state_token,
            transition="correct",
        )
        try:
            await self.repository.replace_prepare(version_id, new_prepare)
        except ValueError as error:
            raise ReadingNotWaitingInputError(
                "Reading is not waiting for input"
            ) from error
        try:
            await self._create_job(version_id)
        except IntegrityError as error:
            raise ReadingAlreadyQueuedError("Reading is already queued") from error
        return await self.get_summary(owner, version_id)

    async def get_summary(
        self,
        owner: OwnerProtocol,
        version_id: UUID,
    ) -> ReadingStartResponse:
        root, version = await self._load_owned_version(
            owner,
            version_id,
        )
        return await self._summary(root, version)

    async def list_summaries(
        self,
        owner: OwnerProtocol,
    ) -> list[ReadingVersionSummary]:
        """List the newest owned Reading Versions, newest first (max 50)."""
        user_id, guest_id = owner_ids(owner)
        rows = await self.repository.list_owned_versions(
            owner_user_id=user_id,
            owner_guest_session_id=guest_id,
            limit=READING_HISTORY_LIMIT,
        )
        return [await self._summary(root, version) for root, version in rows]

    async def get_result(
        self,
        owner: OwnerProtocol,
        version_id: UUID,
    ) -> ReadingResultResponse:
        _root, version = await self._load_owned_version(
            owner,
            version_id,
        )
        brief = await self.repository.load_fact_brief(version_id)
        accepted_copy = await self.repository.load_accepted_copy(version_id)
        verification = await self.repository.load_verification(version_id)
        waiting = await self.repository.load_waiting_input(version_id)
        return ReadingResultResponse(
            reading_version_id=version.id,
            status=version.status,
            accepted_copy=accepted_copy,
            fact_panel=project_public_fact_panel(brief),
            verification=(
                None
                if verification is None
                else _verification_summary(verification)
            ),
            input_request=(
                None if waiting is None else _public_json(waiting.input_request)
            ),
        )

    async def submit_verification(
        self,
        owner: OwnerProtocol,
        *,
        version_id: UUID,
        outcome: str,
        note: str | None,
    ) -> tuple[ReadingVerificationSummary, bool]:
        _root, version = await self._load_owned_version(
            owner,
            version_id,
        )
        if version.status != ReadingStatus.ACCEPTED.value:
            raise ReadingNotAcceptedError("Reading is not accepted")
        saved, created = await self.repository.save_verification(
            version_id=version_id,
            outcome=outcome,
            note=note,
        )
        return _verification_summary(saved), created

    async def follow_up(
        self,
        owner: OwnerProtocol,
        *,
        version_id: UUID,
        query: str | None,
        idempotency_key: str | None,
    ) -> tuple[ReadingStartResponse, bool]:
        user_id, guest_id = owner_ids(owner)
        idempotency = self._idempotency_context(
            idempotency_key,
            action="follow_up",
            payload={"reading_version_id": str(version_id), "query": query},
        )
        replayed = await self._replay_idempotency(owner, idempotency)
        if replayed is not None:
            return replayed, False
        root, version = await self._load_owned_version(
            owner,
            version_id,
        )
        if version.status != ReadingStatus.ACCEPTED.value:
            raise ReadingNotAcceptedError("Follow-up requires an Accepted Reading")
        accepted_copy = await self.repository.load_accepted_copy(version.id)
        if accepted_copy is None:
            raise ReadingNotAcceptedError("Accepted Copy is missing")
        prepare = await self.repository.load_prepare(version.id)
        facts: dict[str, object] = {}
        for subject_ref in cast(tuple[object, ...], prepare.intent["subject_refs"]):
            ref = str(subject_ref)
            subject_facts = dict(
                cast(Mapping[str, object], prepare.facts.get(ref, {}))
            )
            subject_facts["prior_answer"] = accepted_copy
            facts[ref] = subject_facts
        # Follow-up continues the same lineage with the latest Accepted token.
        # transition stays null; only explicit fact correction uses "correct".
        state_token = await self.repository.load_state_token(version.id)
        new_prepare = Prepare(
            query=query or prepare.query,
            intent=prepare.intent,
            facts=facts,
            state_token=state_token,
            transition=None,
        )
        new_version = await self._create_version_and_job(
            root,
            new_prepare,
        )
        if idempotency is not None:
            replayed = await self._save_idempotency_or_replay(
                idempotency,
                owner_user_id=user_id,
                owner_guest_session_id=guest_id,
                reading_version_id=new_version.id,
            )
            if replayed is not None:
                return replayed, False
        summary = await self._summary(root, new_version)
        summary.prior_answer = accepted_copy
        return summary, True

    async def _save_idempotency_or_replay(
        self,
        idempotency: IdempotencyContext,
        *,
        owner_user_id: UUID | None,
        owner_guest_session_id: UUID | None,
        reading_version_id: UUID,
    ) -> ReadingStartResponse | None:
        try:
            await self.repository.save_idempotency(
                key_hash=idempotency.key_hash,
                action=idempotency.action,
                request_fingerprint=idempotency.request_fingerprint,
                owner_user_id=owner_user_id,
                owner_guest_session_id=owner_guest_session_id,
                reading_version_id=reading_version_id,
            )
        except IntegrityError:
            await self.session.rollback()
            return await self._replay_idempotency_for_ids(
                idempotency,
                user_id=owner_user_id,
                guest_id=owner_guest_session_id,
            )
        return None

    async def _persist_start(
        self,
        owner: OwnerProtocol,
        prepare: Prepare,
        *,
        capability_id: str,
        profile_version_id: UUID | None,
        idempotency: IdempotencyContext | None,
    ) -> tuple[ReadingStartResponse, bool]:
        user_id, guest_id = owner_ids(owner)
        release = await self._runtime_release()
        root = await self.repository.create_root(
            capability_id=capability_id,
            owner_user_id=user_id,
            owner_guest_session_id=guest_id,
            profile_version_id=profile_version_id,
        )
        version = await self.repository.create_version(
            reading_root_id=root.id,
            runtime_release_id=release.id,
            prepare_command=prepare,
        )
        await self.session.refresh(version)
        await self._create_job(version.id)
        if idempotency is not None:
            replayed = await self._save_idempotency_or_replay(
                idempotency,
                owner_user_id=user_id,
                owner_guest_session_id=guest_id,
                reading_version_id=version.id,
            )
            if replayed is not None:
                return replayed, False
        return await self._summary(root, version), True

    async def _create_version_and_job(
        self,
        root: Any,
        prepare: Prepare,
    ) -> Any:
        release = await self._runtime_release()
        version = await self.repository.create_version(
            reading_root_id=root.id,
            runtime_release_id=release.id,
            prepare_command=prepare,
        )
        await self.session.refresh(version)
        await self._create_job(version.id)
        return version

    async def _create_job(self, version_id: UUID) -> None:
        await self.repository.create_job(
            reading_version_id=version_id,
            narrative_policy_version=NARRATIVE_POLICY_VERSION,
            output_contract=PREVIEW_V1,
            language="zh-CN",
            max_output_chars=PREVIEW_V1.max_output_chars,
            max_attempts=2,
        )

    async def _runtime_release(self) -> Any:
        try:
            return await self.repository.resolve_runtime_release()
        except LookupError as error:
            raise RuntimeReleaseUnavailableError(
                "no Runtime Release is registered"
            ) from error

    async def _owned_confirmed_profile(
        self,
        owner: OwnerProtocol,
        profile_version_id: UUID,
    ) -> ConfirmedProfileVersion:
        try:
            _profile, version = await self.profiles.get_owned_profile_version(
                owner,
                profile_version_id,
            )
        except LookupError as error:
            raise ProfileVersionNotOwnedError(
                "Profile Version not found"
            ) from error
        payload = await self.profiles.repository.load_version_payload(version.id)
        return ConfirmedProfileVersion(
            subject_ref=f"profile-version:{version.id}",
            birth_datetime=str(payload["birth_datetime"]),
            birth_datetime_or_four_pillars=str(payload["birth_datetime"]),
            timezone=str(payload["timezone"]),
            location=str(payload["location"]),
            gender=str(payload["gender"]),
            time_basis_policy=str(payload["time_basis_policy"]),
            zi_hour_policy=str(payload["zi_hour_policy"]),
            longitude=cast(float | None, payload.get("longitude")),
            latitude=cast(float | None, payload.get("latitude")),
            coordinate_source=cast(str | None, payload.get("coordinate_source")),
        )

    async def _replay_idempotency(
        self,
        owner: OwnerProtocol,
        idempotency: IdempotencyContext | None,
    ) -> ReadingStartResponse | None:
        if idempotency is None:
            return None
        user_id, guest_id = owner_ids(owner)
        return await self._replay_idempotency_for_ids(
            idempotency,
            user_id=user_id,
            guest_id=guest_id,
        )

    async def _replay_idempotency_for_ids(
        self,
        idempotency: IdempotencyContext,
        *,
        user_id: UUID | None,
        guest_id: UUID | None,
    ) -> ReadingStartResponse | None:
        record = await self.repository.find_idempotency(
            idempotency.key_hash,
            owner_user_id=user_id,
            owner_guest_session_id=guest_id,
        )
        if record is None:
            return None
        if (
            record.action != idempotency.action
            or record.request_fingerprint != idempotency.request_fingerprint
        ):
            raise IdempotencyConflictError(
                "Idempotency-Key belongs to a different action or payload"
            )
        try:
            root, version = await self.repository.load_owned_version(
                record.reading_version_id,
                owner_user_id=user_id,
                owner_guest_session_id=guest_id,
            )
        except LookupError as error:
            raise ReadingNotFoundError("Reading Version not found") from error
        return await self._summary(root, version)

    def _idempotency_context(
        self,
        idempotency_key: str | None,
        *,
        action: str,
        payload: Mapping[str, object],
    ) -> IdempotencyContext | None:
        if idempotency_key is None:
            return None
        if not idempotency_key.strip():
            raise ReadingServiceError("Idempotency-Key must be non-empty")
        return IdempotencyContext(
            key_hash=_hmac_digest(
                self._idempotency_secret,
                "reading-idempotency-key-v1",
                idempotency_key,
            ),
            action=action,
            request_fingerprint=_hmac_digest(
                self._idempotency_secret,
                "reading-idempotency-request-v1",
                _canonical_json(payload),
            ),
        )

    async def _load_owned_version(
        self,
        owner: OwnerProtocol,
        version_id: UUID,
    ) -> tuple[Any, Any]:
        user_id, guest_id = owner_ids(owner)
        try:
            return await self.repository.load_owned_version(
                version_id,
                owner_user_id=user_id,
                owner_guest_session_id=guest_id,
            )
        except LookupError as error:
            raise ReadingNotFoundError("Reading Version not found") from error

    async def _summary(
        self,
        root: Any,
        version: Any,
    ) -> ReadingStartResponse:
        waiting = await self.repository.load_waiting_input(version.id)
        return ReadingStartResponse(
            reading_version_id=version.id,
            reading_root_id=root.id,
            profile_version_id=root.profile_version_id,
            capability_id=version.capability_id,
            version=version.version,
            status=version.status,
            object_id=version.object_id,
            dimension_ids=list(version.dimension_ids),
            horizon=dict(version.horizon),
            prior_answer=await self._projected_prior_answer(version.id),
            input_request=(
                None if waiting is None else _public_json(waiting.input_request)
            ),
            created_at=version.created_at,
        )

    async def _projected_prior_answer(self, version_id: UUID) -> str | None:
        brief = await self.repository.load_fact_brief(version_id)
        if brief is not None:
            prior = brief.get("prior_answer")
            if isinstance(prior, str) and prior:
                return prior
        prepare = await self.repository.load_prepare(version_id)
        for subject_ref in cast(tuple[object, ...], prepare.intent["subject_refs"]):
            subject_facts = cast(
                Mapping[str, object],
                prepare.facts.get(str(subject_ref), {}),
            )
            value = subject_facts.get("prior_answer")
            if isinstance(value, str) and value:
                return value
        return None

    @staticmethod
    def _validate_input_values(
        input_request: Mapping[str, Any],
        values: Mapping[str, Any],
    ) -> dict[str, object]:
        requirements = input_request.get("requirements")
        if not isinstance(requirements, (list, tuple)) or not requirements:
            raise InvalidReadingInputError("runtime input request is malformed")
        fields_by_id: dict[str, Mapping[str, object]] = {}
        selected_ids: list[str] = []
        for requirement in requirements:
            if not isinstance(requirement, Mapping):
                raise InvalidReadingInputError("runtime input request is malformed")
            any_of = requirement.get("any_of")
            if not isinstance(any_of, (list, tuple)) or not any_of:
                raise InvalidReadingInputError("runtime input request is malformed")
            fields = [field for field in any_of if isinstance(field, Mapping)]
            field_ids = {str(field.get("id")) for field in fields if field.get("id")}
            if len(field_ids) != len(fields):
                raise InvalidReadingInputError("runtime input request is malformed")
            for field in fields:
                fields_by_id[str(field["id"])] = cast(Mapping[str, object], field)
            selected = sorted(field_ids.intersection(values))
            if len(selected) != 1:
                raise InvalidReadingInputError(
                    "exactly one field from each input alternative is required"
                )
            selected_ids.extend(selected)

        unknown_keys = set(values) - set(fields_by_id)
        if unknown_keys:
            raise InvalidReadingInputError("unknown input fields are forbidden")

        mapped: dict[str, object] = {}
        cast_values: dict[int, int] = {}
        for field_id in selected_ids:
            policy = _INPUT_FIELD_POLICIES.get(field_id)
            if policy is None:
                raise InvalidReadingInputError("runtime input field is not product-approved")
            field = fields_by_id[field_id]
            type_id = field.get("type_id")
            if not isinstance(type_id, str) or type_id not in policy.type_ids:
                raise InvalidReadingInputError("runtime input field type is not approved")
            value = values[field_id]
            _validate_input_value(field, policy, value)
            if policy.target == "cast":
                cast_values[int(field_id.removeprefix("cast_"))] = cast(int, value)
            else:
                mapped[policy.target] = cast(object, value)

        if cast_values:
            if set(cast_values) != set(range(1, 7)):
                raise InvalidReadingInputError("all six cast values are required")
            mapped["cast"] = [cast_values[index] for index in range(1, 7)]
        return mapped


def _canonical_json(payload: Mapping[str, object]) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _hmac_digest(secret: bytes, domain: str, value: str) -> str:
    return hmac.new(
        secret,
        f"{domain}\x00{value}".encode(),
        hashlib.sha256,
    ).hexdigest()


def _validate_input_value(
    field: Mapping[str, object],
    policy: InputFieldPolicy,
    value: object,
) -> None:
    type_id = cast(str, field["type_id"])
    if type_id == "integer":
        if type(value) is not int:
            raise InvalidReadingInputError("integer input must be an integer")
    elif type_id in {"text", "textarea"}:
        if not isinstance(value, str) or not value.strip():
            raise InvalidReadingInputError("text input must be non-empty")
    elif type_id == "choice":
        if not isinstance(value, str):
            raise InvalidReadingInputError("choice input must be a string")
    else:
        raise InvalidReadingInputError("unsupported runtime input type")

    if isinstance(value, (int, float)) and type(value) is not bool:
        if policy.minimum is not None and value < policy.minimum:
            raise InvalidReadingInputError("numeric input is below the allowed range")
        if policy.maximum is not None and value > policy.maximum:
            raise InvalidReadingInputError("numeric input is above the allowed range")

    raw_choices = field.get("choices")
    if raw_choices:
        if not isinstance(raw_choices, (list, tuple)):
            raise InvalidReadingInputError("runtime input choices are malformed")
        choice_ids = {
            str(choice.get("id"))
            for choice in raw_choices
            if isinstance(choice, Mapping) and choice.get("id")
        }
        if value not in choice_ids:
            raise InvalidReadingInputError("input value is outside the allowed choices")


def _apply_runtime_inputs(
    facts: Mapping[str, object],
    values: Mapping[str, Any],
) -> dict[str, object]:
    merged: dict[str, object] = {}
    for ref, subject_facts in facts.items():
        if isinstance(subject_facts, Mapping):
            merged[str(ref)] = {**dict(subject_facts), **dict(values)}
        else:
            merged[str(ref)] = subject_facts
    return merged


def _verification_summary(record: Any) -> ReadingVerificationSummary:
    return ReadingVerificationSummary(
        verification_id=record.id,
        reading_version_id=record.reading_version_id,
        outcome=record.outcome,
        note=record.note,
        created_at=record.created_at,
    )


def _public_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _public_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_public_json(item) for item in value]
    if isinstance(value, list):
        return [_public_json(item) for item in value]
    return value

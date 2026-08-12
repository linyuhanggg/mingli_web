from __future__ import annotations

import asyncio
import json
from collections.abc import Callable, Coroutine, Mapping
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from app.charts.api_schemas import (
    BaziChartNeedInputResponse,
    BaziChartReadyResponse,
    BaziChartSyncResponse,
)
from app.charts.runtime import ChartRuntimeFactory, ChartRuntimeLease
from app.readings.errors import RuntimeTransportError
from app.readings.public_fact_panel import project_public_fact_panel
from app.readings.runtime_contracts import Prepare, Prepared, Stopped
from app.readings.runtime_inputs import (
    InvalidRuntimeInputError,
    apply_runtime_inputs,
    validate_runtime_input_values,
)


class ChartSessionError(RuntimeError):
    """Base class for the in-process synchronous chart lifecycle."""


class ChartHandleNotFoundError(ChartSessionError):
    """The chart handle is absent or belongs to a different owner."""


class ChartHandleGoneError(ChartSessionError):
    """The chart handle reached a terminal state and cannot be replayed."""


class ChartInputInvalidError(ChartSessionError):
    """Supplied values do not satisfy the Runtime input request."""


class ChartIdempotencyConflictError(ChartSessionError):
    """An Idempotency-Key was reused for a different chart operation."""


class ChartPrepareStoppedError(ChartSessionError):
    """Runtime returned a terminal deterministic chart outcome."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class ChartRuntimeUnavailableError(ChartSessionError):
    """The Runtime outcome is unknown or violates the prepare contract."""


@dataclass(slots=True)
class _Operation:
    fingerprint: str
    task: asyncio.Task[BaziChartSyncResponse]


@dataclass(slots=True)
class _PendingChart:
    owner_key: str
    profile_version_id: UUID
    handle: str
    prepare: Prepare
    state_token: str
    input_request: dict[str, Any]
    lease: ChartRuntimeLease
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class ChartSessionManager:
    """Keep only the opaque continuity needed to finish synchronous prepare."""

    def __init__(self, runtime_factory: ChartRuntimeFactory) -> None:
        self._runtime_factory = runtime_factory
        self._operations: dict[tuple[str, str], _Operation] = {}
        self._pending: dict[str, _PendingChart] = {}
        self._gone: set[tuple[str, str]] = set()
        self._operation_lock = asyncio.Lock()

    async def startup(self) -> None:
        await self._runtime_factory.startup()

    async def aclose(self) -> None:
        tasks = [operation.task for operation in self._operations.values()]
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        pending = list(self._pending.values())
        self._pending.clear()
        for chart in pending:
            await chart.lease.aclose()
        self._operations.clear()
        self._gone.clear()
        await self._runtime_factory.aclose()

    async def start(
        self,
        *,
        owner_key: str,
        profile_version_id: UUID,
        prepare: Prepare,
        idempotency_key: str,
    ) -> BaziChartSyncResponse:
        fingerprint = _canonical_json(
            {
                "operation": "start",
                "profile_version_id": str(profile_version_id),
                "prepare": prepare.to_dict(),
            }
        )
        return await self._run_idempotently(
            owner_key=owner_key,
            idempotency_key=idempotency_key,
            fingerprint=fingerprint,
            operation=lambda: self._start_once(
                owner_key=owner_key,
                profile_version_id=profile_version_id,
                prepare=prepare,
            ),
        )

    async def supply_input(
        self,
        *,
        owner_key: str,
        chart_handle: str,
        values: Mapping[str, Any],
        idempotency_key: str,
    ) -> BaziChartSyncResponse:
        fingerprint = _canonical_json(
            {
                "operation": "input",
                "chart_handle": chart_handle,
                "values": dict(values),
            }
        )
        return await self._run_idempotently(
            owner_key=owner_key,
            idempotency_key=idempotency_key,
            fingerprint=fingerprint,
            operation=lambda: self._supply_once(
                owner_key=owner_key,
                chart_handle=chart_handle,
                values=values,
            ),
        )

    async def _run_idempotently(
        self,
        *,
        owner_key: str,
        idempotency_key: str,
        fingerprint: str,
        operation: Callable[[], Coroutine[Any, Any, BaziChartSyncResponse]],
    ) -> BaziChartSyncResponse:
        key = (owner_key, idempotency_key)
        async with self._operation_lock:
            existing = self._operations.get(key)
            if existing is not None:
                if existing.fingerprint != fingerprint:
                    raise ChartIdempotencyConflictError(
                        "Idempotency-Key was reused with another payload"
                    )
                task = existing.task
            else:
                task = asyncio.create_task(operation())
                self._operations[key] = _Operation(fingerprint=fingerprint, task=task)
        return await asyncio.shield(task)

    async def _start_once(
        self,
        *,
        owner_key: str,
        profile_version_id: UUID,
        prepare: Prepare,
    ) -> BaziChartSyncResponse:
        lease = await self._runtime_factory.open()
        keep_lease = False
        try:
            try:
                result = await lease.runtime.execute(prepare)
            except RuntimeTransportError as error:
                raise ChartRuntimeUnavailableError("Runtime outcome is unknown") from error
            if isinstance(result, Prepared):
                return _ready_response(profile_version_id, result)
            if isinstance(result, Stopped) and result.reason == "need_input":
                pending, response = self._waiting_response(
                    owner_key=owner_key,
                    profile_version_id=profile_version_id,
                    prepare=prepare,
                    lease=lease,
                    stopped=result,
                )
                self._pending[pending.handle] = pending
                keep_lease = True
                return response
            if isinstance(result, Stopped):
                raise ChartPrepareStoppedError(result.reason)
            raise ChartRuntimeUnavailableError("Runtime did not return a prepare outcome")
        finally:
            if not keep_lease:
                await lease.aclose()

    async def _supply_once(
        self,
        *,
        owner_key: str,
        chart_handle: str,
        values: Mapping[str, Any],
    ) -> BaziChartSyncResponse:
        pending = self._pending.get(chart_handle)
        if pending is None or pending.owner_key != owner_key:
            if (owner_key, chart_handle) in self._gone:
                raise ChartHandleGoneError("Chart handle is no longer active")
            raise ChartHandleNotFoundError("Chart handle not found")
        async with pending.lock:
            if self._pending.get(chart_handle) is not pending:
                raise ChartHandleGoneError("Chart handle is no longer active")
            try:
                mapped_values = validate_runtime_input_values(
                    pending.input_request,
                    values,
                )
            except InvalidRuntimeInputError as error:
                raise ChartInputInvalidError(str(error)) from error
            prepare = Prepare(
                query=pending.prepare.query,
                intent=pending.prepare.intent,
                facts=apply_runtime_inputs(pending.prepare.facts, mapped_values),
                state_token=pending.state_token,
                transition="correct",
            )
            try:
                result = await pending.lease.runtime.execute(prepare)
            except RuntimeTransportError as error:
                await self._retire(pending)
                raise ChartRuntimeUnavailableError("Runtime outcome is unknown") from error
            except BaseException:
                await self._retire(pending)
                raise
            if isinstance(result, Prepared):
                try:
                    return _ready_response(pending.profile_version_id, result)
                finally:
                    await self._retire(pending)
            if isinstance(result, Stopped) and result.reason == "need_input":
                try:
                    state_token, input_request = _waiting_payload(result)
                except BaseException:
                    await self._retire(pending)
                    raise
                pending.prepare = prepare
                pending.state_token = state_token
                pending.input_request = input_request
                return BaziChartNeedInputResponse(
                    profile_version_id=pending.profile_version_id,
                    status="need_input",
                    chart_handle=pending.handle,
                    input_request=input_request,
                )
            await self._retire(pending)
            if isinstance(result, Stopped):
                raise ChartPrepareStoppedError(result.reason)
            raise ChartRuntimeUnavailableError("Runtime did not return a prepare outcome")

    def _waiting_response(
        self,
        *,
        owner_key: str,
        profile_version_id: UUID,
        prepare: Prepare,
        lease: ChartRuntimeLease,
        stopped: Stopped,
    ) -> tuple[_PendingChart, BaziChartNeedInputResponse]:
        state_token, input_request = _waiting_payload(stopped)
        handle = uuid4().hex
        pending = _PendingChart(
            owner_key=owner_key,
            profile_version_id=profile_version_id,
            handle=handle,
            prepare=prepare,
            state_token=state_token,
            input_request=input_request,
            lease=lease,
        )
        return pending, BaziChartNeedInputResponse(
            profile_version_id=profile_version_id,
            status="need_input",
            chart_handle=handle,
            input_request=input_request,
        )

    async def _retire(self, pending: _PendingChart) -> None:
        self._pending.pop(pending.handle, None)
        self._gone.add((pending.owner_key, pending.handle))
        await pending.lease.aclose()


def _ready_response(
    profile_version_id: UUID,
    result: Prepared,
) -> BaziChartReadyResponse:
    fact_panel = project_public_fact_panel(result.brief)
    if fact_panel is None:
        raise ChartRuntimeUnavailableError("Runtime prepared no public fact panel")
    return BaziChartReadyResponse(
        profile_version_id=profile_version_id,
        status="ready",
        fact_panel=fact_panel,
    )


def _waiting_payload(stopped: Stopped) -> tuple[str, dict[str, Any]]:
    payload = stopped.to_dict()
    state_token = payload.get("state_token")
    input_request = payload.get("input_request")
    if not isinstance(state_token, str) or not isinstance(input_request, dict):
        raise ChartRuntimeUnavailableError("Runtime need_input payload is malformed")
    return state_token, input_request


def _canonical_json(payload: Mapping[str, object]) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )

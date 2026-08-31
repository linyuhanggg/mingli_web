from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal
from uuid import uuid4

import pytest
from app.adapters.runtime import (
    WORKER_STOPPED_COPY,
    failure_for_transport_fault,
    generic_runtime_stopped,
    time_layer_entitlement_resolution_for_session,
    time_layer_entitlement_resolution_for_transport_fault,
)
from app.charts.contracts import TimeLayer
from app.readings.api_schemas import ReadingResultResponse, TimeLayerEntitlementResponse
from app.readings.runtime_contracts import (
    PAID_TIME_LAYER_IDS,
    TIME_LAYER_ENTITLEMENT_SCHEMA_VERSION,
    ContractValidationError,
    TimeLayerEntitlementV1,
    project_time_layer_entitlement,
    resolve_time_layer_entitlement_resolution,
)
from app.readings.service import ReadingService
from pydantic import ValidationError


@dataclass
class _Owner:
    kind: Literal["user", "guest"]
    id: Any


def _layer(
    layer_id: str,
    label: str,
    *,
    available: bool,
    reason: str | None = None,
) -> dict[str, object]:
    return {
        "layer_id": layer_id,
        "label": label,
        "available": available,
        "unavailable_reason": reason,
    }


def _bazi_view(
    *,
    year_available: bool = False,
    month_available: bool = False,
    day_available: bool = False,
    years: tuple[int, ...] | None = None,
    months: tuple[str, ...] | None = None,
    days: tuple[str, ...] | None = None,
    luck_cycles: object | None = None,
    extra_time_layer_field: dict[str, object] | None = None,
) -> dict[str, object]:
    year_layer = _layer(
        "year",
        "流年",
        available=year_available,
        reason=None if year_available else "本次结果只返回本命四柱，尚未返回逐年盘面。",
    )
    if extra_time_layer_field is not None:
        year_layer.update(extra_time_layer_field)
    core_facts: dict[str, object] = {}
    if years is not None:
        core_facts["year_layers"] = [{"year": year} for year in years]
    if months is not None:
        core_facts["month_layers"] = [{"period": month} for month in months]
    if days is not None:
        core_facts["day_layers"] = [{"period": day} for day in days]
    if luck_cycles is not None:
        core_facts["luck_cycles"] = luck_cycles
    return {
        "schema_version": "bazi-chart/v1",
        "subject_ref": "profile-version:test",
        "time_layers": [
            _layer("life", "本命", available=True),
            year_layer,
            _layer(
                "month",
                "流月",
                available=month_available,
                reason=None if month_available else "本次结果只返回本命四柱，尚未返回逐月盘面。",
            ),
            _layer(
                "day",
                "流日",
                available=day_available,
                reason=None if day_available else "本次结果只返回本命四柱，尚未返回逐日盘面。",
            ),
        ],
        "core_facts": core_facts or None,
    }


def _ziwei_view(
    *,
    year_available: bool = False,
    month_available: bool = False,
    years: tuple[int, ...] | None = None,
    months: tuple[tuple[int, int], ...] | None = None,
    major_limits: object | None = None,
) -> dict[str, object]:
    core_facts: dict[str, object] = {}
    if years is not None:
        core_facts["annual_layers"] = [{"year": year} for year in years]
    if months is not None:
        core_facts["monthly_layers"] = [
            {"year": year, "month": month} for year, month in months
        ]
    if major_limits is not None:
        core_facts["major_limits"] = major_limits
    return {
        "schema_version": "ziwei-chart/v1",
        "subject_ref": "profile-version:test",
        "time_layers": [
            _layer("life", "本命", available=True),
            _layer(
                "year",
                "流年",
                available=year_available,
                reason=None if year_available else "本次紫微结果只返回本命盘，尚未返回逐年盘面。",
            ),
            _layer(
                "month",
                "流月",
                available=month_available,
                reason=None if month_available else "本次紫微结果只返回本命盘，尚未返回逐月盘面。",
            ),
            _layer(
                "day",
                "流日",
                available=False,
                reason="本次紫微结果未返回逐日盘面。",
            ),
        ],
        "core_facts": core_facts or None,
    }


def _by_id(contract: TimeLayerEntitlementV1) -> dict[str, Any]:
    return {item.layer_id: item for item in contract.layers}


@pytest.mark.parametrize("art", ["bazi", "ziwei"])
@pytest.mark.parametrize(
    ("resolution", "paid_access", "cta"),
    [
        ("granted", "readable", None),
        ("denied", "locked_paywall", "professional_info"),
        ("unknown", "fail_closed_unknown", "professional_info"),
        ("unauthenticated", "fail_closed_unknown", "professional_info"),
        ("request_failed", "fail_closed_unknown", "professional_info"),
    ],
)
def test_g1_g3_entitlement_separates_paid_lock_from_free_readability(
    art: str,
    resolution: str,
    paid_access: str,
    cta: str | None,
) -> None:
    view = (
        _bazi_view(
            year_available=True,
            month_available=True,
            years=(2024, 2026),
            months=("2026-08",),
            luck_cycles={"status": "calculated"},
        )
        if art == "bazi"
        else _ziwei_view(
            year_available=True,
            month_available=True,
            years=(2025,),
            months=((2025, 8),),
            major_limits=({"sequence": 1},),
        )
    )
    original_layers = [dict(item) for item in view["time_layers"]]

    contract = project_time_layer_entitlement(view, resolution=resolution)

    assert contract is not None
    assert contract.schema_version == TIME_LAYER_ENTITLEMENT_SCHEMA_VERSION
    assert contract.capability_id == art
    assert contract.free_boundary_layer_id == "year"
    assert contract.paid_layer_ids == PAID_TIME_LAYER_IDS
    assert view["time_layers"] == original_layers
    layers = _by_id(contract)
    assert layers["life"].tier == "free"
    assert layers["life"].access == "readable"
    assert layers["life"].upgrade_cta is None
    assert layers["year"].tier == "free"
    assert layers["year"].access == "readable"
    assert layers["year"].upgrade_cta is None
    structural = "luck_cycles" if art == "bazi" else "major_limits"
    assert layers[structural].tier == "free"
    assert layers[structural].access == "readable"
    assert layers[structural].upgrade_cta is None
    assert layers["month"].tier == "paid"
    assert layers["month"].access == paid_access
    assert layers["month"].upgrade_cta == cta
    assert layers["day"].access == "unavailable"
    assert layers["day"].upgrade_cta is None
    assert layers["hour"].access == "unavailable"
    assert layers["hour"].upgrade_cta is None
    for snapshot in contract.capability:
        dumped = snapshot.to_dict()
        assert set(dumped) == {
            "layer_id",
            "label",
            "available",
            "unavailable_reason",
        }
        assert "upgrade_cta" not in dumped
        assert "tier" not in dumped
        assert "access" not in dumped
        assert "resolution" not in dumped


def test_unknown_resolution_keeps_returned_free_years_readable() -> None:
    view = _bazi_view(
        year_available=False,
        years=(1994, 2024, 2025),
        luck_cycles=None,
    )

    contract = project_time_layer_entitlement(view, resolution="unknown")

    assert contract is not None
    layers = _by_id(contract)
    assert contract.free_year_set == (1994, 2024, 2025)
    assert layers["year"].access == "readable"
    assert layers["year"].upgrade_cta is None
    assert layers["luck_cycles"].access == "unavailable"
    assert layers["luck_cycles"].upgrade_cta is None
    year_capability = next(item for item in contract.capability if item.layer_id == "year")
    assert year_capability.available is False
    assert year_capability.unavailable_reason is not None


def test_free_year_set_is_server_returned_not_hardcoded() -> None:
    short = project_time_layer_entitlement(
        _ziwei_view(years=(2031,)),
        resolution="denied",
    )
    long = project_time_layer_entitlement(
        _bazi_view(years=(2020, 2021, 2022, 2023)),
        resolution="denied",
    )

    assert short is not None and long is not None
    assert short.free_year_set == (2031,)
    assert long.free_year_set == (2020, 2021, 2022, 2023)
    assert len(short.free_year_set) != len(long.free_year_set)


def test_missing_free_capability_is_unavailable_without_upgrade_cta() -> None:
    contract = project_time_layer_entitlement(
        _bazi_view(year_available=False, years=None, luck_cycles=None),
        resolution="denied",
    )

    assert contract is not None
    layers = _by_id(contract)
    assert contract.free_year_set == ()
    assert layers["year"].access == "unavailable"
    assert layers["year"].upgrade_cta is None
    assert layers["luck_cycles"].access == "unavailable"
    assert layers["luck_cycles"].upgrade_cta is None
    assert layers["month"].access == "unavailable"
    assert layers["month"].upgrade_cta is None


def test_paid_capability_available_does_not_grant_entitlement() -> None:
    view = _bazi_view(
        month_available=True,
        months=("2026-08",),
        day_available=True,
        days=("2026-08-27",),
    )
    contract = project_time_layer_entitlement(view, resolution="unauthenticated")

    assert contract is not None
    layers = _by_id(contract)
    month_capability = next(item for item in contract.capability if item.layer_id == "month")
    assert month_capability.available is True
    assert month_capability.unavailable_reason is None
    assert layers["month"].access == "fail_closed_unknown"
    assert layers["day"].access == "fail_closed_unknown"
    assert layers["month"].upgrade_cta == "professional_info"
    assert layers["life"].access == "readable"


def test_capability_snapshot_rejects_entitlement_fields() -> None:
    view = _bazi_view(extra_time_layer_field={"upgrade_cta": "professional_info"})

    with pytest.raises(ContractValidationError, match="closed keys"):
        project_time_layer_entitlement(view, resolution="denied")


@pytest.mark.parametrize(
    "payload_mutator",
    [
        lambda payload: payload.__setitem__("schema_version", "time-layer-entitlement/v2"),
        lambda payload: payload.__setitem__("resolution", "guest"),
        lambda payload: payload.__setitem__("free_boundary_layer_id", "month"),
        lambda payload: payload.__setitem__("paid_layer_ids", ["month", "day"]),
        lambda payload: payload.__setitem__("price", 99),
        lambda payload: payload.__setitem__("checkout_url", "/pay"),
        lambda payload: payload["layers"][0].__setitem__("upgrade_cta", "professional_info"),
        lambda payload: payload["capability"]["time_layers"][0].__setitem__("tier", "free"),
        lambda payload: payload["free_year_set"].__setitem__(0, 2024.5)
        if False
        else payload.__setitem__("free_year_set", [2024, 2024]),
    ],
)
def test_entitlement_v1_fail_closes_extra_unsafe_and_missing(payload_mutator: Any) -> None:
    contract = project_time_layer_entitlement(
        _bazi_view(years=(2024,), luck_cycles={"status": "calculated"}),
        resolution="denied",
    )
    assert contract is not None
    payload = contract.to_dict()
    payload_mutator(payload)

    with pytest.raises(ContractValidationError):
        TimeLayerEntitlementV1.from_dict(payload)


_ALL_RESOLUTIONS = (
    "granted",
    "denied",
    "unknown",
    "unauthenticated",
    "request_failed",
)
_ALL_ACCESS = (
    "readable",
    "locked_paywall",
    "fail_closed_unknown",
    "unavailable",
)
_PAID_ACCESS_ALLOWED = {
    "granted": frozenset({"readable", "unavailable"}),
    "denied": frozenset({"locked_paywall", "unavailable"}),
    "unknown": frozenset({"fail_closed_unknown", "unavailable"}),
    "unauthenticated": frozenset({"fail_closed_unknown", "unavailable"}),
    "request_failed": frozenset({"fail_closed_unknown", "unavailable"}),
}


def _paid_cta(access: str) -> str | None:
    return "professional_info" if access in {"locked_paywall", "fail_closed_unknown"} else None


@pytest.mark.parametrize("resolution", _ALL_RESOLUTIONS)
@pytest.mark.parametrize("paid_access", _ALL_ACCESS)
def test_from_dict_enforces_resolution_paid_access_matrix(
    resolution: str,
    paid_access: str,
) -> None:
    contract = project_time_layer_entitlement(
        _bazi_view(
            years=(2026,),
            month_available=True,
            months=("2026-08",),
            luck_cycles={"status": "calculated"},
        ),
        resolution=resolution,
    )
    assert contract is not None
    payload = contract.to_dict()
    month = next(item for item in payload["layers"] if item["layer_id"] == "month")
    month.update(access=paid_access, upgrade_cta=_paid_cta(paid_access))

    if paid_access in _PAID_ACCESS_ALLOWED[resolution]:
        restored = TimeLayerEntitlementV1.from_dict(payload)
        restored_month = next(item for item in restored.layers if item.layer_id == "month")
        assert restored_month.access == paid_access
        return

    with pytest.raises(ContractValidationError, match="incompatible with resolution"):
        TimeLayerEntitlementV1.from_dict(payload)


@pytest.mark.parametrize(
    ("resolution", "paid_access"),
    [
        ("unknown", "readable"),
        ("granted", "locked_paywall"),
        ("denied", "fail_closed_unknown"),
        ("unauthenticated", "readable"),
        ("request_failed", "locked_paywall"),
        ("denied", "readable"),
        ("granted", "fail_closed_unknown"),
        ("unknown", "locked_paywall"),
    ],
    ids=[
        "unknown_with_paid_readable",
        "granted_with_paid_lock",
        "denied_with_unknown_lock",
        "unauthenticated_with_paid_readable",
        "request_failed_with_paid_lock",
        "denied_with_paid_readable",
        "granted_with_unknown_lock",
        "unknown_with_paid_lock",
    ],
)
def test_from_dict_rejects_qa_resolution_access_contradictions(
    resolution: str,
    paid_access: str,
) -> None:
    contract = project_time_layer_entitlement(
        _bazi_view(years=(2026,), month_available=True, months=("2026-08",)),
        resolution="unknown",
    )
    assert contract is not None
    payload = contract.to_dict()
    payload["resolution"] = resolution
    month = next(item for item in payload["layers"] if item["layer_id"] == "month")
    month.update(access=paid_access, upgrade_cta=_paid_cta(paid_access))

    with pytest.raises(ContractValidationError, match="incompatible with resolution"):
        TimeLayerEntitlementV1.from_dict(payload)


@pytest.mark.parametrize("unknown_layer_id", ["quarter", "season", "decade"])
def test_from_dict_rejects_unknown_capability_layer_id(unknown_layer_id: str) -> None:
    contract = project_time_layer_entitlement(
        _bazi_view(years=(2026,), month_available=True, months=("2026-08",)),
        resolution="unknown",
    )
    assert contract is not None
    payload = contract.to_dict()
    payload["capability"]["time_layers"].append(
        {
            "layer_id": unknown_layer_id,
            "label": "未知层",
            "available": True,
            "unavailable_reason": None,
        }
    )

    with pytest.raises(ContractValidationError, match="outside the closed bazi table"):
        TimeLayerEntitlementV1.from_dict(payload)


def test_projection_rejects_unknown_capability_layer_from_view_model() -> None:
    view = _bazi_view(years=(2026,), month_available=True, months=("2026-08",))
    time_layers = view["time_layers"]
    assert isinstance(time_layers, list)
    time_layers.append(_layer("quarter", "流季", available=True))

    with pytest.raises(ContractValidationError, match="outside the closed bazi table"):
        project_time_layer_entitlement(view, resolution="unknown")


def test_from_dict_rejects_ziwei_unknown_capability_layer() -> None:
    contract = project_time_layer_entitlement(
        _ziwei_view(year_available=True, years=(2026,)),
        resolution="denied",
    )
    assert contract is not None
    payload = contract.to_dict()
    payload["capability"]["time_layers"].append(
        {
            "layer_id": "quarter",
            "label": "流季",
            "available": True,
            "unavailable_reason": None,
        }
    )

    with pytest.raises(ContractValidationError, match="outside the closed ziwei table"):
        TimeLayerEntitlementV1.from_dict(payload)


def test_entitlement_round_trip_is_closed_json() -> None:
    contract = project_time_layer_entitlement(
        _ziwei_view(year_available=True, years=(2026, 2027), major_limits=({"sequence": 2},)),
        resolution="granted",
    )
    assert contract is not None
    payload = contract.to_dict()

    restored = TimeLayerEntitlementV1.from_dict(payload)

    assert restored.to_dict() == payload
    assert set(payload) == {
        "schema_version",
        "capability_id",
        "resolution",
        "free_boundary_layer_id",
        "paid_layer_ids",
        "free_year_set",
        "capability",
        "layers",
    }


@pytest.mark.parametrize(
    ("owner_kind", "request_failed", "paid_grant", "expected"),
    [
        ("guest", False, None, "unauthenticated"),
        ("guest", False, True, "unauthenticated"),
        (None, False, True, "unauthenticated"),
        ("user", False, None, "unknown"),
        ("user", False, False, "denied"),
        ("user", False, True, "granted"),
        ("user", True, True, "request_failed"),
        ("guest", True, None, "request_failed"),
    ],
)
def test_resolution_mapping_is_independent_of_time_layers(
    owner_kind: Literal["user", "guest"] | None,
    request_failed: bool,
    paid_grant: bool | None,
    expected: str,
) -> None:
    assert (
        resolve_time_layer_entitlement_resolution(
            owner_kind=owner_kind,
            request_failed=request_failed,
            paid_grant=paid_grant,
        )
        == expected
    )
    if request_failed:
        assert time_layer_entitlement_resolution_for_transport_fault("timeout") == "request_failed"
        assert time_layer_entitlement_resolution_for_transport_fault("pipe-unavailable") == (
            "request_failed"
        )
    else:
        assert (
            time_layer_entitlement_resolution_for_session(
                owner_kind=owner_kind,
                paid_grant=paid_grant,
            )
            == expected
        )


def test_transport_helpers_do_not_change_stopped_copy_or_failure_table() -> None:
    timeout = failure_for_transport_fault("timeout")
    isolated = failure_for_transport_fault("already-isolated")
    stopped = generic_runtime_stopped(failure=timeout)

    assert timeout.to_dict() == {
        "schema_version": "mingli-runtime-failure/v1",
        "code": "transient.timeout",
        "category": "transient",
        "retryable": True,
    }
    assert isolated.to_dict() == {
        "schema_version": "mingli-runtime-failure/v1",
        "code": "transient.resource_unavailable",
        "category": "transient",
        "retryable": True,
    }
    assert stopped.public_copy == WORKER_STOPPED_COPY
    assert stopped.to_dict()["public_copy"] == "本次处理未完成，请稍后重试。"
    assert "time_layers" not in stopped.to_dict()
    assert "entitlement" not in stopped.to_dict()


def test_service_projects_guest_supported_layers_as_readable_in_development() -> None:
    view = _bazi_view(
        years=(2024, 2025),
        month_available=True,
        months=("2026-08",),
        luck_cycles={"status": "calculated"},
    )
    owner = _Owner(kind="guest", id=uuid4())

    contract = ReadingService.project_time_layer_entitlement(view, owner)

    assert contract is not None
    layers = _by_id(contract)
    assert contract.resolution == "granted"
    assert layers["year"].access == "readable"
    assert layers["month"].access == "readable"
    assert layers["month"].upgrade_cta is None
    assert layers["hour"].access == "unavailable"
    assert layers["hour"].upgrade_cta is None


@pytest.mark.parametrize(
    ("request_failed", "paid_grant"),
    [
        (False, None),
        (False, False),
        (True, None),
    ],
)
def test_service_dormant_billing_state_does_not_hide_supported_layers(
    request_failed: bool,
    paid_grant: bool | None,
) -> None:
    view = _ziwei_view(
        years=(2026,),
        month_available=True,
        months=((2026, 1),),
        major_limits=({"sequence": 1},),
    )
    owner = _Owner(kind="user", id=uuid4())

    contract = ReadingService.project_time_layer_entitlement(
        view,
        owner,
        request_failed=request_failed,
        paid_grant=paid_grant,
    )

    assert contract is not None
    layers = _by_id(contract)
    assert contract.resolution == "granted"
    assert layers["life"].access == "readable"
    assert layers["year"].access == "readable"
    assert layers["major_limits"].access == "readable"
    assert layers["month"].access == "readable"
    assert layers["month"].upgrade_cta is None
    assert layers["day"].access == "unavailable"
    assert layers["day"].upgrade_cta is None


def test_pydantic_time_layers_are_capability_only() -> None:
    view = {
        "schema_version": "bazi-chart/v1",
        "time_layers": [
            TimeLayer(layer_id="life", label="本命", available=True),
            TimeLayer(
                layer_id="year",
                label="流年",
                available=False,
                unavailable_reason="尚未返回逐年盘面。",
            ),
        ],
        "core_facts": {"year_layers": [{"year": 2024}]},
    }

    contract = project_time_layer_entitlement(view, resolution="denied")

    assert contract is not None
    assert contract.capability[1].available is False
    assert _by_id(contract)["year"].access == "readable"


def test_other_view_models_are_out_of_scope() -> None:
    assert (
        project_time_layer_entitlement(
            {"schema_version": "liuyao-chart/v1", "time_layers": []},
            resolution="denied",
        )
        is None
    )
    assert project_time_layer_entitlement(None, resolution="denied") is None


def _result_response(
    contract: TimeLayerEntitlementV1 | None,
) -> ReadingResultResponse:
    return ReadingResultResponse(
        reading_version_id=uuid4(),
        status="accepted",
        accepted_copy=None,
        fact_panel=None,
        view_model=None,
        verification=None,
        input_request=None,
        document=None,
        time_layer_entitlement=TimeLayerEntitlementResponse.from_contract(contract),
    )


@pytest.mark.parametrize("art", ["bazi", "ziwei"])
@pytest.mark.parametrize("resolution", _ALL_RESOLUTIONS)
def test_result_response_exposes_entitlement_as_sibling_v1(
    art: str,
    resolution: str,
) -> None:
    view = (
        _bazi_view(
            year_available=True,
            month_available=True,
            years=(2026,),
            months=("2026-08",),
            luck_cycles={"status": "calculated"},
        )
        if art == "bazi"
        else _ziwei_view(
            year_available=True,
            month_available=True,
            years=(2026,),
            months=((2026, 8),),
            major_limits=({"sequence": 1},),
        )
    )
    original_layers = [dict(item) for item in view["time_layers"]]
    contract = project_time_layer_entitlement(view, resolution=resolution)
    assert contract is not None

    dumped = _result_response(contract).model_dump(mode="json")
    payload = dumped["time_layer_entitlement"]
    restored = TimeLayerEntitlementV1.from_dict(payload)

    assert payload["schema_version"] == TIME_LAYER_ENTITLEMENT_SCHEMA_VERSION
    assert restored == contract
    assert dumped["view_model"] is None
    assert "time_layer_entitlement" in dumped
    assert view["time_layers"] == original_layers
    assert all("tier" not in item and "access" not in item for item in original_layers)


def test_result_response_rejects_resolution_access_contradiction() -> None:
    contract = project_time_layer_entitlement(
        _bazi_view(years=(2026,), month_available=True, months=("2026-08",)),
        resolution="unknown",
    )
    assert contract is not None
    payload = contract.to_dict()
    month = next(item for item in payload["layers"] if item["layer_id"] == "month")
    month["access"] = "readable"
    month["upgrade_cta"] = None

    with pytest.raises(ValidationError):
        TimeLayerEntitlementResponse.model_validate(payload)


def test_result_response_rejects_parallel_schema_version() -> None:
    contract = project_time_layer_entitlement(
        _bazi_view(years=(2026,)),
        resolution="denied",
    )
    assert contract is not None
    payload = contract.to_dict()
    payload["schema_version"] = "time-layer-entitlement-http/v1"

    with pytest.raises(ValidationError):
        TimeLayerEntitlementResponse.model_validate(payload)


def test_result_response_omits_entitlement_for_out_of_scope_view() -> None:
    response = _result_response(None)

    assert response.time_layer_entitlement is None
    assert response.model_dump(mode="json")["time_layer_entitlement"] is None

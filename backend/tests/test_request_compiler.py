import importlib
import inspect
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "mingli"


def load_fixture(name: str) -> dict[str, Any]:
    with (FIXTURE_ROOT / name).open(encoding="utf-8") as stream:
        payload: dict[str, Any] = json.load(stream)
    return payload


def canonical_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


def confirmed_profile(compiler: Any) -> Any:
    return compiler.ConfirmedProfileVersion(
        subject_ref="profile-version:test",
        birth_datetime="1994-04-30T05:55:00+08:00",
        birth_datetime_or_four_pillars="1994-04-30T05:55:00+08:00",
        timezone="Asia/Shanghai",
        location="福建省福州市",
        gender="female",
        time_basis_policy="civil",
        zi_hour_policy="midnight",
        longitude=119.2965,
        latitude=26.0745,
        coordinate_source="user_confirmed",
    )


def test_policy_separates_release_inventory_from_p0_exposure() -> None:
    policy = importlib.import_module("app.readings.capability_policy")

    assert policy.V51_RELEASE_CAPABILITY_IDS == (
        "bazi",
        "fengshui",
        "fortune",
        "liuren",
        "liuyao",
        "luming-nayin",
        "meihua",
        "physiognomy",
        "qimen",
        "selection",
        "taiyi",
        "xingming",
        "ziwei",
    )
    assert policy.P0_EXPOSED_CAPABILITY_IDS == ("bazi", "fortune", "liuyao")


@pytest.mark.parametrize(
    "capability_id",
    [
        "fengshui",
        "liuren",
        "luming-nayin",
        "meihua",
        "physiognomy",
        "qimen",
        "selection",
        "taiyi",
        "xingming",
        "ziwei",
    ],
)
def test_product_policy_rejects_unexposed_runtime_capabilities(
    capability_id: str,
) -> None:
    policy = importlib.import_module("app.readings.capability_policy")

    with pytest.raises(policy.CapabilityNotExposedError):
        policy.require_p0_capability(capability_id)


@pytest.mark.parametrize(
    "action, capability_id, object_id, horizon_id",
    [
        ("profile_preview", "bazi", "natal", "life"),
        ("bazi_deep", "bazi", "natal", "life"),
        ("today", "fortune", "near_time_personal", "day"),
        ("near_seven", "fortune", "near_time_personal", "week"),
        ("liuyao_one_question", "liuyao", "concrete_event", "instant"),
    ],
)
def test_product_actions_have_explicit_capability_routes(
    action: str,
    capability_id: str,
    object_id: str,
    horizon_id: str,
) -> None:
    policy = importlib.import_module("app.readings.capability_policy")

    route = policy.route_for_action(action)

    assert (route.capability_id, route.object_id, route.horizon_id) == (
        capability_id,
        object_id,
        horizon_id,
    )
    assert not hasattr(policy, "choose_capability")


def test_profile_preview_default_query_promises_full_chart_overview() -> None:
    service = importlib.import_module("app.readings.service")

    default_query = service.DEFAULT_QUERIES["profile_preview"]

    assert "本命" in default_query
    assert "事业" not in default_query


def test_bazi_dimensions_cover_the_blueprint_vocabulary() -> None:
    compiler = importlib.import_module("app.readings.request_compiler")

    for dimension_ids in (("overview", "state"), ("career", "relationship", "timing")):
        command = compiler.compile_bazi_prepare(
            action="bazi_deep",
            query="请解读我的本命八字。",
            profile=confirmed_profile(compiler),
            dimension_ids=dimension_ids,
        )
        assert command.intent["dimension_ids"] == dimension_ids

    with pytest.raises(compiler.RequestCompilationError):
        compiler.compile_bazi_prepare(
            action="bazi_deep",
            query="请解读我的本命八字。",
            profile=confirmed_profile(compiler),
            dimension_ids=("wealth",),
        )


def test_free_preview_dimensions_are_pinned_to_overview_and_state() -> None:
    compiler = importlib.import_module("app.readings.request_compiler")

    command = compiler.compile_bazi_prepare(
        action="profile_preview",
        query="请预览我的本命八字概览。",
        profile=confirmed_profile(compiler),
        dimension_ids=("overview", "state"),
    )
    assert command.intent["dimension_ids"] == ("overview", "state")

    with pytest.raises(compiler.RequestCompilationError):
        compiler.compile_bazi_prepare(
            action="profile_preview",
            query="请预览我的本命八字概览。",
            profile=confirmed_profile(compiler),
            dimension_ids=("career",),
        )


def test_bazi_compiler_matches_the_frozen_fixture() -> None:
    compiler = importlib.import_module("app.readings.request_compiler")
    command = compiler.compile_bazi_prepare(
        action="profile_preview",
        query="请预览我的本命八字概览。",
        profile=confirmed_profile(compiler),
        dimension_ids=("overview", "state"),
    )
    expected = load_fixture("bazi-prepare.json")

    assert canonical_json(command.to_dict()) == canonical_json(expected)
    assert "birth_datetime_or_four_pillars" in command.to_dict()["facts"]["profile-version:test"]
    assert "birth_datetime_or_four_pillars" not in command.to_dict()["facts"]


@pytest.mark.parametrize(
    "action, reference_datetime, fixture_name",
    [
        (
            "today",
            datetime.fromisoformat("2026-08-09T01:15:00+00:00"),
            "fortune-day-prepare.json",
        ),
        (
            "near_seven",
            datetime.fromisoformat("2026-08-03T01:00:00+00:00"),
            "fortune-week-prepare.json",
        ),
    ],
)
def test_fortune_compiler_uses_server_normalized_profile_time(
    action: str,
    reference_datetime: datetime,
    fixture_name: str,
) -> None:
    compiler = importlib.import_module("app.readings.request_compiler")
    query = "看一下今天运势" if action == "today" else "看一下这周运势"

    command = compiler.compile_fortune_prepare(
        action=action,
        query=query,
        profile=confirmed_profile(compiler),
        server_reference_datetime=reference_datetime,
        dimension_ids=("career",),
    )

    assert canonical_json(command.to_dict()) == canonical_json(load_fixture(fixture_name))
    facts = command.to_dict()["facts"]["profile-version:test"]
    assert set(facts) >= {
        "birth_datetime",
        "timezone",
        "location",
        "gender",
        "reference_datetime",
    }


def test_client_timezone_cannot_override_the_confirmed_profile() -> None:
    compiler = importlib.import_module("app.readings.request_compiler")

    with pytest.raises(compiler.RequestCompilationError, match="timezone"):
        compiler.compile_fortune_prepare(
            action="today",
            query="看一下今天运势",
            profile=confirmed_profile(compiler),
            server_reference_datetime=datetime.fromisoformat("2026-08-09T01:15:00+00:00"),
            requested_timezone="America/New_York",
            dimension_ids=(),
        )


@pytest.mark.parametrize(
    "cast, fixture_name, query, event_datetime, dimensions",
    [
        (
            (9, 7, 7, 7, 7, 6),
            "liuyao-manual-prepare.json",
            "这次岗位面试能否进入下一轮？",
            "2026-08-09T12:10:00+00:00",
            ("career", "outcome", "timing"),
        ),
        (
            "digital_coin",
            "liuyao-digital-prepare.json",
            "这次合作能否按期落地？",
            "2026-08-09T12:30:00+00:00",
            ("outcome", "timing"),
        ),
    ],
)
def test_liuyao_compiler_preserves_manual_order_or_explicit_digital_coin(
    cast: tuple[int, ...] | str,
    fixture_name: str,
    query: str,
    event_datetime: str,
    dimensions: tuple[str, ...],
) -> None:
    compiler = importlib.import_module("app.readings.request_compiler")

    command = compiler.compile_liuyao_prepare(
        action="liuyao_one_question",
        query=query,
        subject_ref="user:test",
        cast=cast,
        event_datetime=datetime.fromisoformat(event_datetime),
        confirmed_timezone="Asia/Shanghai",
        location="上海",
        dimension_ids=dimensions,
    )

    assert canonical_json(command.to_dict()) == canonical_json(load_fixture(fixture_name))


@pytest.mark.parametrize(
    "cast",
    [
        "time",
        (7, 7, 7, 7, 7),
        (7, 7, 7, 7, 7, 10),
        (7, 7, 7, 7, 7, True),
    ],
)
def test_liuyao_rejects_time_cast_and_invalid_bottom_up_tosses(
    cast: tuple[int | bool, ...] | str,
) -> None:
    compiler = importlib.import_module("app.readings.request_compiler")

    with pytest.raises(compiler.RequestCompilationError):
        compiler.compile_liuyao_prepare(
            action="liuyao_one_question",
            query="这件事会怎样？",
            subject_ref="user:test",
            cast=cast,
            event_datetime=datetime.fromisoformat("2026-08-09T12:10:00+00:00"),
            confirmed_timezone="Asia/Shanghai",
            location="上海",
            dimension_ids=("outcome",),
        )


@pytest.mark.parametrize(
    "compiler_name, kwargs",
    [
        (
            "compile_bazi_prepare",
            {
                "action": "profile_preview",
                "query": "看一下这个八字",
                "dimension_ids": ("timing",),
            },
        ),
        (
            "compile_fortune_prepare",
            {
                "action": "today",
                "query": "看一下今天运势",
                "server_reference_datetime": datetime.fromisoformat("2026-08-09T01:15:00+00:00"),
                "dimension_ids": ("timing",),
            },
        ),
    ],
)
def test_compilers_reject_dimensions_outside_their_ui_allowlist(
    compiler_name: str,
    kwargs: dict[str, Any],
) -> None:
    compiler = importlib.import_module("app.readings.request_compiler")
    function = getattr(compiler, compiler_name)
    kwargs["profile"] = confirmed_profile(compiler)

    with pytest.raises(compiler.RequestCompilationError, match="dimension"):
        function(**kwargs)


def test_compilers_preserve_the_real_query_without_keyword_routing() -> None:
    compiler = importlib.import_module("app.readings.request_compiler")
    query = "  这句话原样保留，不拿关键词选择术法。  "

    command = compiler.compile_bazi_prepare(
        action="bazi_deep",
        query=query,
        profile=confirmed_profile(compiler),
        dimension_ids=("overview",),
    )

    assert command.query == query
    assert "query" not in inspect.signature(compiler._route_for_compiler).parameters

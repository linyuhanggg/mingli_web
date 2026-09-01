import importlib
import inspect
import json
from dataclasses import replace
from datetime import UTC, date, datetime
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


def test_public_runtime_gate_only_allows_the_frozen_p0_set() -> None:
    policy = importlib.import_module("app.readings.capability_policy")

    policy.require_public_runtime_capabilities(
        ("bazi", "fortune"),
        environment="production",
        real_traffic_enabled=False,
    )
    policy.require_public_runtime_capabilities(
        ("bazi", "ziwei"),
        environment="test",
        real_traffic_enabled=False,
    )

    with pytest.raises(policy.CapabilityNotExposedError, match="ziwei"):
        policy.require_public_runtime_capabilities(
            ("bazi", "ziwei"),
            environment="production",
            real_traffic_enabled=False,
        )


def test_public_product_gate_keeps_relationship_products_out_of_production() -> None:
    policy = importlib.import_module("app.readings.capability_policy")

    policy.require_public_product_exposure(
        "bazi-relationship",
        environment="test",
        real_traffic_enabled=False,
    )
    with pytest.raises(policy.CapabilityNotExposedError, match="bazi-relationship"):
        policy.require_public_product_exposure(
            "bazi-relationship",
            environment="production",
            real_traffic_enabled=False,
        )


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
        ("bazi_year_preview", "bazi", "natal", "year"),
        ("bazi_month_preview", "bazi", "natal", "month"),
        ("bazi_day_preview", "bazi", "natal", "day"),
        ("bazi_deep", "bazi", "natal", "life"),
        ("five_elements_facts_preview", "bazi", "natal", "life"),
        ("life_kline_series_preview", "bazi", "life_kline", "life"),
        ("today", "fortune", "near_time_personal", "day"),
        ("near_seven", "fortune", "near_time_personal", "week"),
        ("liuyao_one_question", "liuyao", "concrete_event", "instant"),
        ("wenshi_one_question", "liuyao", "concrete_event", "instant"),
        ("ziwei_preview", "ziwei", "natal", "life"),
        ("ziwei_year_preview", "ziwei", "natal", "year"),
        ("ziwei_month_preview", "ziwei", "natal", "month"),
        ("qizheng_preview", "xingming", "natal", "life"),
        ("qizheng_year_preview", "xingming", "natal", "year"),
        ("qizheng_month_preview", "xingming", "natal", "month"),
        ("qizheng_day_preview", "xingming", "natal", "day"),
        ("canwen_preview", "bazi", "natal", "life"),
        ("hecan_preview", "bazi", "natal", "life"),
        ("bazi_relationship_preview", "bazi", "natal", "life"),
        ("ziwei_relationship_preview", "ziwei", "natal", "life"),
        ("qizheng_relationship_preview", "xingming", "natal", "life"),
        ("meihua_preview", "meihua", "concrete_event", "instant"),
        ("luming_nayin_preview", "luming-nayin", "natal", "life"),
        ("rhythm_preview", "luming-nayin", "natal", "life"),
        ("taiyi_preview", "taiyi", "macro_historical", "year"),
        ("selection_preview", "selection", "calendar_choice", "year"),
        ("fengshui_preview", "fengshui", "spatial_observation", "instant"),
        ("physiognomy_preview", "physiognomy", "visible_observation", "instant"),
        ("qimen_one_question", "qimen", "concrete_event", "instant"),
        ("liuren_one_question", "liuren", "concrete_event", "instant"),
        ("liuren_timing_question", "liuren", "concrete_event", "month"),
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


def test_every_p10_provider_has_a_product_action_mapping() -> None:
    policy = importlib.import_module("app.readings.capability_policy")

    expected_actions = {
        "bazi": (
            "profile_preview",
            "bazi_year_preview",
            "bazi_month_preview",
            "bazi_day_preview",
            "bazi_deep",
            "five_elements_facts_preview",
            "life_kline_series_preview",
            "chart_similarity_preview",
            "canwen_preview",
            "hecan_preview",
            "bazi_relationship_preview",
        ),
        "fengshui": ("fengshui_preview",),
        "fortune": ("today", "near_seven"),
        "liuren": ("liuren_one_question", "liuren_timing_question"),
        "liuyao": (
            "liuyao_one_question",
            "liuyao_deep",
            "wenshi_one_question",
        ),
        "luming-nayin": ("luming_nayin_preview", "rhythm_preview"),
        "meihua": ("meihua_preview",),
        "physiognomy": ("physiognomy_preview",),
        "selection": ("selection_preview",),
        "taiyi": ("taiyi_preview",),
        "qimen": ("qimen_one_question", "qimen_deep"),
        "xingming": (
            "qizheng_preview",
            "qizheng_year_preview",
            "qizheng_month_preview",
            "qizheng_day_preview",
            "qizheng_relationship_preview",
        ),
        "ziwei": (
            "ziwei_preview",
            "ziwei_year_preview",
            "ziwei_month_preview",
            "ziwei_relationship_preview",
        ),
        "time-check": ("time_check_preview",),
    }

    assert tuple(expected_actions) == policy.P10_EXPOSED_CAPABILITY_IDS
    assert {
        capability_id: policy.product_actions_for_capability(capability_id)
        for capability_id in policy.P10_EXPOSED_CAPABILITY_IDS
    } == expected_actions


def test_bazi_compiler_matches_the_frozen_fixture() -> None:
    compiler = importlib.import_module("app.readings.request_compiler")
    command = compiler.compile_bazi_prepare(
        action="profile_preview",
        query="看一下这个八字，事业上最该先抓住哪条主线？",
        profile=confirmed_profile(compiler),
        dimension_ids=("career",),
    )
    expected = load_fixture("bazi-prepare.json")

    assert canonical_json(command.to_dict()) == canonical_json(expected)
    assert "birth_datetime_or_four_pillars" in command.to_dict()["facts"]["profile-version:test"]
    assert "birth_datetime_or_four_pillars" not in command.to_dict()["facts"]


def test_bazi_year_compiler_requests_one_exact_year() -> None:
    compiler = importlib.import_module("app.readings.request_compiler")

    command = compiler.compile_bazi_year_prepare(
        action="bazi_year_preview",
        query="检查 2026 流年事实",
        profile=confirmed_profile(compiler),
        year=2026,
        dimension_ids=("career",),
    )

    assert command.intent["horizon"] == {
        "kind_id": "year",
        "start": "2026",
        "end": "2026",
    }
    assert command.intent["capability_id"] == "bazi"


@pytest.mark.parametrize(
    ("compiler_name", "action", "horizon", "argument", "capability_id"),
    [
        (
            "compile_bazi_month_prepare",
            "bazi_month_preview",
            ("month", "2026-08", "2026-08"),
            {"month": "2026-08"},
            "bazi",
        ),
        (
            "compile_bazi_day_prepare",
            "bazi_day_preview",
            ("day", "2026-08-15", "2026-08-15"),
            {"target_date": date(2026, 8, 15)},
            "bazi",
        ),
        (
            "compile_ziwei_month_prepare",
            "ziwei_month_preview",
            ("month", "2026-08", "2026-08"),
            {"month": "2026-08"},
            "ziwei",
        ),
        (
            "compile_qizheng_month_prepare",
            "qizheng_month_preview",
            ("month", "2026-08", "2026-08"),
            {"month": "2026-08"},
            "xingming",
        ),
        (
            "compile_qizheng_day_prepare",
            "qizheng_day_preview",
            ("day", "2026-08-15", "2026-08-15"),
            {"target_date": date(2026, 8, 15)},
            "xingming",
        ),
    ],
)
def test_natal_temporal_compilers_request_exact_runtime_horizon(
    compiler_name: str,
    action: str,
    horizon: tuple[str, str, str],
    argument: dict[str, Any],
    capability_id: str,
) -> None:
    compiler = importlib.import_module("app.readings.request_compiler")
    command = getattr(compiler, compiler_name)(
        action=action,
        query="检查时间层事实",
        profile=confirmed_profile(compiler),
        dimension_ids=("career",),
        **argument,
    )

    assert command.intent["horizon"] == {
        "kind_id": horizon[0],
        "start": horizon[1],
        "end": horizon[2],
    }
    assert command.intent["capability_id"] == capability_id


@pytest.mark.parametrize(
    ("compiler_name", "action", "capability_id"),
    [
        ("compile_ziwei_year_prepare", "ziwei_year_preview", "ziwei"),
        ("compile_qizheng_year_prepare", "qizheng_year_preview", "xingming"),
    ],
)
def test_natal_year_compilers_request_one_exact_year(
    compiler_name: str,
    action: str,
    capability_id: str,
) -> None:
    compiler = importlib.import_module("app.readings.request_compiler")

    command = getattr(compiler, compiler_name)(
        action=action,
        query="检查 2026 年层事实",
        profile=confirmed_profile(compiler),
        year=2026,
        dimension_ids=("career",),
    )

    assert command.intent["horizon"] == {
        "kind_id": "year",
        "start": "2026",
        "end": "2026",
    }
    assert command.intent["capability_id"] == capability_id


def test_bazi_compiler_expands_true_solar_product_label_to_runtime_policy() -> None:
    compiler = importlib.import_module("app.readings.request_compiler")

    command = compiler.compile_bazi_prepare(
        action="profile_preview",
        query="检查真太阳时口径",
        profile=replace(confirmed_profile(compiler), time_basis_policy="solar"),
        dimension_ids=("overview",),
    )

    assert (
        command.to_dict()["facts"]["profile-version:test"]["time_basis_policy"]
        == "local_apparent_solar-v1"
    )


def test_five_elements_facts_compiler_has_a_narrow_state_dimension() -> None:
    compiler = importlib.import_module("app.readings.request_compiler")

    command = compiler.compile_five_elements_facts_prepare(
        action="five_elements_facts_preview",
        query="只展示五行库存和调候事实",
        profile=confirmed_profile(compiler),
        dimension_ids=("state",),
    )

    assert command.to_dict()["intent"] == {
        "subject_refs": ["profile-version:test"],
        "object_id": "natal",
        "dimension_ids": ["state"],
        "horizon": {"kind_id": "life", "start": None, "end": None},
        "capability_id": "bazi",
        "comparisons": [],
    }
    with pytest.raises(compiler.RequestCompilationError, match="outside the product allowlist"):
        compiler.compile_five_elements_facts_prepare(
            action="five_elements_facts_preview",
            query="不能把事业结论混入事实切片",
            profile=confirmed_profile(compiler),
            dimension_ids=("career",),
        )


def test_life_kline_series_compiler_uses_life_kline_object_and_overview() -> None:
    compiler = importlib.import_module("app.readings.request_compiler")

    command = compiler.compile_life_kline_series_prepare(
        action="life_kline_series_preview",
        query="只展示人生K线权威缺口",
        profile=confirmed_profile(compiler),
        dimension_ids=("overview",),
    )

    assert command.to_dict()["intent"] == {
        "subject_refs": ["profile-version:test"],
        "object_id": "life_kline",
        "dimension_ids": ["overview"],
        "horizon": {"kind_id": "life", "start": None, "end": None},
        "capability_id": "bazi",
        "comparisons": [],
    }
    with pytest.raises(compiler.RequestCompilationError, match="outside the product allowlist"):
        compiler.compile_life_kline_series_prepare(
            action="life_kline_series_preview",
            query="不能用 state 维度绕过 life_kline overview",
            profile=confirmed_profile(compiler),
            dimension_ids=("state",),
        )


def test_compiler_translates_product_zi_hour_aliases_before_runtime() -> None:
    compiler = importlib.import_module("app.readings.request_compiler")

    solar = compiler.compile_bazi_prepare(
        action="profile_preview",
        query="检查真太阳时下的子时口径",
        profile=replace(
            confirmed_profile(compiler),
            time_basis_policy="solar",
            zi_hour_policy="solar",
        ),
        dimension_ids=("overview",),
    )
    substitute = compiler.compile_bazi_prepare(
        action="profile_preview",
        query="检查替代子时口径",
        profile=replace(confirmed_profile(compiler), zi_hour_policy="substitute"),
        dimension_ids=("overview",),
    )

    solar_facts = solar.to_dict()["facts"]["profile-version:test"]
    substitute_facts = substitute.to_dict()["facts"]["profile-version:test"]
    assert solar_facts["time_basis_policy"] == "local_apparent_solar-v1"
    assert solar_facts["zi_hour_policy"] == "midnight"
    assert substitute_facts["zi_hour_policy"] == "late-zi-next-day"


def test_compiler_rejects_unknown_zi_hour_policy_before_runtime() -> None:
    compiler = importlib.import_module("app.readings.request_compiler")

    with pytest.raises(compiler.RequestCompilationError, match="Zi-hour"):
        compiler.compile_bazi_prepare(
            action="profile_preview",
            query="不应把未知子时口径送入 Runtime",
            profile=replace(confirmed_profile(compiler), zi_hour_policy="unknown"),
            dimension_ids=("overview",),
        )


def test_bazi_compiler_does_not_mislabel_lunar_datetime_as_civil_time() -> None:
    compiler = importlib.import_module("app.readings.request_compiler")

    with pytest.raises(compiler.RequestCompilationError, match="lunar"):
        compiler.compile_bazi_prepare(
            action="profile_preview",
            query="不应静默转换农历输入",
            profile=replace(confirmed_profile(compiler), time_basis_policy="lunar"),
            dimension_ids=("overview",),
        )


def test_natal_art_compilers_preserve_runtime_policy_and_explicit_capability() -> None:
    compiler = importlib.import_module("app.readings.request_compiler")
    profile = replace(confirmed_profile(compiler), time_basis_policy="solar")

    ziwei = compiler.compile_ziwei_prepare(
        action="ziwei_preview",
        query="查看紫微本命盘",
        profile=profile,
        dimension_ids=("career",),
    )
    qizheng = compiler.compile_qizheng_prepare(
        action="qizheng_preview",
        query="查看七政本命盘",
        profile=profile,
        dimension_ids=("career",),
    )

    assert ziwei.to_dict()["intent"]["capability_id"] == "ziwei"
    assert qizheng.to_dict()["intent"]["capability_id"] == "xingming"
    assert (
        ziwei.to_dict()["facts"]["profile-version:test"]["time_basis_policy"]
        == "local_apparent_solar-v1"
    )
    assert (
        qizheng.to_dict()["facts"]["profile-version:test"]["coordinate_source"]
        == "user_confirmed"
    )


def test_internal_provider_compilers_bind_their_manifest_input_slots() -> None:
    compiler = importlib.import_module("app.readings.request_compiler")
    profile = confirmed_profile(compiler)

    luming = compiler.compile_luming_nayin_prepare(
        action="luming_nayin_preview",
        query="只查看四柱纳音基础事实",
        profile=profile,
        dimension_ids=("career", "state"),
    )
    rhythm = compiler.compile_luming_nayin_prepare(
        action="rhythm_preview",
        query="只查看本命纳音音律事实",
        profile=profile,
        dimension_ids=("state",),
    )
    taiyi = compiler.compile_taiyi_prepare(
        action="taiyi_preview",
        query="查看年度太乙年计盘结构",
        subject_ref="taiyi:fixture",
        reference_datetime=datetime.fromisoformat("2026-08-14T02:00:00+00:00"),
        confirmed_timezone="Asia/Shanghai",
        location="上海市",
        dimension_ids=("outcome", "timing"),
        time_basis_policy="solar",
        longitude=121.4737,
        latitude=31.2304,
        coordinate_source="user_confirmed",
    )
    selection = compiler.compile_selection_prepare(
        action="selection_preview",
        query="比较一段日期里的开市日课事实",
        subject_ref="selection:fixture",
        event_profile="business_opening_transaction",
        requested_actions=("开市",),
        date_range_start="2026-09-01",
        date_range_end="2026-09-03",
        confirmed_timezone="Asia/Shanghai",
        location="上海市",
        dimension_ids=("timing", "state"),
    )
    fengshui = compiler.compile_fengshui_prepare(
        action="fengshui_preview",
        query="只查看已测空间事实",
        subject_ref="fengshui:fixture",
        fengshui_spec={"schema_version": "mingli-fengshui-input-v1"},
        dimension_ids=("current_state", "direction"),
    )
    physiognomy = compiler.compile_physiognomy_prepare(
        action="physiognomy_preview",
        query="只查看已确认的可见观察事实",
        subject_ref="sid-physiognomy-fixture",
        physiognomy_spec={"schema_version": "mingli-physiognomy-input-v1"},
        dimension_ids=("state", "source_comparison"),
    )

    assert luming.to_dict()["intent"]["capability_id"] == "luming-nayin"
    assert rhythm.to_dict()["intent"]["capability_id"] == "luming-nayin"
    assert rhythm.to_dict()["intent"]["object_id"] == "natal"
    assert (
        luming.to_dict()["facts"]["profile-version:test"][
            "birth_datetime_or_four_pillars"
        ]
        == profile.birth_datetime
    )
    assert taiyi.to_dict()["facts"]["taiyi:fixture"]["time_basis_policy"] == (
        "local_apparent_solar-v1"
    )
    assert selection.to_dict()["facts"]["selection:fixture"]["event_profile"] == (
        "business_opening_transaction"
    )
    assert fengshui.to_dict()["intent"]["object_id"] == "spatial_observation"
    assert physiognomy.to_dict()["intent"]["capability_id"] == "physiognomy"
    assert physiognomy.to_dict()["facts"]["sid-physiognomy-fixture"][
        "physiognomy_spec"
    ]["schema_version"] == "mingli-physiognomy-input-v1"


def test_canwen_compiler_binds_selected_arts_as_required_runtime_comparisons() -> None:
    compiler = importlib.import_module("app.readings.request_compiler")

    command = compiler.compile_canwen_prepare(
        action="canwen_preview",
        query="比较三张命盘在事业与关系上的共同信号",
        profile=confirmed_profile(compiler),
        selected_art_ids=("bazi", "ziwei", "qizheng"),
        dimension_ids=("career", "relationship", "state"),
    )

    assert canonical_json(command.to_dict()) == canonical_json(
        load_fixture("canwen-prepare.json")
    )
    assert command.to_dict()["intent"]["comparisons"] == [
        {"capability_id": "ziwei", "requirement": "required"},
        {"capability_id": "xingming", "requirement": "required"},
    ]


def test_hecan_compiler_reuses_the_required_natal_comparison_contract() -> None:
    compiler = importlib.import_module("app.readings.request_compiler")

    command = compiler.compile_hecan_prepare(
        action="hecan_preview",
        query="展示三术共同事实范围",
        profile=confirmed_profile(compiler),
        selected_art_ids=("bazi", "ziwei"),
        dimension_ids=("career",),
    )

    payload = command.to_dict()
    assert payload["intent"]["capability_id"] == "bazi"
    assert payload["intent"]["comparisons"] == [
        {"capability_id": "ziwei", "requirement": "required"},
    ]
    assert payload["facts"]["profile-version:test"]["time_basis_policy"] == "civil"


@pytest.mark.parametrize(
    "art_id, action, capability_id",
    [
        ("bazi", "bazi_relationship_preview", "bazi"),
        ("ziwei", "ziwei_relationship_preview", "ziwei"),
        ("qizheng", "qizheng_relationship_preview", "xingming"),
    ],
)
def test_relationship_compiler_binds_two_subjects_to_one_runtime_prepare(
    art_id: str,
    action: str,
    capability_id: str,
) -> None:
    compiler = importlib.import_module("app.readings.request_compiler")
    first = confirmed_profile(compiler)
    second = replace(first, subject_ref="profile-version:other", gender="male")

    command = compiler.compile_relationship_prepare(
        action=action,
        query="查看双方跨盘结构事实",
        art_id=art_id,
        relationship_type="romantic",
        profiles=(first, second),
        dimension_ids=("relationship",),
    )

    payload = command.to_dict()
    assert payload["intent"]["capability_id"] == capability_id
    assert payload["intent"]["subject_refs"] == [
        "profile-version:test",
        "profile-version:other",
    ]
    assert set(payload["facts"]) == {
        "profile-version:test",
        "profile-version:other",
    }
    assert payload["intent"]["dimension_ids"] == ["relationship"]


def test_wenshi_compiler_binds_the_same_event_to_three_required_runtime_arts() -> None:
    compiler = importlib.import_module("app.readings.request_compiler")

    command = compiler.compile_wenshi_prepare(
        action="wenshi_one_question",
        query="这件事能否按期完成？",
        subject_ref="wenshi:synthetic",
        cast=(6, 7, 8, 9, 6, 7),
        event_datetime=datetime.fromisoformat("2026-08-14T10:00:00+08:00"),
        confirmed_timezone="Asia/Shanghai",
        location="合成测试地点",
        dimension_ids=("outcome", "timing"),
        time_basis_policy="civil",
        zi_hour_policy="midnight",
        longitude=120.0,
        latitude=30.0,
        coordinate_source="synthetic-fixture",
    )

    payload = command.to_dict()
    assert payload["intent"]["capability_id"] == "liuyao"
    assert payload["intent"]["comparisons"] == [
        {"capability_id": "qimen", "requirement": "required"},
        {"capability_id": "liuren", "requirement": "required"},
    ]
    assert payload["intent"]["dimension_ids"] == ["outcome", "timing"]
    assert payload["facts"]["wenshi:synthetic"]["cast"] == [6, 7, 8, 9, 6, 7]
    assert payload["facts"]["wenshi:synthetic"][
        "event_datetime_or_reference_datetime"
    ] == "2026-08-14T10:00:00+08:00"
    assert payload["facts"]["wenshi:synthetic"]["time_basis_policy"] == "civil"


@pytest.mark.parametrize(
    "dimension_ids",
    [("career",), ("outcome", "outcome"), ("unknown",)],
)
def test_wenshi_compiler_rejects_dimensions_outside_the_cross_art_contract(
    dimension_ids: tuple[str, ...],
) -> None:
    compiler = importlib.import_module("app.readings.request_compiler")

    with pytest.raises(compiler.RequestCompilationError, match="dimension"):
        compiler.compile_wenshi_prepare(
            action="wenshi_one_question",
            query="不应生成越界合参",
            subject_ref="wenshi:synthetic",
            cast=(6, 7, 8, 9, 6, 7),
            event_datetime=datetime.fromisoformat("2026-08-14T10:00:00+08:00"),
            confirmed_timezone="Asia/Shanghai",
            location="合成测试地点",
            dimension_ids=dimension_ids,
        )


@pytest.mark.parametrize(
    "selected_art_ids",
    [
        (),
        ("bazi",),
        ("bazi", "bazi"),
        ("bazi", "unknown"),
        ("ziwei", "bazi"),
    ],
)
def test_canwen_compiler_rejects_incomplete_or_ambiguous_art_selection(
    selected_art_ids: tuple[str, ...],
) -> None:
    compiler = importlib.import_module("app.readings.request_compiler")

    with pytest.raises(compiler.RequestCompilationError, match="canwen"):
        compiler.compile_canwen_prepare(
            action="canwen_preview",
            query="不应生成残缺合参",
            profile=confirmed_profile(compiler),
            selected_art_ids=selected_art_ids,
            dimension_ids=("career",),
        )


def test_qizheng_compiler_requires_confirmed_coordinates() -> None:
    compiler = importlib.import_module("app.readings.request_compiler")

    with pytest.raises(compiler.RequestCompilationError, match="longitude"):
        compiler.compile_qizheng_prepare(
            action="qizheng_preview",
            query="缺少坐标不应生成七政盘",
            profile=replace(
                confirmed_profile(compiler),
                longitude=None,
                latitude=None,
                coordinate_source=None,
            ),
            dimension_ids=("career",),
        )


def test_hecan_compiler_requires_confirmed_coordinates_when_qizheng_is_selected() -> None:
    compiler = importlib.import_module("app.readings.request_compiler")

    with pytest.raises(compiler.RequestCompilationError, match="longitude"):
        compiler.compile_hecan_prepare(
            action="hecan_preview",
            query="缺少七政坐标不应生成合参准备",
            profile=replace(
                confirmed_profile(compiler),
                longitude=None,
                latitude=None,
                coordinate_source=None,
            ),
            selected_art_ids=("bazi", "qizheng"),
            dimension_ids=("career",),
        )


def test_meihua_time_compiler_matches_the_frozen_fixture() -> None:
    compiler = importlib.import_module("app.readings.request_compiler")
    command = compiler.compile_meihua_prepare(
        action="meihua_preview",
        query="用时间起一卦看这件事的状态与结果",
        subject_ref="meihua:fixture",
        casting_method="time",
        event_datetime=datetime.fromisoformat("2026-08-14T02:00:00+00:00"),
        confirmed_timezone="Asia/Shanghai",
        location="上海市",
        dimension_ids=("outcome", "state"),
        time_basis_policy="solar",
        longitude=121.4737,
        latitude=31.2304,
        coordinate_source="user_confirmed",
    )

    assert canonical_json(command.to_dict()) == canonical_json(
        load_fixture("meihua-time-prepare.json")
    )


@pytest.mark.parametrize(
    ("casting_method", "method_kwargs", "expected_fields"),
    [
        (
            "supplied_number",
            {"number": 17, "provenance": {"kind": "user_supplied", "source": "fixture"}},
            {
                "casting_method": "supplied_number",
                "number": 17,
                "provenance": {"kind": "user_supplied", "source": "fixture"},
            },
        ),
        (
            "sound_count",
            {"count": 9, "observation_source": {"kind": "sound_count", "source": "fixture"}},
            {
                "casting_method": "sound_count",
                "count": 9,
                "observation_source": {"kind": "sound_count", "source": "fixture"},
            },
        ),
        (
            "observation",
            {
                "upper_trigram": "乾",
                "lower_trigram": "坤",
                "observation_source": {"kind": "direct_observation", "source": "fixture"},
            },
            {
                "casting_method": "observation",
                "upper_trigram": "乾",
                "lower_trigram": "坤",
                "observation_source": {"kind": "direct_observation", "source": "fixture"},
            },
        ),
        (
            "supplied_hexagram",
            {
                "upper_trigram": "乾",
                "lower_trigram": "坤",
                "moving_line": 4,
                "provenance": {"kind": "user_supplied", "source": "fixture"},
            },
            {
                "casting_method": "supplied_hexagram",
                "upper_trigram": "乾",
                "lower_trigram": "坤",
                "moving_line": 4,
                "provenance": {"kind": "user_supplied", "source": "fixture"},
            },
        ),
    ],
)
def test_meihua_compiler_preserves_explicit_method_facts(
    casting_method: str,
    method_kwargs: dict[str, object],
    expected_fields: dict[str, object],
) -> None:
    compiler = importlib.import_module("app.readings.request_compiler")

    command = compiler.compile_meihua_prepare(
        action="meihua_preview",
        query="按明确起法计算梅花盘",
        subject_ref="meihua:fixture",
        casting_method=casting_method,
        event_datetime=datetime.fromisoformat("2026-08-14T02:00:00+00:00"),
        confirmed_timezone="Asia/Shanghai",
        location="上海市",
        dimension_ids=("outcome",),
        **method_kwargs,
    )

    facts = command.to_dict()["facts"]["meihua:fixture"]
    assert isinstance(facts, dict)
    assert {key: facts[key] for key in expected_fields} == expected_fields


@pytest.mark.parametrize(
    ("casting_method", "method_kwargs", "message"),
    [
        ("supplied_number", {}, "number"),
        ("sound_count", {"count": 3}, "observation_source"),
        ("observation", {"upper_trigram": "乾", "lower_trigram": "坤"}, "observation_source"),
        (
            "supplied_hexagram",
            {"upper_trigram": "乾", "lower_trigram": "坤", "moving_line": 2},
            "provenance",
        ),
    ],
)
def test_meihua_compiler_rejects_incomplete_method_facts(
    casting_method: str,
    method_kwargs: dict[str, object],
    message: str,
) -> None:
    compiler = importlib.import_module("app.readings.request_compiler")

    with pytest.raises(compiler.RequestCompilationError, match=message):
        compiler.compile_meihua_prepare(
            action="meihua_preview",
            query="缺少起法资料不应进入 Runtime",
            subject_ref="meihua:fixture",
            casting_method=casting_method,
            event_datetime=datetime.fromisoformat("2026-08-14T02:00:00+00:00"),
            confirmed_timezone="Asia/Shanghai",
            location="上海市",
            dimension_ids=("outcome",),
            **method_kwargs,
        )


@pytest.mark.parametrize(
    "compiler_name, action, capability_id",
    [
        ("compile_qimen_prepare", "qimen_one_question", "qimen"),
        ("compile_liuren_prepare", "liuren_one_question", "liuren"),
    ],
)
def test_event_art_compilers_normalize_event_time_and_policy(
    compiler_name: str,
    action: str,
    capability_id: str,
) -> None:
    compiler = importlib.import_module("app.readings.request_compiler")
    command = getattr(compiler, compiler_name)(
        action=action,
        query="检查事件术数接线",
        subject_ref="event:fixture",
        event_datetime=datetime.fromisoformat("2026-08-14T02:00:00+00:00"),
        confirmed_timezone="Asia/Shanghai",
        location="上海市",
        dimension_ids=("outcome", "timing"),
        time_basis_policy="solar",
    )
    payload = command.to_dict()

    assert payload["intent"]["capability_id"] == capability_id
    event_fact_id = (
        "event_datetime_or_reference_datetime"
        if capability_id == "liuren"
        else "event_datetime"
    )
    assert payload["facts"]["event:fixture"][event_fact_id] == "2026-08-14T10:00:00+08:00"
    assert payload["facts"]["event:fixture"]["time_basis_policy"] == "local_apparent_solar-v1"


def test_liuren_work_compiler_binds_explicit_target_relative() -> None:
    compiler = importlib.import_module("app.readings.request_compiler")
    command = compiler.compile_liuren_prepare(
        action="liuren_one_question",
        query="事业项目能否推进",
        subject_ref="event:work-fixture",
        event_datetime=datetime.fromisoformat("2026-08-14T02:00:00+00:00"),
        confirmed_timezone="Asia/Shanghai",
        location="上海市",
        dimension_ids=("work",),
        target_relative="官鬼",
    )
    assert command.to_dict()["facts"]["event:work-fixture"]["target_relative"] == "官鬼"

    with pytest.raises(compiler.RequestCompilationError, match="target_relative"):
        compiler.compile_liuren_prepare(
            action="liuren_one_question",
            query="不应接受无效类神",
            subject_ref="event:work-fixture",
            event_datetime=datetime.fromisoformat("2026-08-14T02:00:00+00:00"),
            confirmed_timezone="Asia/Shanghai",
            location="上海市",
            dimension_ids=("work",),
            target_relative="不存在",
        )


def test_liuren_timing_compiler_binds_a_bounded_month_horizon() -> None:
    compiler = importlib.import_module("app.readings.request_compiler")
    command = compiler.compile_liuren_prepare(
        action="liuren_timing_question",
        query="这件事何时可能出现回应？",
        subject_ref="event:timing-fixture",
        event_datetime=datetime.fromisoformat("2026-08-14T02:00:00+00:00"),
        confirmed_timezone="Asia/Shanghai",
        location="上海市",
        dimension_ids=("timing",),
        timing_start=date(2026, 8, 15),
        timing_end=date(2026, 9, 14),
    )

    assert command.to_dict()["intent"]["horizon"] == {
        "kind_id": "month",
        "start": "2026-08-15",
        "end": "2026-09-14",
    }

    with pytest.raises(compiler.RequestCompilationError, match="31 days"):
        compiler.compile_liuren_prepare(
            action="liuren_timing_question",
            query="不接受无限时间窗",
            subject_ref="event:timing-fixture",
            event_datetime=datetime.fromisoformat("2026-08-14T02:00:00+00:00"),
            confirmed_timezone="Asia/Shanghai",
            location="上海市",
            dimension_ids=("timing",),
            timing_start=date(2026, 8, 15),
            timing_end=date(2026, 9, 15),
        )


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


def test_fortune_compiler_passes_coordinates_for_true_solar_profile_time() -> None:
    compiler = importlib.import_module("app.readings.request_compiler")
    profile = replace(confirmed_profile(compiler), time_basis_policy="solar")

    command = compiler.compile_fortune_prepare(
        action="today",
        query="检查真太阳时今日运势输入",
        profile=profile,
        server_reference_datetime=datetime.fromisoformat("2026-08-14T02:00:00+00:00"),
        dimension_ids=("career",),
    )

    facts = command.to_dict()["facts"]["profile-version:test"]
    assert facts["time_basis_policy"] == "local_apparent_solar-v1"
    assert facts["longitude"] == 119.2965
    assert facts["latitude"] == 26.0745
    assert facts["coordinate_source"] == "user_confirmed"


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


def test_liuyao_deep_compiles_the_fixed_event_dimensions() -> None:
    compiler = importlib.import_module("app.readings.request_compiler")

    command = compiler.compile_liuyao_prepare(
        action="liuyao_deep",
        query="验证六爻深读合同",
        subject_ref="liuyao-deep:test",
        cast=(6, 7, 8, 9, 7, 8),
        event_datetime=datetime(2026, 8, 14, 10, 0, tzinfo=UTC),
        confirmed_timezone="Asia/Shanghai",
        location="上海市",
        dimension_ids=("outcome", "timing", "state"),
    )

    assert command.intent["capability_id"] == "liuyao"
    assert command.intent["dimension_ids"] == ("outcome", "timing", "state")
    assert command.facts["liuyao-deep:test"]["cast"] == (6, 7, 8, 9, 7, 8)


def test_liuyao_compiler_preserves_explicit_finance_question_class() -> None:
    compiler = importlib.import_module("app.readings.request_compiler")

    command = compiler.compile_liuyao_prepare(
        action="liuyao_one_question",
        query="验证求财问题的结构化输入",
        subject_ref="liuyao-finance:test",
        cast=(6, 7, 8, 9, 7, 8),
        event_datetime=datetime(2026, 8, 14, 10, 0, tzinfo=UTC),
        confirmed_timezone="Asia/Shanghai",
        location="上海市",
        dimension_ids=("outcome",),
        question_class="finance",
    )

    assert command.facts["liuyao-finance:test"]["question_class"] == "finance"

    with pytest.raises(compiler.RequestCompilationError, match="question class"):
        compiler.compile_liuyao_prepare(
            action="liuyao_one_question",
            query="不允许的六爻问题类别",
            subject_ref="liuyao-finance:test",
            cast=(6, 7, 8, 9, 7, 8),
            event_datetime=datetime(2026, 8, 14, 10, 0, tzinfo=UTC),
            confirmed_timezone="Asia/Shanghai",
            location="上海市",
            dimension_ids=("outcome",),
            question_class="unknown",
        )

import json
import os
from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from app.adapters.runtime import MingliRuntime, build_runtime_startup_gate
from app.charts.contracts import (
    BaziChartV1,
    DaliurenChartV1,
    FortuneFactsViewV1,
    LiuyaoChartV1,
    PhysiognomyViewV1,
    QizhengChartV1,
    ZiweiChartV1,
)
from app.charts.projectors import (
    project_bazi_view_model,
    project_daliuren_view_model,
    project_fortune_view_model,
    project_liuyao_view_model,
    project_physiognomy_view_model,
    project_qizheng_view_model,
    project_ziwei_view_model,
)
from app.config import Settings
from app.media.physiognomy import InMemoryPrivateMediaStore, PhysiognomyMediaAdapter
from app.readings.public_fact_panel import project_public_fact_panel
from app.readings.request_compiler import (
    ConfirmedProfileVersion,
    compile_bazi_day_prepare,
    compile_bazi_month_prepare,
    compile_bazi_prepare,
    compile_bazi_year_prepare,
    compile_fortune_prepare,
    compile_liuren_prepare,
    compile_liuyao_prepare,
    compile_qizheng_day_prepare,
    compile_qizheng_month_prepare,
    compile_qizheng_prepare,
    compile_qizheng_year_prepare,
    compile_ziwei_month_prepare,
    compile_ziwei_prepare,
    compile_ziwei_year_prepare,
)
from app.readings.runtime_contracts import Prepared

pytestmark = pytest.mark.skipif(
    os.environ.get("MINGLI_RUN_REAL_RUNTIME_TESTS") != "1",
    reason="real frozen Runtime test is opt-in",
)


SYNTHETIC_PROFILE = ConfirmedProfileVersion(
    subject_ref="profile-version:public-core-synthetic",
    birth_datetime="1994-04-30T05:55:00+08:00",
    birth_datetime_or_four_pillars="1994-04-30T05:55:00+08:00",
    timezone="Asia/Shanghai",
    location="福建省福州市",
    gender="male",
    time_basis_policy="solar",
    zi_hour_policy="midnight",
    longitude=119.2965,
    latitude=26.0745,
    coordinate_source="synthetic-fixture",
)


async def _runtime() -> MingliRuntime:
    gate = build_runtime_startup_gate(Settings())
    await gate.startup()
    return gate.runtime


@pytest.mark.asyncio
async def test_real_runtime_projects_public_natal_and_divination_core() -> None:
    runtime = await _runtime()

    bazi = await runtime.execute(
        compile_bazi_prepare(
            action="profile_preview",
            query="验证八字核心盘面",
            profile=SYNTHETIC_PROFILE,
            dimension_ids=("career",),
        )
    )
    assert isinstance(bazi, Prepared)
    bazi_brief = bazi.to_dict()["brief"]
    bazi_view = project_bazi_view_model(bazi_brief)
    assert isinstance(bazi_view, BaziChartV1)
    assert bazi_view.core_facts is not None
    assert bazi_view.core_facts.year_layers is None
    assert bazi_view.core_facts.month_layers is None
    assert bazi_view.core_facts.day_layers is None
    source_patterns = bazi_view.core_facts.source_conditioned_patterns
    assert [pattern.local_rule_id for pattern in source_patterns] == [
        "DR-01-01",
        "QR-02-01",
        "QTB-M01",
        "R-01-02",
        "R-02-04",
        "ZPR-01",
    ]
    assert all(pattern.fact_paths for pattern in source_patterns)
    assert all(pattern.predicate_audit for pattern in source_patterns)
    assert [
        pattern.local_rule_id
        for pattern in source_patterns
        if pattern.evidence_ref is not None
    ] == ["QR-02-01", "QTB-M01", "R-01-02", "R-02-04", "ZPR-01"]
    assert [
        pattern.local_rule_id
        for pattern in source_patterns
        if pattern.evidence_ref is None
    ] == ["DR-01-01"]
    bazi_values = {
        str(item["ref"]).split("/calculated/bazi/", 1)[1]: item.get("value")
        for item in bazi_brief["facts"]
        if isinstance(item, dict)
        and "/calculated/bazi/" in str(item.get("ref"))
    }
    calendar_normalization = bazi_values["calendar_normalization"]
    assert calendar_normalization["true_solar_time"]["status"] == (
        "apparent_solar_applied"
    )
    assert "civil_datetime" not in calendar_normalization
    assert "location" not in calendar_normalization
    assert "longitude" not in calendar_normalization

    ziwei = await runtime.execute(
        compile_ziwei_prepare(
            action="ziwei_preview",
            query="验证紫微核心盘面",
            profile=SYNTHETIC_PROFILE,
            dimension_ids=("career",),
        )
    )
    assert isinstance(ziwei, Prepared)
    assert isinstance(project_ziwei_view_model(ziwei.to_dict()["brief"]), ZiweiChartV1)

    qizheng = await runtime.execute(
        compile_qizheng_prepare(
            action="qizheng_preview",
            query="验证七政核心盘面",
            profile=SYNTHETIC_PROFILE,
            dimension_ids=("career",),
        )
    )
    assert isinstance(qizheng, Prepared)
    assert isinstance(
        project_qizheng_view_model(qizheng.to_dict()["brief"]), QizhengChartV1
    )

    liuyao = await runtime.execute(
        compile_liuyao_prepare(
            action="liuyao_one_question",
            query="验证六爻核心卦盘",
            subject_ref="liuyao:public-core-synthetic",
            cast=(6, 7, 8, 9, 6, 7),
            event_datetime=datetime.fromisoformat("2026-08-14T10:00:00+08:00"),
            confirmed_timezone="Asia/Shanghai",
            location="福建省福州市",
            dimension_ids=("outcome",),
        )
    )
    assert isinstance(liuyao, Prepared)
    liuyao_view = project_liuyao_view_model(liuyao.to_dict()["brief"])
    assert isinstance(liuyao_view, LiuyaoChartV1)
    assert liuyao_view.core_facts is not None
    assert liuyao_view.core_facts.najia is not None
    assert liuyao_view.core_facts.relation_facts is not None
    assert liuyao_view.core_facts.line_facts is not None
    assert liuyao_view.core_facts.returning_relations is not None
    assert [
        pattern.local_rule_id
        for pattern in liuyao_view.core_facts.source_conditioned_patterns
    ] == ["BSZZ-M01", "HJC-M001", "HZL-M001", "ZZR-M001"]

    daliuren = await runtime.execute(
        compile_liuren_prepare(
            action="liuren_one_question",
            query="验证大六壬核心课盘",
            subject_ref="liuren:public-core-synthetic",
            event_datetime=datetime.fromisoformat("2026-08-14T10:00:00+08:00"),
            confirmed_timezone="Asia/Shanghai",
            location="福建省福州市",
            dimension_ids=("outcome", "timing"),
        )
    )
    assert isinstance(daliuren, Prepared)
    daliuren_view = project_daliuren_view_model(daliuren.to_dict()["brief"])
    assert isinstance(daliuren_view, DaliurenChartV1)
    assert daliuren_view.core_facts is not None
    assert daliuren_view.core_facts.heaven_plate is not None
    assert daliuren_view.core_facts.lesson_method is not None
    assert daliuren_view.core_facts.timing_candidates is not None
    assert daliuren_view.core_facts.dimension_facts is not None

    daliuren_timing = await runtime.execute(
        compile_liuren_prepare(
            action="liuren_timing_question",
            query="验证大六壬有界应期候选",
            subject_ref="liuren:public-timing-synthetic",
            event_datetime=datetime.fromisoformat("2026-08-14T10:00:00+08:00"),
            confirmed_timezone="Asia/Shanghai",
            location="福建省福州市",
            dimension_ids=("timing",),
            timing_start=date(2026, 8, 15),
            timing_end=date(2026, 9, 14),
        )
    )
    assert isinstance(daliuren_timing, Prepared)
    timing_values = {
        str(item["ref"]).split("/calculated/liuren/", 1)[1]: item.get("value")
        for item in daliuren_timing.to_dict()["brief"]["facts"]
        if isinstance(item, dict)
        and "/calculated/liuren/" in str(item.get("ref"))
    }
    timing_candidates = timing_values["timing_candidates"]
    assert timing_candidates
    assert timing_candidates[0]["source_rule"] == "LM-R21"
    assert timing_candidates[0]["candidate_not_guarantee"] is True
    assert "2026-08-15" <= timing_candidates[0]["solar_date"] <= "2026-09-14"

    daliuren_work = await runtime.execute(
        compile_liuren_prepare(
            action="liuren_one_question",
            query="验证大六壬事业类神事实链",
            subject_ref="liuren:public-work-synthetic",
            event_datetime=datetime.fromisoformat("2026-08-14T10:00:00+08:00"),
            confirmed_timezone="Asia/Shanghai",
            location="福建省福州市",
            dimension_ids=("work",),
            target_relative="兄弟",
        )
    )
    assert isinstance(daliuren_work, Prepared)
    work_values = {
        str(item["ref"]).split("/calculated/liuren/", 1)[1]: item.get("value")
        for item in daliuren_work.to_dict()["brief"]["facts"]
        if isinstance(item, dict)
        and "/calculated/liuren/" in str(item.get("ref"))
    }
    work_dimension = work_values["dimension_facts"]["work"]
    assert work_dimension["target_relative"] == "兄弟"
    assert work_dimension["target_contract_status"] == "bound"
    assert work_dimension["target_presence"] is True
    assert "LR-19" in work_dimension["source_rule_ids"]
    assert work_dimension["rule_evidence"]["hard_verdict"] is None

    adapter = PhysiognomyMediaAdapter(store=InMemoryPrivateMediaStore())
    asset = adapter.ingest(
        owner_kind="guest",
        owner_id=uuid4(),
        content_type="image/png",
        filename="synthetic-face.png",
        payload=b"\x89PNG\r\n\x1a\nsynthetic",
        width=1200,
        height=1600,
        consent=True,
        mode="face",
        now=datetime(2026, 8, 14, 2, 0, tzinfo=UTC),
    )
    physiognomy_input = adapter.build_runtime_input(
        asset_id=asset.asset_id,
        subject_ref="sid-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        observations=(
            {
                "region": "forehead",
                "feature_kind": "visible_morphology",
                "descriptor": "region_visible",
                "visibility": "full",
                "uncertainty": 0.1,
            },
        ),
        dimension_ids=("state",),
    )
    physiognomy = await runtime.execute(
        physiognomy_input.to_prepare(
            query="验证相法结构化观察核心",
            action="physiognomy_preview",
        )
    )
    assert isinstance(physiognomy, Prepared)
    assert isinstance(
        project_physiognomy_view_model(physiognomy.to_dict()["brief"]), PhysiognomyViewV1
    )


@pytest.mark.asyncio
async def test_real_runtime_projects_non_face_physiognomy_modes() -> None:
    """The native Runtime must preserve the declared non-face observation mode."""

    runtime = await _runtime()
    mode_rows = (
        ("palm", "life_line", "line_continuous", "anatomical_palm_v1"),
        ("posture", "shoulder_line", "level", "posture_observation_v1"),
        ("combined", "walking_gait", "steady", "posture_observation_v1"),
    )
    for mode, region, descriptor, taxonomy in mode_rows:
        adapter = PhysiognomyMediaAdapter(store=InMemoryPrivateMediaStore())
        asset = adapter.ingest(
            owner_kind="guest",
            owner_id=uuid4(),
            content_type="image/jpeg",
            filename=f"synthetic-{mode}.jpg",
            payload=b"\xff\xd8\xff\xe0synthetic",
            width=1200,
            height=1600,
            consent=True,
            mode=mode,  # type: ignore[arg-type]
            now=datetime(2026, 8, 14, 2, 0, tzinfo=UTC),
        )
        runtime_input = adapter.build_runtime_input(
            asset_id=asset.asset_id,
            subject_ref="sid-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            observations=(
                {
                    "region": region,
                    "feature_kind": "visible_morphology",
                    "descriptor": descriptor,
                    "visibility": "full",
                },
            ),
            dimension_ids=("state",),
        )
        result = await runtime.execute(
            runtime_input.to_prepare(
                query=f"验证相法 {mode} 结构化观察核心",
                action="physiognomy_preview",
            )
        )
        assert isinstance(result, Prepared), mode
        view_model = project_physiognomy_view_model(result.to_dict()["brief"])
        assert isinstance(view_model, PhysiognomyViewV1), mode
        assert view_model.mode == mode, mode
        assert view_model.observations[0].region_id == region, mode
        assert taxonomy in runtime_input.physiognomy_spec["requested_targets"][0]["taxonomy"]  # type: ignore[index]


@pytest.mark.asyncio
async def test_real_runtime_projects_bazi_year_layer() -> None:
    runtime = await _runtime()

    result = await runtime.execute(
        compile_bazi_year_prepare(
            action="bazi_year_preview",
            query="验证指定年份流年事实",
            profile=SYNTHETIC_PROFILE,
            year=2026,
            dimension_ids=("career",),
        )
    )

    assert isinstance(result, Prepared)
    view_model = project_bazi_view_model(result.to_dict()["brief"])
    assert isinstance(view_model, BaziChartV1)
    assert view_model.time_layers[1].available is True
    assert view_model.core_facts is not None
    assert view_model.core_facts.year_layers is not None
    assert [item.year for item in view_model.core_facts.year_layers] == [2026]
    assert view_model.core_facts.month_layers is None
    assert view_model.core_facts.day_layers is None


@pytest.mark.asyncio
async def test_real_runtime_projects_ziwei_and_qizheng_year_layers() -> None:
    runtime = await _runtime()

    ziwei = await runtime.execute(
        compile_ziwei_year_prepare(
            action="ziwei_year_preview",
            query="验证紫微指定年份事实",
            profile=SYNTHETIC_PROFILE,
            year=2026,
            dimension_ids=("career",),
        )
    )
    assert isinstance(ziwei, Prepared)
    ziwei_view = project_ziwei_view_model(ziwei.to_dict()["brief"])
    assert isinstance(ziwei_view, ZiweiChartV1)
    assert ziwei_view.time_layers[1].available is True
    assert ziwei_view.core_facts is not None
    assert ziwei_view.core_facts.chart_convention is not None
    assert ziwei_view.core_facts.active_major_limit is not None
    assert ziwei_view.core_facts.annual_layers is not None
    assert [item.year for item in ziwei_view.core_facts.annual_layers] == [2026]
    assert ziwei_view.core_facts.source_conditioned_patterns
    assert {
        pattern.local_rule_id
        for pattern in ziwei_view.core_facts.source_conditioned_patterns
    } >= {"TR-01", "ZW-M01"}
    assert all(
        pattern.status == "predicate_matched_not_verdict"
        for pattern in ziwei_view.core_facts.source_conditioned_patterns
    )

    qizheng = await runtime.execute(
        compile_qizheng_year_prepare(
            action="qizheng_year_preview",
            query="验证七政指定年份事实",
            profile=SYNTHETIC_PROFILE,
            year=2026,
            dimension_ids=("career",),
        )
    )
    assert isinstance(qizheng, Prepared)
    qizheng_view = project_qizheng_view_model(qizheng.to_dict()["brief"])
    assert isinstance(qizheng_view, QizhengChartV1)
    assert qizheng_view.time_layers[1].available is True
    assert qizheng_view.core_facts is not None
    assert qizheng_view.core_facts.ephemeris is not None
    assert qizheng_view.core_facts.conventions is not None
    assert qizheng_view.core_facts.annual_transformations is not None
    assert [item.year for item in qizheng_view.core_facts.annual_transformations] == [2026]
    assert qizheng_view.core_facts.source_conditioned_patterns
    assert {
        pattern.local_rule_id
        for pattern in qizheng_view.core_facts.source_conditioned_patterns
    } >= {"GR-01-01", "XR-M01", "XXDC-M01"}
    assert all(
        pattern.status == "predicate_matched_not_verdict"
        for pattern in qizheng_view.core_facts.source_conditioned_patterns
    )


@pytest.mark.asyncio
async def test_real_runtime_projects_ziwei_major_limit_boundary_segments() -> None:
    runtime = await _runtime()
    boundary_profile = ConfirmedProfileVersion(
        subject_ref="profile-version:public-core-major-limit-boundary",
        birth_datetime="1990-06-15T10:00:00+08:00",
        birth_datetime_or_four_pillars="1990-06-15T10:00:00+08:00",
        timezone=SYNTHETIC_PROFILE.timezone,
        location=SYNTHETIC_PROFILE.location,
        gender=SYNTHETIC_PROFILE.gender,
        time_basis_policy=SYNTHETIC_PROFILE.time_basis_policy,
        zi_hour_policy=SYNTHETIC_PROFILE.zi_hour_policy,
        longitude=SYNTHETIC_PROFILE.longitude,
        latitude=SYNTHETIC_PROFILE.latitude,
        coordinate_source="synthetic-boundary-fixture",
    )

    ziwei = await runtime.execute(
        compile_ziwei_year_prepare(
            action="ziwei_year_preview",
            query="验证紫微跨大限边界事实",
            profile=boundary_profile,
            year=2025,
            dimension_ids=("career",),
        )
    )

    assert isinstance(ziwei, Prepared)
    brief = ziwei.to_dict()["brief"]
    raw_segments = next(
        item["value"]
        for item in brief["facts"]
        if isinstance(item, dict)
        and str(item.get("ref", "")).endswith("/active_major_limit_segments")
    )
    view = project_ziwei_view_model(brief)
    assert isinstance(view, ZiweiChartV1)
    assert view.core_facts is not None
    assert view.core_facts.active_major_limit_segments is not None
    projected_segments = view.model_dump(mode="json")["core_facts"][
        "active_major_limit_segments"
    ]
    expected_segments = [
        {
            key: segment[key]
            for key in ("start_inclusive", "end_exclusive", "major_limit")
        }
        for segment in raw_segments
    ]
    assert projected_segments == expected_segments
    assert len(projected_segments) >= 2
    assert projected_segments[0]["end_exclusive"] == (
        projected_segments[1]["start_inclusive"]
    )
    assert projected_segments[0]["major_limit"] != (
        projected_segments[1]["major_limit"]
    )


@pytest.mark.asyncio
async def test_real_runtime_projects_declared_month_and_day_layers() -> None:
    runtime = await _runtime()

    bazi_month = await runtime.execute(
        compile_bazi_month_prepare(
            action="bazi_month_preview",
            query="验证八字指定月份事实",
            profile=SYNTHETIC_PROFILE,
            month="2026-08",
            dimension_ids=("career",),
        )
    )
    assert isinstance(bazi_month, Prepared)
    bazi_month_view = project_bazi_view_model(bazi_month.to_dict()["brief"])
    assert isinstance(bazi_month_view, BaziChartV1)
    assert bazi_month_view.core_facts is not None
    assert bazi_month_view.core_facts.month_layers is not None
    assert [item.period for item in bazi_month_view.core_facts.month_layers] == ["2026-08"]
    assert bazi_month_view.core_facts.year_layers is None
    assert bazi_month_view.core_facts.day_layers is None
    assert next(
        layer for layer in bazi_month_view.time_layers if layer.layer_id == "month"
    ).available

    bazi_day = await runtime.execute(
        compile_bazi_day_prepare(
            action="bazi_day_preview",
            query="验证八字指定日期事实",
            profile=SYNTHETIC_PROFILE,
            target_date=date(2026, 8, 15),
            dimension_ids=("career",),
        )
    )
    assert isinstance(bazi_day, Prepared)
    bazi_day_view = project_bazi_view_model(bazi_day.to_dict()["brief"])
    assert isinstance(bazi_day_view, BaziChartV1)
    assert bazi_day_view.core_facts is not None
    assert bazi_day_view.core_facts.day_layers is not None
    assert [item.period for item in bazi_day_view.core_facts.day_layers] == ["2026-08-15"]
    assert bazi_day_view.core_facts.year_layers is None
    assert bazi_day_view.core_facts.month_layers is None
    assert next(layer for layer in bazi_day_view.time_layers if layer.layer_id == "day").available

    ziwei_month = await runtime.execute(
        compile_ziwei_month_prepare(
            action="ziwei_month_preview",
            query="验证紫微指定月份事实",
            profile=SYNTHETIC_PROFILE,
            month="2026-08",
            dimension_ids=("career",),
        )
    )
    assert isinstance(ziwei_month, Prepared)
    ziwei_month_view = project_ziwei_view_model(ziwei_month.to_dict()["brief"])
    assert isinstance(ziwei_month_view, ZiweiChartV1)
    assert ziwei_month_view.core_facts is not None
    assert ziwei_month_view.core_facts.monthly_layers is not None
    assert [
        (item.year, item.month)
        for item in ziwei_month_view.core_facts.monthly_layers
    ] == [(2026, 8)]
    assert next(
        layer for layer in ziwei_month_view.time_layers if layer.layer_id == "month"
    ).available

    qizheng_month = await runtime.execute(
        compile_qizheng_month_prepare(
            action="qizheng_month_preview",
            query="验证七政指定月份事实",
            profile=SYNTHETIC_PROFILE,
            month="2026-08",
            dimension_ids=("career",),
        )
    )
    assert isinstance(qizheng_month, Prepared)
    qizheng_month_view = project_qizheng_view_model(qizheng_month.to_dict()["brief"])
    assert isinstance(qizheng_month_view, QizhengChartV1)
    assert qizheng_month_view.core_facts is not None
    assert qizheng_month_view.core_facts.requested_limit_layers is not None
    assert next(
        layer
        for layer in qizheng_month_view.time_layers
        if layer.layer_id == "month"
    ).available

    qizheng_day = await runtime.execute(
        compile_qizheng_day_prepare(
            action="qizheng_day_preview",
            query="验证七政指定日期事实",
            profile=SYNTHETIC_PROFILE,
            target_date=date(2026, 8, 15),
            dimension_ids=("career",),
        )
    )
    assert isinstance(qizheng_day, Prepared)
    qizheng_day_view = project_qizheng_view_model(qizheng_day.to_dict()["brief"])
    assert isinstance(qizheng_day_view, QizhengChartV1)
    assert qizheng_day_view.core_facts is not None
    assert qizheng_day_view.core_facts.requested_limit_layers is not None
    assert next(
        layer for layer in qizheng_day_view.time_layers if layer.layer_id == "day"
    ).available


@pytest.mark.asyncio
async def test_real_runtime_projects_fortune_fact_panel_without_chart_claim() -> None:
    runtime = await _runtime()
    fortune = await runtime.execute(
        compile_fortune_prepare(
            action="today",
            query="验证日运事实面板",
            profile=SYNTHETIC_PROFILE,
            server_reference_datetime=datetime.fromisoformat(
                "2026-08-14T02:00:00+00:00"
            ),
            dimension_ids=("career",),
        )
    )

    assert isinstance(fortune, Prepared)
    brief = fortune.to_dict()["brief"]
    assert brief["request_view"]["capability_ids"] == ["fortune"]
    panel = project_public_fact_panel(brief)
    assert panel is not None
    assert panel["request_view"]["capability_ids"] == ["fortune"]
    view_model = project_fortune_view_model(brief)
    assert isinstance(view_model, FortuneFactsViewV1)
    assert view_model.period_markers
    assert view_model.period_markers[0].specific_event_policy
    assert view_model.calendar_normalization.time_basis.policy == (
        "local_apparent_solar-v1"
    )
    assert view_model.calendar_normalization.true_solar_time.status == (
        "apparent_solar_applied"
    )
    public_payload = json.dumps(
        {"panel": panel, "view_model": view_model.model_dump(mode="json")},
        ensure_ascii=False,
        sort_keys=True,
    )
    assert SYNTHETIC_PROFILE.birth_datetime not in public_payload
    assert SYNTHETIC_PROFILE.location not in public_payload
    assert str(SYNTHETIC_PROFILE.longitude) not in public_payload
    assert str(SYNTHETIC_PROFILE.latitude) not in public_payload
    assert "/input/" not in public_payload

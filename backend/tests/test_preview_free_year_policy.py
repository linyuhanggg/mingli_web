from __future__ import annotations

from datetime import UTC, datetime

from app.readings.request_compiler import ConfirmedProfileVersion
from app.readings.service import ReadingService, _profile_free_preview_year


def _profile(*, timezone: str = "Asia/Shanghai") -> ConfirmedProfileVersion:
    return ConfirmedProfileVersion(
        subject_ref="profile-version:ming-83",
        birth_datetime="1994-04-30T05:55:00+08:00",
        birth_datetime_or_four_pillars="1994-04-30T05:55:00+08:00",
        timezone=timezone,
        location="北京市朝阳区",
        gender="female",
        time_basis_policy="civil",
        zi_hour_policy="midnight",
        longitude=116.4074,
        latitude=39.9042,
        coordinate_source="synthetic-test",
    )


def test_free_preview_year_uses_the_profile_civil_timezone() -> None:
    instant = datetime(2031, 12, 31, 16, 30, tzinfo=UTC)

    assert _profile_free_preview_year(_profile(), reference=instant) == 2032
    assert (
        _profile_free_preview_year(
            _profile(timezone="America/Los_Angeles"),
            reference=instant,
        )
        == 2031
    )


def test_default_bazi_preview_requests_the_server_selected_free_year() -> None:
    prepare = ReadingService._compile_profile_preview_prepare(
        _profile(),
        query="查看免费盘与流年",
        dimension_ids=("career",),
        target_year=None,
        target_month=None,
        target_date=None,
        free_preview_year=2032,
    )

    assert prepare.intent["horizon"] == {
        "kind_id": "year",
        "start": "2032",
        "end": "2032",
    }
    assert prepare.intent["capability_id"] == "bazi"


def test_default_ziwei_preview_requests_the_server_selected_free_year() -> None:
    prepare = ReadingService._compile_ziwei_preview_prepare(
        _profile(),
        query="查看免费盘与流年",
        dimension_ids=("career",),
        target_year=None,
        target_month=None,
        free_preview_year=2032,
    )

    assert prepare.intent["horizon"] == {
        "kind_id": "year",
        "start": "2032",
        "end": "2032",
    }
    assert prepare.intent["capability_id"] == "ziwei"


def test_explicit_year_stays_authoritative_over_the_free_preview_policy() -> None:
    bazi = ReadingService._compile_profile_preview_prepare(
        _profile(),
        query="查看指定流年",
        dimension_ids=("career",),
        target_year=2028,
        target_month=None,
        target_date=None,
        free_preview_year=2032,
    )
    ziwei = ReadingService._compile_ziwei_preview_prepare(
        _profile(),
        query="查看指定流年",
        dimension_ids=("career",),
        target_year=2028,
        target_month=None,
        free_preview_year=2032,
    )

    assert bazi.intent["horizon"]["start"] == "2028"
    assert ziwei.intent["horizon"]["start"] == "2028"

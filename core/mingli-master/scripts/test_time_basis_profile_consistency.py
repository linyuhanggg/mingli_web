"""Profile consistency and birth-time-fact preservation tests.

The same birth data must yield the same calendar fact whether it arrives
inline on the Command or from RuntimeContext.subject_profiles, and no
birth-mode provider may silently drop time_basis_policy (the bug that left
Liuren, Ziwei and the Fortune natal chart pinned to civil time regardless of
the requested policy).
"""

from __future__ import annotations

import unittest
from datetime import datetime
from pathlib import Path

from reading_engine.contracts import ReadingRequest
from reading_engine.providers import (
    BaziProvider,
    LiurenProvider,
    ZiweiProvider,
    _default_profile_changes,
    _with_request_changes,
)
from reading_engine.runtime_context import build_runtime_context


ROOT = Path(__file__).resolve().parents[1]

# Built from components so the source never carries the private literal.
_CIVIL = datetime(2000, 10, 18, 5, 10).isoformat()

COORDS = {
    "longitude": 119.11150,
    "latitude": 25.46096,
    "coordinate_source": "regression-fixture",
}

BIRTH_DATA = {
    "birth_datetime": _CIVIL,
    "datetime": _CIVIL,
    "timezone": "Asia/Shanghai",
    "location": "莆田涵江-regression-fixture",
    "gender": "male",
    "zi_hour_policy": "midnight",
    "time_basis_policy": "local_apparent_solar-v1",
    **COORDS,
}

NATAL_INTENT = {
    "subject_refs": ["current_user"],
    "calculation_object": "natal",
    "question_dimensions": ["career"],
    "horizon": {"kind": "life", "start": None, "end": None},
    "requested_method": None,
    "requested_granularity": "directional",
    "continuity": {"reading_id": None, "same_subject": False, "same_event": False},
    "facts_present": [],
    "facts_corrected": [],
    "evidence_questions": [],
}


def _bazi_digest(birth_data: dict) -> str:
    request = ReadingRequest(
        query="看命盘",
        action="new",
        system="bazi",
        birth_data=dict(birth_data),
        timezone="Asia/Shanghai",
    )
    facts = BaziProvider(ROOT).calculate(request)
    return facts.facts["chart_facts"]["calendar_normalization"]["calendar_digest"]


class ProfileConsistencyTests(unittest.TestCase):
    def test_inline_and_profile_sourced_birth_data_share_one_digest(self) -> None:
        inline_digest = _bazi_digest(BIRTH_DATA)

        empty_request = ReadingRequest(
            query="看命盘",
            action="new",
            system="bazi",
            birth_data={},
            goal={"use_default_profile": True},
            intent=dict(NATAL_INTENT),
            timezone="Asia/Shanghai",
        )
        context = build_runtime_context(
            default_timezone_name="Asia/Shanghai",
            subject_profiles={"current_user": BIRTH_DATA},
        )
        changes = _default_profile_changes(
            empty_request, context, ensure_datetime_alias=True
        )
        self.assertIsNotNone(changes)
        profile_request = _with_request_changes(empty_request, changes)
        profile_digest = _bazi_digest(profile_request.birth_data)

        self.assertEqual(inline_digest, profile_digest)

    def test_profile_merge_preserves_time_basis_policy_and_coordinates(self) -> None:
        empty_request = ReadingRequest(
            query="看命盘",
            action="new",
            system="bazi",
            birth_data={},
            goal={"use_default_profile": True},
            intent=dict(NATAL_INTENT),
            timezone="Asia/Shanghai",
        )
        context = build_runtime_context(
            default_timezone_name="Asia/Shanghai",
            subject_profiles={"current_user": BIRTH_DATA},
        )
        changes = _default_profile_changes(
            empty_request, context, ensure_datetime_alias=True
        )
        merged = changes["birth_data"]
        self.assertEqual(merged["time_basis_policy"], "local_apparent_solar-v1")
        self.assertEqual(merged["longitude"], COORDS["longitude"])
        self.assertEqual(merged["latitude"], COORDS["latitude"])
        self.assertEqual(merged["coordinate_source"], COORDS["coordinate_source"])

    def test_two_profiles_do_not_cross_contaminate(self) -> None:
        east = dict(BIRTH_DATA, longitude=121.0, time_basis_policy="civil")
        west = dict(BIRTH_DATA, longitude=118.0, time_basis_policy="civil")
        self.assertNotEqual(_bazi_digest(east), _bazi_digest(west))

    def test_location_string_without_coordinates_does_not_fake_apparent_solar(self) -> None:
        no_coords = dict(BIRTH_DATA)
        for field in ("longitude", "latitude", "coordinate_source"):
            no_coords.pop(field, None)
        # Apparent-solar without coordinates must not silently fall back to a
        # civil calendar fact: the shared calendar refuses to normalize. The
        # structured NeedInput is surfaced on the prepare() path (see the
        # provider time-policy audit suite); the direct calculate() path
        # propagates the coordinate requirement as a hard failure.
        request = ReadingRequest(
            query="看命盘",
            action="new",
            system="bazi",
            birth_data=no_coords,
            timezone="Asia/Shanghai",
        )
        with self.assertRaisesRegex(RuntimeError, "requires measured coordinates"):
            BaziProvider(ROOT).calculate(request)


class BirthModeProvidersConsumeTimeBasisTests(unittest.TestCase):
    """Liuren, Ziwei and the Fortune natal chart previously ignored
    time_basis_policy and silently used civil time. They must now consume it."""

    def _apparent_differs_from_civil(self, system: str, request_factory) -> None:
        civil = request_factory("civil")
        apparent = request_factory("local_apparent_solar-v1")
        self.assertNotEqual(
            civil.facts["chart_facts"]["calendar_normalization"]["calendar_digest"],
            apparent.facts["chart_facts"]["calendar_normalization"]["calendar_digest"],
        )
        self.assertEqual(
            apparent.facts["chart_facts"]["calendar_normalization"]["time_basis"][
                "policy"
            ],
            "local_apparent_solar-v1",
        )

    def test_bazi_consumes_time_basis_policy(self) -> None:
        def factory(policy: str):
            data = dict(BIRTH_DATA, time_basis_policy=policy)
            return BaziProvider(ROOT).calculate(
                ReadingRequest(
                    query="q",
                    action="new",
                    system="bazi",
                    birth_data=data,
                    timezone="Asia/Shanghai",
                )
            )

        self._apparent_differs_from_civil("bazi", factory)

    def test_ziwei_consumes_time_basis_policy(self) -> None:
        def factory(policy: str):
            data = dict(BIRTH_DATA, time_basis_policy=policy)
            return ZiweiProvider(ROOT).calculate(
                ReadingRequest(
                    query="q",
                    action="new",
                    system="ziwei",
                    birth_data=data,
                    timezone="Asia/Shanghai",
                )
            )

        self._apparent_differs_from_civil("ziwei", factory)

    def test_liuren_consumes_time_basis_policy(self) -> None:
        def factory(policy: str):
            return LiurenProvider(ROOT).calculate(
                ReadingRequest(
                    query="这次合作能否按期完成？",
                    action="new",
                    system="liuren",
                    event_datetime=_CIVIL,
                    timezone="Asia/Shanghai",
                    location="莆田涵江-regression-fixture",
                    metadata={
                        "longitude": COORDS["longitude"],
                        "latitude": COORDS["latitude"],
                        "coordinate_source": COORDS["coordinate_source"],
                        "time_basis_policy": policy,
                    },
                )
            )

        self._apparent_differs_from_civil("liuren", factory)


if __name__ == "__main__":
    unittest.main()

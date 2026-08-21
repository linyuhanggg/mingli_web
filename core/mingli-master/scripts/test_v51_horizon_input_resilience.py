"""Horizon boundary shapes a real host actually submits, through the public
interface.

Every case here drives ``ReadingInterface.execute`` only. A host model that
picked the right capability but expressed the period as an ISO datetime --
the common shape when a host turns "this week" into a concrete civil day --
must reach a deterministic ``Prepared`` on the FIRST prepare, without the
host having to clear the horizon and call again.

A single anchor may come from either boundary: a host that submitted only
``end`` must bind that boundary, never fall back to the reference day.  An
explicitly wrong range must still stop: widening, truncating or reordering
it silently would answer a question the user never asked.  Only the two
declared spellings are accepted -- a strict ``YYYY-MM-DD`` civil date and a
full ISO-8601 datetime -- so compact dates, ISO week-dates and partial month
tokens are refused instead of being silently guessed.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from reading_engine.interface import ReadingInterface
from reading_engine.interface_contracts import (
    Accepted,
    Complete,
    HorizonSelection,
    IntentSelection,
    Prepare,
    Prepared,
    Stopped,
)
from reading_engine.runtime_context import build_runtime_context

ROOT = Path(__file__).resolve().parents[1]

# One fixed reference instant so every expectation below is an exact date.
# 2026-08-03 is a Monday in Asia/Shanghai, so the containing week is
# 2026-08-03 .. 2026-08-09.
REFERENCE = "2026-08-03T10:00:00+08:00"
WEEK = (
    "2026-08-03",
    "2026-08-04",
    "2026-08-05",
    "2026-08-06",
    "2026-08-07",
    "2026-08-08",
    "2026-08-09",
)

BUSINESS_TIMEZONE = "Asia/Shanghai"


def _profile() -> dict:
    return {
        "birth_datetime": "1994-04-30T05:55:00",
        "timezone": BUSINESS_TIMEZONE,
        "location": "福建省福州市",
        "gender": "female",
    }


class _HorizonCaseMixin(unittest.TestCase):
    def _interface(self, **context_values) -> ReadingInterface:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        defaults = {
            "now_iso": REFERENCE,
            "default_timezone_name": BUSINESS_TIMEZONE,
            "subject_profiles": {"current_user": _profile()},
        }
        defaults.update(context_values)
        return ReadingInterface(
            skill_root=ROOT,
            store_root=Path(tmp.name),
            runtime_context=build_runtime_context(**defaults),
        )

    @staticmethod
    def _command(
        kind_id: str,
        start: str | None = None,
        end: str | None = None,
        *,
        query: str = "算一下这周运势",
        facts: dict | None = None,
    ) -> Prepare:
        return Prepare(
            query=query,
            intent=IntentSelection(
                subject_refs=("current_user",),
                object_id="near_time_personal",
                dimension_ids=(),
                horizon=HorizonSelection(kind_id=kind_id, start=start, end=end),
                capability_id="fortune",
            ),
            facts=facts if facts is not None else {},
        )

    def _prepared(
        self,
        kind_id: str,
        start: str | None = None,
        end: str | None = None,
        *,
        interface: ReadingInterface | None = None,
        **command_values,
    ) -> tuple[ReadingInterface, Prepared]:
        """Assert exactly one prepare call reaches a Prepared."""

        interface = interface or self._interface()
        result = interface.execute(
            self._command(kind_id, start, end, **command_values)
        )
        self.assertIsInstance(result, Prepared, result)
        return interface, result

    def _assert_effective_horizon(
        self, prepared: Prepared, kind_id: str, start: str, end: str
    ) -> None:
        request_view = prepared.brief.request_view
        self.assertIsNotNone(request_view, prepared.brief.to_dict())
        assert request_view is not None
        self.assertEqual(
            request_view.horizon,
            HorizonSelection(kind_id=kind_id, start=start, end=end),
        )

    def _assert_calculated_days(
        self, prepared: Prepared, expected: tuple[str, ...]
    ) -> None:
        """The published period must match what was actually calculated."""

        periods = [
            fact.value
            for fact in prepared.brief.facts
            if fact.ref.endswith("/available_periods")
        ]
        self.assertEqual(periods, [list(expected)], prepared.brief.to_dict())

    def _assert_target_day(self, prepared: Prepared, expected: str) -> None:
        target_day = [
            fact.value
            for fact in prepared.brief.facts
            if fact.ref.endswith("/target_day")
        ]
        self.assertEqual(target_day, [expected], prepared.brief.to_dict())

    def _assert_stopped(
        self, kind_id: str, start: str | None, end: str | None
    ) -> Stopped:
        interface = self._interface()
        result = interface.execute(self._command(kind_id, start, end))
        self.assertIsInstance(result, Stopped, result)
        assert isinstance(result, Stopped)
        self.assertTrue(result.public_copy.strip(), result)
        return result


class DayBoundaryShapeTests(_HorizonCaseMixin):
    """A day request resolves the civil day the host actually meant."""

    def test_start_only_civil_date_anchors_that_day(self) -> None:
        _, prepared = self._prepared("day", "2026-08-05", None)
        self._assert_effective_horizon(prepared, "day", "2026-08-05", "2026-08-05")
        self._assert_calculated_days(prepared, ("2026-08-05",))
        self._assert_target_day(prepared, "2026-08-05")

    def test_end_only_civil_date_anchors_that_day(self) -> None:
        """The host named only ``end``; it must bind, not the reference day."""

        _, prepared = self._prepared("day", None, "2026-08-05")
        self._assert_effective_horizon(prepared, "day", "2026-08-05", "2026-08-05")
        self._assert_calculated_days(prepared, ("2026-08-05",))
        self._assert_target_day(prepared, "2026-08-05")

    def test_start_only_aware_datetime_anchors_that_day(self) -> None:
        _, prepared = self._prepared("day", "2026-08-05T14:00:00+08:00", None)
        self._assert_effective_horizon(prepared, "day", "2026-08-05", "2026-08-05")
        self._assert_calculated_days(prepared, ("2026-08-05",))
        self._assert_target_day(prepared, "2026-08-05")

    def test_end_only_aware_datetime_anchors_that_day(self) -> None:
        """The P1 shape: reference 08-03, only end 08-05 14:00+08:00.

        The cast day must be 2026-08-05 and the public horizon must say so;
        nothing may silently keep computing 2026-08-03 while the request view
        still points at 08-05.
        """

        _, prepared = self._prepared("day", None, "2026-08-05T14:00:00+08:00")
        self._assert_effective_horizon(prepared, "day", "2026-08-05", "2026-08-05")
        self._assert_calculated_days(prepared, ("2026-08-05",))
        self._assert_target_day(prepared, "2026-08-05")

    def test_same_civil_day_datetimes_resolve_to_that_day(self) -> None:
        _, prepared = self._prepared(
            "day",
            "2026-08-03T08:00:00+08:00",
            "2026-08-03T22:00:00+08:00",
            query="今天运势怎么样",
        )
        self._assert_effective_horizon(prepared, "day", WEEK[0], WEEK[0])
        self._assert_calculated_days(prepared, (WEEK[0],))
        self._assert_target_day(prepared, WEEK[0])

    def test_utc_datetime_converts_into_the_business_timezone(self) -> None:
        """2026-08-02T17:00Z is 2026-08-03 01:00 in the business zone."""

        _, prepared = self._prepared(
            "day",
            "2026-08-02T17:00:00Z",
            "2026-08-02T17:00:00Z",
            query="今天运势怎么样",
        )
        self._assert_effective_horizon(prepared, "day", "2026-08-03", "2026-08-03")
        self._assert_calculated_days(prepared, ("2026-08-03",))
        self._assert_target_day(prepared, "2026-08-03")

    def test_offset_datetime_converts_into_the_business_timezone(self) -> None:
        """2026-08-03T02:00+02:00 is 2026-08-03 08:00 in the business zone."""

        _, prepared = self._prepared(
            "day",
            "2026-08-03T02:00:00+02:00",
            None,
            query="今天运势怎么样",
        )
        self._assert_effective_horizon(prepared, "day", "2026-08-03", "2026-08-03")
        self._assert_calculated_days(prepared, ("2026-08-03",))
        self._assert_target_day(prepared, "2026-08-03")

    def test_naive_datetime_is_read_in_the_business_timezone(self) -> None:
        _, prepared = self._prepared(
            "day",
            "2026-08-03T09:30:00",
            "2026-08-03T09:30:00",
            query="今天运势怎么样",
        )
        self._assert_effective_horizon(prepared, "day", "2026-08-03", "2026-08-03")
        self._assert_calculated_days(prepared, ("2026-08-03",))
        self._assert_target_day(prepared, "2026-08-03")

    def test_utc_datetime_late_enough_to_cross_into_the_next_civil_day(
        self,
    ) -> None:
        """20:00Z on 2026-08-03 is already 2026-08-04 in the business zone.

        Truncating the string instead of converting the instant would answer
        for the wrong civil day.
        """

        _, prepared = self._prepared(
            "day",
            "2026-08-03T20:00:00Z",
            "2026-08-03T20:00:00Z",
            query="这一天运势怎么样",
        )
        self._assert_effective_horizon(prepared, "day", "2026-08-04", "2026-08-04")
        self._assert_calculated_days(prepared, ("2026-08-04",))
        self._assert_target_day(prepared, "2026-08-04")

    def test_plain_civil_date_is_taken_as_that_civil_date(self) -> None:
        _, prepared = self._prepared(
            "day", "2026-08-04", "2026-08-04", query="这一天运势怎么样"
        )
        self._assert_effective_horizon(prepared, "day", "2026-08-04", "2026-08-04")
        self._assert_calculated_days(prepared, ("2026-08-04",))
        self._assert_target_day(prepared, "2026-08-04")

    def test_two_distinct_civil_days_are_refused_for_a_day_request(self) -> None:
        self._assert_stopped(
            "day",
            "2026-08-03T08:00:00+08:00",
            "2026-08-04T08:00:00+08:00",
        )


class WeekBoundaryShapeTests(_HorizonCaseMixin):
    """A week request survives every boundary shape a host commonly submits."""

    def test_empty_boundaries_bind_the_reference_week(self) -> None:
        _, prepared = self._prepared("week")
        self._assert_effective_horizon(prepared, "week", WEEK[0], WEEK[-1])
        self._assert_calculated_days(prepared, WEEK)

    def test_start_only_civil_date_expands_to_its_week(self) -> None:
        _, prepared = self._prepared("week", "2026-08-06", None)
        self._assert_effective_horizon(prepared, "week", WEEK[0], WEEK[-1])
        self._assert_calculated_days(prepared, WEEK)

    def test_end_only_civil_date_expands_to_its_week(self) -> None:
        """A week anchor supplied only through ``end`` binds its own week."""

        _, prepared = self._prepared("week", None, "2026-08-05")
        self._assert_effective_horizon(prepared, "week", WEEK[0], WEEK[-1])
        self._assert_calculated_days(prepared, WEEK)

    def test_start_only_aware_datetime_expands_to_its_week(self) -> None:
        _, prepared = self._prepared("week", "2026-08-05T14:00:00+08:00", None)
        self._assert_effective_horizon(prepared, "week", WEEK[0], WEEK[-1])
        self._assert_calculated_days(prepared, WEEK)

    def test_end_only_aware_datetime_expands_to_its_week(self) -> None:
        """The P1 week shape: reference 08-03, only end 08-05 14:00+08:00.

        This must no longer surface as ``Stopped.error``: the single anchor
        expands to the containing week 08-03 .. 08-09 on the first prepare.
        """

        _, prepared = self._prepared("week", None, "2026-08-05T14:00:00+08:00")
        self._assert_effective_horizon(prepared, "week", WEEK[0], WEEK[-1])
        self._assert_calculated_days(prepared, WEEK)

    def test_plain_civil_dates_keep_their_exact_week(self) -> None:
        _, prepared = self._prepared("week", WEEK[0], WEEK[-1])
        self._assert_effective_horizon(prepared, "week", WEEK[0], WEEK[-1])
        self._assert_calculated_days(prepared, WEEK)

    def test_one_civil_day_expressed_as_full_datetimes_expands_to_its_week(
        self,
    ) -> None:
        """The exact shape from the failing host transcript.

        The host bounded a week request with the 00:00:00/23:59:59 edges of a
        single civil day. That is a same-day anchor, not a one-day week: it
        must expand to the containing week on the first prepare.
        """

        _, prepared = self._prepared(
            "week",
            "2026-08-03T00:00:00+08:00",
            "2026-08-03T23:59:59+08:00",
        )
        self._assert_effective_horizon(prepared, "week", WEEK[0], WEEK[-1])
        self._assert_calculated_days(prepared, WEEK)

    def test_single_datetime_anchor_expands_to_its_week(self) -> None:
        _, prepared = self._prepared("week", "2026-08-05T14:00:00+08:00")
        self._assert_effective_horizon(prepared, "week", WEEK[0], WEEK[-1])
        self._assert_calculated_days(prepared, WEEK)

    def test_same_civil_day_anchor_is_not_read_as_a_one_day_week(self) -> None:
        _, prepared = self._prepared("week", "2026-08-05", "2026-08-05")
        self._assert_effective_horizon(prepared, "week", WEEK[0], WEEK[-1])
        self._assert_calculated_days(prepared, WEEK)

    def test_datetime_seven_day_range_is_accepted_as_given(self) -> None:
        _, prepared = self._prepared(
            "week",
            "2026-08-03T09:00:00+08:00",
            "2026-08-09T21:30:00+08:00",
        )
        self._assert_effective_horizon(prepared, "week", WEEK[0], WEEK[-1])
        self._assert_calculated_days(prepared, WEEK)

    def test_utc_end_anchor_crosses_into_the_business_day(self) -> None:
        """end-only with a Z suffix across the business-timezone date line.

        2026-08-02T20:00:00Z is 2026-08-03 04:00 in Asia/Shanghai, so the
        end anchor names 2026-08-03 and the containing week is 08-03..08-09.
        """

        _, prepared = self._prepared("week", None, "2026-08-02T20:00:00Z")
        self._assert_effective_horizon(prepared, "week", WEEK[0], WEEK[-1])
        self._assert_calculated_days(prepared, WEEK)

    def test_date_and_datetime_inputs_agree_on_the_same_effective_week(
        self,
    ) -> None:
        """Equivalent boundary spellings must not produce different weeks."""

        shapes = (
            (None, None),
            (WEEK[0], WEEK[-1]),
            ("2026-08-03T00:00:00+08:00", "2026-08-03T23:59:59+08:00"),
            ("2026-08-05T14:00:00+08:00", None),
            (None, "2026-08-05T14:00:00+08:00"),
            ("2026-08-05", "2026-08-05"),
            ("2026-08-02T17:00:00Z", None),
            (None, "2026-08-02T20:00:00Z"),
        )
        seen = []
        for start, end in shapes:
            with self.subTest(start=start, end=end):
                _, prepared = self._prepared("week", start, end)
                request_view = prepared.brief.request_view
                assert request_view is not None
                seen.append(request_view.horizon)
        self.assertEqual(
            seen,
            [
                HorizonSelection(kind_id="week", start=WEEK[0], end=WEEK[-1])
            ]
            * len(shapes),
        )


class StrictFormatRejectionTests(_HorizonCaseMixin):
    """Only the two declared spellings are boundaries; everything else stops.

    ``date.fromisoformat`` would also accept a compact date, an ISO week-date
    and basic datetime spellings, but the public contract only declares
    ``YYYY-MM-DD`` and a full ISO-8601 datetime.  Any other literal is
    refused with a non-empty ``Stopped``, never guessed.
    """

    def test_compact_date_is_refused(self) -> None:
        self._assert_stopped("week", "20260803", None)

    def test_compact_date_as_end_is_refused(self) -> None:
        self._assert_stopped("day", None, "20260803")

    def test_iso_week_date_is_refused(self) -> None:
        self._assert_stopped("week", "2026-W32-1", None)

    def test_iso_week_date_as_end_is_refused(self) -> None:
        self._assert_stopped("week", None, "2026-W32-1")

    def test_basic_datetime_is_refused(self) -> None:
        self._assert_stopped("week", "20260803T100000", None)

    def test_basic_datetime_as_end_is_refused(self) -> None:
        self._assert_stopped("day", None, "20260803T100000")

    def test_partial_month_text_is_refused(self) -> None:
        self._assert_stopped("week", "2026-08", None)

    def test_partial_month_as_end_is_refused(self) -> None:
        self._assert_stopped("day", None, "2026-08")

    def test_natural_language_boundary_is_refused(self) -> None:
        self._assert_stopped("week", "这周", None)

    def test_natural_language_end_is_refused(self) -> None:
        self._assert_stopped("day", None, "下周三")

    def test_refused_boundary_never_comes_back_as_prepared(self) -> None:
        for kind_id, start, end in (
            ("week", "20260803", None),
            ("week", "2026-W32-1", None),
            ("week", "20260803T100000", None),
            ("week", "2026-08", None),
            ("day", None, "20260803"),
        ):
            with self.subTest(kind_id=kind_id, start=start, end=end):
                interface = self._interface()
                result = interface.execute(self._command(kind_id, start, end))
                self.assertNotIsInstance(result, Prepared, result)

    def test_whitespace_padded_boundary_is_refused(self) -> None:
        """The full submitted string is validated, never trimmed first.

        A leading/trailing-space padded literal must not be silently repaired
        into the same civil day: the public contract declares the exact
        spelling, so the padded shape is refused with a non-empty Stopped.
        """

        shapes = (
            (" 2026-08-05", None),
            ("2026-08-05 ", None),
            (" 2026-08-05 ", None),
            (None, " 2026-08-05 "),
            (None, "2026-08-05 "),
            (" 2026-08-05T14:00:00+08:00 ", None),
        )
        for start, end in shapes:
            with self.subTest(start=start, end=end):
                self._assert_stopped("day", start, end)

    def test_whitespace_only_boundary_is_refused(self) -> None:
        self._assert_stopped("week", "   ", None)

    def test_space_separated_datetime_is_refused(self) -> None:
        """Only the ``T`` separator is declared; a space between date and
        time widens the input dialect and must stop."""

        for kind_id, start, end in (
            ("day", "2026-08-05 14:00:00+08:00", None),
            ("week", "2026-08-05 14:00:00+08:00", None),
            ("day", None, "2026-08-05 14:00:00Z"),
        ):
            with self.subTest(kind_id=kind_id, start=start, end=end):
                self._assert_stopped(kind_id, start, end)

    def test_provider_boundary_rejects_an_unknown_horizon_kind(self) -> None:
        from reading_engine.providers import _near_time_period_days

        with self.assertRaisesRegex(ValueError, "unsupported fortune horizon"):
            _near_time_period_days(
                "unknown-kind",
                "2026-08-05",
                None,
                timezone_name=BUSINESS_TIMEZONE,
                fallback_anchor=date(2026, 8, 5),
            )


class IllegalRangeTests(_HorizonCaseMixin):
    """An explicitly wrong range is refused, never quietly rewritten."""

    def test_explicit_three_day_week_range_is_refused(self) -> None:
        self._assert_stopped("week", "2026-08-03", "2026-08-05")

    def test_explicit_eight_day_week_range_is_refused(self) -> None:
        self._assert_stopped("week", "2026-08-03", "2026-08-10")

    def test_reversed_week_range_is_refused(self) -> None:
        self._assert_stopped("week", "2026-08-09", "2026-08-03")

    def test_two_distinct_days_spanning_a_partial_week_is_refused(self) -> None:
        self._assert_stopped(
            "week",
            "2026-08-03T00:00:00+08:00",
            "2026-08-05T23:59:59+08:00",
        )

    def test_refused_range_is_never_silently_widened_to_a_full_week(
        self,
    ) -> None:
        """A wrong range must not come back as a Prepared for another period."""

        for start, end in (
            ("2026-08-03", "2026-08-05"),
            ("2026-08-03", "2026-08-10"),
            ("2026-08-09", "2026-08-03"),
        ):
            with self.subTest(start=start, end=end):
                interface = self._interface()
                result = interface.execute(self._command("week", start, end))
                self.assertNotIsInstance(result, Prepared, result)


class NormalizedTurnLifecycleTests(_HorizonCaseMixin):
    """A normalized horizon still produces one ordinary committed turn."""

    def test_normalized_week_completes_into_accepted(self) -> None:
        interface, prepared = self._prepared(
            "week",
            "2026-08-03T00:00:00+08:00",
            "2026-08-03T23:59:59+08:00",
        )
        draft = "这一周的重点还是先把手上的事收拢，节奏比铺开更要紧。"
        accepted = interface.execute(
            Complete(state_token=prepared.state_token, public_copy=draft)
        )
        self.assertIsInstance(accepted, Accepted, accepted)
        assert isinstance(accepted, Accepted)
        self.assertEqual(accepted.public_copy, draft)
        self.assertTrue(accepted.public_copy.strip())

    def test_end_only_day_completes_into_accepted(self) -> None:
        interface, prepared = self._prepared("day", None, "2026-08-05T14:00:00+08:00")
        draft = "这一天的关键是把节奏缓下来，先把手上事情收尾。"
        accepted = interface.execute(
            Complete(state_token=prepared.state_token, public_copy=draft)
        )
        self.assertIsInstance(accepted, Accepted, accepted)
        assert isinstance(accepted, Accepted)
        self.assertEqual(accepted.public_copy, draft)
        self.assertTrue(accepted.public_copy.strip())

    def test_repeated_complete_on_one_token_replays_the_same_accepted(
        self,
    ) -> None:
        interface, prepared = self._prepared(
            "week",
            "2026-08-03T00:00:00+08:00",
            "2026-08-03T23:59:59+08:00",
        )
        first = interface.execute(
            Complete(state_token=prepared.state_token, public_copy="第一稿正文。")
        )
        self.assertIsInstance(first, Accepted, first)
        replay = interface.execute(
            Complete(state_token=prepared.state_token, public_copy="第二稿正文。")
        )
        self.assertIsInstance(replay, Accepted, replay)
        assert isinstance(first, Accepted) and isinstance(replay, Accepted)
        self.assertEqual(replay.public_copy, first.public_copy)

    def test_missing_birth_facts_still_need_input_on_the_same_capability(
        self,
    ) -> None:
        """Normalization must not become a reason to switch capability."""

        interface = self._interface(subject_profiles={})
        result = interface.execute(
            self._command(
                "week",
                "2026-08-03T00:00:00+08:00",
                "2026-08-03T23:59:59+08:00",
            )
        )
        self.assertIsInstance(result, Stopped, result)
        assert isinstance(result, Stopped)
        self.assertEqual(result.reason, "need_input")
        self.assertTrue(result.public_copy.strip())
        self.assertIsNotNone(result.input_request)
        assert result.input_request is not None
        asked = {
            field.id
            for requirement in result.input_request.requirements
            for field in requirement.any_of
        }
        self.assertTrue(asked)
        # The capability that was asked for is the one that stays bound.
        self.assertTrue(
            asked
            <= {
                "birth_datetime",
                "timezone",
                "location",
                "gender",
                "reference_datetime",
            },
            asked,
        )

    def test_normalized_brief_stays_closed_against_ambient_memory(self) -> None:
        import os
        from unittest import mock

        clean_interface, clean = self._prepared(
            "week",
            "2026-08-03T00:00:00+08:00",
            "2026-08-03T23:59:59+08:00",
        )
        del clean_interface
        polluted_environment = {
            **os.environ,
            "HOST_AMBIENT_MEMORY": "订单 回款 对账 催款 报价 供应商项目",
        }
        with mock.patch.dict(os.environ, polluted_environment, clear=True):
            _, polluted = self._prepared(
                "week",
                "2026-08-03T00:00:00+08:00",
                "2026-08-03T23:59:59+08:00",
            )
        rendered = json.dumps(polluted.brief.to_dict(), ensure_ascii=False)
        for leaked in ("订单", "回款", "对账", "催款", "报价", "供应商"):
            self.assertNotIn(leaked, rendered)
        self.assertEqual(
            json.dumps(clean.brief.to_dict(), ensure_ascii=False, sort_keys=True),
            json.dumps(
                polluted.brief.to_dict(), ensure_ascii=False, sort_keys=True
            ),
        )

    def test_every_terminal_result_carries_public_text(self) -> None:
        cases = (
            ("week", "2026-08-03T00:00:00+08:00", "2026-08-03T23:59:59+08:00"),
            ("week", "2026-08-03", "2026-08-05"),
            ("week", "2026-08-09", "2026-08-03"),
            ("week", "这周", None),
            ("week", "20260803", None),
            ("week", "2026-W32-1", None),
            ("day", "2026-08-03T08:00:00+08:00", "2026-08-04T08:00:00+08:00"),
            ("day", None, "2026-08-05T14:00:00+08:00"),
        )
        for kind_id, start, end in cases:
            with self.subTest(kind_id=kind_id, start=start, end=end):
                interface = self._interface()
                result = interface.execute(self._command(kind_id, start, end))
                if isinstance(result, Prepared):
                    accepted = interface.execute(
                        Complete(
                            state_token=result.state_token,
                            public_copy="这一轮的正文。",
                        )
                    )
                    self.assertIsInstance(accepted, Accepted, accepted)
                    assert isinstance(accepted, Accepted)
                    self.assertTrue(accepted.public_copy.strip())
                else:
                    self.assertIsInstance(result, Stopped, result)
                    assert isinstance(result, Stopped)
                    self.assertTrue(result.public_copy.strip())


class NoNewDomainRoutingTests(unittest.TestCase):
    """This fix must not buy resilience with keyword or id routing."""

    def test_vocabulary_locality_audit_still_passes(self) -> None:
        import sys

        scripts = str(ROOT / "scripts")
        if scripts not in sys.path:
            sys.path.insert(0, scripts)
        from audit_v51_vocabulary_locality import audit

        self.assertEqual(audit(), [])

    def test_skill_document_names_no_capability_object_or_horizon(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        body = text.split("---", 2)[-1]
        for forbidden in (
            "near_time_personal",
            "fortune",
            "capability_id=",
            "object_id=",
            "kind_id",
            "aliases",
            "keywords",
            "synonyms",
        ):
            self.assertNotIn(forbidden, body, forbidden)

    def test_skill_document_adds_no_keyword_selection_table(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("触发词", text)
        self.assertNotIn("别名表", text)
        self.assertNotIn("对照表", text)


if __name__ == "__main__":
    unittest.main()

"""Tests for preparing external Bazi cases without calendar guesswork."""

from __future__ import annotations

import copy
import unittest

from bazi_case_prepare import prepare_bazi_case


def _case(*, case_id: str = "baziqa-2024-p1-q1", place: str = "广东，中国", hour: int = 16) -> dict:
    return {
        "case_schema": "mingli-benchmark-input-v1",
        "case_id": case_id,
        "system": "bazi",
        "source_person_id": "guangdong_female_19800824_P001",
        "birth_profile": {
            "birth": {
                "year": 1980,
                "month": 8,
                "day": 24,
                "hour": hour,
                "minute": 30,
                "place": place,
                "approximate": False,
            },
            "gender": "female",
        },
        "question": "以下哪项描述符合命主的学历情况？",
        "options": ["A. 小学", "B. 中学", "C. 大学", "D. 硕士"],
        "answer_isolated": True,
    }


class BaziCasePrepareTests(unittest.TestCase):
    def test_civil_utc8_birth_is_calculated_and_lunarized(self) -> None:
        prepared = prepare_bazi_case(_case())
        self.assertEqual(prepared["preparation_status"], "calculated")
        facts = prepared["fact_snapshot"]
        self.assertEqual(
            facts["output"]["four_pillars"],
            {"year": "庚申", "month": "甲申", "day": "己巳", "hour": "壬申"},
        )
        self.assertEqual(facts["calendar_normalization"]["lunar_date"]["month"], 7)
        self.assertEqual(prepared["time_profile"]["timezone"], "Asia/Shanghai")

    def test_same_person_different_question_has_same_fact_digest(self) -> None:
        first = prepare_bazi_case(_case())
        second_case = _case(case_id="baziqa-2024-p1-q2")
        second_case["question"] = "以下哪项描述符合命主的事业情况？"
        second = prepare_bazi_case(second_case)
        self.assertEqual(first["facts_digest"], second["facts_digest"])

    def test_late_zi_hour_is_not_silently_forced_to_one_school(self) -> None:
        prepared = prepare_bazi_case(_case(hour=23))
        self.assertEqual(prepared["preparation_status"], "ambiguous_zi_hour_policy")
        self.assertNotIn("fact_snapshot", prepared)
        self.assertEqual(
            set(prepared["required_resolution"]["candidate_policies"]),
            {"midnight", "late-zi-next-day"},
        )

    def test_country_only_america_location_is_not_guessed(self) -> None:
        prepared = prepare_bazi_case(_case(place="美国"))
        self.assertEqual(prepared["preparation_status"], "missing_timezone")
        self.assertNotIn("fact_snapshot", prepared)

    def test_supported_places_use_their_own_iana_timezones(self) -> None:
        singapore = prepare_bazi_case(_case(place="新加坡"))
        self.assertEqual(singapore["preparation_status"], "calculated")
        self.assertEqual(singapore["time_profile"]["timezone"], "Asia/Singapore")
        self.assertEqual(
            singapore["fact_snapshot"]["calendar_normalization"]["timezone"],
            "Asia/Singapore",
        )

        miyazaki = prepare_bazi_case(_case(place="日本宫崎县"))
        self.assertEqual(miyazaki["preparation_status"], "calculated")
        self.assertEqual(miyazaki["time_profile"]["timezone"], "Asia/Tokyo")
        self.assertTrue(
            miyazaki["fact_snapshot"]["calendar_normalization"]["civil_datetime"].endswith(
                "+09:00"
            )
        )

    def test_outcome_contamination_is_rejected(self) -> None:
        contaminated = copy.deepcopy(_case())
        contaminated["outcome"] = {"correct_option": "B"}
        with self.assertRaisesRegex(ValueError, "outcome"):
            prepare_bazi_case(contaminated)


if __name__ == "__main__":
    unittest.main()

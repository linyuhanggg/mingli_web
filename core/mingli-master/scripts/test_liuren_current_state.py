"""Source-bound current-state interpretation for Da Liu Ren."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from liuren_current_state import (
    build_current_state_context,
    load_general_imagery,
    target_relative_for_query,
)


SKILL_ROOT = Path(__file__).resolve().parents[1]


class LiurenCurrentStateTests(unittest.TestCase):
    def test_complete_miben_general_table_is_loaded_from_distilled_runtime_data(self) -> None:
        table = load_general_imagery(SKILL_ROOT)

        self.assertEqual(len(table), 12)
        self.assertEqual(set(table["腾蛇"]["by_branch"]), set("子丑寅卯辰巳午未申酉戌亥"))
        self.assertIn("酒食", table["腾蛇"]["by_branch"]["未"]["source_text"])
        self.assertIn("爭", table["勾陈"]["by_branch"]["辰"]["source_text"])

    def test_runtime_table_is_hash_bound_and_contains_only_short_excerpts(self) -> None:
        payload = json.loads(
            (SKILL_ROOT / "scripts" / "data" / "liuren-miben-general-imagery.json").read_text(
                encoding="utf-8"
            )
        )
        catalog = json.loads(
            (SKILL_ROOT / "references" / "catalog" / "catalog.json").read_text(encoding="utf-8")
        )
        catalog_entry = next(
            entry
            for entry in catalog["ready_reference_packs"]
            if entry["system"] == "san-shi" and entry["slug"] == "liuren-miben"
        )
        self.assertEqual(payload["source"]["sha256"], catalog_entry["local_fulltext_sha256"])
        excerpts = [
            item["source_text"]
            for general in payload["generals"].values()
            for item in general["by_branch"].values()
        ]
        self.assertTrue(excerpts)
        self.assertLessEqual(max(map(len, excerpts)), 80)

    def test_subject_class_deity_is_not_misread_as_the_subjects_activity(self) -> None:
        self.assertEqual(target_relative_for_query("我女朋友现在在干啥"), "妻财")
        self.assertEqual(target_relative_for_query("我爸现在在干嘛"), "父母")

        output = {
            "heaven_plate": [
                {"earth": branch, "heaven": branch}
                for branch in "子丑寅卯辰巳午未申酉戌亥"
            ],
            "three_transmissions": [
                {
                    "stage": "initial",
                    "branch": "辰",
                    "six_relative": "妻财",
                    "heavenly_general": "勾陈",
                    "season_strength": "旺",
                    "is_xunkong": True,
                },
                {
                    "stage": "middle",
                    "branch": "未",
                    "six_relative": "妻财",
                    "heavenly_general": "腾蛇",
                    "season_strength": "旺",
                    "is_xunkong": False,
                },
                {
                    "stage": "final",
                    "branch": "丑",
                    "six_relative": "妻财",
                    "heavenly_general": "白虎",
                    "season_strength": "旺",
                    "is_xunkong": False,
                },
            ],
        }
        context = build_current_state_context(
            SKILL_ROOT,
            "算一下我女朋友现在大概在干啥",
            output,
        )

        self.assertEqual(context["target_relative"], "妻财")
        self.assertEqual(context["target_match_count"], 3)
        self.assertIn("吃", context["stages"][1]["activity_candidates"][0])
        self.assertNotIn("钱", "".join(context["stages"][1]["activity_candidates"]))
        self.assertEqual(context["stages"][1]["landing_branch"], "未")
        self.assertEqual(len(context["source_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()

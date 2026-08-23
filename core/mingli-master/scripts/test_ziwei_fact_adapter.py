"""Tests for the pinned local Zi Wei Dou Shu fact adapter."""

from __future__ import annotations

import hashlib
import json
import subprocess
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

import adapter_validate
import ziwei_fact_adapter


class ZiweiFactAdapterTests(unittest.TestCase):
    def test_adapter_invokes_the_vendored_runtime_without_jit(self) -> None:
        completed = mock.Mock(
            returncode=0,
            stdout=json.dumps({"palaces": [{} for _ in range(12)]}),
            stderr="",
        )
        with mock.patch.object(
            ziwei_fact_adapter.subprocess,
            "run",
            return_value=completed,
        ) as run:
            ziwei_fact_adapter._run_iztro(datetime(1990, 5, 6, 8), "男")

        self.assertEqual(
            run.call_args.args[0],
            ["node", "--jitless", str(ziwei_fact_adapter.RUNTIME)],
        )

    def test_jitless_runtime_matches_the_default_chart_bytes(self) -> None:
        payload = json.dumps(
            {
                "year": 1990,
                "month": 5,
                "day": 6,
                "hour": 8,
                "gender": "男",
                "ziHourPolicy": "midnight",
            },
            ensure_ascii=False,
        )
        outputs: list[str] = []
        for flags in ((), ziwei_fact_adapter.NODE_RUNTIME_FLAGS):
            completed = subprocess.run(
                ["node", *flags, str(ziwei_fact_adapter.RUNTIME)],
                input=payload,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            outputs.append(completed.stdout)

        self.assertEqual(outputs[0], outputs[1])

    def test_public_benchmark_case_matches_the_pinned_chart_fixture(self) -> None:
        facts = ziwei_fact_adapter.build_from_birth(
            "1970-07-22T15:00:00+08:00",
            timezone_name="Asia/Shanghai",
            location="北京，中国",
            gender="male",
        )

        self.assertEqual(
            facts["calendar_normalization"]["ganzhi"],
            {"year": "庚戌", "month": "癸未", "day": "癸卯", "hour": "庚申"},
        )
        self.assertEqual(
            facts["output"]["ming_shen"],
            {
                "ming_branch": "亥",
                "shen_branch": "卯",
                "soul_star": "巨门",
                "body_star": "文昌",
            },
        )
        self.assertEqual(facts["output"]["five_elements_class"], "土五局")
        first = facts["output"]["palaces"][0]
        self.assertEqual(
            (first["name"], first["earthlyBranch"]),
            ("田宅", "寅"),
        )
        self.assertEqual(
            [(star["name"], star["brightness"], star["mutagen"]) for star in first["majorStars"]],
            [("太阳", "旺", "禄"), ("巨门", "庙", "")],
        )
        validation = adapter_validate.validate_payload("ziwei", facts)
        self.assertTrue(validation["ok"], validation)

    def test_vendored_runtime_matches_recorded_provenance_hash(self) -> None:
        provenance = json.loads(
            (ziwei_fact_adapter.VENDOR / "PROVENANCE.json").read_text(encoding="utf-8")
        )
        digest = hashlib.sha256(
            (ziwei_fact_adapter.VENDOR / "iztro.min.js").read_bytes()
        ).hexdigest()
        self.assertEqual(provenance["version"], ziwei_fact_adapter.IZTRO_VERSION)
        self.assertEqual(digest, provenance["vendored_sha256"])
        self.assertTrue((ziwei_fact_adapter.VENDOR / "LICENSE").is_file())

    def test_fact_provenance_is_workspace_independent(self) -> None:
        facts = ziwei_fact_adapter.build_from_birth(
            "1970-07-22T15:00:00+08:00",
            timezone_name="Asia/Shanghai",
            location="北京，中国",
            gender="male",
        )

        self.assertEqual(
            facts["adapter"]["dependency"]["provenance"],
            "vendor/iztro-2.5.8/PROVENANCE.json",
        )

    def test_rejects_unknown_timezone_or_missing_location(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown timezone"):
            ziwei_fact_adapter.build_from_birth(
                "2000-01-01T12:00:00",
                timezone_name="Moon/SeaOfTranquility",
                location="月球",
                gender="male",
            )
        with self.assertRaisesRegex(ValueError, "location"):
            ziwei_fact_adapter.build_from_birth(
                "2000-01-01T12:00:00",
                timezone_name="Asia/Shanghai",
                location="",
                gender="male",
            )


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Generate the frozen lunar-python comparator rows for Selection Task 7K."""

from __future__ import annotations

from pathlib import Path

import yaml
from lunar_python import Solar


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "references/fixtures/selection-v51.yaml"
DATES = (
    "2024-01-01",
    "2024-02-03", "2024-02-04", "2024-02-05",
    "2024-02-09", "2024-02-10", "2024-02-11",
    "2024-03-19", "2024-03-20", "2024-03-21",
    "2024-05-04", "2024-05-05", "2024-05-06",
    "2024-06-20", "2024-06-21", "2024-06-22",
    "2024-08-06", "2024-08-07", "2024-08-08",
    "2024-09-16", "2024-09-17", "2024-09-18",
    "2024-11-06", "2024-11-07", "2024-11-08",
    "2025-01-28", "2025-01-29", "2025-01-30",
    "2025-07-24", "2026-07-24",
)
SOURCE = {
    "project": "6tail/lunar-python",
    "version": "1.4.8",
    "commit": "000c8a3d74eed098d6256a28fdd51b869324c559",
    "license": "MIT",
    "role": "independent engineering comparator; not a classical source",
}


def _case(identifier: int, value: str) -> dict:
    year, month, day = (int(part) for part in value.split("-"))
    lunar = Solar.fromYmdHms(year, month, day, 12, 0, 0).getLunar()
    return {
        "id": f"lunar-python-{identifier:02d}",
        "source": dict(SOURCE),
        "input": {
            "date": value,
            "time": "12:00:00",
            "timezone": "Asia/Shanghai",
            "location": "上海",
        },
        "expected": {
            "lunar_date": {
                "year": lunar.getYear(),
                "month": abs(lunar.getMonth()),
                "day": lunar.getDay(),
                "is_leap_month": lunar.getMonth() < 0,
            },
            "ganzhi": {
                "year": lunar.getYearInGanZhiExact(),
                "month": lunar.getMonthInGanZhiExact(),
                "day": lunar.getDayInGanZhiExact(),
            },
            "jianchu": lunar.getZhiXing(),
            "mansion": lunar.getXiu(),
            "day_twelve_god": lunar.getDayTianShen().replace("金匮", "金贵"),
            "huanghei": "huang" if lunar.getDayTianShenLuck() == "吉" else "hei",
            "clash": lunar.getDayChongDesc(),
        },
    }


def main() -> int:
    payload = {
        "schema_version": "mingli-selection-fixtures-v51",
        "profile_id": "xieji-official-cnlunar-v1",
        "external_reference_cases": [
            _case(index, value) for index, value in enumerate(DATES, start=1)
        ],
        "completion_cases": [],
        "boundary_cases": [],
        "event_profile_cases": [],
        "no_candidate_cases": [],
    }
    OUTPUT.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    print(f"wrote {OUTPUT} with {len(DATES)} external cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

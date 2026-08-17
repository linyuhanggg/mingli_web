#!/usr/bin/env python3
"""基准盘组：生成确定性、可复现的合成盘输入，用于谓词判别力测量。

为什么需要它
    一条谓词写成 `nonempty(/four_pillars)` 能通过编译、路径和命中检查，
    但它在每张盘上都命中——是存在性检查，不是条件判别。要区分两者，
    必须在一组**多样化**的盘上测命中率。这个文件就是那组盘。

覆盖设计（不用随机数，完全可复现）
    **日期 × 时辰的交叉积**，不是线性扫描。

    日期步长取 61 天：61 mod 60 == 1，因此每步日柱前进一位，
    连续 60 个日期覆盖六十甲子一轮；61 天 ≈ 2 个农历月，月令也随之轮转。
    时辰独立取十二双时辰全集，与日期做交叉。

    为什么必须交叉：命宫由农历月与生时共同决定。若让时辰随日期线性递进
    （早先的写法），(月, 时) 只会出现 lcm 个组合——任何线性扫描都有这个
    上限。结果是「某星落某宫」这类条件出现系统性盲区，判别力会被误判成
    恒不成立。交叉积消除该盲区。

用法
    python3 scripts/baseline_charts.py                    # 打印覆盖概要
    python3 scripts/baseline_charts.py --emit fixtures.json
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# 起点取立春之后，避开年柱换柱边界；该边界另有专门的边界用例，不混进判别力盘组。
BASE = datetime(1970, 2, 20, 1, 0, tzinfo=timezone(timedelta(hours=8)))
DAY_STEP = 61          # 61 mod 60 == 1 → 日柱逐步前进一位
HOURS = tuple(range(1, 24, 2))   # 十二双时辰的中点：1,3,5…23，避开时辰边界
DEFAULT_DATES = 30     # 30 个日期 × 12 时辰 = 360 张
DEFAULT_COUNT = DEFAULT_DATES * len(HOURS)

# 北京；判别力只关心四柱/宫位的多样性，坐标固定即可，也避免把地点当变量。
GEO: dict[str, Any] = {
    "longitude": 116.4,
    "latitude": 39.9,
    "location": "synthetic",
    "coordinate_source": "synthetic_fixture",
    "coordinate_accuracy_meters": 1000,
    "time_basis_policy": "local_apparent_solar-v1",
}


def build(count: int = DEFAULT_COUNT) -> list[dict[str, Any]]:
    """日期 × 十二时辰的交叉积，按 count 截断（截断时优先保证时辰全覆盖）。"""
    charts: list[dict[str, Any]] = []
    dates = -(-count // len(HOURS))  # ceil：先按时辰成组，再按需截断
    for day_index in range(dates):
        day = BASE + timedelta(days=DAY_STEP * day_index)
        for hour_index, hour in enumerate(HOURS):
            moment = day.replace(hour=hour)
            index = day_index * len(HOURS) + hour_index
            charts.append(
                {
                    "chart_id": f"baseline-{index:04d}",
                    "datetime": moment.isoformat(),
                    # 性别按 (日期 + 时辰) 交替，避免与时辰同相位
                    "gender": "male" if (day_index + hour_index) % 2 == 0 else "female",
                    **GEO,
                }
            )
    return charts[:count]


def facts_for(chart: dict[str, Any], capability: str) -> dict[str, Any]:
    """把一张基准盘翻译成某个 capability 的 facts 载荷。

    各能力声明的时间字段名不同（describe 的 input_fields 是权威），
    这里只做字段名映射，不改动时刻本身。
    """
    geo = {key: chart[key] for key in GEO}
    moment = chart["datetime"]
    if capability == "bazi":
        return {**geo, "birth_datetime_or_four_pillars": moment, "gender": chart["gender"]}
    if capability == "luming-nayin":
        return {**geo, "birth_datetime_or_four_pillars": moment}
    if capability == "ziwei":
        return {**geo, "birth_datetime": moment, "gender": chart["gender"]}
    if capability == "xingming":
        return {**geo, "birth_datetime": moment}
    raise ValueError(f"基准盘组暂不支持该能力：{capability}（命类之外的输入形状不同）")


SUPPORTED = ("bazi", "ziwei", "xingming", "luming-nayin")


def main() -> int:
    parser = argparse.ArgumentParser(description="生成基准盘组")
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--emit", help="写出 JSON fixture")
    args = parser.parse_args()

    charts = build(args.count)
    print(f"基准盘 {len(charts)} 张")
    print(f"  起点     {charts[0]['datetime']}")
    print(f"  终点     {charts[-1]['datetime']}")
    dates = -(-len(charts) // len(HOURS))
    print(f"  结构     {dates} 个日期 × {len(HOURS)} 时辰（交叉积）")
    print(f"  日柱     步长 {DAY_STEP} 天（61 mod 60 = 1）→ 覆盖 {min(dates, 60)}/60 个日柱")
    print(f"  时辰     {len(HOURS)}/12 全覆盖，每个时辰 {dates} 张")
    print(f"  性别     男 {sum(1 for c in charts if c['gender'] == 'male')} / "
          f"女 {sum(1 for c in charts if c['gender'] == 'female')}")
    print(f"  适用能力 {', '.join(SUPPORTED)}")

    if args.emit:
        Path(args.emit).write_text(
            json.dumps({"schema": "mingli-baseline-charts-v1", "charts": charts},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\n已写出 {args.emit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

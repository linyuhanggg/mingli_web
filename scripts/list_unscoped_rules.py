#!/usr/bin/env python3
"""列出某个 route 下还没有触发条件的规则，附原文，供谓词施工取活。

用法
    python3 scripts/list_unscoped_rules.py --route ziwei
    python3 scripts/list_unscoped_rules.py --route ziwei --pack ziwei-doushu-quanshu --limit 10
    python3 scripts/list_unscoped_rules.py --route bazi --json todo.json

只读，不修改任何文件。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

DEFAULT_TREE = Path("core/mingli-master")

# 与 build_evidence_index.SCOPE_BINDING_PACK_PREFIXES 一致：route 决定哪些书目归它管。
ROUTE_PACK_PREFIXES: dict[str, tuple[str, ...]] = {
    "bazi": ("bazi/",),
    "ziwei": ("ziwei/",),
    "luming-nayin": ("luming-nayin/",),
    "xingming": ("xingming/",),
    "liuyao": (
        "divination/zengshan-buyi",
        "divination/bushi-zhengzong",
        "divination/huangjin-ce",
        "divination/huozhu-lin",
    ),
    "meihua": (
        "divination/meihua-yishu",
        "divination/zhouyi-zhezhong",
        "divination/huangji-jingshi",
    ),
    "liuren": (
        "san-shi/daliuren-daquan",
        "san-shi/liuren-miben",
        "san-shi/liuren-zhiyin",
    ),
    "selection": ("selection/",),
    "fengshui": ("fengshui/",),
    "physiognomy": ("physiognomy/",),
}


def main() -> int:
    parser = argparse.ArgumentParser(description="列出待写谓词的规则")
    parser.add_argument("--route", required=True, choices=sorted(ROUTE_PACK_PREFIXES))
    parser.add_argument("--tree", default=str(DEFAULT_TREE))
    parser.add_argument("--pack", help="只看某一部书，例如 ziwei-doushu-quanshu")
    parser.add_argument("--limit", type=int, default=0, help="0 表示不限")
    parser.add_argument("--role", default="issue_specific_judgment_rule",
                        help="默认只列问题级判断规则；传 all 列全部")
    parser.add_argument("--json", help="写出 JSON")
    args = parser.parse_args()

    index = Path(args.tree) / "references" / "index" / "evidence-rules.jsonl"
    if not index.exists():
        sys.exit(f"找不到证据索引：{index}")

    prefixes = ROUTE_PACK_PREFIXES[args.route]
    rows: list[dict[str, Any]] = []
    for line in index.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rule = json.loads(line)
        rule_id = rule["rule_id"]
        if not rule_id.startswith(prefixes):
            continue
        if rule.get("classical_binding_status") != "inactive_unscoped":
            continue
        if args.role != "all" and rule.get("evidence_role") != args.role:
            continue
        if args.pack and args.pack not in rule_id:
            continue
        rows.append(
            {
                "rule_id": rule_id,
                "title": rule.get("title", ""),
                "source_title": rule.get("source_title", ""),
                "source_anchor": rule.get("source_anchor", ""),
                "evidence_role": rule.get("evidence_role", ""),
                "quote": rule.get("quote", ""),
            }
        )

    rows.sort(key=lambda r: r["rule_id"])
    shown = rows[: args.limit] if args.limit else rows

    print(f"route={args.route}  待写谓词 {len(rows)} 条"
          f"{f'（显示前 {len(shown)} 条）' if args.limit else ''}\n")
    for row in shown:
        print(f"{row['rule_id']}")
        print(f"    {row['title']}")
        print(f"    出处 {row['source_title']} {row['source_anchor']}")
        print(f"    原文「{row['quote']}」")
        print()

    if args.json:
        Path(args.json).write_text(
            json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"已写出 {args.json}（{len(rows)} 条）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

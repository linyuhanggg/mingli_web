#!/usr/bin/env python3
"""Fact path 盘点：导出各 Provider 实际可寻址的事实路径，并与规则谓词交叉。

回答两个问题：
  1. 每个 Provider 的 Runtime 实际输出了哪些叶子路径（谓词能引用的地址）？
  2. 已写好谓词的规则，它引用的路径在真实输出里存在吗？
     —— 不存在的规则即使通过语义核对也永远不会命中，属于「死规则」。

用法：
    python3 scripts/fact_path_inventory.py                    # 全部 Provider
    python3 scripts/fact_path_inventory.py --only bazi,ziwei
    python3 scripts/fact_path_inventory.py --json out.json

只使用合成资料，不读取也不写入任何个人出生资料。
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any

DEFAULT_ROOTS = (
    Path.home() / ".codex" / "skills" / "mingli-master",
    Path.home() / ".claude" / "skills" / "mingli-master",
)
DEFAULT_VENV_PY = Path.home() / ".local/share/mingli-master/venv/bin/python"

# 合成出生资料（北京坐标，非任何真实个人）
SYNTHETIC_BIRTH = {
    "birth_datetime_or_four_pillars": "1985-03-02T00:00:00+08:00",
    "gender": "male",
    "longitude": 116.4,
    "latitude": 39.9,
    "location": "synthetic",
    "coordinate_source": "synthetic_fixture",
    "coordinate_accuracy_meters": 1000,
    "time_basis_policy": "local_apparent_solar-v1",
}
EVENT_TIME = "2026-08-17T10:00:00+08:00"
GEO = {
    "longitude": 116.4,
    "latitude": 39.9,
    "location": "synthetic",
    "coordinate_source": "synthetic_fixture",
    "coordinate_accuracy_meters": 1000,
    "time_basis_policy": "local_apparent_solar-v1",
}

# capability -> (object_id, horizon, 该能力的事实字段)
# 字段名严格取自 describe 的 input_fields；不同能力用的时间字段名不同。
PROFILES: dict[str, tuple[str, str, dict[str, Any]]] = {
    "bazi": ("natal", "life", SYNTHETIC_BIRTH),
    "ziwei": ("natal", "life", {**GEO, "birth_datetime": SYNTHETIC_BIRTH["birth_datetime_or_four_pillars"], "gender": "male"}),
    "xingming": ("natal", "life", {**GEO, "birth_datetime": SYNTHETIC_BIRTH["birth_datetime_or_four_pillars"]}),
    "luming-nayin": ("natal", "life", {**GEO, "birth_datetime_or_four_pillars": SYNTHETIC_BIRTH["birth_datetime_or_four_pillars"]}),
    "fortune": ("near_time_personal", "day", {**GEO, "birth_datetime": SYNTHETIC_BIRTH["birth_datetime_or_four_pillars"], "gender": "male", "reference_datetime": EVENT_TIME}),
    "qimen": ("concrete_event", "instant", {**GEO, "event_datetime": EVENT_TIME}),
    "liuren": ("concrete_event", "instant", {**GEO, "event_datetime_or_reference_datetime": EVENT_TIME}),
    "taiyi": ("macro_historical", "year", {**GEO, "reference_datetime": EVENT_TIME}),
    "liuyao": ("concrete_event", "instant", {**GEO, "event_datetime": EVENT_TIME, "cast": {"tosses": [7, 8, 9, 6, 8, 7]}}),
    "meihua": ("concrete_event", "instant", {**GEO, "event_datetime": EVENT_TIME, "casting_method": "number", "number": 27, "count": 2}),
    "selection": ("calendar_choice", "day", {**GEO, "date_range": {"start": "2026-09-01", "end": "2026-09-10"}, "event_profile": "general", "requested_actions": ["general"]}),
    "fengshui": ("spatial_observation", "instant", {**GEO, "fengshui_spec": {"method": "bazhai", "sitting": "壬", "facing": "丙"}}),
    "physiognomy": ("visible_observation", "instant", {**GEO, "physiognomy_spec": {"target": "face", "observations": ["额高"]}}),
}


# 在 matcher 一侧拦截取路径。brief.facts 是公开投影（/calculated/<system>/…），
# 与规则谓词使用的命名空间（/output/…）不同；只有 match_rule 收到的 FactRef.path
# 才是寻址判定的真实依据，用 brief 会把全部规则误判成死规则。
TRACER = '''
import json, sys
from pathlib import Path
ROOT = Path(sys.argv[1]).resolve(); PAYLOAD = Path(sys.argv[2]); OUT = Path(sys.argv[3])
sys.path.insert(0, str(ROOT / "scripts")); sys.dont_write_bytecode = True
import reading_engine.evidence_rules as ER
SEEN = set(); _orig = ER.match_rule
def traced(rule, facts):
    for item in facts: SEEN.add(item.path)
    return _orig(rule, facts)
ER.match_rule = traced
import reading_evidence_bundle as REB
REB.match_rule = traced
from reading_engine.interface import ReadingInterface
from reading_engine.interface_contracts import command_from_dict
store = Path(sys.argv[4])
store.mkdir(parents=True, exist_ok=True)
cmd = command_from_dict(json.loads(PAYLOAD.read_text(encoding="utf-8")))
res = ReadingInterface(skill_root=ROOT, store_root=store).execute(cmd).to_dict()
OUT.write_text(json.dumps({
    "kind": res.get("kind"), "reason": res.get("reason"),
    "input_request": res.get("input_request"), "paths": sorted(SEEN),
}, ensure_ascii=False), encoding="utf-8")
'''


def _child_env() -> dict[str, str]:
    """Provider 可能 spawn node（如 ziwei_runtime.js），PATH 必须保留宿主查找路径。"""
    return {
        "PYTHONDONTWRITEBYTECODE": "1",
        "HOME": str(Path.home()),
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
    }


def run_command(root: Path, python: Path, payload: dict[str, Any]) -> dict[str, Any]:
    proc = subprocess.run(
        [str(python), str(root / "scripts" / "runtime_launcher.py")],
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True,
        text=True,
        env=_child_env(),
    )
    if not proc.stdout.strip():
        return {"kind": "stopped", "reason": "no_output", "stderr": proc.stderr[:400]}
    return json.loads(proc.stdout)


def describe(root: Path, python: Path) -> dict[str, dict[str, Any]]:
    """能力清单 -> {id: {objects, horizons, dimensions}}；探测参数一律取自这里，不硬编码。"""
    result = run_command(root, python, {"kind": "describe"})
    views: dict[str, dict[str, Any]] = {}
    for cap in result.get("capabilities") or []:
        cid = cap.get("id") or cap.get("capability_id")
        views[cid] = {
            "objects": [o["id"] for o in cap.get("objects") or []],
            "horizons": [h["id"] for h in cap.get("horizons") or []],
            "dimensions": cap.get("default_dimension_ids")
            or [d["id"] for d in cap.get("dimensions") or []],
        }
    return views


def probe(root: Path, python: Path, capability: str, view: dict[str, Any]) -> dict[str, Any]:
    object_id, horizon, facts = PROFILES.get(capability, ("natal", "life", SYNTHETIC_BIRTH))
    # describe 是权威：PROFILES 里的猜测若不在声明范围内，回退到声明的第一个值。
    if object_id not in view["objects"] and view["objects"]:
        object_id = view["objects"][0]
    if horizon not in view["horizons"] and view["horizons"]:
        horizon = view["horizons"][0]
    dimension = view["dimensions"][0] if view["dimensions"] else "state"
    payload = {
        "kind": "prepare",
        "query": "整体总览",
        "intent": {
            "subject_refs": ["s1"],
            "object_id": object_id,
            "dimension_ids": [dimension],
            "horizon": {"kind_id": horizon},
            "capability_id": capability,
        },
        "facts": {"s1": facts},
    }
    result = run_traced(root, python, payload)
    if result.get("kind") != "prepared":
        need = result.get("input_request") or {}
        missing = [
            item.get("id")
            for group in (need.get("requirements") or [])
            for item in (group.get("any_of") or [])
        ]
        return {
            "capability": capability,
            "ok": False,
            "reason": result.get("reason"),
            "missing_inputs": missing,
            "paths": [],
        }
    return {"capability": capability, "ok": True, "paths": result["paths"]}


def run_traced(root: Path, python: Path, payload: dict[str, Any]) -> dict[str, Any]:
    """跑一次 prepare，并抓取 matcher 实际收到的 fact 路径。"""
    with tempfile.TemporaryDirectory() as tmp:
        tracer = Path(tmp) / "tracer.py"
        request = Path(tmp) / "request.json"
        out = Path(tmp) / "out.json"
        tracer.write_text(TRACER, encoding="utf-8")
        request.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        proc = subprocess.run(
            [str(python), str(tracer), str(root), str(request), str(out), str(Path(tmp) / "store")],
            capture_output=True,
            text=True,
            env=_child_env(),
        )
        if not out.exists():
            return {"kind": "stopped", "reason": "tracer_failed", "stderr": proc.stderr[-400:]}
        return json.loads(out.read_text(encoding="utf-8"))


def load_rules(root: Path) -> list[dict[str, Any]]:
    index = root / "references" / "index" / "evidence-rules.jsonl"
    return [json.loads(line) for line in index.read_text(encoding="utf-8").splitlines() if line.strip()]


# 规则 system -> capability（规则库用学科名，Runtime 用能力名）
SYSTEM_TO_CAPABILITY = {
    "bazi": "bazi",
    "ziwei": "ziwei",
    "xingming": "xingming",
    "luming-nayin": "luming-nayin",
    "divination": "liuyao",
    "qimen": "qimen",
    "liuren": "liuren",
    "taiyi": "taiyi",
    "selection": "selection",
    "fengshui": "fengshui",
    "physiognomy": "physiognomy",
}


def _addressable(predicate: dict[str, Any], available: set[str]) -> bool:
    """镜像 evidence_rules._predicate_fact_refs 的寻址语义。

    `present` / `nonempty` / `descendant_eq` / `same_record_fields` 以「路径包含
    suffix + '/'」命中嵌套子树；其余算子按结尾匹配。判定只看地址是否可达，
    不判断值是否满足——那是 matcher 在真实盘上的事。
    """
    suffix = predicate["path_suffix"]
    nested = suffix + "/"
    if predicate.get("operator") in {"present", "nonempty", "descendant_eq", "same_record_fields"}:
        return any(path.endswith(suffix) or nested in path for path in available)
    return any(path.endswith(suffix) for path in available)


def crossref(rules: list[dict[str, Any]], inventory: dict[str, dict[str, Any]]) -> dict[str, Any]:
    report: dict[str, Any] = {}
    for system, capability in SYSTEM_TO_CAPABILITY.items():
        entry = inventory.get(capability)
        if not entry or not entry.get("ok"):
            report[system] = {"status": "probe_failed", "capability": capability}
            continue
        available = set(entry["paths"])
        rows = [r for r in rules if r.get("system") == system]
        dead: list[dict[str, Any]] = []
        live = 0
        for rule in rows:
            preds = (rule.get("required_fact_predicates") or []) + (
                rule.get("excluded_fact_predicates") or []
            )
            if not preds:
                continue
            missing = [p["path_suffix"] for p in preds if not _addressable(p, available)]
            if missing:
                dead.append(
                    {
                        "rule_id": rule["rule_id"],
                        "status": rule.get("classical_binding_status"),
                        "active": rule.get("runtime_active"),
                        "missing_paths": missing,
                    }
                )
            else:
                live += 1
        report[system] = {
            "capability": capability,
            "available_paths": len(available),
            "rules_total": len(rows),
            "rules_with_predicates": live + len(dead),
            "rules_resolvable": live,
            "rules_dead": len(dead),
            "dead_samples": dead[:8],
            "missing_path_freq": _freq(dead),
        }
    return report


def _freq(dead: list[dict[str, Any]]) -> list[tuple[str, int]]:
    counter: dict[str, int] = defaultdict(int)
    for row in dead:
        for path in row["missing_paths"]:
            counter[path] += 1
    return sorted(counter.items(), key=lambda kv: -kv[1])[:10]


def resolve_root(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser()
    for candidate in DEFAULT_ROOTS:
        if (candidate / "scripts" / "runtime_launcher.py").exists():
            return candidate
    sys.exit("未找到 mingli-master 发行包，请用 --root 指定")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fact path 盘点与规则交叉")
    parser.add_argument("--root", help="发行包根目录")
    parser.add_argument("--python", help="provisioned runtime venv 的 python")
    parser.add_argument("--only", help="逗号分隔的 capability 子集")
    parser.add_argument("--json", help="把完整结果写到此文件")
    args = parser.parse_args()

    root = resolve_root(args.root)
    python = Path(args.python).expanduser() if args.python else DEFAULT_VENV_PY
    if not python.exists():
        sys.exit(f"runtime venv 不存在：{python}")

    views = describe(root, python)
    caps = list(views)
    if not caps:
        sys.exit("describe 失败：Runtime 未通过启动准入")
    if args.only:
        wanted = {c.strip() for c in args.only.split(",")}
        caps = [c for c in caps if c in wanted]

    inventory = {}
    for capability in caps:
        entry = probe(root, python, capability, views[capability])
        inventory[capability] = entry
        mark = "✓" if entry["ok"] else "✗"
        detail = (
            f"{len(entry['paths'])} 个可寻址路径"
            if entry["ok"]
            else f"{entry['reason']} 缺 {entry.get('missing_inputs')}"
        )
        print(f"  {mark} {capability:<14} {detail}")

    print()
    report = crossref(load_rules(root), inventory)
    print(f"{'学科':<16}{'可用路径':>8}{'有谓词规则':>10}{'可命中':>8}{'死规则':>8}")
    print("-" * 52)
    for system, row in sorted(report.items()):
        if row.get("status") == "probe_failed":
            print(f"{system:<16}{'—':>8}{'(探测失败)':>10}")
            continue
        print(
            f"{system:<16}{row['available_paths']:>8}{row['rules_with_predicates']:>10}"
            f"{row['rules_resolvable']:>8}{row['rules_dead']:>8}"
        )

    if args.json:
        Path(args.json).write_text(
            json.dumps({"inventory": inventory, "crossref": report}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\n完整结果：{args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

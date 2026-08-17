#!/usr/bin/env python3
"""谓词验收：对 scope 绑定跑全部可机械判定的检查。

覆盖施工规范里的第 1/2/3/5/7 项；第 4 项（引文真实）由
`verify_citation.py` 负责，第 6 项（语义忠实）必须人工，本脚本不假装能做。

  1 编译     build_evidence_index.py --check 必须 pass
  2 路径真实 谓词引用的 path_suffix 必须在 Runtime 真实输出里可寻址
  3 真盘命中 在基准盘组上至少命中一次（永不命中 = 写错了或写死了）
  5 判别力   命中率必须落在 [floor, ceiling]；100% 命中 = 存在性检查，打回
  7 未越界   计算事实中不得出现 verdict 字段

用法
    # 全量审计某个 route
    python3 scripts/verify_predicates.py --route ziwei

    # 只验收本次新增/改动的规则（推荐用于验收外包成果）
    python3 scripts/verify_predicates.py --route ziwei --since snapshots/ziwei-before.json

    # 施工前先存一份基线
    python3 scripts/verify_predicates.py --route ziwei --snapshot snapshots/ziwei-before.json

退出码 0 = 全部通过；1 = 有规则未通过；2 = 环境或编译问题（未开始逐条检查）。
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import baseline_charts

# 源码树与签名 Runtime 是两个路径，不能合并：
#   core/mingli-master           可编辑，含 scope YAML 与编译器，但**没有签名清单**，跑不了 Provider
#   .runtime/<release>           已签名，能跑 Provider，但它的 YAML 是上次发布时的快照
# 判别力测量不需要新谓词进入 release——tracer 直接对 fact index 评估目标谓词，
# 绕过 runtime_active 门禁。所以新写的谓词从源码树读，盘面事实从签名 Runtime 取。
DEFAULT_SOURCE_TREE = Path("core/mingli-master")
DEFAULT_RUNTIME = Path(".runtime/v53-time-check-release")
DEFAULT_VENV_PY = Path.home() / ".local/share/mingli-master/venv/bin/python"

# route -> capability。规则库按学科分包，Runtime 按能力注册，两者不同名。
ROUTE_TO_CAPABILITY = {
    "bazi": "bazi",
    "ziwei": "ziwei",
    "xingming": "xingming",
    "luming-nayin": "luming-nayin",
}
# 上限 0.60 是判别力门槛：一条真条件不该在六成以上的盘上成立。
# 下限不设百分比，只要求「至少成立 1 次」——实测合法的罕见格局可以低到
# 0.8%（如「太阳会文昌于官禄」在 360 张盘上 3 次），用百分比下限会误杀。
HIT_CEILING = 0.60

# 判别力必须绕过 runtime_active 门禁直接评估谓词。
# 新写的谓词按定义还没有 verified 的古籍绑定，runtime_active=False，
# match_rule 会在第一行短路返回；靠它测命中率永远得 0。所以这里只借
# match_rule 的调用时机拿到每张盘的 fact index，再用引擎自己的
# _predicate_matches 直接评估目标谓词——语义与生产一致，但不受激活状态影响。
TRACER = r'''
import json, sys, tempfile
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
CAPABILITY = sys.argv[2]
FIXTURES = Path(sys.argv[3])
OUT = Path(sys.argv[4])
REPO_SCRIPTS = Path(sys.argv[5])
TARGETS = json.loads(Path(sys.argv[6]).read_text(encoding="utf-8"))

sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(REPO_SCRIPTS))
sys.dont_write_bytecode = True

import reading_engine.evidence_rules as ER
import baseline_charts

_orig = ER.match_rule
PATHS = set()
CURRENT = {"facts": ()}

def traced(rule, facts):
    if facts and not CURRENT["facts"]:
        CURRENT["facts"] = facts
        for item in facts:
            PATHS.add(item.path)
    return _orig(rule, facts)

ER.match_rule = traced
import reading_evidence_bundle as REB
REB.match_rule = traced


def evaluate(binding, facts):
    """用引擎自己的谓词语义判断一条 scope 绑定在本盘是否成立。"""
    required = binding.get("predicates") or []
    excluded = binding.get("excluded_predicates") or []
    for raw in required:
        if not ER._predicate_matches(ER.FactPredicate.from_dict(raw), facts):
            return False
    for raw in excluded:
        if ER._predicate_matches(ER.FactPredicate.from_dict(raw), facts):
            return False
    return True

from reading_engine.interface import ReadingInterface
from reading_engine.interface_contracts import command_from_dict


def find_verdicts(node, trail=""):
    """越界扫描：计算事实里出现 verdict 就是把谓词命中升级成了断语。"""
    found = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "verdict" and value is not None:
                found.append(f"{trail}/{key}")
            found.extend(find_verdicts(value, f"{trail}/{key}"))
    elif isinstance(node, list):
        for i, value in enumerate(node):
            found.extend(find_verdicts(value, f"{trail}/{i}"))
    return found


descr = ReadingInterface(
    skill_root=ROOT, store_root=Path(tempfile.mkdtemp())
).execute(command_from_dict({"kind": "describe"})).to_dict()
view = next(
    c for c in descr["capabilities"]
    if (c.get("id") or c.get("capability_id")) == CAPABILITY
)
objects = [o["id"] for o in view.get("objects") or []]
horizons = [h["id"] for h in view.get("horizons") or []]
dims = view.get("default_dimension_ids") or [d["id"] for d in view.get("dimensions") or []]
object_id = "natal" if "natal" in objects else objects[0]
horizon = "life" if "life" in horizons else horizons[0]

charts = json.loads(FIXTURES.read_text(encoding="utf-8"))["charts"]
prepared = 0
failures = []
verdicts = []

HITS = {rule_id: 0 for rule_id in TARGETS}

with tempfile.TemporaryDirectory() as tmp:
    for chart in charts:
        payload = {
            "kind": "prepare",
            "query": "整体总览",
            "intent": {
                "subject_refs": ["s1"],
                "object_id": object_id,
                "dimension_ids": [dims[0]],
                "horizon": {"kind_id": horizon},
                "capability_id": CAPABILITY,
            },
            "facts": {"s1": baseline_charts.facts_for(chart, CAPABILITY)},
        }
        store = Path(tmp) / chart["chart_id"]
        store.mkdir(parents=True, exist_ok=True)
        CURRENT["facts"] = ()
        try:
            result = ReadingInterface(
                skill_root=ROOT, store_root=store
            ).execute(command_from_dict(payload)).to_dict()
        except Exception as error:
            failures.append({"chart": chart["chart_id"], "error": repr(error)[:200]})
            continue
        if result.get("kind") != "prepared":
            failures.append({"chart": chart["chart_id"], "reason": result.get("reason")})
            continue
        prepared += 1
        hit = find_verdicts(result.get("brief") or {})
        if hit:
            verdicts.append({"chart": chart["chart_id"], "paths": hit[:5]})
        facts = CURRENT["facts"]
        if not facts:
            failures.append({"chart": chart["chart_id"], "reason": "no_fact_index_captured"})
            continue
        for rule_id, binding in TARGETS.items():
            if evaluate(binding, facts):
                HITS[rule_id] += 1

OUT.write_text(json.dumps({
    "prepared": prepared,
    "charts": len(charts),
    "failures": failures[:10],
    "hits": HITS,
    "paths": sorted(PATHS),
    "verdict_violations": verdicts[:10],
}, ensure_ascii=False), encoding="utf-8")
'''


def compile_check(tree: Path, python: Path) -> tuple[bool, str]:
    proc = subprocess.run(
        [str(python), "scripts/build_evidence_index.py", "--check"],
        cwd=tree,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    text = (proc.stdout or proc.stderr).strip()
    return ('"status": "pass"' in text or '"status":"pass"' in text), text[-300:]


def load_scope(tree: Path, python: Path) -> dict[str, dict[str, Any]]:
    """读 scope YAML（含 series 展开）。用 Runtime venv 的 PyYAML，仓库不引入新依赖。"""
    code = (
        "import json,sys;sys.path.insert(0,'scripts');"
        "from build_evidence_index import load_evidence_scope_bindings as L;"
        "print(json.dumps(L(),ensure_ascii=False,default=str))"
    )
    proc = subprocess.run(
        [str(python), "-c", code],
        cwd=tree,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    if proc.returncode != 0:
        sys.exit(f"读 scope 绑定失败：{proc.stderr[-400:]}")
    return json.loads(proc.stdout)


def run_tracer(
    tree: Path,
    python: Path,
    capability: str,
    fixtures: Path,
    targets: dict[str, Any],
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        tracer = Path(tmp) / "tracer.py"
        out = Path(tmp) / "out.json"
        target_file = Path(tmp) / "targets.json"
        tracer.write_text(TRACER, encoding="utf-8")
        target_file.write_text(json.dumps(targets, ensure_ascii=False), encoding="utf-8")
        proc = subprocess.run(
            [
                str(python), str(tracer), str(tree.resolve()), capability,
                str(fixtures.resolve()), str(out),
                str(Path(__file__).resolve().parent), str(target_file),
            ],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        if not out.exists():
            sys.exit(f"基准盘探测失败：\n{proc.stderr[-1200:]}")
        return json.loads(out.read_text(encoding="utf-8"))


def load_activation(tree: Path) -> dict[str, bool]:
    """规则的激活状态。新写谓词按定义未激活，报告里要区分「未激活」和「写错了」。"""
    index = tree / "references" / "index" / "evidence-rules.jsonl"
    states: dict[str, bool] = {}
    for line in index.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            states[row["rule_id"]] = bool(row.get("runtime_active"))
    return states


def addressable(predicate: dict[str, Any], available: set[str]) -> bool:
    """镜像 evidence_rules._predicate_fact_refs 的寻址语义。"""
    suffix = str(predicate.get("path_suffix", ""))
    nested = suffix + "/"
    if predicate.get("operator") in {
        "present", "nonempty", "descendant_eq", "same_record_fields",
    }:
        return any(p.endswith(suffix) or nested in p for p in available)
    return any(p.endswith(suffix) for p in available)


def main() -> int:
    parser = argparse.ArgumentParser(description="谓词验收")
    parser.add_argument("--route", required=True, choices=sorted(ROUTE_TO_CAPABILITY))
    parser.add_argument("--tree", default=str(DEFAULT_SOURCE_TREE),
                        help="源码树：scope YAML、编译器、规则索引的来源")
    parser.add_argument("--runtime", default=str(DEFAULT_RUNTIME),
                        help="签名 Runtime release：跑 Provider 取盘面事实")
    parser.add_argument("--python", default=str(DEFAULT_VENV_PY))
    parser.add_argument("--count", type=int, default=baseline_charts.DEFAULT_COUNT)
    parser.add_argument("--snapshot", help="把当前 route 的规则集写成基线快照后退出")
    parser.add_argument("--since", help="只验收相对该快照新增/改动的规则")
    parser.add_argument("--json", help="完整结果写到此文件")
    args = parser.parse_args()

    tree = Path(args.tree)
    runtime = Path(args.runtime)
    python = Path(args.python).expanduser()
    if not (tree / "scripts" / "build_evidence_index.py").exists():
        sys.exit(f"源码树不对（缺 build_evidence_index.py）：{tree}")
    if not (runtime / ".mingli-release-manifest.json").exists():
        sys.exit(f"签名 Runtime 不对（缺 .mingli-release-manifest.json）：{runtime}")
    if not python.exists():
        sys.exit(f"Runtime venv 不存在：{python}")

    scope = load_scope(tree, python)
    mine = {rid: b for rid, b in scope.items() if b.get("route") == args.route}
    if not mine:
        sys.exit(f"route {args.route} 下没有 scope 绑定")

    if args.snapshot:
        Path(args.snapshot).parent.mkdir(parents=True, exist_ok=True)
        Path(args.snapshot).write_text(
            json.dumps({"route": args.route, "bindings": mine}, ensure_ascii=False, indent=2,
                       sort_keys=True),
            encoding="utf-8",
        )
        print(f"基线快照已写出：{args.snapshot}（{len(mine)} 条）")
        return 0

    targets = mine
    if args.since:
        before = json.loads(Path(args.since).read_text(encoding="utf-8"))["bindings"]
        targets = {
            rid: b for rid, b in mine.items()
            if rid not in before or before[rid] != b
        }
        print(f"相对快照有 {len(targets)} 条新增/改动（route 共 {len(mine)} 条）")
        if not targets:
            print("没有需要验收的改动。")
            return 0

    print("[1/5] 编译检查 …", end=" ", flush=True)
    ok, detail = compile_check(tree, python)
    print("pass" if ok else "FAIL")
    if not ok:
        print(f"      {detail}")
        return 2

    fixtures_dir = Path(tempfile.mkdtemp())
    fixtures = fixtures_dir / "baseline.json"
    fixtures.write_text(
        json.dumps({"schema": "mingli-baseline-charts-v1",
                    "charts": baseline_charts.build(args.count)}, ensure_ascii=False),
        encoding="utf-8",
    )
    capability = ROUTE_TO_CAPABILITY[args.route]
    print(f"[2/5] 在 {args.count} 张基准盘上跑 {capability}（Runtime: {runtime}）…", flush=True)
    trace = run_tracer(runtime, python, capability, fixtures, targets)
    print(f"      prepared {trace['prepared']}/{trace['charts']}")
    if trace["failures"]:
        print(f"      注意：{len(trace['failures'])} 张盘未 prepared，样例 {trace['failures'][0]}")
    if trace["prepared"] == 0:
        print("      没有任何盘 prepared，判别力无法测量。")
        return 2

    available = set(trace["paths"])
    hits = trace["hits"]
    activation = load_activation(tree)
    denominator = trace["prepared"]

    rows: list[dict[str, Any]] = []
    for rule_id, binding in sorted(targets.items()):
        preds = list(binding.get("predicates") or [])
        preds += list(binding.get("excluded_predicates") or [])
        missing = [p["path_suffix"] for p in preds if not addressable(p, available)]
        hit = hits.get(rule_id, 0)
        rate = hit / denominator if denominator else 0.0

        # 方法论规则本身就是「只要有这类盘面就适用」的陈述，恒成立是它的正确形态；
        # 对它套判别力上限会把正确的规则误报成缺陷。豁免要显式标注，不能静默放过。
        role = str(binding.get("evidence_role") or "issue_specific_judgment_rule")
        exempt = role in {"methodology_rule", "terminology_only", "edition_boundary"}

        problems = []
        if missing:
            problems.append(f"路径不可寻址 {missing}")
        elif hit == 0:
            problems.append(
                f"在 {denominator} 张基准盘上均不成立。三种可能："
                "①条件组合在术数上不存在（如「紫府同宫在丑」——实际只在寅申）；"
                "②路径对但取值字符串错；③确实极罕见，用更大的 --count 复测"
            )
        elif rate > HIT_CEILING and not exempt:
            problems.append(f"成立率 {rate:.0%} 超过 {HIT_CEILING:.0%}，是存在性检查而非条件判别")
        rows.append({
            "rule_id": rule_id, "hit": hit, "denominator": denominator,
            "rate": round(rate, 4), "missing_paths": missing,
            "predicates": len(preds), "problems": problems,
            "runtime_active": activation.get(rule_id, False),
            "evidence_role": role, "discrimination_exempt": exempt,
        })

    print(f"[3/5] 路径与判别力 … {sum(1 for r in rows if not r['problems'])}/{len(rows)} 通过")
    print("[4/5] 越界扫描 …", end=" ", flush=True)
    violations = trace["verdict_violations"]
    print("clean" if not violations else f"FAIL（{len(violations)} 张盘出现 verdict）")
    print("[5/5] 汇总\n")

    print(f"{'规则':<44}{'谓词':>4}{'成立':>8}{'成立率':>8} {'激活':>5}  判定")
    print("-" * 92)
    for row in rows:
        verdict = "✓" if not row["problems"] else "✗"
        if not row["problems"] and row["discrimination_exempt"] and row["rate"] > HIT_CEILING:
            verdict = "✓ 豁免"   # methodology_rule 恒成立是正确形态
        active = "是" if row["runtime_active"] else "待核对"
        print(f"{row['rule_id']:<44}{row['predicates']:>4}"
              f"{row['hit']:>5}/{row['denominator']:<3}{row['rate']:>7.0%} {active:>5}  {verdict}")
        for problem in row["problems"]:
            print(f"{'':<44}     └ {problem}")

    failed = [r for r in rows if r["problems"]]
    print()
    print(f"通过 {len(rows) - len(failed)} / {len(rows)}")
    if violations:
        print(f"越界：{violations[0]}")
    print("\n第 4 项（引文真实）用 verify_citation.py；第 6 项（谓词是否忠实表达原文）必须人工复核。")

    if args.json:
        Path(args.json).write_text(
            json.dumps({"route": args.route, "rows": rows,
                        "verdict_violations": violations,
                        "available_paths": len(available)},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"完整结果：{args.json}")

    return 1 if (failed or violations) else 0


if __name__ == "__main__":
    raise SystemExit(main())

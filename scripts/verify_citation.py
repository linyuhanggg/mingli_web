#!/usr/bin/env python3
"""古籍引文核验：全文逐字核验，或签名发行物引用绑定核验。

用法：
    python3 scripts/verify_citation.py "偏财源活，最宜食伤生扶；忌比劫劫夺" --claim ziping-zhenquan
    python3 scripts/verify_citation.py --file claims.txt --json
    python3 scripts/verify_citation.py --mode release-bound \
      --release-root .runtime/v53-time-check-release \
      --file vertical-result.json --citations-file citations.txt

判定：
    verified_exact   规范化后在全文库中逐字命中
    partial_match    未逐字命中，但存在高相似段落（疑似转述/改写）
    not_found        全库无对应原文

规范化只做「繁简统一 + 去标点空白」，不做同义替换；命中即可回到
`path#Lnnn` 复核原文，不命中不做任何推断。

繁简转换依赖 zhconv（`pip install zhconv`）。缺失时脚本拒绝出具判定，
不用简体 grep 冒充全库核验——繁体正文会被静默漏掉。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

# 发行包默认位置：优先 codex，其次 claude；均可用 --root 覆盖。
DEFAULT_ROOTS = (
    Path.home() / ".codex" / "skills" / "mingli-master",
    Path.home() / ".claude" / "skills" / "mingli-master",
)

NGRAM = 3
PARTIAL_THRESHOLD = 0.55  # 3-gram 包含率达到此值才报 partial_match
TOP_K = 3

_PUNCT = re.compile(r"[\s，。、；：！？「」『』（）()《》〈〉…—·,.;:!?\"'\[\]【】]+")


def _load_converter():
    try:
        from zhconv import convert
    except ImportError:
        sys.exit(
            "缺少 zhconv：pip install zhconv\n"
            "（全文库含繁体正文，无转换时核验结果不可信，故直接退出。）"
        )
    return lambda text: convert(text, "zh-cn")


def normalize(text: str, to_simplified) -> str:
    return _PUNCT.sub("", to_simplified(text))


def ngrams(text: str, n: int = NGRAM) -> set[str]:
    if len(text) < n:
        return {text} if text else set()
    return {text[i : i + n] for i in range(len(text) - n + 1)}


@dataclass
class Passage:
    pack: str  # 如 bazi/ziping-zhenquan
    title: str  # 书名（取全文首个一级标题）
    path: str  # 相对发行包根的路径
    line: int
    raw: str
    norm: str


@dataclass
class Match:
    pack: str
    title: str
    anchor: str  # path#Lnnn
    containment: float
    text: str


@dataclass
class Verdict:
    quote: str
    status: str
    claimed_pack: str | None
    found_in_claimed: bool
    matches: list[dict]
    note: str


@dataclass
class ReleaseBoundVerdict:
    evidence_ref: str
    excerpt: str
    locator: str
    status: str
    rule_id: str | None
    source_path: str | None
    source_sha256: str | None
    verbatim_quote_sha256: str | None
    note: str


def load_passages(root: Path, to_simplified) -> list[Passage]:
    fulltext_root = root / "references" / "fulltext"
    if not fulltext_root.is_dir():
        sys.exit(f"找不到全文库：{fulltext_root}")
    passages: list[Passage] = []
    for path in sorted(fulltext_root.rglob("fulltext.md")):
        pack = f"{path.parent.parent.name}/{path.parent.name}"
        title = pack
        lines = path.read_text(encoding="utf-8").splitlines()
        for number, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("# ") and title == pack:
                title = stripped[2:].strip()
            if stripped.startswith(("- source_url:", "```")):
                continue
            norm = normalize(stripped.lstrip("#>- "), to_simplified)
            if len(norm) < NGRAM:
                continue
            passages.append(
                Passage(
                    pack=pack,
                    title=title,
                    path=str(path.relative_to(root)),
                    line=number,
                    raw=stripped,
                    norm=norm,
                )
            )
    if not passages:
        sys.exit("全文库为空")
    return passages


def verify(
    quote: str,
    passages: list[Passage],
    to_simplified,
    claimed_pack: str | None = None,
) -> Verdict:
    target = normalize(quote, to_simplified)
    if len(target) < NGRAM:
        return Verdict(quote, "not_found", claimed_pack, False, [], "引文过短，无法核验")

    exact = [p for p in passages if target in p.norm]
    if exact:
        matches = [Match(p.pack, p.title, f"{p.path}#L{p.line}", 1.0, p.raw) for p in exact[:TOP_K]]
        in_claimed = _in_claimed(exact, claimed_pack)
        return Verdict(
            quote,
            "verified_exact",
            claimed_pack,
            in_claimed,
            [asdict(m) for m in matches],
            "逐字命中"
            if in_claimed or not claimed_pack
            else f"逐字命中，但不在声称的出处 {claimed_pack} 内",
        )

    target_grams = ngrams(target)
    scored: list[tuple[float, Passage]] = []
    for p in passages:
        common = target_grams & ngrams(p.norm)
        if not common:
            continue
        scored.append((len(common) / len(target_grams), p))
    scored.sort(key=lambda item: (-item[0], item[1].pack, item[1].line))

    top = scored[:TOP_K]
    matches = [
        Match(p.pack, p.title, f"{p.path}#L{p.line}", round(score, 3), p.raw) for score, p in top
    ]
    best = top[0][0] if top else 0.0
    if best >= PARTIAL_THRESHOLD:
        status, note = (
            "partial_match",
            (f"未逐字命中；最高 3-gram 包含率 {best:.0%}，疑为转述或改写，请人工比对原文"),
        )
    else:
        status, note = "not_found", (f"全库无对应原文（最高 3-gram 包含率仅 {best:.0%}）")
    return Verdict(
        quote,
        status,
        claimed_pack,
        _in_claimed([p for _, p in top], claimed_pack),
        [asdict(m) for m in matches],
        note,
    )


def _in_claimed(passages: list[Passage], claimed_pack: str | None) -> bool:
    if not claimed_pack:
        return False
    return any(claimed_pack in p.pack for p in passages)


def render(verdict: Verdict) -> str:
    icon = {"verified_exact": "✅", "partial_match": "⚠️ ", "not_found": "❌"}[verdict.status]
    out = [f"{icon} {verdict.status}  「{verdict.quote}」", f"   {verdict.note}"]
    if verdict.claimed_pack:
        mark = "命中" if verdict.found_in_claimed else "未命中"
        out.append(f"   声称出处 {verdict.claimed_pack}：{mark}")
    for m in verdict.matches:
        out.append(f"   · [{m['containment']:.0%}] {m['title']}  {m['anchor']}")
        out.append(f"       {m['text'][:110]}")
    return "\n".join(out)


def render_release_bound(verdict: ReleaseBoundVerdict) -> str:
    icon = "✅" if verdict.status == "verified_release_bound" else "❌"
    out = [
        f"{icon} {verdict.status}  {verdict.evidence_ref}",
        f"   {verdict.note}",
    ]
    if verdict.source_path and verdict.source_sha256:
        out.append(f"   · {verdict.source_path}  sha256={verdict.source_sha256}")
    if verdict.locator:
        out.append(f"   · locator={verdict.locator}")
    return "\n".join(out)


def _missing_fulltext_message(targets: list[Path]) -> str:
    checked = "\n".join(f"  - {target}" for target in targets)
    return (
        "找不到独立授权的 mingli-master 全文库。已检查：\n"
        f"{checked}\n"
        "请安装全文语料，或用 --root <mingli-master-root> 指定其根目录。\n"
        "可直接复制的复核命令：\n"
        "PYTHONDONTWRITEBYTECODE=1 \\\n"
        "PYTHONPATH=.runtime/backups/2026-08-18-g1-resign/runtime-extras \\\n"
        "~/.local/share/mingli-master/venv/bin/python -B "
        "scripts/verify_citation.py --root <mingli-master-root> "
        "--file <引文清单>.txt"
    )


def resolve_root(explicit: str | None) -> Path:
    if explicit:
        root = Path(explicit).expanduser()
        fulltext_root = root / "references" / "fulltext"
        if fulltext_root.is_dir():
            return root
        sys.exit(_missing_fulltext_message([fulltext_root]))
    for candidate in DEFAULT_ROOTS:
        if (candidate / "references" / "fulltext").is_dir():
            return candidate
    sys.exit(
        _missing_fulltext_message(
            [candidate / "references" / "fulltext" for candidate in DEFAULT_ROOTS]
        )
    )


def resolve_release_root(explicit: str | None) -> Path:
    if not explicit:
        sys.exit("release-bound 模式必须提供 --release-root <path>")
    root = Path(explicit).expanduser()
    index_path = root / "references" / "index" / "evidence-rules.jsonl"
    if not index_path.is_file():
        sys.exit(f"找不到签名发行物规则索引：{index_path}")
    return root


def load_release_index(root: Path) -> dict[str, dict[str, Any]]:
    index_path = root / "references" / "index" / "evidence-rules.jsonl"
    records: dict[str, dict[str, Any]] = {}
    for number, line in enumerate(index_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            sys.exit(f"规则索引第 {number} 行不是合法 JSON：{exc}")
        rule_id = record.get("rule_id")
        if not isinstance(rule_id, str) or not rule_id:
            sys.exit(f"规则索引第 {number} 行缺少 rule_id")
        if rule_id in records:
            sys.exit(f"规则索引包含重复 rule_id：{rule_id}")
        records[rule_id] = record
    if not records:
        sys.exit(f"签名发行物规则索引为空：{index_path}")
    return records


def _extract_release_evidence(payload: object) -> object | None:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return None
    if isinstance(payload.get("evidence"), list):
        return payload["evidence"]
    result = payload.get("result")
    if isinstance(result, dict) and isinstance(result.get("evidence"), list):
        return result["evidence"]
    fact_panel = payload.get("fact_panel")
    if isinstance(fact_panel, dict) and isinstance(fact_panel.get("evidence"), list):
        return fact_panel["evidence"]
    return None


def load_release_evidence(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        sys.exit(f"无法读取 release-bound evidence JSON：{path}：{exc}")

    evidence = _extract_release_evidence(payload)
    if evidence is None:
        sys.exit(
            "release-bound evidence JSON 必须是 evidence 数组，"
            "或包含 result.evidence / fact_panel.evidence 数组"
        )
    if not evidence:
        sys.exit("release-bound evidence 清单为空")
    if not all(isinstance(item, dict) for item in evidence):
        sys.exit("release-bound evidence 每一项都必须是对象")
    return evidence


def assert_citations_match(evidence: list[dict[str, Any]], citations_path: Path) -> None:
    citations = [
        line.strip()
        for line in citations_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    excerpts = [item.get("excerpt") for item in evidence]
    if citations != excerpts:
        sys.exit(
            f"引文清单与页面 evidence 不逐行一致：{citations_path} "
            f"({len(citations)} 行) != evidence ({len(excerpts)} 条)"
        )


def _release_failure(
    evidence_ref: object,
    excerpt: object,
    locator: object,
    note: str,
    rule_id: str | None = None,
) -> ReleaseBoundVerdict:
    return ReleaseBoundVerdict(
        evidence_ref=evidence_ref if isinstance(evidence_ref, str) else "",
        excerpt=excerpt if isinstance(excerpt, str) else "",
        locator=locator if isinstance(locator, str) else "",
        status="release_binding_failed",
        rule_id=rule_id,
        source_path=None,
        source_sha256=None,
        verbatim_quote_sha256=None,
        note=note,
    )


def verify_release_bound(
    evidence: dict[str, Any], records: dict[str, dict[str, Any]]
) -> ReleaseBoundVerdict:
    evidence_ref = evidence.get("evidence_ref")
    excerpt = evidence.get("excerpt")
    locator = evidence.get("locator")
    if not all(isinstance(value, str) and value for value in (evidence_ref, excerpt, locator)):
        return _release_failure(
            evidence_ref, excerpt, locator, "evidence_ref / excerpt / locator 必须完整"
        )

    payload = evidence_ref.removeprefix("evidence:")
    if payload == evidence_ref or "/" not in payload:
        return _release_failure(evidence_ref, excerpt, locator, "evidence_ref 格式无效")
    system, rule_id = payload.split("/", 1)
    if not system or not rule_id:
        return _release_failure(evidence_ref, excerpt, locator, "evidence_ref 格式无效")

    record = records.get(rule_id)
    if record is None:
        return _release_failure(
            evidence_ref,
            excerpt,
            locator,
            f"规则索引中找不到 rule_id：{rule_id}",
            rule_id,
        )
    if record.get("system") != system:
        return _release_failure(
            evidence_ref,
            excerpt,
            locator,
            f"evidence_ref system 与规则记录不一致：{system}",
            rule_id,
        )

    sources = record.get("classical_sources")
    if not isinstance(sources, list) or not sources:
        return _release_failure(
            evidence_ref, excerpt, locator, "对应规则没有 classical_sources", rule_id
        )
    quote_matches = [
        source
        for source in sources
        if isinstance(source, dict) and source.get("verbatim_quote") == excerpt
    ]
    if not quote_matches:
        return _release_failure(
            evidence_ref,
            excerpt,
            locator,
            "页面 excerpt 与对应规则的 verbatim_quote 不逐字相等",
            rule_id,
        )
    locator_matches = [source for source in quote_matches if source.get("anchor") == locator]
    if not locator_matches:
        return _release_failure(
            evidence_ref,
            excerpt,
            locator,
            "页面 locator 与对应 verbatim_quote 的 anchor 不一致",
            rule_id,
        )

    source = locator_matches[0]
    quote_digest = source.get("verbatim_quote_sha256")
    actual_digest = sha256(excerpt.encode("utf-8")).hexdigest()
    if not isinstance(quote_digest, str) or actual_digest != quote_digest:
        return _release_failure(
            evidence_ref,
            excerpt,
            locator,
            "verbatim_quote_sha256 校验失败",
            rule_id,
        )
    source_path = source.get("path")
    source_digest = source.get("sha256")
    if not isinstance(source_path, str) or not source_path:
        return _release_failure(
            evidence_ref, excerpt, locator, "classical source 缺少 path", rule_id
        )
    if not isinstance(source_digest, str) or not source_digest:
        return _release_failure(
            evidence_ref, excerpt, locator, "classical source 缺少 sha256", rule_id
        )

    return ReleaseBoundVerdict(
        evidence_ref=evidence_ref,
        excerpt=excerpt,
        locator=locator,
        status="verified_release_bound",
        rule_id=rule_id,
        source_path=source_path,
        source_sha256=source_digest,
        verbatim_quote_sha256=quote_digest,
        note="发行记录已闭合第 1–3 步；未读取外部全文，不代表第 4 步 verified_exact",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="古籍引文核验")
    parser.add_argument("quote", nargs="?", help="待核验的引文")
    parser.add_argument(
        "--mode",
        choices=("fulltext", "release-bound"),
        default="fulltext",
        help="fulltext 查外部全文；release-bound 只核验签名发行记录第 1–3 步",
    )
    parser.add_argument(
        "--file",
        help="fulltext：每行一句引文；release-bound：页面 evidence JSON",
    )
    parser.add_argument("--claim", help="声称的出处 pack，如 ziping-zhenquan")
    parser.add_argument("--root", help="发行包根目录")
    parser.add_argument("--release-root", help="签名 Runtime release 根目录")
    parser.add_argument(
        "--citations-file",
        help="release-bound 可选：断言该逐行引文清单与 evidence excerpt 完全一致",
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    if args.mode == "release-bound":
        if args.quote or not args.file:
            parser.error("release-bound 模式需要 --file <页面 evidence JSON>")
        release_root = resolve_release_root(args.release_root)
        evidence = load_release_evidence(Path(args.file))
        if args.citations_file:
            assert_citations_match(evidence, Path(args.citations_file))
        records = load_release_index(release_root)
        verdicts = [verify_release_bound(item, records) for item in evidence]
        if args.json:
            print(
                json.dumps(
                    [asdict(verdict) for verdict in verdicts],
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(f"发行绑定索引：{len(records)} 条规则 / {len(verdicts)} 条页面引文\n")
            for verdict in verdicts:
                print(render_release_bound(verdict))
                print()
        return 0 if all(verdict.status == "verified_release_bound" for verdict in verdicts) else 1

    if not args.quote and not args.file:
        parser.error("fulltext 模式需要提供引文或 --file")

    root = resolve_root(args.root)
    to_simplified = _load_converter()
    passages = load_passages(root, to_simplified)

    quotes = (
        [args.quote]
        if args.quote
        else [
            line.strip()
            for line in Path(args.file).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    )
    verdicts = [verify(q, passages, to_simplified, args.claim) for q in quotes]

    if args.json:
        print(json.dumps([asdict(v) for v in verdicts], ensure_ascii=False, indent=2))
    else:
        print(f"全文库：{len({p.pack for p in passages})} 部典籍 / {len(passages)} 段\n")
        for v in verdicts:
            print(render(v))
            print()
    return 0 if all(v.status == "verified_exact" for v in verdicts) else 1


if __name__ == "__main__":
    raise SystemExit(main())

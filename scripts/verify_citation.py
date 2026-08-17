#!/usr/bin/env python3
"""引文核验：给定一句声称的古籍引文，在发行包全文库中查证真伪。

用法：
    python3 scripts/verify_citation.py "偏财源活，最宜食伤生扶；忌比劫劫夺" --claim ziping-zhenquan
    python3 scripts/verify_citation.py --file claims.txt --json

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
from dataclasses import dataclass, asdict
from pathlib import Path

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
    pack: str          # 如 bazi/ziping-zhenquan
    title: str         # 书名（取全文首个一级标题）
    path: str          # 相对发行包根的路径
    line: int
    raw: str
    norm: str


@dataclass
class Match:
    pack: str
    title: str
    anchor: str        # path#Lnnn
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
        matches = [
            Match(p.pack, p.title, f"{p.path}#L{p.line}", 1.0, p.raw) for p in exact[:TOP_K]
        ]
        in_claimed = _in_claimed(exact, claimed_pack)
        return Verdict(
            quote,
            "verified_exact",
            claimed_pack,
            in_claimed,
            [asdict(m) for m in matches],
            "逐字命中" if in_claimed or not claimed_pack
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
        Match(p.pack, p.title, f"{p.path}#L{p.line}", round(score, 3), p.raw)
        for score, p in top
    ]
    best = top[0][0] if top else 0.0
    if best >= PARTIAL_THRESHOLD:
        status, note = "partial_match", (
            f"未逐字命中；最高 3-gram 包含率 {best:.0%}，疑为转述或改写，请人工比对原文"
        )
    else:
        status, note = "not_found", (
            f"全库无对应原文（最高 3-gram 包含率仅 {best:.0%}）"
        )
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


def resolve_root(explicit: str | None) -> Path:
    if explicit:
        root = Path(explicit).expanduser()
        if not root.is_dir():
            sys.exit(f"发行包不存在：{root}")
        return root
    for candidate in DEFAULT_ROOTS:
        if (candidate / "references" / "fulltext").is_dir():
            return candidate
    sys.exit("未找到 mingli-master 发行包，请用 --root 指定")


def main() -> int:
    parser = argparse.ArgumentParser(description="古籍引文核验")
    parser.add_argument("quote", nargs="?", help="待核验的引文")
    parser.add_argument("--file", help="批量核验：每行一句引文")
    parser.add_argument("--claim", help="声称的出处 pack，如 ziping-zhenquan")
    parser.add_argument("--root", help="发行包根目录")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    if not args.quote and not args.file:
        parser.error("需要提供引文或 --file")

    to_simplified = _load_converter()
    passages = load_passages(resolve_root(args.root), to_simplified)

    quotes = [args.quote] if args.quote else [
        line.strip()
        for line in Path(args.file).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
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

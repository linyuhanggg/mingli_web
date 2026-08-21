#!/usr/bin/env python3
"""Read-only: P10-013 解梦 / 姓名 — signed V53 vs core."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path("/Volumes/Lexar/code/mingli_web")
SIGNED = ROOT / ".runtime/v53-time-check-release"
CORE = ROOT / "core/mingli-master"

NEEDLE = re.compile(r"(dream|jiemeng|解梦|姓名学|姓名分析|onomanc|name-analysis|name_analysis)", re.I)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def claim_ids(path: Path) -> list[str]:
    return re.findall(r'"claim_unit_id":\s*"([^"]+)"', path.read_text(encoding="utf-8"))


def provider_ids(root: Path) -> list[str]:
    return sorted(p.stem for p in (root / "resources/runtime/providers").glob("*.json"))


def catalog_hits(root: Path) -> bool:
    p = root / "resources/runtime/catalog-v1.json"
    return bool(NEEDLE.search(p.read_text(encoding="utf-8")))


def rule_hits(path: Path) -> list[str]:
    out: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        blob = json.dumps(row, ensure_ascii=False)
        if NEEDLE.search(blob):
            out.append(str(row.get("rule_id")))
    return out


def fixture_names(root: Path) -> list[str]:
    fx = root / "references/fixtures"
    if not fx.exists():
        return []
    return sorted(p.name for p in fx.iterdir() if NEEDLE.search(p.name))


def main() -> int:
    man = SIGNED / ".mingli-release-manifest.json"
    inspector = hashlib.sha256(man.read_bytes()).hexdigest()
    manj = json.loads(man.read_bytes())
    nfiles = len(manj.get("files") or {})
    signed_provs = provider_ids(SIGNED)
    core_provs = provider_ids(CORE)
    signed_cu = claim_ids(SIGNED / "scripts/reading_engine/providers.py")
    core_cu = claim_ids(CORE / "scripts/reading_engine/providers.py")
    dream_name_cu_signed = [x for x in signed_cu if NEEDLE.search(x)]
    dream_name_cu_core = [x for x in core_cu if NEEDLE.search(x)]
    rules = rule_hits(SIGNED / "references/index/evidence-rules.jsonl")
    n_rules = sum(1 for line in (SIGNED / "references/index/evidence-rules.jsonl").read_text(encoding="utf-8").splitlines() if line.strip())
    signed_fx = fixture_names(SIGNED)
    core_fx = fixture_names(CORE)
    extra_core_provs = sorted(set(core_provs) - set(signed_provs))
    extra_signed_provs = sorted(set(signed_provs) - set(core_provs))
    shensha = CORE / "references/matrices/shensha-name-disambiguation.yaml"
    shensha_signed = (SIGNED / "references/matrices/shensha-name-disambiguation.yaml").exists()
    prepares = [
        Path("/tmp/mingli-oneshot-v53-time-check-20260819/out/prepare.stdout.json"),
        Path("/Volumes/Lexar/code/mingli_web/.runtime/oneshot-20260819-claim-unit/prepare-out.json"),
        Path("/tmp/mingli-oneshot-v53-fixture2-20260819/out/prepare.stdout.json"),
    ]
    prepare_hits = {}
    for p in prepares:
        prepare_hits[str(p)] = bool(NEEDLE.search(p.read_text(encoding="utf-8"))) if p.exists() else None

    print(f"inspector={inspector}")
    print(f"source_commit={manj.get('source_commit')}")
    print(f"files={nfiles}")
    print(f"signed_providers={signed_provs}")
    print(f"core_providers={core_provs}")
    print(f"has_dream_or_name_provider={('dream' in signed_provs) or ('name' in signed_provs) or ('jiemeng' in signed_provs)}")
    print(f"extra_core_providers={extra_core_provs}")
    print(f"extra_signed_providers={extra_signed_provs}")
    print(f"signed_cu={signed_cu}")
    print(f"dream_name_cu_signed={dream_name_cu_signed}")
    print(f"dream_name_cu_core={dream_name_cu_core}")
    print(f"evidence_rules_total={n_rules}")
    print(f"dream_name_rule_hits={rules}")
    print(f"signed_catalog_hits={catalog_hits(SIGNED)}")
    print(f"core_catalog_hits={catalog_hits(CORE)}")
    print(f"golden_fixture_in_signed={signed_fx}")
    print(f"golden_fixture_in_core={core_fx}")
    print(f"shensha_name_disambiguation_core={shensha.exists()}")
    print(f"shensha_name_disambiguation_signed={shensha_signed}")
    print(f"prepare_dream_name_hits={prepare_hits}")
    print(f"prepare_any_hit={any(v for v in prepare_hits.values() if v)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

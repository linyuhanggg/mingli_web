#!/usr/bin/env python3
"""Read-only: 寻时定盘 / time-check — signed V53 vs core."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path("/Volumes/Lexar/code/mingli_web")
SIGNED = ROOT / ".runtime/v53-time-check-release"
CORE = ROOT / "core/mingli-master"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def claim_ids(path: Path) -> list[str]:
    return re.findall(r'"claim_unit_id":\s*"([^"]+)"', path.read_text(encoding="utf-8"))


def extract_class(text: str, name: str = "class TimeCheckProvider") -> str:
    i = text.find(name)
    if i < 0:
        return ""
    rest = text[i:]
    m = re.search(r"\nclass ", rest[1:])
    return rest if not m else rest[: m.start() + 1]


def main() -> int:
    man = json.loads((SIGNED / ".mingli-release-manifest.json").read_bytes())
    inspector = hashlib.sha256((SIGNED / ".mingli-release-manifest.json").read_bytes()).hexdigest()
    signed_cu = claim_ids(SIGNED / "scripts/reading_engine/providers.py")
    core_cu = claim_ids(CORE / "scripts/reading_engine/providers.py")
    j = json.loads((SIGNED / "resources/runtime/providers/time-check.json").read_text(encoding="utf-8"))
    outs = [b.get("name") for b in (j.get("runtime_capability") or {}).get("output_bindings") or []]
    signed_body = extract_class((SIGNED / "scripts/reading_engine/providers.py").read_text(encoding="utf-8"))
    core_body = extract_class((CORE / "scripts/reading_engine/providers.py").read_text(encoding="utf-8"))
    n_rules = 0
    rule_hits = []
    for line in (SIGNED / "references/index/evidence-rules.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        n_rules += 1
        row = json.loads(line)
        blob = json.dumps(row, ensure_ascii=False)
        if re.search(r"(time-check|time_check|寻时|校时)", blob):
            rule_hits.append(row.get("rule_id"))
    brief = (SIGNED / "scripts/reading_engine/brief.py").read_text(encoding="utf-8")
    print(f"inspector={inspector}")
    print(f"source_commit={man.get('source_commit')}")
    print(f"files={len(man.get('files') or {})}")
    print(f"release_name=v53-time-check-release")
    print(f"provider_id={j.get('id')}")
    print(f"entrypoint={j.get('entrypoint')}")
    print(f"evidence_profile_id={j.get('evidence_profile_id')}")
    print(f"finding_bindings={j.get('finding_bindings')}")
    print(f"output_bindings={outs}")
    print(f"json_identical={sha(SIGNED / 'resources/runtime/providers/time-check.json') == sha(CORE / 'resources/runtime/providers/time-check.json')}")
    print(f"TimeCheckProvider_identical={signed_body == core_body}")
    print(f"calendar_core_identical={sha(SIGNED / 'scripts/reading_engine/calendar_core.py') == sha(CORE / 'scripts/reading_engine/calendar_core.py')}")
    print(f"brief_identical={sha(SIGNED / 'scripts/reading_engine/brief.py') == sha(CORE / 'scripts/reading_engine/brief.py')}")
    print(f"time_check_cu_signed={[x for x in signed_cu if 'time' in x or 'xun' in x]}")
    print(f"time_check_cu_core={[x for x in core_cu if 'time' in x or 'xun' in x]}")
    print(f"evidence_rules_total={n_rules}")
    print(f"time_check_rule_hits={rule_hits}")
    print(f"brief_time_check_hits={len(re.findall(r'time.check|time_check|寻时', brief, re.I))}")
    print(f"golden_fixture_signed={(SIGNED / 'references/fixtures').exists()}")
    print(f"TimeCheckProvider_claim_unit={signed_body.count('claim_unit')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

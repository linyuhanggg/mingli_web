#!/usr/bin/env python3
"""Read-only: 运势 / fortune — signed V53 vs core."""
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


def extract_class(text: str, name: str = "class FortuneProvider") -> str:
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
    j = json.loads((SIGNED / "resources/runtime/providers/fortune.json").read_text(encoding="utf-8"))
    outs = [b.get("name") for b in (j.get("runtime_capability") or {}).get("output_bindings") or []]
    signed_body = extract_class((SIGNED / "scripts/reading_engine/providers.py").read_text(encoding="utf-8"))
    core_body = extract_class((CORE / "scripts/reading_engine/providers.py").read_text(encoding="utf-8"))
    n_rules = 0
    pack_hits = []
    for line in (SIGNED / "references/index/evidence-rules.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        n_rules += 1
        row = json.loads(line)
        pack = str(row.get("source_pack") or "")
        if pack.startswith("fortune"):
            pack_hits.append(row.get("rule_id"))
    brief = (SIGNED / "scripts/reading_engine/brief.py").read_text(encoding="utf-8")
    fx = CORE / "references/fixtures/fortune-v51.yaml"
    bfx = CORE / "references/fixtures/bazi-fortune-v51.yaml"
    fx_ids = len(re.findall(r"\bid:", fx.read_text(encoding="utf-8"))) if fx.exists() else 0
    bfx_ids = len(re.findall(r"- id:", bfx.read_text(encoding="utf-8"))) if bfx.exists() else 0
    print(f"inspector={inspector}")
    print(f"source_commit={man.get('source_commit')}")
    print(f"files={len(man.get('files') or {})}")
    print(f"provider_id={j.get('id')}")
    print(f"entrypoint={j.get('entrypoint')}")
    print(f"evidence_profile_id={j.get('evidence_profile_id')}")
    print(f"finding_bindings={j.get('finding_bindings')}")
    print(f"output_bindings={outs}")
    print(f"extension_outputs={(j.get('runtime_capability') or {}).get('extension_outputs')}")
    print(f"json_identical={sha(SIGNED / 'resources/runtime/providers/fortune.json') == sha(CORE / 'resources/runtime/providers/fortune.json')}")
    print(f"adapter_identical={sha(SIGNED / 'scripts/near_time_fortune_adapter.py') == sha(CORE / 'scripts/near_time_fortune_adapter.py')}")
    print(f"FortuneProvider_identical={signed_body == core_body}")
    print(f"fortune_calc_signed={(SIGNED / 'scripts/fortune_calc.py').exists()}")
    print(f"fortune_calc_core={(CORE / 'scripts/fortune_calc.py').exists()}")
    print(f"fortune_cu_signed={[x for x in signed_cu if 'fortune' in x]}")
    print(f"fortune_cu_core={[x for x in core_cu if 'fortune' in x]}")
    print(f"evidence_rules_total={n_rules}")
    print(f"fortune_pack_rule_hits={pack_hits}")
    print(f"brief_fortune_hits={len(re.findall(r'fortune|运势', brief, re.I))}")
    print(f"FortuneProvider_claim_unit={signed_body.count('claim_unit')}")
    print(f"golden_fixture_signed={(SIGNED / 'references/fixtures').exists()}")
    print(f"fortune_v51_core_ids={fx_ids}")
    print(f"bazi_fortune_v51_core_ids={bfx_ids}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

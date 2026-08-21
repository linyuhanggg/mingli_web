#!/usr/bin/env python3
"""P10-001 harvest re-confirm on signed V53 (c451de5e). Read-only. No resign."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

SIGNED = Path("/Volumes/Lexar/code/mingli_web/.runtime/v53-time-check-release")
CORE = Path("/Volumes/Lexar/code/mingli_web/core/mingli-master")
MANIFEST = SIGNED / ".mingli-release-manifest.json"
SIGNED_PROVIDERS = SIGNED / "scripts" / "reading_engine" / "providers.py"
CORE_PROVIDERS = CORE / "scripts" / "reading_engine" / "providers.py"
PREPARE_1994 = Path("/tmp/mingli-oneshot-v53-time-check-20260819/out/prepare.stdout.json")
DESCRIBE_1994 = Path("/tmp/mingli-oneshot-v53-time-check-20260819/out/describe.stdout.json")
ROOT_ID = "bazi.day-master-root-support-v1"
DR = "bazi/ditiansui-chanwei#DR-01-01"


def _claim_unit_ids(providers_path: Path) -> list[str]:
    tree = ast.parse(providers_path.read_text(encoding="utf-8"))
    ids: list[str] = []
    seen: set[str] = set()
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name != "_bazi_public_claim_findings":
            continue
        for sub in ast.walk(node):
            if not isinstance(sub, ast.Dict):
                continue
            for key, value in zip(sub.keys, sub.values):
                if (
                    isinstance(key, ast.Constant)
                    and key.value == "claim_unit_id"
                    and isinstance(value, ast.Constant)
                    and isinstance(value.value, str)
                    and value.value not in seen
                ):
                    seen.add(value.value)
                    ids.append(value.value)
    return ids


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    man_raw = MANIFEST.read_bytes()
    man = json.loads(man_raw)
    signed_ids = _claim_unit_ids(SIGNED_PROVIDERS)
    core_ids = _claim_unit_ids(CORE_PROVIDERS)
    signed_src = SIGNED_PROVIDERS.read_text(encoding="utf-8")
    core_src = CORE_PROVIDERS.read_text(encoding="utf-8")

    prep = json.loads(PREPARE_1994.read_text(encoding="utf-8"))
    evidence = prep["brief"]["evidence"]
    evidence_ids = [e.get("rule_id") for e in evidence]
    findings_ids = []
    for finding in prep["brief"]["findings"]:
        data = finding.get("data") or {}
        cid = data.get("claim_unit_id")
        if cid:
            findings_ids.append(cid)

    fact_refs = [f.get("ref", "") for f in prep["brief"]["facts"]]
    calc_suffixes = []
    for ref in fact_refs:
        marker = "/calculated/bazi/"
        if marker in ref:
            calc_suffixes.append(ref.split(marker, 1)[1])

    desc = json.loads(DESCRIBE_1994.read_text(encoding="utf-8"))
    cap_ids = [c.get("id") for c in desc.get("capabilities") or []]
    provider_jsons = sorted(
        p.name for p in (SIGNED / "resources" / "runtime" / "providers").glob("*.json")
    )

    turns = (SIGNED / "scripts" / "reading_engine" / "turns.py").read_text(encoding="utf-8")
    core_turns = (CORE / "scripts" / "reading_engine" / "turns.py").read_text(encoding="utf-8")

    print("=== IDENTITY ===")
    print(f"signed_root={SIGNED}")
    print(f"core_root={CORE}")
    print(f"signed_manifest_path={MANIFEST}")
    print(f"signed_manifest_sha256={_sha256(MANIFEST)}")
    print(f"signed_manifest_bytes={len(man_raw)}")
    print(f"signed_source_commit={man.get('source_commit')}")
    print(f"signed_n_files={len(man.get('files') or [])}")
    print(f"signed_schema_version={man.get('schema_version')}")
    print(f"signed_release={man.get('release')}")
    print(f"describe_kind={desc.get('kind')}")
    print(f"describe_manifest_digest={desc.get('manifest_digest')}")
    print(f"describe_n_capabilities={len(cap_ids)}")
    print(f"describe_capability_ids={cap_ids}")
    print(f"signed_provider_json_files={provider_jsons}")
    print(f"signed_provider_json_count={len(provider_jsons)}")

    print("=== CLAIM_UNITS ===")
    print(f"signed_providers_claim_unit_ids={signed_ids}")
    print(f"core_providers_claim_unit_ids={core_ids}")
    print(f"signed_only={[i for i in signed_ids if i not in core_ids]}")
    print(f"core_only={[i for i in core_ids if i not in signed_ids]}")
    print(f"signed_has_{ROOT_ID}={'YES' if ROOT_ID in signed_ids else 'NO'}")
    print(f"signed_providers_text_has_root={'YES' if ROOT_ID in signed_src else 'NO'}")
    print(f"core_providers_text_has_root={'YES' if ROOT_ID in core_src else 'NO'}")

    print("=== PREPARE_1994_CAREER ===")
    print(f"prepare_path={PREPARE_1994}")
    print(f"prepare_kind={prep.get('kind')}")
    print(f"prepare_query={prep['brief'].get('question')}")
    print(f"prepare_dimension_ids={prep['brief'].get('request_view', {}).get('dimension_ids')}")
    print(f"prepare_n_facts={len(prep['brief']['facts'])}")
    print(f"prepare_calculated_bazi={calc_suffixes}")
    print(f"prepare_n_evidence={len(evidence_ids)}")
    print(f"prepare_evidence_rule_ids={evidence_ids}")
    print(f"prepare_evidence_has_{DR}={'YES' if DR in evidence_ids else 'NO'}")
    print(f"prepare_findings_claim_unit_ids={findings_ids}")
    print(f"prepare_findings_has_root={'YES' if ROOT_ID in findings_ids else 'NO'}")
    print(f"prepare_facts_has_relationship_signals={'YES' if any('relationship_signals' in r for r in fact_refs) else 'NO'}")

    print("=== RELATIONSHIP_LAYER ===")
    print(f"signed_turns_has_relationship_signals={'YES' if 'relationship_signals' in turns else 'NO'}")
    print(f"core_turns_has_relationship_signals={'YES' if 'relationship_signals' in core_turns else 'NO'}")
    print(f"signed_turns_has__append_runtime_relationship={'YES' if '_append_runtime_relationship' in turns else 'NO'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

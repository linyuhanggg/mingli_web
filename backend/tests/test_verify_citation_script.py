from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "verify_citation.py"


def _run(*args: object, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(SCRIPT), *(str(arg) for arg in args)],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        check=False,
        text=True,
    )


def _write_release_bound_fixture(tmp_path: Path) -> tuple[Path, Path, dict[str, Any]]:
    quote = "干为天元，支为地元，支中所藏为人元。"
    rule_id = "bazi/ditiansui-chanwei#DR-01-01"
    release_root = tmp_path / "release"
    index_path = release_root / "references" / "index" / "evidence-rules.jsonl"
    index_path.parent.mkdir(parents=True)
    record = {
        "rule_id": rule_id,
        "system": "bazi",
        "classical_sources": [
            {
                "anchor": "fulltext.md#L11",
                "path": "references/fulltext/bazi/ditiansui-chanwei/fulltext.md",
                "sha256": "source-file-digest",
                "verbatim_quote": quote,
                "verbatim_quote_sha256": hashlib.sha256(quote.encode("utf-8")).hexdigest(),
            }
        ],
    }
    index_path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
    evidence = {
        "evidence_ref": f"evidence:bazi/{rule_id}",
        "source_title": "滴天髓阐微",
        "locator": "fulltext.md#L11",
        "excerpt": quote,
        "verification_status": "verified_exact",
    }
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text(
        json.dumps({"result": {"evidence": [evidence]}}, ensure_ascii=False),
        encoding="utf-8",
    )
    return release_root, evidence_path, evidence


def _write_evidence(path: Path, evidence: dict[str, Any]) -> None:
    path.write_text(
        json.dumps({"result": {"evidence": [evidence]}}, ensure_ascii=False),
        encoding="utf-8",
    )


def test_release_bound_is_ref_bound_and_fails_closed(tmp_path: Path) -> None:
    release_root, evidence_path, evidence = _write_release_bound_fixture(tmp_path)
    positive = _run(
        "--mode",
        "release-bound",
        "--release-root",
        release_root,
        "--file",
        evidence_path,
    )
    assert positive.returncode == 0, positive.stderr
    assert "verified_release_bound" in positive.stdout

    altered_excerpt = dict(evidence, excerpt=f"{evidence['excerpt']}改")
    _write_evidence(evidence_path, altered_excerpt)
    excerpt_result = _run(
        "--mode", "release-bound", "--release-root", release_root, "--file", evidence_path
    )
    assert excerpt_result.returncode != 0
    assert "verbatim_quote 不逐字相等" in excerpt_result.stdout

    altered_locator = dict(evidence, locator="fulltext.md#L12")
    _write_evidence(evidence_path, altered_locator)
    locator_result = _run(
        "--mode", "release-bound", "--release-root", release_root, "--file", evidence_path
    )
    assert locator_result.returncode != 0
    assert "anchor 不一致" in locator_result.stdout

    fake_ref = dict(evidence, evidence_ref="evidence:bazi/bazi/fake#NOPE")
    _write_evidence(evidence_path, fake_ref)
    ref_result = _run(
        "--mode", "release-bound", "--release-root", release_root, "--file", evidence_path
    )
    assert ref_result.returncode != 0
    assert "找不到 rule_id" in ref_result.stdout


def test_release_bound_accepts_accepted_result_fact_panel(tmp_path: Path) -> None:
    release_root, _evidence_path, evidence = _write_release_bound_fixture(tmp_path)
    accepted_path = tmp_path / "accepted-result.json"
    accepted_path.write_text(
        json.dumps(
            {
                "status": "accepted",
                "fact_panel": {"evidence": [evidence]},
                "document": {
                    "evidence": [
                        {
                            "evidence_ref": evidence["evidence_ref"],
                            "title": evidence["source_title"],
                        }
                    ]
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    citations_path = tmp_path / "citations.txt"
    citations_path.write_text(f"{evidence['excerpt']}\n", encoding="utf-8")
    result = _run(
        "--mode",
        "release-bound",
        "--release-root",
        release_root,
        "--file",
        accepted_path,
        "--citations-file",
        citations_path,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "verified_release_bound" in result.stdout


def test_fulltext_mode_stays_exact_and_missing_root_is_actionable(
    tmp_path: Path,
) -> None:
    fake_module_root = tmp_path / "pythonpath"
    fake_module_root.mkdir()
    (fake_module_root / "zhconv.py").write_text(
        "def convert(text, target):\n    return text\n", encoding="utf-8"
    )
    fulltext_root = tmp_path / "corpus"
    fulltext_path = fulltext_root / "references" / "fulltext" / "bazi" / "book" / "fulltext.md"
    fulltext_path.parent.mkdir(parents=True)
    fulltext_path.write_text("# 测试典籍\n干为天元，支为地元。\n", encoding="utf-8")
    env = {**os.environ, "PYTHONPATH": str(fake_module_root)}

    positive = _run("干为天元，支为地元。", "--root", fulltext_root, env=env)
    assert positive.returncode == 0, positive.stderr
    assert "verified_exact" in positive.stdout

    missing_root = tmp_path / "signed-release-without-fulltext"
    missing_root.mkdir()
    negative = _run("干为天元，支为地元。", "--root", missing_root)
    assert negative.returncode != 0
    assert str(missing_root / "references" / "fulltext") in negative.stderr
    assert "--root <mingli-master-root>" in negative.stderr
    assert "PYTHONPATH=.runtime/backups/2026-08-18-g1-resign/runtime-extras" in negative.stderr

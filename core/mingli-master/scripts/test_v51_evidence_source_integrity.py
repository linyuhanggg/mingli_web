"""Task 7N fail-closed evidence source-binding regressions."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import build_evidence_index
from reading_engine import evidence_rules
from reading_engine.evidence_rules import load_evidence_rules


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "references" / "index" / "evidence-rules.jsonl"
SAMPLE_RULE_ID = "bazi/ditiansui-chanwei#DR-01-01"


def _sample_record() -> dict[str, object]:
    return next(
        json.loads(line)
        for line in INDEX.read_text(encoding="utf-8").splitlines()
        if line.strip() and json.loads(line)["rule_id"] == SAMPLE_RULE_ID
    )


def _copy_required_research_sources(
    detached: Path,
    detached_research_root: Path,
) -> None:
    manifest = json.loads(
        (
            detached
            / "references/matrices/classical-evidence-bindings-v1.json"
        ).read_text(encoding="utf-8")
    )
    source_root = Path(
        os.environ.get(
            "MINGLI_RESEARCH_ROOT",
            ROOT / "__missing_external_research__",
        )
    ).resolve()
    relative_paths = {
        Path(source["path"])
        for binding in manifest["bindings"].values()
        for source in binding["classical_sources"]
        if source["location"] == "research_tree"
    }
    for relative in sorted(relative_paths):
        target = detached_research_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_root / relative, target)


class EvidenceSourceIntegrityTests(unittest.TestCase):
    def test_loader_validates_only_the_requested_system_partition(self) -> None:
        with mock.patch.object(
            evidence_rules,
            "_validate_rule",
            wraps=evidence_rules._validate_rule,
        ) as validate_rule:
            loaded = load_evidence_rules(INDEX, root=ROOT, system="ziwei")

        self.assertEqual(len(loaded), 95)
        self.assertEqual({rule.system for rule in loaded}, {"ziwei"})
        self.assertEqual(validate_rule.call_count, 95)

    def test_partition_loader_still_fails_closed_on_schema_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            index = Path(temporary) / "evidence-rules.jsonl"
            index.write_text(
                json.dumps(
                    {
                        "schema_version": "unsupported",
                        "system": "bazi",
                    },
                    separators=(",", ":"),
                )
                + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "unsupported evidence rule schema"):
                load_evidence_rules(index, root=ROOT, system="ziwei")

    def test_loader_hashes_a_shared_release_source_once(self) -> None:
        records = [
            json.loads(line)
            for line in INDEX.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ][:2]
        self.assertEqual(records[0]["source_path"], records[1]["source_path"])
        source = (ROOT / records[0]["source_path"]).resolve(strict=True)
        source_reads = 0
        original_read_bytes = Path.read_bytes

        def tracked_read_bytes(path: Path) -> bytes:
            nonlocal source_reads
            if path == source:
                source_reads += 1
            return original_read_bytes(path)

        build_evidence_index._source_rule_bindings.cache_clear()
        with tempfile.TemporaryDirectory() as temporary:
            index = Path(temporary) / "evidence-rules.jsonl"
            index.write_text(
                "".join(
                    json.dumps(
                        record,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    + "\n"
                    for record in records
                ),
                encoding="utf-8",
            )
            with mock.patch.object(Path, "read_bytes", tracked_read_bytes):
                loaded = load_evidence_rules(index, root=ROOT)

        self.assertEqual(len(loaded), 2)
        # One release digest plus one source-parser read; neither repeats for
        # the second rule that points at the same immutable source file.
        self.assertEqual(source_reads, 2)

    def test_compiler_fails_closed_when_a_research_source_tree_is_missing(self) -> None:
        source = {
            "path": "references/fulltext/bazi/qiongtong-baojian/fulltext.md",
            "sha256": "0" * 64,
            "anchor": "fulltext.md#L1",
            "verbatim_quote": "probe",
            "location": "research_tree",
        }
        with tempfile.TemporaryDirectory() as temporary:
            detached = Path(temporary) / "release"
            detached.mkdir()
            with self.assertRaisesRegex(ValueError, "research source is missing"):
                build_evidence_index._verify_research_source_if_present(
                    source,
                    root=detached,
                )

    def _load_mutation(self, mutation) -> None:
        record = copy.deepcopy(_sample_record())
        mutation(record)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "evidence-rules.jsonl"
            path.write_text(
                json.dumps(
                    record,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n",
                encoding="utf-8",
            )
            load_evidence_rules(path, root=ROOT)

    def test_loader_rejects_a_forged_quote_even_with_a_matching_new_hash(self) -> None:
        def forge(record: dict[str, object]) -> None:
            record["quote"] = "这段伪造文本从未出现在对应源码规则中。"
            record["quote_hash"] = hashlib.sha256(
                str(record["quote"]).encode("utf-8")
            ).hexdigest()

        with self.assertRaisesRegex(ValueError, "quote.*source"):
            self._load_mutation(forge)

    def test_loader_rejects_an_incorrect_or_missing_quote_hash(self) -> None:
        with self.subTest(kind="incorrect"):
            with self.assertRaisesRegex(ValueError, "quote hash"):
                self._load_mutation(
                    lambda record: record.__setitem__("quote_hash", "0" * 64)
                )

        with self.subTest(kind="missing"):
            with self.assertRaisesRegex((KeyError, ValueError), "quote_hash|quote hash"):
                self._load_mutation(lambda record: record.pop("quote_hash"))

    def test_loader_rejects_an_invented_source_anchor(self) -> None:
        with self.assertRaisesRegex(ValueError, "source anchor"):
            self._load_mutation(
                lambda record: record.__setitem__(
                    "source_anchor",
                    "invented-source.md L999999",
                )
            )

    def test_rules_line_anchor_must_cover_the_rule_that_supplies_the_quote(self) -> None:
        record = _sample_record()
        self.assertEqual(record["source_anchor"], "rules.md#L12-L20")

        with self.assertRaisesRegex(ValueError, "source anchor|anchored source"):
            self._load_mutation(
                lambda mutated: mutated.__setitem__(
                    "source_anchor",
                    "rules.md#L21-L29",
                )
            )

    def test_loader_rejects_a_source_file_detached_from_its_pack_identity(self) -> None:
        record = _sample_record()
        original = ROOT / str(record["source_path"])
        with tempfile.TemporaryDirectory() as temporary:
            detached = Path(temporary) / "skill"
            forged = detached / "references/books/forged/rules.md"
            forged.parent.mkdir(parents=True)
            shutil.copyfile(original, forged)
            record["source_path"] = forged.relative_to(detached).as_posix()
            record["source_sha256"] = hashlib.sha256(forged.read_bytes()).hexdigest()
            index = detached / "references/index/evidence-rules.jsonl"
            index.parent.mkdir(parents=True)
            index.write_text(
                json.dumps(
                    record,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "source path|source identity"):
                load_evidence_rules(index, root=detached)

    def test_compiler_rejects_a_rules_line_anchor_for_another_rule_block(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            detached = Path(temporary) / "skill"
            shutil.copytree(ROOT / "references", detached / "references")
            rules = (
                detached
                / "references/books/bazi/ditiansui-chanwei/rules.md"
            )
            source = rules.read_text(encoding="utf-8")
            marker = "## DR-01-01"
            start = source.index(marker)
            statement = source.index("- **source_chapter**", start)
            source = (
                source[:statement]
                + "- **source_anchor**: rules.md#L21-L29\n"
                + source[statement:]
            )
            rules.write_text(source, encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "source anchor|anchored source"):
                build_evidence_index.compile_evidence_rules(root=detached)

    def test_detached_root_compiles_and_loads_only_its_own_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            detached = Path(temporary) / "skill"
            detached_research_root = Path(temporary) / "research"
            shutil.copytree(ROOT / "references", detached / "references")
            _copy_required_research_sources(detached, detached_research_root)
            records = build_evidence_index.compile_evidence_rules(
                root=detached,
                verify_research_sources=True,
                research_root=detached_research_root,
            )
            output = detached / "references/index/evidence-rules.jsonl"
            output.write_text(
                build_evidence_index.render_jsonl(records),
                encoding="utf-8",
            )

            loaded = load_evidence_rules(output, root=detached)

        self.assertEqual(len(records), 1328)
        self.assertEqual(len(loaded), 1328)
        self.assertTrue(
            all(not Path(record["source_path"]).is_absolute() for record in records)
        )


if __name__ == "__main__":
    unittest.main()

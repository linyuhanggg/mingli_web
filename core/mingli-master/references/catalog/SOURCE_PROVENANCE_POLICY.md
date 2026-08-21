# Source Provenance And Distribution Policy

`D2_READY_REFERENCE_PACKS.yaml` is the consolidated source-provenance manifest for every
reference pack shipped with `mingli-master`. It records the source anchor, source risk,
distilled-pack index hash, local fulltext path, and local fulltext SHA-256.

Complete source transcriptions are research inputs, not runtime payloads. Because the source
pages and modern transcriptions do not share one verified redistribution licence, files under
`references/fulltext/` remain local, are ignored by Git, and are excluded from releases. The
runtime consumes only the compact distilled packs under `references/books/`.

`d2_status: ready` means the distilled pack passed the repository's structure and evidence
checks. It does not assert copyright clearance, historical authenticity, empirical predictive
accuracy, or word-for-word collation against every surviving edition.

Run the following before a local distillation or release audit:

```bash
python3 scripts/audit_reference_catalog.py --require-local-fulltext
python3 scripts/audit_reference_catalog.py
```

Use `--write` only when pack paths, source anchors, or recorded checksums intentionally change.

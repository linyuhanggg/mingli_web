# Hardcoding audit 2026-07-22

## V4 ownership boundary

- The caller owns admission meaning, action/system choice, natural intake
  questions, semantic responsiveness, and every byte of successful public
  prose.
- The runtime owns schemas, structured calculation, fact/evidence identity,
  source relationships, lineage, digests, exact answer spans, and atomic state.
- Capability cards describe calculable inputs and output granularity. They do
  not map user vocabulary to a route.

## Kept intentionally

- Protocol constants: action/status names, field names, IDs, digest formats,
  span rules, and file layout.
- Deterministic domain data required for calculation, including calendrical
  tables and canonical system IDs.
- Source-backed rules and corpus metadata, including prerequisites,
  counterconditions, anchors, hashes, and lineage relationships.
- Fixed fixtures under tests and regression artifacts.

## Removed from the v4 operating path

- Query synonym inventories and keyword-based intent/continuity routing.
- System selection inferred from raw user text.
- Runtime-authored successful answers, fixed intake questions, scene templates,
  and reusable public wording.
- Semantic phrase scoring, answer-reversal checks, and prose repair loops.
- Runtime accuracy logging and probability presentation in an ordinary reading.

Compatibility code for importing immutable v3 records is isolated from the v4
request contract. `scripts/audit_v4_runtime_boundary.py` now imports
`reading_transaction` in a clean interpreter and rejects any loaded module that
owns legacy routing, semantic prose gates, fallback prose, or calibration.

The audit found one real boundary leak: the Bazi reasoning helper imported the
offline prediction-freeze module only to reuse its digest function. Production
now uses the digest implementation in `evidence_contract.py`, and the v4
provider assembly lives in `reading_engine/providers.py`. The older provider
adjudicators remain available to explicit compatibility tests, but they are not
loaded by the v4 entrypoint.

## Executable audit

The audit has three independent results:

1. **Runtime import boundary.** A clean subprocess records the modules loaded
   by the v4 entrypoint. Exact forbidden responsibilities are classified as
   `legacy_routing_import`, `semantic_gate_import`,
   `fallback_prose_import`, or `calibration_import`.
2. **Public prose ownership.** Python files actually loaded by that entrypoint
   are parsed as AST. Literal paragraphs assigned to public answer fields are
   failures. The only text categories exempt from this review are protocol
   constants, deterministic domain data, corpus text, and test fixtures.
3. **Corpus integrity.** Catalog count and index hashes, source anchors and
   recorded fulltext hashes, D2-ready status, required pack files, and
   hashable quote-index rows are checked independently. A clean runtime cannot
   turn an incomplete corpus into a pass.

Current repository result:

- v4 forbidden runtime imports: `0`
- loaded production Python files with program-authored public paragraphs: `0`
- catalog/D2-ready packs checked: `54`
- source-provenance records checked: `54`
- quote-index rows hashed: `18810`

Run it with:

```bash
PYTHONPATH=scripts python3 scripts/audit_v4_runtime_boundary.py
```

## Documentation minimalism review

`SKILL.md` contains the five operating duties only: launch the transaction,
choose action/system semantically from capabilities, use facts and applicable
sources, write a source-traced answer, and preserve conversation state. System
details live in capability/source cards; answer mechanics and state transitions
live in their focused references. Duplication was reviewed by responsibility,
without a character-count rule.

## Corpus boundary

No raw or normalized classical corpus content is changed by this refactor.
Runtime-boundary cleanliness and corpus completeness are separate properties;
catalog, provenance, quote-hash, D2-ready, and repository-privacy audits remain
mandatory. A `ready` catalog entry means that the current distilled evidence
pack satisfies its recorded checks; it does not claim exhaustive classical
coverage or completed edition collation.

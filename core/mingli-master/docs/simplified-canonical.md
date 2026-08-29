# Product simplified canonical

The product text canonical is `mingli-product-simplified-v1`. Its public
foundation is the Apache-2.0 `OpenCC==1.4.2` distribution with the `t2s`
configuration. OpenCC runs to a stable fixed point first; the project-owned editorial rules in
`references/matrices/simplified-canonical-v1.json` run second. The manifest is
the only allowed project supplement. Rules must name their source, target,
scope, decision reference, rationale, and raw evidence.

`MING-66-EDITORIAL-001` converts `夘` to `卯`. This is a project editorial
decision for one product-wide simplified representation. Its evidence is the
raw `亥夘未木合` passage at
`references/fulltext/san-shi/daliuren-daquan/fulltext.md#L2460`; it was not
inferred from another converter's output or mapping table.

Raw research fulltexts remain read-only local evidence. Product search,
display, citation, and verdict paths consume deterministic simplified
derivatives. Complete fulltext derivatives are written only beneath an
explicit local output root and are not added to the release tree. The 55
distilled `quote-index.md` registries and the compiled evidence index are
release data, so their displayed text is stored in the product canonical while
raw source paths, hashes, and line anchors remain unchanged.

Run the complete rebuild from the repository root with an environment that has
the exact Core requirements installed:

```bash
MINGLI_RESEARCH_ROOT=/absolute/path/to/mingli-master-research \
python core/mingli-master/scripts/build_simplified_corpus.py \
  --research-root /absolute/path/to/mingli-master-research \
  --output-root /absolute/path/to/local-derived-output
```

The output root must be absent or empty and must not be the research root or
one of its descendants.

The release 5.1 count contract is 54 fulltexts, 101,701 accepted passages, 55
quote indexes with 18,940 citations, and 478 evidence-index citations: 19,418
registered citations in total. The builder fails on count drift or on any
formerly exact registered citation that is no longer exact.

`references/regression/ming66-legacy-citation-verdicts-v1.jsonl` records only
the old comparator's citation ID, status, and anchor. It contains no legacy
normalized text or mapping and never generates new expected values. The new
verdicts are recomputed solely from OpenCC, the project manifest, registered
citations, and raw evidence. The complete old/new audit is written to the local
output and can be refreshed in the committed migration Golden with
`--write-migration-golden`. Two rebuilds against the same raw tree must be
byte-identical.

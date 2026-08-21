# Accuracy And Statistical Validation

This reference belongs to the optional offline Mingli Lab sidecar. It is not a
production reading instruction. A normal reading neither records outcomes nor
shows a probability or calibration label.

## Keep the layers separate

| Layer | Evidence | Appropriate check |
|---|---|---|
| Calculation | Deterministic chart, cast, calendar, and declared convention | Exact fixtures and boundary tests |
| Classical evidence | Source identity, anchor, applicability, lineage, counter-evidence | Provenance and digest checks |
| Caller judgment | Whether the answer follows current facts and applicable sources | Human review of claim traces |
| Empirical outcome | What objectively happened after publication | Prospective append-only outcome records |

A correct chart does not prove an interpretation statistically. Textual or
classical support is not an empirical probability. Do not translate evidence
strength, caller confidence, source count, or fluent wording into odds.

## Prospective protocol

1. Invoke the lab explicitly, outside the production transaction.
2. Before seeing an outcome, publish one specific claim with its exact text,
   publication time, resolution window, method, source references, fact digest,
   and counter-evidence.
3. Preserve the immutable claim hash.
4. After the window closes, append an outcome with observation time and
   auditable provenance. Never edit the claim.
5. If feedback is absent or cannot be verified, append or report `unknown`.
   `unknown` is not a miss.
6. Review batches rather than treating one memorable case as calibration.

Use anonymized identifiers. Keep private birth data, credentials, personal
messages, and raw documents out of the outcome ledger.

## Metrics

- Hit, partial, miss, abstention, unknown, and coverage counts may be reported
  from objective outcome records.
- Brier score is valid only when the claim contained an explicit numeric
  probability before publication and the later outcome is objectively binary.
- Interval score is valid only when an explicit numeric interval was frozen and
  a comparable numeric value was later observed.
- Qualitative `evidence_strength` never enters either calculation.
- Open-ended usefulness and prose quality require a human rubric; they are not
  exact-match accuracy.

The canonical architecture and record boundary are documented in
`docs/architecture/mingli-lab-sidecar.md`. The offline tools are
`scripts/case_log.py`, `scripts/prediction_freeze.py`, and
`scripts/evaluate_answer.py`.

# Mingli Lab Sidecar

`mingli-lab` is an **offline, optional** research workflow. It is not imported
by `reading_transaction.py`, is not mentioned in the production `SKILL.md`, and
is never run merely because a user asks for a reading. A normal transaction
does not write a claim, outcome, score, probability, or personal feedback log.

## Boundary

The production Skill calculates facts, retrieves source-bound evidence,
persists reading lineage, and validates caller-authored answers. The lab may be
invoked separately when an operator deliberately runs a prospective study or a
blind benchmark. It cannot authorize, rewrite, block, or embellish a public
reading.

```text
production reading ───────────────> committed reading artifact

explicit offline study
  -> publish immutable claim
  -> wait until its resolution window closes
  -> append an independently sourced outcome (or unknown)
  -> calculate optional research metrics
```

## Append-only records

`scripts/case_log.py` stores separate JSONL records:

- A `mingli-lab-claim-v1` record keeps the exact prediction text, publication
  time, resolution window, method, source references, optional fact digest,
  counter-evidence, and an immutable `claim_digest`.
- A `mingli-lab-outcome-v1` record binds to that digest and keeps the later
  observation time, outcome provenance, optional objective value, and an
  immutable `outcome_digest`.

Records are appended; an existing claim is never rewritten after an outcome is
known. If no feedback or objective record exists, the outcome is `unknown`.
`unknown` is neither a hit nor a miss and never lowers an accuracy score.

Outcome records must not contain secrets, raw identity data, or credentials.
Use anonymized case IDs and provenance references that can be audited without
copying private source material into the ledger.

## Evidence strength is not probability

`evidence_strength` describes the quality and applicability of the facts and
sources supporting a traditional interpretation. It is qualitative. The lab
does not map `low`, `medium`, `high`, a caller confidence phrase, or a book count
to numeric odds.

A numeric `probability` is accepted only when the study protocol supplies it
explicitly before the outcome. Brier score is computed only for such claims and
objective binary values. Likewise, interval scoring runs only for an explicit
numeric interval and an observed numeric value. These metrics remain absent
from public readings.

## Existing blind benchmark helpers

`scripts/prediction_freeze.py` remains an offline immutable store for structured
and multiple-choice experiments. It records generic method identity rather
than selecting a runtime model or provider. Missing outcomes produce
`result: unknown`; scoring never treats absent feedback as failure.

`scripts/evaluate_answer.py` is an opt-in offline review helper. It is not a
production gate and does not require public answers to expose calibration
fields, probabilities, confidence buckets, or case-log markers.

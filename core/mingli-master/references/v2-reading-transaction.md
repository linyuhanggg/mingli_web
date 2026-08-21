# Portable Reading Interface Reference

This document describes the portable `execute(Command) -> Result` contract
behind the JSON Adapter. It never instructs temporary files, permission
bits, digests, command shapes or any gateway observation.

## Physical call

One process, one turn: the adapter reads exactly one Command JSON object
from stdin and writes exactly one Result JSON object to stdout. stderr is
diagnostics only. Malformed input, runtime validation problems and
provider or store failures still produce a parsable, non-empty
`stopped` Result on stdout.

## Commands

```json
{"kind": "describe"}
```

```json
{
  "kind": "prepare",
  "query": "…",
  "intent": {
    "subject_refs": ["…"],
    "object_id": "…",
    "dimension_ids": [],
    "horizon": {"kind_id": "…", "start": null, "end": null},
    "capability_id": null,
    "comparisons": [
      {"capability_id": "…", "requirement": "required"}
    ]
  },
  "facts": {"subject_ref": {"input_field_id": "value"}},
  "state_token": null,
  "transition": null
}
```

```json
{"kind": "complete", "state_token": "…", "public_copy": "…"}
```

All structured identifiers come from the cached `describe` data. An empty
`dimension_ids` means a broad question; capabilities that declare default
dimensions answer directly without a clarification round. `transition`
accepts only `correct` and `restart`; continuation needs no transition
value at all.

Each comparison lives only in `intent.comparisons`. `required` means the
turn cannot claim a completed comparison when that capability is unavailable
or still needs input. `optional` keeps the primary result and records a
visible limit when the entire comparison cannot be completed. Older persisted
pending records containing `comparison_capability_ids` are read as required
comparisons for migration only; new hosts must not emit that field.

## Results

- `described`: `protocol_version`, `manifest_digest`, `capabilities`
  (ids, labels, descriptions, term views, input fields, required
  any-of input groups, default dimension ids). Cache it per installed
  artifact version.
- `prepared`: a fresh `state_token` plus a closed-world `brief`
  containing `question`, `vocabulary`, `facts`, `evidence`,
  `claim_scopes`, `limits` and, for a continuation, `prior_answer`.
  The brief is self-contained: every opaque identifier it references is
  defined in `vocabulary`; nothing outside the brief may inform the
  drafted answer.
- `accepted`: the committed `public_copy`, byte-stable across replays of
  the same prepared token. Display it verbatim; nothing re-validates it.
- `stopped`: `reason` is one of `need_input`, `unsupported`, `conflict`,
  `error`; `public_copy` is always non-empty and displayable as-is.

## Token semantics

Keep only the latest `state_token`; it is opaque and single-typed.

- no token: a new root reading.
- pending token + more facts: the intake continues automatically.
- accepted token, no transition: a follow-up in the same lineage with
  fresh applicability retrieval.
- accepted token + `correct`: a superseding version; old versions stay
  immutable.
- accepted token + `restart`: a new child reading with preserved
  lineage; cast-based capabilities draw a fresh seed.
- an independent new question simply omits the token.

Idempotency is token-bound. Replaying a prepared token is stable, but two
identical no-token commands are two distinct user turns and therefore create
different root reading ids. A transition cannot simultaneously switch scope
or capability; that contradictory request returns a non-empty `conflict`.

Replays of the same prepared token commit first-wins and return the same
`accepted` bytes; `conflict` appears only when a stale parent or a rival
child competes for one lineage slot.

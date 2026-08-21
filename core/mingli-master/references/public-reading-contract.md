# Public reading responsibilities

The host model owns public prose; the core owns facts, evidence identity
and atomic state. `complete` performs mechanical validation only: a
non-empty `public_copy`, a valid state token, and one atomic commit. It
never judges natural-language meaning, never requests spans or claim
traces, and never re-validates an already accepted answer.

## Drafting from the brief

- The `prepared.brief` is the entire drafting surface. Facts, evidence,
  claim scopes, limits and their public term definitions all travel
  inside it.
- Stay inside the claim scopes: each scope names the subject, the
  answerable dimension, the allowed claim kinds and the certainty
  ceiling. Content the brief does not authorize does not enter the
  answer, no matter what else the host environment knows.
- State the limits honestly. A source gap means no citation is
  fabricated; an unanswerable dimension is said to be unanswerable.
- `prior_answer`, when present, is continuity context from the same
  lineage, not a template to repeat.

## Delivery

- `accepted.public_copy` and `stopped.public_copy` are displayed
  verbatim. Adapters never rewrite, truncate, suppress or re-check a
  non-empty result.
- Replaying `complete` on the same prepared token returns byte-identical
  `accepted` output; later drafts never overwrite a committed answer.

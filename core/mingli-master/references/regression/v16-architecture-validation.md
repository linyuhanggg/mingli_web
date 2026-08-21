# v16 Architecture Validation

Date: 2026-07-13

## Release Question

This validation separates three claims that must not be conflated:

1. The deterministic adapter produced traceable chart facts.
2. The inference pipeline bound its rules and prose to those facts.
3. The resulting concrete life-event prediction was accurate.

The first two claims passed structural regression. The third did not pass the
current blind benchmark.

## Frozen Architecture

- Exact user query, options, facts, evidence, rule activations, model proposal,
  public draft, and final copy are digest-bound.
- Question domains and option-candidate domains are separate.
- Correlated books in one lineage do not count as independent votes.
- Confidence cannot exceed the question precision or direct rule-tool ceiling.
- Same-reading follow-ups reuse the frozen chart or lesson.
- Every formal reading snapshots the scripts and selected source files it needs;
  each file is hash-verified before a follow-up can run.
- Initial and follow-up publication commit the complete accepted envelope to a
  HMAC/checkpoint-protected v2 index. `public-accepted.json` and the public
  text/manifest pair are only recoverable compatibility copies.
- Every accepted event has a unique operation ID and immutable sequence.
  Recovery uses the external checkpoint rather than directory scans, `mtime`,
  or an artifact-local pending journal.
- Follow-up discovery never imports historical runtime modules. Before a gate
  runs, the trusted publisher re-verifies and privately snapshots every frozen
  runtime byte and every SHA-bound gate input, then rewrites the gate command to
  those captured files; symlinked reservation directories are rejected.
- Pipeline-creation records are signed to one active root before initial
  acceptance. A live copied root cannot create a second history; a true move
  can rebind only after the old path disappears.
- Latest-reading recovery validates index events newest-first. A dangerous
  compatibility path on the newest candidate fails closed instead of falling
  back, while damage confined to an older candidate cannot block a newer one.
- Follow-up reservations have no age-based cleanup. Their mode-0600 bytes are
  retained for idempotent retry and audit unless an explicit index-aware
  maintenance operation is introduced.
- Same-reading elaboration cannot alter frozen claims or chart sections. A new
  question dimension requires a new contract instead of being inserted into
  an old reading.
- Bazi birth conversion preserves reviewed civil time zones and blocks an
  unresolved 23:xx late-Zi policy instead of choosing silently.
- Exact state, event identity, timing, amount, location, and closed candidate
  selection are marked `experimental_specific_hypothesis` with a low ceiling.
  There is no topic taboo, but an interpretation cannot be asserted as fact.

Automated regression: `634/634` tests passed with Python 3.14.6. Skill Creator
quick validation and Python bytecode compilation also passed.

## Live Hermes Follow-Up Replay

An isolated `minglitest` profile using `openai-codex/gpt-5.5` ran a fresh Da
Liu Ren query and three natural follow-ups. The initial reading persisted one
`pipeline-manifest.json` under reading ID
`d67b0b6713e74874a4a8a6ea45a98269`; no follow-up created a second cast.

The first replay exposed a real forked-session failure: Hermes loaded the skill
but answered directly from prose with a Bazi-only `【未校盘】` tag. After the
recovery contract was moved into skill metadata and the non-negotiable section,
the same prompt ran `session_search`, recovered the exact original query and
visible chart marker, called `reading_followup.py`, retained the chart, and
published a hash-bound explanation through the original reading.

The publisher was then made transactional. In that replay, its first candidate
failed `legacy_public_gate` with `liuren_public_single_general_story`; the
accepted answer remained unchanged. One wording repair passed both gates, and
the final manifest linked to the prior accepted digest. No old direct-finalizer
command was exposed and the final public SHA-256 matched `public.txt`.

A final 2026-07-13 replay exercised the rebuilt protocol. A `now` cast during
late Zi failed its calendar cross-check and produced no accepted reading. A
separate explicit `2026-07-13 22:30 Asia/Shanghai` contract-signing query
persisted reading `03bea6e736404311b0133dbcd35c31f6` with initial manifest
digest `4683ac0377d58e8efbc45fda3d0f88835848c1b0f3da246015e893892c0938d8`.
The first forked semantic search incorrectly found the failed late-Zi session;
this exposed the need for deterministic deictic recovery. After adding
`--latest-valid`, a fresh `刚才/上一课/沿用这卦` turn ignored the failed cast,
verified the runtime/source snapshot and accepted envelope, reused the same
reading, and published manifest
`257462c8c4d075cd5ac7fce2ded9806a9dc2c674c760b190e50dc0209b9fd194`.
Its `followup_of_manifest_digest` equals the initial digest, no second pipeline
was created. The original replay removed its reservation under the older
cleanup policy; the hardened publisher now retains successful reservations as
mode-0600 audit evidence so it never deletes a path after validating an inode.

A later adversarial replay asked the model to elaborate again. It tried to add
an unrequested `blockage` dimension to the old lesson. This now fails before
publication: the follow-up publisher compares the draft with the last accepted
claims and chart sections exactly. Regression tests also cover `能否` as an
outcome request and ensure that cast metadata such as `北京时间` does not become
a spurious timing dimension.

The resulting security regression set also reproduces and closes initial
acceptance rollback, stale-checkpoint replay, valid-prefix root-index rollback,
cross-root substitution and live-copy takeover, pipeline-creation replacement,
pre-acceptance copied-root double sealing, hash-bound gate-input replacement,
gate/commit byte races, one-read draft replacement, concurrent reservation
misattribution, pipeline-manifest partial writes, runtime replacement after
discovery, forged `mtime` ordering, reservation and compatibility-file symlink
escape, newest-reading fallback and older-reading overblocking,
historical-operation retry after a later commit, retained old reservations,
post-index crash recovery, and whole-tree relocation.

This replay establishes artifact continuity, gate execution, and failure
rollback. It does not establish that the hidden-activity judgment was true.

## Residual Trust Boundary

The acceptance index is an integrity and continuity mechanism inside one
trusted local account. It detects stale replay, accidental live-root copies,
and byte replacement during publication; it is not a sandbox against arbitrary
code already running as that account. Such code can read the HMAC key or replace
an installed trusted publisher. A cross-parent relocation must exclusively move
the sibling trust directory and remove the old active path; duplicating both the
root and its trust store after the old path disappears can create independent
administrative lineages. Disk, directory `fsync`, or checkpoint failures are
fail-stop availability events rather than something the publisher conceals or
repairs by guessing.

## Development Diagnostics

- Legacy v11 development result: `31/77 = 40.26%`; it included neutral Ziwei
  context and is not a release score.
- Repeated 22-question smoke runs with the same model ranged from `7/22` to
  `11/22`. This variance forbids selecting the best run as evidence.
- Option selection and confidence assignment were therefore split into two
  frozen stages.

## Retired Validation Split

A validation prediction run covered 48 of 58 cases before the timezone repair.
While inspecting the upstream source, answers for eleven validation questions
were exposed: five Miyazaki questions, five Singapore questions, and one
adjacent Hong Kong question. The entire validation split was retired. No score
from it is used for release or tuning.

## Final Blind Evaluation

Both evaluation protocols were generated before either answer set was scored.
Model: `openai-codex/gpt-5.6-terra`.

Eligibility from 65 evaluation questions:

| Status | Count |
|---|---:|
| Predicted | 55 |
| Blocked: unresolved late-Zi policy | 5 |
| Blocked: country-only US timezone | 5 |

### Forced Choice

- Correct: `16/55 = 29.09%`
- Four-choice random baseline: `25%`
- One-sided binomial test against 25%: `p = 0.286798`
- Wilson 95% interval: `18.77% - 42.14%`
- Timing questions: `4/18 = 22.22%`
- Non-timing questions: `12/37 = 32.43%`
- Finance: `6/15 = 40.00%`
- Family: `5/13 = 38.46%`
- Work: `6/18 = 33.33%`
- Relationship: `4/12 = 33.33%`
- Travel: `0/3 = 0%`

This result is not statistically distinguishable from random choice.

### Allow Abstain

- Abstained: `51/55`
- Coverage: `4/55 = 7.27%`
- Correct among answered: `1/4 = 25%`
- Correct over all eligible questions: `1/55 = 1.82%`

The abstention policy did not isolate a useful high-accuracy subset.

## Release Decision

The architecture is suitable for traceable traditional-text interpretation and
for collecting better evidence. It is not evidence that exact occupation,
hidden current activity, event identity, year, place, amount, or comparable
life outcomes can currently be predicted accurately. Such answers may still be
given directly as low-confidence hypotheses with their chart or lesson basis,
but must not be represented as empirically validated facts.

Do not tune on the consumed evaluation answers. The next accuracy claim needs a
new unseen set, preregistered metrics, fixed code/model hashes, sufficient
sample size by domain, calibration and coverage reporting, and prospective
real-case outcomes with timestamps.

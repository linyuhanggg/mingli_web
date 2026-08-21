# Immutable outcome calibration

Outcome calibration records what happened after an accepted reading without editing its public answer, calculation, evidence, judgment, cross-check, classical sources, or version history.

## Frozen claim registry

An outcome cannot name arbitrary public text. Completion freezes every validated `AnswerDraft.claim_trace` into `AcceptedReading.accepted_claims`, including its exact public-copy span, visible text, role, dimension, fact refs, evidence refs, counter-evidence refs, and digest. `OutcomeStore.claims()` then derives the calibratable registry from an exact accepted `reading_id` plus `prepared_digest`:

- each frozen visible accepted claim becomes one `judgment_dimension` claim, even when the internal judgment conclusion is empty;
- each accepted `CrossCheckReviewDimension` becomes one `cross_check_review` claim;
- claim identity binds reading/version/prepared/public-copy identities, dimension, explicit horizon, structured conclusion or verified visible review text, and contributor identities;
- every contributor binds role, system, provider ID/version, accepted-claim or judgment-claim digest, exact fact refs, rule IDs, and source lineages;
- cross-system claims contain both primary and secondary contributors.

Cross-system contributors use the accepted review dimension's side-local fact, evidence, and counter-evidence refs rather than the whole side judgment. A visible span plus dimension is one semantic claim identity: duplicate roles or traces at that identity fail as a repairable draft error, refs are canonicalized, and an overlapping cross-reviewed claim replaces the primary-only identity. The registry is derived from accepted artifacts, so later outcome knowledge cannot create a new claim span, split a sentence, choose unrelated rules, or attribute a secondary result only to the primary provider. `record()` accepts only a registry `claim_id`.

## Authenticated immutable records

Each outcome stores one `hit`, `partial`, `miss`, or `unknown` observation, a timezone-aware report time, and bounded evidence. Evidence accepts only:

- `kind`: `user_report`, `document`, `observed_event`, or `third_party_report`;
- `summary`: 1–1000 characters;
- optional timezone-aware `observed_at`.

Nested payloads, extra keys, raw media, arbitrary locators, and oversized evidence fail closed. Do not put passwords, API keys, or unrelated personal data in the summary.

Records are private (`0700` directories, `0600` files), immutable by claim ID, self-digested, and authenticated with HMAC-SHA-256 using a key held outside both reading and outcome stores. The key must contain at least 32 bytes, remain in a current-user-owned single-link `0600` file, and be backed up separately; losing it makes old records unverifiable. A disk writer cannot change status/evidence and merely recompute the public digest. Locks use `O_NOFOLLOW` and validate owner/type/link-count/mode before locking.

An authenticated manifest checkpoint is stored outside both stores. It binds the complete set of claim IDs and record digests to the outcome-store identity. Writes use an authenticated two-phase record: the checkpoint first names one pending claim/digest, the outcome is atomically written, and the checkpoint then commits it. After a crash, startup either rolls back a missing pending file or verifies its HMAC and exact reading registry before completing the commit. Loading all records and aggregation compare the exact file/input set with that checkpoint, so selective deletion, omission, or rollback of only the outcome store fails closed. The checkpoint belongs in a separately protected and backed-up location; outcome-store write access must not include checkpoint or key write access.

Each reading store receives one private random persistent identity under its isolated identity lock when outcome calibration is first enabled. Startup probes that identity without creating either the identity or its lock and captures the private reading directory's device/inode identity. An existing outcome binding is authenticated first, so a wrong reading-store path, a replacement directory at the same path, or a missing identity is rejected without modifying the candidate reading store. Only a confirmed new store or a fully authenticated legacy migration may create the identity; concurrent first attachments may adopt the identity-lock winner only while the captured directory identity is unchanged, and legacy records are verified again after that election.

Each outcome root also has an external HMAC-authenticated guard at `.mingli-outcome-root-guards/<canonical-root-sha256>.json` beneath the outcome root's parent, outside the outcome-root directory itself. Before an identity can be created, an atomic reservation in that guard fixes the resolved outcome, checkpoint, and reading paths plus the reading directory device/inode; it is upgraded to the final guard only after identity election. The final guard and root-local copies bind the same paths, persistent reading-store ID, and binding digest, while checkpoint schema v2 cross-binds its manifest to that digest. Device/inode is deliberately reservation-scoped: a byte-identical backup that preserves the persistent store ID and reading history can be restored at the same path on a new inode. Outcome-root write access must not include the guard directory. An existing guard that cannot be authenticated with the configured key always fails closed; key rotation or a path-changing storage migration requires an explicit offline migration rather than automatic v1 downgrade.

Initialization uses the fixed lock order `external root guard -> outcome root -> checkpoint -> reading identity` (the final lock is needed only for first attachment); later reads and writes use `external root guard -> outcome root -> checkpoint -> claim`. The root-anchor writer handles short writes, truncates only after the complete replacement is present, and synchronizes the descriptor. An empty or interrupted local anchor is treated as a recoverable crash, not as proof that initialization completed: the matching external guard or authenticated local binding can repair it. If the external guard is genuinely absent during an upgrade, a matching v2 checkpoint can reconstruct missing—not unauthenticatable—local copies. A legacy v1 checkpoint is migrated exactly once only when no prior identity copy exists, and only after its MAC, complete file set, record digests, and immutable reading registry all validate; the registry is validated again after identity election. Deleting or corrupting both root-local copies therefore cannot select a different checkpoint, and a crash between reservation and final guard cannot change the reserved paths.

Repeating the exact report is idempotent. A different report for the same claim is rejected instead of replacing history. Use `unknown` when available evidence cannot decide the claim.

## Recording without argv disclosure

Put the report in a current-user-owned `0600` JSON file (or pass `-` and provide it through stdin):

```json
{"reading_id":"0123456789abcdef0123456789abcdef","prepared_digest":"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef","claim_id":"abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789","status":"partial","evidence":{"kind":"user_report","summary":"发生了一部分","observed_at":"2026-08-01T09:30:00+08:00"},"reported_at":"2026-08-01T10:00:00+08:00"}
```

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/record_reading_outcome.py \
  --reading-store /private/path/readings \
  --outcome-store /private/path/outcomes \
  --integrity-key-file /private/checkpoint/outcome-integrity.key \
  --integrity-checkpoint /private/checkpoint/outcome-manifest.json \
  --report-file /private/path/outcome-report.json
```

The CLI returns only claim/record digests, status, schema, and stored state; it never echoes claim text or evidence. Store paths and claim IDs are not model-selection policy and never enter production reading digests.

## Aggregation and use

`OutcomeStore.aggregate()` reauthenticates every record, re-derives its exact claim from immutable reading history, requires the complete externally checkpointed outcome set, rejects duplicates/omissions, and publishes counts along five axes: every contributing provider version, rule ID, source lineage, question dimension, and horizon. Rule and source-lineage axes keep separate `support` and `counter` lanes so an outcome never treats a counter-rule as supporting evidence. Every lane or ordinary bucket contains `sample_count` plus hit/partial/miss/unknown counts. It emits no percentages, probabilities, confidence estimates, accuracy claims, or weights.

Calibration is diagnostic. Retrieval weighting may change only after a separately documented minimum sample threshold, selection-bias and unknown-handling review, independent validation, and a reversible versioned rollout. No outcome report may rewrite an accepted reading or classical source text.

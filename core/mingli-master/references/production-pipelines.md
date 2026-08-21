# Production Transaction

This file records the production boundary without defining a second workflow.
The only production entrypoint is `scripts/run_reading_transaction.sh`; the
authoritative command and surface rules live in the root `SKILL.md`.

## One Transaction

For every admitted reading, the transaction owns routing, missing-fact intake,
deterministic calculation, source-bound evidence, frozen judgment, draft
validation, persistence, and delivery. Do not directly orchestrate
`bazi_calc.py`, `fortune_calc.py`, `liuren_calc.py`, `reading_followup.py`, or a
public gate from a conversation.

The production sequence is:

1. `prepare` the exact user query with only the facts supplied in the current
   conversation or trusted profile.
2. If the result is `prepared`, write one natural draft against its
   `draft_contract` and `complete` the same `reading_id` and
   `prepared_digest`.
3. If the result is `need_user_fact`, preserve its `intake_id` and ask only the
   returned fact question.
4. If the result is `not_applicable`, continue as ordinary chat without a
   Mingli tag.
5. Internal failures stay internal. Never expose a retry phrase, ask the user
   to resend the question, or start an unbound replacement calculation.

## System Inputs

- Bazi and Ziwei timing require complete birth data. Four validated pillars can
  answer static chart questions but do not silently create luck-cycle timing.
- Current Da Liu Ren uses the exact question, one authoritative civil time, and
  timezone. The subject's city is not a casting input.
- Daily fortune uses the configured validated birth profile and the requested
  target period. It does not become a short-event cast.
- Structured systems accept only their complete validated chart until a
  deterministic calculator is available.

## Follow-Ups

A natural follow-up passes the accepted `reading_id` and a newly formed
`IntentFrame` to the same transaction. The runtime reuses only the immutable
base calculation. It recompiles applicable evidence, counter-evidence,
judgment, and the answer for the latest active query, and stores independent
intent, evidence, and judgment digests for that version. Earlier claims remain
conversation context, never current authority or fallback copy. Do not locate
prior work by scanning temporary files, choosing the newest directory,
searching prose, or rerunning the original cast.

A new object, event, horizon, or explicitly requested method starts a new
transaction. A clarification, challenge, request for detail, or newly supplied
event context stays on the current reading.

## Delivery

Hermes Gateway delivery uses the private envelope described in `SKILL.md` and
verifies it against the local transaction before sending `public_copy`. Direct
surfaces return only the accepted public copy or the exact missing-fact
question. Internal paths, hashes, markers, gate findings, and implementation
status never belong in the user-facing answer.

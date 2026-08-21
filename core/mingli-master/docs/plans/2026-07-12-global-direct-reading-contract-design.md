# Global Direct Reading Contract Design

**Status:** approved scope expansion

## Goal

Make every `mingli-master` system answer directly and usefully on the first
reply without category-based censorship, while retaining deterministic facts,
source applicability, and system-specific limits.

## Product Decision

"No taboo" means no output category is suppressed merely because it concerns
money, drinking, gambling, secrets, relationships, sex, betrayal, private
meetings, or location. It does not permit invented chart facts, invented
addresses, or a current-event claim from a system that was only asked for a
long-term natal tendency.

The response must distinguish:

- `主断`: the strongest supported reading.
- `次象`: a supported secondary reading when it helps disambiguate.
- `不主`: a direct negative reading when the requested scene is not the
  leading indication, rather than a generic refusal.

## Global Output Contract

1. First response is expanded by default for a personal/event reading. A user
   can explicitly ask for a short answer; detail is not withheld pending a
   follow-up.
2. The visible basis precedes the first judgment, using the correct display
   term for the selected system:
   - Bazi, Ziwei, Xingming: `命盘` / `盘面`
   - Liuyao, Meihua, Da Liu Ren: `卦象`
   - Qimen, Taiyi: `局象` / `盘面`
   - Selection: `日课`
   - Fengshui: `宅局` / `形势`
   - Physiognomy: `相象`
3. Each answer resolves the actual question, gives a direct conclusion, then
   explains the decisive process in ordinary language. It must not publish a
   fixed prose template or stock life scene.
4. A direct scene needs a traceable fact-and-rule basis. One isolated god,
   star, ten-god label, or shensha cannot create the entire story by itself.
5. Location is stated at the resolution the selected system can support:
   direction, distance, indoor/outdoor, venue type, movement, and company.
   A street address or shop name may only be ranked from user-supplied
   candidates; it is never invented.
6. Follow-ups such as `具体解读一下`, `说细一点`, and `按原课重写` reuse the
   bound chart/lesson and deepen the interpretation; they do not re-ask the
   original question or silently recast.

## Architecture

Create one machine-readable public-reading contract matrix. It maps
`system + question shape` to the display label, default depth, required
interpretation dimensions, location resolution, and permitted fact scope.

`reading_public_brief.py` and `liuren_public_brief.py` compile this contract
into each pipeline's `synthesis_context`. `gate_check.py` validates the
visible label, fact consistency, question alignment, and required coverage;
it must never reject a response merely for using a sensitive scene word.

Prompt documents consume the same contract rather than carrying independent,
contradictory instructions.

## System-Specific Scope

| System | Direct reading scope | Non-negotiable boundary |
|---|---|---|
| Bazi / Luming | life structure, tendencies, timing layers, relationship and money patterns | does not claim a person's current GPS location or present act without an event system |
| Daily fortune | supported day-level direction in the domain the user asks about | does not invent a concrete event from a transit symbol alone |
| Ziwei / Xingming | natal/palace or star-pattern tendency after a complete chart | no uncalculated palace/ephemeris claims |
| Liuyao / Meihua / Da Liu Ren / Qimen / Taiyi | concrete event, present state, scene, people, direction, timing when their fact layer exists | no single-symbol story and no fabricated chart/plate |
| Selection | candidate-date recommendation and avoidance | no day ranking without event, calendar, and required constraints |
| Fengshui / Physiognomy | direct observation-derived environmental or visual reading | no unseen layout, compass, or feature claim |

## Known Regressions To Fix

1. Da Liu Ren prompt requires a compact `课象`, makes detail follow-up-only,
   and overrides the user's requested `卦象` label.
2. The public gate accepts sensitive-scene prose but has no contract requiring
   it to be grounded, so removing prose restrictions alone would overcorrect.
3. The source routing matrix still calls some one-off events Liuyao/Meihua
   while live Hermes defaults natural concrete events to Da Liu Ren.
4. No regression suite asserts that a detail follow-up retains the original
   bound lesson and becomes deeper rather than more evasive.
5. There is no single audit asserting that canonical, Codex, default Hermes,
   and liujing Hermes copies carry the same output contract.

## Acceptance Criteria

- No public prompt says a sensitive category is forbidden by default.
- A current-state reading first gives a detailed, direct answer; it can say
  `主应应酬`, `不主赌局`, `隐情象偏重`, or a comparable conclusion when its
  fact/rule trace supports that resolution.
- All named charts, plates, dates, transmissions, and source claims still
  match the hash-bound artifacts.
- Explicitly requested systems remain authoritative; broad questions still
  route to the correct primary system.
- Contract tests, source unit tests, gateway tests, and real Hermes replays
  pass before deployment.

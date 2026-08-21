# Bazi Input And Fact Boundaries

Provider-internal note for the bazi fact layer. It describes what each input
route may determine and where interpretation must stop. It carries no host
workflow, no host-side checking step, and no fixed answer template; the
portable interface (`describe` / `prepare` / `complete`) and the public
`brief` are the only drafting surface.

## Non-Negotiable Boundary

`vision/OCR is transcription only`. It may report visible characters and
layout, but it is never a deterministic bazi fact layer. Reading
`乙酉、辛巳、丙午、癸巳` from pixels does not by itself verify that the
pillars form the correct chart for a birth moment, nor does it derive a
complete static chart. Do not move from image transcription directly to
claims about personality, work, talent, relationships, wealth, health, luck,
or timing.

## Input Routes And Fact Scopes

### Supplied four pillars (with or without an image)

The `pillars` mode of `bazi_fact_adapter.py` validates the four values
against the sixty Jiazi and derives static facts only. The payload carries
`fact_layer_status=validated_user_provided_four_pillars` and
`fact_layer_scope=natal_static`, which means:

- all four values are valid members of the sixty Jiazi;
- hidden stems, ten gods, Nayin, month command, seasonal anchors, coarse
  Tiaohou markers, element inventory, branch relations, and provider-owned
  mechanical salience signals were deterministically derived;
- the birth calendar, solar-term boundary, and true solar time were not
  independently verified.

Luck-cycle scope depends on whether a valid gender was supplied:

- With gender: `luck_cycles.status=sequence_only`. The declared direction
  rule and the ten-step pillar sequence are determined, and the provider
  publishes `limit.partial_luck_timing` in `Prepared.limits`. Direction and
  ordering may be described. Start ages, calendar-year mappings, the active
  cycle, and any precise timing remain unavailable and must not be stated or
  estimated.
- Without gender: `luck_cycles.status=not_calculated_missing_gender` and
  `limit.partial_luck_no_gender` is published. Static interpretation stays
  available; no luck direction, ordering, or timing may be claimed.
- Invalid gender tokens are rejected by the adapter, never guessed.

If the user pivots to timing questions, the correct move is to request civil
birth data and rerun birth mode, never to invent timing from a partial
scope.

### Civil birth data

Require civil birth date, accurate time, gender convention, birthplace, IANA
timezone, measured longitude/latitude, and a coordinate source.  For this
Provider, `time_semantics.default_policy` is
`local_apparent_solar-v1`: when a birth moment is supplied and the caller
omits `time_basis_policy`, the runtime materializes that declared default.
It never silently falls back to `civil`.  Missing longitude, latitude, or
coordinate source therefore produces structured `Stopped.need_input`; a
location string is not treated as measured coordinates.

The `birth` mode converts the effective local-apparent-solar moment to a
lunar date, calculates the four pillars with Jieqi month switching, derives
the static chart, and calculates major-luck direction and start age under the
declared `三日折一年` rule profile.  The normalized calendar fact records the
policy, correction components, coordinates, source, and boundary uncertainty
used by the deterministic calculation.

Only `fact_layer_status=calculated_natal_chart_from_birth_datetime` permits
natal and full major-luck interpretation.

### Supplied pillars plus civil birth data

Birth mode accepts the transcribed pillars as an independent comparison.
`fact_layer_status=conflict_birth_data_vs_supplied_pillars` is a hard stop.
Compare transcription, solar/lunar input, timezone, location, late-Zi-hour
policy, and chart convention before interpreting. Never choose whichever
chart gives a more convenient reading.

## Interpretation Discipline

Adapter fields are facts, not conclusions:

1. Element counts do not by themselves establish 旺衰 or 用神; coarse
   Tiaohou markers do not by themselves select a 调候用神.
2. Salience signals are mechanical candidates with `hard_verdict` fixed at
   `null`; they highlight repetition, relations, and seasonal anchors but
   never justify a final verdict, a score, or a probability.
3. While `interpretive_candidates.strength.status=evidence_only`, the public
   brief must carry `limit.interpretive_verdict_unavailable`.  This boundary
   forbids a hard 旺衰/格局 verdict, an element or stem ranking, and a final
   喜用忌神 conclusion even when a classical excerpt is present.
4. Apply 月令格局, 旺衰气势/通关, 调候, and only then auxiliary Shensha,
   always inside the published claim scopes and limits.
5. A supplied-pillars chart remains inside its published scope; the partial
   luck layer adds direction and ordering, nothing temporal.
6. Follow-ups inherit the chart's fact status. An unvalidated turn cannot be
   retroactively promoted; when the prior turn lacks validated facts, stop
   and collect them.

## Validation

Every payload is checked by `adapter_validate.py`. Supplied-pillars payloads
validate fail-closed: unknown statuses, missing layers, undeclared fields,
fabricated timing keys, capability states that contradict the scope, and
sequences that disagree with the declared direction rule are all rejected.
The production seam runs this validation on every calculation; no host-side
gate or visible status tag is part of this contract.

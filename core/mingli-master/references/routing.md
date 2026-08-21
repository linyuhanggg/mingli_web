# Mingli capability routing

The caller model converts the whole conversation into a semantic `IntentFrame`.
A generic deterministic resolver selects a primary system by comparing that
frame with provider-declared capabilities and current state. This file
describes capabilities only. The executable registry in
`scripts/route_capabilities.py` remains authoritative for accepted system IDs
and missing structured fields.

The production transaction accepts only an explicit V4 action and structured
request. This capability document never authorizes an action-less fallback or
the legacy V3 language router.

## Capability cards

| system | calculation capability | required inputs | fact readiness | output granularity | source card |
|---|---|---|---|---|---|
| `bazi` | Four pillars, hidden stems, Ten Gods, month command, and luck-cycle facts | Birth datetime, timezone, location, and gender; or validated four pillars | Ready for deterministic facts | Natal and timing mechanisms bounded by supplied facts | `references/system-cards/bazi.md` |
| `fortune` | Natal baseline plus a frozen near-time target and calendar normalization | Birth datetime, timezone, location, and gender | Ready for deterministic facts | Tendency and mechanism for the caller's declared horizon; not an invented event | `references/system-cards/bazi.md` |
| `liuren` | Four lessons, three transmissions, lesson method, month general, and Xunkong | Exact question and a transaction-resolved current time, or supplied event datetime; timezone when needed | Ready for deterministic facts | Event-bound lesson mechanisms at the precision supported by the cast | `references/system-cards/san-shi.md` |
| `ziwei` | Ming/Shen positions, palaces, stars, and transformations | Birth datetime, timezone, location, and gender | Ready for deterministic chart facts | Neutral chart and domain facts; directional interpretation remains bounded by executable evidence | `references/system-cards/ziwei.md` |
| `xingming` | Ephemeris-backed classical points, houses, Ming/Shen degrees, transformations, and Bailiu limits | Birth datetime, timezone, location, longitude/latitude with coordinate source | Ready for deterministic facts | Chart and limit facts under the declared Guolao conventions | `references/system-cards/xingming.md` |
| `liuyao` | Complete supplied six-toss cast, or a transaction-created preserved digital coin cast, with full Najia/line facts | A complete cast, or an explicit digital-cast request with event datetime, timezone, and location | Ready for deterministic facts | Main/changed plates, moving lines, relatives, spirits, Xunkong, and strength facts | `references/system-cards/divination.md` |
| `meihua` | Time, number, sound/count, observation, and supplied-hexagram casting from declared method facts | Casting method facts plus event datetime, timezone, and location | Ready for deterministic facts | Primary/mutual/changed hexagrams, body/use, and seasonal strength | `references/system-cards/divination.md` |
| `qimen` | Complete Shijia rotating-plate time board with palaces, stars, doors, deities, and named patterns | Event datetime, timezone, and location | Ready for deterministic facts | Full board facts across solar-term boundaries | `references/system-cards/san-shi.md` |
| `taiyi` | Annual Taiyi board under the declared epoch and macro/historical scope | Reference datetime, timezone, and location | Ready for deterministic facts | Board, deity, and count facts inside the declared scope | `references/system-cards/san-shi.md` |
| `selection` | Generate and rank civil-date and double-hour candidates with exact Jie boundaries, official Yi/Ji, gods, clashes, exclusions, participant facts, and optional folk comparison | Structured event profile plus exact requested action identities, date range, timezone, location; optional hard constraints, participant facts, direction, and folk comparison | Ready for deterministic candidate calculation | Full day/time candidates, explicit eliminations, exact fact-bound evidence, and source-lineage disagreements | `references/system-cards/selection.md` |
| `fengshui` | Normalize supplied compass/site observations and calculate the explicitly selected supported school | `chart_data.fengshui_spec`: measurement provenance, selected `form`/`liqi` subprofiles, assets/region anchors, layout and building chronology | `observation_driven_ready`; 24-mountain normalization plus Bazhai only, with ambiguous/unmeasured facts left explicit | Separate form observations, compass facts, Bazhai correspondences, exact active source-rule ids, conflicts and uncertainty; no outcome verdict | `references/system-cards/fengshui.md` |
| `physiognomy` | Normalize caller-transcribed visible face observations; compare only the activated historical terminology/method layers | `chart_data.physiognomy_spec`: one bound subject, requested regions, hash-bound image metadata or user text, visible observations, lighting/angle/focus/filtering/occlusion quality, uncertainty, and corrections | `observation_driven_ready`; the provider never receives raw media or performs vision, and missing/uncertain regions remain explicit | Visible region/descriptor/quality facts, safe conflict and cross-capture projections, and source-layer comparison; no unseen feature, identity, health, personality, wealth, lifespan, or outcome verdict | `references/system-cards/physiognomy.md` |
| `luming-nayin` | Early Luming/Nayin facts: sixty-Jiazi Nayin, three Yuan, Taiyuan, and source-named Lu/Ma/Gui relations | Birth datetime with timezone and location, or validated four pillars | Ready for deterministic facts | Independent early-Luming fact lineage without modern Ten-God translation | `references/system-cards/luming-nayin.md` |

Aliases, if accepted by the executable registry, normalize to one of these
canonical systems before the transaction begins.

## Selection responsibilities

1. The caller records subject references, calculation object, dimensions,
   horizon, granularity, continuity, present/corrected facts, evidence
   questions, and cross-check intent in the extensible frame.
2. An explicitly user-requested executable method has first precedence; a valid
   same-reading continuation has second precedence.
3. Otherwise the resolver compares object, horizon, dimensions, available
   structured inputs, unsupported assumptions, and stable default priority.
4. It returns ambiguity only when equally suitable executable providers from
   materially distinct calculation lineages remain.
5. A validation-only provider cannot be selected for an automatic cast; it
   requires complete supplied chart data.
6. A caller-proposed `system` that cannot satisfy the frame is rejected with a
   recommended selection and per-provider reasons. Raw `query` text is never
   read by the resolver.
7. Do not promote source availability into fact readiness. A source pack can
   explain a rule without calculating the chart to which it would apply.
8. Do not use a second system merely to increase apparent confidence. Source
   relationships and counter-evidence remain visible in the prepared bundle.

The selected primary, considered providers, rejected reasons, and ambiguity
set are digest-bound in private transaction records and deliberately absent
from the public prepared response.

## Cross-system corroboration

Cross-book corroboration inside the primary system runs by default: the
evidence bundle already retrieves every applicable source pack and records
source relationships, and repeated derivative texts never count as
independent support.

Running a second calculation system requires one explicit purpose:
`caller_requested`, `unresolved_primary`, `material_source_conflict`, or
`distinct_compatible_fact_layer`. Without a purpose the transaction stays a
single-system reading. The caller supplies `cross_check_purpose` and optional
`requested_secondary_system` in the structured IntentFrame for caller-owned
purposes. The runtime may derive `unresolved_primary` only from an actually
unsupported requested dimension and `material_source_conflict` only from an
applicable selected `SourceRelationship(relation="conflict")`; neither purpose
is inferred from query wording.

A secondary system qualifies only when it comes from a genuinely independent
calculation lineage, supports the same calculation object, shares at least
one requested answer dimension, and either already has its required
structured inputs or is missing exactly one askable external fact. The
transaction honors an explicit secondary target or deterministically orders
untargeted candidates by declared `default_priority` and stable system ID. One
missing indispensable fact enters the existing intake/resume flow only for an
explicit caller request. Automatic purposes never block a valid primary
reading for secondary inputs, and two or more missing secondary inputs leave
the primary reading single-system.

The secondary calculation, evidence, and judgment stay in their own
namespaced cross-check record with complete calculation, side-local fact
index, evidence, judgment, lineage, selection audit, and independent digests.
Nothing merges into the primary fact index, evidence bundle, or gateway
digests, and no symbol translation or duplicate voting exists. The prepared
response exposes a privacy-bounded view of both sides plus the exact shared
dimensions. It does not manufacture agreement or conflict.

The current caller submits one `cross_check_review` after comparing the two
fact/evidence sides. Each shared dimension must be classified as `agreement`,
`conflict`, `primary_only`, `secondary_only`, or `unresolved`, with separate
primary and secondary references, visible text/span, priority system, and
priority reason. `complete` validates only structure, side-local provenance,
prepared dimensions, spans, digests, and priority boundaries. It rejects
`unassessed`; it never compares prose strings, votes, or averages systems. A
`secondary_only` result is allowed only when the prepared primary judgment
records that exact dimension as unsupported. The accepted record persists the
complete cross-check and caller review while leaving the primary gateway
digests unchanged.

The transaction returns missing field IDs mechanically. The caller phrases any
question and maps the reply; the capability registry never interprets reply
wording.

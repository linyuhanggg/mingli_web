# Life K-line Runtime facts v1

`mingli-life-kline-facts-v1` is the internal Runtime authority contract for
the product-facing life K-line series. It deliberately does not claim that a
drawable series exists.

## Current authority boundary

The signed Runtime can calculate the following ordered Bazi time facts:

- major-luck direction, sequence, start age, and age intervals under the
  declared luck-cycle rule profile;
- Gregorian-year, month, and civil-day transit layers with exact calendrical
  boundaries, stems/branches, Ten Gods, relations, and rule traces;
- a near-time mechanism stack across major luck, year, month, and day.

Those facts are temporal keys and categorical mechanisms. They are not one
numeric measure, are not empirically calibrated as a cross-period scale, and
cannot lawfully be converted into a 0–100 score or candle values. In
particular, element inventory, Ten-God counts, relation counts, evidence
counts, and UI fixtures are not substitute measures.

The current Runtime therefore emits only
`status=unavailable_algorithm_gap`, an empty `series`, unavailable value-axis,
candle, and change records, and the exact machine-readable gap below. A host
must project this to an unavailable/empty state. It must not unlock a ready
chart.

## Identity and cache semantics

`identity` binds the result to all of the following:

- opaque `subject_ref` and immutable `profile_version_id`;
- Runtime release and exact Runtime source commit;
- signed Runtime manifest digest;
- profile-specific source fact digest;
- `schema_version` and `contract_version` through `cache_identity`.

No clock or generated timestamp participates. Repeating the same identity
produces byte-for-byte equal JSON. Changing any bound identity changes the
cache identity. A host must not reuse this result across profiles, fact
digests, Runtime releases, or manifests.

## Field semantics

| Field | Meaning |
| --- | --- |
| `candidate_time_axes[]` | Existing ordered time keys only. `series_ready=false` is invariant in v1. |
| `value_axis.available` | Always `false`; no unit, range, polarity, or comparable measure exists. |
| `candles.available` | Always `false`; no authoritative field set or sampling rule exists. |
| `change.available` | Always `false`; direction and delta require authoritative close values. |
| `series` | Always empty. Numeric points or candle fields are contract violations. |
| `algorithm_gap.user_input_can_resolve` | `false`; asking for more birth/profile input cannot close an algorithm-authority gap. |

## Exact ALGO-GAP

Missing algorithm-authority inputs:

1. a versioned definition of one comparable measure;
2. a calibration and validation corpus for that declared measure.

Missing semantics:

1. unit and range;
2. polarity;
3. cross-period comparability;
4. open/close sampling points;
5. intra-period high/low resolution;
6. flat-direction threshold;
7. missing-observation policy.

Any future ready contract must version the measure, unit/range/polarity,
sampling rule, comparability key, point-level fact refs, ProfileVersion,
ReadingDocument version, Runtime release and manifest, and source fact digest.

The minimum implementation slice is:

1. freeze one comparable measure and its evidence authority;
2. implement it as a deterministic, versioned pure function;
3. freeze candle sampling semantics, or remove OHLC from the product contract;
4. derive direction and delta only from authoritative close values;
5. validate boundaries, missingness, idempotency, and calibration before any
   result can use a ready status.

Until all five steps are complete, `life-kline-series/v1` at the Backend/Web
boundary may expose only an unavailable projection of this Runtime fact.

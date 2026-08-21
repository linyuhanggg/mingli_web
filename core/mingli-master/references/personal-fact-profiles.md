# Personal Fact Profiles

Use this file only when the user explicitly wants a reusable personal baseline, long-running calibration, or repeated readings from the same birth data. A profile can speed up future work, but it is not a substitute for a fresh adapter check on serious readings.

## Profile Template

```json
{
  "profile_id": "stable local id",
  "scope": "bazi | ziwei | mixed",
  "consent": "explicit user request to reuse this baseline",
  "source": "user_provided | adapter_generated",
  "adapter_version": "tool/version/commit",
  "created_at": "ISO-8601",
  "input": {
    "birth_datetime_or_four_pillars": "",
    "birth_datetime": "",
    "birthplace": "",
    "timezone": "",
    "location": "",
    "calendar_type": "",
    "sex_or_gender_convention": "",
    "gender": "",
    "longitude": null,
    "latitude": null,
    "coordinate_source": "",
    "coordinate_accuracy_meters": null,
    "zi_hour_policy": "midnight",
    "time_basis_policy": "civil | longitude_mean_solar-v1 | local_apparent_solar-v1",
    "missing_or_ambiguous": []
  },
  "calendar_normalization": {
    "civil_datetime": "",
    "lunar_date": "",
    "leap_month_status": "",
    "ganzhi": {},
    "solar_terms": "",
    "timezone_location": ""
  },
  "bazi": {
    "four_pillars": [],
    "hidden_stems": {},
    "ten_gods": {},
    "nayin": {},
    "month_command": "",
    "seasonal_profile": "",
    "tiaohou_markers": [],
    "luck_cycles": []
  },
  "ziwei": {
    "palaces": {},
    "ming_shen": {},
    "stars": {},
    "sihua": {},
    "major_limits": []
  },
  "known_caveats": [],
  "do_not_store": [],
  "refresh_policy": "revalidate before serious readings or when adapter/rule profile changes"
}
```

## Rules

- The reusable baseline passed to `RuntimeContext.subject_profiles` is a flat
  mapping keyed by the provider manifest's input field ids (for example
  `birth_datetime_or_four_pillars`, `longitude`, `latitude`,
  `coordinate_source`, `time_basis_policy`). Keys that are not declared input
  fields of the routed capability are dropped by the public interface, so a
  profile that uses legacy slot names (such as `birth_datetime` alone for
  Bazi, or `true_solar_time_policy`) will not satisfy the required input group
  and will re-ask for birth data. Use the manifest field ids.
- Store only the minimum facts the user asked to reuse.
- Keep raw personal identifiers out unless they are necessary for the calculation and the user wants them stored.
- Mark user-provided charts as `source=user_provided`; do not claim tool verification.
- Revalidate profiles when adapter version, rule profile, timezone policy, birthplace, calendar type, leap-month policy, or time-basis policy changes.
- For accuracy work, link the profile id from the case log but keep scored outcomes in the case log, not inside the personal profile.
- If a profile is incomplete, use it as a prompt to request missing fields, not as a fact layer.
- A profile may carry a `time_basis_policy` of `local_apparent_solar-v1` only with measured `longitude`, `latitude`, and `coordinate_source`; otherwise the public interface returns a structured NeedInput instead of silently falling back to civil time.

# Wave 0 Bazi/Ziwei legal golden baseline

This receipt covers only the accepted `mingli-master` Runtime canonical facts at
`fdfbee2ead72145e1c67daad6eba7f63cf4b60e6` (tree
`e36435068294f9501cc06eb882fd3ddbffa01542`). Candidate OSS engine output is
reserved for future differential `actual` values and was not used to define any
expected value.

## Coverage

- Bazi: normal civil time, the two sides of the exact Li Chun boundary, both
  late-Zi policies, historical Shanghai DST, and apparent-solar hour crossing.
- Ziwei: normal civil time, the first day of a lunar leap month, both late-Zi
  policies, and apparent-solar hour crossing.
- Every input location is explicitly synthetic. Each case carries adapter,
  engine, policy, time-basis, schema, baseline commit/tree, source references,
  and structured canonical facts with complete provenance.

## Replay

```bash
PYTHONDONTWRITEBYTECODE=1 "$MINGLI_PYTHON" -B \
  core/mingli-master/scripts/test_oss_chart_wave0_golden_baseline.py
```

The focused suite directly compares structured canonical facts, schema/version,
and provenance. It also validates manifest integrity, unique IDs, required
boundary coverage, synthetic-only inputs, raw third-party container exclusion,
and two exact deterministic replays per case. The machine-readable result is
`replay-receipt.json`.

## Environment gap

None for the admitted Runtime. The host `python3` lacked pinned `sxtwl`; replay
therefore used the existing pinned Mingli Runtime Python as required by the
repository contract. No dependency or `.runtime/**` file was changed.

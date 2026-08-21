# Da Liu Ren 720 Transmission Table Notice

- Vendored file: `liuren-720-transmissions.json`
- Upstream: `look-fate/liuren-ts-lib`, `src/sanchuan.json`
- Upstream commit: `8e9a7b53245c8ae19fa12773087e1f90b3376d5e`
- Upstream license: Apache-2.0; see `LICENSE.Apache-2.0.txt`
- Vendored SHA-256: `f4e77cce9d72c000aae228d1d07ed1ca9361baf3fbbad9f41f5fbe4ca346483b`

The table has 60 sexagenary days by 12 first-lesson upper branches, for 720
records. It is a deterministic lookup witness, not an ancient-text source and
not an empirical validation dataset. `liuren_fact_adapter.py` independently
builds the plate and four lessons and calculates all nine transmission methods
from the selected 《大六壬大全》/WYG rule profile. This table is never allowed to
select or override a transmission.

The full local audit finds four method-label disagreements and sixteen
transmission-result disagreements. The fourth label disagreement is
`丁卯/offset 4`; all sixteen result disagreements occur in 涉害 selection.
The adapter preserves both results under audit/conflict metadata and emits the
auditable classical calculation as primary.

Normal cast payloads contain only compact audit counts to avoid wasting model
context. Run `python3 scripts/liuren_fact_adapter.py audit-table` when the full
disagreement list is needed.

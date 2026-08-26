# Runtime Dependencies And Provenance

## Tested Deployment

| Layer | Tested version | Use |
|---|---:|---|
| Dedicated Mingli Python | 3.14.6 | All production reading transactions and adapters |
| Hermes Python | 3.12.x | Gateway process only; it does not calculate a reading |
| `PyYAML` | 6.0.3 | Structured corpus manifests and public contracts |
| `sxtwl` | 2.0.7 | Solar terms, sexagenary calendar and lunar conversion |
| `astronomy-engine` | 2.1.19 | Versioned geocentric true-ecliptic ephemeris for Xingming |
| `cnlunar` | 0.2.4 | Pinned engineering implementation of selected Xieji almanac tables |
| Node.js | 26.3.0 | Vendored Ziwei runtime |
| IANA `zoneinfo` | Host database | Declared timezone conversion |

The v2 engine requires Python 3.10 or newer. Production uses
`~/.local/share/mingli-master/venv/bin/python`, selected by
`scripts/run_reading_transaction.sh`. There is no system-Python fallback.
`MINGLI_PYTHON` may override the path only when it points to a runtime that
passes the same dependency check.

Both the dependency probe and the production transaction execute with Python
isolated mode. The production bootstrap discards cwd and `PYTHONPATH`, imports
and validates the pinned dependencies first, then appends the resolved artifact
`scripts` directory and invokes `reading_transaction.py` with `runpy`. A
same-named `yaml.py` or `cnlunar.py` in the checkout, cwd, or `PYTHONPATH`
therefore cannot replace the validated runtime dependency.

The Ziwei adapter invokes the vendored Node runtime with the fixed
`--jitless` flag.  This keeps V8 compatible with hardened service units that
enforce `MemoryDenyWriteExecute=yes`; the flag is not caller-configurable.
The pinned chart regression suite verifies that default and JIT-less execution
produce the same deterministic JSON facts.

For a clean checkout, install the locked Python runtime dependencies before
running validation. `scripts/provision_runtime.py` creates the dedicated venv
from the version-pinned `requirements.txt`:

```bash
python3 scripts/provision_runtime.py
scripts/run_reading_transaction.sh --help
```

Tests resolve scripts from the checkout itself. Equality checks against an
installed Hermes copy belong to deployment verification and are not required
for repository tests.

## Vendored Dependencies

### iztro

- Upstream: `SylarLong/iztro`
- Version: `2.5.8`
- Reviewed upstream commit: `2dfe3ecb41d725b2bea1084bbdfe4dd655e37b13`
- License: MIT, stored at `vendor/iztro-2.5.8/LICENSE`
- Runtime SHA-256: `4b8eca323e5d4291471567c62255a2166471c55c77ebe8f0d2d38240e69d12b1`
- License SHA-256: `e6c7b6e313cbda3135b41bccc66c98be132cb8319d0d465903d17e669e748b36`

The adapter records the iztro rule profile and warns that true solar time and
school-specific brightness/four-transformation conventions may differ.
V5.1 uses adapter `1.1.0` and records a machine-readable engine contract:
`algorithm=default`, `fixLeap=true`, `yearDivide=normal`,
`horoscopeDivide=normal`, and `ageDivide=normal`. At 23:00, both policies keep
iztro's late-Rat index 12; `midnight` selects `dayDivide=current`, while
`late-zi-next-day` selects `dayDivide=forward`. Requested major-limit, annual,
and monthly palace/star/four-transformation placements remain facts-only.

### Early Luming/Nayin

`reading_engine.luming` adds no external runtime dependency. It consumes the
same pinned `sxtwl`/IANA calendar facts used by Bazi and binds the shared
calendar digest when birth data are available. Its versioned tables cover all
sixty Jiazi plus ten-stem Lu/Tianyi and twelve-branch Yima lookups; disputed
Taiyuan and Renyuan conventions remain separately named source profiles.

### Astronomy Engine

- Upstream: `cosinekitty/astronomy`
- Version: `2.1.19`
- Reviewed upstream commit: `61dc07020aaa6885d2c7f688a4d82beaf6edb9ef`
- License: MIT, stored at `vendor/astronomy-engine-2.1.19/LICENSE`
- PyPI sdist SHA-256: `95b797b87b659adc0602a6a205143ce5a10451664e80650bb7cd8ba3c8f1f02b`
- License SHA-256: `b4d9dd0fd80fce3879c4cd9e3754364f74fc5ec046f33276475ba3876785c8b7`
- Numerical data model: versioned coefficients embedded in the distribution;
  there are no separately downloaded data files.

`reading_engine.ephemeris_core` records this provenance in every result and
binds its declared coordinate convention and observer metadata into the
ephemeris digest.

### cnlunar

- Upstream: `OPN48/cnlunar`
- Version: `0.2.4`
- Reviewed upstream commit: `71e448a3ad4fa17bb731a57637ee0728e6f53d37`
- License: MIT, stored at `vendor/cnlunar-0.2.4/LICENSE`
- PyPI wheel SHA-256: `19689288604e86a3ef48dba23d39d6a7efbd5efabcb3923d4d656319762af4ea`
- Provenance: `vendor/cnlunar-0.2.4/PROVENANCE.json`

Runtime admission parses the provenance `reviewed_files` mapping and requires
the complete seven-module wheel contract. It hashes the installed package
entrypoint plus `lunar.py`, `config.py`, `solar24.py`, `tools.py`, `holidays.py`,
and `demo.py`, and compares every byte digest with that mapping. Imports must
also originate below the interpreter's exact `purelib`/`platlib` roots. A
missing key, malformed digest, missing installed file, origin mismatch, or
byte-level mismatch fails closed even when package metadata still reports
version 0.2.4.

### Da Liu Ren 60 x 12 table

- Upstream: `look-fate/liuren-ts-lib`
- Locked commit: `8e9a7b53245c8ae19fa12773087e1f90b3376d5e`
- License: Apache-2.0
- Table SHA-256: `f4e77cce9d72c000aae228d1d07ed1ca9361baf3fbbad9f41f5fbe4ca346483b`
- Notice SHA-256: `2199bf8ae17dd13919efce112183c4001f23222b5e1e79e1101185533212d327`
- License SHA-256: `26049b4e4af10b0c5ad392100980605ce14ef532d22197ab621fe605156adf75`

This table is an audit witness only. The local classical nine-method algorithm
is authoritative because the full 720-case audit found method and transmission
disagreements with the table.

## Reference-Only Projects

FateCat, Mingyu, fortune-skill, MingLi-Bench, `china-testing/bazi`,
`jinchenma94/bazi-skill` and similar projects contributed design or evaluation
ideas only unless a vendored item is listed above. Code with an absent,
noncommercial or otherwise incompatible license is not copied into the runtime.

## Deployment Checks

```bash
~/.local/share/mingli-master/venv/bin/python --version
~/.local/share/mingli-master/venv/bin/python -c "import importlib.metadata as m; print(m.version('PyYAML'), m.version('sxtwl'), m.version('astronomy-engine'), m.version('cnlunar'))"
node --version
shasum -a 256 vendor/iztro-2.5.8/iztro.min.js
scripts/run_reading_transaction.sh --help
```

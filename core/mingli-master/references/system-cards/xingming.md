# 七政四余 / 星命 (xingming)

## Deterministic provider

- Provider: `mingli-master.xingming.v1`; mode: `calculation`.
- Inputs: birth datetime, IANA timezone, named location, WGS84 longitude/latitude, and coordinate source through the shared calendar core.
- Facts: seven ephemeris-backed luminaries, four separately identified residual points, tropical longitudes, twelve equal houses, Ming/Shen degrees, ten-stem transformations, the 100-year-6-month Dongwei/Bailiu table, and requested annual limit/transformations.
- Validation: natal, calendar, and ephemeris digests are bound; recalculation detects changed positions, houses, transformations, and limits. A follow-up reuses only the natal calculation and receives a new result digest.
- Evidence boundary: `qizheng-siyu-tianjing`, `qizheng-quanshu-dacheng`, and `minghai-quanbian` remain blocked from first-line evidence because their provenance is not release-ready.

## Deterministic astronomy boundary

Astronomy-dependent facts use `reading_engine.ephemeris_core` schema
`mingli-ephemeris-v1`, backed by pinned Astronomy Engine 2.1.19. The service
binds the validated shared calendar digest, observer coordinates and source,
engine/license provenance, and the declared tropical geocentric true
ecliptic-of-date convention. Classical texts supply interpretation and school
rules; ancient tables are never substituted for the numerical ephemeris.

The selected V5.1 convention is tropical, geocentric true ecliptic-of-date for
the seven observed bodies. Ming is the local eastern ecliptic/horizon
intersection and Shen its exact opposition; houses are equal 30-degree houses.
Under the selected Guolao convention, Luo Hou is the interpolated descending
lunar node (`交初`) and Ji Du is its exactly opposing ascending node (`交中`),
while Yuebo uses interpolated lunar-apogee events. Ziqi preserves the 10228-day mean cycle
in 《星学大成》 and binds its absolute phase to the dated Ming-almanac value
documented by Niu Weixing (JDN 2280289.5, 284.58 degrees). The calibration is
versioned and hash-bound in `xingming-ziqi-calibration-v1.yaml`; it is a
classical mean point, never an observed astronomical body. All four residual
points remain separately named and their profiles are never silently
exchanged. Fixed-star mansion mapping is not applied until a source-verified
precession catalog is selected.

Thirty frozen reference charts cover ordinary cases plus date, location, and
historical-timezone boundaries. The machine-readable provider and algorithm
source audits must both pass before this route is registered in production.

## Packs

| pack | title | best for | do not use for | caveat |
|---|---|---|---|---|
| `xingming/guotian-jing` | 果天经/果老星宗 | See index.md | See safety-and-versioning.md | 版本/作者存疑（托名张果）；'果天经'之名易与其他星命典籍混淆，需先正名为《果老星宗》。 |
| `xingming/xingming-suyuan` | 星命溯源 | See index.md | See safety-and-versioning.md | 四庫全書本；題唐張果傳文系統，需在蒸餾端標注題撰性質。 |
| `xingming/xingxue-dacheng` | 星学大成 | 七政四余大全式资料库、星曜图例、十二宫法、十干变曜、观星节要、空实夹拱与诸家限例 | 语言模型手排星盘、星度、行限或岁差校正; 把古星度表直接当现代天文位置 | 维基文库《星学大成（四库全书本）》主页面 + 卷一至卷三十；所有星度计算必须走 adapter。 |

## Runtime use

This card is capability and source metadata for selecting the transaction
system before `prepare`. During a live reading, use only the bounded evidence
returned by the transaction; do not load packs or run a separate corpus search.

# 八字子平 (bazi)

## Deterministic calendar boundary

Birth, transit, and near-time facts consume
`reading_engine.calendar_core` schema `mingli-calendar-normalization-v2`.
The fact layer preserves the IANA timezone and historical offset, coordinate
source, leap-month state, exact Jie/Li-Chun instants, and the declared Zi-hour
and time-basis conventions. The time_basis block records the selected policy
(`civil`, `longitude_mean_solar-v1`, or `local_apparent_solar-v1`), the
longitude correction, the equation of time, the total correction, the local
mean and apparent solar datetimes, the versioned EoT algorithm, and a
double-hour boundary analysis. Every timed provider result binds the shared
`calendar_digest`; classical texts interpret those facts but never recalculate
them.

## V5.1 fact horizon

The Bazi adapter emits immutable natal facts plus explicitly requested year,
month, or day layers. Each temporal layer carries the active major-luck
interval, stem Ten God, hidden stems, typed branch relations, exact calendar
boundary, structural candidates, and a source-bound seasonal/Tiaohou delta.
Strength, structure, following, and transformation remain candidate facts for
classical adjudication; the calculator never emits a hard verdict for them.

Fortune is a bounded civil-day view over the same `natal_fact_digest`, not a
second simplified natal system. The independently validated Shensha subset is
kept under `shensha_auxiliary`; it cannot override month command, structure,
strength, Tiaohou, Ten Gods, luck cycles, or transit facts.

## Core Decision Stack

Before choosing a single bazi pack, read `references/matrices/bazi-core-decision-stack.md` and `references/matrices/bazi-core-decision-stack.yaml`.

The stack order is:

1. deterministic bazi fact layer and `calendar_normalization`;
2. `sanming-tonghui` / `yuanhai-ziping` for entry,日主、月令、十神、岁运粗框架;
3. `ziping-zhenquan` for 月令格局、相神、成败救应;
4. `ditiansui-chanwei` for 旺衰、气势、通关、病药;
5. `qiongtong-baojian` for 调候、寒暖燥湿;
6. 大运流年 activation;
7. 神煞 only as auxiliary after `shensha-*` matrices;
8. `shenfeng-tongkao` / `mingli-yueyan` for later critique and anti-template checks.

Do not let 神煞, a single quote, or a daily-fortune motif override 月令、格局、旺衰、调候、十神 and 大运流年.

## Packs

| pack | title | best for | do not use for | caveat |
|---|---|---|---|---|
| `bazi/ditiansui-chanwei` | 滴天髓阐微 | 日干旺衰精细判断（含强弱、得令失令、有根无根）; 五行气势 / 通关 / 病药 / 寒暖燥湿 / 调候 在旺衰框架内的应用; 顺、反、从、化、战、合、君、臣、母、子等气势格局 | 排盘事实计算（不替代 tool.bazi.paipan）; 月令格局成败救应（不替代《子平真诠》）; 调候用神细则（不替代《穷通宝鉴》） | - Batch D1 完成全书覆盖型文件组创建。源文件：references/fulltext/bazi/ditiansui-chanwei/fulltext.md。 - source_status 维持 partial：维基文库整理本与古书网本对照未逐章复核。 - 三层切分（[原]/[任注]/[案例]）需要逐章人工复核；当前 normalized 文本... |
| `bazi/mingli-yueyan` | 命理约言 | See index.md | See safety-and-versioning.md | 本轮覆盖的是精选/通行四卷本，不声称等同所有清抄本或全本异本；HTML 录入须以后续 PDF/OCR 或馆藏影印校对。 |
| `bazi/qiongtong-baojian` | 穷通宝鉴 | 十干日主在十二月令的调候用神取法; 寒暖燥湿 / 火暖水润 / 金白水清 等调候组合; 与《滴天髓阐微》"寒暖燥湿"章互参 | 排盘事实计算（不替代 tool.bazi.paipan）; 旺衰、气势、通关（不替代《滴天髓阐微》）; 月令格局成败（不替代《子平真诠》） | - Batch D1 完成全书覆盖型文件组创建。源文件：references/fulltext/bazi/qiongtong-baojian/fulltext.md（维基文库整理本）。 - source_status 维持 partial：维基文库整理本与清刊本影印未逐章对校。 - 余春台编订本是否包含全部 100 个 "十干 × 月令" 子目，需逐目核对。 |
| `bazi/sanming-tonghui` | 三命通会 | 八字综合检索与术语溯源; 月令格局基本框架查找; 神煞汇总查询 | 排盘事实计算（不替代 tool.bazi.paipan）; 调候用神细则（应优先《穷通宝鉴》）; 月令格局成败救应的精细推演（应优先《子平真诠》） | - 作者万民英归属、版本系统（万历本 vs 四库本 vs 民国整理本）需进一步核验。 - 四库本与万历原刊本在编次、收录子目上有差异，需逐卷复核。 - "继善篇""喜忌篇""玄机赋"等通行段落是否原属本书 / 抑或转录他书，需复核。 - 神煞清单数量存在不同抄本差异，详见 terms.md 的神煞分组。 - 卷八卷九的"日时断"几百条，聚合到"日组"粒... |
| `bazi/shenfeng-tongkao` | 神峰通考 | 张神峰对子平旧说的批判，如五星、纳音、合婚、魁罡、日贵等谬说辨析; 动静、盖头、病药、雕枯旺弱、损益生长等理论术语; 正官、财、杀、印、伤食、从格等子平格局讨论 | 直接给真人作寿夭疾病刑伤硬断; 不经排盘工具手算八字; 把辑录古赋当作张楠本人观点而不标层 | 7 个 CTP 页全部抽取；chapter-map 为 3027 行级单元，quote-index 取 300+ 条跨页短引。 |
| `bazi/yuanhai-ziping` | 渊海子平 | 子平法体系源流与早期术语溯源; 四柱八字、十神、月令、格局雏形的基本框架; 早期大运 / 流年 / 神煞用法 | 排盘事实计算（不替代 tool.bazi.paipan）; 月令格局成败救应的精细推演（应优先《子平真诠》）; 旺衰、气势、通关、病药（应优先《滴天髓阐微》） | - Batch 1A-1 返工为全书覆盖型文件组结构。source_status 维持 partial（四库本影印未逐章复核）。 - 作者"徐大升"/"徐子平"身份、序跋、各家书目记载需交叉验证。 - 本书与早期禄命文献的段落继承关系需逐段对读。 - "继善篇""喜忌篇"等通行段落的归属待考。 - 四库本与万历/明清增补本在卷次上的差异尚未完成复核。 |
| `bazi/ziping-zhenquan` | 子平真诠 | 月令用神与格局成败救应; 四吉神/四凶神顺逆用法; 正官、财、印、食神、七煞、伤官、阳刃、建禄月劫取运框架 | 不排盘、不手算大运流年; 不把富贵贫贱等古代评价语用于现实决定论; 不把徐乐吾评注或现代强弱派解释冒充沈氏原典 | 本 pack 以东里书斋繁体二校本为 normalized 全文底本，含 47 个沈氏原典核心章节、命例附录和序跋。 规则层只抽取一至四十七核心章节；电子版前言、凡例、读后附记、序跋、命例附录只作为版本说明和旁证。 仍需与 Wikimedia/NLC 影印 PDF 及 CTP 锚点逐段校勘。徐乐吾评注不进入本 pack 原典规则层。 |

## Runtime use

This card is capability and source metadata for selecting the transaction
system before `prepare`. During a live reading, use only the bounded evidence
returned by the transaction; do not load packs or run a separate corpus search.

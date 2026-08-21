---
title: 玉照神应真经
slug: yuzhao-shenying
system: luming-nayin
school:
  - 早期禄命
  - 神煞断语
  - 干支纳音断语
  - 三主（年/胎/月/日/时）法
source_layer: primary
source_status: normalized_ready
source_links:
  - https://ctext.org/wiki.pl?if=gb&remap=gb&res=787826
version_notes: |
  《玉照定真经》一卷，旧题晋郭璞撰、张顒注。
  《四库全书总目提要》考订实为后世（南宋之前）依托之本，注文与正文均出张顒一人之手。
  《隋志》《唐志》《宋志》及诸家书目皆不著录，惟《永乐大典》存其全帙，今四库本由此辑出。
  全书为单卷，注文与正文混排，赋语形式，每条主述年、月、日、时、胎"三主"或"五主"配合干支纳音/神将的吉凶断语。
  本 pack 取四库本（CTP 子部·术数类）为底本。
depends_on:
  - li-xuzhong-mingshu
  - luoluzi-sanming
informs:
  - wuxing-jingji
  - sanming-tonghui
core_use_cases:
  - 早期禄命断语风格的代表（"以年/胎/月/日/时为主"的多主参看）
  - 干支神将（青龙/白虎/勾陈/朱雀/玄武等）断语溯源
  - 与《李虚中命书》《珞琭子三命消息赋》对读
  - 神煞断语的早期形态（六害/三刑/空亡/魁罡）
not_for:
  - 排盘事实计算（不替代 tool.bazi.paipan）
  - 子平法格局成败（应优先《子平真诠》）
  - 月令调候（应优先《穷通宝鉴》）
  - 现代医学疾病诊断（书中"病"的描述只能作文化研究参考）
  - 把"晋郭璞撰"当作信史（实为依托）
extraction_targets:
  - concepts
  - terms
  - rules
  - cautions
  - quote_index
conflict_policy: |
  与同体系其他典籍冲突时按问题类型裁判（详见 matrices/conflict-policy.md §1.4）：
  - 与《李虚中命书》冲突 → 二者并行，本书断语风格更接近"经验断语集"。
  - 与《五行精纪》冲突 → 以《五行精纪》为汇编正源，本书作早期片段。
  - 与子平法（《渊海子平》及以下）冲突 → 本书是禄命残留，子平为主流。
  - 涉及"军人/盗贼/僧道/孤寡"等社会身份断语 → 必须 reframe 为文化研究，不作铁口断。
validation_notes: |
  - 作者归属（晋郭璞撰系伪托；张顒生平不可考）须在待核验项中。
  - 本地 normalized source 已完整取得；与永乐大典/影印本的逐句对校待补。
  - 注文与正文层级标注（注文在原文以"注云"或圆括号"〔〕"区隔）需统一。
  - 涉及寿夭/盗贼/官刑等极端断语必须严格 reframe。
modern_notes: |
  本书在明清后逐渐被《五行精纪》《三命通会》等汇编替代。
  现代禄命研究价值在于其早期"多主参看"的方法论，而非具体断语。
---

# 玉照神应真经 Reference Pack（index）

> 本文件是《玉照定真经》参考包的入口索引。
> 详细内容分布在 `chapter-map.md / terms.md / rules.md / procedures.md / quote-index.md / validation.md`。

## Source

- **作者**：旧题晋·郭璞撰；张顒注。四库提要考为南宋以前依托之本。
- **版本系统**：《钦定四库全书》子部·术数类本（自《永乐大典》辑出）。
- **在线索引**：https://ctext.org/wiki.pl?if=gb&remap=gb&res=787826
- **结构**：单卷一册，赋文形式（注文与正文混排）。约 200 余条断语。
- **复核状态**：`normalized_ready / verified=false`。本地全文已取得；CTP/四库影印逐条对校待补。

## Position In Lineage

- **在禄命纳音体系中的位置**：早期禄命断语集的代表，与《李虚中命书》《珞琭子三命消息赋》并列为禄命三源之一。
- **上游**：
  - 《李虚中命书》：年柱为主的禄命法。
  - 《珞琭子三命消息赋》：早期赋文骨架。
- **下游**：
  - 《五行精纪》：宋代禄命汇编，吸收本书部分断语。
  - 《三命通会》：明代汇编巨著，间引本书。

## Loading Guide

1. **默认只加载本文件** `index.md`。
2. 需要章节 → `chapter-map.md`。
3. 需要术语 → `terms.md`。
4. 需要判断规则 → `rules.md`。
5. 需要可操作流程 → `procedures.md`（极简，禄命排盘依赖 `tool.bazi.paipan`）。
6. 需要短引 → `quote-index.md`。
7. 需要校验 → `validation.md`。

## File Map

| 文件 | 职责 |
|---|---|
| [index.md](./index.md) | 入口索引 |
| [chapter-map.md](./chapter-map.md) | 单卷分段地图（断语主题归类） |
| [terms.md](./terms.md) | 术语抽取（神将/神煞/三主） |
| [rules.md](./rules.md) | 判断规则 |
| [procedures.md](./procedures.md) | 流程（仅排盘+查断） |
| [quote-index.md](./quote-index.md) | 短引索引 |
| [validation.md](./validation.md) | 覆盖率与待办 |

## Routing

详见 matrices/routing-matrix.md §2.4（禄命纳音类）。
事实层未确定的盘必须先调用 `tool.bazi.paipan`。

## 冲突裁判

详见 frontmatter `conflict_policy` 与 matrices/conflict-policy.md §1.4。

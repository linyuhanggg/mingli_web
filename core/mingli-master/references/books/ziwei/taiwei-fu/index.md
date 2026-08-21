---
title: 太微赋
slug: taiwei-fu
system: ziwei
school:
  - 紫微斗数
  - 古赋骨架
  - 星曜入庙失度
  - 格局总论
source_layer: primary
source_status: partial
source_links:
  - https://zh.wikisource.org/zh-hant/太微賦
version_notes: |
  《太微赋》是紫微斗数早期纲领性赋文，被《紫微斗数全书》卷一全文收录并在后世注释中反复引用。
  作者无明确署名，传为宋元间紫微术家所作。
  本 pack 取通行本一篇赋文（约 50 行）为主体，与《紫微斗数全书》卷一所载文本互校。
  赋文用语高度凝练，多以 4-8 字短句陈述星曜入庙失度、格局吉凶要诀。
depends_on: []
informs:
  - ziwei-doushu-quanshu
  - doushu-guanjian
core_use_cases:
  - 紫微斗数早期纲领与术语溯源
  - 星曜入庙/失度/落陷的判断口诀
  - 格局名（如金舆捧栉、玉袖天香、君臣庆会等）的源头
  - 与《增补太微赋》《斗数骨髓赋》对照阅读
not_for:
  - 排盘事实计算（不替代 tool.ziwei.bindisk）
  - 紫微星系的完整定义（应回查《紫微斗数全书》卷二）
  - 流年/大限断语的精细推演（应优先《斗数骨髓赋》）
  - 现代紫微派别（中州派、三合派、飞星派、四化派）的派系细则
  - 把"寿夭"等断语作铁口断
extraction_targets:
  - concepts
  - terms
  - rules
  - cautions
  - quote_index
conflict_policy: |
  与同体系其他典籍冲突时按问题类型裁判（详见 matrices/conflict-policy.md §1.7）：
  - 与《紫微斗数全书》冲突 → 以全书为完整体系，本赋为骨架源。
  - 与《增补太微赋》冲突 → 二者并行，以本赋为先出本。
  - 寿夭/疾病断语 → 仅作文化研究参考，不作铁口判断。
validation_notes: |
  - 本赋作者与年代尚无定论。
  - 通行本与《紫微斗数全书》卷一所载文本逐句比对待补。
  - 赋中"七杀临身命加恶杀，必定死亡"等极端断语必须 reframe 为吉凶倾向参考。
modern_notes: |
  现代紫微教学（中州派/紫云派/飞星派）多以本赋为入门口诀。
  其经验性断语不可直接套用为铁律；现代 commentary 不进入本 pack 原典层。
---

# 太微赋 Reference Pack（index）

> 本文件是《太微赋》参考包的入口索引。
> 详细内容分布在 `chapter-map.md / terms.md / rules.md / procedures.md / quote-index.md / validation.md`。

## Source

- **作者**：无明确署名，传为宋元紫微术家。
- **版本系统**：通行本（与《紫微斗数全书》卷一所收为同一系统）。
- **在线索引**：https://zh.wikisource.org/zh-hant/太微賦
- **结构**：单篇赋文（无章节划分），约 50 行，分两部分：
  - 总论（开篇至"各司其職，不可參差"）：纲领性陈述。
  - 例曰（"祿逢沖破"以降）：经验断语集。
- **复核状态**：`partial`。需与《紫微斗数全书》卷一文本逐句对校。

## Position In Lineage

- **在紫微斗数体系中的位置**：紫微斗数最早期的纲领性赋文之一，是后世骨髓赋、增补太微赋的源头。
- **上游**：无明确上游典籍（紫微斗数本身源流即与本赋同期）。
- **下游**：
  - 《紫微斗数全书》：卷一直接全文收录本赋，并附"增补太微赋"。
  - 《斗数骨髓赋》：体例与本赋相承，断语更详。

## Loading Guide

1. **默认只加载本文件** `index.md`。
2. 需要术语 → `terms.md`。
3. 需要判断规则 → `rules.md`。
4. 需要排盘流程 → `procedures.md`（极简，紫微排盘依赖 `tool.ziwei.bindisk`）。
5. 需要短引 → `quote-index.md`。
6. 需要校验 → `validation.md`。

## File Map

| 文件 | 职责 |
|---|---|
| [index.md](./index.md) | 入口索引 |
| [chapter-map.md](./chapter-map.md) | 单篇赋文分段地图 |
| [terms.md](./terms.md) | 术语抽取（星曜/格局） |
| [rules.md](./rules.md) | 判断规则（赋中断语） |
| [procedures.md](./procedures.md) | 流程（仅排盘+查赋） |
| [quote-index.md](./quote-index.md) | 短引索引 |
| [validation.md](./validation.md) | 覆盖率与待办 |

## Routing

详见 matrices/routing-matrix.md §2.7（紫微类）。
本 pack 是紫微斗数体系的"早期赋文骨架"。事实层未确定的盘必须先调用 `tool.ziwei.bindisk`。

## 冲突裁判

详见 frontmatter `conflict_policy` 与 matrices/conflict-policy.md §1.7。

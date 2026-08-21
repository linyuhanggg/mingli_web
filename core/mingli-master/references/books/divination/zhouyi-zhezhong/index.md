---
title: 御纂周易折中
slug: zhouyi-zhezhong
system: divination
school:
  - 易学
  - 经传
  - 康熙敕撰
source_layer: primary
source_status: partial
source_links:
  - https://zh.wikisource.org/wiki/%E5%BE%A1%E7%BA%82%E5%91%A8%E6%98%93%E6%8A%98%E4%B8%AD
version_notes: |
  清·李光地等奉康熙敕命编纂（康熙五十四年，1715），折中朱熹《周易本义》、程颐《伊川易传》及历代易学诸家说，
  为清代官方易学权威读本。通行本系统：四库全书文渊阁本，22 卷。
  本 pack 以维基文库整理本（CC BY-SA 4.0）为参考底本。
  全书结构：
    - 卷首：凡例 / 綱領（一二三）/ 義例（位 / 徳 / 應 / 比 / 中 / 才 / 卦主 等）
    - 卷一至卷十二：經文（六十四卦本義 + 程傳 + 集說 + 案語）
    - 卷十三至卷十五：繫辭上下傳
    - 卷十六至卷十七：説卦傳 / 序卦傳 / 雜卦傳
    - 卷十八至卷二十二：啟蒙（朱熹《易学启蒙》四篇 + 康熙诸臣案语）
depends_on:
  - huangji-jingshi
informs: []
core_use_cases:
  - 周易经传义理 + 象数注疏汇编（程朱二派为主，旁采诸家）
  - 64 卦卦爻辞解读（程传 + 本义 + 集说 + 案语 4 层结构）
  - 易学义例（位 / 徳 / 應 / 比 / 中 / 才 / 卦主 等概念框架）
  - 易学綱領（易书源流 + 易学传授 + 易理之奥）
  - 朱熹《启蒙》——河图洛书 / 蓍法 / 变占法 之康熙官方折中本
not_for:
  - 卜筮装卦操作（应转 `zengshan-buyi` 或 `meihua-yishu`）
  - LLM 手算占筮蓍法（蓍法虽收入啟蒙，但实操应由 `tool.divination.qiguagua` 处理）
  - 个人命术 / 八字推算（应转 `bazi/*`）
  - 取代经典原文阅读（本 pack 是注疏汇编的索引，非全文复制）
extraction_targets:
  - concepts
  - terms
  - rules
  - procedures
  - cautions
  - quote_index
conflict_policy: |
  - 与朱熹《周易本义》单行本冲突 → 本书为康熙官方折中本，以本义为主、程传为辅、集说为旁；
    与单行本義之差异属编纂层而非内容层；以官方折中本为准。
  - 与程颐《伊川易传》单行本冲突 → fulltext.md。
  - 与象数派（汉象数 / 邵雍）冲突 → 本书重义理而旁取象数；象数源头应转 `huangji-jingshi`。
  - 与卜筮派（京房 / 增删卜易）冲突 → 本书不涉占断实务；占法实务转 `zengshan-buyi`。
validation_notes: |
  - 本书 22 卷涉及 64 卦 + 系传 + 启蒙，文本量极大（约 1.4 MB）；
    本 pack 采用粗粒度策略：按卷次列条目，64 卦不逐卦展开。
  - 程傳 / 本義 / 集說 / 案語 四层文献结构，本 pack 仅给框架性概览，不复制注疏原文。
  - 與《周易本義》《伊川易傳》單行本之文本差異未在本 pack 復核。
  - 全部章节 `verified: false`。
modern_notes: |
  现代易学研究（朱伯崑、廖名春、黄寿祺等）多以本书为清代易学官方文献依据；
  本 pack 仅做导航，具体义理研究应回归原书 + 现代学术注疏。
---

## D2 Source Scope

- **source_lines**: 7976
- **structural_units**: 1582
- **scope**: 四库本维基文库整理源；含卷首、经传、启蒙与序杂卦等。
- **version_note**: 当前 D2 ready 表示本地 normalized source 已按标题全建图；经传/程传/本义/集说/案语层次仍需 production skill 进一步分层。
- **evidence_files**: `section-map.md`, `chapter-map.md`, `quote-index.md`


# 御纂周易折中 Reference Pack（index）

> 本文件是《御纂周易折中》参考包的**入口索引**。详细内容分布在 `chapter-map.md / terms.md / rules.md / procedures.md / quote-index.md / validation.md`。

## Source

- **作者**：清·李光地等奉康熙敕命编纂（康熙五十四年，1715）。
- **版本系统**：四库全书文渊阁本（清乾隆，22 卷）。
- **本 pack 底本**：维基文库整理本（CC BY-SA 4.0）。
- **复核状态**：`partial`。文渊阁本与单行《本义》《伊川易传》之文本差异未复核。

## Position In Lineage

- **在易学谱系中的位置**：清代官方易学权威读本；折中宋程朱二派与历代诸家。
- **上游**：周易经传 → 王弼《注》/ 孔颖达《正义》→ 程颐《伊川易传》→ 朱熹《周易本义》《易学启蒙》→ 元明易学诸家。
- **下游**：清代易学（毛奇龄、惠栋、张惠言等汉学派之反动 / 调和），现代易学研究之重要文献。

## Core Use Cases

- 64 卦卦爻辞义理 / 象数注疏（程朱为主）
- 易学义例（位 / 徳 / 應 / 比 / 中 / 才 / 卦主 等概念框架）
- 繫辭傳 / 説卦傳 / 序卦傳 / 雜卦傳 之诸家集说
- 朱熹《启蒙》之康熙官方折中本（河图洛书 / 蓍法 / 变占）
- 易学綱領 / 凡例（学易方法论）

## Not For

- 卜筮装卦实操（转 `zengshan-buyi` / `meihua-yishu`）
- LLM 手算占筮（蓍法实操应由 `tool.divination.qiguagua` 处理）
- 个人命术（转 `bazi/*`）
- 现代严格哲学论证（应回归原典 + 现代学术）

## Loading Guide

1. **默认只加载** `index.md`：拿 frontmatter / 卷次概览 / 路由。
2. **查具体章节** → `chapter-map.md`。
3. **查易学概念** → `terms.md`。
4. **查义理 / 象数判断原则** → `rules.md`。
5. **查解卦框架 / 蓍法** → `procedures.md`。
6. **查短引 + 出处** → `quote-index.md`。
7. **查覆盖率 / 版本状态** → `validation.md`。

## File Map

| 文件 | 职责 | 何时加载 |
|---|---|---|
| [index.md](./index.md) | 入口索引 + frontmatter + 卷次概览 + 路由 | 默认加载 |
| [chapter-map.md](./chapter-map.md) | 22 卷地图（卷首 + 64 卦 + 系传 + 启蒙） | 需要查具体章节 |
| [terms.md](./terms.md) | 易学义例 + 程朱核心概念 | 需要查术语 |
| [rules.md](./rules.md) | 解卦义理 + 象数判断原则 | 需要查判断规则 |
| [procedures.md](./procedures.md) | 解卦框架 + 启蒙蓍法（不实操） | 需要查操作流程 |
| [quote-index.md](./quote-index.md) | 短引索引 | 需要引用原文 |
| [validation.md](./validation.md) | 覆盖率 + 版本状态 | 需要校验覆盖率 |

## Routing

主 skill 收到易学义理 / 经传相关问题后：

1. **64 卦义理** → 本 pack `chapter-map.md` 卷一至卷十二
2. **繫辭传义理** → 本 pack `chapter-map.md` 卷十三至卷十五
3. **説卦 / 序卦 / 雜卦** → 本 pack `chapter-map.md` 卷十六至卷十七
4. **河图洛书 / 蓍法 / 变占** → 本 pack `chapter-map.md` 卷十八至卷二十二（啟蒙）
5. **易学义例（位 / 應 / 中 / 卦主）** → 本 pack `terms.md` + `rules.md` ZZR-02-*
6. **占断实务（金钱卦 / 体用）** → 转 `zengshan-buyi` / `meihua-yishu`
7. **象数源头（元会运世）** → 转 `huangji-jingshi`
8. **个人命术 / 八字** → 转 `bazi/*`
9. **蓍法实操**（数字起卦 / 蓍草起卦）→ 必须 `tool.divination.qiguagua`，**禁止 LLM 手算**

## 冲突裁判

详见 frontmatter `conflict_policy`。

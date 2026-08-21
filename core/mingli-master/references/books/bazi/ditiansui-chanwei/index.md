---
title: 滴天髓阐微
slug: ditiansui-chanwei
system: bazi
school:
  - 旺衰派
  - 气势生克
  - 通关调候
source_layer: primary
source_status: partial
source_links:
  - https://zh.wikisource.org/wiki/%E6%BB%B4%E5%A4%A9%E9%AB%93%E9%97%A1%E5%BE%AE
version_notes: |
  《滴天髓》原文托名京图（一说宋人撰，一说明初刘基注），任铁樵于清道光年间作《滴天髓阐微》注解，是子平旺衰派／气势生克派最具影响的注解本。
  本 pack 处理对象为任铁樵《阐微》本，文本结构有 **三层** 必须严格区分：
  - `[原]`：京图原文（含原注）
  - `[任注]`：任铁樵阐微之文
  - `[案例]`：任氏所举古今命例（八字 + 断语 + 验证）
  规则抽取仅限 `[原]` 与 `[任注]`；`[案例]` 仅在 quote-index.md 中作引用，不上升为 rules.md 的判断条文。
  通行版本仍有徐乐吾补注本、袁树珊《滴天髓补注》、孙正治点校本等多家，本次以任氏阐微原本为基。
depends_on:
  - yuanhai-ziping
  - sanming-tonghui
informs:
  - 现代旺衰派教学
core_use_cases:
  - 日干旺衰精细判断（含强弱、得令失令、有根无根）
  - 五行气势 / 通关 / 病药 / 寒暖燥湿 / 调候 在旺衰框架内的应用
  - 顺、反、从、化、战、合、君、臣、母、子等气势格局
  - 何知章式经验断诀
  - 通神论与六亲论的语料锚点
not_for:
  - 排盘事实计算（不替代 tool.bazi.paipan）
  - 月令格局成败救应（不替代《子平真诠》）
  - 调候用神细则（不替代《穷通宝鉴》）
  - 把任氏案例当作绝对断验铁律
  - 在缺乏现代医学事实的情况下作疾病 / 寿命 / 死亡硬断
extraction_targets:
  - concepts
  - terms
  - rules
  - procedures
  - cautions
  - quote_index
conflict_policy: |
  与同体系其他典籍冲突时按问题类型裁判（详见 matrices/conflict-policy.md §1.2）：
  - 旺衰、气势、通关、病药、寒暖燥湿 → 以本书为精修版主线。
  - 月令格局成败 → 以《子平真诠》为精修版，本书旺衰仅作旁证。
  - 调候用神 → 以《穷通宝鉴》为精修版，本书"寒暖燥湿"章作旁证。
  - 阴干顺逆十二长生说 → 任注主张"阴阳同生同死"，与《渊海子平》"阴干逆行"说冲突；本书提供精修视角，二说并陈。
  - [原] 与 [任注] 冲突时：以 [原] 为底，[任注] 为发挥；当 [任注] 引申过远（如个别玄学语）时回 [原] 字面。
validation_notes: |
  - Batch D1 完成全书覆盖型文件组创建。源文件：references/fulltext/bazi/ditiansui-chanwei/fulltext.md。
  - source_status 维持 partial：维基文库整理本与古书网本对照未逐章复核。
  - 三层切分（[原]/[任注]/[案例]）需要逐章人工复核；当前 normalized 文本已用 `> [注] 原注：...` / `> [注] 任氏曰：...` 标记，但 [案例] 多嵌入 [任注] 段中，未单独切层。
  - 任氏所引古今命例的真伪、纪年、人物身份多不可考，不入规则层。
modern_notes: |
  现代旺衰派（梁湘润、李涵辰、台北各家、东海一脉）大量取自任氏阐微，但常将任注当作铁律使用，与原典语气不符；本 pack 应回到任注的"经验语气"层。
  涉及疾病（疾病章）/寿夭（小儿章 / 贞元章）/出身（出身章 / 地位章）的内容，现代使用必须 reframe，不作硬断。
---

## D2 Source Scope

- **source_lines**: 11493
- **structural_units**: 65
- **scope**: 任铁樵注本；含通神论与六亲论，须区分原文、原注、任注、案例。
- **version_note**: 当前 D2 ready 只表示任铁樵注本文本结构与证据层完整；下游 skill 必须保留“原文/任注/案例”分层。
- **evidence_files**: `section-map.md`, `chapter-map.md`, `quote-index.md`


# 滴天髓阐微 Reference Pack（index）

> 本文件是《滴天髓阐微》参考包的**入口索引**，不做规则 / 术语 / 短引的详细内容。
> 详细内容分布在 `chapter-map.md / terms.md / rules.md / procedures.md / quote-index.md / validation.md`。
> 主 skill 默认只加载本文件；按需加载其它文件（详见 §Loading Guide）。

## Source

- **作者层**：
  - **京图**：《滴天髓》原文。
  - **刘基（伯温）**：相传作原注（即文中 `> [注] 原注：...`）。
  - **任铁樵**：清道光年间撰《滴天髓阐微》（即文中 `> [注] 任氏曰：...`）。
- **版本系统**：
  - 任铁樵阐微原本（本 pack 主要参照系统）
  - 徐乐吾补注本、袁树珊《滴天髓补注》（commentary 层）
  - 现代点校本（commentary 层）
- **在线锚点**：
  - 维基文库：https://zh.wikisource.org/wiki/滴天髓闡微
- **卷次结构**：
  - **通神论**：34 章（天道 → 坎离）
  - **六亲论**：29 章（夫妻 → 贞元）
  - **总计**：63 章
- **复核状态**：`partial`。维基文库整理本与古书网本未逐章对校；[原]/[任注]/[案例] 三层切层尚未完成。

## Position In Lineage

- **在八字子平体系中的位置**：旺衰派 / 气势生克派的最高经典；与《子平真诠》（格局派）、《穷通宝鉴》（调候派）三足鼎立。
- **上游**：
  - 《渊海子平》：日为主、月令、十神、十二长生的子平骨架。
  - 《三命通会》：旺衰相关汇编。
- **下游**：
  - 现代旺衰派教学（徐乐吾 / 梁湘润 / 李涵辰 / 东海一脉等），但其注解归 commentary 层。
- **冲突边界**（详见 frontmatter `conflict_policy`）：
  - 不替代《子平真诠》的格局成败。
  - 不替代《穷通宝鉴》的调候十干配合。
  - 仅在 **旺衰、气势、通关、病药、寒暖燥湿** 主线上为精修版。

## Loading Guide

主 skill 加载约定（遵循 matrices/validation-checklist.md §L.11）：

1. **默认只加载本文件** `index.md`：拿 frontmatter / 卷次概览 / 分流路由。
2. **需要查具体章节** → 加载 `chapter-map.md`。
3. **需要查术语** → 加载 `terms.md`。
4. **需要查判断规则** → 加载 `rules.md`。
5. **需要查可操作流程** → 加载 `procedures.md`。
6. **需要查短引 + 出处 + 案例锚点** → 加载 `quote-index.md`。
7. **需要校验覆盖率 / 版本状态** → 加载 `validation.md`。

不允许主 skill 一次性加载全部 7 个文件；按需加载。

## File Map

| 文件 | 职责 | 何时加载 |
|---|---|---|
| [index.md](./index.md) | 入口索引 + frontmatter + 卷次概览 + 路由 | 默认加载 |
| [chapter-map.md](./chapter-map.md) | 通神论 34 + 六亲论 29 章节地图 | 需要查具体章节 |
| [terms.md](./terms.md) | 全书术语抽取（按分组，含旺衰/气势/通关/病药特有术语） | 需要查术语定义 |
| [rules.md](./rules.md) | 全书判断规则（仅从 [原] 和 [任注] 提取） | 需要查判断规则 |
| [procedures.md](./procedures.md) | 全书可操作流程（旺衰判断主线） | 需要查操作流程 |
| [quote-index.md](./quote-index.md) | 短引 + 出处 + [案例] 锚点 | 需要引用原文或案例 |
| [validation.md](./validation.md) | 全书覆盖率 + 三层切层进度 + 待办 | 需要校验覆盖率 |

## Routing

主 skill 收到八字相关问题后：

1. 本 pack 是八字体系的"旺衰派 / 气势生克派"精修版（详见 matrices/routing-matrix.md §2.1）。
2. 按问题类型分流：
   - 综合查找 / 百科 → `bazi/sanming-tonghui`（ready）
   - 子平法骨架 / 术语溯源 → `bazi/yuanhai-ziping`
   - 月令格局成败 → `bazi/ziping-zhenquan`
   - **旺衰 / 气势 / 通关 / 病药 / 寒暖燥湿 → 本 pack（首选）**
   - 调候十干配合 → `bazi/qiongtong-baojian`
3. 事实层未确定的盘必须先调用 `tool.bazi.paipan`。

## 三层切分约定

正文采用 `> [注] 原注：...` 与 `> [注] 任氏曰：...` 两种引用块标记，对应：

- `[原]`：章题正文（七言或四言体）+ 原注（多归刘基注）。
- `[任注]`：任铁樵《阐微》之文。
- `[案例]`：任氏在 [任注] 段中所举的具体八字案例（八字 + 大运 + 断语 + 验证）。

抽取规则：

- `rules.md` 仅从 `[原]` 与 `[任注]` 提取经过抽象化的判断条文。
- `quote-index.md` 可同时引用 `[原]` / `[任注]` / `[案例]` 三层短引，并在 `purpose` 字段标明层级。
- `[案例]` 不上升为规则，但可作为"此规则在某类八字上的应用样本"被引用。

## 冲突裁判

详见 frontmatter `conflict_policy` 与 matrices/conflict-policy.md §1.2。

---
title: 穷通宝鉴
slug: qiongtong-baojian
system: bazi
school:
  - 调候派
  - 月令调候
  - 用神取法
source_layer: primary
source_status: partial
source_links:
  - https://zh.wikisource.org/wiki/%E7%A9%B7%E9%80%9A%E5%AE%9D%E9%89%B4
version_notes: |
  又名《栏江网》《造化元钥》。原本为明末清初坊间手抄《栏江网》，清道光年间余春台编订成今本。
  通行版本：余春台《穷通宝鉴》编订本（本 pack 主要参照系统）；徐乐吾《穷通宝鉴评注》（commentary 层）。
  本书为子平法 **调候派** 的核心文献：以 **十干 × 四季** 为结构，逐月罗列调候用神组合。
  作者归属仍有争议；"原撰人不详"是较稳妥的表述。
depends_on:
  - yuanhai-ziping
  - sanming-tonghui
informs:
  - 现代调候派教学
core_use_cases:
  - 十干日主在十二月令的调候用神取法
  - 寒暖燥湿 / 火暖水润 / 金白水清 等调候组合
  - 与《滴天髓阐微》"寒暖燥湿"章互参
  - 调候 + 旺衰双视角的用神冲突处理
not_for:
  - 排盘事实计算（不替代 tool.bazi.paipan）
  - 旺衰、气势、通关（不替代《滴天髓阐微》）
  - 月令格局成败（不替代《子平真诠》）
  - 把调候当作命理唯一视角（必与旺衰格局合参）
  - 用调候用神判富贵贫贱铁口
extraction_targets:
  - concepts
  - terms
  - rules
  - procedures
  - cautions
  - quote_index
conflict_policy: |
  与同体系其他典籍冲突时按问题类型裁判（详见 matrices/conflict-policy.md §1.2）：
  - 调候用神 → 以本书为精修版主线。
  - 旺衰、气势、通关、病药 → 以《滴天髓阐微》为精修版，本书"调候用神"作辅。
  - 月令格局成败 → 以《子平真诠》为精修版，本书调候作辅。
  - 综合查找 / 百科 → 以《三命通会》为汇编源。
  - 当调候用神与旺衰用神冲突时：先看日主之"寒暖燥湿"是否极端 → 极端者优先调候，非极端者优先旺衰。
validation_notes: |
  - Batch D1 完成全书覆盖型文件组创建。源文件：references/fulltext/bazi/qiongtong-baojian/fulltext.md（维基文库整理本）。
  - source_status 维持 partial：维基文库整理本与清刊本影印未逐章对校。
  - 余春台编订本是否包含全部 100 个 "十干 × 月令" 子目，需逐目核对。
modern_notes: |
  现代调候派教学常将本书的"用神组合"当作硬性配方使用，与原典"以调候为主、旺衰格局合参"的语气不符；本 pack 应回到"调候为主线、其它视角合参"的层次。
  涉及"贫贱"等贬义判语需现代 reframe；不作硬性社会分类。
---

## D2 Source Scope

- **source_lines**: 1764
- **structural_units**: 56
- **scope**: 维基文库整理本；五行总论 + 十干分论体例；无明确卷数划分。
- **version_note**: 当前 D2 ready 只表示维基文库整理本全文已建图；与传统余春台编订本、清刊本的章节差异仍需 edition-diff。
- **evidence_files**: `section-map.md`, `chapter-map.md`, `quote-index.md`


# 穷通宝鉴 Reference Pack（index）

> 本文件是《穷通宝鉴》参考包的**入口索引**，不做规则 / 术语 / 短引的详细内容。
> 详细内容分布在 `chapter-map.md / terms.md / rules.md / procedures.md / quote-index.md / validation.md`。
> 主 skill 默认只加载本文件；按需加载其它文件（详见 §Loading Guide）。

## Source

- **作者**：原撰人不详；清道光年间余春台编订成今本。
- **版本系统**：
  - 余春台编订本（本 pack 主要参照系统）
  - 徐乐吾《穷通宝鉴评注》（commentary 层）
  - 民国及现代点校本（commentary 层）
- **在线锚点**：
  - 维基文库：https://zh.wikisource.org/wiki/穷通宝鉴
- **卷次结构**：本书不分卷次，按 **十干 × 四季** 组织：
  - **五行总论**：1 章
  - **十干分论**：5 行（木/火/土/金/水）+ 10 干分论（甲～癸）
    - 每干下分 **三春 / 三夏 / 三秋 / 三冬** 4 节
    - 共 10 干 × 4 季 = **40 个月令子目**
  - **总计**：1（总论） + 5（行论） + 10（干论） + 40（月令子目） = **约 56 章节条目**
- **复核状态**：`partial`。维基文库整理本与清刊本影印未逐章对校。

## Position In Lineage

- **在八字子平体系中的位置**：调候派的最高经典；与《子平真诠》（格局派）、《滴天髓阐微》（旺衰派）三足鼎立。
- **上游**：
  - 《渊海子平》：月令、十干、季节性五行旺衰的子平骨架。
  - 《五行精纪》：宋代禄命汇编中已有月令五行宜忌的雏形。
- **下游**：
  - 现代调候派教学（徐乐吾 / 韦千里 / 各家），但其评注归 commentary 层。
- **冲突边界**（详见 frontmatter `conflict_policy`）：
  - 仅在 **调候用神** 主线上为精修版。
  - 不替代《滴天髓阐微》的旺衰气势通关。
  - 不替代《子平真诠》的月令格局成败。

## Loading Guide

主 skill 加载约定（遵循 matrices/validation-checklist.md §L.11）：

1. **默认只加载本文件** `index.md`：拿 frontmatter / 卷次概览 / 分流路由。
2. **需要查具体章节**（如"丙火生于寅月"） → 加载 `chapter-map.md`。
3. **需要查术语** → 加载 `terms.md`。
4. **需要查判断规则** → 加载 `rules.md`。
5. **需要查可操作流程** → 加载 `procedures.md`。
6. **需要查短引 + 出处** → 加载 `quote-index.md`。
7. **需要校验覆盖率 / 版本状态** → 加载 `validation.md`。

不允许主 skill 一次性加载全部 7 个文件；按需加载。

## File Map

| 文件 | 职责 | 何时加载 |
|---|---|---|
| [index.md](./index.md) | 入口索引 + frontmatter + 卷次概览 + 路由 | 默认加载 |
| [chapter-map.md](./chapter-map.md) | 五行总论 + 十干 × 四季子目（约 56 条） | 需要查具体章节 |
| [terms.md](./terms.md) | 全书术语抽取（按分组，含调候特有术语） | 需要查术语定义 |
| [rules.md](./rules.md) | 全书判断规则（调候用神为主） | 需要查判断规则 |
| [procedures.md](./procedures.md) | 调候取用流程 | 需要查操作流程 |
| [quote-index.md](./quote-index.md) | 短引索引 + 出处 | 需要引用原文 |
| [validation.md](./validation.md) | 全书覆盖率 + 版本状态 + 待办 | 需要校验覆盖率 |

## Routing

主 skill 收到八字相关问题后：

1. 本 pack 是八字体系的"调候派"精修版（详见 matrices/routing-matrix.md §2.1）。
2. 按问题类型分流：
   - 综合查找 / 百科 → `bazi/sanming-tonghui`（ready）
   - 子平法骨架 / 术语溯源 → `bazi/yuanhai-ziping`
   - 月令格局成败 → `bazi/ziping-zhenquan`
   - 旺衰 / 气势 / 通关 → `bazi/ditiansui-chanwei`
   - **调候用神 → 本 pack（首选）**
3. 事实层未确定的盘必须先调用 `tool.bazi.paipan`。

## 调候取用流程依赖

本书 procedures.md 中的"调候取用流程"严格依赖 `tool.bazi.paipan`：

- 必须先由 `tool.bazi.paipan` 取得四柱与节气换月信息。
- 月令以节气分界（不以朔望分界），方能正确锁定"三春／三夏／三秋／三冬"。
- 任何人工手算节气都视为不可靠，须重新调用工具。

## 冲突裁判

详见 frontmatter `conflict_policy` 与 matrices/conflict-policy.md §1.2。

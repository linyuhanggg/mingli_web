---
title: "六壬指南 / 六壬指南注解"
slug: "liuren-zhiyin"
system: "san-shi"
school:
  - "大六壬"
  - "指南系"
source_layer: "mixed_layer_annotated_edition"
source_status: "complete_text"
source_state_summary: "完整可检索注本已入库、原本影印已取得、未全本逐页校勘"
depends_on: []
requires_adapter:
  - "deterministic_liuren_chart"
  - "calendar_and_month_general"
optional_comparison:
  - "daliuren-daquan"
informs:
  - "mingli-master"
core_use_cases:
  - "解释《指南》卷一核心取用决策树"
  - "按卷一、卷二赋文语义段定位术语和解释次序"
  - "按卷三分门检索陈公献旧占验、张洪史注与现代增补课例"
  - "按卷四岁月旬干支层检索神煞，并限制为盘后辅证"
not_for:
  - "替代确定性排盘或历算"
  - "把现代注释或潍坊课例称为古籍原文"
  - "仅凭神煞作结论"
  - "医疗、法律、投资、婚育、灾祸等现实保证"
coverage_claim: "normalized 全文已结构索引；核心规则选择性蒸馏；未声称逐句规则覆盖。"
---

# 《六壬指南 / 六壬指南注解》Reference Pack

## Status

**完整可检索注本已入库、原本影印已取得、未全本逐页校勘。**

当前可检索底本是张洪完整注本，不是一个可整本统称“陈公献原文”的单层文本。NLC 248 页影印已在本地，但没有完成全本逐页逐行校勘，因此本包使用 normalized 行号，不伪造影印页码。

## What is in the edition

- 两赋短句：`original_text`，不强定作者。
- 两赋旧注和卷三《会纂》主体：`chen_gongxian_content`。
- 卷四《神煞图位》传统归庄公远，卷末又署庄广之：`zhuang_gongyuan_content`，身份关系待考。
- 张洪自序、简注、史注、合卷结构和第三十章：`zhang_hong_modern_annotation`。
- 1998 年、潍坊、工商局等课例：`modern_case` / `modern_weifang_case`。
- CTP 题下注但未稳归作者：`annotated_comment_unattributed`。

## Use order

1. `source-manifest.yaml`：来源、校验和、状态和层级定义。
2. `conflict-notes.md`：标题、卷次、章数、异文和现代增补冲突。
3. `chapter-map.md`：卷一、二语义段，卷三 1-30 章，卷四神煞层。
4. `procedures.md`：确定性排盘契约、核心取用决策树和停止条件。
5. `rules.md`：带 `quote_id`、前置字段、例外和冲突的规则卡。
6. `quote-index.md`：逐字短引与 normalized 行号。
7. `terms.md`：术语与来源层词表。
8. `test-prompts.json`、`validation.md`：压力测试和验收结果。

## Core execution policy

- 排盘由 adapter 完成；文本不手算月将、天地盘、四课、三传或神煞。
- 取用严格走：直接贼克优先 -> 多克比用/涉害 -> 无直接克取遥克 -> 特殊盘式或昴星/别责。
- 伏吟、反吟、八专有各自无克分支，不能互相套用。
- 解释顺序是课传、初中末、占类、神将、刑冲旺衰，最后才是神煞。
- 神煞只作盘后辅证；现代占例只作案例层。

## Dependency correction

本包不强制依赖《大六壬大全》。跨书比较时可显式加载 `daliuren-daquan`，但《大全》不能覆盖《指南》本身的涉害口径、来源层或卷次问题。唯一硬依赖是确定性六壬排盘与历算 adapter。

---
title: 增删卜易
slug: zengshan-buyi
system: divination
school:
  - 六爻
  - 纳甲
  - 世应
  - 用神
source_layer: primary
source_status: partial
source_links:
  - https://zh.wikisource.org/wiki/%E5%A2%9E%E5%88%AA%E5%8D%9C%E6%98%93
version_notes: |
  清·野鹤老人著（一作李我平 / 李文辉，名号说法不一），增删《卜筮正宗》《黄金策》等前人成说。
  通行本系统：清刻本 / 民国石印本，民间六爻金钱卦集大成之作，流传极广。
  本 pack 以维基文库整理本（CC BY-SA 4.0）为参考底本。
  卷次结构：通行本 4 卷（卷之一 26 章 / 卷之二 27-35 / 卷之三 36-68 / 卷之四 69-130），共 130 章+。
depends_on:
  - meihua-yishu
informs: []
core_use_cases:
  - 六爻金钱卦装卦（纳甲、世应、六亲、动变）
  - 用神取法（按问占类型取用神）
  - 元神 / 忌神 / 仇神判断
  - 旺衰生克墓绝合冲应期判断
  - 各门类问占（功名 / 求财 / 婚姻 / 疾病 / 家宅 等130余门）
not_for:
  - LLM 手算装卦 / 排纳甲 / 安世应（必须调用 tool.divination.liuyao_bindisk）
  - 象数体用占法（应转 meihua-yishu）
  - 易学义理 / 经传解读（应转 zhouyi-zhezhong）
  - 严格的医学 / 寿命 / 法律预测结论
extraction_targets:
  - concepts
  - terms
  - rules
  - procedures
  - cautions
  - quote_index
conflict_policy: |
  - 与梅花易数体用法冲突 → 本书属六爻金钱卦体系（装卦 + 用神 + 世应），与体用法不混用；问占者明确"摇钱起卦"用本书，"数字 / 物象起卦"用梅花。
  - 与《卜筮正宗》冲突 → 本书是对《卜筮正宗》《黄金策》的"增删"，存在差异时本书代表清代后期共识；古旧观点以原书为据。
  - 与早期纳甲（京房）冲突 → 本书简化民间通行版本，与京房原本细节有出入，需注明来源。
validation_notes: |
  - 作者归属待考（野鹤老人 / 李我平 / 李文辉）。
  - 卷篇划分各本不同（12 卷或 14 篇之说），本 pack 采用维基文库整理本之 4 卷 130+ 章版本。
  - 含大量占例（每章往往附 5-20 个），本 pack 仅做摘要 + 短引，不复制占例原文。
  - status：本 batch 完成框架，章节级 digest_status 全部 partial。
modern_notes: |
  现代六爻教学（如王虎应、邵伟华、李洪成等）多沿用本书框架；本 pack 仅收原典章节，不收现代演绎。
---

## D2 Source Scope

- **source_lines**: 6898
- **structural_units**: 155
- **scope**: 维基文库整理本；含卷首增订说明、卷一至卷四、占卦法与八宫六十四卦附录。
- **version_note**: 作者名号与卷篇划分各本不同；当前 D2 ready 只表示本地维基文库整理本全源建图，现代录入者说明与附录须与原典层区分。
- **evidence_files**: `section-map.md`, `chapter-map.md`, `quote-index.md`


# 增删卜易 Reference Pack（index）

> 本文件是《增删卜易》参考包的**入口索引**。详细内容分布在 `chapter-map.md / terms.md / rules.md / procedures.md / quote-index.md / validation.md`。

## Source

- **作者**：清·野鹤老人（李我平 / 李文辉，名号说法不一），男婿陈文吉、茹芝山校。
- **版本系统**：维基文库整理本（清刻本 / 民国石印本系统，CC BY-SA 4.0；本 pack 主要参照）。
- **卷次结构**：通行本 4 卷
  - 卷之一（26 章）：八卦、卦象图、八宫、浑天甲子、六亲歌、世应、动变、用神、元神忌神仇神、旺衰、相生相克、动静生克、月将、日辰、六神、六合六冲三刑、暗动、动散、卦变生克墓绝、反伏、旬空、生旺墓绝、归魂游魂等基础理论
  - 卷之二（章 27-35）：月破、飞伏神、进退、随鬼入墓、独发、两现、星煞、增删黄金策千金赋、天时
  - 卷之三（章 36-68）：身命、终身财福功名、寿元、趋避、六亲（父母兄弟夫妇子嗣）、学业、求名（童试到武试）、求财
  - 卷之四（章 69-130）：求财细分、婚姻、胎孕、出行、官讼、疾病痘疹、家宅蓋造、风水阴宅塋葬等
- **复核状态**：`partial`。维基文库本未与古本逐章复核。

## Position In Lineage

- **在卜筮体系中的位置**：六爻金钱卦集大成之作；继《卜筮正宗》《黄金策》之后的清代权威实战手册。
- **上游**：《京氏易传》（纳甲）、《卜筮正宗》、《黄金策》。
- **下游**：现代六爻所有派别（王虎应、邵伟华、李洪成等）实战教学。

## Core Use Cases

- 六爻金钱卦装卦（含纳甲 / 世应 / 六亲 / 动变 / 旬空）
- 用神取法（按问占类型）
- 元神 / 忌神 / 仇神判断
- 月破 / 旬空 / 暗动 / 动散 / 反伏等爻态判断
- 应期判断（合冲生克墓绝）
- 130 余门类问占断诀

## Not For

- LLM 手算装卦 / 排纳甲 / 安世应 / 旬空 / 月破（必须 `tool.divination.liuyao_bindisk`）
- 象数体用法（应转 `divination/meihua-yishu`）
- 易学义理（应转 `divination/zhouyi-zhezhong`）
- 严格医学 / 寿命预后（占断仅供参考）

## Loading Guide

1. **默认只加载** `index.md`：拿 frontmatter / 卷次概览 / 路由。
2. **查具体章节** → `chapter-map.md`。
3. **查术语 / 神煞** → `terms.md`。
4. **查判断规则** → `rules.md`。
5. **查装卦 / 占断流程** → `procedures.md`。
6. **查短引 + 出处** → `quote-index.md`。
7. **查覆盖率 / 版本状态** → `validation.md`。

## File Map

| 文件 | 职责 | 何时加载 |
|---|---|---|
| [index.md](./index.md) | 入口索引 + frontmatter + 卷次概览 + 路由 | 默认加载 |
| [chapter-map.md](./chapter-map.md) | 4 卷 130+ 章地图 + digest_status | 需要查具体章节 |
| [terms.md](./terms.md) | 六爻装卦核心术语 + 神煞 | 需要查术语 |
| [rules.md](./rules.md) | 取用神 + 旺衰 + 应期等判断规则 | 需要查判断规则 |
| [procedures.md](./procedures.md) | 装卦 / 占断流程 | 需要查操作流程 |
| [quote-index.md](./quote-index.md) | 短引索引 | 需要引用原文 |
| [validation.md](./validation.md) | 覆盖率 + 版本核验 | 需要校验覆盖率 |

## Routing

主 skill 收到六爻 / 卜筮相关问题后：

1. 本 pack 是六爻金钱卦的主入口（清代实战权威）。
2. 按问题类型分流：
   - 装卦 / 纳甲 / 世应 / 旬空 → 本 pack `procedures.md` ZP-01~03
   - 用神取法 → 本 pack `rules.md` ZR-04-* + procedures.md ZP-04
   - 旺衰判断 → 本 pack `rules.md` ZR-05-*
   - 应期判断 → 本 pack `rules.md` ZR-08-*
   - 130 类问占 → 本 pack `chapter-map.md` 卷三卷四 + rules.md ZR-10-*
   - 象数体用法 → `divination/meihua-yishu`
   - 易学义理 → `divination/zhouyi-zhezhong`
3. 装卦事实层一律调用 `tool.divination.liuyao_bindisk`，**禁止 LLM 手算**。

## 冲突裁判

详见 frontmatter `conflict_policy`。

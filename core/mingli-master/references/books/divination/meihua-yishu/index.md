---
title: 梅花易数
slug: meihua-yishu
system: divination
school:
  - 梅花
  - 先天起卦
  - 后天起卦
  - 体用
source_layer: primary
source_status: partial
source_links:
  - https://zh.wikisource.org/wiki/%E6%A2%85%E8%8A%B1%E6%98%93%E6%95%B8
  - https://ctext.org/mei-hua-yi-shu/zh
version_notes: |
  传宋·邵雍（实为后人托名编纂），宋元成书。
  通行本系统：明清刻本流传极广，民间增删较多，需指定底本。
  本 pack 以维基文库整理本（CC BY-SA 4.0）为参考底本，CTP 仅作锚点。
  卷次结构：通行本 5 篇 / 卷（象数易理篇 1-3、体用生克篇 1-5、断占总诀篇 1-4），合 12 部分。
depends_on: []
informs:
  - bushi-zhengzong
  - zengshan-buyi
core_use_cases:
  - 先天数起卦（年月日时、字数、声音、物数、字数等）
  - 后天起卦（端法：以物为上卦、方位为下卦）
  - 体用生克吉凶判断
  - 八卦万物类象查找
  - 占梅、占牡丹、占牛鸣等典型占例对照
not_for:
  - LLM 手算起卦（必须调用 tool.divination.qiguagua）
  - 六爻纳甲世应用神（应转 zengshan-buyi / bushi-zhengzong）
  - 易学义理解经（应转 zhouyi-zhezhong）
  - 严格的医学/寿命预测结论
extraction_targets:
  - concepts
  - terms
  - rules
  - procedures
  - cautions
  - quote_index
conflict_policy: |
  - 与六爻金钱卦冲突 → 本书属象数占法（先天数 + 体用），不宜混用六爻装卦体系；金钱卦法以《增删卜易》《卜筮正宗》为主。
  - 与易学义理冲突 → 本书重象数占断，不解经传义理；义理转 zhouyi-zhezhong。
  - 与卦象类象冲突 → 本书《八卦万物属类》是民间通行本，与古本说卦传出入处以本书为占法实用准。
validation_notes: |
  - 作者归属待考：传邵雍，实为后人托名编纂。
  - 通行本与古本差异较大，民间增删较多；本 pack 章节命名依维基文库整理本。
  - 占例（观梅、牡丹、牛鸣等）原文叙述较长，本 pack 仅做摘要 + 短引，不复制大段原文。
  - status：本 batch 完成框架，章节级 digest_status 全部 partial；待与古本对校升级 done。
modern_notes: |
  现代占卜书大量沿用本书体用框架；本 pack 仅收录原典章节，不收录现代演绎。
---

## D2 Source Scope

- **source_lines**: 1629
- **structural_units**: 138
- **scope**: 维基文库通行本；序、目录、附录与象数/体用/断占诸篇。
- **version_note**: 作者与版本均有托名/通行本差异风险；当前 D2 ready 只表示本地维基文库通行本已完整建图。
- **evidence_files**: `section-map.md`, `chapter-map.md`, `quote-index.md`


# 梅花易数 Reference Pack（index）

> 本文件是《梅花易数》参考包的**入口索引**。详细内容分布在 `chapter-map.md / terms.md / rules.md / procedures.md / quote-index.md / validation.md`。
> 主 skill 默认只加载本文件；按需加载其它文件（详见 §Loading Guide）。

## Source

- **作者**：传宋·邵雍（康节），实为宋元后人托名编纂。
- **版本系统**：
  - 维基文库整理本（明清通行刻本系统，CC BY-SA 4.0；本 pack 主要参照）
  - CTP《梅花易数》专项条目（仅作锚点）
- **卷次结构**：通行本分三大类共 12 篇
  - 象数易理篇（之一 / 之二 / 之三）：八卦数、五行生克、八宫五行、卦气旺衰、起卦诸例、八卦万物属类、占静物动物
  - 体用生克篇（之一 / 之二 / 之三 / 之四 / 之五）：体用之分、内外卦、生克比和吉凶
  - 断占总诀篇（之一 / 之二 / 之三 / 之四）：天时、人事、家宅、婚姻、求财、求名等十类问占断诀
- **复核状态**：`partial`。维基文库文本未与古本逐章复核。

## Position In Lineage

- **在卜筮体系中的位置**：象数占法代表，介于古本《周易》与后世六爻金钱卦之间。
- **上游**：宋代象数易学（邵雍先天易学）。
- **下游**：
  - 《卜筮正宗》《增删卜易》：六爻装卦体系另起一线，与本书并列而不混。
  - 民间数字占卜、字占、物占多承本书体例。

## Core Use Cases

- 用先天数 / 后天端法起卦
- 体用生克吉凶判断（核心方法）
- 八卦万物类象查找（八卦对应物象）
- 占例对照（观梅、牡丹、牛鸣、鸡鸣、人字、字迹等）
- 字占、声音占、物数占等多元起卦法

## Not For

- LLM 手算起卦 / 排互卦 / 排变卦（必须 `tool.divination.qiguagua`）
- 六爻金钱卦装卦 / 用神 / 世应（应转 `divination/zengshan-buyi`）
- 易学义理 / 经传解读（应转 `divination/zhouyi-zhezhong`）
- 严格医学预后、寿命断定（占断仅供参考，须加现代使用边界）

## Loading Guide

1. **默认只加载** `index.md`：拿 frontmatter / 篇次概览 / 路由。
2. **查具体章节** → `chapter-map.md`。
3. **查术语 / 类象** → `terms.md`。
4. **查判断规则** → `rules.md`。
5. **查起卦 / 占断流程** → `procedures.md`。
6. **查短引 + 出处** → `quote-index.md`。
7. **查覆盖率 / 版本状态** → `validation.md`。

不允许主 skill 一次性加载全部 7 个文件；按需加载。

## File Map

| 文件 | 职责 | 何时加载 |
|---|---|---|
| [index.md](./index.md) | 入口索引 + frontmatter + 篇次概览 + 路由 | 默认加载 |
| [chapter-map.md](./chapter-map.md) | 12 篇章节地图 + digest_status | 需要查具体章节 |
| [terms.md](./terms.md) | 术语 + 八卦万物类象 | 需要查术语 |
| [rules.md](./rules.md) | 体用生克 + 占断判断规则 | 需要查判断规则 |
| [procedures.md](./procedures.md) | 起卦 / 占断流程 | 需要查操作流程 |
| [quote-index.md](./quote-index.md) | 短引索引 | 需要引用原文 |
| [validation.md](./validation.md) | 覆盖率 + 版本核验 | 需要校验覆盖率 |

## Routing

主 skill 收到象数占卜相关问题后：

1. 本 pack 是象数占法的主入口（先天数 + 体用）。
2. 按问题类型分流：
   - 先天数起卦 / 字占 / 物数占 → 本 pack `procedures.md` MP-01~04
   - 后天端法起卦（物 + 方位）→ 本 pack `procedures.md` MP-05
   - 体用生克 → 本 pack `rules.md` MR-04-*
   - 十类问占（天时/家宅/婚姻 等）断诀 → 本 pack `rules.md` MR-07-* ~ MR-12-*
   - 六爻金钱卦装卦 → `divination/zengshan-buyi`
   - 易学义理 → `divination/zhouyi-zhezhong`
3. 起卦事实层一律调用 `tool.divination.qiguagua`，**禁止 LLM 手算**。

## 冲突裁判

详见 frontmatter `conflict_policy`。

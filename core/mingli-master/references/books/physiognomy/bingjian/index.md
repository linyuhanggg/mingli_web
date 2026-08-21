---
title: 冰鉴
slug: bingjian
system: physiognomy
school:
  - 面相
  - 神骨
  - 刚柔
source_layer: side_evidence
source_status: partial
source_links:
  - https://zh.wikisource.org/wiki/%E5%86%B0%E9%91%92
version_notes: |
  传统题署清代曾国藩撰，但学界多认为是托名，原撰人不详；
  本 pack 采用 normalized 文本中"民国简沙侣抄简熙尧校本"作为整理底本（题署：清·罗祖真人）。
  全书共 7 篇：神骨、刚柔、容貌、情态、须眉、声音、气色，加序跋共 9 节，约 4500 字。
  本书在文人鉴人传统中地位颇高（"非如麻衣柳庄等流俗坊本可比"），
  但仍属传统相术范畴，本 pack 严格按 **旁证层** 处理。
depends_on: []
informs:
  - 现代相术教学（节选用）
core_use_cases:
  - 神骨视角的"内在精神"分类（澄清到底 / 尖巧喜淫 / 别才深思 / 隐流败器）
  - 刚柔视角的内外刚柔（五行外刚柔 + 喜怒伏跳深浅之内刚柔）
  - 情态四分（弱态 / 狂态 / 疏懒态 / 周旋态）的人物气质画像
  - 须眉、声音、气色的"气象"判读
not_for:
  - 命盘事实计算（不与 bazi/ziwei/xingming 同层）
  - 富贵贫贱铁口判断（仅作旁证，不作硬判）
  - 健康、寿命、子嗣、女命断语（走 safety-redlines）
  - 凭面相判断犯罪倾向、伴侣选择、雇佣决定（现代禁用）
extraction_targets:
  - concepts
  - terms
  - rules
  - procedures
  - cautions
  - quote_index
conflict_policy: |
  本书属 **physiognomy / 旁证层**，与 bazi / ziwei / xingming 命盘类典籍**不同层**：
  - 命盘判断时：本书结论仅作旁证，不参与硬判。
  - 与 shenxiang-quanbian 冲突时：以本书"文人鉴人语气"为雅训层；以 shenxiang-quanbian 为汇编百科层。
  - 命盘 vs 相法冲突 → 命盘（bazi/ziwei/xingming）优先；相法仅作辅证。
validation_notes: |
  - Batch D1 完成全书覆盖型文件组创建。源文件：references/fulltext/physiognomy/bingjian/fulltext.md。
  - source_status 维持 partial：清刊本影印未对校。
  - 本书全文短，rules.md 抽取覆盖率高；但每条 rules 必须带 caveats "仅作旁证参考，不参与命盘硬判断"。
modern_notes: |
  本书内含若干贬义判语（如"刀剑随身"、"孤寒老矣"、"市井之夫"、"敗类"、"贱徵"、"贫贱者有声无音"等），
  在现代语境中**必须 reframe**：
  - 不作社会身份等级评价。
  - 不据相貌断人贫富、贞淫、贵贱。
  - 仅作"古典相术语义还原"，主 skill 输出时必须加现代使用边界。
  本 pack 的 rules.md 在所有贬义条文上都已附 reframe caveat。
---

# 冰鉴 Reference Pack（index）

> 本文件是《冰鉴》参考包的**入口索引**，不做规则 / 术语 / 短引的详细内容。
> 详细内容分布在 `chapter-map.md / terms.md / rules.md / procedures.md / quote-index.md / validation.md`。
> 主 skill 默认只加载本文件；按需加载其它文件。

## Source

- **作者**：原撰人不详；传统题署罗祖真人 / 民间俗传曾国藩；本 pack 不作权威归属。
- **底本**：民国简沙侣抄简熙尧校本（normalized 文本所采）。
- **在线锚点**：维基文库 https://zh.wikisource.org/wiki/冰鑑
- **本地 normalized**：`references/fulltext/physiognomy/bingjian/fulltext.md`（约 80 行 / 4500 字）。
- **结构**：序 + 神骨 + 刚柔 + 容貌 + 情态 + 须眉 + 声音 + 气色 + 跋 = **9 节**。

## Position In Lineage

- **在相法体系中的位置**：文人鉴人传统的雅训本；与《麻衣相法》《神相全编》等坊间汇编不同。
- **上游**：先秦"瞽史观人"、《孟子·眸子论》、汉魏六朝以降的察举鉴识传统。
- **下游**：清末民国的"鉴人录"类小书；现代相术教学常引"神骨"、"情态"两章。
- **横向**：与本 pack 的 `physiognomy/shenxiang-quanbian` 互参——
  - 冰鉴：雅训语气，文人观人，重"神骨气象"。
  - 神相全编：百科汇编，覆盖广，重"局部相部分类"。

## Loading Guide

主 skill 加载约定：

1. 默认只加载 `index.md`：拿 frontmatter / 章节概览 / 路由。
2. 需要查具体章节 → `chapter-map.md`。
3. 需要查术语 → `terms.md`。
4. 需要查判断规则 → `rules.md`（**所有规则带 "仅作旁证参考"**）。
5. 需要查可操作流程 → `procedures.md`（旁证流程，绝不替代命盘）。
6. 需要查短引 + 出处 → `quote-index.md`。
7. 需要校验覆盖率 / 版本状态 → `validation.md`。

## File Map

| 文件 | 职责 | 何时加载 |
|---|---|---|
| [index.md](./index.md) | 入口索引 + frontmatter + 章节概览 + 路由 | 默认加载 |
| [chapter-map.md](./chapter-map.md) | 9 节章节地图 | 需要查具体章节 |
| [terms.md](./terms.md) | 全书术语抽取 | 需要查术语定义 |
| [rules.md](./rules.md) | 全书判断规则（旁证层） | 需要查判断规则 |
| [procedures.md](./procedures.md) | 旁证查询流程 | 需要查操作流程 |
| [quote-index.md](./quote-index.md) | 短引索引 + 出处 | 需要引用原文 |
| [validation.md](./validation.md) | 全书覆盖率 + 版本状态 + 待办 | 需要校验覆盖率 |

## Routing

主 skill 收到相术相关问题后：

1. 本 pack 是相术体系的"文人雅训层"。
2. 不作命盘类问题的主回答源。
3. 与命盘冲突 → 命盘优先；本书仅作辅证标记。

## 相法旁证使用约束（重要）

- **绝不允许**：凭相貌单独判定人命、富贵、贫贱、贞淫、子嗣、寿夭。
- **绝不允许**：将本书的描述用于职场、招聘、婚配、刑侦决定。
- **允许**：作为传统文化语义还原；作为命盘综合判断的"软辅证"。
- **必须**：所有规则在输出时带"仅作旁证参考，不参与命盘硬判断"。
- **必须**：贬义判语（如"贱徵"、"敗類"、"市井之夫"、"贫贱"）在输出层做现代 reframe。

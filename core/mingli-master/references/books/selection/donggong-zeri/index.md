---
title: 董公择日
slug: donggong-zeri
system: selection
school:
  - 民间通书
  - 月将吉凶日
  - 神煞择日
  - 嫁娶起造
  - 丧葬出行
source_layer: commentary
source_status: normalized_ready
source_links:
  - https://upload.wikimedia.org/wikipedia/commons/8/87/NLC416-12jh005366-44510
  - https://zh.wikisource.org/wiki/%E8%91%A3%E5%85%AC%E9%81%B8%E8%A6%81%E8%A6%BD
version_notes: |
  托名"董德彰"（号银峯）的民间择日通书，明清以降流传甚广。
  本 pack 底本以国家图书馆藏《董公选要览》为主（Wikimedia Commons CC0 镜像）。
  序言载嘉庆二十二年（1817）蒋奇峰（号"奇峰散人"）在京师宣武门外琉璃厂延寿禅林撰序付梓。
  传本异文较多，《董公选要览》《董公诹吉新书》《董公选秘訣要覧》等同源异书并存。
  作者"董德彰"身份未确定（历史可能为伪托）；与官方四库本择日典籍不同体系。
depends_on: []
informs: []
related:
  - yuqia-ji
core_use_cases:
  - 民间嫁娶/起造/丧葬/出行/上任择日的"通书系"对照参考
  - 月将吉凶日（金神七煞、煞贡、直星、人专吉日）的口诀汇总
  - 与官方《协纪辨方书》《星历考原》比对的民间口径参照
not_for:
  - 实际择日计算（必须调用 mingli-master.selection.v1）
  - 嫁娶/丧葬/出行吉凶的事实性断言（仅作文化参考）
  - 与皇历/通书系统的系统化对照（应优先 xieji-bianfang-shu）
  - 神煞起例的源流考据（应优先 xingli-kaoyuan）
extraction_targets:
  - terms
  - rules
  - procedures
  - cautions
  - quote_index
conflict_policy: |
  与同体系其他典籍冲突时按 matrices/conflict-policy.md §1.4 裁判：
  - 与《协纪辨方书》（官方）口径冲突 → 以官方为准，本书作"民间口径"备查。
  - 与《星历考原》神煞起例不一致 → 以《星历考原》为准，本书仅作口诀对照。
  - 与《玉匣记》同属民间通书 → 互参；规则口径以民间通行版本为参考，不互相覆盖。
  - 涉及具体日子吉凶 → 一律转 mingli-master.selection.v1 计算，本书不下事实判断。
validation_notes: |
  - source_status 调整为 normalized_ready：本地维基文库整理文本已完整规范化；但尚未对国图影印逐页校勘。
  - "董德彰"身份及成书年代均待考。
  - 书中涉及嫁娶/丧葬/出行吉凶的"应验"语气均需 reframe 为"文化参考"。
  - 月份吉凶日与四柱神煞的对应关系需与《协纪辨方书》《星历考原》交叉验证。
cultural_caveats: |
  本书所载"嫁娶吉日""丧葬避忌""出行吉时"等内容属古代民间风俗，
  现代不构成事实判断；输出时必须加 caveat："文化参考，非事实判断"。
---

# 董公择日 Reference Pack（index）

> 本文件是《董公择日》（《董公选要览》系）参考包的**入口索引**，不做规则 / 术语 / 短引的详细内容。
> 详细内容分布在 `chapter-map.md / terms.md / rules.md / procedures.md / quote-index.md / monthly-day-table.md / validation.md`。

## Source

- **作者**：题"董德彰"（号银峯，托名）；嘉庆二十二年蒋奇峰序付梓。
- **底本**：国家图书馆藏《董公选要览》（Wikimedia Commons NLC416-12jh005366-44510）。
- **派系**：民间通书系（与官方《协纪辨方书》《星历考原》不同源）。
- **结构**：略记 → 蒋奇峰论略十三则 → 正月至十二月吉凶日 → 金神七煞歌 → 煞贡直星人专吉日 → 董公择日选时歌诀。
- **复核状态**：`normalized_ready`（本地整理文本完整；Wikimedia / 国图影印尚未逐页校勘）。

## Position In Lineage

- **在择日体系中的位置**：民间通书代表，与《玉匣记》并列；非官方历法系统。
- **上游**：传承自唐宋以降的择日口诀汇编，与《历神辨方》《选择求真》等通书有源流关系。
- **下游**：清末民国以降各类民间皇历、通书直接承袭。

## Loading Guide

主 skill 加载约定（遵循 matrices/validation-checklist.md §L.11）：

1. **默认只加载本文件** `index.md`：拿 frontmatter / 卷次概览 / 分流路由。
2. **需要查具体月份/章节** → 加载 `chapter-map.md`。
3. **需要查术语** → 加载 `terms.md`。
4. **需要查判断规则** → 加载 `rules.md`。
5. **需要查可操作流程** → 加载 `procedures.md`。
6. **需要查逐月逐日条目** → 加载 `monthly-day-table.md`。
7. **需要查短引 + 出处** → 加载 `quote-index.md`。
8. **需要校验覆盖率 / 版本状态** → 加载 `validation.md`。

## File Map

| 文件 | 职责 | 何时加载 |
|---|---|---|
| [index.md](./index.md) | 入口索引 + frontmatter + 概览 + 路由 | 默认加载 |
| [chapter-map.md](./chapter-map.md) | 全书章节地图 + digest_status | 需要查具体章节 |
| [terms.md](./terms.md) | 全书术语抽取（按分组） | 需要查术语定义 |
| [rules.md](./rules.md) | 全书判断规则（按主题） | 需要查判断规则 |
| [procedures.md](./procedures.md) | 全书可操作流程（工具调用） | 需要查操作流程 |
| [quote-index.md](./quote-index.md) | 156 条 exact-match 短引 + 出处 | 需要引用原文 |
| [monthly-day-table.md](./monthly-day-table.md) | 144 条逐月逐日建除宜忌表 | 需要查具体月日条目 |
| [validation.md](./validation.md) | 全书覆盖率 + 版本核验 + 待办 | 需要校验覆盖率 |

## Routing

主 skill 收到择日相关问题后：

1. 本 pack 是择日体系的"民间通书"代表（详见 matrices/routing-matrix.md §6）。
2. 按问题类型分流：
   - 官方择日体系 / 神煞起例考源 → `selection/xingli-kaoyuan`
   - 官方择日全书 / 通用万年历 → `selection/xieji-bianfang-shu`
   - 民间杂占 / 通书 → `selection/yuqia-ji` 或本 pack
   - 涉及具体日子吉凶 → `mingli-master.selection.v1`（必需）
3. 本 pack 输出"民间口径"对照，不替代官方择日。

## 冲突裁判

详见 frontmatter `conflict_policy` 与 matrices/conflict-policy.md §1.4。

## 文化警示

本 pack 中的"嫁娶吉日""丧葬避忌""探病忌日""出行吉时"等内容均属古代民间习俗，
**输出时必须 reframe 为"文化参考，非事实判断"**，禁止下事实性吉凶判断。

---
title: 華山陳希夷先生飛星紫微斗數原旨
slug: feixing-ziwei-doushu-yuanzhi
system: ziwei
school:
  - 紫微斗数
  - 飞星紫微
  - 斗数观测录
  - 民国观测注释层
source_layer: commentary_or_late_observation
source_status: ocr_reviewed_complete
source_links:
  - https://commons.wikimedia.org/wiki/File:NLC416-12jh004539-48693_%E8%8F%AF%E5%B1%B1%E9%99%B3%E5%B8%8C%E5%A4%B7%E5%85%88%E7%94%9F%E9%A3%9B%E6%98%9F%E7%B4%AB%E5%BE%AE%E6%96%97%E6%95%B8%E5%8E%9F%E6%97%A8.pdf
version_notes: |
  本 pack 依据 NLC/Wikimedia Commons 116 页影印本 OCR 校阅全文。
  馆藏/Commons 题名为《華山陳希夷先生飛星紫微斗數原旨》，正文可见《斗數觀測錄序》《斗數觀測錄》。
  source manifest 说明其与王裁珊《斗數宣微》第三集/斗數觀測錄线索相近，但本 pack 不冒称王裁珊定本，也不替代 blocked 的 `ziwei/doushu-guanjian`。
depends_on:
  - ziwei-doushu-quanshu
  - taiwei-fu
informs:
  - ziwei current-event observation
  - ziwei twelve-palace borrowing
  - ziwei environment/physiognomy cross-check
core_use_cases:
  - 已有紫微盘事实层之后，补充民国斗数观测法
  - 十二宫活用、假借、亲属/姻亲/外孙等宫位扩展
  - 命盘与阴宅、阳宅、相法、村镇/邻里方位互证
  - 红鸾、大耗、咸池、流羊、天刑、巨门等星曜在案例中的经验旁证
  - 占课时把一事一物一地一人视作有身命的实验性斗数用法
not_for:
  - 代替 `tool.ziwei.bindisk` 排盘或自由手算宫位星曜
  - 作为古法紫微的一线原典
  - 替代《紫微斗数全书》《太微赋》的基础星曜、安星、赋文骨架
  - 未给命盘/时间/地点/方位事实时直接断具体吉凶
  - 将疾病、死亡、刑讼、性道德等民国断语铁口化
extraction_targets:
  - source_identity
  - terms
  - observation_rules
  - twelve_palace_borrowing
  - procedures
  - quote_index
conflict_policy: |
  本 pack 属晚近观测/注释层。与《紫微斗数全书》《太微赋》冲突时，基础排盘、星曜原义、赋文源流以一线 pack 为先；本 pack 仅作为案例观察、旁证和方法提示。
  与现代飞星、钦天、中州等流派冲突时，不自动外推，只标注为本书《斗数观测录》脉络。
  与风水、相法、择日、八字等系统相交时，只作交叉旁证，不跨系统覆盖其本门规则。
validation_notes: |
  2026-07-05 已按本地 NLC/Commons 页图逐页校阅 116/116 页并装配 `reviewed_fulltext.md`。
  page-115 是勘误表，保留为版本元数据，不直接升级为正文规则。
  由于影印本题名、作者题署、正文书名之间存在层次差异，本 pack 必须保守标注为民国观测注释层。
modern_notes: |
  本书有大量直接、粗砺的民国式断语。输出时不删去传统指征，但必须分清“原书说法 / 可复核事实 / 现代解释 / 不确定性”。
---

# 華山陳希夷先生飛星紫微斗數原旨 Reference Pack（index）

> 本文件是《華山陳希夷先生飛星紫微斗數原旨 / 斗數觀測錄》参考包入口。
> 详细内容分布在 `chapter-map.md / terms.md / rules.md / procedures.md / quote-index.md / validation.md`。

## Source

- **题名**：華山陳希夷先生飛星紫微斗數原旨。
- **正文线索**：斗數觀測錄序、斗數觀測錄。
- **作者题署**：题陈希夷；实际撰者待考。
- **版本系统**：NLC 民国图书，Wikimedia Commons 116 页 PDF 影印。
- **本地全文**：`references/fulltext/ziwei/feixing-ziwei-doushu-yuanzhi/fulltext.md`。
- **校阅状态**：`ocr_reviewed_complete`，116/116 页。

## Position In Lineage

- **上游依赖**：先用《紫微斗数全书》《太微赋》建立紫微盘、星曜、宫位、赋文骨架。
- **本书位置**：民国时期紫微观测法、案例法、十二宫假借法、环境/相法互证法。
- **下游作用**：给 `mingli-master` 增加“同一张盘如何观察人、宅、邻里、方向、事件”的旁证层。

## Loading Guide

1. 默认只加载本文件 `index.md`。
2. 需要术语和边界 → `terms.md`。
3. 需要判断规则 → `rules.md`。
4. 需要执行流程 → `procedures.md`。
5. 需要短引证据 → `quote-index.md`。
6. 需要来源和风险 → `validation.md`。
7. 只有用户问题涉及紫微盘的具体观察、亲属宫位假借、邻里/阴阳宅方位、红鸾大耗、天刑巨门等细节时，再加载本 pack 的细节文件。

## File Map

| 文件 | 职责 |
|---|---|
| [index.md](./index.md) | 入口索引 |
| [chapter-map.md](./chapter-map.md) | 116 页影印本分段地图 |
| [terms.md](./terms.md) | 术语、别名、观测法概念 |
| [rules.md](./rules.md) | 可追溯判断规则 |
| [procedures.md](./procedures.md) | 可执行调用流程 |
| [quote-index.md](./quote-index.md) | 短引与页码定位 |
| [validation.md](./validation.md) | 完整性、OCR、风险、测试 |

## Routing

本 pack 只能在紫微事实层已完成后调用：

- 必需：`calendar_normalization`、十二宫、命身宫、星曜、四化、大限/流年/小限等 adapter 等价输出。
- 可选增强：出生地、居住地、阴阳宅坐向、房屋/邻里方位、用户实际观察事实。
- 禁止：缺少盘面事实时自由按“明天运势”或“某方位吉凶”空断。

## Conflict

若用户问基础紫微，请优先 `ziwei-doushu-quanshu` 与 `taiwei-fu`。
若用户问“这件事、这个家宅、这处方位、某亲属宫位怎么借用”，且已有事实层，再调用本 pack。

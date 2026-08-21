---
title: 神相全编
slug: shenxiang-quanbian
system: physiognomy
school:
  - 面相
  - 全身相
  - 五官四肢
  - 部位形局
  - 神气骨肉
  - 黑子纹理
source_layer: side_evidence
source_status: normalized_ready
source_scope: 古今图书集成艺术典第631-639卷辑录本；非独立十二卷刊本
source_links:
  - https://zh.wikisource.org/wiki/%E6%AC%BD%E5%AE%9A%E5%8F%A4%E4%BB%8A%E5%9C%96%E6%9B%B8%E9%9B%86%E6%88%90/%E5%8D%9A%E7%89%A9%E5%BD%99%E7%B7%A8/%E8%97%9D%E8%A1%93%E5%85%B8/%E7%AC%AC631%E5%8D%B7
version_notes: |
  本 pack 当前采用《钦定古今图书集成·博物汇编·艺术典》第 631-639 卷“相术部汇考”作为 normalized source。该来源覆盖“神相全编一”至“神相全编九”，并含相儿经、论相、人相篇、相术部汇考标题等上下文材料。
  因此本 pack 的 D2 ready 只表示“当前本地辑录本源文已完整建图并可追溯”，不表示已取得独立《神相全编》十二卷刊本全文。后续若补国图 PDF / 识典古籍十二卷本，应另建 edition layer 并做差异表。
depends_on: []
informs:
  - 现代相术教学
  - bingjian
core_use_cases:
  - 全身部位、五官、五岳四渎、五星六曜、六府三才三停的传统相法术语溯源
  - 形神气声、骨肉、气色等相术总纲的原文证据检索
  - 神异赋、岩电道人神眼经、麻衣金锁赋、银匙歌、袁柳庄诸赋等长赋篇名与短引定位
  - 与《冰鉴》作旁证互参
not_for:
  - 命盘事实计算
  - 对真人照片、视频或外貌作判断
  - 富贵贫贱、寿夭、灾厄、婚育、子嗣、疾病的硬断
  - 招聘、婚配、保险、刑侦等现实决策
extraction_targets:
  - section_map
  - concepts
  - terms
  - rules
  - procedures
  - cautions
  - quote_index
conflict_policy: |
  本书属 physiognomy / side_evidence / 汇编百科层。命盘判断时只作旁证；与 bazi/ziwei/xingming 冲突时，命盘主线优先。与 bingjian 冲突时，bingjian 可作雅训语义，本书作百科查全。
validation_notes: |
  D2 修订完成：source_lines=5109，structural_units=410，chapter-map 全部 done，quote-index 每单元一条精确短引。source_risk 保留：当前源为古今图书集成辑录本，不是独立十二卷本。
modern_notes: |
  本书含大量古代贵贱、寿夭、灾祸、婚育、性别与身体评价判语。任何下游 skill 必须把它们视为历史术语和文本证据，不得据此评价具体个人。
---

# 神相全编 Reference Pack

本包是相法体系的旁证层资料，不是命盘主线。主 skill 默认只加载本文件；需要原文证据时再加载 `section-map.md` / `chapter-map.md` / `quote-index.md`。

## Source

- **底本**：《钦定古今图书集成·博物汇编·艺术典》第 631-639 卷“相术部汇考”。
- **本地 normalized**：`references/fulltext/physiognomy/shenxiang-quanbian/fulltext.md`。
- **源文范围**：5109 行，410 个结构单元；覆盖“神相全编一至九”与相术部上下文。
- **版本红线**：当前并非独立《神相全编》十二卷刊本；不要把 D2 ready 误写成十二卷全本已完成。

## Loading Guide

1. 默认加载 `index.md` 获取路由、版本边界和禁用范围。
2. 查完整目录或小节范围，加载 `section-map.md`。
3. 查 D2 覆盖状态，加载 `chapter-map.md`。
4. 查术语定义，加载 `terms.md`。
5. 查可用/禁用规则，加载 `rules.md` 与 `procedures.md`。
6. 查短引出处，加载 `quote-index.md`。
7. 校验版本和审计结论，加载 `validation.md`。

## File Map

| 文件 | 职责 | 何时加载 |
|---|---|---|
| [index.md](./index.md) | 入口索引、版本边界、路由 | 默认加载 |
| [section-map.md](./section-map.md) | 410 个结构单元全索引 | 需要完整目录/按篇检索 |
| [chapter-map.md](./chapter-map.md) | D2 章节覆盖表 | 需要审计覆盖率 |
| [terms.md](./terms.md) | 核心术语抽取 | 需要术语解释 |
| [rules.md](./rules.md) | 旁证规则与禁用规则 | 需要规则召回 |
| [procedures.md](./procedures.md) | 调用流程和安全包装 | 需要输出流程 |
| [quote-index.md](./quote-index.md) | 每结构单元短引证据 | 需要原文引用 |
| [validation.md](./validation.md) | 验证报告与后续补本计划 | 需要验收 |

## Safety

- 不接收真人照片或视频帧做“看相”。
- 不据本书判断具体个人的富贵、贫贱、寿夭、疾病、灾厄、婚育、子嗣。
- 动物比喻、贵贱判语、灾祸判语只作古文术语研究，不作现实评价。
- 输出时必须标注：`旁证层 / 不参与命盘硬判断 / 当前为古今图书集成辑录本`。

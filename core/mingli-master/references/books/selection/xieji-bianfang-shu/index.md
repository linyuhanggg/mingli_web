---
title: 钦定协纪辨方书
slug: xieji-bianfang-shu
system: selection
school:
  - 官方历法
  - 御定择日
  - 神煞辨方
  - 嫁娶丧葬
  - 建除黄黑道
source_layer: primary
source_status: normalized_ready
source_links:
  - https://zh.wikisource.org/zh-hans/%E6%AC%BD%E5%AE%9A%E5%8D%94%E7%B4%80%E8%BE%A8%E6%96%B9%E6%9B%B8_(%E5%9B%9B%E5%BA%AB%E5%85%A8%E6%9B%B8%E6%9C%AC)
  - https://ctext.org/wiki.pl?if=gb&res=595276
  - https://archive.org/details/06056502.cn
version_notes: |
  清乾隆四年（1739）允禄、梅毂成、何国宗等奉敕编纂的官方择日典籍。
  收入《钦定四库全书》子部·术数类·阴阳五行属。全书三十六卷。
  御制序言：纪元厘正民时、协五纪、辨五方，以匡正《选择通书》之讹。
  系康熙朝《星历考原》的扩展与订正，为清代官方颁行的择日总汇。
  本 pack 取四库全书本（维基文库 + Internet Archive 影印）为基。
  现代仍是择日体系的"集大成"权威；与民间通书（董公择日、玉匣记）属不同口径。
depends_on:
  - xingli-kaoyuan
informs:
  - donggong-zeri
  - yuqia-ji
core_use_cases:
  - 官方择日体系的"集大成"参考（嫁娶/丧葬/起造/出行/上任/祭祀）
  - 全套年神 / 月神 / 日神 / 时神的考源与裁判
  - 建除十二神、二十八宿、黄黑道的官方取法
  - 与民间通书冲突时的"官方裁判"参照
not_for:
  - 实际择日计算（必须调用 mingli-master.selection.v1）
  - 嫁娶/丧葬/出行的事实性吉凶断言（仅作历法参考）
  - 神煞起例源流考据（应优先 xingli-kaoyuan 卷一卷二）
  - 通书系民俗杂占（应优先 yuqia-ji）
extraction_targets:
  - terms
  - rules
  - procedures
  - cautions
  - quote_index
conflict_policy: |
  与同体系其他典籍冲突时按 matrices/conflict-policy.md §1.4 裁判：
  - 与民间通书（董公择日 / 玉匣记）口径冲突 → 以本书（官方）为准。
  - 与《星历考原》冲突 → 本书是《星历考原》的订正与扩展，以本书为后出定论。
  - 神煞起例口诀差异 → 以本书"辨讹"卷为定论。
  - 涉及具体日子吉凶 → 一律转 mingli-master.selection.v1 计算。
validation_notes: |
  - source_status 维持 partial（维基文库 + Internet Archive 文本未对四库本影印逐卷复核）。
  - 全书 36 卷，本 pack 按"卷"作 chapter 粒度，做摘要级覆盖（不做小目级）。
  - 卷十至卷三十二为"日表 / 时辰" 大型表格，本 pack 不复制原表，只声明"调用 mingli-master.selection.v1"。
  - 卷三十三至三十六"辨讹"为本书最大特色，需重点保留辨讹规则。
cultural_caveats: |
  本书为清代官方颁行的择日典籍，其"嫁娶/丧葬/出行/起造"吉凶规则仍属古代礼仪体系，
  现代不构成事实判断；输出时必须加 caveat："文化参考，非事实判断"。
---

# 钦定协纪辨方书 Reference Pack（index）

> 本文件是《钦定协纪辨方书》参考包的**入口索引**，不做规则 / 术语 / 短引的详细内容。
> 详细内容分布在 `chapter-map.md / section-map.md / terms.md / rules.md / procedures.md / quote-index.md / validation.md`。
> 主 skill 默认只加载本文件；按需加载其它文件。

## Source

- **作者**：清·允禄、梅毂成、何国宗等奉敕编纂。
- **成书**：乾隆四年（1739）御制序，颁行天下。
- **底本系统**：
  - 《钦定四库全书》子部·术数类本（本 pack 主要参照系统）
  - 维基文库 / Internet Archive 影印 PDF
  - CTP 文本锚点（不作下载源，TOS 限制）
- **卷次结构**：全书 36 卷
  - 卷一·二：基础（河图、洛书、八卦、甲历、四序、十二月辟卦、二十八宿配日、五行用事、干支、纳音、纳甲、二十四方位、八卦纳甲三合等）
  - 卷三：年表（年神：岁德合、岁枝德、岁破、大将军、博士、蚕室、太阴、白虎、豹尾、金神等）
  - 卷四：月表（月神：建除十二神、月厌、月空、天德、月德、五合等）
  - 卷五·六：日表 / 时辰（具体逐日 / 逐时神煞分布）
  - 卷七·八：用事吉凶宜忌（嫁娶、入宅、纳采、丧葬、起造、出行等）
  - 卷九~三十二：年神 / 月神 / 日神 / 时神逐项详考
  - 卷三十三~三十六：辨讹（订正《选择通书》及民间通书之讹）
- **复核状态**：`partial`。维基文库文本应继续与四库本影印对校。

## Position In Lineage

- **在择日体系中的位置**：清代官方择日的总汇，集大成之作。
- **上游**：
  - 《星历考原》（康熙朝御定，本书的直接前身）
  - 《选择通书》（旧本，本书"辨讹"对象）
- **下游**：
  - 清末民国通书直接承袭本书框架。
  - 现代万年历 / 黄历应用底层规则多出本书。
  - 民间通书系（董公、玉匣记）虽口径不同，但形式语言互通。

## Loading Guide

主 skill 加载约定（遵循 matrices/validation-checklist.md §L.11）：

1. **默认只加载本文件** `index.md`：拿 frontmatter / 卷次概览 / 分流路由。
2. **需要查具体卷次** → 加载 `chapter-map.md`。
3. **需要查术语** → 加载 `terms.md`。
4. **需要查判断规则** → 加载 `rules.md`。
5. **需要查可操作流程** → 加载 `procedures.md`。
6. **需要查短引 + 出处** → 加载 `quote-index.md`。
7. **需要校验覆盖率 / 版本状态** → 加载 `validation.md`。

## File Map

| 文件 | 职责 | 何时加载 |
|---|---|---|
| [index.md](./index.md) | 入口索引 + frontmatter + 卷次概览 + 路由 | 默认加载 |
| [chapter-map.md](./chapter-map.md) | 全书 36 卷章节地图 + digest_status | 需要查具体卷次 |
| [terms.md](./terms.md) | 全书术语抽取（按分组） | 需要查术语定义 |
| [rules.md](./rules.md) | 全书判断规则（按主题抽取） | 需要查判断规则 |
| [procedures.md](./procedures.md) | 全书可操作流程（工具调用） | 需要查操作流程 |
| [quote-index.md](./quote-index.md) | 短引索引 + 出处 | 需要引用原文 |
| [validation.md](./validation.md) | 全书覆盖率 + 版本核验 + 待办 | 需要校验覆盖率 |

## Routing

主 skill 收到择日相关问题后：

1. 本 pack 是择日体系的"官方集大成"代表（详见 matrices/routing-matrix.md §6）。
2. 按问题类型分流：
   - 神煞起例考源 → `selection/xingli-kaoyuan`
   - 通用择日 / 嫁娶 / 丧葬 / 起造 / 上任 → 本 pack（官方裁判）
   - 民间杂占 / 通书 → `selection/yuqia-ji`
   - 月将吉凶日（民间口径） → `selection/donggong-zeri`
   - 涉及具体日子吉凶 → `mingli-master.selection.v1`（必需）
3. 与民间通书冲突时，以本 pack 为权威裁判。

## 冲突裁判

详见 frontmatter `conflict_policy` 与 matrices/conflict-policy.md §1.4。

## 文化警示

本 pack 的择日规则属古代官方礼仪体系；输出涉及"某日吉凶""某事宜忌"的内容时，
**必须加 caveat："文化参考，非事实判断"**。

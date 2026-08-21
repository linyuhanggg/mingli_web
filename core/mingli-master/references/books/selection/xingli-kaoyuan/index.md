---
title: 御定星历考原
slug: xingli-kaoyuan
system: selection
school:
  - 官方历法
  - 御定择日
  - 神煞起例考源
  - 年神月神
source_layer: primary
source_status: normalized_ready
source_links:
  - https://zh.wikisource.org/zh-hans/%E5%BE%A1%E5%AE%9A%E6%98%9F%E6%9B%86%E8%80%83%E5%8E%9F
  - https://ctext.org/wiki.pl?if=gb&res=595275
version_notes: |
  康熙朝（1713 前后）御定，李光地等奉敕考定，凡六卷。
  收入《钦定四库全书》子部·术数类·阴阳五行属。
  乾隆朝《钦定协纪辨方书》36 卷的直接前身与素材底本。
  本书最大价值在"神煞起例的考源"——逐神煞溯源至《历事明原》《选择通书》并加考订。
  本 pack 取四库全书本（维基文库）为基。
  与《协纪辨方书》比对：本书是单卷小型考源；协纪是 36 卷集大成。
depends_on: []
informs:
  - xieji-bianfang-shu
  - donggong-zeri
  - yuqia-ji
core_use_cases:
  - 神煞起例的官方考源（"此神出于何典、起法如何"）
  - 年神 / 月神 / 日神 / 时神的起例口诀考证
  - 与《协纪辨方书》对照差异，定本源
  - 与民间通书冲突时，作为"上游官方源"的二次参证
not_for:
  - 实际择日计算（必须调用 mingli-master.selection.v1）
  - 嫁娶 / 丧葬 / 出行的事实性吉凶断言（仅作历法参考）
  - 用事宜忌的"定论"（应优先 xieji-bianfang-shu 卷七·八）
  - 民俗杂占（应优先 yuqia-ji）
extraction_targets:
  - terms
  - rules
  - procedures
  - cautions
  - quote_index
conflict_policy: |
  与同体系其他典籍冲突时按 matrices/conflict-policy.md §1.4 裁判：
  - 与《协纪辨方书》冲突 → 协纪是本书的订正与扩展，以协纪为后出定论；
    但本书在"神煞起例溯源"层面优先（协纪辨讹卷亦多次引本书）。
  - 与民间通书（董公择日 / 玉匣记）口径冲突 → 以本书（官方上游）为准。
  - 涉及具体日子吉凶 → 一律转 mingli-master.selection.v1 计算。
validation_notes: |
  - source_status 维持 partial（维基文库文本未对四库本影印逐卷复核）。
  - 全书 6 卷，本 pack 按"卷"作 chapter 粒度，关键神煞（每卷 5~10 条）作为 partial 引用。
  - 不复制大段原文；神煞起例口诀只引题名 + 起例锚点。
cultural_caveats: |
  本书为清初官方颁行的择日典籍考源；其"嫁娶/丧葬/出行/起造"吉凶规则属古代礼仪体系，
  现代不构成事实判断；输出时必须加 caveat："文化参考，非事实判断"。
---

# 御定星历考原 Reference Pack（index）

> 本文件是《御定星历考原》参考包的**入口索引**，不做规则 / 术语 / 短引的详细内容。
> 详细内容分布在 `chapter-map.md / terms.md / rules.md / procedures.md / quote-index.md / validation.md`。
> 主 skill 默认只加载本文件；按需加载其它文件。

## Source

- **奉敕**：清·李光地等奉康熙帝敕考定。
- **成书**：康熙五十二年（1713）前后；与《选择通书》《万年书》同时颁行。
- **底本系统**：
  - 《钦定四库全书》子部·术数类本（本 pack 主要参照系统）
  - 维基文库电子文本
  - CTP 文本锚点（不作下载源，TOS 限制）
- **卷次结构**：全书 6 卷
  - 卷一·象数考原（天地、五纪、八卦、五行、甲历、十干、十二支、十二月辟卦、二十四方位、五行用事、闰月、纳音、十二辰二十八宿、五虎遁、五鼠遁、三合五合六合）
  - 卷二·年神方位（三元年九星、岁干合、岁德合、岁枝德、太岁、博士、力士、蚕室、蚕官、蚕命、大将军、太阴、白虎、豹尾、金神等）
  - 卷三·月事吉神（建除十二神中的吉神 / 天德 / 月德 / 月空 / 五合 / 母仓等）
  - 卷四·月事凶神（月厌 / 月破 / 月虚 / 月害 / 大耗 / 小耗等）
  - 卷五·日时总类（黄道黑道 / 二十八宿 / 贵登天门 / 四大吉时等）
  - 卷六·用事宜忌（六十事项的宜忌通例）
- **复核状态**：`partial`。维基文库文本应继续与四库本影印对校。

## Position In Lineage

- **在择日体系中的位置**：清代官方择日的"考源蓝本"。
- **上游**：
  - 曹振圭《历事明原》（元代）
  - 旧本《选择通书》
- **下游**：
  - 《钦定协纪辨方书》36 卷（直接扩展）
  - 清末民国通书系
  - 民间通书（董公择日 / 玉匣记）多处取义于本书

## Loading Guide

主 skill 加载约定（遵循 matrices/validation-checklist.md §L.11）：

1. **默认只加载本文件** `index.md`。
2. **需要查神煞起例考源** → 加载 `rules.md` 与 `quote-index.md`。
3. **需要查具体卷次** → 加载 `chapter-map.md`。
4. **需要查术语** → 加载 `terms.md`。
5. **需要查可操作流程** → 加载 `procedures.md`（全部依赖 mingli-master.selection.v1）。
6. **需要校验覆盖率** → 加载 `validation.md`。

## File Map

| 文件 | 职责 | 何时加载 |
|---|---|---|
| [index.md](./index.md) | 入口索引 + frontmatter + 路由 | 默认加载 |
| [chapter-map.md](./chapter-map.md) | 全书 6 卷章节地图 + digest_status | 需要查具体卷次 |
| [terms.md](./terms.md) | 全书术语抽取（按分组） | 需要查术语定义 |
| [rules.md](./rules.md) | 全书判断规则（含神煞起例口诀考源） | 需要查判断规则 |
| [procedures.md](./procedures.md) | 全书可操作流程（工具调用） | 需要查操作流程 |
| [quote-index.md](./quote-index.md) | 短引索引 + 出处 | 需要引用原文 |
| [validation.md](./validation.md) | 全书覆盖率 + 版本核验 + 待办 | 需要校验覆盖率 |

## Routing

主 skill 收到择日相关问题后：

1. 本 pack 是"神煞起例考源"的官方源（详见 matrices/routing-matrix.md §6）。
2. 按问题类型分流：
   - 神煞起例考源 → 本 pack（首选）
   - 通用择日 / 嫁娶 / 丧葬 / 起造 → `selection/xieji-bianfang-shu`（官方裁判）
   - 民间杂占 / 通书 → `selection/yuqia-ji`
   - 月将吉凶日（民间口径） → `selection/donggong-zeri`
   - 涉及具体日子吉凶 → `mingli-master.selection.v1`（必需）

## 冲突裁判

详见 frontmatter `conflict_policy` 与 matrices/conflict-policy.md §1.4。

## 文化警示

本 pack 的择日规则属古代官方礼仪体系；输出涉及"某日吉凶""某事宜忌"的内容时，
**必须加 caveat："文化参考，非事实判断"**。

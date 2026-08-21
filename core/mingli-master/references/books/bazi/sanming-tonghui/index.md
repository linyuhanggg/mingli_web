---
title: 三命通会
slug: sanming-tonghui
system: bazi
school:
  - 子平综合汇编
  - 月令格局
  - 旺衰生克
  - 调候
  - 神煞辅助
  - 古法源流
  - 纳音
source_layer: primary
source_status: partial
source_links:
  - https://ctext.org/wiki.pl?if=gb&res=532360
version_notes: |
  明万历，万民英（号育吾子）编。
  版本系统：
  - 明万历原刊本（编次与四库本略有差异，需馆藏复核）
  - 《钦定四库全书》子部·术数类本（清乾隆官修，本 pack 主要参照系统）
  - 民国与现代点校本（归 commentary 层，不在本 pack）
  CTP 所收为四库本系统的电子化文本。
  URN: ctp:wb532360
  卷次结构：9 卷（卷一至卷九）。
depends_on:
  - yuanhai-ziping
  - wuxing-jingji
  - li-xuzhong-mingshu
  - luoluzi-sanming
informs:
  - ziping-zhenquan
  - ditiansui-chanwei
  - qiongtong-baojian
  - shenfeng-tongkao
core_use_cases:
  - 八字综合检索与术语溯源
  - 月令格局基本框架查找
  - 神煞汇总查询
  - 早期禄命到子平过渡的术语桥接
  - 多派观点的横向对照
  - 日柱 + 时辰断语查找（卷八卷九）
not_for:
  - 排盘事实计算（不替代 tool.bazi.paipan）
  - 调候用神细则（应优先《穷通宝鉴》）
  - 月令格局成败救应的精细推演（应优先《子平真诠》）
  - 气势通关病药的精细推演（应优先《滴天髓阐微》）
  - 现代命理流派结论
  - 真太阳时换算等历法事实
extraction_targets:
  - concepts
  - terms
  - rules
  - procedures
  - cautions
  - quote_index
conflict_policy: |
  与同体系其他典籍冲突时按问题类型裁判（详见 matrices/conflict-policy.md §1.2）：
  - 月令格局成败 → 优先《子平真诠》；本书作总索引。
  - 五行旺衰、气势通关 → 优先《滴天髓阐微》；本书作汇总参考。
  - 调候 → 优先《穷通宝鉴》；本书作补充。
  - 神煞与格局 / 用神冲突 → 神煞作辅证，不主主线。
  - 与早期禄命纳音冲突 → 本书已是后世子平整合，源流问题回查《李虚中命书》《珞琭子三命消息赋注》《五行精纪》。
validation_notes: |
  - 作者万民英归属、版本系统（万历本 vs 四库本 vs 民国整理本）需进一步核验。
  - 四库本与万历原刊本在编次、收录子目上有差异，需逐卷复核。
  - "继善篇""喜忌篇""玄机赋"等通行段落是否原属本书 / 抑或转录他书，需复核。
  - 神煞清单数量存在不同抄本差异，详见 terms.md 的神煞分组。
  - 卷八卷九的"日时断"几百条，聚合到"日组"粒度；逐条复核需要后续 Batch。
  - 本 pack 经 Batch 0.5→0.7 返工为文件组结构，Batch 0.8 §L.9 重审通过 → status: ready。source_status 维持 partial（四库本影印未逐章复核）。ready 表示可按需加载，不表示四库影印已复核。
modern_notes: |
  现代部分作者（如徐乐吾、韦千里、梁湘润、李涵辰、台北各教学派）会引用《三命通会》原文做注释或反驳，
  这些观点 **不**进入原典层；如需引入，必须放在对应作者的 commentary / modern 层 pack 中，本 pack 不收录。
---

## D2 Source Scope

- **source_lines**: 8641
- **structural_units**: 970
- **scope**: 维基文库整理本；按卷章 Markdown 标题建图，文本层面为全本覆盖。
- **version_note**: 维基文库整理质量仍需四库本影印复核；本次 D2 ready 只表示本地 normalized source 可完整追溯。
- **evidence_files**: `section-map.md`, `chapter-map.md`, `quote-index.md`


# 三命通会 Reference Pack（index）

> 本文件是《三命通会》参考包的**入口索引**，不做规则 / 术语 / 短引的详细内容。
> 详细内容分布在 `chapter-map.md / terms.md / rules.md / procedures.md / quote-index.md / validation.md`。
> 主 skill 默认只加载本文件；按需加载其它文件（详见 §Loading Guide）。

## Source

- **作者**：万民英（号育吾子），明万历间编集。
- **版本系统**：
  - 《钦定四库全书》子部·术数类本（清乾隆官修，本 pack 主要参照系统）
  - 万历原刊本（明代原刊，编次与小目略异）
  - 民国及现代点校本（commentary 层）
- **在线索引**：
  - CTP：https://ctext.org/wiki.pl?if=gb&res=532360
  - CTP URN：`ctp:wb532360`
- **卷次结构**：全书 9 卷
  - 卷一：基础理论（五行生成 / 生克 / 干支 / 纳音）
  - 卷二：干支与岁运（人元司事 / 节气 / 遁月日 / 大运小运 / 太岁 / 干支合化 / 刑冲）
  - 卷三：神煞大全（禄马 / 贵人 / 空亡 / 羊刃 / 孤辰寡宿 / 天罗地网 等 23 类）
  - 卷四：十干坐支与十二月得干吉凶、时地分野
  - 卷五：十神论（印食官财名义 / 正官 / 偏官）
  - 卷六：杂格 + 十神（财印食伤刃禄）
  - 卷七：性情 / 疾病 / 女命 / 小儿 / 六亲 / 孕生男女
  - 卷八：六甲 / 六乙 / 六丙 / 六丁 / 六戊 日 + 十二时 断语（60 组）
  - 卷九：六己 / 六庚 / 六辛 / 六壬 / 六癸 日 + 十二时 断语（60 组）
- **复核状态**：`partial`。CTP 文本应继续与四库本影印（文渊阁本）对校。

## Position In Lineage

- **在八字子平体系中的位置**：总汇编型枢纽，处于「早期禄命纳音 / 渊海子平 → 子平真诠 / 滴天髓阐微 / 穷通宝鉴」之间。
- **上游**：
  - 《李虚中命书》《珞琭子三命消息赋注》《玉照神应真经》《兰台妙选》：禄命源头，本书广泛汇集其断语与术语。
  - 《五行精纪》：宋代禄命汇编，与本书在术语与例句上有继承与互证关系。
  - 《渊海子平》：南宋徐子平系统的整理本，是本书直接承袭的子平骨架。
- **下游**：
  - 《子平真诠》：从本书及《渊海子平》中提炼月令格局成败救应。
  - 《滴天髓阐微》：从气势生克、通关病药一线发展，对本书神煞 / 杂论部分有取舍。
  - 《穷通宝鉴》：从月令调候一线发展。
  - 《神峰通考》：与本书略同期，互为旁证。

简言之：**子平体系想做"百科查找"先翻《三命通会》；想做"派别精修"再分别去《子平真诠》《滴天髓阐微》《穷通宝鉴》。**

## Core Use Cases

- 八字综合检索与术语溯源
- 月令格局基本框架查找
- 神煞汇总查询（本书是神煞条目的最大汇编之一）
- 早期禄命到子平过渡的术语桥接
- 多派观点的横向对照
- 日柱 + 时辰断语查找（卷八卷九）

## Not For

- 排盘事实计算（必须调用 `tool.bazi.paipan`）
- 调候用神细则（应优先《穷通宝鉴》）
- 月令格局成败救应的精细推演（应优先《子平真诠》）
- 气势通关病药的精细推演（应优先《滴天髓阐微》）
- 现代命理流派结论（应进对应作者的 commentary / modern 层 pack）
- 真太阳时换算等历法事实

## Loading Guide

主 skill 加载约定（遵循 matrices/validation-checklist.md §L.11）：

1. **默认只加载本文件** `index.md`：拿 frontmatter / 卷次概览 / 分流路由。
2. **需要查具体章节** → 加载 `chapter-map.md`，按卷 / 小目查找。
3. **需要查术语** → 加载 `terms.md`，按分组查定义。
4. **需要查判断规则** → 加载 `rules.md`，按 `rule_id` 或 `source_chapter` 查。
5. **需要查可操作流程** → 加载 `procedures.md`。
6. **需要查短引 + 出处** → 加载 `quote-index.md`。
7. **需要校验覆盖率 / 版本状态** → 加载 `validation.md`。

不允许主 skill 一次性加载全部 7 个文件；按需加载。

## File Map

| 文件 | 职责 | 何时加载 |
|---|---|---|
| [index.md](./index.md) | 入口索引 + frontmatter + 卷次概览 + 路由 | 默认加载 |
| [chapter-map.md](./chapter-map.md) | 全书 9 卷章节地图 + digest_status | 需要查具体章节 |
| [terms.md](./terms.md) | 全书术语抽取（按分组） | 需要查术语定义 |
| [rules.md](./rules.md) | 全书判断规则（按卷抽取） | 需要查判断规则 |
| [procedures.md](./procedures.md) | 全书可操作流程 | 需要查操作流程 |
| [quote-index.md](./quote-index.md) | 短引索引 + 出处 | 需要引用原文 |
| [validation.md](./validation.md) | 全书覆盖率 + 版本核验 + 待办 | 需要校验覆盖率 |

## Routing

主 skill 收到八字相关问题后：

1. 本 pack 是八字体系的"综合查找入口"（详见 matrices/routing-matrix.md §2.1）。
2. 按问题类型分流：
   - 月令格局成败 → `bazi/ziping-zhenquan`
   - 旺衰气势通关病药 → `bazi/ditiansui-chanwei`
   - 调候 → `bazi/qiongtong-baojian`
   - 子平法源流 → `bazi/yuanhai-ziping`
   - 神煞 / 纳音 / 古法 → 本 pack 内查 `chapter-map.md`（卷三、卷一、卷二）
3. 事实层未确定的盘必须先调用 `tool.bazi.paipan`。

## 冲突裁判

详见 frontmatter `conflict_policy` 与 matrices/conflict-policy.md §1.2。

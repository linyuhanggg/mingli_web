---
title: 渊海子平
slug: yuanhai-ziping
system: bazi
school:
  - 子平骨架
  - 月令格局雏形
  - 十神论命
  - 大运流年
  - 神煞辅助
source_layer: primary
source_status: partial
source_links:
  - https://ctext.org/wiki.pl?if=gb&remap=gb&res=727782
version_notes: |
  通行说法：宋末元初徐大升（徐大升 / 徐昇）据徐子平法整理成书。
  CTP 所收为《钦定四库全书》本系统的电子文本；四库提要归子部·术数类·相宅相墓。
  书名"渊海"喻"深广如海"；"子平"指徐子平（宋代）的命法体系。
  版本系统仍有争议：
  - 徐大升本系（早期本）
  - 明清增补本系（与万历、四库本差异较大）
  - 现代点校本（多家，归 commentary 层）
  本 pack 取四库本为基，但具体卷次与增补段落仍需逐段复核。
  "徐子平"的历史身份尚无定论（是否为宋初或更早），本书归属问题需在待核验项中持续核查。
depends_on:
  - li-xuzhong-mingshu
  - luoluzi-sanming
informs:
  - sanming-tonghui
  - ziping-zhenquan
  - shenfeng-tongkao
core_use_cases:
  - 子平法体系源流与早期术语溯源
  - 四柱八字、十神、月令、格局雏形的基本框架
  - 早期大运 / 流年 / 神煞用法
  - 与《三命通会》的对照（哪些段落被《三命通会》直接承袭）
not_for:
  - 排盘事实计算（不替代 tool.bazi.paipan）
  - 月令格局成败救应的精细推演（应优先《子平真诠》）
  - 旺衰、气势、通关、病药（应优先《滴天髓阐微》）
  - 调候用神细则（应优先《穷通宝鉴》）
  - 把本书当作"子平法最终权威"（本书只是源流骨架）
  - 把"徐子平"当作确定作者（历史身份仍有争议）
extraction_targets:
  - concepts
  - terms
  - rules
  - procedures
  - cautions
  - quote_index
conflict_policy: |
  与同体系其他典籍冲突时按问题类型裁判（详见 matrices/conflict-policy.md §1.2）：
  - 本书术语与《三命通会》不一致 → 以本书为术语源流参考，《三命通会》作汇编回查。
  - 格局成败与《子平真诠》不一致 → 以《子平真诠》为精修版，本书作早期雏形。
  - 旺衰气势与《滴天髓阐微》不一致 → 以《滴天髓阐微》为精修版，本书不主一线判断。
  - 调候与《穷通宝鉴》不一致 → 以《穷通宝鉴》为精修版。
  - 与早期禄命（李虚中、珞琭子、五行精纪）在术语上同源 → 本书是过渡枢纽，不取代上游。
validation_notes: |
  - Batch 1A-1 返工为全书覆盖型文件组结构。source_status 维持 partial（四库本影印未逐章复核）。
  - 作者"徐大升"/"徐子平"身份、序跋、各家书目记载需交叉验证。
  - 本书与早期禄命文献的段落继承关系需逐段对读。
  - "继善篇""喜忌篇"等通行段落的归属待考。
  - 四库本与万历/明清增补本在卷次上的差异尚未完成复核。
modern_notes: |
  现代子平教学（徐乐吾 / 韦千里 / 梁湘润 / 李涵辰 / 台北各派）常以《渊海子平》为"祖书"并附大量注释。
  这些注释 **不** 进入本 pack 原典层；若需引入必须放到对应作者的 commentary / modern 层 pack。
  特别注意：现代某些派别把《渊海子平》中某些"经验断语"当作铁律，这与原典语气（经验性）不符，需回原典核对语气。
---

## D2 Source Scope

- **source_lines**: 4974
- **structural_units**: 74
- **scope**: 维基文库通行五卷本整理本；原页面未严格按五卷标注，以小节标题组织。
- **version_note**: 通行本与四库本存在版本差异，维基文库有 No source 风险；本次 D2 ready 只表示当前 normalized source 的章节证据层完整。
- **evidence_files**: `section-map.md`, `chapter-map.md`, `quote-index.md`


# 渊海子平 Reference Pack（index）

> 本文件是《渊海子平》参考包的**入口索引**，不做规则 / 术语 / 短引的详细内容。
> 详细内容分布在 `chapter-map.md / terms.md / rules.md / procedures.md / quote-index.md / validation.md`。
> 主 skill 默认只加载本文件；按需加载其它文件（详见 §Loading Guide）。

## Source

- **作者**：署名徐大升（徐昇），据"徐子平"之法整理。宋末元初成书。
- **版本系统**：
  - 《钦定四库全书》子部·术数类本（本 pack 主要参照系统）
  - 明清增补本（与四库本差异较大）
  - 民国及现代点校本（commentary 层）
- **在线索引**：
  - CTP：https://ctext.org/wiki.pl?if=gb&remap=gb&res=727782
- **卷次结构**：全书 5 卷
  - 卷一：基础理论（造化源流 / 天干地支 / 阴阳五行 / 十二长生 / 月令 / 合冲刑害）
  - 卷二：论命总纲（继善篇 / 看命入式 / 喜忌篇 / 十神格局）
  - 卷三：运限与六亲（大运 / 流年 / 小运 / 纳音 / 六亲 / 女命 / 小儿）
  - 卷四：神煞（各类神煞取法与断语）
  - 卷五：杂论与赋文（看命总节 / 造化元钥 / 各种经验赋文）
- **复核状态**：`partial`。CTP 文本应继续与四库本影印对校。

## Position In Lineage

- **在八字子平体系中的位置**：子平法骨架与术语枢纽，是"早期禄命 → 子平 → 后世四派"的关键过渡。
- **上游**：
  - 《李虚中命书》《珞琭子三命消息赋注》：禄命源头，本书承袭部分术语，但把"以年为主"改为"以日为主"。
  - 《五行精纪》：宋代禄命汇编，与本书有术语继承关系。
- **下游**：
  - 《三命通会》：直接承袭本书骨架，大量扩充。
  - 《子平真诠》：从本书格局雏形提炼出月令格局成败救应。
  - 《滴天髓阐微》：从本书旺衰生克思路提炼气势/通关/病药。
  - 《穷通宝鉴》：从本书月令取用思路提炼调候主线。

简言之：**子平法以本书为"骨架源"；后世四派精修版都需先回到本书看雏形。**

## Loading Guide

主 skill 加载约定（遵循 matrices/validation-checklist.md §L.11）：

1. **默认只加载本文件** `index.md`：拿 frontmatter / 卷次概览 / 分流路由。
2. **需要查具体章节** → 加载 `chapter-map.md`。
3. **需要查术语** → 加载 `terms.md`。
4. **需要查判断规则** → 加载 `rules.md`。
5. **需要查可操作流程** → 加载 `procedures.md`。
6. **需要查短引 + 出处** → 加载 `quote-index.md`。
7. **需要校验覆盖率 / 版本状态** → 加载 `validation.md`。

不允许主 skill 一次性加载全部 7 个文件；按需加载。

## File Map

| 文件 | 职责 | 何时加载 |
|---|---|---|
| [index.md](./index.md) | 入口索引 + frontmatter + 卷次概览 + 路由 | 默认加载 |
| [chapter-map.md](./chapter-map.md) | 全书 5 卷章节地图 + digest_status | 需要查具体章节 |
| [terms.md](./terms.md) | 全书术语抽取（按分组） | 需要查术语定义 |
| [rules.md](./rules.md) | 全书判断规则（按卷抽取） | 需要查判断规则 |
| [procedures.md](./procedures.md) | 全书可操作流程 | 需要查操作流程 |
| [quote-index.md](./quote-index.md) | 短引索引 + 出处 | 需要引用原文 |
| [validation.md](./validation.md) | 全书覆盖率 + 版本核验 + 待办 | 需要校验覆盖率 |

## Routing

主 skill 收到八字相关问题后：

1. 本 pack 是八字体系的"子平法骨架源"（详见 matrices/routing-matrix.md §2.1）。
2. 按问题类型分流：
   - 综合查找 / 百科 → `bazi/sanming-tonghui`（ready）
   - 月令格局成败 → `bazi/ziping-zhenquan`
   - 旺衰气势通关 → `bazi/ditiansui-chanwei`
   - 调候 → `bazi/qiongtong-baojian`
   - 子平法源流 / 术语溯源 → 本 pack
3. 事实层未确定的盘必须先调用 `tool.bazi.paipan`。

## 冲突裁判

详见 frontmatter `conflict_policy` 与 matrices/conflict-policy.md §1.2。

---
title: 子平真诠
slug: ziping-zhenquan
system: bazi
school:
  - 子平法
  - 格局派
source_layer: primary_with_editorial_notes
source_status: ready
source_links:
  - https://www.donglishuzhai.net/books/63.html
  - https://ctext.org/wiki.pl?if=gb&res=374904
  - https://upload.wikimedia.org/wikipedia/commons/f/fe/NLC416-11jh010455-35296_%E5%AD%90%E5%B9%B3%E7%9C%9F%E8%A9%AE.pdf
version_notes: |
  本 pack 以东里书斋繁体二校本为 normalized 全文底本，含 47 个沈氏原典核心章节、命例附录和序跋。
  规则层只抽取一至四十七核心章节；电子版前言、凡例、读后附记、序跋、命例附录只作为版本说明和旁证。
  仍需与 Wikimedia/NLC 影印 PDF 及 CTP 锚点逐段校勘。徐乐吾评注不进入本 pack 原典规则层。
depends_on:
  - yuanhai-ziping
  - sanming-tonghui
  - ditiansui-chanwei
informs:
  - bazi-master-skill
  - ziping-geju-routing
core_use_cases:
  - 月令用神与格局成败救应
  - 四吉神/四凶神顺逆用法
  - 正官、财、印、食神、七煞、伤官、阳刃、建禄月劫取运框架
  - 子平法中“格局优先于神煞”的规则边界
not_for:
  - 不排盘、不手算大运流年
  - 不把富贵贫贱等古代评价语用于现实决定论
  - 不把徐乐吾评注或现代强弱派解释冒充沈氏原典
extraction_targets:
  - concepts
  - terms
  - rules
  - procedures
  - quote_index
---

# 子平真诠 Reference Pack（index）

本目录是《子平真诠》的 D2 reference pack。完整原文在 `references/fulltext/bazi/ziping-zhenquan/fulltext.md`。
本 pack 的核心约束是：**只把沈氏原典 47 章进入规则层**，序跋、整理说明、命例附录只提供版本背景和案例旁证。

## File Map

| 文件 | 职责 |
|---|---|
| index.md | 入口索引 + frontmatter |
| chapter-map.md | 47 章核心章节地图 |
| terms.md | 术语抽取 |
| rules.md | 判断规则 |
| procedures.md | 流程与工具依赖 |
| quote-index.md | 47 章短引索引 |
| validation.md | 覆盖率与版本核验 |

## 使用边界

《子平真诠》适合回答“格局、用神、相神、成败救应、十神取运”的文献问题。涉及命盘计算时，必须由排盘工具提供四柱、月令、藏干、透干、合冲刑会、大运流年等结构化输入；LLM 只做规则路由和解释，不手算。

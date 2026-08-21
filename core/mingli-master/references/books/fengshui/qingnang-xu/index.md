---
title: 青囊序
slug: qingnang-xu
system: fengshui
school:
  - 理气派
  - 玄空
  - 三元
  - 雌雄水法
source_layer: primary
source_status: partial
source_links:
  - https://zh.wikisource.org/zh-hans/青囊序
version_notes: |
  题唐·曾文迪（曾求己）作，紧承《青囊经》而立。本 pack 取维基文库通行本为底本，
  并以蒋大鸿《地理辨正》所收本与各家校本为对校系统。全书为通篇韵文，无显式
  分章；本 pack 按文意分为 8 个 stanza 作为 chapter-map 条目。
  作者归属、与《青囊奥语》《天玉经》《都天宝照经》合刊关系待考；source_status
  维持 partial，影印逐段复核未完成。
depends_on:
  - qingnang-jing
informs:
  - hanlong-jing
  - yilong-jing
core_use_cases:
  - 理气派"看雌雄""认金龙""察血脉"水法源头
  - 二十四山阴阳顺逆与四十八局体系
  - 山龙水龙各管一路（"山管山兮水管水"）
  - 净阴净阳法、生旺退神、进退神水法
not_for:
  - 排盘/起卦/择日事实计算（不替代工具）
  - 风水坐向实际测量（不替代 tool.fengshui.luopan）
  - 罗盘度数手算（严格禁止 LLM 手算坐向）
  - 把"十墳埋下九墳貧"等命题作现代决定论陈述
extraction_targets:
  - concepts
  - terms
  - rules
  - procedures
  - quote_index
---

# 青囊序 Reference Pack（index）

> 本文件是《青囊序》参考包入口索引。详细内容分布在
> `chapter-map.md / terms.md / rules.md / procedures.md / quote-index.md / validation.md`。

## 简介

《青囊序》传为唐代曾文迪（杨筠松弟子）作，紧承《青囊经》而专论水法。
全书韵文一篇，提出"看雌雄""先看金龙动不动""次察血脉认来龙""山管山兮水管水"
"二十四山分顺逆共成四十八局"等水法核心命题，并展开生旺退神、净阴净阳、
进退神水法、公位水法等具体细则。蒋大鸿《地理辨正》以此篇为玄空理气主要解读对象。

## File Map

| 文件 | 职责 |
|---|---|
| index.md | 入口索引 + frontmatter |
| chapter-map.md | 8 个 stanza 文意分段 |
| terms.md | 术语抽取 |
| rules.md | 判断规则 |
| procedures.md | 流程（仅声明工具依赖） |
| quote-index.md | 短引索引 |
| validation.md | 覆盖率与版本核验 |

## 现代使用边界

理气水法术语（雌雄、金龙、血脉、二十四山、四十八局）属传统象数体系，
仅作文化与古文献研究参考。"請騐一家舊日墳，十墳埋下九墳貧"等评价语
为古代水法陈述，不构成现代任何决定论建议。
所有规则均标注 `verified: false`。

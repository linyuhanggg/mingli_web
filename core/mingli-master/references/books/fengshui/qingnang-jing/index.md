---
title: 青囊经
slug: qingnang-jing
system: fengshui
school:
  - 理气派
  - 玄空
  - 三元
  - 形气一体
source_layer: primary
source_status: partial
source_links:
  - https://zh.wikisource.org/zh-hans/青囊經
version_notes: |
  传为黄石公授赤松子，今传本经唐宋以后整理。本 pack 取维基文库通行本为底本，
  并以蒋大鸿《地理辨正》所收注本为对校系统。全书分上中下三卷：化始（河图洛书先后天卦理）、
  化机（天文星宿与地形相感）、化成（理气入用准绳）。
  作者源流不可考；蒋大鸿注本为现行理气派最重要解读系统之一。
  四库本与各家注本逐段复核未完成，source_status 维持 partial。
depends_on:
  - zangshu
informs:
  - qingnang-xu
core_use_cases:
  - 理气派河图洛书与先后天八卦体系源头
  - "形止气蓄，万物化生"理气化机命题
  - 三卷化始/化机/化成框架（理一气一形一用）
  - 玄空、三元理气派的源头经文
not_for:
  - 排盘/起卦/择日事实计算（不替代工具）
  - 风水坐向实际测量（不替代 tool.fengshui.luopan）
  - 罗盘度数手算（严格禁止 LLM 手算坐向）
  - 把"陰陽相見禍咎踵門"等命题作现代决定论陈述
extraction_targets:
  - concepts
  - terms
  - rules
  - procedures
  - quote_index
---

# 青囊经 Reference Pack（index）

> 本文件是《青囊经》参考包入口索引。详细内容分布在
> `chapter-map.md / terms.md / rules.md / procedures.md / quote-index.md / validation.md`。

## 简介

《青囊经》是理气派风水奠基性经文，传为黄石公授赤松子，源流难考。
全书分上中下三卷，分别题为"化始""化机""化成"：上卷立河图洛书与先后天八卦
之理（化始）；中卷以天文星宿与山川地形相感而立人纪（化机）；下卷以"乘风则散、
界水则止"为入用准绳（化成）。蒋大鸿《地理辨正》所收注本为最重要的解读系统，
本 pack 同时收录正文与蒋注作为对照。

## File Map

| 文件 | 职责 |
|---|---|
| index.md | 入口索引 + frontmatter |
| chapter-map.md | 三卷六节地图 |
| terms.md | 术语抽取 |
| rules.md | 判断规则 |
| procedures.md | 流程（仅声明工具依赖） |
| quote-index.md | 短引索引 |
| validation.md | 覆盖率与版本核验 |

## 现代使用边界

理气派术语（卦、星、运、气）属传统象数体系，仅作文化与古文献研究参考。
"陰陽相見福祿永貞，陰陽相乘禍咎踵門"等命题为古代象数语言，不构成
现代任何吉凶预测或行动建议。
所有规则均标注 `verified: false`。

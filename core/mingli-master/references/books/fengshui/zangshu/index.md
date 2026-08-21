---
title: 葬书
slug: zangshu
system: fengshui
school:
  - 形势派
  - 峦头
  - 阴宅葬法
  - 形气一体
source_layer: primary
source_status: partial
source_links:
  - https://zh.wikisource.org/zh-hans/葬書
version_notes: |
  托名晋·郭璞，今传本主要由宋元以后整理。本 pack 取《地理眞詮》一集所收《葬书》本（吴澄删定本，分内篇、外篇、雜篇共 8+2 篇约 1246 字）为底本，
  并以《钦定四库全书》子部·术数类·相宅相墓本为对校系统。
  作者归属、篇章删定、版本流派均存在争议；蔡季通去十二存其八，吴澄草庐先生再删定为今本。
  四库本影印逐段复核尚未完成，source_status 维持 partial。
depends_on: []
informs:
  - qingnang-jing
  - qingnang-xu
  - hanlong-jing
  - yilong-jing
core_use_cases:
  - 形势派阴宅葬法源流与"乘生气"核心命题
  - 形—势—气—理一体框架（藏风得水、外气内气、形止气蓄）
  - 山形吉凶判断（童、断、石、过、独五不可葬）
  - 四勢八方葬法基本原则（青龙白虎朱雀玄武）
not_for:
  - 排盘/起卦/择日事实计算（不替代工具）
  - 风水坐向实际测量（不替代 tool.fengshui.luopan）
  - 罗盘度数手算（严格禁止 LLM 手算坐向）
  - 把"鬼福及人""銅山西崩，靈鍾東應"等命题作现代科学陈述
extraction_targets:
  - concepts
  - terms
  - rules
  - procedures
  - quote_index
---

# 葬书 Reference Pack（index）

> 本文件是《葬书》参考包入口索引。详细内容分布在
> `chapter-map.md / terms.md / rules.md / procedures.md / quote-index.md / validation.md`。

## 简介

《葬书》题晋·郭璞（景纯）撰，是形势派风水开山经典，约 1246 字（吴澄删定本）。
全书以"葬者乘生气也"开篇，确立"气—形—势—理"一体框架，提出"得水为上，
藏风次之""外气横形，内气止生""形止气蓄，化生万物"等命题，奠定阴宅葬法
的形势派传统。后世杨筠松《撼龙经》《疑龙经》及理气派《青囊经》《青囊序》
均承此体系而别有发挥。

## File Map

| 文件 | 职责 |
|---|---|
| index.md | 入口索引 + frontmatter |
| chapter-map.md | 全书 11 节地图 |
| terms.md | 术语抽取 |
| rules.md | 判断规则 |
| procedures.md | 可操作流程（仅声明工具依赖） |
| quote-index.md | 短引索引 |
| validation.md | 覆盖率与版本核验 |

## 现代使用边界

涉及阴宅、葬地、死亡、坟墓的内容仅作**文化与古文献研究参考**，
不构成任何当代选择葬地、迁葬、风水改运的建议。
所有规则均标注 `verified: false`，待四库影印逐段复核后逐条提升。

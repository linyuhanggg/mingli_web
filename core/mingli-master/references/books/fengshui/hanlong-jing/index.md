---
title: 撼龙经
slug: hanlong-jing
system: fengshui
school:
  - 形势派
  - 峦头
  - 九星龙脉
  - 杨公风水
source_layer: primary
source_status: partial
source_links:
  - https://zh.wikisource.org/zh-hans/撼龍經_(四庫全書本)
version_notes: |
  题唐·杨筠松（救贫先生）撰，《钦定四库全书》子部·术数类·相宅相墓收录，
  与《疑龙经》《葬法倒杖》合刊。本 pack 取四库本（维基文库整理）为底本，
  专论山陇落脉形势，分贪狼、巨门、禄存、文曲、廉贞、武曲、破军、左辅、右弼
  九星各为之说。
  作者归属与版本流传仍有争议；李国本旧注庸陋已删；source_status 维持 partial
  待四库影印逐段复核。
depends_on:
  - zangshu
informs:
  - yilong-jing
core_use_cases:
  - 形势派九星龙脉体系（贪巨禄文廉武破辅弼）
  - 峦头形势核心范式（高山落脉、平洋寻龙、星峰辨认）
  - 九星形态学与穴形对应
  - 廉贞为祖、贪狼出穴等龙脉变换原理
not_for:
  - 排盘/起卦/择日事实计算（不替代工具）
  - 风水坐向实际测量（不替代 tool.fengshui.luopan）
  - 罗盘度数手算（严格禁止 LLM 手算坐向）
  - 把"破军作穴""廉贞凶灾"等命题作现代决定论陈述
extraction_targets:
  - concepts
  - terms
  - rules
  - procedures
  - quote_index
---

# 撼龙经 Reference Pack（index）

> 本文件是《撼龙经》参考包入口索引。详细内容分布在
> `chapter-map.md / terms.md / rules.md / procedures.md / quote-index.md / validation.md`。

## 简介

《撼龙经》题唐·杨筠松撰，是形势派九星龙脉的奠基经典。全书以须弥山为天地骨开篇，
立北辰为天极，分论贪狼、巨门、禄存、文曲、廉贞、武曲、破军、左辅、右弼九星，
每星各有形态、变换、剥换、关局、出穴方式之论。其核心命题包括"高山须认星峰起，
平地龙行别有名""廉贞是祖宗""贪狼作穴是乳头，巨门作穴窝中求"等。
后世形势派寻龙术多以本经为骨架，与《疑龙经》《葬法倒杖》合称"杨公三经"。

## File Map

| 文件 | 职责 |
|---|---|
| index.md | 入口索引 + frontmatter |
| chapter-map.md | 13 章地图（提要 + 总论 + 九星 + 出穴 + 七星歌） |
| terms.md | 九星与术语抽取 |
| rules.md | 龙脉判断规则 |
| procedures.md | 流程（仅声明工具依赖） |
| quote-index.md | 短引索引 |
| validation.md | 覆盖率与版本核验 |

## 现代使用边界

九星龙脉仅作传统形势派文化与古文献研究参考。
"破军作穴""男人破家因酒色"等评价语为古文措辞，不构成现代决定论陈述。
所有规则均标注 `verified: false`。

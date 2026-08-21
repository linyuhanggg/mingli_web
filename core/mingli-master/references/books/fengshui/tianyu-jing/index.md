---
title: 天玉经
slug: tianyu-jing
system: fengshui
school:
  - 理气派
  - 玄空
  - 三合
  - 三元
source_layer: primary_with_commentary
source_status: ready
source_links:
  - https://zh.wikisource.org/wiki/天玉經內傳
  - https://zh.wikisource.org/wiki/天玉經外編
  - https://archive.org/details/06054157.cn
  - https://ctext.org/wiki.pl?if=gb&res=604706
version_notes: |
  本 pack 取维基文库《天玉經內傳》与《天玉經外編》raw 导出为 canonical fulltext；文本含经文与吴公等注释性文字，
  使用时必须区分“经文口诀层”“外编层”和“注解阐释层”。四库/CTP/Internet Archive 影印仅作对校锚点。
  题唐杨筠松撰之归属有争议；本 pack 仅按传统题名入库。
depends_on:
  - qingnang-jing
  - qingnang-xu
  - qingnang-aoyu
informs:
  - dili-bianzheng
  - dutian-baozhao-jing
  - shenshi-xuankong-xue
core_use_cases:
  - 玄空理气的三卦、父母卦、东西南北卦框架
  - 天卦/地卦/玄空卦/挨星的术语溯源
  - 二十四山、零正神、双山三合、四龙折水的文献锚点
  - 与《青囊序》《青囊奥语》《地理辨正》的源流互证
not_for:
  - 实地风水勘测或住宅建议
  - 罗盘度数、坐向、水口、挨星飞排的 LLM 手算
  - 把富贵贫贱等古代评价语作现代决定论陈述
extraction_targets:
  - concepts
  - terms
  - rules
  - procedures
  - quote_index
---

# 天玉经 Reference Pack（index）

> 本文件是《天玉经》参考包入口索引。详细内容分布在
> `chapter-map.md / terms.md / rules.md / procedures.md / quote-index.md / validation.md`。

## 简介

《天玉经》为风水理气派核心经典之一，本 pack 收内传上、中、下三篇及外编，
围绕江东/江西/南北三卦、天卦/地卦、父母卦、玄空、挨星、零正神、
双山三合、四龙折水、九星形势等命题展开。维基文库底本同时保留注解性文字，
因此 downstream skill 应优先把短句口诀作为“原典触发词”，再把注解作为解释层。

## File Map

| 文件 | 职责 |
|---|---|
| index.md | 入口索引 + frontmatter |
| chapter-map.md | 内传上中下三篇章节地图 |
| terms.md | 术语抽取 |
| rules.md | 判断规则 |
| procedures.md | 流程与工具依赖 |
| quote-index.md | 短引索引 |
| validation.md | 覆盖率与版本核验 |

## 使用边界

本 pack 只服务于古籍 corpus 蒸馏、术语检索、流派源流比对。涉及坐向、水口、
挨星、零正神等操作时，必须由外部罗盘/历法/地理工具提供结构化输入；
LLM 不直接手算，也不把古代“富贵”“败绝”等断语应用到现实个案。

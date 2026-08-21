---
title: 都天宝照经
slug: dutian-baozhao-jing
system: fengshui
school:
  - 理气派
  - 玄空
  - 三元
source_layer: primary_with_commentary_risk
source_status: ready
source_links:
  - https://www.ncc.com.tw/fate/paleo/eg/eg_02.htm
  - https://ctext.org
version_notes: |
  本 pack 以 NCC「陽宅堪輿古文 - 都天寶照經」单页 HTML 为临时全文底本，页面题署含
  「都天寶照經 地理辨正疏 - 蔣大鴻」。原文分上篇、中篇、下篇。网页授权与底本系统未完全核实，
  后续必须与《地理辨正》刊本/影印本校勘。题杨筠松口授、黄妙应笔录之归属按传统题名处理，不作史实断定。
depends_on:
  - qingnang-jing
  - qingnang-xu
  - qingnang-aoyu
  - tianyu-jing
informs:
  - dili-bianzheng
  - shenshi-xuankong-xue
core_use_cases:
  - 玄空理气源流中的山水、龙穴、坐向与水法术语索引
  - 都天大卦、天元/地元/人元、五吉星、城门、零正神相关文献锚点
  - 与《青囊序》《天玉经》《地理辨正》的依赖关系与冲突标注
  - 形势与理气交界处的“龙、水、穴、向”流程抽象
not_for:
  - 实地阴宅/阳宅吉凶判断
  - 罗盘度数、坐向、来龙去水、挨星或城门诀的 LLM 手算
  - 把古代富贵贫贱、伤亡、官禄等断语用于现代个案
extraction_targets:
  - concepts
  - terms
  - rules
  - procedures
  - quote_index
---

# 都天宝照经 Reference Pack（index）

本 pack 是《都天宝照经》的 D2 参考包入口。完整原文在
`references/fulltext/fengshui/dutian-baozhao-jing/fulltext.md`，本目录只放蒸馏后的术语、规则、流程、短引和校验说明。

## File Map

| 文件 | 职责 |
|---|---|
| index.md | 入口索引 + frontmatter |
| chapter-map.md | 上中下三篇地图 |
| terms.md | 术语抽取 |
| rules.md | 判断规则 |
| procedures.md | 流程与工具依赖 |
| quote-index.md | 短引索引 |
| validation.md | 覆盖率与版本核验 |

## 使用边界

本 pack 只服务于古籍 corpus 蒸馏、术语检索、流派源流比对。凡涉及罗盘、坐向、水口、来龙、穴场、城门诀、零正神、五吉星等操作，都必须交给外部工具或人工校勘；LLM 不直接手算，不输出现实个案的确定性吉凶。

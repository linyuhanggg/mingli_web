---
title: 蘭臺妙選
slug: lantai-miaoxuan
system: luming-nayin
school:
  - 早期禄命
  - 纳音取象
  - 三元四柱格局
  - 明代禄命赋文
source_layer: primary
source_status: normalized_ready
source_links:
  - https://ctext.org/wiki.pl?chapter=747132&if=gb&remap=gb
  - https://www.donglishuzhai.net/chapter/3764.html
  - https://www.donglishuzhai.net/chapter/3765.html
  - https://www.donglishuzhai.net/chapter/3766.html
  - https://zh.wikisource.org/zh-hant/欽定古今圖書集成/博物彙編/藝術典/第591卷
  - https://zh.wikisource.org/zh-hant/欽定古今圖書集成/博物彙編/藝術典/第592卷
version_notes: |
  《蘭臺妙選》旧题明西窗老人辑，通行文本见《古今图书集成·博物汇编·艺术典》星命部。
  本 pack 以 CTP《兰台妙选》页面作权威文本锚点，以东里书斋三篇静态正文抽取为 normalized 底本；维基文库第591、592卷作《古今图书集成》卷次锚点。
  第591卷页面目录与 proofread 正文混排，目录中有“蘭臺妙選一〈上篇〉”，实际采集时不得把同卷前置《磨鑴賦》误并入本书。
depends_on:
  - li-xuzhong-mingshu
  - luoluzi-sanming
  - yuzhao-shenying
informs:
  - wuxing-jingji
  - sanming-tonghui
core_use_cases:
  - 纳音取象格局的系统样本
  - 三元（天元/地元/人元）与四柱、胎元、禄马贵人并看的早期禄命法
  - 与《李虚中命书》《玉照神应真经》《五行精纪》对读，辨析子平法之前的格局语言
  - 为主 skill 提供“纳音象格/禄命古法”旁证，而非现代八字主断
not_for:
  - 现代八字排盘或十神强弱计算
  - 医疗、寿夭、刑伤、贫贱等真人硬断
  - 将取象格名直接套用为确定结论
  - 替代《子平真诠》《滴天髓》等子平体系
extraction_targets:
  - chapter_map
  - terms
  - rules
  - procedures
  - quote_index
conflict_policy: |
  与子平法冲突时，以“体系不同”处理：本书保存明代禄命纳音取象法，适合作历史谱系与象格旁证；现代八字主断优先使用子平体系。
  与《五行精纪》冲突时，《五行精纪》作为宋代汇编可优先说明源流，本书作为明代整理型赋文保留异文与格名。
  涉及凶煞、疾病、夭折、贫愚、刑伤等断语，必须改写为“文本中如何归类风险象”，不得输出为对真人的确定判断。
validation_notes: |
  D2 覆盖对象为三篇：上篇、中篇、下篇。quote-index 短引全部应能在 normalized fulltext exact-ish 命中。
  版本风险：东里底本为现代整理 HTML；CTP/Wikisource/影印本逐字校对仍待补。
modern_notes: |
  现代使用时只作“禄命纳音取象参考层”，不作为一线命理判断核心。
---

# 蘭臺妙選 Reference Pack

## Source

- **作者/题署**：旧题明西窗老人辑。
- **体系位置**：早期禄命/纳音取象格局，处于《李虚中命书》《珞琭子三命消息赋》《玉照神应真经》之后、《五行精纪》《三命通会》可引用吸收之前或旁支。
- **本地全文**：`references/fulltext/luming-nayin/lantai-miaoxuan/fulltext.md`。
- **采集说明**：CTP 为权威锚点；东里三篇为本次 normalized 底本；维基文库《古今图书集成》第591、592卷为卷次锚点。

## Loading Guide

1. 默认加载本文件。
2. 需要全书覆盖状态看 `chapter-map.md`。
3. 需要术语看 `terms.md`。
4. 需要规则看 `rules.md`。
5. 需要流程看 `procedures.md`。
6. 需要短引证据看 `quote-index.md`。
7. 需要验收/风险看 `validation.md`。

---
slug: dutian-baozhao-jing
file: rules
---

# 都天宝照经 规则集

> 以下规则是古籍语义抽取，不直接用于现实风水判断。凡涉及坐向、水口、三元、城门、星辰分组，均依赖工具或人工校勘。

## DTR-01: 龙穴先以龙真、水口、砂曲定大纲

- **source_chapter**: shang-longshui
- **rule**: 上篇先以龙穴、水口、砂水、平洋来龙作为总纲；砂曲星辰正、水口锁门、穴见阳神等共同构成兴隆语境。
- **source_anchor**: fulltext.md L12-L34
- **caveats**: “发福”“豪雄”“官僚”等为古代断语，不作现代因果陈述。
- **verified**: false

## DTR-02: 平洋军州不执后龙

- **source_chapter**: shang-longshui
- **rule**: 对军州、平洋地形，文中强调“天下军州总住空”，不可机械要求后头龙，而要向水神朝处取。
- **source_anchor**: fulltext.md L34-L36
- **caveats**: 此为文献规则，实地判断必须有地形与水系数据。
- **verified**: false

## DTR-03: 分水脉脊处以罗经照出路

- **source_chapter**: shang-longshui
- **rule**: 大山五星聚脉难分时，须从分水脉脊处辨脉，并以罗经确定出路。
- **source_anchor**: fulltext.md L40-L42
- **caveats**: 罗经读数必须由 `tool.fengshui.luopan` 或人工测量给出，LLM 不手算。
- **verified**: false

## DTR-04: 三元分组不可阴阳错

- **source_chapter**: shang-longshui
- **rule**: 子癸午丁、卯乙酉辛，辰戌丑未、乾坤艮巽，甲庚壬丙、寅申巳亥等分组用于辨天元、地元、人元；文本反复警告阳差阴错。
- **source_anchor**: fulltext.md L44-L52
- **caveats**: 各派三元分组解释不完全一致，master skill 应以所选流派裁判。
- **verified**: false

## DTR-05: 立宅安坟要合龙，不以奇峰为先

- **source_chapter**: shang-longshui
- **rule**: 文中提出立宅安坟要合龙，不须拟对好奇峰，并以主客东西关系比喻山水宾主。
- **source_anchor**: fulltext.md L54-L56
- **caveats**: 仅作文献原则，不作现实选址建议。
- **verified**: false

## DTR-06: 空龙与平洋墓宅同法

- **source_chapter**: zhong-konglong
- **rule**: 中篇把军州空龙与平洋墓宅相通，认为龙若空时气不空，穴得水则不畏风。
- **source_anchor**: fulltext.md L60-L68
- **caveats**: “空龙”需结合地形、水界、城市格局判断，不能仅凭文字套用。
- **verified**: false

## DTR-07: 不可机械依八卦阴阳

- **source_chapter**: zhong-konglong
- **rule**: 文中警示“莫依八卦阴阳取”，并批评把八卦作先宗、妄将卦例更阴阳。
- **source_anchor**: fulltext.md L70-L82
- **caveats**: 这是《地理辨正》系理气批判语境，不可用来否定所有八卦法。
- **verified**: false

## DTR-08: 城门诀优先作为水法良法索引

- **source_chapter**: zhong-konglong
- **rule**: 文中称五星一诀非真术，城门一诀最为良；识得五星城门诀，则立宅安坟大吉昌。
- **source_anchor**: fulltext.md L110-L112
- **caveats**: 城门操作必须工具化，不能由 LLM 推断方位。
- **verified**: false

## DTR-09: 阴阳需山情水意配合

- **source_chapter**: zhong-konglong
- **rule**: 都天大卦总阴阳，但须能知山情与水意，配合方可论阴阳。
- **source_anchor**: fulltext.md L122-L124
- **caveats**: 只保留为“山水合参”原则，不输出现实吉凶。
- **verified**: false

## DTR-10: 下篇以中阳明堂和乙字水为吉形索引

- **source_chapter**: xia-shuifa
- **rule**: 下篇强调安坟最要看中阳，明堂宽抱、乙字水缠、九曲来朝等作为水形吉象。
- **source_anchor**: fulltext.md L136-L144
- **caveats**: “吉形”仅作传统术语解释，实地需地图/测绘/人工勘验。
- **verified**: false

## DTR-11: 直水、反水、射腰等凶水只作古文风险词

- **source_chapter**: xia-shuifa
- **rule**: 下篇列举直水、插胁水、四杀、八杀、拖刀杀、反水、射腰等凶水名目。
- **source_anchor**: fulltext.md L146-L160
- **caveats**: 这些包含伤亡绝嗣等强断语，skill 输出时必须转为“古文风险词”，禁止现代决定论。
- **verified**: false

## DTR-12: 玄武摆头不可执一端

- **source_chapter**: xia-shuifa
- **rule**: 文中明确玄武摆头有斜、侧、正出多种，不可执一端，须凭直节对堂安。
- **source_anchor**: fulltext.md L166-L168
- **caveats**: 属形势判断，需地形数据或人工照片，不由 LLM 想象。
- **verified**: false

## DTR-13: 五吉与凶恶龙须分

- **source_chapter**: xia-shuifa
- **rule**: 贪武辅弼巨门为可寻之吉龙，破禄廉文为凶恶龙，二者不可混同。
- **source_anchor**: fulltext.md L172-L174
- **caveats**: 九星名目需与《撼龙经》《疑龙经》《天玉经外编》互证。
- **verified**: false

## DTR-14: 寻龙过气以三节和孟仲季接脉核查

- **source_chapter**: xia-shuifa
- **rule**: 寻龙过气要分父母宗枝，孟山连孟山、仲山接仲山；三节不乱则可称真龙。
- **source_anchor**: fulltext.md L184-L206
- **caveats**: 这是龙脉结构规则，不可在无地形资料时断定。
- **verified**: false

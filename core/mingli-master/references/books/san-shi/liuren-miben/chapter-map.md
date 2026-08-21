---
slug: liuren-miben
file: chapter-map
normalized_sha256: 44ea31ef43f874ffc9da03c6ed6c01eee62081db6c2faf11593ec9bbe47847e0
source_lines: 5354
---

# 《大六壬秘本》结构地图

> `structural_status=indexed` 只表示该段已进入完整结构索引；`rule_extraction=selective` 表示只抽取了有明确出处、前置字段和停止条件的规则。两者都不表示逐句规则化或逐页影印校勘。

## Coverage Summary

| metric | value |
|---|---:|
| normalized lines | 5354 |
| normalized bytes | 295312 |
| catalog/title unit | 1 |
| juan present | 17 / 17 |
| collation-record unit | 1 |
| missing juan | 0 |
| replacement characters in body | 0 |
| missing-character placeholders in body | 0 |
| scan-verified CTP junctions | 3 |
| fully page-collated juan | 0 |

## Unit Map

| unit | title / contents | normalized lines | source layer | structural status | rule extraction | evidence |
|---|---|---:|---|---|---|---|
| LM-00A | 现代归一化题头与来源说明 | L1-L3 | `normalization_scaffold` | indexed | not_applicable | LM-Q001 |
| LM-00B | “序文与目录”单元：实含书题、目录、篇目清单；没有可独立辨认的叙事性序文 | L5-L81 | `catalog_and_colophons` | indexed | structure_only | LM-Q002 |
| LM-01 | 卷一：十二月将照显变化论；十二支数、味、宿度及人物/物类；李道生附记和黄、施朱批 | L82-L256 | `transmitted_body` + named notes | indexed | selective_lookup | LM-Q003-LM-Q006 |
| LM-02 | 卷二：十二天将所主及各加十二辰类象 | L257-L359 | `transmitted_body` | indexed | selective_lookup | LM-Q007 |
| LM-03 | 卷三：六旬仪神、丁神、天中、奇神、闭口、五亡等表 | L360-L376 | `transmitted_body` | indexed | lookup_only | LM-Q008 |
| LM-04 | 卷四：神物论；射覆起例、用传、时过、旺衰、形色、虚实、生死、新旧、表里等 | L377-L599 | `transmitted_body` + mixed variants | indexed | selective | LM-Q009-LM-Q012 |
| LM-05 | 卷五：十二天官加十二辰射覆物类表 | L600-L732 | `transmitted_body` | indexed | lookup_only | LM-Q013 |
| LM-06 | 卷六：乾坎艮震巽离坤兑与将神射覆物类 | L733-L771 | `transmitted_body` | indexed | lookup_only | LM-Q014 |
| LM-07 | 卷七：十干旺相死休囚、物类、二十八宿度位；含“两日轮转”异说 | L772-L970 | `transmitted_body` + attributed saying | indexed | selective_with_conflict | LM-Q015-LM-Q017 |
| LM-08 | 卷八：李九万六壬百章歌；来意、年命、类神、病盗行人等歌诀及注语 | L971-L1369 | `transmitted_body` + mixed commentary | indexed | selective | LM-Q018 |
| LM-09 | 卷九：穿杨百章歌；科举、婚姻、行人、病盗等；施锦堂抄录款 | L1370-L1764 | `transmitted_body` + Jin notes + colophon | indexed | selective | LM-Q019-LM-Q021 |
| LM-10 | 卷十：通天鬼翼赋及注解；主客、旺衰、救神、空亡、关隔、盗失等 | L1765-L2073 | `transmitted_body` + `mixed_body_commentary` | indexed | selective | LM-Q022-LM-Q025 |
| LM-11 | 卷十一：大六壬玉成歌注解；课体、吉凶神将、宅、财、应期、神煞等 | L2074-L2406 | `transmitted_body` + `mixed_body_commentary` | indexed | selective | LM-Q026-LM-Q027 |
| LM-12 | 卷十二：玉田歌；婚姻、疾病、出行、行人、谒人、诉讼、田产、晴雨、科举、干禄、人宅、奴婢 | L2407-L2863 | `transmitted_body` + title note | indexed | category_routing_only | LM-Q028 |
| LM-13 | 卷十三：五行旺相胎孕休囚、壬机秘要法语；课名、日辰、三传、年命异说、空墓合鬼等 | L2864-L3104 | `transmitted_body` + `mixed_body_commentary` | indexed | selective_with_conflict | LM-Q029-LM-Q038 |
| LM-14 | 卷十四：五要权衡三十类、虚实聚散、动静始终迟速、人物器用、盗逃、名殊义同、毕法略说、过将法 | L3105-L3543 | `transmitted_body` + Jin notes + quoted lineages | indexed | core_selective | LM-Q039-LM-Q048 |
| LM-15 | 卷十五：管辂神书；终身、空亡、破刑冲害、丁神、干支、争讼、富贵、课名 | L3544-L4494 | `transmitted_body` + `mixed_body_commentary` + Jin notes | indexed | selective_with_conflict | LM-Q049-LM-Q056 |
| LM-16 | 卷十六：六壬心镜经；晴雨、水势、人宅、修造、黄黑道、求婚、谒人、官举、产育、田蚕、商贾、诉讼等 | L4495-L4981 | `transmitted_body` + `mixed_body_commentary` | indexed | category_routing_only | LM-Q057-LM-Q059 |
| LM-17 | 卷十七：三才应事；五行应日、病、盗、行人、渔猎、怪异、博戏、逃亡、假借；乾隆四十年录竟款 | L4982-L5332 | `transmitted_body` + `mixed_body_commentary` + colophon | indexed | selective | LM-Q060-LM-Q065 |
| LM-99 | 影印补字与版本记录；三处章界补字、卷三标题恢复、卷数冲突和校勘边界 | L5333-L5354 | `normalization_scaffold` + `scan_collated_junction` record | indexed | audit_only | LM-Q066-LM-Q069 |

## Inner Section Index

### 卷一至卷七：类象与射覆

- 卷一：子、丑、寅、卯、辰、巳、午、未、申、酉、戌、亥十二月将类象。
- 卷二：贵人、螣蛇、朱雀、六合、勾陈、青龙、天空、白虎、太常、玄武、太阴、天后。
- 卷三：六旬神煞表；只作为本书表法，不能脱离 adapter 单独推断。
- 卷四：射覆起例、用传、及时/过时、可用、完整、五行、五色、有无、虚实、生死、水陆、形状、可食、五味、新故、集类、表里等。
- 卷五：天官 x 十二辰物类矩阵。
- 卷六：八卦 x 将神射覆类象。
- 卷七：十干旺相死休囚、五行物类、课名用神物类、二十八宿度位。

### 卷八至卷十二：歌赋与专项门类

- 卷八、卷九：百章歌和穿杨歌，条目多为类神加临与事项歌诀。
- 卷十：通天鬼翼赋，适合抽取“全吉仍须察鬼”“救神有距离/力量”“旺衰与主客”等权衡规则。
- 卷十一：玉成歌注解，强调吉将受伤、凶神受制和旺衰修饰。
- 卷十二：十二个显式分门，主要用于问题域路由；本包未把每首占辞逐条规则化。

### 卷十三至卷十四：解释框架

- 卷十三：课名解释存在异文/冲突，不进入确定性起课算法；日辰、三传、空墓、德合、鬼救等只作盘后解释候选。
- 卷十四：本包的主要方法层。三十类先分问题结构，再审天时、地利、喜忌、虚实、聚散、动静、始终、迟速等。
- 卷十四还明示“若断休咎，只用干为主，三传生克正时论，不必用变求奇”，作为防止过度堆叠奇格的内部约束。

### 卷十五至卷十七：专项占法

- 卷十五：终身、空亡、破刑冲害、丁神、干支、争讼、富贵、课名。空亡段和课名段内部注层复杂，规则卡只抽取可设停止条件者。
- 卷十六：按事项检索，不把黄黑道、修造、婚产、诉讼等表法移植到其他术数系统。
- 卷十七：三才取应和专项类神。三才算法若要执行，仍须 adapter 输出天罡、河魁、贵人落处及孟仲季定位。

## Coverage Semantics

- **全结构覆盖**：书题、目录、十七卷和校勘记录均有行界与内容说明。
- **选择性规则化**：只有通过来源定位、前置字段、执行/停止条件和 adapter 门槛的条目进入 `rules.md`。
- **未做的工作**：全文逐句规则卡、全书逐页影印校勘、所有夹注作者判定、所有类象的现代语义归并、独立模型盲测。

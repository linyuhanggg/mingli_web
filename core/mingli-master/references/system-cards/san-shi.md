# 三式 (san-shi)

## Deterministic calendar boundary

Time casts consume `reading_engine.calendar_core` rather than maintaining a
separate sxtwl conversion. The cast binds civil time, historical timezone
offset, coordinates and their source, leap-month state, exact solar-term
boundary, four Ganzhi fields, declared Zi-hour convention, and
`calendar_digest` before any board or lesson rule runs.

## Packs

| pack | title | best for | do not use for | caveat |
|---|---|---|---|---|
| `san-shi/daliuren-daquan` | 大六壬大全 | 九宗门起例、四课三传、十二天将、课经与毕法的主干证据；处理元首/重审、涉害、昴星、别责、八专、伏吟、反吟等算法冲突 | 语言模型手排课盘；把古籍断语当现代事实或统计结论；用未校图表硬编码规则 | `complete_chapter_set`；13,800 行全文、Kanripo 文渊阁十二卷转写与四库影印均已入库。规则卡为选择性蒸馏，影印起讫页与逐页校勘仍未完成；实际起课必须先运行本地 `liuren_fact_adapter.py` v2。 |
| `san-shi/liuren-miben` | 大六壬秘本 | 月将、天将、射覆物类、歌赋、五要权衡、三才应事与专项占法的补充证据 | 覆盖《大全》的取传算法；让卷十三/十五异文改写事实层；脱离课盘孤断神煞 | `complete_text`；十七卷 5,354 行完整全文已入 skill，三处章界据 NCL 影印修复。其余页尚未逐行对校，正文、夹注、朱批仍有混排。 |
| `san-shi/liuren-zhiyin` | 六壬指南 / 六壬指南注解 | 《心印赋》《指掌赋》、分门占法、占验与神煞解释；为《大全》主干提供教学和案例旁证 | 覆盖《大全》起例；把张洪注、本书原文与后人注混为一层；单独承担计算 | `complete_text`；2,798 行完整注本及 248 页原本影印已入库，来源层已拆分。古本页码与逐句作者归属仍待全本影印校勘。 |
| `san-shi/qimen-dunjia-tongzhi` | 奇门遁甲统宗大全 | 奇门遁甲术语、格局、门奇、值符值使、三奇六仪等概念蒸馏; 奇门选择与占法原则的文本证据定位; 与《奇门遁甲秘笈大全》《奇门五总龟》等同类文本互证 | 现实事件事实预测; 医疗、法律、投资、灾祸等重大决策; 未经排盘工具验证的起局计算 | 9 个章节段落全部抽取，quote-index 短引均来自本地 normalized fulltext。 |
| `san-shi/taiyi-shenshu` | 太乙神数 | 太乙神数的起例考源（积年 / 六纪三元 / 太岁 / 太乙所在）; 五将 / 九宫 / 八门 / 太乙诸神（君基 / 臣基 / 民基 / 五福 / 大游 / 小游 / 四神 / 天乙 / 地乙 / 直符 / 天皇 / 帝符 / 天时 / 太尊 / 飞鸟 / 五行 / 八风）的语义体系; 太乙七术 + 16 推占法的纲领 | 实际起局（必须调用 tool.taiyi.bindisk）; 局结果的"事实预测"（仅作语义参考）; 古代国家占法的现代直接应用（仅文化遗产） | - source_status 调整为 normalized_ready：本地四库整理文本完整；具体局数计算属 tool 范畴。 - 卷一~十骨干已纳入；纲领性内容已抽取。 - 涉及兵占 / 国家占法（敌国动静 / 巡狩举贤良 等）须强 caveats："文化遗产，非现代决策"。 |

## Runtime use

This card is capability and source metadata for selecting the transaction
system before `prepare`. During a live reading, use only the bounded evidence
returned by the transaction; do not load packs or run a separate corpus search.

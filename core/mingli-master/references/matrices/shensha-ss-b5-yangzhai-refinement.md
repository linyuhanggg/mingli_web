# SS-B5 阳宅 / 八宅神煞隔离矩阵

generated_at: 2026-07-05  
matrix_version: v0.1  
batch_id: SS-B5  
source_status: distilled_from_ready_yangzhai_packs

本文件是 `shensha-distillation-backlog.md` 的第五批落地产物。它不替代《阳宅十书》《阳宅三要》的单书 reference pack；它只回答：八宅游年九星、天乙巨门、五鬼、六煞、祸害、绝命、天医等名目怎样依赖阳宅事实层，怎样避免串到八字、六壬、择日、紫微或星命里。

## 来源状态

| Pack | 角色 | 当前口径 |
|---|---|---|
| `fengshui/yangzhai-shishu` | 主权威层 | `complete_chapter_set`；用于福元、东四/西四、大游年九星、穿宫分房、开门修造、放水与选择边界 |
| `fengshui/yangzhai-sanyao` | 门主灶支撑层 | normalized ready；用于门、主、灶三要、东西四宅、游年九星与门灶断验，但含翻印/后出整理风险 |
| `fengshui/yangzhai-aizhong-pian` | acquisition-only | 只作为后续书目/OCR 线索，未完成 manifest/OCR 前不进入规则 |

## 必要事实层

八宅/阳宅神煞不是命盘神煞，而是 `yangzhai_bazhai_property_fact_layer` 字段。最少需要：

- 房屋类型、地点、坐向或门向、罗盘度数
- 户型/布局图、主门、主房/主屋、灶、床、水、关键房位
- 宅卦、命卦或福元，东四/西四分组
- 八宅/游年九星映射
- 多进、多层或墙门隔断时的门序/分房/层位事实
- 具体用途：看宅、改门、安灶、安床、放水、修造择日等
- `source_trace` 与警告

若涉及修门、动土、开门或上梁等，还必须另有 `mingli-master.selection.v1` 的确定性择日事实层。若涉及放水，还必须有水路与二十四山事实层。

## 使用总则

1. 八宅天乙/天乙巨门/后世天医是宅局游年九星语义，不等于八字天乙贵人，也不等于六壬天乙天将。
2. 五鬼、六煞、祸害、绝命只在宅向、门主灶、床灶水位、福元命卦和布局事实层内解释，不进入八字命盘神煞清单。
3. 单个星名不能独立断宅。必须合看坐向、宅卦/命卦、门主灶、布局、外形、层位或门序。
4. 《阳宅十书》的开门修门、门光星、太阴太阳过宫等属于择日/图表事实层，不得由语言模型手推。
5. 《阳宅三要》中的疾病、寿夭、寡居、产亡等古代断语只能作为传统文本指向，不能说成现代现实事实或医疗保证。

## 条目精修

| Entry | 阳宅用途 | 一线来源 | 禁止外推 |
|---|---|---|---|
| `shensha-you-nian-jiuxing` 游年九星/天乙巨门 | 八宅游年九星、东四/西四、宅向门主灶吉凶分组 | `yangzhai-shishu`, `yangzhai-sanyao` | 不等于八字神煞；不等于六壬天乙；五鬼六煞绝命不得加入命盘 inventory |
| `shensha-tianyi-medical` 天医/天乙巨门 | 八宅天乙/巨门土星/后世天医俗称 | `yangzhai-shishu`, `yangzhai-sanyao` | 不等于八字天乙贵人、六壬天乙贵人或择日求医天医；不作医疗保证 |

## 回答层融入规则

- 来源问题：可以说明八宅星名、异名和来源，不做现实住宅断事。
- 具体阳宅问题：先过 `tool.fengshui.eight_mansion` 或等价事实层，再读《阳宅十书》为主、《阳宅三要》为辅。
- 缺事实层：只列缺项，不给“此宅五鬼重/绝命重/天医旺”的结论。
- 串台问题：直接说明“八宅名目是宅局事实层，不并入命盘神煞或六壬课式”。

## 后续神煞书籍队列

继续找“神煞相关书籍”时走 `shensha-distillation-backlog.md` 的 SS-B10：先做书目、底本、馆藏、manifest、OCR 状态核验。`fengshui/yangzhai-aizhong-pian` 未完成 manifest/OCR 前只能 acquisition，不进入阳宅规则层。

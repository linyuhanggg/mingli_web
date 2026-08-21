# 神煞专项蒸馏 Backlog

generated_at: 2026-07-05
matrix_version: v0.1
source_status: promoted_from_qoder_followup_and_current_D2_catalog
scope: 神煞相关书籍的后续蒸馏批次、二次精修任务、OCR/acquisition 边界。

本文件把 Qoder 侧 `sources/SHENSHA_FOLLOWUP.md` 的临时计划提升为 `mingli-master` 可调用的 backlog。它不替代 `shensha-source-book-matrix.md` 的书目权重，也不替代 `shensha-entry-source-profile.yaml` 的逐条来源 overlay；它回答“下一批该蒸馏/精修什么、不能碰什么、完成后如何验收”。

## 总原则

1. 神煞不做独立 oracle；只做名称消歧、起例来源、规则旁证、权重降级。
2. 已 D2-ready 的 pack 才能进入规则/索引二次精修；`image_only`、`source_lead_only`、`blocked_unstable_title` 只能进入 acquisition/OCR 任务。
3. 每次新增或精修神煞来源后，必须重跑 `scripts/audit_shensha_traces.py --json`；如果生成 trace，静态 YAML 必须与脚本输出一致。
4. 每条神煞必须保留 `system`、`source_pack_role`、`book_priority`、`fact_layer_requirement` 和 `cannot_override`。
5. 同名神煞严禁串台：八字天乙、六壬天乙、八宅天乙巨门、太乙术语必须分开。

## 批次队列

| Batch | 优先级 | 状态 | 目标 | 输入来源 | 输出 |
|---|---|---|---|---|---|
| SS-B1 | P0 | refined_v0.1 | 八字/禄命高频神煞二次精修 | `sanming-tonghui`, `wuxing-jingji`, `li-xuzhong-mingshu`, `luoluzi-sanming`, `yuzhao-shenying` | 已产出 `shensha-ss-b1-refinement.md` / `.yaml` |
| SS-B2 | P0 | refined_v0.1 | 官方择日神煞起例与裁判 | `xingli-kaoyuan`, `xieji-bianfang-shu` | 已产出 `shensha-ss-b2-selection-refinement.md` / `.yaml` |
| SS-B3 | P1 | refined_v0.1 | 六壬课内神煞、天将、类神边界 | `daliuren-daquan`, `liuren-zhiyin`, `liuren-miben` | 已产出 `shensha-ss-b3-liuren-refinement.md` / `.yaml` |
| SS-B4 | P1 | refined_v0.1 | 紫微/星命同名神煞消歧 | `ziwei-doushu-quanshu`, `taiwei-fu`, `feixing-ziwei-doushu-yuanzhi`, `guotian-jing` | 已产出 `shensha-ss-b4-ziwei-xingming-refinement.md` / `.yaml` |
| SS-B5 | P1 | refined_v0.1 | 阳宅/八宅游年九星与命盘神煞隔离 | `yangzhai-shishu`, `yangzhai-sanyao` | 已产出 `shensha-ss-b5-yangzhai-refinement.md` / `.yaml` |
| SS-B6 | P2 | ocr_pipeline_initialized_v0.3 | 《星平会海/命海全编》OCR 校勘 | `xingming/minghai-quanbian` raw scans | 已产出 `shensha-ss-b6-minghai-ocr-plan.md` / `.yaml`；batch 001 page 013-024、batch 002 page 025、batch 003 page 026 均已有 `in_review` 初校稿，合计 page 013-026 / `in_review=14`；OCR reviewed complete 之前不得输出规则 |
| SS-B7 | P2 | acquisition_only | 《七政全书大成》表格 OCR | `xingming/qizheng-quanshu-dacheng` raw scans | 表格结构化和星命 adapter 评估 |
| SS-B8 | P2 | acquisition_only | 《阳宅爱众篇》获取/校勘 | source lead | source-manifest、scan、OCR/collation |
| SS-B9 | P3 | bibliographic_only | 葬法/墓葬神煞源流 | 《大汉原陵秘葬经》等 source leads | 只做书目考证，不进入一线解释 |
| SS-B10 | P2 | planned_v0.1 | 神煞专门书籍与跨体系书目核验 | ready packs + source leads | 已产出 `shensha-ss-b10-bibliography-plan.md` / `.yaml`；只做书目核验、manifest、OCR/acquisition 计划 |

## SS-B1：八字 / 禄命高频神煞

目标：

- 继续精修 `天乙`、`金舆`、`禄/禄神/禄存/化禄`、`驿马/天马`、`桃花/咸池`、`空亡`、`天罗/地网（canonical id: shensha-luowang）`、`伏吟/反吟`、`白虎`、`丧门/吊客` 等高风险同名条目。
- 以 `bazi/sanming-tonghui` 为八字入口，`luming-nayin/wuxing-jingji` 为早期源流入口；`yuanhai-ziping`、`li-xuzhong-mingshu`、`luoluzi-sanming`、`yuzhao-shenying` 只作源流和互证。
- 不允许把禄命源流直接覆盖现代子平主线。

验收：

- 每个条目在 `shensha-entry-source-profile.yaml` 中有 `book_priority` 和 `source_pack_role`。
- `shensha-quote-trace.yaml` 对相关体系达到 `first_line_quote_index_hit`，否则写明 `needs_second_pass`。
- `bazi-core-decision-stack` 仍保证神煞低于月令、格局、旺衰、调候、十神、大运流年。

## SS-B2：官方择日神煞

目标：

- 把《御定星历考原》的年神/月神/日神/时神起例与《钦定协纪辨方书》的辨方/辨讹/用事宜忌分层。
- 让择日神煞只作为 `mingli-master.selection.v1` 的事实层字段，不作为命盘神煞。
- 明确《玉匣记》《董公择日》只作通书系 comparison，低于官方层。

验收：

- 择日回答仍先读 `selection-fact-layer-profile.yaml`。
- 不出现“只凭黄黑道/建除/某神煞直接选日”的路径。
- 通书冲突写入 comparison / conflict，不覆盖官方裁判。
- v0.1 精修产物：`shensha-ss-b2-selection-refinement.md` / `.yaml`。

## SS-B3：六壬神煞

目标：

- 把《大六壬大全》《六壬指南》《大六壬秘本》中的神煞、天将、类神限定在六壬课式内。
- 防止“天乙”“白虎”“丧门吊客”“青龙朱雀玄武”等词被移植到八字/紫微。

验收：

- 六壬神煞解释必须要求四课三传、天将、月将、日辰、占时。
- 若没有六壬 fact layer，输出缺项而不是断事。
- v0.1 精修产物：`shensha-ss-b3-liuren-refinement.md` / `.yaml`。

## SS-B4：紫微 / 星命同名消歧

目标：

- 紫微侧区分星曜、辅煞、流煞与八字神煞。
- 星命侧只使用 `guotian-jing` 等 ready pack，并要求现代天文排盘；旧度数表不得当现代星历。
- `feixing-ziwei-doushu-yuanzhi` 继续作为民国观测注释层，不升为古典主线。

验收：

- `羊刃/擎羊`、`天马/驿马`、`咸池/桃花`、`禄/禄存/化禄` 不跨系统合并。
- `minghai-quanbian` 仍为 acquisition-only，不能因含“论诸吉神起例”而进入解释。
- v0.1 精修产物：`shensha-ss-b4-ziwei-xingming-refinement.md` / `.yaml`。
- 紫微名目必须有 `tool.ziwei.bindisk` 事实层；星命名目必须有 `tool.xingming.bindisk` + ephemeris 事实层。

## SS-B5：阳宅 / 八宅神煞

目标：

- 把《阳宅十书》《阳宅三要》中的游年九星、天乙巨门、五鬼、六煞、祸害、绝命限定在宅向/命卦/门灶床房位事实层内。
- 明确八宅天乙不是八字天乙，也不是六壬天乙。

验收：

- 阳宅神煞解释必须要求坐向、宅卦/命卦或门主灶事实。
- 不把阳宅九星写入命盘神煞清单。
- v0.1 精修产物：`shensha-ss-b5-yangzhai-refinement.md` / `.yaml`。
- `yangzhai-aizhong-pian` 仍为 acquisition-only，不因八宅神煞线索进入解释。

## Acquisition / OCR 禁区

| Slug | 书名 | 当前状态 | 禁止事项 | 下一步 |
|---|---|---|---|---|
| `xingming/minghai-quanbian` | 《新刻星平總會命海全編 / 星平会海》 | raw acquired, image_only, normalized blocked；SS-B6 OCR pipeline v0.3 initialized | 不得进入解释、规则、quote trace 一线 | 继续 page/leaf accounting + reviewed OCR 到 `ocr_reviewed_complete` |
| `xingming/qizheng-quanshu-dacheng` | 《七政全書大成》 | raw acquired, image_only | 不得使用旧表格推星命事实 | 表格 OCR、结构化、adapter 评估 |
| `xingming/qizheng-siyu-tianjing` | 《七政四余天经》 | blocked_unstable_title | 不得用其他书冒名替代 | 继续书名考证 |
| `san-shi/liuren-zhiyin-vol5-shensha-charts` | 《六壬指南》卷五神煞全图及相关表 | local vision assets exist；pages 225-248 `draft_empty` | 不得把未校勘图表写入六壬规则或 quote trace | 表格/图式 OCR、人工校勘，再合并到 `liuren-zhiyin` 支持层 |
| `selection/xiangji-tongshu` | 《增补象吉通书大全 / 象吉通书》 | source_lead_only；待核馆藏/版本 | 不得用通书条目覆盖官方择日裁判 | 建 manifest、核完整影印、OCR/校勘 |
| `selection/chongzheng-bimiu-tongshu` | 《崇正辟谬通书 / 崇正辟谬》 | source_lead_only；版本复杂 | 不得以二手网页或书名线索生成规则 | 书目核验、版本确认、再决定获取 |
| `selection/xieji-tongyi` | 《协吉通义》 | CTP/OCR source lead；本地未建 manifest | 不得视为《协纪辨方书》同等一线底本 | 核底本、覆盖、OCR 噪声和重复度 |
| `selection/jiugong-bagua-dunfa-mishu` | 《九宫八卦遁法秘书》 | CTP/OCR source lead；本地未建 manifest | 不得把九宫/杂术神煞并入八字或择日一线 | 书目核验、manifest、系统边界复核 |
| `fengshui/yangzhai-aizhong-pian` | 《阳宅爱众篇》 | source_lead_only | 不得进入阳宅规则 | manifest + scan + OCR |
| `fengshui/dahan-yuanling-mizangjing` | 《大汉原陵秘葬经》 | source_lead_only | 不得进入个人命盘/日常择日 | 书目验证 |

## SS-B10：神煞专门书籍与跨体系书目核验

目标：

- 后续若继续找“神煞相关书籍”，先做书目层核验，不把书名线索直接变成可断事规则。
- ready pack 优先做二次精修：`sanming-tonghui`、`wuxing-jingji`、`xieji-bianfang-shu`、`xingli-kaoyuan`、`daliuren-daquan`、`guotian-jing` 等。
- image-only / source-lead-only 只做 manifest、版本、馆藏、OCR 计划。
- ready pack 内部的未校勘图表也按 acquisition/OCR 缺口管理，例如《六壬指南》卷五神煞全图及相关表。
- 新增通书/神煞杂书候选先入核验池：`xiangji-tongshu`、`chongzheng-bimiu-tongshu`、`xieji-tongyi`、`jiugong-bagua-dunfa-mishu`；没有完整底本前不进入规则层。
- v0.1 计划产物：`shensha-ss-b10-bibliography-plan.md` / `.yaml`。

验收：

- 每个候选书籍都有 `source_status`、底本/馆藏说明、是否可整本蒸馏。
- 只有 `complete_text`、`complete_chapter_set`、`ocr_reviewed_complete` 可以进入 rules/procedures/quote-index。
- 未核验书名不得作为一线 reference，也不得参与回答层解释。

## 当前可执行下一步

1. SS-B10 已完成 v0.1 书目核验计划；它不产出解释规则。
2. SS-B6 已初始化 OCR 校勘计划、review asset 脚本、逐页草稿位和草稿校验脚本；下一步仍继续 SS-B6 的 reviewed transcription，不转入规则蒸馏。
3. 《六壬指南》卷五神煞图表已纳入 SS-B10 发现池；它是 SS-B3 的后续图表校勘工单，不改变 SS-B3 refined_v0.1 的解释边界。
4. SS-B6~SS-B9 及新增图表缺口未过 source status gate 前不进入 D2，不写 rules/procedures。

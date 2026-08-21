# 八字核心判读栈 (bazi-core-decision-stack)

generated_at: 2026-07-05
matrix_version: v0.1
source_status: derived_from_D2_ready_bazi_reference_packs
scope: 八字子平在 `mingli-master` 中的加载顺序、书籍依赖、事实层要求、冲突裁判和神煞降权。

本矩阵不新造规则，也不替代单书 reference pack。它把 `bazi/sanming-tonghui`、`bazi/yuanhai-ziping`、`bazi/ziping-zhenquan`、`bazi/ditiansui-chanwei`、`bazi/qiongtong-baojian`、`bazi/shenfeng-tongkao`、`bazi/mingli-yueyan` 的已蒸馏流程串成主 skill 的执行栈，避免回答时只抓一个神煞、一个财务词，或只用某一本书的局部断语。

## 0. 入口原则

1. 先有事实层，再读古籍。出生资料完整时，八字事实层必须含 `calendar_normalization`、四柱、藏干、十神、纳音、节气换月/月令、`seasonal_tiaohou_profile`、寒暖燥湿/调候标记、起运/大运；问年份时还要有流年。若只有用户或图片提供的四柱，只能在 `bazi_fact_adapter.py pillars` 校验并派生静态字段后进入 `natal_static`，不得进入 BZ-06 岁运层。
2. 原始公历时间只是输入，不是传统事实层。必须保留原始 civil time、时区/地点、农历日期含闰月、干支、节气边界和真太阳时策略。
3. 书籍优先级按问题类型切换，不按“哪本更有名”切换：格局看《子平真诠》，旺衰/气势/通关看《滴天髓阐微》，调候看《穷通宝鉴》，综合入口和神煞检索看《三命通会》与《渊海子平》。
4. 神煞永远在八字主线之后。没有月令、格局、旺衰、调候、十神、大运流年，不得用神煞作主结论。
5. 现代流派、经验记忆和单案调参只能进入 hypothesis / calibration 层，不得写成原典规则。

## 1. 判读栈

| Step | 层级 | 必读来源 | 需要的事实字段 | 输出 |
|---|---|---|---|---|
| BZ-00 | 事实层守门 | `bazi-input-and-image-gate.md`, `bazi_fact_adapter.py`, `tool-adapters.md`, `adapter_validate.py` | `natal_static`: 已校验四柱、藏干、十神、月令、季节/调候标记；`natal_timing`: 再加完整 `calendar_normalization` 与大运/流年 | 限定范围内可解释 / 停止并列缺项 |
| BZ-01 | 子平入口和粗框架 | `sanming-tonghui/procedures.md` P-01~P-05, `yuanhai-ziping/rules.md` YR-01~YR-03 | 日主、月令、人元司事、透干、合冲刑害 | 日主主线、月令粗格、十神表、岁运图谱 |
| BZ-02 | 月令格局 / 成败救应 | `ziping-zhenquan/rules.md` ZPR-01~ZPR-16, `procedures.md` ZPP-01~ZPP-05 | 月令藏干、透干、会支、四吉四凶、合冲刑害、大运 | 格局候选、相神、成败、救应、取运方向 |
| BZ-03 | 旺衰 / 气势 / 通关 | `ditiansui-chanwei/procedures.md` DP-01~DP-04, `rules.md` DR-02-06~DR-04-02 | 得令失令、根气、十干性情、五行分布、相战、通关神 | 旺衰等级、扶抑/从化、通关或制伏方案 |
| BZ-04 | 调候 / 寒暖燥湿 | `qiongtong-baojian/procedures.md` QP-01~QP-05, `rules.md` QR-NN-MM | 日干、节气月令、三春/三夏/三秋/三冬、透藏、寒暖燥湿极端度 | 调候用神组合、配齐/有损/虚用/缺失 |
| BZ-05 | 冲突裁判 | `conflict-policy.md`, 本矩阵 §3 | BZ-02~BZ-04 的分歧 | 哪一层优先、哪一层降为旁证 |
| BZ-06 | 大运流年落点 | `sanming-tonghui/procedures.md` P-05, `ditiansui-chanwei/procedures.md` DP-04, `ziping-zhenquan/rules.md` ZPR-12~ZPR-13 | 仅 `natal_timing`：大运柱、流年柱、干支关系、触发十神/宫位/用神 | 年份/阶段主题、可测试时间窗 |
| BZ-07 | 神煞辅助 | shensha matrices + `sanming-tonghui` / `wuxing-jingji` 等 | 已完整八字事实层；若用户问神煞则读消歧矩阵 | 事项标签、应象、缺席项；不得覆盖主线 |
| BZ-08 | 后出辨析 / 反模板 | `shenfeng-tongkao/rules.md`, `mingli-yueyan/rules.md`, accuracy protocol | 前面结论的弱点、旧说争议、过度模板风险 | 纠偏、反例、输出压缩和校准字段 |

## 2. 书籍依赖与权重

| Pack | 一线角色 | 依赖 | 关键锚点 | 不得替代 |
|---|---|---|---|---|
| `bazi/sanming-tonghui` | 综合入口、术语索引、神煞总表、岁运关系图 | `yuanhai-ziping`, 早期禄命源流 | P-01~P-06; SM-Q128, SM-Q131, SM-Q185, SM-Q679, SM-Q829 | 精细格局、调候、旺衰 |
| `bazi/yuanhai-ziping` | 子平源流、日干为主、月令、人元司事、大运流年雏形 | 李虚中、珞琭子等早期禄命 | YR-01-03, YR-01-04, YR-01-12, YR-03-01, YR-03-02 | 后世格局精修、调候精修 |
| `bazi/ziping-zhenquan` | 月令格局、相神、成败救应、正格/外格边界 | `yuanhai-ziping`, `sanming-tonghui` | ZPR-01~ZPR-16; ZPP-01~ZPP-06; ZPQ-008~ZPQ-047 | 旺衰派、调候派、神煞 |
| `bazi/ditiansui-chanwei` | 旺衰精判、气势、通关、病药、寒暖燥湿旁证 | 子平总框架 | DP-01~DP-04; DR-02-06, DR-03-01, DR-03-04, DR-04-01, DR-04-02; DT-Q016, DT-Q021, DT-Q030, DT-Q031 | 月令格局成败、十干调候表 |
| `bazi/qiongtong-baojian` | 十干 × 月令调候用神 | 节气月令事实层、旺衰/格局合参 | QP-01~QP-05; QR-00~QR-05; QT-Q005~QT-Q056 | 格局成败、旺衰扶抑、神煞 |
| `bazi/shenfeng-tongkao` | 张神峰辨伪、病药法、混杂旧说纠偏 | 子平主线结论已成形后 | SF-R01~SF-R05 | 原典入口、确定寿夭疾病硬断 |
| `bazi/mingli-yueyan` | 清代实务辨证、反机械套格/套神煞 | 前五层结论 | MLY-R001~MLY-R008 | 原典主轴、事实计算 |

## 3. 冲突裁判

| 冲突 | 主裁判 | 说明 |
|---|---|---|
| 格局用神 vs 旺衰用神 | 先看问题类型；格局成败问题以 `ziping-zhenquan` 为主，体用强弱问题以 `ditiansui-chanwei` 为主 | 输出中保留“格局视角 / 旺衰视角”的差异，不硬揉成一个词 |
| 调候用神 vs 旺衰用神 | 寒暖燥湿极端时调候升权；非极端时调候作修正层 | `qiongtong-baojian` 明确不得单独断富贵贫贱 |
| 月令得令 vs 全局根气 | 以 `ditiansui-chanwei` DP-01/DR-03-01 精判 | 得令未必旺，失令未必衰；必须看根、透、合冲 |
| 外格/从化 vs 正格 | 正格可成立则不乱取外格；月令无用或特殊条件足时才开外格/从化分支 | 用 `ziping-zhenquan` ZPR-11/ZPR-16 与 `ditiansui-chanwei` DP-03 互校 |
| 神煞吉凶 vs 主线结构 | 主线结构优先，神煞只作事项标签 | 用 `shensha-cross-system-index.md` 和 `shensha-entry-source-profile.yaml` 消歧 |
| 单案反馈 vs 原典流程 | 单案反馈进入 case log 或 hypothesis，不改原典规则 | 必须等批量校准后才调整权重 |

## 4. 输出要求

八字正式回答至少私下生成以下中间字段，用户要求简短时可压缩展示，但不能跳过：

```text
question_type
fact_layer_status
calendar_normalization
four_pillars
hidden_stems
ten_gods
month_command
seasonal_tiaohou_profile
pattern_layer
strength_flow_layer
tiaohou_layer
luck_transit_layer
shensha_layer_if_used
source_packs_loaded
conflict_notes
confidence: fact/text/interpretation
```

如果最终回答被改写成聊天口吻，仍要在私下用 `gate_check.py --mode answer` 检查最终文本；涉及准确率/统计学时再用 `evaluate_answer.py --accuracy-requested`。

## 5. 反模板规则

1. “今天/明天运势”不能默认写财务、收尾、回款、催回复。只有当事实层或用户问题明确指向钱、合同、谈判、消息时才写。
2. 每个现实结论要能回指到 `十神/格局/岁运/调候/神煞` 中至少一个明确触发点；不能只给泛化鸡汤。
3. 输出应先回答用户问题，再给证据和边界。不要把所有八字问题写成同一种长报告。
4. 对“最真实的话”可以直说传统读法，但要分清传统读法、事实层、经验校准和现实证据。

## 6. 神煞书籍后续队列

用户后续要继续看神煞相关书籍时，按以下顺序处理：

| Priority | 书籍/方向 | 当前状态 | 用途 |
|---|---|---|---|
| S0 | 《三命通会》卷三神煞细校 | ready pack, 可二次精修 | 八字神煞第一入口 |
| S0 | 《五行精纪》《李虚中命书》《珞琭子三命消息赋》《玉照神应真经》 | ready pack | 禄命源流、贵神禄马罗网空亡等 |
| S0 | 《御定星历考原》《钦定协纪辨方书》 | ready pack | 择日神煞、黄黑道、建除、年月日时神 |
| S1 | 《大六壬大全》《六壬指南》《大六壬秘本》 | ready pack | 六壬课内神煞与天将类神 |
| S1 | 《紫微斗数全书》《太微赋》 | ready pack | 紫微星曜/辅煞消歧 |
| S1 | 《果天经/果老星宗》 | ready pack, 版本风险 | 七政四余神煞，只能在星命事实层内使用 |
| S1 | 《阳宅十书》《阳宅三要》 | ready pack | 八宅游年九星、天乙巨门、五鬼六煞等宅局语义 |
| S2 | 《星平会海/命海全编》《七政全书大成》 | image_only / OCR blocked | OCR 校勘前只能 acquisition，不得蒸馏成规则 |
| S3 | 《阳宅爱众篇》等阳宅神煞材料 | source lead only | 先建 manifest 和完整文本获取任务 |

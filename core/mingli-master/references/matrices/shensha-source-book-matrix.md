# 神煞来源书目矩阵

generated_at: 2026-07-05  
matrix_version: v0.1  
source_status: derived_from_current_catalog_and_qoder_manifests  
scope: 神煞相关书籍的来源层级、可用状态、加载边界

本矩阵回答“神煞相关应优先看哪些书”。它不替代 `shensha-cross-system-index.md` 的名称消歧，也不替代 `shensha-name-disambiguation.yaml` 的机器词表；每个具体神煞条目的书目优先级和 `source_pack_role` 见 `shensha-entry-source-profile.yaml`，现有 `quote-index/terms/rules` 可追溯覆盖见 `shensha-quote-trace.yaml`。本矩阵只规定神煞专题继续蒸馏时，哪些书可以作为一线来源，哪些只能作为源流旁证，哪些只是 acquisition/OCR 任务。具体下一批二次精修、验收条件和 acquisition 禁区见 `shensha-distillation-backlog.md` / `.yaml`；已完成的 SS-B1 八字/禄命高频神煞二次精修见 `shensha-ss-b1-refinement.md` / `.yaml`；已完成的 SS-B2 官方择日神煞起例/裁判精修见 `shensha-ss-b2-selection-refinement.md` / `.yaml`；已完成的 SS-B3 六壬神煞/天将边界精修见 `shensha-ss-b3-liuren-refinement.md` / `.yaml`；已完成的 SS-B4 紫微/星命同名神煞消歧见 `shensha-ss-b4-ziwei-xingming-refinement.md` / `.yaml`；已完成的 SS-B5 阳宅/八宅神煞隔离见 `shensha-ss-b5-yangzhai-refinement.md` / `.yaml`；SS-B6《星平会海/命海全编》OCR 校勘计划见 `shensha-ss-b6-minghai-ocr-plan.md` / `.yaml`；SS-B10 神煞专门书籍与跨体系书目核验计划见 `shensha-ss-b10-bibliography-plan.md` / `.yaml`。

## 总原则

1. ready pack 可以进入解释和索引；blocked/image-only 只能进入 acquisition/OCR backlog。
2. 神煞不是独立 oracle。书籍层的来源矩阵只能决定“读哪本书”，不能跳过八字、择日、六壬、紫微、星命、风水的事实层。
3. 同名神煞先查体系，再查书。`天乙`、`驿马/天马`、`羊刃/擎羊`、`太岁`、`白虎`、`空亡` 等不得跨体系合并。
4. 子平八字中，神煞低于月令、格局、旺衰、调候、十神、大运流年；择日中，神煞是事实层字段；六壬、紫微、星命、风水中，只在本系统盘/课/宅局内生效。

## 一线可用书目

| Priority | System | Pack | 书名 | 神煞用途 | 加载边界 |
|---|---|---|---|---|---|
| P0 | `bazi` | `bazi/sanming-tonghui` | 《三命通会》 | 八字神煞总入口：天乙、驿马、桃花、华盖、空亡、羊刃、魁罡等 | 必须已有八字事实层；只作旁证 |
| P0 | `luming-nayin` | `luming-nayin/wuxing-jingji` | 《五行精纪》 | 早期禄命贵神、禄马、华盖、金舆、凶煞、空亡、刑害源流 | 源流优先；不覆盖现代子平主线 |
| P0 | `selection` | `selection/xingli-kaoyuan` | 《御定星历考原》 | 年神、月神、日神、时神、黄黑道、二十八宿、四离四绝起例 | 起例考据；不单独定最终吉凶 |
| P0 | `selection` | `selection/xieji-bianfang-shu` | 《钦定协纪辨方书》 | 择日神煞辨方、用事宜忌、辨讹、冲突裁判 | 官方裁判；必须绑定 `mingli-master.selection.v1` |
| P0 | `san-shi` | `san-shi/daliuren-daquan` | 《大六壬大全》 | 六壬课内神煞、天将、类神、岁月神煞 | 只在六壬课式事实层内使用 |
| P0 | `ziwei` | `ziwei/ziwei-doushu-quanshu` | 《紫微斗数全书》 | 紫微星曜、辅煞、流年太岁、羊陀火铃空劫天刑天姚等 | 必须有紫微盘事实层；不并入八字 |
| P0 | `xingming` | `xingming/guotian-jing` | 《果天经/果老星宗》 | 七政四余神煞群：天刑、天马地驿、阳刃、咸池、空亡、劫亡、三刑六害等 | ready，但托名/版本有风险；必须有星命天文排盘 |
| P0 | `fengshui` | `fengshui/yangzhai-shishu` | 《阳宅十书》 | 八宅游年九星、生气、天乙巨门、五鬼、六煞、祸害、绝命 | 只在宅向/门灶床/福元事实层内使用 |

## Quote Trace 状态

`shensha-quote-trace.yaml` 由 `scripts/audit_shensha_traces.py` 从本地 ready pack 机械生成。它只证明“本地 pack 层里有可查锚点”，不等于该锚点已经转成可断事规则。

当前 v0.1 覆盖：39 个神煞条目；25 条全系统命中一线 `quote-index`；12 条有 `terms/rules` 层命中但需二次精修为 `quote-index`；1 条仅支撑源有 `quote-index`；1 条存在二次精校缺口。优先二次精修：`天医` 在阳宅/八宅语义中的天乙/天医异名关系、`天乙贵人` 八字一线 quote、`金舆` 八字一线 quote、禄命源流中的 `白虎/伏吟反吟/罗网/丧门吊客` 等 layer-only 项。

## 二线补充与边界书

| Priority | System | Pack | 书名 | 用途 | 边界 |
|---|---|---|---|---|---|
| P1 | `bazi` | `bazi/yuanhai-ziping` | 《渊海子平》 | 早期子平神煞术语、太岁、天乙、驿马、桃花、华盖、空亡等 | 源流/互证，不作精修派结论 |
| P1 | `bazi` | `bazi/ziping-zhenquan` | 《子平真诠》 | “星辰神煞不关格局”的降权边界 | 只作降权原则，不作神煞总表 |
| P1 | `bazi` | `bazi/shenfeng-tongkao` | 《神峰通考》 | 子平实务与旧说辨析，可互证神煞权重 | 不作为神煞独立断语来源 |
| P1 | `bazi` | `bazi/mingli-yueyan` | 《命理约言》 | 诸神煞辨伪、反机械套神煞 | 降权/纠偏层 |
| P1 | `luming-nayin` | `luming-nayin/li-xuzhong-mingshu` | 《李虚中命书》 | 早期贵神、文星、华盖、截路空亡、进神、伏神、羊刃等 | 禄命源流，不直接覆盖子平 |
| P1 | `luming-nayin` | `luming-nayin/luoluzi-sanming` | 《珞琭子三命消息赋》 | 将星、伏吟、反吟、空亡、天罗地网、禄命格局神煞 | 源流层，需区分徐注 |
| P1 | `luming-nayin` | `luming-nayin/lantai-miaoxuan` | 《兰台妙选》 | 禄命格局和贵格旁证 | 不作高频神煞总入口 |
| P1 | `luming-nayin` | `luming-nayin/yuzhao-shenying` | 《玉照神应真经》 | 早期干支神、刑害、禄命应象 | 只作源流与旁证 |
| P1 | `selection` | `selection/yuqia-ji` | 《玉匣记》 | 彭祖百忌、杨公忌、月忌、往亡、归忌、民俗禁忌日 | 民俗对照；低于官方择日层 |
| P1 | `selection` | `selection/donggong-zeri` | 《董公择日》 | 民间月日表、月日吉凶、通书冲突样本 | 只作 comparison |
| P1 | `san-shi` | `san-shi/liuren-zhiyin` | 《六壬指南/指引》 | 卷四“大六壬神煞指南” | 课内使用，不外推 |
| P1 | `san-shi` | `san-shi/liuren-miben` | 《大六壬秘本》 | 六壬秘本神煞、类神、课法旁证 | 课内使用，不外推 |
| P1 | `san-shi` | `san-shi/taiyi-shenshu` | 《太乙神数》 | 太岁、四神太乙、天乙太乙等宏观术语 | 只在太乙盘事实层内使用 |
| P1 | `ziwei` | `ziwei/taiwei-fu` | 《太微赋》 | 天马、擎羊、空亡、桃花、白虎等紫微赋文语义 | 星曜/赋文层，不并入八字 |
| P1 | `ziwei` | `ziwei/feixing-ziwei-doushu-yuanzhi` | 《飞星紫微斗数原旨/斗数观测录》 | 民国观测层，红鸾、大耗、天刑巨门等 | 注释层；不作古典主线 |
| P1 | `divination` | `divination/huangjin-ce` | 《黄金策》 | 六爻/火珠林法中神煞低于生克制化的边界证据 | 只用于六爻，不给八字/择日当来源 |
| P1 | `fengshui` | `fengshui/yangzhai-sanyao` | 《阳宅三要》 | 门主灶与游年九星、三吉四凶 | 只在阳宅事实层内使用 |

## Acquisition / OCR Backlog

| Priority | Candidate | System | Current source status | 为什么重要 | 下一步 |
|---|---|---|---|---|---|
| P2 | `xingming/minghai-quanbian`《新刻星平總會命海全編》/《星平会海》 | 星命/子平混合 | raw acquired, normalized blocked, source_status image_only；SS-B6 OCR pipeline v0.3 initialized；batch 001 page 013-024、batch 002 page 025、batch 003 page 026 均为 `in_review` 初校稿，合计 page 013-026 / `in_review=14` | 首卷已目检到“论诸吉神起例”，含诸吉神、诸煞星、小儿关煞等神煞线索 | 继续 page/leaf accounting + reviewed-page 转写/校勘到 `ocr_reviewed_complete`，计划见 `shensha-ss-b6-minghai-ocr-plan.md` |
| P2 | `xingming/qizheng-quanshu-dacheng`《七政全書大成》 | 七政四余/星命历算 | raw acquired, normalized blocked, source_status image_only | 七政四余历算表格来源，可补星命事实层 | 需要表格 OCR/人工校勘 |
| P2 | `xingming/qizheng-siyu-tianjing`《七政四余天经》 | 七政四余 | blocked，疑似误题/混名 | 名称不稳，不能冒名填充 | 继续 blocked；不得用《七政全书大成》冒名替代 |
| P2 | `san-shi/liuren-zhiyin-vol5-shensha-charts`《六壬指南》卷五神煞全图及相关表 | 六壬 | 本地图像资产已存在，pages 225-248 为 `draft_empty` | 可补六壬岁月神煞图表、掌诀和图式来源 | 表格/图式 OCR、人工校勘；未校勘前不得进入六壬断事规则 |
| P2 | 《阳宅爱众篇》 | 阳宅/八宅/择时 | source lead only | 可能补八宅游年九星、宅门修补择时、年月吉神煞 | 建 manifest、下载/校勘、确认完整度 |
| P3 | 《大汉原陵秘葬经》及墓葬神煞资料 | 葬法/墓葬神煞 | source lead only | 墓葬神煞历史源流 | 仅作文化史/葬法旁证，低优先 |
| P2 | `selection/xiangji-tongshu`《增补象吉通书大全 / 象吉通书》 | 择日/通书/风水择造 | source lead only；待核馆藏/版本 | 可补通书系择日神煞、修造安葬、二十四山与民间选择体系 | 先建 manifest、核完整影印；未完整前不得进入规则 |
| P2 | `selection/chongzheng-bimiu-tongshu`《崇正辟谬通书 / 崇正辟谬》 | 择日/通书/风水择造 | source lead only；版本复杂 | 可补择日神煞、造葬选择、斗首等通书旁证 | 只做书目核验与获取计划；不以二手网页作底本 |
| P3 | `selection/xieji-tongyi`《协吉通义》 | 择日/协纪旁支 | CTP/OCR source lead；本地未建 manifest | 可作《协纪辨方书》相关异文或抄撮线索 | 核底本、覆盖和 OCR 噪声；确认非重复后再决定是否获取 |
| P3 | `selection/jiugong-bagua-dunfa-mishu`《九宫八卦遁法秘书》 | 九宫/神煞/禄命杂术 | CTP/OCR source lead；本地未建 manifest | 可补神煞专门杂书、天德贵人与九宫八卦干支配置源流 | 仅书目核验/OCR 计划；不得并入八字或择日一线规则 |

## SS-B10 书目核验计划

`shensha-ss-b10-bibliography-plan.md` / `.yaml` 是本矩阵的执行计划层，只做三件事：

1. 把 ready pack 分成可二次精修的书目组：八字/禄命、官方择日、六壬、紫微/星命、阳宅。
2. 把 `星平会海/命海全编`、`七政全书大成`、`六壬指南卷五神煞图表`、`阳宅爱众篇`、`大汉原陵秘葬经` 等线索压在 acquisition/OCR 层。
3. 定义晋级门槛：manifest 完整、全文完整或 OCR 已校、规则有精确位置、体系边界清楚、同名不移植测试存在。

因此，后续“再找神煞书”时先看 SS-B10：能补书目和获取计划，不能直接写断事规则。

## SS-B6 OCR 校勘计划

`shensha-ss-b6-minghai-ocr-plan.md` / `.yaml` 是 `xingming/minghai-quanbian` 的执行层。当前它证明：

1. 6 册 PDF、437 页已下载并进入 page-map。
2. PDF 没有可抽取文字层。
3. Tesseract 与 Vision 在 page 14 样本上都不足以自动升格。
4. 已建立 review asset 生成脚本，但产物只能供人工/模型辅助校勘。

所以 SS-B6 仍不能进入解释层；下一步是 reviewed OCR，不是规则蒸馏。

## 加载决策

| 用户问题 | 先读 | 再读 | 不读 |
|---|---|---|---|
| “某神煞是什么意思” | `shensha-name-disambiguation.yaml` + `shensha-entry-source-profile.yaml` + `shensha-quote-trace.yaml` | 本矩阵中对应 system 的 ready pack | image-only/backlog |
| “我命里有哪些神煞” | `shensha-entry-source-profile.yaml` + `shensha-quote-trace.yaml` + `bazi/sanming-tonghui` + 本矩阵 | `wuxing-jingji` 作源流旁证；`mingli-yueyan` 作降权 | 择日/六壬/紫微/风水神煞 |
| “神煞从哪本书来” | 本矩阵 | `shensha-cross-system-index.md` 与对应 `quote-index.md` | 未校勘影印 |
| “择日神煞/黄道/建除” | `selection-fact-layer-profile.yaml` | `xingli-kaoyuan` 起例 + `xieji-bianfang-shu` 裁判 | 八字神煞总表 |
| “六壬神煞/天将” | `shensha-ss-b3-liuren-refinement.md` + 六壬 fact layer | `daliuren-daquan`, `liuren-zhiyin`, `liuren-miben` | 八字/紫微/择日同名神煞 |
| “紫微神煞/辅煞/流煞” | `shensha-ss-b4-ziwei-xingming-refinement.md` + 紫微 fact layer | `ziwei-doushu-quanshu`, `taiwei-fu`; `feixing-ziwei-doushu-yuanzhi` 只作注释 | 八字/择日/六壬同名神煞 |
| “星命神煞/果老神煞” | `shensha-ss-b4-ziwei-xingming-refinement.md` + 星命 fact layer | `guotian-jing`; `xingming-suyuan` 可互证 | `minghai-quanbian` until OCR complete |
| “八宅天乙/五鬼/六煞” | `shensha-ss-b5-yangzhai-refinement.md` + 风水/阳宅 fact layer | `yangzhai-shishu`, `yangzhai-sanyao` | 八字天乙/六壬天乙/择日天医 |

## 后续蒸馏顺序

1. 维护 `shensha-entry-source-profile.yaml`，确保每个高频神煞条目都有 `book_priority` 和 `source_pack_role`。
2. 维护 `shensha-quote-trace.yaml`，每次新增/精修神煞 pack 后运行 `python scripts/audit_shensha_traces.py --write-yaml references/matrices/shensha-quote-trace.yaml`。
3. SS-B4 已约束紫微/星命同名项；SS-B5 已约束阳宅/八宅神煞隔离。
4. SS-B10 已完成 v0.1 书目核验计划；继续神煞专书方向时，优先执行 SS-B6《星平会海/命海全编》OCR 校勘。当前已填写并校验 page 013-026 的 reviewed-page 初校稿，下一步仍是继续 OCR/校勘扩页，而不是直接抽规则。
5. 最后处理 P2/P3：只在 OCR/校勘通过后进入 D2；否则只保留 acquisition 状态。

# SS-B10 神煞书籍核验计划

generated_at: 2026-07-05  
matrix_version: v0.1  
source_status: bibliography_and_acquisition_plan_only  
scope: 神煞相关书籍、跨体系来源依赖、以及后续获取/OCR/校勘工单。

本文件回应“后续顺便看看神煞相关的书籍”。它不是断事规则，也不是新的神煞总表；它只规定哪些本地 ready pack 可以继续做二次精修，哪些书名只能作为 source lead，哪些必须先完成 manifest、下载、OCR 和校勘。

## 核心结论

1. 当前可继续二次精修的神煞来源，主要仍是本地 D2/normalized ready pack：`三命通会`、`五行精纪`、`李虚中命书`、`星历考原`、`协纪辨方书`、`大六壬大全`、`六壬指南`、`六壬秘本`、`紫微斗数全书`、`果天经/果老星宗`、`阳宅十书`、`阳宅三要`。
2. 当前没有把任何“神煞专书”直接升为可断事来源。`星平会海/命海全编` 虽然有“诸吉神/诸煞星/小儿关煞”线索，但目前是 image-only，不能蒸馏规则。
3. 后续新增神煞书籍时，先做书目核验和整本获取；没有 `complete_text`、`complete_chapter_set` 或 `ocr_reviewed_complete`，就只能进 acquisition/OCR backlog。
4. 现有 ready pack 内部若还有未校勘图表，也按 acquisition/OCR 处理。例如《六壬指南》卷五 225-248 页“神煞全图及相关表”已有本地图像资产，但仍是 `draft_empty`，不能直接进规则。
5. 《星平会海/命海全编》已为 v.1 page 013-026 创建 reviewed-page 草稿位；当前 batch 001 page 013-024、batch 002 page 025、batch 003 page 026 均为 `in_review` 初校稿，合计 `in_review=14`。这只表示有稳定转写落点，不表示已有 final reviewed text。
6. 神煞不是独立 oracle。八字、禄命、择日、六壬、紫微、星命、风水各有事实层，同名词不得串台。

## 可二次精修书目

| Group | Priority | Pack | 书名 | 当前用途 | 不允许 |
|---|---|---|---|---|---|
| 八字/禄命 | P0 | `bazi/sanming-tonghui` | 《三命通会》 | 八字神煞总入口；补 quote-index、条目权重、边界 | 不凭单一神煞断命 |
| 八字/禄命 | P0 | `luming-nayin/wuxing-jingji` | 《五行精纪》 | 早期禄命贵神、禄马、华盖、金舆、凶煞源流 | 不覆盖现代子平主线 |
| 八字/禄命 | P1 | `luming-nayin/li-xuzhong-mingshu` | 《李虚中命书》 | 天乙贵神、贵合贵食、紫虚局、三元九命源流 | 不把传本真伪争议抹平 |
| 择日 | P0 | `selection/xingli-kaoyuan` | 《御定星历考原》 | 年月日时神煞起例考源 | 不单独定吉凶 |
| 择日 | P0 | `selection/xieji-bianfang-shu` | 《钦定协纪辨方书》 | 官方择日裁判、辨讹、用事宜忌 | 不绕过 `mingli-master.selection.v1` |
| 六壬 | P1 | `san-shi/daliuren-daquan` | 《大六壬大全》 | 六壬课内神煞、天将、类神 | 不移植到八字/紫微/择日 |
| 六壬 | P1 | `san-shi/liuren-zhiyin` | 《六壬指南/指引》 | 卷四神煞指南，入门表述定位 | 不离开四课三传事实层 |
| 六壬 | P1 | `san-shi/liuren-miben` | 《大六壬秘本》 | 类神、秘本神煞、课法旁证 | 不覆盖《大六壬大全》 |
| 紫微/星命 | P1 | `ziwei/ziwei-doushu-quanshu` | 《紫微斗数全书》 | 紫微星曜、辅煞、流煞 | 不并入八字神煞 |
| 紫微/星命 | P1 | `xingming/guotian-jing` | 《果天经/果老星宗》 | 七政四余神煞群 | 不用旧行度表替代现代星历 |
| 阳宅 | P1 | `fengshui/yangzhai-shishu` | 《阳宅十书》 | 八宅游年九星、三吉四凶 | 不写入命盘神煞清单 |
| 阳宅 | P1 | `fengshui/yangzhai-sanyao` | 《阳宅三要》 | 门主灶、东西四宅、游年九星支持层 | 不忽略翻印/整理层风险 |

## 只能当线索的书目

| Source lead | System | Current status | 为什么值得看 | 现在只能做什么 |
|---|---|---|---|---|
| `xingming/minghai-quanbian`《新刻星平總會命海全編 / 星平会海》 | 星命/子平混合 | image_only；raw acquired；normalized blocked | 已记录有“论诸吉神起例”“诸煞星起例”“小儿关煞”等线索；识典 HY1442 仅可作小范围对勘线索 | manifest、页码 inventory、OCR、人工校勘；不得批量抓取识典或以其生成 normalized source |
| `xingming/qizheng-quanshu-dacheng`《七政全书大成》 | 七政四余/星命 | image_only；raw acquired；normalized blocked | 星命历算表格与事实层 adapter 候选 | 表格 OCR、结构化校验、adapter 评估 |
| `xingming/qizheng-siyu-tianjing`《七政四余天经》 | 七政四余 | blocked_unstable_title | 书名疑似误题或混名 | 只做书名/版本考证 |
| `san-shi/liuren-zhiyin-vol5-shensha-charts`《六壬指南》卷五神煞全图及相关表 | 六壬 | local vision assets exist；pages 225-248 `draft_empty` | 可补六壬岁月神煞图表、掌诀和图式来源 | 表格/图式 OCR、人工校勘、再合并到 `liuren-zhiyin` 支持层 |
| `fengshui/yangzhai-aizhong-pian`《阳宅爱众篇》 | 阳宅/八宅 | source lead only；unverified | 可能补八宅游年、宅门修补择时、年月吉神煞 | 先核馆藏/版本，再决定是否抓取/OCR |
| `fengshui/dahan-yuanling-mizangjing`《大汉原陵秘葬经》 | 葬法/墓葬神煞 | source lead only；unverified | 墓葬神煞历史源流线索 | 只做书目验证，不进个人命理解释 |

## 待核验新增候选

这些书名回应“后续顺便看看神煞相关书籍”。它们只进入书目核验队列，不进入解释层；后续必须先补 `source-manifest.yaml`、版本/馆藏说明、来源使用限制和完整度状态。

| Candidate | System | Initial lead | 为什么值得看 | 现在只能做什么 |
|---|---|---|---|---|
| `selection/xiangji-tongshu`《增补象吉通书大全 / 象吉通书》 | 择日/通书/风水择造 | 台湾文化部/历史博物馆等可见馆藏或翻页线索；本地未建 manifest | 通书系择日、修造、安葬、二十四山、年/月/日/时吉凶神煞与民间选择体系 | 核馆藏与版本；确认是否可获取整本影印；未得完整文本前不蒸馏 |
| `selection/chongzheng-bimiu-tongshu`《崇正辟谬通书 / 崇正辟谬》 | 择日/风水择造 | 书格与百科线索显示为清李泰来汇编，版本复杂；本地未建 manifest | 集命理、风水、择吉，可能补通书系神煞、造葬选择、斗首等旁证 | 只做书目和版本核验；优先找馆藏/影印，不用二手网页作底本 |
| `selection/xieji-tongyi`《协吉通义》 | 择日/协纪旁支 | CTP 可见 OCR/wiki 线索，需核书名、底本、章节覆盖 | 可能是《协纪辨方书》相关择日神煞旁支或抄撮本，可作版本/异文线索 | 先创建 source lead manifest；确认是否完整、是否 OCR 噪声、是否与《协纪辨方书》重复 |
| `selection/jiugong-bagua-dunfa-mishu`《九宫八卦遁法秘书》 | 九宫/禄命/神煞杂术 | CTP 条目说明其以天干地支、天德贵人等星宿相配推吉凶，基于阴阳家神煞说并融入禄命学 | 可补“神煞专门杂书”源流，尤其天德贵人与九宫/八卦/干支配置 | 仅书目核验与 OCR/acquisition；不得并入八字或择日一线规则 |

## 晋级门槛

任何神煞相关书籍，只有同时满足以下条件，才能从“线索”晋级为可蒸馏 reference pack：

1. `source-manifest.yaml` 完整：书名、slug、system、版本、source_status、来源链接、本地文件、卷章覆盖、出处说明、OCR/校勘质量、使用限制都齐。
2. 文本状态是 `complete_text`、`complete_chapter_set` 或 `ocr_reviewed_complete`。
3. 每条规则都有卷/章/页/URN/本地行号等可复核位置。
4. 明确它属于哪个体系：八字、禄命、择日、六壬、紫微、星命、风水或相法。
5. 有同名不移植边界：例如八字天乙、六壬天乙、八宅天乙巨门、择日天医不能合并。

## 工单顺序

| Work order | Target | 对应批次 | 下一步 |
|---|---|---|---|
| SS-B10-A1 | `xingming/minghai-quanbian` | SS-B6 | manifest → 页码/卷次 inventory → reviewed-page 草稿位 → OCR/图像模型/人工转写 → 人工抽样校勘 → 行号覆盖；识典 HY1442 只作 logged comparison aid |
| SS-B10-A2 | `xingming/qizheng-quanshu-dacheng` | SS-B7 | manifest → 表格 inventory → 表格 OCR → 结构化校验 → adapter 可用性评估 |
| SS-B10-A3 | `fengshui/yangzhai-aizhong-pian` | SS-B8 | 书目核验 → manifest → 获取扫描/全文 → OCR/转写 → source_status 复核 |
| SS-B10-A4 | `fengshui/dahan-yuanling-mizangjing` | SS-B9 | 书目核验 → 身份确认 → 决定获取或放弃 |
| SS-B10-A5 | `san-shi/liuren-zhiyin-vol5-shensha-charts` | SS-B3 follow-up | page 225-248 图表 inventory → table OCR/人工校勘 → 与《六壬指南》支持层合并 → 六壬 fact-layer 边界复核 |

## 给后续蒸馏的约束

- 如果只是问“神煞相关还有哪些书”，可以读本文件和 `shensha-source-book-matrix.md`。
- 如果要真正进入规则蒸馏，必须回到每本书的 `source-manifest.yaml` 和完整原文。
- 如果只是 image-only 或 source-lead-only，就算书名再像“神煞专书”，也不能写进 `rules.md`、`procedures.md` 或回答层。
- 如果 ready pack 内部还有未校勘图表，按未校勘来源处理；图表 OCR 完成前只作为工单，不作为 quote 或 rule。
- 当前下一步应先做 SS-B6《星平会海/命海全编》OCR 校勘，因为它最像神煞专门书目线索，但目前文本状态还没过关。

# 三命通会 — Procedures

> 本文件抽取《三命通会》中可被主 skill 调用的可操作流程。
> 字段：`procedure_id` / `name` / `inputs` / `steps` / `outputs` / `tool_dependencies` / `source_chapter` / `verification_status`。
> 所有涉及排盘、节气换月、起运岁数、藏干配比等事实计算的步骤一律以 `tool.bazi.paipan` 标注，**不让 LLM 手算**。

---

## P-01 八字排盘前置

- **name**：八字排盘前置
- **inputs**：公历生年月日时（精确到分）/ 出生地经纬度或时区 / 性别 / 是否真太阳时
- **steps**：
  1. 校验 inputs 是否齐全；不齐则进入降级流程，不强行排盘。
  2. 调用 `tool.bazi.paipan` 取得四柱、藏干、十神、大运、流年。
  3. 校验节气换月（以节气分界，不以朔望分界）。
  4. 校验真太阳时（如未做，输出加"待真太阳时复核"标注）。
  5. 输出干支表 + 大运表 + 流年表，作为后续流程的事实层基础。
- **outputs**：四柱八字 / 月令藏干 / 十神 / 大运表 / 流年表
- **tool_dependencies**：`tool.bazi.paipan`（必需）
- **source_chapter**：vol-02/nian-yue-ri-shi；vol-02/sishi-jieqi
- **verification_status**：pending_verification

## P-02 月令取格（粗框架）

- **name**：月令取格粗框架
- **inputs**：P-01 的输出
- **steps**：
  1. 取月支所藏本气、中气、余气（人元司令）。
  2. 看本气是否透出年/日/时干。
     - 本气透 → 以本气取格。
     - 本气不透 → 看中气透干。
     - 中气余气皆不透 → 看其余柱所透干。
  3. 月支为辰戌丑未时按"杂气格"特例处理。
  4. 月支建禄（日干临官）、阳刃（阳干在刃位）→ 不取格，转扶抑。
  5. 输出格局粗框架；精修判断转 `bazi/ziping-zhenquan` (R2 / R3 / R4)。
- **outputs**：候选格局名 / 透干清单 / 是否建禄 / 是否阳刃
- **tool_dependencies**：`tool.bazi.paipan`
- **source_chapter**：vol-02/renyuan-sishi；vol-05/zhengguan；vol-06/jianlu；vol-06/yangren；vol-06/zaqi
- **verification_status**：pending_verification

## P-03 十神判读

- **name**：十神判读
- **inputs**：P-01 的四柱与藏干
- **steps**：
  1. 以日干为参照，判其余 7 柱及月令藏干的十神归属。
  2. 标注每个十神所在柱位（年/月/日支/时）与所在天干/地支。
  3. 看十神是否在月令、是否透干、是否被冲合刑害。
  4. 输出十神清单 + 强弱倾向（不做最终结论）。
- **outputs**：十神配属表 / 透干清单 / 月令所藏十神
- **tool_dependencies**：`tool.bazi.paipan`
- **source_chapter**：vol-05/lishou-yinmingyi；vol-06/yinshou；vol-06/zhengcai 等
- **verification_status**：pending_verification

## P-04 五行旺衰扶抑（粗框架）

- **name**：日主旺衰扶抑粗框架
- **inputs**：P-01 的四柱
- **steps**：
  1. 以日干在月令的旺、相、休、囚、死定基础旺衰。
  2. 看其它柱对日干的扶（印、比劫）与抑（食伤、财、官煞）。
  3. 综合得出"身强 / 身弱 / 中和"粗判。
  4. 输出粗框架；精细旺衰转 `bazi/ditiansui-chanwei`。
- **outputs**：粗旺衰判断 / 扶 / 抑成员清单
- **tool_dependencies**：`tool.bazi.paipan`
- **source_chapter**：vol-02/wuxing-wangxiang；vol-02/tiangan-yinyang-shengsi
- **verification_status**：pending_verification

## P-05 大运流年合参

- **name**：大运流年合参
- **inputs**：P-01 的大运表 + 流年表 + 待问年份
- **steps**：
  1. 锁定待问年份所在大运柱与流年柱。
  2. 看大运、流年与命局的生克冲合刑害。
  3. 看大运、流年是否岁运并临（同支或同冲）。
  4. 看大运、流年触发的神煞（驿马、桃花、贵人、空亡填实等）。
  5. 输出"该年大运流年与命局的关系图谱"，不下铁口结论。
- **outputs**：大运流年关系图 / 触发的神煞清单
- **tool_dependencies**：`tool.bazi.paipan`
- **source_chapter**：vol-02/dayun；vol-02/taisui；vol-02/zonglun-suiyun
- **verification_status**：pending_verification

## P-06 神煞查表

- **name**：神煞查表
- **inputs**：P-01 的四柱
- **steps**：
  1. 以日干为主查：天乙贵人、禄、羊刃、空亡、三奇、天月德。
  2. 以年支或日支为主查：驿马、华盖、将星、咸池、孤辰、寡宿、灾煞、劫煞、亡神。
  3. 以月支为主查：天罗、地网。
  4. 标注每个神煞的所在柱与是否被冲合。
  5. 输出神煞清单；按 R-03-05 神煞作辅证不主主线。
- **outputs**：神煞清单（按煞名 + 所在柱 + 是否动）
- **tool_dependencies**：`tool.bazi.paipan`（取支柱信息）
- **source_chapter**：vol-03/*（神煞大全）；vol-02/jiangxing-huagai；vol-02/xianchi
- **verification_status**：pending_verification

## P-07 合化判断

- **name**：合化判断
- **inputs**：P-01 的四柱
- **steps**：
  1. 检测天干五合（甲己、乙庚、丙辛、丁壬、戊癸）。
  2. 检测地支六合、三合、半三合。
  3. 对每组合判断是否化（化神当令、有根、不被冲克破合）。
  4. 输出"成功化气" vs "合而不化"两类。
  5. 化气格的判定转 `bazi/ziping-zhenquan` 或 `bazi/ditiansui-chanwei` 精细审查。
- **outputs**：合化清单 + 是否真化
- **tool_dependencies**：`tool.bazi.paipan`
- **source_chapter**：vol-02/shigan-he；vol-02/shigan-huaqi；vol-02/zhiyuan-liuhe；vol-02/zhiyuan-sanhe
- **verification_status**：pending_verification

## P-08 刑冲破害判断

- **name**：刑冲破害判断
- **inputs**：P-01 的四柱
- **steps**：
  1. 检测六冲（子午、丑未、寅申、卯酉、辰戌、巳亥）。
  2. 检测三刑（寅巳申、丑戌未、子卯）与自刑（辰午酉亥）。
  3. 检测六害（子未、丑午、寅巳、卯辰、申亥、酉戌）。
  4. 标注涉及的柱与是否动神（被冲为动）。
  5. 输出刑冲破害清单 + 简要影响（不下铁口）。
- **outputs**：刑冲破害清单
- **tool_dependencies**：`tool.bazi.paipan`
- **source_chapter**：vol-02/chongji；vol-02/sanxing；vol-02/liuhai
- **verification_status**：pending_verification

## P-09 杂格快查

- **name**：杂格快查
- **inputs**：P-01 的四柱
- **steps**：
  1. 按日柱查：魁罡、日贵、日德、财官双美。
  2. 按时柱查：日禄归时、时上偏财、时上一位贵。
  3. 按多柱配合查：拱禄拱贵、飞天禄马、六阴朝阳、六乙鼠贵、子午双包、四位纯全。
  4. 命中候选 → 进入对应杂格规则审查（R-06-01 至 R-06-15 等）。
  5. 输出候选杂格清单 + 是否真成。
- **outputs**：候选杂格清单
- **tool_dependencies**：`tool.bazi.paipan`
- **source_chapter**：vol-06/kuigang；vol-06/rilu-guishi；vol-06/feitian-luma 等
- **verification_status**：pending_verification

## P-10 五行专局格审查

- **name**：五行专局格审查
- **inputs**：P-01 的四柱
- **steps**：
  1. 检测地支三合或方局是否成（亥卯未/寅卯辰、寅午戌/巳午未、申子辰/亥子丑、巳酉丑/申酉戌、辰戌丑未全）。
  2. 看日干是否为本局五行；不是 → 转其它格。
  3. 看四柱是否有克化神之神；有则破。
  4. 真成时以化神为用；忌运逢克化神。
  5. 输出专局格判断（曲直/炎上/从革/润下/稼穑）。
- **outputs**：专局格判断 + 喜忌倾向
- **tool_dependencies**：`tool.bazi.paipan`
- **source_chapter**：vol-06/quzhi 等（R-06-02）
- **verification_status**：pending_verification

## P-11 女命模块

- **name**：女命模块
- **inputs**：P-01 的四柱（性别 = 女）
- **steps**：
  1. 取夫星：以正官为夫；夫宫看日支。
  2. 取子星：以食伤为子。
  3. 看夫宫稳定性（被冲、被合、空亡）。
  4. 看伤官见官（R-06-12）的影响。
  5. 输出女命基本结构；不照搬本书贬义判语（如"濁滥娼淫"等条目），现代输出统一 reframe。
- **outputs**：夫星 / 子星 / 夫宫 / 主要喜忌
- **tool_dependencies**：`tool.bazi.paipan`
- **source_chapter**：vol-07/numing 及其全部子目
- **verification_status**：pending_verification

## P-12 性情形貌倾向

- **name**：性情形貌倾向
- **inputs**：P-01 的四柱
- **steps**：
  1. 看日干所属五行：木仁、火礼、土信、金义、水智。
  2. 看十神偏重（食伤多则才艺、印多则学、官煞多则压力等）。
  3. 看五行偏枯（缺火、缺水、过燥、过湿等）。
  4. 输出性情形貌倾向；与命主自我描述对照，不作绝对判定。
- **outputs**：性情倾向 / 形貌倾向
- **tool_dependencies**：`tool.bazi.paipan`
- **source_chapter**：vol-07/xingqing-xiangmao
- **verification_status**：pending_verification

## P-13 体质倾向（不作医学结论）

- **name**：体质倾向
- **inputs**：P-01 的四柱
- **steps**：
  1. 按 R-07-02 配五脏六腑：甲乙肝胆、丙丁心小肠、戊己脾胃、庚辛肺大肠、壬癸肾膀胱。
  2. 看五行偏枯（过旺、过弱、被冲、被合）对应脏腑。
  3. 输出体质倾向；**遇用户问诊一律建议就医**，不作医学结论。
- **outputs**：体质倾向（仅倾向）
- **tool_dependencies**：`tool.bazi.paipan`
- **source_chapter**：vol-07/jibing
- **verification_status**：pending_verification

## P-14 日时断查表

- **name**：日时断查表
- **inputs**：P-01 的日柱与时柱
- **steps**：
  1. 由日柱定 60 日组之一。
  2. 由时柱在日组内定 12 时之一。
  3. 在 chapter-map.md 卷八 / 卷九中定位对应日组的 chapter URL。
  4. 加载 quote-index.md 中对应日时的短引（若已抽取）。
  5. **本 Batch 大量日时断条目仍 `pending`**；查不到时输出 "本日时段未抽取，留待后续 Batch"。
- **outputs**：对应日时断语短引（若有）
- **tool_dependencies**：`tool.bazi.paipan`（日柱时柱）
- **source_chapter**：vol-08/*；vol-09/*
- **verification_status**：pending_verification

## P-15 六亲推断

- **name**：六亲推断
- **inputs**：P-01 的四柱
- **steps**：
  1. 按 R-07-05：父—偏印；母—正印；兄弟姐妹—比劫；妻—正财；子—食伤（男）；夫—正官（女）。
  2. 看对应十神的所在柱、是否被冲合、是否得用。
  3. 输出六亲倾向；现代有"父—偏财"等异说，需明标流派。
- **outputs**：六亲倾向
- **tool_dependencies**：`tool.bazi.paipan`
- **source_chapter**：vol-07/liuqin
- **verification_status**：pending_verification

## P-16 十干坐支与月时配合查询

- **name**：十干坐支与月时配合查询
- **inputs**：P-01 的四柱（日干、日支、月支、时支）
- **steps**：
  1. 由日干确定十干喜忌支位（R-04-01）。
  2. 看日干坐支是否在喜支或忌支（R-04-01 十干喜忌表）。
  3. 看月支对日干的旺衰影响：当令则旺，失令则衰（R-04-04）。
  4. 看时支对日干的扶抑：时支生日干或为日干禄旺之地则为扶（R-04-02）。
  5. 综合月时配合得出"得月得时 / 得月失时 / 失月得时 / 失月失时"等粗判。
  6. 看大运是否改变月时配合的旺衰重心（R-04-03）。
- **outputs**：十干坐支喜忌 / 月时配合等级 / 大运扶抑倾向
- **tool_dependencies**：`tool.bazi.paipan`
- **source_chapter**：vol-04/shigan-zuozhi；vol-04/shier-yuezhi-derigan
- **verification_status**：pending_verification

## P-17 杂格筛选流程

- **name**：杂格筛选流程
- **inputs**：P-01 的四柱
- **steps**：
  1. 按日柱查日柱特格：魁罡（R-06-01）、日贵（R-06-21）、日德（R-06-21）、财官双美（R-06-21）、八专禄旺（R-06-28）。
  2. 按时柱查时柱特格：六阴朝阳（R-06-18）、六乙鼠贵（R-06-18）、日禄归时（R-06-18）、六壬趋艮（R-06-20）、六甲趋乾（R-06-20）。
  3. 按多柱配合查遥合冲合类：子遥巳禄（R-06-17）、冲合禄马（R-06-17）、飞天禄马（R-06-23）、拱禄拱贵（R-06-19）、子午双包（R-06-25）。
  4. 按五行查六神兽格（R-06-26）和五行专格补（R-06-29）。
  5. 命中候选杂格 → 进入对应规则审查是否真成（忌破格条件）。
  6. **重要**：输出时明确标注"以上杂格属古法/杂格参考，不作为现代八字主线结论；主线判断以月令格局（P-02）为第一路径"（R-06-37）。
- **outputs**：候选杂格清单 + 真成/不成判断 + caveats
- **tool_dependencies**：`tool.bazi.paipan`
- **source_chapter**：vol-06/*（杂格全章）；vol-06/kuigang；vol-06/feitian-luma 等
- **verification_status**：pending_verification

## P-18 纳音六十甲子查法

- **name**：纳音六十甲子查法
- **inputs**：年柱或日柱干支
- **steps**：
  1. 取年柱或日柱干支的甲子组合（如甲子、乙丑等）。
  2. 查纳音五行取象表：甲子乙丑→海中金、丙寅丁卯→炉中火…（30组纳音）。
  3. 查六十甲子吉凶判词（如"甲子海中金，藏而不露"）。
  4. 输出纳音取象及吉凶倾向。
- **outputs**：纳音五行 / 取象名称 / 吉凶倾向
- **tool_dependencies**：`tool.bazi.paipan`（取年柱日柱干支）
- **source_chapter**：vol-01/nayin-quxiang；vol-01/liushi-jiazi-jixiong
- **verification_status**：pending_verification

## P-19 胎元查询

- **name**：胎元查询
- **inputs**：P-01 的月柱
- **steps**：
  1. 取月柱天干进一位（甲→乙、丙→丁…）。
  2. 取月柱地支进三位（子→卯、丑→辰…）。
  3. 合成胎元干支柱。
  4. 看胎元与命局四柱的生克关系（古法辅助判断）。
- **outputs**：胎元干支 / 与命局关系
- **tool_dependencies**：`tool.bazi.paipan`（取月柱）
- **source_chapter**：vol-02/taiyuan
- **verification_status**：pending_verification

## P-20 女命子目 reframe 流程

- **name**：女命子目 reframe 流程
- **inputs**：P-01 的四柱 + 用户性别（女）
- **steps**：
  1. 按 R-07-06~R-07-11 逐一对照女命子目（纯和清贵→夫星子星关系→官煞正偏→夫宫稳定）。
  2. 用中性命理语言表述结果（如"正官得用，夫星清纯"替代"纯和清贵"）。
  3. 对敏感内容（R-07-07 浊滥、R-07-10 横夭）严格执行 reframe 规则：古文判语一律不输出。
  4. 输出现代中性化解读。
- **outputs**：女命结构分析 / 中性化表述
- **tool_dependencies**：`tool.bazi.paipan`
- **source_chapter**：vol-07/numing/*（女命全章）
- **verification_status**：pending_verification

## P-21 日时断查法

- **name**：日时断查法（卷八卷九完整版）
- **inputs**：P-01 的日柱与时柱
- **steps**：
  1. 由日柱定日干（甲~癸，10干）。
  2. 由时柱定时支（子~亥，12支）。
  3. 在 chapter-map.md 卷八/卷九中定位对应日组（R-08-01~R-09-05）。
  4. 加载 quote-index.md 中对应日时的短引（若已抽取）。
  5. **输出时明确标注"本条为古法日时断语索引，不可作为现代八字主线结论"。**
- **outputs**：对应日时古法断语索引（若有）
- **tool_dependencies**：`tool.bazi.paipan`（日柱时柱）
- **source_chapter**：vol-08/*；vol-09/*
- **verification_status**：pending_verification

---

## 流程总图

```text
[用户问题] ─► P-01 排盘前置 (tool.bazi.paipan)
                 │
                 ├─► P-02 月令取格 ─► (精修转 bazi/ziping-zhenquan)
                 ├─► P-03 十神判读
                 ├─► P-04 旺衰扶抑 ─► (精修转 bazi/ditiansui-chanwei)
                 ├─► P-05 大运流年合参
                 ├─► P-06 神煞查表
                 ├─► P-07 合化判断
                 ├─► P-08 刑冲破害
                 ├─► P-09 杂格快查
                 ├─► P-10 专局格审查
                 ├─► P-11 女命模块（性别=女）
                 ├─► P-12 性情形貌倾向
                 ├─► P-13 体质倾向（不作医学结论）
                 ├─► P-14 日时断查表
                 ├─► P-15 六亲推断
                 ├─► P-16 十干坐支与月时配合查询（卷四）
                 ├─► P-17 杂格筛选流程（卷六完整版）
                 ├─► P-18 纳音六十甲子查法（卷一）
                 ├─► P-19 胎元查询（卷二）
                 ├─► P-20 女命子目 reframe（卷七）
                 └─► P-21 日时断查法（卷八卷九）
                 │
                 ▼
       conflict-policy.md 裁判
                 │
                 ▼
       skill-draft/SKILL.md §6 输出骨架
```

---

**说明**：所有事实层步骤均由 `tool.bazi.paipan` 完成；本 pack 不包含任何手算逻辑。Batch 0.5 初始 15 条流程；Batch 0.6 +2 条（P-16/P-17）；Batch 0.7 +4 条（P-18~P-21），总计 21 条流程。

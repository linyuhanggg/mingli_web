# 董公择日 — Rules

> D2 规则包。规则来自《董公选择日要览》本地规范化文本与 `monthly-day-table.md` 全书逐日条目表。
> 字段：`rule_id` / `rule_statement` / `source_chapter` / `evidence` / `applicable_to` / `caveats` / `verified`。
> `verified=false` 表示尚未对国图影印逐页校勘；所有输出均须标注“文化参考，非事实判断”。

---

## DR-01 择日选时总纲

- **rule_statement**：本书把筮仕、受官、出行、谋干、婚姻、起造移居、丧凶葬祭等用事都纳入“择日选时”框架；日与时并看，不能只看日课。
- **source_chapter**：front/lue-ji；front/lunlue-shisanze
- **evidence**：quote-index.md DG-Q002~DG-Q004
- **applicable_to**：择日总纲 / 主 skill 路由
- **caveats**：文化参考，非事实判断；现代事项不以此作实际决策依据。
- **verified**：false

## DR-02 月建建除十二日为核心索引

- **rule_statement**：全书主体按正月寅月至十二月丑月，每月列 12 个建除日（建、除、满、平、定、执、破、危、成、收、开、闭）并给出宜忌、应事与凶验叙述。
- **source_chapter**：month/01-yin~month/12-chou
- **evidence**：monthly-day-table.md DG-D001~DG-D144；quote-index.md DG-Q007~DG-Q150
- **applicable_to**：逐月逐日民间通书口径查询
- **caveats**：不得让 LLM 手算日期；具体某日属于何月建、何干支，必须调用 `mingli-master.selection.v1`。
- **verified**：false

## DR-03 月日表只能作历史文本证据

- **rule_statement**：当用户问“某日是否宜嫁娶/动土/安葬/出行”时，主 skill 应先调用历算工具确定干支与月建，再用本表检索对应月支+建除日；输出时说明这是《董公选择日要览》的民间通书说法。
- **source_chapter**：month/*
- **evidence**：monthly-day-table.md 全表
- **applicable_to**：择日问答流程 / skill 运行约束
- **caveats**：不得直接把表内“吉”“凶”“应验”当事实判断；需与《协纪辨方书》《星历考原》交叉。
- **verified**：false

## DR-04 煞入中宫、白虎入中宫优先避用

- **rule_statement**：本书论略中特别提示煞入中宫或白虎入中宫之日，不宜在庭院中钉钉、鼓乐喧哗；即使有煞贡、直星、人专、天德、月德等，也主张避用为上。
- **source_chapter**：front/lunlue-shisanze
- **evidence**：quote-index.md DG-Q005
- **applicable_to**：起造 / 嫁娶 / 中庭动作 / 凶煞冲突裁判
- **caveats**：这是本书民间风险偏好，官方口径仍应以《协纪辨方书》《星历考原》为上位参照。
- **verified**：false

## DR-05 金神七煞为兴工动土类避忌

- **rule_statement**：金神七煞歌把角、亢、奎、娄、牛、鬼等宿与出兵、行船、修造、嫁娶等凶象相连；技能中应把它作为“民间通书避忌项”，不是独立断验。
- **source_chapter**：appendix/jinshen-qisha-ge
- **evidence**：quote-index.md DG-Q151
- **applicable_to**：兴工 / 动土 / 修造 / 行船 / 嫁娶避忌
- **caveats**：金神起例需与《星历考原》核对；冲突时以官方神煞考原为准。
- **verified**：false

## DR-06 煞贡、直星、人专作为民间通用吉日层

- **rule_statement**：本书将煞贡、直星、人专列为可用于上官赴任、临政亲民、入学等事的吉日类；可作民间通书“通用吉日”证据层。
- **source_chapter**：appendix/sha-gong-zhi-xing-ren-zhuan
- **evidence**：quote-index.md DG-Q152~DG-Q153
- **applicable_to**：上官 / 赴任 / 入学 / 通用吉日
- **caveats**：不得替代官方黄道、神煞起例；需说明为《董公》口径。
- **verified**：false

## DR-07 选时层高于单看日课

- **rule_statement**：本书反复强调同一日用于不同人、不同事可能吉凶不同，需兼看本命、用事类型、入宅/敬神/发轿等关键时辰；技能应优先路由到“日课+时辰+本命”组合判断。
- **source_chapter**：front/lunlue-shisanze；appendix/zeri-xuanshi-gejue
- **evidence**：quote-index.md DG-Q003~DG-Q004；DG-Q154~DG-Q156
- **applicable_to**：嫁娶 / 移居 / 开张 / 起造 / 出行
- **caveats**：现代输出只作文化说明；不作实际择吉承诺。
- **verified**：false

## DR-08 事项类型必须区分，不可“一日通断”

- **rule_statement**：月日表中同一日常出现“宜安葬但不宜起造婚姻”“宜小修但大用凶”等差异；主 skill 检索时必须带上事项类型，不得只输出单一吉凶。
- **source_chapter**：month/*
- **evidence**：monthly-day-table.md 全表，尤其 `recommended_uses` / `avoid_uses` 字段
- **applicable_to**：所有择日问答
- **caveats**：若用户未说明事项，应先分类为嫁娶、动土、出行、安葬、入宅、开张、上任等，再检索。
- **verified**：false

## DR-09 与官方择日书冲突时降级为旁证

- **rule_statement**：本书属于民间通书系；遇到《协纪辨方书》《星历考原》对神煞、宜忌、起例的不同说法时，本书只能作为旁证或民间异说，不能覆盖官方系统。
- **source_chapter**：全书
- **evidence**：index.md conflict_policy；validation.md
- **applicable_to**：跨书冲突裁判 / master skill routing
- **caveats**：官方书未覆盖的民间用法，也要保留“通书异说”标注。
- **verified**：false

## DR-10 输出必须重写凶验语气

- **rule_statement**：原书大量使用“犯之主官司、损人口、重丧、大凶”等应验语。蒸馏为 skill 时必须改写为“原书以某日列为某类避忌”，禁止直接断言会发生灾祸。
- **source_chapter**：month/*；front/lunlue-shisanze
- **evidence**：monthly-day-table.md `risk_terms` 字段；quote-index.md DG-Q005
- **applicable_to**：安全输出 / 文化风俗说明
- **caveats**：必须附“文化参考，非事实判断”。
- **verified**：false

---

## 月日表调用规则

1. 先用 `mingli-master.selection.v1` 取得目标日期的农历月建、日干支、建除十二值与时辰。
2. 再按 `month_branch + day_type + day_branch` 检索 `monthly-day-table.md`。
3. 输出时引用 `quote-index.md` 或 `monthly-day-table.md` 的 line anchor，不直接复述长段凶验。
4. 若与《协纪辨方书》《星历考原》冲突，以官方书为主，本书降级为“民间通书旁证”。
5. 任何现实决策场景都必须加 caveat：“文化参考，非事实判断”。

---

## D2 状态

- 共 10 条规则。
- 全书 144 个逐日条目已抽入 `monthly-day-table.md`。
- 规则可作为后续 skill 的 reference layer，但尚未完成国图影印校勘。

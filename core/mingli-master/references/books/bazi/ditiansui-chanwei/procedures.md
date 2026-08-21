# 滴天髓阐微 — Procedures

> 本文件抽取《滴天髓阐微》中可被主 skill 调用的可操作流程。
> 字段：`procedure_id` / `name` / `inputs` / `steps` / `outputs` / `tool_dependencies` / `source_chapter` / `verification_status`。
> 所有涉及排盘的步骤一律以 `tool.bazi.paipan` 标注，**不让 LLM 手算**。
> procedure_id 前缀 `DP` = Ditiansui Procedure。

---

## DP-01 旺衰判断主线

- **name**：旺衰精判（本派核心流程）
- **inputs**：YP-01 等价的四柱（年月日时干支）
- **steps**：
  1. 调用 `tool.bazi.paipan` 取得四柱，**不允许手算**。
  2. 由月令判得令／失令（DR-02-06）。
  3. 查日主在四柱地支的根（本气、中气、余气；DR-01-08）。
  4. 看十干性情对日主的支援或克泄（DR-01-07）。
  5. 看合冲解化对根气的影响（DR-01-08、DR-04-05、DR-04-06）。
  6. 综合判定旺衰：得令未必旺、失令未必衰（DR-03-01）。
  7. 输出旺衰倾向（极旺／偏旺／中和／偏弱／极弱）+ 取用方向（扶／抑／从）。
- **outputs**：旺衰倾向 + 取用方向
- **tool_dependencies**：`tool.bazi.paipan`（必需）
- **source_chapter**：tongshen/15-yueling；tongshen/17-shuaiwang
- **verification_status**：pending_verification

## DP-02 通关化战

- **name**：通关化战（相战处理）
- **inputs**：DP-01 的旺衰倾向 + 命局相战格局
- **steps**：
  1. 识别相战：金木相战、水火相战、土木相战、火金相战。
  2. 寻找通关之神：金木战取水（金生水、水生木）；水火战取木（水生木、木生火）；土木战取火（木生火、火生土）；火金战取土（火生土、土生金）。
  3. 校验通关之神：是否得令？是否有根？是否被合冲？
  4. 若通关之神有力 → 战局化解，命局得救。
  5. 若通关之神无力或无 → 转向制伏视角（取制相战二者中较忌之一）。
- **outputs**：通关结论 + 通关之神位置
- **tool_dependencies**：`tool.bazi.paipan`
- **source_chapter**：tongshen/20-tongguan
- **verification_status**：pending_verification

## DP-03 气势格局判断

- **name**：气势格局判断（从化顺反战合）
- **inputs**：DP-01 的旺衰 + 命局气势分布
- **steps**：
  1. 判断是否符合从象（日主无根 + 一神独旺）：从财／从煞／从儿／从势。
  2. 判断是否符合化象（天干五合 + 化神当令）。
  3. 若日主有微根但大势从之 → 假从（DR-06-04）。
  4. 若化神不当令但合而似化 → 假化（DR-06-05）。
  5. 若不符合从化 → 看是否成顺局／反局／战局／合局。
  6. 若皆不成 → 回到普通旺衰扶抑（DP-01）。
- **outputs**：气势格局结论
- **tool_dependencies**：`tool.bazi.paipan`
- **source_chapter**：liuqin/12-congxiang ~ liuqin/19-heju
- **verification_status**：pending_verification

## DP-04 岁运合参

- **name**：大运流年合参
- **inputs**：DP-01 的旺衰 + 大运表 + 待问年份
- **steps**：
  1. 由 `tool.bazi.paipan` 取大运表。
  2. 锁定待问年份的大运柱与流年柱。
  3. 看岁运是否扶用神 / 抑忌神 / 通关 / 引动从化。
  4. 看岁运是否冲克命局根气、用神。
  5. 输出岁运吉凶倾向（不下铁口）。
- **outputs**：岁运分析
- **tool_dependencies**：`tool.bazi.paipan`
- **source_chapter**：liuqin/28-suiyun
- **verification_status**：pending_verification

## DP-05 何知章问答

- **name**：何知章经验断
- **inputs**：DP-01 的旺衰 + 用户问点（富/贵/贫/贱/吉/凶/寿/夭）
- **steps**：
  1. 按 DR-05-05 的判语对应：
     - 富 → 看财气是否通门户
     - 贵 → 看官星是否有理会
     - 寿 → 看五行是否流通
  2. ⚠️ 不作铁口断；只输出"倾向"。
  3. 涉及"夭"绝不作寿命结论；涉及健康转 DP-06。
- **outputs**：经验倾向（带 caveats）
- **tool_dependencies**：`tool.bazi.paipan`
- **source_chapter**：liuqin/05-hezhi-zhang
- **verification_status**：pending_verification

## DP-06 体质倾向（疾病章）

- **name**：体质倾向参考
- **inputs**：DP-01 的旺衰 + 五行偏枯方向
- **steps**：
  1. 按 DR-07-02 干支配脏腑：甲乙肝胆、丙丁心小肠、戊己脾胃、庚辛肺大肠、壬癸肾膀胱。
  2. 看哪一五行偏枯严重 → 对应脏腑体质倾向。
  3. ⚠️ 输出限定为"五行体质倾向"，不作医学诊断。
  4. 遇用户描述具体症状 → 一律建议就医。
- **outputs**：体质倾向（命理层）
- **tool_dependencies**：`tool.bazi.paipan`
- **source_chapter**：liuqin/25-jibing
- **verification_status**：pending_verification

## DP-07 女命模块

- **name**：女命模块
- **inputs**：DP-01 的旺衰（性别=女）
- **steps**：
  1. 取夫星（正官）、子星（食伤）、夫宫（日支）。
  2. 看夫星纯正与否、子星生旺与否。
  3. 现代输出 reframe，不照搬古文"贞淫"等贬义判语。
  4. 与男命同用旺衰扶抑框架。
- **outputs**：女命结构分析
- **tool_dependencies**：`tool.bazi.paipan`
- **source_chapter**：liuqin/06-numing-zhang
- **verification_status**：pending_verification

---

## 流程总图

```text
[用户问题] ─► tool.bazi.paipan ─► DP-01 旺衰判断
                                     │
                                     ├─► DP-02 通关化战（如有相战）
                                     ├─► DP-03 气势格局（如不符合常规）
                                     ├─► DP-04 岁运合参
                                     ├─► DP-05 何知章经验问答
                                     ├─► DP-06 体质倾向（限制使用）
                                     └─► DP-07 女命模块（性别=女）
```

---

**说明**：所有事实层步骤均由 `tool.bazi.paipan` 完成。本 pack 作为旺衰派精修源；月令格局精修需转 `bazi/ziping-zhenquan`，调候用神精修需转 `bazi/qiongtong-baojian`。Batch D1 框架抽取，7 条流程。

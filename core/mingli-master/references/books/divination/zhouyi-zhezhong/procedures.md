# 御纂周易折中 — Procedures

> 本文件抽取《御纂周易折中》之解卦框架与啟蒙蓍法流程。
> 字段：`procedure_id` / `name` / `inputs` / `steps` / `outputs` / `tool_dependencies` / `source_chapter` / `verification_status`。
> 全部 `pending_verification`。
> **核心约束**：本书不涉占断实务（金钱卦 / 体用占法）；蓍法实操由 `tool.divination.qiguagua` 处理；**严禁** LLM 手算揲蓍。
> procedure_id 前缀 `ZZP` = ZheZhong Procedure。

---

## ZZP-01 解卦总流程（义理解卦）

- **inputs**：给定卦（卦名 / 上下卦 / 六爻爻辞）+ 解读问题
- **steps**：
  1. **识卦时**：由卦名 / 卦象判定卦时（屯之难、需之待、否之闭等）。
  2. **辨卦德**：上下两卦德合（如坎下离上 → 既济）。
  3. **定卦主**：识本卦之主爻（多为五爻或独成卦义之爻）。
  4. **逐爻析义**：按 ZZP-02 分析每爻。
  5. **综合卦义**：综时、德、主三层得卦总义。
  6. **查反对 / 错卦**：参看综卦（反对）与错卦义。
  7. **集说参证**：查程傳 / 本義 / 集說 / 案语四层之异同。
- **outputs**：卦的义理解读
- **tool_dependencies**：—（义理推演由 LLM）
- **source_chapter**：vol-00/yi-li 总论 + vol-01 ~ vol-12 各卦
- **verification_status**：pending_verification

## ZZP-02 爻辞解读流程

- **inputs**：给定爻（爻位 + 阴阳 + 爻辞）
- **steps**：
  1. **识时位**：初为始 / 二为臣民 / 三为公卿 / 四为大夫 / 五为君 / 上为亢。
  2. **判当位 / 不当位**：阳居阳 / 阴居阴位为当（多吉）；反之不当。
  3. **判中**：二、五为中；得中（刚中 / 柔中）多吉。
  4. **判中正**：得中又当位（六二、九五）为大吉之爻。
  5. **看应**：与对应爻（一四 / 二五 / 三上）阴阳是否相应。
  6. **看比**：与相邻爻关系（亲 / 敌）。
  7. **综合得爻德 / 爻才**：刚柔 + 时位 + 应比 → 该爻吉凶悔吝。
- **outputs**：爻的义理解读 + 吉凶判断
- **tool_dependencies**：—
- **source_chapter**：vol-00/yi-li + 各卦爻辞下注
- **verification_status**：pending_verification

## ZZP-03 揲蓍成卦法（啟蒙第三篇）

- **inputs**：占问主题（一事一占）
- **steps**：
  1. 取蓍草 50 根，去 1 不用，余 49 根。
  2. **第一变**：分二（任意分两堆）→ 挂一（右堆取一根挂左手小指）→ 揲四（两堆各以四根为一组揲数）→ 归奇（余数挂左手）。三步后得 9 或 5。
  3. **第二变**：以余下 40 或 44 根再分二、挂一、揲四、归奇；得 8 或 4。
  4. **第三变**：以余下再变；得 8 或 4。
  5. 三变成一爻：合三变之归奇得 25 / 21 / 17 / 13，配 9（老阳）/ 8（少阴）/ 7（少阳）/ 6（老阴）。
  6. 凡 18 变成 6 爻一卦。
- **outputs**：本卦六爻 + 老阴老阳之动爻
- **tool_dependencies**：`tool.divination.qiguagua`（**强制**：揲蓍实操禁止 LLM 手算）
- **source_chapter**：vol-20/qimeng-3-mingshi
- **verification_status**：pending_verification

## ZZP-04 变占法（啟蒙第四篇 / 朱熹折中）

- **inputs**：揲蓍所得本卦六爻 + 动爻
- **steps**：
  1. **数动爻**：统计 6（老阴）+ 9（老阳）的总数。
  2. **按动爻数定占断对象**：
     - 0 动（六爻全静）→ 占本卦彖辞（卦辞）
     - 1 动 → 占本卦变爻爻辞
     - 2 动 → 占本卦二变爻、以上爻为主
     - 3 动 → 占本卦 + 变卦彖辞、本卦为主
     - 4 动 → 占变卦二不变爻、以下爻为主
     - 5 动 → 占变卦不变爻
     - 6 动（六爻全变）→ 占之卦（变卦）彖辞
     - 例外：乾全变占"用九"、坤全变占"用六"
  3. **综合判断**：依变占对象之爻辞 / 卦辞综合得占断结果。
- **outputs**：占断对象 + 占辞解读
- **tool_dependencies**：—（变占规则由 LLM 推理；动爻数由 ZZP-03 已得）
- **source_chapter**：vol-21/qimeng-4-kaobianzhan
- **verification_status**：pending_verification

## ZZP-05 河图洛书解读

- **inputs**：河图 / 洛书图
- **steps**：
  1. **河图**：辨"天数 1 3 5 7 9（白圈）"与"地数 2 4 6 8 10（黑圈）"。
  2. **天地数和**：天数 25、地数 30，合 55。
  3. **生成数**：1-2-3-4-5 为生数，6-7-8-9-10 为成数。
  4. **洛书**：辨九数纵横皆 15（戴九履一、左三右七、二四为肩、六八为足）。
- **outputs**：图书数理解读
- **tool_dependencies**：—（图理推演）
- **source_chapter**：vol-18/qimeng-1-bentu
- **verification_status**：pending_verification

## ZZP-06 折中阅读流程（学习方法论）

- **inputs**：本书内容
- **steps**：
  1. **第一层 程傳**：先读程颐义理解卦（重事理人事）。
  2. **第二层 本義**：再读朱熹兼象数与卜筮之解（重原义）。
  3. **第三层 集說**：参考宋元明诸家说，得多角度。
  4. **第四层 案語**：读康熙诸臣折中之议，得官方立场。
- **outputs**：对该卦 / 爻 / 系传段的全面理解
- **tool_dependencies**：—
- **source_chapter**：凡例 + 全书
- **verification_status**：pending_verification

## ZZP-07 路由（按问题类型分流）

- **inputs**：用户问题
- **steps**：
  1. **64 卦义理 / 卦爻辞** → ZZP-01 + ZZP-02 + chapter-map 卷一至卷十二
  2. **繫辭传义理** → quote-index ZZQ-04-* + chapter-map 卷十三至十五
  3. **説卦取象 / 序卦杂卦** → terms.md 八卦象义 + rules.md ZZR-03-* + chapter-map 卷十六十七
  4. **河图洛书数理** → ZZP-05 + chapter-map 卷十八
  5. **加一倍法 / 先天图** → terms.md + chapter-map 卷十九（兼参 `huangji-jingshi`）
  6. **揲蓍成卦** → ZZP-03 + `tool.divination.qiguagua`
  7. **变占法** → ZZP-04
  8. **占断实务（金钱卦 / 体用）** → 转 `zengshan-buyi` / `meihua-yishu`
  9. **元会运世数理** → 转 `huangji-jingshi`
  10. **个人命术** → 转 `bazi/*`
- **outputs**：路由到的子流程或外部 pack
- **tool_dependencies**：—
- **source_chapter**：—（架构性）
- **verification_status**：pending_verification

---

## 现代使用边界

- **ZZP-01 解卦**：义理解卦不预测具体吉凶事件；多用于哲学 / 修身 / 决策思辨参考。
- **ZZP-03 揲蓍**：实操**严禁** LLM 手算；必须 `tool.divination.qiguagua`。
- **ZZP-04 变占**：变占规则虽可由 LLM 推理，但占辞解读应配合具体语境。
- **ZZP-05 河图洛书**：作为象数文化参考；不可作为现代数理证明。
- **占断不替代修身**：本书核心立场（ZZR-06-06）；占断为辅、修身为本；不应过度依赖占卜决疑。
- **本书不涉占断实务**：必须明确分流到 `zengshan-buyi` / `meihua-yishu`。

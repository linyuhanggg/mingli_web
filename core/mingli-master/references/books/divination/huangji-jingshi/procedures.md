# 皇极经世书 — Procedures

> 本文件抽取《皇极经世书》可路由的数理 / 义理操作流程。
> 字段：`procedure_id` / `name` / `inputs` / `steps` / `outputs` / `tool_dependencies` / `source_chapter` / `verification_status`。
> 全部 `pending_verification`。
> **核心约束**：所有元会运世数表查询、年甲子推算、卦气配年等事实层运算，一律调用 `tool.divination.huangji`；**严禁 LLM 手算**。
> procedure_id 前缀 `HP` = Huangji Procedure。

---

## HP-01 元会运世年代换算

- **inputs**：
  - 给定公历年份（如 2026 年）
  - 或给定经世表中"某会某运某世某年"
- **steps**：
  1. 以邵雍元始甲辰（公元前 2357 年）为基准。
  2. 计算该年距元始的纪年数。
  3. 按 1 元 = 129600 年、1 会 = 10800 年、1 运 = 360 年、1 世 = 30 年逐级分解。
  4. 落到具体"某元某会某运某世第几年"。
  5. 反向：给定"某会某运某世某年"，按上式累加得公历年。
- **outputs**：元会运世坐标 + 公历年对照
- **tool_dependencies**：`tool.divination.huangji`（**强制**：年代换算属事实层运算，禁止 LLM 手算）
- **source_chapter**：vol-05 ~ vol-10（经世表 + HR-09-02 元始甲辰）
- **verification_status**：pending_verification

## HP-02 卦气配年查询

- **inputs**：给定公历年份 / 经世坐标
- **steps**：
  1. 由 HP-01 得经世坐标。
  2. 按本书经世表查该年所配六十四卦之卦。
  3. 按月气查该月所配十二消息卦（复 / 临 / 泰 / 大壮 / 夬 / 乾 / 姤 / 遯 / 否 / 观 / 剥 / 坤）。
- **outputs**：年配卦 + 月配卦
- **tool_dependencies**：`tool.divination.huangji`（卦气表查询事实层）
- **source_chapter**：vol-05 ~ vol-10
- **verification_status**：pending_verification

## HP-03 先天图解读

- **inputs**：给定卦或起卦数
- **steps**：
  1. **先天数**：乾 1、兑 2、离 3、震 4、巽 5、坎 6、艮 7、坤 8。
  2. **加一倍法**：以二进位逐爻递推（一爻 2 / 二爻 4 / 三爻 8 / 六爻 64）。
  3. **方圆图定位**：外圆按一年阳气消长（复 → 乾 → 姤 → 坤）、内方按地理方位。
  4. **先后天方位区分**：先天乾南坤北、后天离南坎北。
- **outputs**：卦在先天图中的位置 + 阳气状态 + 方位
- **tool_dependencies**：—（义理推演由 LLM；具体起卦应由 `tool.divination.qiguagua` 处理）
- **source_chapter**：vol-13（觀物外篇上）
- **verification_status**：pending_verification

## HP-04 声音律吕配数

- **inputs**：给定汉字 / 音韵
- **steps**：
  1. 判该字声母（开发收闭哪类）。
  2. 判该字韵母（天声 10 类哪类）。
  3. 判平上去入四调。
  4. 按邵雍声音唱和图查配数。
- **outputs**：该字的声音律吕坐标 + 数理对应
- **tool_dependencies**：`tool.divination.huangji`（声音律吕表查询）
- **source_chapter**：vol-11
- **verification_status**：pending_verification

## HP-05 观物（义理推演）

- **inputs**：所观对象（事 / 物 / 现象）
- **steps**：
  1. **去情累**：先放下"以我观物"的主观偏见。
  2. **以物观物**：从物自身的性、命、理出发观察。
  3. **得理通**：物理通则与天地之理合一。
  4. **反观**：以观所得反推主体心法（"心为太极"）。
- **outputs**：对所观对象的义理认识 + 反观所得的心法
- **tool_dependencies**：—（属义理思辨，无事实层运算）
- **source_chapter**：vol-13 ~ vol-14
- **verification_status**：pending_verification

## HP-06 体用相须解卦

- **inputs**：给定卦
- **steps**：
  1. 识别本卦体用：乾坤为体、坎离为用；或按问占主体（体）/ 客体（用）划分。
  2. 体用相须：体立而用行；用行而体显。
  3. **注意**：与梅花易数"体用生克吉凶"占法不同——此处仅是义理识别，非占断。
- **outputs**：卦的体用关系 + 义理解释
- **tool_dependencies**：—
- **source_chapter**：vol-13
- **verification_status**：pending_verification

## HP-07 路由（按问题类型分流）

- **inputs**：用户问题
- **steps**：
  1. **元会运世数理 / 年代换算** → HP-01 + HR-01-* + `tool.divination.huangji`
  2. **卦气配年** → HP-02 + `tool.divination.huangji`
  3. **先天易理 / 方位** → HP-03 + HR-04-*
  4. **声音律吕** → HP-04 + `tool.divination.huangji`
  5. **观物义理 / 心法** → HP-05 + HR-05-*
  6. **个人占断 / 卜筮** → 不在本 pack；转 `meihua-yishu` / `zengshan-buyi`
  7. **个人命术** → 不在本 pack；转 `bazi/*`
  8. **易学义理 / 经传** → 转 `divination/zhouyi-zhezhong`
  9. **国运 / 历史预测** → 给出"术数史观文化参考"caveats，不做实证预测
- **outputs**：路由到的具体子流程或外部 pack
- **tool_dependencies**：—
- **source_chapter**：—（架构性）
- **verification_status**：pending_verification

---

## 现代使用边界

- **HP-01 年代换算**：仅为术数符号系统，不可与现代天文学 / 历史学时间体系混同。
- **HP-02 卦气配年**：用于文化 / 学术参考，不应据以预测国运、政治、经济。
- **HP-03 先天图**：作为先天易学源头文献参考；具体卜筮起卦应由 `tool.divination.qiguagua` 处理。
- **HP-05 观物**：义理思辨，可指导认知方法；不应作为占断 / 决策直接依据。
- **HP-07 路由**：本书不涉个人卜筮 / 命术，必须明确分流。
- **全局禁止**：LLM 手算元会运世年表 / 卦气表 / 声音律吕表。

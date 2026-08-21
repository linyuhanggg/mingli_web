# 梅花易数 — Procedures

> 本文件抽取《梅花易数》中可被主 skill 调用的可操作流程。
> 字段：`procedure_id` / `name` / `inputs` / `steps` / `outputs` / `tool_dependencies` / `source_chapter` / `verification_status`。
> 所有涉及起卦、排互卦、排变卦的步骤一律以 `tool.divination.qiguagua` 标注，**禁止 LLM 手算**。
> procedure_id 前缀 `MP` = Meihua Procedure。

---

## MP-01 数字起卦（卦以八除、爻以六除）

- **name**：先天数字起卦法
- **inputs**：上卦数 + 下卦数（用户报数 / 字数 / 物数 / 年月日时数）
- **steps**：
  1. 调用 `tool.divination.qiguagua`，传入 `mode=xian-tian`，输入上下卦数与动爻总数。
  2. 工具按 MR-02-01 与 MR-02-02 计算上下卦与动爻位。
  3. 工具返回本卦 / 互卦 / 变卦三组卦象。
  4. **不允许** LLM 自行做 "数 mod 8" 或 "数 mod 6" 的算术；事实层一律由工具产出。
- **outputs**：本卦 / 互卦 / 变卦 + 动爻位
- **tool_dependencies**：`tool.divination.qiguagua`（必需）
- **source_chapter**：xsly-1/gua-yibachu, xsly-1/yao-yiliuchu
- **verification_status**：pending_verification

## MP-02 互卦取法

- **name**：互卦取法
- **inputs**：本卦的六爻（含上下卦标识）
- **steps**：
  1. 由 `tool.divination.qiguagua` 在 MP-01 中一并返回互卦（取重卦二三四爻为下互、三四五爻为上互）。
  2. 若本卦为乾或坤，按 MR-02-03 取变卦之互。
  3. **不允许** LLM 手算互卦。
- **outputs**：互卦
- **tool_dependencies**：`tool.divination.qiguagua`
- **source_chapter**：xsly-1/hugua-qili
- **verification_status**：pending_verification

## MP-03 年月日时起卦

- **name**：年月日时起卦
- **inputs**：年（地支序数）+ 月 + 日 + 时（地支序数）
- **steps**：
  1. 输入用户出生 / 起卦时刻（公历或农历，含时辰）。
  2. 由 `tool.divination.qiguagua` 转换为对应的地支序数与年月日时数。
  3. 由工具计算：上卦 = (年 + 月 + 日) mod 8、下卦 = (年 + 月 + 日 + 时) mod 8、动爻 = (年 + 月 + 日 + 时) mod 6。
  4. 工具返回本卦 / 互卦 / 变卦。
- **outputs**：本卦 / 互卦 / 变卦 + 动爻
- **tool_dependencies**：`tool.divination.qiguagua`
- **source_chapter**：xsly-1/nianyueri-qili
- **verification_status**：pending_verification

## MP-04 字占 / 声音占 / 物数占

- **name**：因事起卦（字数 / 声音 / 物数 / 丈尺等）
- **inputs**：起卦事件描述（字数 / 闻声次数 / 物数 / 丈尺数 / 颜色 等）
- **steps**：
  1. 用户提供原始数据（如字数、声音次数、物数）。
  2. 调用 `tool.divination.qiguagua`，传入起卦类型与原始数据。
  3. 工具按本书各起例（一字至十一字、丈尺占、尺寸占、声音占、物数占）的具体规则取上下卦与动爻。
  4. 工具返回本卦 / 互卦 / 变卦。
- **outputs**：本卦 / 互卦 / 变卦
- **tool_dependencies**：`tool.divination.qiguagua`（必需，含起例参数）
- **source_chapter**：xsly-1/zizhan, xsly-1/shengyin-zhanli, xsly-1/wushu-zhanli, xsly-1/zhangchi-zhan, xsly-1/chicun-zhan
- **verification_status**：pending_verification

## MP-05 后天端法起卦（物 + 方位）

- **name**：后天端法（物为上卦、方位为下卦）
- **inputs**：所见之物（取八卦类象）+ 方位（八方对应卦）+ 时辰
- **steps**：
  1. 根据所见之物，由 terms.md §4 八卦万物属类映射出上卦。
  2. 根据方位（东=震、东南=巽、南=离、西南=坤、西=兑、西北=乾、北=坎、东北=艮）映射出下卦。
  3. 调用 `tool.divination.qiguagua`，传入 `mode=hou-tian`、上下卦、时辰，工具计算动爻 = (上 + 下 + 时) mod 6。
  4. 工具返回本卦 / 互卦 / 变卦。
- **outputs**：本卦 / 互卦 / 变卦
- **tool_dependencies**：`tool.divination.qiguagua`
- **source_chapter**：xsly-2/wugua-qili-duanfa
- **verification_status**：pending_verification

## MP-06 体用占断流程

- **name**：体用生克占断
- **inputs**：MP-01~05 任一所得之本卦 / 互卦 / 变卦 + 动爻
- **steps**：
  1. 由动爻位确定体用：含动爻一卦为用，不含动爻一卦为体（MR-04-01）。
  2. 查体卦 / 用卦的五行（MR-01-03 八宫五行）。
  3. 判定体用关系（MR-04-02）：用生体 / 体生用 / 用克体 / 体克用 / 比和。
  4. 查时令（春夏秋冬 / 四季月）以判体用衰旺（MR-01-04 / MR-01-05 / MR-05-02）。
  5. 看互卦判事中曲折（MR-04-04）。
  6. 看变卦判事终归宿（MR-04-04 / MR-04-06）。
  7. 综合卦象类象（terms.md §4）补充取义。
  8. 输出占断 + 应期（MR-05-01）+ caveats。
- **outputs**：占断结论（含吉凶 / 程度 / 应期 / 注意事项）
- **tool_dependencies**：`tool.divination.qiguagua` 提供卦体；五行映射可由工具或 LLM 检索 terms.md
- **source_chapter**：tyk-1/tiyong-shengke-jixiong, tyk-3/keying-zhi-qi
- **verification_status**：pending_verification

## MP-07 十类问占应用流程

- **name**：按问占类型取占断框架
- **inputs**：用户问占类型（天时 / 人事 / 家宅 / 婚姻 / 生产 / 求财 / 交易 / 出行 / 行人 / 谒见 / 失物 / 疾病 / 官讼 / 坟墓）+ MP-06 的占断主轴
- **steps**：
  1. 识别问占类型，路由到 rules.md MR-07~MR-12 对应规则。
  2. 在 MP-06 主轴基础上，按问占类型加入特定取象（如天时占的坎雨离晴；婚姻占的体我用对方；生产占的阳卦男阴卦女）。
  3. 按问占类型加入 caveats（如疾病占必加"不替代医学"、生产占必加"以现代产检为主"、官讼占必加"不替代法律意见"、坟茔占必加"以法规为主"）。
  4. 输出最终占断 + caveats。
- **outputs**：分类问占结论 + caveats
- **tool_dependencies**：`tool.divination.qiguagua`
- **source_chapter**：dz-1/* ~ dz-4/*
- **verification_status**：pending_verification

## MP-08 占例对照（观梅 / 牡丹 / 牛鸣等）

- **name**：经典占例对照
- **inputs**：用户场景描述
- **steps**：
  1. 检索 chapter-map.md `xsly-3/*` 经典占例条目，找到结构相似的占例。
  2. 比对类象、起卦机、体用关系。
  3. 用作类比说明，**不直接套用**结论。
- **outputs**：占例引用 + 类比说明
- **tool_dependencies**：—（仅文档检索）
- **source_chapter**：xsly-3/*
- **verification_status**：pending_verification

## MP-09 起卦机辨别

- **name**：起卦时机判断
- **inputs**：用户提议起卦的事
- **steps**：
  1. 按 MR-02-04 判定可否起卦：江河山石、未成之物、强求无故 → 不可起卦。
  2. 若不可，提示用户改换起卦机或暂不起卦。
  3. 若可起卦，进入 MP-01~05 流程。
- **outputs**：可 / 不可 + 原因
- **tool_dependencies**：—
- **source_chapter**：xsly-1/zhan-jingwu
- **verification_status**：pending_verification

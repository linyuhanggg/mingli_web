# 華山陳希夷先生飛星紫微斗數原旨 — Procedures

> 全部流程都依赖完整紫微事实层。严禁 LLM 手算农历、干支、命盘、星曜、四化、大限、流年、小限。

## FZ-P01 Late Observation Pack Loading Workflow

- **purpose**: 决定何时加载本 pack。
- **steps**:
  1. 确认用户问题属于紫微或可由紫微旁证的问题。
  2. 检查是否已有 `calendar_normalization` 与 `tool.ziwei.bindisk` 等价输出。
  3. 若问题只是基础命盘、星曜定义、安星法，先使用 `ziwei-doushu-quanshu` 与 `taiwei-fu`，不加载本 pack。
  4. 若问题涉及当前事件、方位、住宅/祖坟/邻里、亲属假借、红鸾大耗、天刑巨门等，再加载本 pack。
  5. 输出时标注“本书观测层/旁证层”，不让本 pack 覆盖主盘结论。
- **tool_dependency**: `tool.ziwei.bindisk`
- **source_chapter**: page-002 to page-005, page-030, page-997
- **verified**: true

## FZ-P02 Environment And Direction Cross-Check

- **purpose**: 用本书方法检查命盘方位与阴阳宅/邻里环境是否互证。
- **steps**:
  1. 取得紫微盘的十二宫、流年星煞、限运所到宫位。
  2. 取得实际环境事实：居住地/祖坟坐向、房屋布局、四邻方位、是否有道路、水沟、树木、庙宇、坑洼、拆修、动土等。
  3. 将命盘宫位方位与实际方位对齐；不能对齐则停止此流程。
  4. 检查白虎、喪門、弔客、歲破、大耗、流羊、红鸾天喜、祿存、陀罗、巨门等在该方的传统象义。
  5. 只输出“可核验的方位旁证”，并列出需要用户确认的现实观察点。
- **tool_dependency**: `tool.ziwei.bindisk` + 用户提供方位/环境事实
- **source_chapter**: page-008 to page-010, page-018 to page-023, page-854
- **verified**: true

## FZ-P03 Twelve-Palace Borrowing Workflow

- **purpose**: 回答外孙、岳父母、子女配偶、叔伯等基础十二宫未直列的亲属问题。
- **steps**:
  1. 先用标准十二宫定位命主本人、父母、兄弟、夫妻、子女等基础关系。
  2. 若问题对象不在标准宫位中，加载本 pack 的假借法。
  3. 按本书示例：外孙由迁移宫与命垣对照并用三合；岳父母、子女配偶、叔伯等按相关宫位顺逆推借。
  4. 检查借用宫的主星、辅星、煞曜、四化、限运和三方四正。
  5. 输出必须说明“这是《斗数观测录》假借法”，并把置信度降一级。
- **tool_dependency**: `tool.ziwei.bindisk`
- **source_chapter**: page-025 to page-030, page-997
- **verified**: true

## FZ-P04 Red-Luan-Da-Hao Check

- **purpose**: 避免把所有运势机械说成财务/回款，只在盘面确有触发时使用红鸾大耗。
- **steps**:
  1. 检查命盘、大限、流年、小限是否有红鸾、天喜、咸池、大耗同宫/会照/入相关宫。
  2. 确认用户问题是否涉及婚恋、家庭、家眷移动、喜庆、人情支出、关系波动或伴侣健康。
  3. 若二者都满足，才引用本书红鸾大耗案例群。
  4. 输出时同时列出可能的“喜事/移动/耗费/关系波动”分支，不直接定为单一结论。
  5. 若盘面无该组合，禁止套用“花钱、回款、财务动静”等模板。
- **tool_dependency**: `tool.ziwei.bindisk`
- **source_chapter**: page-012, page-037 to page-038, page-895 to page-902
- **verified**: true

## FZ-P05 Ju-Men Tian-Xing Legal/Conflict Check

- **purpose**: 判断法律、公门、争执、口舌类问题时如何使用巨门/天刑旁证。
- **steps**:
  1. 检查巨门、天刑、官符、流羊、化忌等是否落命身、官禄、迁移、流年相关宫位。
  2. 确认用户问题是否本来就涉及法律、公门、合同、争执、举报、警署、法院等事实。
  3. 若无现实争议事实，只能提示“传统象义有口舌/规则/公门意味”，不得断官非。
  4. 若事实与盘象同时成立，输出为风险清单和留痕建议，不替代法律意见。
- **tool_dependency**: `tool.ziwei.bindisk`
- **source_chapter**: page-016 to page-018, page-870, page-895, page-920
- **verified**: true

## FZ-P06 Event Divination With One-Matter-One-Chart

- **purpose**: 使用本书“一物一事均有身命”的实验法处理事件占测。
- **steps**:
  1. 优先判断该问题是否更适合六爻、梅花、六壬、奇门、太乙等本门占事体系。
  2. 若用户明确要用斗数占事，取得起课时间、地点、时区，并完成 calendar normalization。
  3. 用 deterministic adapter 排出事件斗数盘；不得手算。
  4. 以该课的身命、十二宫、三方四正作为“一事全局”观察，不另分主客用神。
  5. 输出时标注“本书实验法/不作为紫微主流优先流程”。
- **tool_dependency**: `calendar_normalization` + `tool.ziwei.bindisk`
- **source_chapter**: page-030 to page-031
- **verified**: true

## FZ-P07 Delivery Evidence Split

- **purpose**: 让命理输出不再生硬模板化，也不把晚近断语当事实。
- **steps**:
  1. 先列事实层：时间、历法、盘面、星曜、限运、方位等。
  2. 再列原书依据：引用本 pack 的 rule_id 与页码。
  3. 再列现代解释：把“死、病、刑、淫”等传统词转成风险、关系、健康/安全/法律维度。
  4. 最后列不确定性和需要核验的现实信息。
  5. 避免固定模板：没有红鸾大耗就不要说财务/收尾/回款；没有巨门天刑就不要说口舌官非。
- **tool_dependency**: none
- **source_chapter**: page-010 to page-011, page-893
- **verified**: true

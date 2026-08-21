# 葬书 — Procedures

> 严格禁止 LLM 手算风水坐向、罗盘度数；本文件只声明流程与工具依赖。
> 所有 verified 为 false。

## P-01: 寻势察形定全气

- **purpose**: 按"势来形止"原则定位全气之地
- **steps**:
  1. 勘察千尺以上来势（需要工具：tool.fengshui.terrain）
  2. 勘察百尺以下落形（需要工具：tool.fengshui.terrain）
  3. 判断势与形是否顺合
  4. 排除"五不可葬"（童、断、石、过、独）
- **tool_dependency**:
  - tool.fengshui.terrain（地形勘测；本工具尚未实装时，结果只作概念演示）
- **source_chapter**: neipian-3, neipian-4
- **verified**: false

## P-02: 支垄之辨与葬位选择

- **purpose**: 区分平地"支"与山地"垄"，按规则选葬位
- **steps**:
  1. 判断龙脉为支（平地隐隆）还是垄（山地起伏）（需要工具：tool.fengshui.terrain）
  2. 支葬其巓、垄葬其麓
  3. 配合形势顺逆排除花假
- **tool_dependency**:
  - tool.fengshui.terrain
- **source_chapter**: waipian-1
- **verified**: false

## P-03: 四兽辨认与穴位环境核查

- **purpose**: 辨认青龙白虎朱雀玄武四方山水形势
- **steps**:
  1. 标定穴位坐向（需要工具：tool.fengshui.luopan，**严禁 LLM 手算**）
  2. 按坐向辨左右前后四兽形势
  3. 排除虎蹲（含尸）、龙踞（嫉主）、玄武不垂、朱雀不舞四凶
- **tool_dependency**:
  - tool.fengshui.luopan（罗盘工具，必须）
  - tool.fengshui.terrain（地形勘测）
- **source_chapter**: waipian-4
- **verified**: false

## P-04: 八方葬法形势核查

- **purpose**: 按八方坐向核查形势配合是否合规
- **steps**:
  1. 由 tool.fengshui.luopan 取得坐向（**严禁 LLM 手算**）
  2. 查阅 R-13 中对应方位的"势欲—形欲"要求
  3. 结合 R-14 三吉六凶综合评定
- **tool_dependency**:
  - tool.fengshui.luopan
- **source_chapter**: zapian-xia
- **verified**: false

## P-05: 土质核查（五色五备）

- **purpose**: 评估穴土是否符合"细而坚、润而不泽、备具五色"
- **steps**:
  1. 现场取样（需要工具：tool.fengshui.soil_sample，未实装则跳过）
  2. 判断是否水泉砂砾、干如穴粟、湿如刲肉等凶土特征
- **tool_dependency**:
  - tool.fengshui.soil_sample（待定）
- **source_chapter**: waipian-3
- **verified**: false

> **现代使用边界**：以上流程仅作传统形势派文献的工具化映射，不构成对当代墓地选址、迁葬、风水改运的现实建议。

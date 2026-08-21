# 青囊序 — Procedures

> 严格禁止 LLM 手算理气水法（罗经度数、二十四山局位、生旺退神方位）；只声明工具依赖。

## P-01: 看雌雄认金龙察血脉

- **purpose**: 按杨公养老法实施雌雄水法总纲
- **steps**:
  1. 由 tool.fengshui.luopan 取得来山去水方位（**严禁 LLM 手算**）
  2. 判断金龙动否（须地形辅证）
  3. 察血脉认来龙、二水夹处认主龙
  4. 三叉水位辨宗法
- **tool_dependency**:
  - tool.fengshui.luopan
  - tool.fengshui.terrain
- **source_chapter**: s1-cixiong
- **verified**: false

## P-02: 二十四山顺逆四十八局推演

- **purpose**: 按二十四山分顺逆推 48 局
- **steps**:
  1. 由 tool.fengshui.luopan 定坐山与朝向（**严禁 LLM 手算**）
  2. 由工具按二十四山顺逆出局
  3. 与净阴净阳法合参
- **tool_dependency**:
  - tool.fengshui.luopan
- **source_chapter**: s3-24shan
- **verified**: false

## P-03: 生旺水法与城门核查

- **purpose**: 实施生旺水法、城门三八相遇判断
- **steps**:
  1. 由 tool.fengshui.luopan 与 tool.fengshui.terrain 标定明堂、朝水、城门方位
  2. 检查水城门是否在三八相遇位
  3. 排除直射直流（R-07 凶象）
- **tool_dependency**:
  - tool.fengshui.luopan
  - tool.fengshui.terrain
- **source_chapter**: s5-shengwang
- **verified**: false

## P-04: 进退神水法判断

- **purpose**: 判断水流为进神还是退神
- **steps**:
  1. 由 tool.fengshui.luopan 取得水来去之方位与五行
  2. 按 R-08 计算生入克入或生出克出（**严禁 LLM 手算**，由工具完成）
  3. 出具进退判断
- **tool_dependency**:
  - tool.fengshui.luopan
- **source_chapter**: s6-jintui
- **verified**: false

## P-05: 公位水神核查

- **purpose**: 按八卦配三男三女查公位水神
- **steps**:
  1. 由 tool.fengshui.luopan 取得诸方位水之纳支
  2. 按 R-09 配公位（长/中/少男）
  3. 按 R-10 综合山水主分（水主财禄山主人丁）
- **tool_dependency**:
  - tool.fengshui.luopan
- **source_chapter**: s7-gongwei
- **verified**: false

> **现代使用边界**：以上流程仅作传统理气水法的工具化映射；本 pack 不直接给出公位人事吉凶判定。

# 青囊经 — Procedures

> 严格禁止 LLM 手算理气推演（卦运、飞星、六甲、八门）；只声明工具依赖。verified 全 false。

## P-01: 因形察气流程

- **purpose**: 按"因形察气"原则推演形气配合
- **steps**:
  1. 勘察山川形势（需要工具：tool.fengshui.terrain）
  2. 由 tool.fengshui.luopan 获取坐向方位（**严禁 LLM 手算**）
  3. 按 R-05/R-08 判断外气行形与内气止生
- **tool_dependency**:
  - tool.fengshui.luopan
  - tool.fengshui.terrain
- **source_chapter**: zhong-huaji, xia-huacheng
- **verified**: false

## P-02: 顺五兆—用八卦—排六甲—布八门

- **purpose**: 实施下卷"四审"框架（审象、审位、审运、审气）
- **steps**:
  1. 顺五兆（审五行兆象）
  2. 用八卦（审八方位次，由 tool.fengshui.luopan 提供，**严禁手算**）
  3. 排六甲（审六十甲子运，由 tool.fengshui.calendar 提供）
  4. 布八门（审八方风气，由 tool.fengshui.luopan 提供）
- **tool_dependency**:
  - tool.fengshui.luopan
  - tool.fengshui.calendar（待定）
- **source_chapter**: xia-huacheng
- **verified**: false

## P-03: 推五运定六气

- **purpose**: 配合岁时节令以扶地理用法
- **steps**:
  1. 推五运（依五纪盈虚审岁，由 tool.fengshui.calendar 提供）
  2. 定六气（依六气代谢审令）
  3. 与 P-02 结果合参
- **tool_dependency**:
  - tool.fengshui.calendar（待定，不可由 LLM 手算）
- **source_chapter**: xia-huacheng
- **verified**: false

## P-04: 阴阳相见之冲和判断

- **purpose**: 判断山水朝应是否得冲和之正
- **steps**:
  1. 由 tool.fengshui.luopan 取得来山去水方位
  2. 按 R-06 判断阴阳是否相见
  3. 检验是否得冲和之正（具体卦运推演由工具完成）
- **tool_dependency**:
  - tool.fengshui.luopan
- **source_chapter**: zhong-huaji
- **verified**: false

> **现代使用边界**：以上流程仅作传统理气派文献的工具化映射；本 pack 不直接做卦运、飞星、奇门式推演。

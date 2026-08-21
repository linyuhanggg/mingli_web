# 撼龙经 — Procedures

> 严格禁止 LLM 手算坐向、罗经度数；只声明流程与工具依赖。verified 全 false。

## P-01: 寻龙望气与顿伏认识

- **purpose**: 实施"望气—寻脉—顿伏—剥换"寻龙总流程
- **steps**:
  1. 实地观察云霓生处（需要工具：tool.fengshui.terrain）
  2. 沿脉寻顿伏、辨曲转生枝
  3. 记录星峰类型与剥换次数
- **tool_dependency**:
  - tool.fengshui.terrain
- **source_chapter**: zonglun
- **verified**: false

## P-02: 九星辨认

- **purpose**: 按九星正形与变形辨认龙脉星峰
- **steps**:
  1. 由地形勘测取山形（需要工具：tool.fengshui.terrain）
  2. 按 R-03/R-05/R-06/R-09 等比对九星正形/变形
  3. 由 tool.fengshui.luopan 标定星峰方位（**严禁 LLM 手算**）
- **tool_dependency**:
  - tool.fengshui.terrain
  - tool.fengshui.luopan
- **source_chapter**: tanlang, jumen, lucun, wenqu, lianzhen, wuqu, pojun, zuofu, youbi
- **verified**: false

## P-03: 平洋寻龙

- **purpose**: 在平地按"高水一寸即山、低水一寸即平"原则寻龙
- **steps**:
  1. 勘察细微高程差（需要工具：tool.fengshui.terrain）
  2. 寻"两水夹流是龙脊"
  3. 辨右弼星之隐曜行
- **tool_dependency**:
  - tool.fengshui.terrain
- **source_chapter**: youbi, zonglun
- **verified**: false

## P-04: 出穴与龙穴对应

- **purpose**: 按九星出穴规则出具穴形假设
- **steps**:
  1. 完成 P-02 九星辨认
  2. 按 R-12 出穴对应推穴形（贪乳/巨窝/武钗钳等）
  3. 由 tool.fengshui.luopan 校核坐向（**严禁 LLM 手算**）
- **tool_dependency**:
  - tool.fengshui.luopan
- **source_chapter**: chuxue
- **verified**: false

## P-05: 罗星水口核查

- **purpose**: 核查水口关锁与罗星正形
- **steps**:
  1. 实地勘察水口位置（需要工具：tool.fengshui.terrain）
  2. 辨罗星正形（方匾尖圆）与变形（破碎尖破）
  3. 与缠护重数综合评判
- **tool_dependency**:
  - tool.fengshui.terrain
  - tool.fengshui.luopan
- **source_chapter**: tanlang
- **verified**: false

> **现代使用边界**：以上流程仅作传统形势派寻龙方法的工具化映射；不构成对当代选址、墓葬、风水改运的现实建议。

# Chart fact inventory

本目录记录 2026-08-12 对冻结 mingli-master 5.1 的一次真实 one-shot 探测。

执行链只有：标准已确认档案 → `compile_bazi_prepare` → Runtime `prepare` → `project_public_fact_panel`。没有调用 Model，没有创建 Reading Root / Job，也没有检查或核销权益。

结果为 `prepared`，脱敏后共有 14 类 public facts。四柱、十神、藏干、纳音有直接字段；神煞与五行可从 Runtime 已计算字段做纯展示映射；空亡、地势、自坐、三宫没有投影，MVP 不在浏览器推导。

证据文件没有写入 Prepare、出生资料原文或 state token。`fact-inventory.json` 只保留 ref 后缀、kind、display/value 形态；`field-alignment.json` 是据此冻结的 Phase 1 展示边界。

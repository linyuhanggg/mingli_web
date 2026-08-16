# P10-009 Wenshi 大六壬来源证据投影接线

日期：2026-08-16

## 本轮完成

本轮把 V53 大六壬已经计算出的、带来源绑定的 `rule_evidence.matched` 接到 Wenshi 的逐术信号层。它只表示“大六壬有一条可追溯的规则证据”，不把证据改写成问事结论，也不把单术证据冒充三术互证。

- Wenshi projector 只消费 `dimension_facts.<dimension>.rule_evidence.matched`。
- 每条信号保留 `art_id=daliuren`、规则 ID、来源绑定的 calculated fact ref 和明确的边界文案。
- `convergence` 与 `disagreements` 继续为空；当前没有形成跨术的实质互证或分歧裁判。
- Web live chart 注册 `wenshi-view/v1`，并把 Wenshi 识别为 `wenshi` 合参产品。
- Admin readings/jobs/detail 暴露 `product_id`，不再只显示主 `capability_id`。
- 修正 brief fact value helper 的引用返回值，使 ReadingDocument 的相关引用落到真实 fact ref。

## 真实 Runtime 证据

黄金样例：

- Runtime release profile：`v53-time-check`，当前 V53 manifest describe digest 为 `4189cfd86910a9eb005407b2c7b87be1d847fc96ae2b54e4f23a35ad304744d5`。
- 事件时间：`2026-01-01T00:00:00+08:00`。
- subject：`wenshi:golden-rule-evidence`。
- 运行方式：本机 one-shot pinned Runtime，真实 `Prepared`；不是 Fake Runtime。
- 测试：`test_v53_runtime_projects_source_bound_liuren_rule_evidence_into_wenshi`，结果 `1 passed`。

实际投影信号为：

```text
signal_id: daliuren.outcome.rule_evidence.final_overcomes_initial
fact_ref: fact:wenshi:golden-rule-evidence/calculated/liuren/dimension_facts
```

该样例同时确认 `convergence=()`、`disagreements=()`，没有生成“吉凶”“成败”或其他硬结论。由于工作树位于 exFAT 卷，签名 release 的 `0600` 文件模式无法在原目录保留；本次真实校验复制到临时 APFS 目录后恢复 manifest 模式，源码和签名内容未改动。

## Worker、文档和局部回归

- V53 Canwen/Hecan/Wenshi 真实 Runtime → Worker → Accepted → typed ReadingDocument 矩阵：`1 passed`。
- Backend projector/Admin 定向回归：`23 passed`。
- Web `reading-result`/`runtime-chart` 定向回归：`37 passed`。
- Admin readings/jobs/detail 定向回归：`7 passed`。
- 本轮最终全仓 `make check`：Backend `937 passed, 114 skipped`，Web `72 files / 454 tests`，Admin `33 files / 122 tests`；Ruff、mypy、两端 lint/typecheck/build 全通过。
- 旧的 V53 大六壬规则包证据仍保留在 [`2026-08-16-p10-liuren-rule-evidence`](../2026-08-16-p10-liuren-rule-evidence/README.md)，本文件只记录 Wenshi/前后台接线，不覆盖旧记录。

## 明确边界

这不是生产部署，也没有把测试服务器切成真实 Runtime；测试服务器仍是 `local + Fake`。本轮没有完成 Canwen/Hecan/Wenshi 的实质规则互证或分歧裁判，没有完成全术产品级深读、追问、导出、发布，也没有用户逐页验收或 P12 生产外部门禁。状态为“证据就绪，待用户验收”。

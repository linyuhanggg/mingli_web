# P10/P11 大六壬事件时间接线修复

日期：2026-08-15

## 结论

本轮发现并修复了一个真实的 Host→Runtime 接线问题：大六壬 v51 manifest 的输入字段名是 `event_datetime_or_reference_datetime`，Request Compiler 之前写成了 `event_datetime`。Runtime 会过滤未知字段并用当前时钟兜底，导致事件术数可能没有使用调用方指定的事件时刻。

- 单术大六壬现在写入 manifest 规定的字段。
- 问事合参同时保留 `event_datetime` 与 `event_datetime_or_reference_datetime`，让六爻、奇门和大六壬收到同一事件时刻。
- 回归黄金样例增加日时断言，防止未来静默回退到当前时钟。
- 相法此前的失败是临时 smoke 夹具使用了错误的主体标识，已按仓库 `sid-...` 合同重跑；没有修改相法算法。

## 本地验证

- 事件编译器与 Wenshi 合参：`3 passed`。
- 真实 v51 Wenshi Runtime：`1 passed`。
- 真实 v51 Runtime→Worker→ReadingDocument 矩阵：`3 passed, 1 skipped`；skip 是未安装的 v52 relationship release，不是 v51 单术 Provider 失败。
- 个人资料只在临时进程中做了验证：13/13 Runtime admission；出生类入口均返回 calculated facts；另用非当前日期事件验证大六壬确实使用指定事件时刻。证据不保存个人资料。
- 完整 `make check`：Backend `908 passed, 110 skipped`；Web `71 files / 448 tests`；Admin `33 files / 121 tests`；Ruff、mypy、两端 lint/typecheck/build 全通过。

## 测试服务器热更新

- 服务器：`fateradar-prod`，当前 release 仍为 `ui-preview-20260815-public-products`。
- 更新文件：`backend/app/readings/request_compiler.py`。
- 更新前备份：`/opt/fateradar/shared/cache/liuren-event-contract-hotfix-20260815/request_compiler.py.before`。
- API/Worker 已重启；API/Worker/Web/Admin active，数据库 ready，Nginx `/healthz`、`/bazi`、`/daliuren`、`/wenshi` 均返回 200。
- 测试机仍是 `local + Fake`，只供页面浏览和合同验收，不代表生产 Runtime、真实支付、备案或公开生产上线。

## 浏览入口

```text
http://127.0.0.1:18080/bazi
http://127.0.0.1:18080/daliuren
http://127.0.0.1:18080/wenshi
```

如本机尚未建立隧道：

```bash
ssh -L 18080:127.0.0.1:8080 -L 13001:127.0.0.1:3001 fateradar-prod
```

P4-007 仍需要用户逐页浏览并明确批准；本轮没有重新大改 UI。

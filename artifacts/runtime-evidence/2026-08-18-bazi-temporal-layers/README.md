# 阶段 L：八字真实目标时间层证据

日期：2026-08-18

状态：证据就绪，待用户验收

## 定性结论

H 阶段的 owner result 没带目标时间，走的是 `profile_preview / life`，所以只返回本命与大运；`year_layers / month_layers / day_layers` 都为空是正确结果，不是 Runtime 算法缺口，也不是把层投影丢了。

真实 V53 定向回归证明三种互斥目标分别可算、可投影：

- `target_year=2026` → `bazi_year_preview / year`，只开放流年
- `target_month=2026-08` → `bazi_month_preview / month`，只开放流月
- `target_date=2026-08-15` → `bazi_day_preview / day`，只开放流日

一次 preview 只允许一个目标，因此不是一张结果同时硬凑流年、流月、流日。未选择的另外两层继续 `data-status=unavailable`、disabled、零渲染；没有拿大运顶替，没有 Fixture，也没有前端推算。

调查同时发现两处真实产品接线漏项并修复：

1. 目标字段的校验、API contract、service 与 payload 拼装都已存在，但 `/bazi` 的高级排盘选项没有渲染输入。现已补回三个可选且三选一的正式表单字段。
2. year/month 请求能持久化，但公开 `Horizon` 响应模型只接受完整日期，解析 `2026` / `2026-08` 时返回 HTTP 500。现已把边界合同收紧为仅接受 `YYYY`、`YYYY-MM`、`YYYY-MM-DD`，仍拒绝时间戳和任意字符串。

## 真实链路与发行物

取证通过 production `/bazi` 正式表单创建 guest session、ProfileVersion 和 `/api/v1/readings/preview`；后台 Worker 调用签名 one-shot Runtime，Web 读取 owner result。Model 使用仓库本地确定性 fake，只推进既有状态机，不计算或补造盘面事实。

- Runtime release：`.runtime/v53-time-check-release`
- release manifest SHA-256：`c451de5e4390c2a264a49aed972057081c61cb74ada160df308ac7a2af993c4b`
- Core source commit：`663543e65ae037843b03dca1dec9486293affc9d`
- 浏览器：Playwright + 系统 Chrome
- 视口：360 / 768 / 1024 / 1440

临时 PostgreSQL 跑在 55432，Alembic 为 `0039_export_ck_names`；取证结束后 API、Worker、Web 和 PostgreSQL 全部停止，3000 / 8000 / 55432 均无监听。

## 四视口结果

三个子目录各有完整 `report.json`、四档五层截图，以及 768 / 1440 与本地 `qingnang/site` 的并排图：

| 子目录 | 正式输入 | 四档可用目标层 | 每档目标层结构事实 | 另外两层 | overflow / 截断 |
|---|---|---|---:|---|---|
| `year/` | `target_year=2026` | 流年 | 19 | unavailable / 0 | 0 / 0 |
| `month/` | `target_month=2026-08` | 流月 | 24 | unavailable / 0 | 0 / 0 |
| `day/` | `target_date=2026-08-15` | 流日 | 56 | unavailable / 0 | 0 / 0 |

三组在四档均同时保留本命 59 条、大运 18 条；三个 `report.json` 均为 `ok=true / failures=[]`，且 release manifest 都是 `c451de5e…`。

审计按真实 `role=tab` 点击目标层并验证 `aria-selected=true`。仓库既有 `bazi-chart-density` 回归锁住同一 tabpanel ID、仅 opacity/transform 的 120–180ms 过渡和无 skeleton；`chart-workspace-shell` 回归锁住键盘切换与 disabled 层不被选中。盘面容器没有被替换成另一路 Fixture 页面。

## 定向门禁

- 真实签名 V53：无目标、year、month、day 共 `3 passed / 3 deselected`（其中 month/day 在同一测试内）
- API 公开 horizon：year/month/day `3 passed / 61 deselected`
- Web 正式输入字段：`10 passed`
- Ruff 定向：通过
- production Web build：通过

## 阶段门禁

最终从头执行 `PYTHONDONTWRITEBYTECODE=1 make check`，显式返回 `MAKE_CHECK_EXIT=0`：Backend `1061 passed / 131 skipped`、Ruff 全通过、mypy `147 source files` 无错误、Web `80 files / 501 passed`、Admin `33 files / 123 passed`，两端 lint/typecheck 与 production build 全绿。

阶段 L 状态：**证据就绪，待用户验收**。未 push、未上传测试机、未部署；`/liuyao`、`/meihua` 的 B 档与 `user_decision_pending=True` 未改。

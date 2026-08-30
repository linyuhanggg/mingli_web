# UI-REWORK-01-UT · 复测结论

- 入口: `http://106.14.10.235:18080`
- Release: `ui-rework-01-20260830-181606-on-revision20`
- 资料: 林宇航 / 男 / 2000-10-18 05:10 / 福建省莆田市涵江区（虚构）
- 视口: 1440×900、360×800（另抽查 768）
- 总判: **FUNCTIONAL_BLOCKED**

## §9 清单

| # | 项 | 结论 | 可观察证据 |
| --- | --- | --- | --- |
| 1 | 首页主 CTA / 非卡片墙 / 无纸墨剧场 | **PASS** | 1440/360 首屏唯一实心主钮「开始排八字」；主入口为八字 lead + 紧凑列表，非等权卡片墙；无纸墨/液态玻璃/黑金剧场。截图 `1440/00-home-viewport.png`、`360/00-home-viewport.png` |
| 2 | 录入必填/摘要/无假四柱/360 可点 | **PASS** | 必填标注清晰；「即将提交」与表单一致（男·2000-10-18·05:10·福建/莆田/涵江）；无假干支；360 主 CTA 高 48px。截图 `*/02-bazi-filled.png` |
| 3 | 结果四柱主角 / 付费不压盘 / 待接入 / 无内部字段 | **BLOCKED** | 提交后 60s+ 仍停在「正在准备免费盘面」，四柱从未上屏，无法验收结果页视觉。见 `*/04-natal-top.png`、`probe/` |
| 4 | 秒出无额外排队叙事 | **FAIL** | `POST /api/v1/readings/preview` → 201，`status=prepared`，`result_available=true`，`poll_required=false`，view_model 已含庚辰/丙戌/己酉/丁卯；UI 却持续「服务端正在处理…离开页面后任务仍会继续 / 正在准备免费盘面」，并反复 GET 同一 reading。证据 `probe/probe.json` |
| 5 | 视口无整页横滑 | **PASS** | 360/768/1440 的 home/input/stuck-result `overflowX=false` |
| 6 | 玄序观感 | **PASS** | 灰阶底 + 朱砂眉题/链；非旧纸墨宣纸剧场。截图同上 |

## 关键 finding（沿用 UI-REWORK-01）

**F1 · FUNCTIONAL_BLOCKED · 免费盘结果不渲染 / 秒出体感回退**

- 入口: `/bazi` 填资料 → 「立即排盘」
- 期望: 同步秒出可核对四柱；不出现异步排队叙事
- 实际: API 已 prepared+view_model，页面卡在任务进度「正在准备免费盘面」≥60s；URL 不进入 `?reading=&profile=` 结果态
- 严重度: P0（阻断 §9 结果与秒出验收；相对上一预览「基本上能秒出」回归）
- 归属建议: `frontend-dev`（后端 preview 合同正常；前端未消费 prepared 结果）

## 证据目录

`docs/releases/evidence/2026-08-30-ui-rework-01-ut/`

# UI-REWORK-01-UT2 · 复测结论

- 入口: `http://106.14.10.235:18080`
- Release: `ui-rework-01-fe2-f1-20260830-184242-on-rework01`（REL2）
- 资料: 林宇航 / 男 / 2000-10-18 05:10 / 福建省莆田市涵江区（虚构）
- 视口: 1440×900、360×800
- 对照首轮: `docs/releases/evidence/2026-08-30-ui-rework-01-ut/VERDICT.md`（总判 FUNCTIONAL_BLOCKED / F1）
- 总判: **UI_REWORK**（F1 已解；§9.3 未过，不可关单）

## 必验项

| # | 项 | 结论 | 可观察证据 |
| --- | --- | --- | --- |
| F1 | 秒出：四柱迅速上屏；无长时间「正在准备免费盘面」；poll 完成路径无「离开页面后任务仍会继续」 | **PASS** | POST preview → 201 `prepared` + `result_available=true` + `poll_required=false` + view_model。页面约 **1.3–1.6s** 出现「免费盘面已就绪」与四柱干支（年庚/辰、月丙/戌、日己/酉、时丁/卯，干支分行）。全文无「正在准备免费盘面」「离开页面后任务仍会继续」。计时 `probe-timing.json`；截图 `*/04-natal-top.png`、`probe-*/top.png` |
| §9.3 | 首屏主角四柱+日主；专业表在后；付费不压盘；待接入不刷屏；无内部字段名 | **FAIL** | 见下方 finding F2/F3。付费「深读/测试期未开放」在盘面之后（PASS）；「待接入」全文 1 次（PASS）；专业表在四柱后（PASS） |
| 首页/录入 | 顺手确认未回退 | **PASS** | 首页主 CTA「开始排八字」仍在；录入摘要含男·2000-10-18·05:10·福建/莆田/涵江。`*/00-home-*`、`*/02-bazi-filled*` |

## Finding（沿用 UI-REWORK-01）

### F1 · 原 FUNCTIONAL_BLOCKED · **本轮已修复 · PASS**

- 首轮：API prepared 但 UI 卡「正在准备免费盘面」≥60s，四柱不上屏
- 本轮：~1.6s 出「免费盘面已就绪」+ 可核对四柱；无排队叙事

### F2 · UI_REWORK · 结果首屏主角不是四柱+日主

- 入口: `/bazi` 提交后结果工作台（scrollY=0）
- 期望: 首屏（扣 chrome）主角为四柱网格 + 日主眉题；任务/说明不抢主视高
- 实际:
  - **1440**: 首屏上半为步进器 +「任务进度 / 免费盘面已就绪」；「日主 己（土·阴）」约 top=828（贴底）；**年/月/日/时柱标签 top≈930，落在 900 视口折线下**。截图 `1440/04-natal-top.png`、`probe-1440/top.png`
  - **360**: 首屏几乎全是工作台壳 + 任务进度 +「免费确定性盘面」说明；**日主己行 top≈930、四柱 top≈1060，均在 800 视口外**；仅见「八字命盘」标题贴底。截图 `360/04-natal-top.png`、`probe-360/top.png`
- 严重度: P1（HANDOFF §9.3 / §4 主工件比未满足；用户须下滚才见可核对四柱）
- 归属: `frontend-dev`

### F3 · UI_REWORK · 结果页泄漏内部字段名 / 英文工程文案

- 入口: 同上，滚动至「神煞 / 判定过程」「五行盘点」
- 期望: 无 snake_case / 内部 key；用户可见文案为中文产品语
- 实际: 神煞判定过程可见  
  `month_command、structure、strength、tiaohou、ten_gods、luck_cycles、transit_facts`  
  及英文句 `no Shensha item may override…`；五行区另有 `inventory only; these counts do not determine 旺衰 or 用神`
- 证据: `1440/04-natal-text.txt` L242、L226；`360/04-natal-text.txt` 对应行；`probe-timing.json` `hasInternalEn=true`
- 严重度: P1（HANDOFF §0/§9.3「无内部字段名」）
- 归属: `frontend-dev`（若文案来自 Runtime 公开字段，可协同后端/算法改公开文案，但预览 UI 不得原样甩出）

## 证据目录

`docs/releases/evidence/2026-08-30-ui-rework-01-ut2/`

- `run-ut2.mjs` / `run.log` / `summary.json`
- `probe-timing.json` / `probe-1440/top.png` / `probe-360/top.png`
- `1440/` · `360/`：home → entry → filled → after-click → natal top/full/mid

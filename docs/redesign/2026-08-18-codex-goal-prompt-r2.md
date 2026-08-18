# Codex Goal 模式任务提示词 R2 — 提交收口 + C6 密度证据 + G1 真实闭环

> 用法：把本文件全文粘贴给 Codex，以 goal 模式（长时自动续轮）执行。目标仓库：`/Volumes/Lexar/code/mingli_web`。
> 编制日期：2026-08-18，依据是上一轮施工后的独立验收（记录见 `docs/CHECKLIST.md` 第 15 节末尾四行）。
> 本文是**执行提示词，不是权威合同**。判据只在 `DESIGN.md` §17/§19/§20/§21/§22 与 `docs/CHECKLIST.md`。

---

## 0. 动手前必读

1. `docs/CHECKLIST.md` 第 15 节末尾四行 — 上一轮的验收结论、两项未通过、本轮待办定稿
2. `DESIGN.md` §19–§22 — 判据；§20.1 的能力分层归档与「判断规则」机器定义
3. `docs/redesign/2026-08-18-codex-goal-prompt.md` — 上一轮提示词，阶段 A/B/C 已完成，**不要重做**

## 1. 上一轮已完成，先验证不要重做

独立复跑确认：Backend `1058 passed / 131 skipped`、Ruff `All checks passed`、mypy `147 source files` 无错误、
Web `80 files / 500 passed`、Admin `33 files / 123 passed`、两端 lint/typecheck/production build 全绿，`ahead 7` 未 push。

- **阶段 A**：ruff/mypy 已真修，AppleDouble 清零，`.gitignore` 补 `._*` 与 `/snapshots/`，binding manifest 基线迁入证据目录，core 提交 `a93c0c6`
- **阶段 B（G4）**：`backend/app/readings/capability_policy.py` 从签名 release 的 `evidence-rules.jsonl` 现算档位；`divination` 按 `rule_id` 前缀拆六爻/梅花；`_tier_for` 把两者钉在 B 档并置 `user_decision_pending=True`；缺 projection 时 fail-closed 到 C 档
- **阶段 C（G5 代码）**：`bazi-chart.tsx` 888→1549 行，SVG 干支关系图 + 语义表、五行计数区、大运完整序列/起运元数据/三态/`unavailable`、流年流月流日面板、联动扩展至十神与藏干元素贡献

**保持不动的约束**：`/liuyao` 与 `/meihua` 继续钉在 B 档、`user_decision_pending=True`，等用户裁决。本轮**不得**据实测规则数自行升档。

---

## 阶段 E · 提交收口（先做完再进 F）

上一轮的 B/C 产出全部还在工作区：52 个已跟踪改动 + 新增文件。**严禁 `git add -A` / `git checkout .` / `git reset --hard`**，逐条 `git add <path>`，每组 commit 前用 `git diff --cached --stat` 复核范围。

| # | 范围 |
|---|---|
| 1 | G4 能力档位：`backend/app/readings/capability_policy.py`、`backend/app/api/capabilities.py`、`backend/app/api/router.py`、`contracts/openapi/v1.yaml`、`backend/tests/test_capability_policy.py`、`web/src/test/runtime-capability-gate.test.tsx` 及其消费侧改动 |
| 2 | G5 八字密度与联动：`web/src/components/readings/bazi-chart.*`、`chart-workspace-shell.*`、`web/src/lib/chart-workspace.ts`、`web/src/test/bazi-chart-density.test.tsx` 及相关测试更新 |
| 3 | 其余散项：新增的 `backend/tests/test_*_adjudication_runtime.py`、`test_bazi_verified_exact_evidence_contract.py`、`web/src/lib/china-division.ts` 等——逐个确认属于哪一轮工作再归组，**不确定的先 `git log`/`git diff` 查证，不要凭文件名猜** |
| 4 | 证据与账本：`artifacts/browser-evidence/**`、`artifacts/runtime-evidence/**`、`docs/CHECKLIST.md`、本文件 |
| 5 | `core/mingli-master` 仓内单独提交剩余的 `SKILL.md` |

每组 commit 前跑该组定向测试；全部落地后跑一次全量 `make check` 并把实测数字写进 CHECKLIST 第 15 节。**不 push。**

---

## 阶段 F · C6 真实浏览器密度证据

### F1 先纠正工具路径（这是上一轮记为「阻塞」的真实原因）

上一轮 README 写「浏览器连接返回无可用实例，`agent.browsers.list()` 返回空列表」——那是 browser MCP 通道。
**本仓不走那条通道。**已实测确认可用的路径：

- `@playwright/test 1.62.1` 已在 `web/package.json` 装好
- 既有范式在 `web/scripts/audit-phase4.mjs:126`：
  `chromium.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" })`
- 本轮 `artifacts/browser-evidence/2026-08-18-bazi-deep-authority/` 的 360/768/1024/1440 四视口截图就是这条路径产出的
- 现场复跑该 launch 成功

所以 C6 不是环境阻塞，是走错了通道。参照 `web/scripts/audit-phase4.mjs` 写 `web/scripts/audit-g5-density.mjs`。

### F2 要产出什么

- **四视口截图**：360 / 768 / 1024 / 1440，覆盖八字结果页完整区段（命盘头、四柱、关系图、盘面明细、五行分布、大运、候选事实、古籍命中抽屉）
- **页面级横向溢出实测**：每档断言 `scrollWidth <= innerWidth + 1`；关系图允许在自身容器内横滚，页面级不许
- **并排密度计数**：1440 与 768 两档，与本地镜像 `qingnang/site` 并排统计**可见结构化事实条目数**，本产品不得低于对方。计数方法必须写进 README 并可复算（选择器、计数单位、去重规则），不得只给一个结论数字
- **不得**靠超小字、截断或页面横滚达标（§17）

证据落 `artifacts/browser-evidence/2026-08-18-bazi-g5-density/`，覆盖现有那份 blocked README，写清计数方法与两边结果。

### F3 数据来源边界

结果页用真实 Runtime 产出优先；只能用 `/_ui-lab/bazi-result` Fixture 时，README 必须显著标注「合成 Fixture，不代表 Runtime 已发布」，**不得**把 Fixture 截图记为 `BROWSER_VERIFIED`。

---

## 阶段 G · G1 真实闭环（本轮重点）

### G1a 问题定性

上一轮实测：真实 V53 preview 结果里抽出的 4 条引文经 `scripts/verify_citation.py` 判为
`not_found / partial_match / not_found / not_found`，退出码 `1`。已独立复核确认它们是**摘要改写**而非逐字原文，例如
Runtime 输出「三春庚金：正月庚金以丙甲为上、丁火次之…」全库最高 3-gram 包含率仅 19%，
真正原文在《穷通宝鉴》`references/fulltext/bazi/qiongtong-baojian/fulltext.md#L1084`。

原因是**当前准入的签名 V53 release 仍在投影旧 excerpt**——core 源码里的 exact evidence 投影（本轮 `a93c0c6`）
还没进入签名发行物。所以 DESIGN §22 的 G1 在真实产品链路上不成立。

### G1b 本地重建并重签 V53（**仅限本地**）

- 用 `core/mingli-master/scripts/release_deploy.py` 重建并重签，把本轮 core 的 exact evidence 投影带进发行物
- **旧 release 目录与 `.runtime/backups` 必须保留可回滚**；重签前记录旧 manifest/describe/shape 哈希，重签后记录新值
- 用 `scripts/verify_frozen_runtime_release.py` 校验发行物完整性
- 后端准入常量（source-table SHA、manifest 期望值）若随之变化，同步更新并补回归——上一轮就出过 `liuren_calc` 与
  `liuren_fact_adapter` SHA 漂移把真实 Runtime 折叠成 `Stopped(error)` 的事故，别再犯

**边界：只做本地重建、重签、本地准入。上传测试机、部署、push 一律需要用户另行授权，本轮不做。**

### G1c 复验

重签后重跑真实纵链（guest session → ProfileVersion → `/api/v1/readings/preview` → Worker → owner result），
从结果 `fact_panel.evidence` **原样**抽取全部引文，然后：

```bash
python3 scripts/verify_citation.py --file <引文清单>.txt   # 退出码必须为 0
```

- **不得**改脚本阈值、不得挑样本、不得替换 excerpt、不得只抽能过的那几条
- 退出码仍非 0 就如实记录哪几条不过、包含率多少、真正原文在哪一行，并说明是发行物问题还是投影问题
- 证据落 `artifacts/runtime-evidence/`，README 写明新旧 manifest 哈希、抽取方法、逐条判定

---

## 每阶段完成定义（缺一不可）

- [ ] `make check` 全绿：Backend pytest + Ruff + mypy、Web 与 Admin 的 test/lint/typecheck、production build
- [ ] 该阶段产出已分组 commit（Conventional Commits，只含该阶段文件），**不 push**
- [ ] `docs/CHECKLIST.md` 第 15 节追加记录：日期 / 范围 / **当次实际跑出来的**门禁数字 / 证据路径
- [ ] 状态标注为「证据就绪，待用户验收」——**你没有批准权**

## 红线

1. **严禁** `git add -A`、`git checkout .`、`git reset --hard`；只 add 你明确改动的文件
2. **严禁把未实际运行的验证写成通过**。写进账本的每个数字必须是当次跑出来的
3. **不 push、不上传测试机、不部署**。本轮只允许本地重建/重签/本地准入，且必须可回滚
4. `/liuyao`、`/meihua` 维持 B 档与 `user_decision_pending=True`，**不得自行升档**
5. 不得为了让 G1 过门而改 `verify_citation.py` 阈值、替换 excerpt 或挑样本；过不了就如实记录
6. 需要改 `DESIGN.md`、`CONTEXT.md`、`docs/MINGLI_V51_WEB_INTEGRATION.md` 的**规则本身**时，先停下写影响范围交用户批准
7. 不新增依赖；不回归 §17 禁令与 §22 各门

## 环境事实（已实测，直接用）

- 全量门禁：`make check`；分项见 `Makefile`
- **浏览器走 Playwright + 系统 Chrome**：`chromium.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" })`，
  范式见 `web/scripts/audit-phase4.mjs:126`。**不要用 browser MCP 通道**，那条通道在本机返回空列表
- G3/core 原生回归用 `~/.local/share/mingli-master/venv/bin/python`（该 venv 无 pytest，用 unittest 直跑）。
  **不要新建 venv 装 `sxtwl==2.0.7`**——该版本 PyPI sdist 缺 `src/JD.cpp`，构建必失败
- `zhconv` 在上述 venv 里可用，`verify_citation.py` 依赖它做繁简统一
- 参考站本地镜像：`qingnang/site`（已 gitignore），G5 并排统计用它，不要联网抓
- 规则索引：`.runtime/v53-time-check-release/references/index/evidence-rules.jsonl`，是 G4 分档唯一数据源
- 发布工具：`core/mingli-master/scripts/release_deploy.py`、`scripts/verify_frozen_runtime_release.py`、`make mingli-core-status`

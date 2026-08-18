# Codex Goal 模式任务提示词 R5 — 全站 G6 证据刷新 + 提交收口 + P4-007 验收清单

> 用法：把本文件全文粘贴给 Codex，以 goal 模式（长时自动续轮）执行。目标仓库：`/Volumes/Lexar/code/mingli_web`。
> 当前分支：`codex/h-i-j-runtime-evidence`（继续在此分支提交，不要切回 main、不要 rebase 已有提交）。
> 编制日期：2026-08-19，依据是阶段 K/L/M/N 完成后的独立验收（见 `docs/CHECKLIST.md` 第 15 节末尾三行）。
> 本文是**执行提示词，不是权威合同**。判据只在 `DESIGN.md` §17/§18/§19/§20/§21/§22 与 `docs/CHECKLIST.md`。

---

## 0. 动手前必读

1. `docs/CHECKLIST.md` 第 15 节末尾三行 — K/L/M/N 验收结论、授权待确认项、本轮范围
2. `DESIGN.md` §18（真实浏览器验收）与 §22 G6 — 本轮主判据
3. `docs/releases/evidence/2026-08-14-route-acceptance/README.md` 与 `…-working-tree/README.md` — 上一版全站证据的口径与脚本范式，本轮沿用
4. `docs/redesign/2026-08-18-codex-goal-prompt-r4.md` — 上一轮，K/L/M/N 已全部完成并验收，**不要重做**

## 1. 上一轮状态（已独立复核，不要重做）

- **K**：真实 `/bazi` 古籍抽屉已渲染，四视口 `evidenceDrawerRendered=true`、「命中古法 6 条 · 可核验」；
  页面 DOM 抽取的 6 条引文复跑 `6/6 verified_exact`、退出码 `0`
- **L**：时间层空缺归因为输入未带目标时间，非算法缺口；三种互斥目标各自可算可投影
- **M**：免费 `preview-v1` 非 Prepared-only 合同，真实 PostgreSQL/API 纵链回归已补
- **N**：`--mode release-bound` 落地，正向 `0`、三种负向全部 `1`；路线 B 缺语料 fail closed 并给出复核命令
- 当前 release manifest `c451de5e…`，回滚点 G1 与 K 两套均保留
- 门禁基线：Backend `1063 passed / 132 skipped`、Web `80 files / 501 passed`、Admin `33 files / 123 passed`，
  Ruff/mypy/两端 lint/typecheck/production build 全绿

**保持不动的约束**：`/liuyao`、`/meihua` 继续钉在 B 档且 `user_decision_pending=True`，等用户裁决。

---

## 阶段 P · 提交收口（先做完再进 Q）

工作区有 7 项未提交，逐条 `git add`，**严禁 `git add -A`**：

| # | 范围 |
|---|---|
| 1 | `docs/CHECKLIST.md`、`docs/redesign/2026-08-18-codex-goal-prompt-r3.md`、`…-r4.md`、本文件 |
| 2 | `artifacts/runtime-evidence/2026-08-18-g1-self-verification-investigation/`（含 2026-08-18 dated addendum） |
| 3 | `docs/releases/evidence/2026-08-12-reference-site-audits/visual-craft-excerpt.md` — 先查清它属于哪一轮、是否该进证据目录，再决定提交或删除 |
| 4 | `artifacts/browser-evidence/2026-08-19-bazi-test-server-acceptance/`、`docs/releases/evidence/2026-08-19-bazi-test-server-upload/` — **见阶段 P2** |

### P2 测试服务器发布产物的处理

这两个目录记录了 2026-08-19 02:28–02:31 把 HEAD `7822dd9` 上传测试服务器并原子切换的事实。
该动作**不在 R4 授权范围内**（R4 红线 3 明确禁止上传测试机与部署），且本机当时没有 codex 会话在跑。

- **不要重复该动作，不要再次上传或切换测试服务器。**
- 证据本身照实保留，按原样提交，不得修改、美化或删除其中的版本身份与回滚信息
- 在 `docs/CHECKLIST.md` 追加一行，写明该发布的执行来源**尚待用户确认**，在确认前不作为 P4-007 的推进依据

提交后跑一次全量 `make check`，把实测数字写进 CHECKLIST。**不 push。**

---

## 阶段 Q · G6 / §18 全站四视口 × 六态证据刷新（本轮主体）

### Q1 为什么要做

现存全站证据是 `docs/releases/evidence/2026-08-14-route-acceptance/` 与 `…-working-tree/`，
基线为 2026-08-14 工作树。此后经历方向 C 重构、G1–G5 纵链、两次 V53 重签与八字结果页重写，
该证据**已不能代表当前构建**。G1–G5 已在八字主线闭合，G6 是当前唯一还没在本构建上过的机器可判定门。

### Q2 范围与口径

沿用上一版 route-acceptance 的路由清单与脚本范式，在**当前构建**上重跑：

- 视口：360 / 768 / 1024 / 1440 四档
- 状态：§14 的六态（loading / empty / error / processing / unavailable / unauthorized / locked 按既有状态库存实况取）
- 每路由每视口断言：`document.documentElement.scrollWidth <= window.innerWidth + 1`（页面级无横向溢出）
- 双栏工作台实测右侧阅读区 `>= 360px`（§18）
- 唯一 h1、Skip Link、focus-visible 不被 sticky 遮挡、键盘可达
- `prefers-reduced-motion: reduce` 下动效静态降级且内容不缺失
- **正常路由无 Fixture、无 raw JSON、无 snake_case 内部引用、无旧品牌残留**（§17）

### Q3 硬约束

- 浏览器走 Playwright + 系统 Chrome，**不要用 browser MCP 通道**
- 数据源用真实签名 Runtime（manifest `c451de5e…`）；确实只能用 Fixture 的路由（`/_ui-lab/**`）必须在
  README 显著标注，且**不得计入正常路由的通过项**
- 任何一条断言不过就如实记录路由、视口、实测值，**不得调整阈值或跳过该路由**
- 证据落 `docs/releases/evidence/2026-08-19-route-acceptance/`，README 写明路由清单、口径、
  与 2026-08-14 版的差异、失败项列表

### Q4 完成判据

- `report.json` 含逐路由逐视口的实测值与 `failures[]`
- 失败项要么当轮修掉并重跑，要么写清原因与归属（UI 缺陷 / Runtime 缺口 / 合同待裁决）
- 回写 `docs/CHECKLIST.md` 第 13 节证据索引与第 15 节变更记录

---

## 阶段 R · P4-007 逐页验收清单

P4-007 是「用户亲自浏览并批准」，**你没有批准权，也不能代替用户浏览**。你要做的是把验收变得可执行：

- 生成一份 `docs/releases/evidence/2026-08-19-route-acceptance/USER-ACCEPTANCE-CHECKLIST.md`
- 按页面族（公共站 / 产品录入 / 工作台与结果 / 账户区 / Admin）列出用户需要逐页确认的条目
- 每条给出：路由、该页本轮的关键变化、对应截图路径、需要用户判断的问题（如「这一屏的信息密度是否可接受」）
- 明确标出**当前仍待用户裁决的两项**：`/liuyao` 与 `/meihua` 的能力档位、以及 2026-08-19 测试服务器发布的授权归属
- 不要在清单里替用户预填结论，不要出现 `USER_ACCEPTED` 字样

---

## 每阶段完成定义（缺一不可）

- [ ] `make check` 全绿：Backend pytest + Ruff + mypy、Web 与 Admin 的 test/lint/typecheck、production build
- [ ] 该阶段产出已分组 commit（Conventional Commits，只含该阶段文件），**不 push**
- [ ] `docs/CHECKLIST.md` 第 15 节追加记录：日期 / 范围 / **当次实际跑出来的**门禁数字 / 证据路径
- [ ] 状态标注为「证据就绪，待用户验收」——**你没有批准权**

## 红线

1. **严禁** `git add -A`、`git checkout .`、`git reset --hard`；只 add 你明确改动的文件；不切分支、不 rebase 已有提交
2. **严禁把未实际运行的验证写成通过**。写进账本的每个数字必须是当次跑出来的
3. **不 push、不上传测试机、不部署、不切换 `/opt/fateradar/current`**。2026-08-19 那次发布已发生且待用户确认归属，
   **不得以「已经发过一次」为由再发一次**
4. `/liuyao`、`/meihua` 维持 B 档与 `user_decision_pending=True`，不得自行升档
5. 不得用 Fixture 冒充正常路由的通过项；不得为过门调整阈值、跳过路由或挑样本
6. 不得实施路线 A（fulltext 进发行物）——再分发授权未确认
7. 重签后的 release 与全部回滚副本不得删除；本轮无需重签，若确有必要先备份并记录新旧哈希
8. 需改 `DESIGN.md`、`CONTEXT.md`、`docs/MINGLI_V51_WEB_INTEGRATION.md` 的**规则本身**时，先停下交用户批准
9. 不新增依赖；不回归 §17 禁令与 §22 各门

## 环境事实（已实测，直接用）

- 当前分支 `codex/h-i-j-runtime-evidence`，相对 `main` 领先 5 个提交；`main` 亦领先 `origin/main`，全部未 push
- 全量门禁 `make check`；核心漂移 `make mingli-core-status`
- 当前签名 release manifest SHA-256：`c451de5e4390c2a264a49aed972057081c61cb74ada160df308ac7a2af993c4b`
- **浏览器走 Playwright + 系统 Chrome**：`chromium.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" })`，
  范式见 `web/scripts/audit-phase4.mjs:126`
- 引文核验两条链（均已实测）：
  ```bash
  # 第 1–3 步，仅依赖签名 release
  python3 -B scripts/verify_citation.py --mode release-bound \
    --release-root .runtime/v53-time-check-release --file <result>.json

  # 第 4 步，需外置全文语料
  PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=.runtime/backups/2026-08-18-g1-resign/runtime-extras \
  ~/.local/share/mingli-master/venv/bin/python -B scripts/verify_citation.py --file <清单>.txt
  ```
- core 原生回归用 `~/.local/share/mingli-master/venv/bin/python`（无 pytest，用 unittest 直跑）；
  **不要新建 venv 装 `sxtwl==2.0.7`**（sdist 缺 `src/JD.cpp`）
- 参考站本地镜像 `qingnang/site`（已 gitignore）

# Codex Goal 模式任务提示词 R3 — G5 真实数据版 + G1 可核验性收口 + 免费链 Accepted 闭合

> 用法：把本文件全文粘贴给 Codex，以 goal 模式（长时自动续轮）执行。目标仓库：`/Volumes/Lexar/code/mingli_web`。
> 编制日期：2026-08-18，依据是阶段 E/F/G 完成后的独立验收（记录见 `docs/CHECKLIST.md` 第 15 节末尾两行）。
> 本文是**执行提示词，不是权威合同**。判据只在 `DESIGN.md` §17/§19/§20/§21/§22 与 `docs/CHECKLIST.md`。

---

## 0. 动手前必读

1. `docs/CHECKLIST.md` 第 15 节末尾两行 — 阶段 E/F/G 的独立验收结论与本轮三项待办
2. `DESIGN.md` §19–§22 — 判据；§20.1 能力分层归档与「判断规则」机器定义
3. `artifacts/runtime-evidence/2026-08-18-bazi-v53-g1/README.md` — 上一轮 G1 闭环的完整复现步骤
4. `docs/redesign/2026-08-18-codex-goal-prompt-r2.md` — 上一轮提示词，阶段 E/F/G 已完成，**不要重做**

## 1. 上一轮已完成，先验证不要重做

独立复跑确认：Backend `1058 passed / 131 skipped`、Ruff 全通过、mypy `147 source files` 无错误、
Web `80 files / 500 passed`、Admin `33 files / 123 passed`、两端 lint/typecheck/production build 全绿，`ahead 17` 未 push。

- **阶段 E**：B/C 产出已分组提交，`core/mingli-master` 无未提交项
- **阶段 F**：四视口 × 五时间层截图、768/1440 并排、`report.json` 记录 `overflow=0` / 最小字号 13 / 截断 0
- **阶段 G**：V53 已本地重建重签，manifest `7996b033…`，`mingli-core-status` 为 `220/0/0/0`，
  回滚副本 `.runtime/v53-time-check-release-before-g1-20260818/` 与 `.runtime/backups/2026-08-18-g1-resign/` 保留；
  **G1 真实闭环成立**：真实 preview 的 7 条 evidence excerpt 经未修改的 `verify_citation.py` 复核为 `7/7 verified_exact`、退出码 `0`

**保持不动的约束**：`/liuyao`、`/meihua` 继续钉在 B 档且 `user_decision_pending=True`，等用户裁决，本轮**不得**自行升档。

---

## 阶段 H · G5 密度证据改用真实 Runtime 重做

### H1 问题

`artifacts/browser-evidence/2026-08-18-bazi-g5-density/report.json` 自己标了：

```
"productRoute": "/_ui-lab/bazi-result",
"productDataBoundary": "synthetic-ui-lab-fixture-not-runtime-release"
```

即当前 84 vs 33 的密度结论建立在**合成 Fixture** 上。重签后真实 `/bazi` 已能返回 A 档结果
（`19 facts / 7 evidence / 4 findings`，见 `artifacts/runtime-evidence/2026-08-18-bazi-v53-g1/vertical-result.json`），
所以 G5 必须在真实结果页上重跑，否则这道门只在 Fixture 上成立。

### H2 要做什么

- 复用 F 阶段已写好的密度审计脚本，把产品侧数据源从 `/_ui-lab/bazi-result` 换成**真实签名 Runtime 驱动的 `/bazi` owner 结果页**
- 计数方法、去重规则、排除占位项的口径**保持与上一轮完全一致**（README 已写明），只换数据源，便于与 84 vs 33 直接对比
- 四视口 360 / 768 / 1024 / 1440 全跑，每档每层断言 `document.documentElement.scrollWidth <= window.innerWidth + 1`
- 1440 与 768 与 `qingnang/site` 并排统计，本产品不得低于参考站
- 真实数据下若某些区块因字段缺失不渲染导致条目数低于 Fixture 版，**如实记录差额与缺失字段**，不得回退去用 Fixture 补数

### H3 边界

- 新证据落 `artifacts/browser-evidence/2026-08-18-bazi-g5-density-runtime/`，**不要覆盖** Fixture 版那份，两份都留作对照
- 新 README 必须写明 `productDataBoundary` 为真实签名 Runtime，并记录所用 release manifest 哈希
- 浏览器走 Playwright + 系统 Chrome，**不要用 browser MCP 通道**（见环境事实）

---

## 阶段 I · G1 可核验性缺口收口

### I1 问题

签名 release 的 `references/` 只含 `books / catalog / index / inference / matrices / source-excerpts`，
**不含 `fulltext/`**。但引文锚点形如：

```
references/fulltext/bazi/sanming-tonghui/fulltext.md#L34
```

指向 release 内不存在的路径。上一轮核验能过，是因为用了外部语料库
（`~/.codex/skills/mingli-master/references/fulltext`）。

`DESIGN.md` §22 G1 的命题是「每一句都能翻回原书第几行、可当场证伪」。
**只拿到 release 的人现在自证不了**——这是差异化命题的实际缺口，不是文档笔误。

### I2 先调查再动手，两条路选一条并说明理由

- **路线 A：把 fulltext 纳入发行物**——查清体积、`release_deploy.py` 的 `PRESERVE_PREFIXES` 为何把
  `references/fulltext` 列为保留项、纳入后对 manifest/签名/分发的影响
- **路线 B：显式声明核验依赖**——在 `docs/MINGLI_V51_WEB_INTEGRATION.md` 与 `DESIGN.md` §22 G1 写明
  「引文锚点面向独立语料库，核验需另装 `mingli-master` 语料，获取方式为 X」，并让 `verify_citation.py`
  在缺语料库时给出明确的获取指引而非笼统报错

**先把调查结论写出来再选**，把体积、影响面、对 G1 命题的实际效果列清楚。
若结论是需要改 `DESIGN.md` §22 的**规则表述**，停下来交用户批准再改。

### I3 无论选哪条都要做的

- 补一条回归：引文锚点指向的路径若在当前核验根下不可解析，必须 fail closed 并给出可执行的修复指引
- 把结论回写 `docs/CHECKLIST.md`

---

## 阶段 J · 免费链 Accepted → Typed ReadingDocument 闭合

### J1 现状

上一轮 G 的真实纵链只到 `prepared`——证据 README 明确写了「没有把 `prepared` 写成 Accepted，也没有生造 ReadingDocument」，
这是对的。付费链已有真实 V53 Worker → Accepted → Typed Document `1 passed`。
缺的是**免费 owner 结果**这条路径的 Accepted → Typed ReadingDocument 真实闭环。

### J2 要做什么

- 用重签后的签名 V53，跑真实免费纵链：guest session → ProfileVersion → `/api/v1/readings/preview` →
  Worker → **Accepted** → Typed `bazi-chart/v1` ReadingDocument
- 断言 `ReadingDocument.versions.runtime_release` 指向重签后的 release
- Accepted 正文必须逐字等于所引 `fact.display_text` / `finding.public_text` / `limit.public_text`，
  沿用既有 `bazi-deep-output-v1` 的抽取与去重门禁口径，不得拼接改写
- 从 Accepted 后的文档再抽一次引文跑 `verify_citation.py`，退出码必须 `0`；非 0 就如实记录

### J3 边界

- 若免费链按产品合同本来就不产出 Accepted（只到 `prepared` 即为设计），**停下来把这个合同事实写清楚并交用户确认**，
  不要为了「闭合」而新造一条免费 Accepted 路径

---

## 每阶段完成定义（缺一不可）

- [ ] `make check` 全绿：Backend pytest + Ruff + mypy、Web 与 Admin 的 test/lint/typecheck、production build
- [ ] 该阶段产出已分组 commit（Conventional Commits，只含该阶段文件），**不 push**
- [ ] `docs/CHECKLIST.md` 第 15 节追加记录：日期 / 范围 / **当次实际跑出来的**门禁数字 / 证据路径
- [ ] 状态标注为「证据就绪，待用户验收」——**你没有批准权**

## 红线

1. **严禁** `git add -A`、`git checkout .`、`git reset --hard`；只 add 你明确改动的文件
2. **严禁把未实际运行的验证写成通过**。写进账本的每个数字必须是当次跑出来的
3. **不 push、不上传测试机、不部署**。当前 `ahead 17`，推送需用户另行授权
4. `/liuyao`、`/meihua` 维持 B 档与 `user_decision_pending=True`，**不得自行升档**
5. 不得为了过门而改 `verify_citation.py` 阈值、替换 excerpt、挑样本或用 Fixture 冒充真实数据；过不了就如实记录
6. 重签后的 release 与两份回滚副本不得删除；若本轮需再次重签，同样先备份并记录新旧哈希
7. 需要改 `DESIGN.md`、`CONTEXT.md`、`docs/MINGLI_V51_WEB_INTEGRATION.md` 的**规则本身**时，先停下写影响范围交用户批准
8. 不新增依赖；不回归 §17 禁令与 §22 各门

## 环境事实（已实测，直接用）

- 全量门禁：`make check`；分项见 `Makefile`；核心漂移检查 `make mingli-core-status`（当前 `220/0/0/0`）
- **浏览器走 Playwright + 系统 Chrome**：`chromium.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" })`，
  范式见 `web/scripts/audit-phase4.mjs:126`。**不要用 browser MCP 通道**，那条通道在本机返回空列表
- **`verify_citation.py` 需要 `zhconv`，但 `~/.local/share/mingli-master/venv` 里没有**。可用的调用方式（已实测退出码 0）：
  ```bash
  PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=.runtime/backups/2026-08-18-g1-resign/runtime-extras \
  ~/.local/share/mingli-master/venv/bin/python -B scripts/verify_citation.py --file <清单>.txt
  ```
  不加 `--root` 时脚本默认用 `~/.codex/skills/mingli-master`，该语料库存在且可核验通过
- G3/core 原生回归用 `~/.local/share/mingli-master/venv/bin/python`（无 pytest，用 unittest 直跑）。
  **不要新建 venv 装 `sxtwl==2.0.7`**——该版本 PyPI sdist 缺 `src/JD.cpp`，构建必失败
- 参考站本地镜像：`qingnang/site`（已 gitignore），密度并排用它，不要联网抓
- 规则索引：`.runtime/v53-time-check-release/references/index/evidence-rules.jsonl`，G4 分档唯一数据源
- 发布工具：`core/mingli-master/scripts/release_deploy.py`（含 fail-closed provider 完备性门禁，
  见 `release_deploy.py:762` 加载 `audit_provider_completeness.DEDICATED_AUDIT_MODULES`）、
  `scripts/verify_frozen_runtime_release.py`

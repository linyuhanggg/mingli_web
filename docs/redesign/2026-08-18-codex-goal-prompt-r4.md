# Codex Goal 模式任务提示词 R4 — 古籍抽屉真实可见 + 时间层缺口 + 免费链 Accepted

> 用法：把本文件全文粘贴给 Codex，以 goal 模式（长时自动续轮）执行。目标仓库：`/Volumes/Lexar/code/mingli_web`。
> 当前分支：`codex/h-i-j-runtime-evidence`（不要切回 main，不要 rebase 已有提交）。
> 编制日期：2026-08-18，依据是阶段 H/I 完成后的独立验收（记录见 `docs/CHECKLIST.md` 第 15 节末尾两行）。
> 本文是**执行提示词，不是权威合同**。判据只在 `DESIGN.md` §17/§19/§20/§21/§22 与 `docs/CHECKLIST.md`。

---

## 0. 动手前必读

1. `docs/CHECKLIST.md` 第 15 节末尾两行 — H/I 验收结论与本轮待办
2. `artifacts/browser-evidence/2026-08-18-bazi-g5-density-runtime/README.md` — 真实数据密度证据，本轮问题的来源
3. `artifacts/runtime-evidence/2026-08-18-g1-self-verification-investigation/README.md` — 阶段 I 的路线调查与审批点
4. `DESIGN.md` §19.1（古籍命中卡）、§21.2（时间层连续性）、§22 G1
5. `docs/redesign/2026-08-18-codex-goal-prompt-r3.md` — 上一轮，阶段 H 已完成、I 已调查完，**不要重做**

## 1. 上一轮状态

- **H 已完成并提交** `7f28164`：真实 `/bazi` owner result 的四视口密度证据，`59 ≥ 33` 通过，`overflow=0`、最小字号 `13px`、截断 `0`
- **I 调查完成，用户已裁决：做 C + B，不做 A**。路线 C（仅依赖签名 release 的 ref 绑定核验）是原调查遗漏项，
  依据见该调查 README 的 2026-08-18 dated addendum。阶段 N 直接施工，不要重新论证选择
- **J 未开始**

**保持不动的约束**：`/liuyao`、`/meihua` 继续钉在 B 档且 `user_decision_pending=True`，本轮不得自行升档。

---

## 阶段 K · 古籍抽屉在真实结果页零渲染（最高优先级）

### K1 现象

H 阶段四个真实视口全部记录 `evidenceDrawerRendered=false`——**真实 `/bazi` 页面上一条古籍引文都没渲染**。
但阶段 G 已确认真实 Runtime 返回 7 条引文且 `7/7 verified_exact`。

已定位的线索：

- `web/src/components/readings/bazi-chart.tsx:1363` 的抽屉条件读 `facts.source_conditioned_patterns`
- 阶段 G 复核通过的 7 条走的是结果 `evidence[*]` 通道，字段为
  `evidence_ref / source_title / locator / excerpt / verification_status`

### K2 先定性，再动手

**不要直接改组件。**先查清并写出结论：

1. 真实 `/bazi` owner result 的 ViewModel 里 `source_conditioned_patterns` 到底是空数组、缺字段，还是有值但被过滤掉
2. `evidence[*]` 与 `source_conditioned_patterns` 是不是同一批规则的两种投影；若是，为什么页面只接了后者
3. 是投影层（`backend/app/charts/projectors.py`）没填，还是 Runtime 对该输入本来就不产出

把结论写进证据 README 再决定改哪一层。**若结论是 Runtime 对该输入确实不产出来源谓词命中，那就是事实，不得在前端用 `evidence[*]` 硬凑一个抽屉冒充 §19.1 的古籍命中卡**——那两者语义不同（一个是「谓词命中」，一个是「引用的原文」）。

### K3 修复后的验收

- 真实 `/bazi` 结果页上古籍引文可见，且按 §19.1 三部分渲染：原文原样、`predicate_audit` 可读化的「为什么适用」、书名与行号锚点
- 文案只能表达「此条适用」「条件成立」，不得出现「所以你…」「主…」「宜/忌…」（§19.1 / §22 G2）
- `fact_paths` 等内部引用不进正文（§17）
- 默认折叠抽屉，收起态只显示计数；键盘可达、`aria-expanded` 正确
- 重跑真实四视口证据，`evidenceDrawerRendered=true`，并从**页面上实际渲染出来的**引文重新抽清单跑
  `verify_citation.py`，退出码必须 `0`

---

## 阶段 L · 时间层在真实数据上的缺口

### L1 现象

真实 owner result 只开放本命与大运；`core_facts.year_layers` / `month_layers` / `day_layers` 未返回，
流年/流月/流日 tab 为 `data-status=unavailable` 且禁用。DESIGN §21.2 的时间层切换连续性在真实数据上无从体现。

### L2 要做什么

先查清属于哪一种，再决定动作：

- **输入未带目标时间**：H 的取数用的是「无目标时间」的 owner result。若带上目标时间就能产出三层，
  那这不是缺陷，是取证输入选错了——补一组带目标时间的真实证据即可
- **Runtime 未计算**：如实记录，归入算法缺口，不在前端造层
- **投影未接**：接上并补回归

**禁止**为了让三层「有内容」而用大运内容顶替、用 Fixture 补齐或前端自行推算。

### L3 验收

- 结论写进 `docs/CHECKLIST.md`
- 若属第一种，补一组带目标时间的真实四视口证据，并在 README 说明两组输入的差异
- 若属后两种，`data-status=unavailable` 的禁用态就是正确表现，补一条回归锁住「不可用层不得渲染任何内容」

---

## 阶段 M · 免费链 Accepted → Typed ReadingDocument（原 J）

### M1 现状

阶段 G 的真实纵链只到 `prepared`，证据 README 明确没把 `prepared` 写成 Accepted，这是对的。
付费链已有真实 V53 Worker → Accepted → Typed Document `1 passed`。缺的是免费 owner 结果这条路径。

### M2 要做什么

- 用重签后的签名 V53 跑真实免费纵链：guest session → ProfileVersion → `/api/v1/readings/preview` →
  Worker → **Accepted** → Typed `bazi-chart/v1` ReadingDocument
- 断言 `ReadingDocument.versions.runtime_release` 指向重签后的 release（manifest `7996b033…`）
- Accepted 正文必须逐字等于所引 `fact.display_text` / `finding.public_text` / `limit.public_text`，
  沿用既有 `bazi-deep-output-v1` 的抽取与去重门禁口径，不得拼接改写
- 从 Accepted 后的文档再抽一次引文跑 `verify_citation.py`，退出码必须 `0`

### M3 边界

若免费链按产品合同本来就只到 `prepared`（不产出 Accepted），**停下来把这个合同事实写清楚交用户确认**，
不要为了「闭合」新造一条免费 Accepted 路径。

---

## 阶段 N · G1 可核验性落地（用户已裁决：**做 C + B，不做 A**）

裁决依据见 `artifacts/runtime-evidence/2026-08-18-g1-self-verification-investigation/README.md`
的 2026-08-18 dated addendum 与 `docs/CHECKLIST.md` 对应记录。**不要重新论证路线选择，直接施工。**

### N0 先理解四步链条

| 步 | 内容 | 需要外置 fulltext |
|---|---|---|
| 1 | 页面引文 == 签名发行物记录的 `verbatim_quote` | 否 |
| 2 | `verbatim_quote_sha256` 校验通过（防篡改） | 否 |
| 3 | `path` + `sha256` 锁定语料文件版本，`anchor` 给出行号 | 否 |
| 4 | 该原文确实位于该书该行 | **是** |

**C 覆盖第 1–3 步，B 把第 4 步的依赖显式声明。A（fulltext 进发行物）本轮不做，不得擅自实施。**

### N1 路线 C：仅依赖签名 release 的核验模式

已实测的数据事实，直接用，不要重新调研：

- 数据源：`.runtime/v53-time-check-release/references/index/evidence-rules.jsonl`
- 1328 条规则下共 478 条 `classical_sources` 条目，**478 条全部**带 `verbatim_quote` 与
  `verbatim_quote_sha256`（覆盖率 100%）
- 条目字段：`anchor / location / path / sha256 / verbatim_quote / verbatim_quote_sha256`
- `verbatim_quote_sha256` == `sha256(verbatim_quote.encode("utf-8"))`，**无额外规范化**
- 页面 evidence 字段：`evidence_ref / source_title / locator / excerpt / verification_status`，
  `evidence_ref` 形如 `evidence:bazi/bazi/sanming-tonghui#R-01-02`，`locator` 形如 `fulltext.md#L34`
  与记录的 `anchor` 同形

核验必须是 **ref 绑定**，不是全库文本碰撞：

1. 由页面 evidence 的 `evidence_ref` 解析出 rule_id，在 index 中定位该规则记录
2. 逐字比对页面 `excerpt` 与该规则 `classical_sources[].verbatim_quote`
3. 比对页面 `locator` 与记录 `anchor`
4. 校验 `sha256(verbatim_quote) == verbatim_quote_sha256`
5. **任一步不满足即 fail closed**；`evidence_ref` 解析不到规则、规则无 `classical_sources`、
   或该条目缺 `verbatim_quote`，同样 fail closed，不得降级为「跳过」或「警告」

实现要求：

- 作为 `scripts/verify_citation.py` 的新模式（如 `--mode release-bound --release-root <path>`）或独立脚本，
  由你按现有代码结构决定，但**不得改动现有全文核验模式的阈值与判定语义**
- 退出码语义与现有一致：全通过 `0`，任一不通过非 `0`
- 用本轮真实数据实跑：`artifacts/runtime-evidence/2026-08-18-bazi-v53-g1/citations.txt`
  的 7 条应全部通过（已实测 release 自带记录逐字命中 `7/7`）
- 补负向回归：篡改一条 `excerpt` 一个字、篡改 `locator`、伪造一个 `evidence_ref`，三种情况都必须非 `0` 退出

### N2 路线 B：显式声明第 4 步的语料依赖

1. `docs/MINGLI_V51_WEB_INTEGRATION.md`：冻结核验环境定义为「签名 Runtime 的引用锚点与自带 `verbatim_quote`
   记录（第 1–3 步）+ 独立授权的 `mingli-master` 全文语料（第 4 步）」；写明签名 release 本身不内置全文，
   且这是既有发布合同（Core `.gitignore` 排除、README 声明不进发布包、`test_v51_release_surface.py` 断言）
2. `DESIGN.md` §22 G1：把「100%」的判定前提写清楚——第 1–3 步凭签名 release 判定，第 4 步需已安装独立语料根；
   并给出安装位置与可直接复制的复核命令。**只补充判定前提与命令，不得放宽 100% 与 `verified_exact` 的要求**
3. `scripts/verify_citation.py`：默认根或 `--root` 缺 `references/fulltext` 时 fail closed，错误信息必须包含
   目标路径、`--root` 用法、以及可直接复制的复核命令（含 `PYTHONPATH` 那一段）
4. 回归：对没有 fulltext 的签名 release 根运行全文模式必须非零退出，且错误含上述三项

### N3 验收

- C 与 B 的两种模式各有正向与负向回归，全部实跑并把退出码写进证据 README
- 证据落 `artifacts/runtime-evidence/2026-08-18-g1-release-bound-verification/`
- 回写 `docs/CHECKLIST.md`：两种模式各自证明了链条哪几步、哪几步仍需外置语料

## 每阶段完成定义（缺一不可）

- [ ] `make check` 全绿：Backend pytest + Ruff + mypy、Web 与 Admin 的 test/lint/typecheck、production build
- [ ] 该阶段产出已分组 commit（Conventional Commits，只含该阶段文件），**不 push**
- [ ] `docs/CHECKLIST.md` 第 15 节追加记录：日期 / 范围 / **当次实际跑出来的**门禁数字 / 证据路径
- [ ] 状态标注为「证据就绪，待用户验收」——**你没有批准权**

## 红线

1. **严禁** `git add -A`、`git checkout .`、`git reset --hard`；只 add 你明确改动的文件；不要切分支、不要 rebase 已有提交
2. **严禁把未实际运行的验证写成通过**。写进账本的每个数字必须是当次跑出来的
3. **不 push、不上传测试机、不部署**
4. `/liuyao`、`/meihua` 维持 B 档与 `user_decision_pending=True`，不得自行升档
5. 不得用 Fixture、`evidence[*]` 硬凑或前端推算冒充真实 Runtime 产出；产不出就如实记录为算法缺口
6. 不得改 `verify_citation.py` 阈值、替换 excerpt、挑样本
7. 重签后的 release 与两份回滚副本不得删除
8. 阶段 N 改 `DESIGN.md` §22 G1 时**只补充判定前提与复核命令，不得放宽 100% 与 `verified_exact` 的要求**；
   **不得实施路线 A（把 fulltext 打进发行物）**——授权未确认；其余需改权威合同规则的情况先停下交用户批准
9. 不新增依赖；不回归 §17 禁令与 §22 各门

## 环境事实（已实测，直接用）

- 当前分支 `codex/h-i-j-runtime-evidence`；`main` 已落后，本轮继续在该分支提交
- 全量门禁 `make check`；核心漂移 `make mingli-core-status`（当前 `220/0/0/0`）
- **浏览器走 Playwright + 系统 Chrome**：`chromium.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" })`，
  范式见 `web/scripts/audit-phase4.mjs:126`。**不要用 browser MCP 通道**
- **`verify_citation.py` 需要 `zhconv`，`~/.local/share/mingli-master/venv` 里没有**，实测可用调用：
  ```bash
  PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=.runtime/backups/2026-08-18-g1-resign/runtime-extras \
  ~/.local/share/mingli-master/venv/bin/python -B scripts/verify_citation.py --file <清单>.txt
  ```
  不加 `--root` 时默认用 `~/.codex/skills/mingli-master`，该语料库存在且可通过
- core 原生回归用 `~/.local/share/mingli-master/venv/bin/python`（无 pytest，用 unittest 直跑）；
  **不要新建 venv 装 `sxtwl==2.0.7`**（sdist 缺 `src/JD.cpp`）
- 参考站本地镜像 `qingnang/site`（已 gitignore）
- 规则索引 `.runtime/v53-time-check-release/references/index/evidence-rules.jsonl`，G4 分档唯一数据源

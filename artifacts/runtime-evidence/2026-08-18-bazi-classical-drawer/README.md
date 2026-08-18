# 阶段 K：真实八字古籍抽屉定性与验收证据

日期：2026-08-18。当前状态：**证据就绪，待用户验收**。本目录不是 `USER_ACCEPTED`。

## 定性输入

- 签名 Runtime：`.runtime/v53-time-check-release`
- 修复前 release manifest SHA-256：`7996b03356de9918484b83cdf84677b4e2946b1b55d7f0c504dd40cfd5ee7ca6`
- 输入与阶段 H 相同：`1994-04-30 05:55 +08:00`、男、北京市朝阳区、民用时、午夜换日
- 调用：真实 one-shot V53 `profile_preview`，只读 release，Runtime state 使用临时目录

## 定性结论

真实 Prepared brief 的 `source_conditioned_patterns` **不是空数组，也不是缺字段**；本次返回 6 条：

- `bazi/ditiansui-chanwei#DR-01-01`
- `bazi/qiongtong-baojian#QR-02-01`
- `bazi/qiongtong-baojian#QTB-M01`
- `bazi/sanming-tonghui#R-01-02`
- `bazi/sanming-tonghui#R-02-04`
- `bazi/ziping-zhenquan#ZPR-01`

但 Runtime 投出的每条 pattern 只有 identity、来源和 `source_dependency_id`，缺少 DESIGN §19.1 要求的 `fact_paths` 与 `predicate_audit`。`backend/app/charts/projectors.py` 的 `_source_conditioned_patterns` 对这两个字段 fail closed，因此整批解析为 `None`，最终 `BaziCoreFacts.source_conditioned_patterns=[]`。`project_public_fact_panel` 保留了原 fact；空数组不是隐私投影造成的。

同一 Prepared brief 返回 6 条完整 `verified_exact` evidence，包含 `evidence_ref / rule_id / source_title / locator / excerpt / verbatim_excerpt / verbatim_citations`。它们证明逐字引文闭合，但不包含“为什么这条规则适用于此盘”的谓词审计，所以不能用来替代 `source_conditioned_patterns`。页面只把两条通道按同一 `rule_id` 绑定后渲染，是正确的 fail-closed 设计。

因此故障位于 Runtime 的八字 pattern 事实输出链，不在 Web 抽屉条件，也不是 Runtime 对该输入零命中。修复必须让真实 Runtime 原样投出实际匹配得到的 `fact_paths` 与 `predicate_audit`，再由现有 Backend 绑定 exact evidence；不得在前端用 `evidence[*]` 硬凑 §19.1 古籍命中卡。

## 修复与新签名 release

Core `scripts/reading_engine/providers.py` 的八字公共投影原先把 `fact_paths` / `predicate_audit` 作为通用私有字段递归删除。修复只在 `source_conditioned_patterns` 子树保留这两个 §19.1 必需字段；其他八字候选和证据内部结构仍继续剥离。原生回归同时锁住“pattern 保留”和“其他位置不泄漏”，当次为 `16 tests / OK`。

- Core commit：`663543e65ae037843b03dca1dec9486293affc9d`（`fix(runtime): preserve bazi pattern audit`）
- 新 release：`220 files / 14 Providers / 55 packs / 1328 evidence`
- 新 release manifest SHA-256：`c451de5e4390c2a264a49aed972057081c61cb74ada160df308ac7a2af993c4b`
- `describe.manifest_digest`：`3403992cb31aebea19e69ec3b1280a5ef02718c5f9ca3e3f94448ef7b039facc`（未变）
- capability shape SHA-256：`fb9da7fa1969e449e91222a0f10a2076da2e8cca43d1083b531aa218ff31e042`（未变）
- 发布时 13 个 Provider 的独立语料源验证全部 `verified`；同步计划 `copy=1 / remove=0`，同步后验签 `verified=true`
- K 回滚点：`.runtime/v53-time-check-release-before-k-20260818/` 与 `.runtime/backups/2026-08-18-stage-k-resign/manifest.before.json`；两者旧 manifest 均为 `7996b033…`。阶段 G 的 release-before-G1 与 G1 manifest 备份原样保留。

冻结 release 验签当次返回 `status=ok`，source commit、manifest、220 个文件、14 Providers、55 packs、1328 evidence 全闭合。真实 V53 Backend 定向回归 `1 passed`；同一输入有 6 条 predicate pattern，其中实际可与 exact evidence 按 rule-id 闭合的 5 条进入抽屉，未绑定 pattern 继续 fail closed。Web 抽屉定向回归 `8 passed`，覆盖默认折叠、逐字多引文、predicate audit 可读化、未知 audit 原样显示、legacy summary 不冒充原文与 `fact_paths` 不进正文。

## 真实四视口浏览器证据

证据位于 [`browser/`](browser/)。以临时 PostgreSQL 跑到 Alembic head，登记上述新 V53，通过正式 `/bazi` 创建 guest、ProfileVersion 和 preview；one-shot Worker 使用签名 Runtime 计算盘面，仓库既有本地确定性 Model 只推进状态机。浏览器为 Playwright + 系统 Chrome，没有使用 Fixture 或 browser MCP。

360 / 768 / 1024 / 1440 四个视口均为：

- `evidenceDrawerRendered=true`，标题为「命中古法 6 条 · 可核验」；每档实际渲染 `6 cards / 6 quotes`
- 默认 `details.open=false`；`summary` 可聚焦并用 Enter 展开
- Chrome Accessibility tree 的角色为 `DisclosureTriangle`，折叠态 `expanded=false`，聚焦后仍为 false，展开后 `expanded=true`
- 每卡均有原文、为什么适用、书名与行号锚点；自动边界检查无「所以你」「宜」「忌」或句首结论式「主」
- `report.json` 为 `ok=true / failures=[]`，新 release manifest 为 `c451de5e…`

审计为截图需要主动打开抽屉，所以 768 / 1440 的可见结构事实计数为 `77 ≥ 33`；这不是 H 阶段默认折叠页面的密度替代值，H 的 `59 ≥ 33` 基线保持不变。

`browser/citations.txt` 由四个真实页面 DOM 的 blockquote 原样抽取并按逐字内容去重，共 6 行。未修改全文核验阈值、未替换 excerpt、未挑样本；调用：

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=.runtime/backups/2026-08-18-g1-resign/runtime-extras \
~/.local/share/mingli-master/venv/bin/python -B scripts/verify_citation.py \
  --file artifacts/runtime-evidence/2026-08-18-bazi-classical-drawer/browser/citations.txt
```

当次结果为 `6/6 verified_exact`，退出码 `0`。

## 阶段门禁

最终从头执行 `PYTHONDONTWRITEBYTECODE=1 make check`：Backend `1058 passed / 131 skipped`、Ruff 全通过、mypy `147 source files` 无错误、Web `80 files / 500 passed`、Admin `33 files / 123 passed`，两端 lint/typecheck 与 production build 全绿。

阶段 K 状态：**证据就绪，待用户验收**。未 push、未上传测试机、未部署；`/liuyao`、`/meihua` 仍维持 B 档与 `user_decision_pending=True`。

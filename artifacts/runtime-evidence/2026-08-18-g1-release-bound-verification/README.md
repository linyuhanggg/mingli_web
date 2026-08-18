# 阶段 N：G1 release-bound + 外部全文双链证据

日期：2026-08-18

结论：路线 C+B 已按用户裁决落地，不做 A。签名 Runtime release 自身足以按 `evidence_ref` 证明可核验链第 1–3 步；第 4 步仍须读取独立授权的 `mingli-master` 全文语料。两条链都 fail closed，且 `release-bound` 的成功不会被写成 `verified_exact`。

## 真实输入与发行物

- 页面 evidence：`artifacts/runtime-evidence/2026-08-18-bazi-v53-g1/vertical-result.json`
- 页面摘录清单：`artifacts/runtime-evidence/2026-08-18-bazi-v53-g1/citations.txt`
- 两者通过 `--citations-file` 断言逐行完全一致，共 7 条；没有挑样本或替换摘录。
- 签名规则索引：`.runtime/v53-time-check-release/references/index/evidence-rules.jsonl`，1328 条规则。
- 当前 release manifest SHA-256：`c451de5e4390c2a264a49aed972057081c61cb74ada160df308ac7a2af993c4b`。
- 外部全文根：`~/.codex/skills/mingli-master`。

## 路线 C：签名 release 第 1–3 步

执行：

```bash
python3 -B scripts/verify_citation.py \
  --mode release-bound \
  --release-root .runtime/v53-time-check-release \
  --file artifacts/runtime-evidence/2026-08-18-bazi-v53-g1/vertical-result.json \
  --citations-file artifacts/runtime-evidence/2026-08-18-bazi-v53-g1/citations.txt
```

结果：退出码 `0`，`7/7 verified_release_bound`。每条都由页面 `evidence_ref` 解析 `rule_id`，只在对应规则的 `classical_sources` 内逐字比对 `excerpt == verbatim_quote` 与 `locator == anchor`，再校验 `sha256(verbatim_quote.encode("utf-8")) == verbatim_quote_sha256`，并要求非空 `path + sha256`。输出见 `release-bound-positive.txt`。

三份负例都从上述真实 `vertical-result.json` 复制后只改第一条 evidence 的一个字段，不是正向证据，也不是 Fixture：

- `altered-excerpt.json`：摘录末尾增加一个“改”；`altered-excerpt-negative.txt` 为退出码 `1`，原因是页面摘录与对应规则逐字不等。
- `altered-locator.json`：`L34` 改成 `L35`；`altered-locator-negative.txt` 为退出码 `1`，原因是 locator 与 anchor 不一致。
- `fake-evidence-ref.json`：规则号改成 `FAKE`；`fake-evidence-ref-negative.txt` 为退出码 `1`，原因是索引找不到该 rule_id。

## 路线 B：外部全文第 4 步

执行：

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=.runtime/backups/2026-08-18-g1-resign/runtime-extras \
~/.local/share/mingli-master/venv/bin/python -B scripts/verify_citation.py \
  --file artifacts/runtime-evidence/2026-08-18-bazi-v53-g1/citations.txt
```

结果：退出码 `0`，外部全文共 54 部典籍 / 101701 段，真实七条为 `7/7 verified_exact`。输出见 `fulltext-positive.txt`。

对不含 `references/fulltext` 的签名 release 运行旧全文模式，`fulltext-missing-root-negative.txt` 为退出码 `1`；错误同时给出实际检查路径 `.runtime/v53-time-check-release/references/fulltext`、`--root <mingli-master-root>` 用法，以及带 `PYTHONPATH` 的可复制命令。签名 release 不内置全文是再分发授权边界，不是体积优化；明确授权前不得把全文放入 release。

## 回归与完整门禁

- 新增 CLI 回归：`backend/tests/test_verify_citation_script.py`，`2 passed`。覆盖 release-bound 正向、改摘录、改 locator、假 ref，以及旧全文模式 exact 正向和缺全文 actionable failure。
- `PYTHONDONTWRITEBYTECODE=1 make mingli-core-status`：退出码 `0`；`managed=220 / missing=0 / drifted=0 / unsigned=0 / source_sync_ready=yes`，见 `mingli-core-status.txt`。
- `PYTHONDONTWRITEBYTECODE=1 make check`：退出码 `0`。Backend `1063 passed / 132 skipped`；Ruff 全通过；mypy `147 source files` 无错误；Web `80 files / 501 passed`；Admin `33 files / 123 passed`；两端 lint、typecheck、production build 全绿。完整输出见 `make-check.txt`。

本阶段未改全文相似阈值、规范化规则、默认判定语义或样本内容；未 push、未上传、未部署。`/liuyao`、`/meihua` 继续保持 B 档且 `user_decision_pending=True`。

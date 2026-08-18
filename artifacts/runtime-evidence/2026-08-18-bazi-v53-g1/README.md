# V53 G1 本地真实 Runtime 闭环

日期：2026-08-18。状态：**证据就绪，待用户验收**。本记录只证明本地重签发行物的 G1 闭环，不是测试机/生产发布，也不代表 P4-007 用户批准。

## 发行物与回滚点

| 项目 | 重签前 | 重签后 |
|---|---|---|
| release manifest SHA-256 | `495dcd1d97ab3b5e9dabcafbf5103cf8af4d7845b735a314ec5efe2c2ccdd962` | `7996b03356de9918484b83cdf84677b4e2946b1b55d7f0c504dd40cfd5ee7ca6` |
| describe manifest digest | `3f8863b313f62a2b773720c98193486a0966dfbf8ba3335f8b1819e596e8ad1` | `3403992cb31aebea19e69ec3b1280a5ef02718c5f9ca3e3f94448ef7b039facc` |
| capability shape SHA-256 | `3bf92ce5d12005be6d50c01a76161e1754f49c210d6c064cb6a0e91d95db19ed` | `fb9da7fa1969e449e91222a0f10a2076da2e8cca43d1083b531aa218ff31e042` |
| source commit | `local-v53-core-source-20260817` | `403fbc259564c3dfdb57bfa10d492a8f4f9a7e0a` |
| signed files / Providers | `220 / 14` | `220 / 14` |

旧发行物完整保留在 `.runtime/v53-time-check-release-before-g1-20260818/`；重签前 manifest 另存 `.runtime/backups/2026-08-18-g1-resign/manifest.before.json`，220 个旧文件已校验。

使用 `core/mingli-master/scripts/release_deploy.py` 的源树校验、manifest 构建与目标同步逻辑本地重建。CLI dry-run 的 13 个专用 Provider 审计全通过；首次 apply 因 Lexar 盘的 exFAT `noowners` 会把 `0644` 实际呈现为 `0700` 而自动回滚。随后仍用同一发布模块的 `build_manifest` + `sync_destination`，按该文件系统的真实 `0700` 模式生成可验证 manifest，`verified=true / copy=20 / remove=0`。旧发行物的 manifest 也记录为 `0700`，没有伪造不可持久的权限。

`scripts/verify_frozen_runtime_release.py` 实测返回 `status=ok`：220 files、14 Providers、55 packs、1328 evidence rows。后端 V53 准入已同步新 source commit、manifest、describe 与 shape。新 Core `describe` 会显式发布 `transition_ids=[correct,restart]`，父仓严格 Result Schema 已允许该字段，同时保持真实旧 V51/V52 不带此字段时可读。

## 真实产品纵链与抽取

在隔离 SQLite 中创建 guest session 和已确认 ProfileVersion，通过正式 `POST /api/v1/readings/preview` 创建任务，启动通过准入门的 one-shot V53 Runtime，运行一次真实 Worker，再从同一 guest cookie 的 owner-scoped `GET /api/v1/readings/{id}/result` 取结果。

响应为 `prepared / bazi-chart/v1`，公开投影为 A 档，包含 19 facts、7 evidence、4 findings，判断规则为 19。这里没有把 `prepared` 写成 Accepted，也没有生造 ReadingDocument。纵链与全部 evidence 记录在 [vertical-result.json](vertical-result.json)。

抽取只按响应顺序遍历 `fact_panel.evidence[*].excerpt`，不读 Runtime 自报的 `verification_status` 作为最终判定，不按结果过滤。全部 7 行在 [citations.txt](citations.txt)。首次人工落盘曾把罕见字“耑”误录为“耍”，核验器当场报出 88% partial match；已与当次 owner result 逐字对齐更正。最终机械比对确认 `citations.txt == [evidence[*].excerpt]`，数量同为 7。

## 独立全文核验

未修改 `scripts/verify_citation.py`、未改 0.55 阈值、未替换 excerpt、未挑样本。用本地完整古籍库和 Core 已锁定的 `zhconv==1.4.3` 执行：

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=.runtime/backups/2026-08-18-g1-resign/runtime-extras \
/Users/yuhanglin/.local/share/mingli-master/venv/bin/python -B \
  scripts/verify_citation.py \
  --root "/Users/yuhanglin/Library/Mobile Documents/com~apple~CloudDocs/Documents/Codex/2026-07-31/xian/work/mingli-sync-20260731-091235/stage" \
  --file artifacts/runtime-evidence/2026-08-18-bazi-v53-g1/citations.txt \
  --json
```

最终退出码为 `0`，原始 JSON 输出在 [citation-verdicts.json](citation-verdicts.json)。

| # | Runtime evidence | 出处 | 独立判定 | 命中位置 |
|---:|---|---|---|---|
| 1 | `sanming-tonghui#R-01-02` | 《三命通会》 | `verified_exact` / 100% | `references/fulltext/bazi/sanming-tonghui/fulltext.md#L34` |
| 2 | `sanming-tonghui#R-02-04` | 《三命通会》 | `verified_exact` / 100% | `references/fulltext/bazi/sanming-tonghui/fulltext.md#L636` |
| 3 | `yuanhai-ziping#YR-M01` | 《渊海子平》 | `verified_exact` / 100% | `references/fulltext/bazi/yuanhai-ziping/fulltext.md#L109` |
| 4 | `ziping-zhenquan#ZPR-01` | 《子平真诠》 | `verified_exact` / 100% | `references/fulltext/bazi/ziping-zhenquan/fulltext.md#L179` |
| 5 | `ditiansui-chanwei#DR-01-01` | 《滴天髓阐微》 | `verified_exact` / 100% | `references/fulltext/bazi/ditiansui-chanwei/fulltext.md#L11` |
| 6 | `qiongtong-baojian#QR-02-01` | 《穷通宝鉴》 | `verified_exact` / 100% | `references/fulltext/bazi/qiongtong-baojian/fulltext.md#L319` |
| 7 | `qiongtong-baojian#QTB-M01` | 《穷通宝鉴》 | `verified_exact` / 100% | `references/fulltext/bazi/qiongtong-baojian/fulltext.md#L9`（另在《三命通会》 `#L450` 命中） |

边界保持不变：`/liuyao` 和 `/meihua` 仍为 B 档且 `user_decision_pending=True`；本轮没有 push、没有上传测试机、没有部署。

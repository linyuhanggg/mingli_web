# 阶段 M：免费八字 Accepted → Typed ReadingDocument

日期：2026-08-18

状态：证据就绪，待用户验收

## 合同结论

免费 `preview-v1` 不是 Prepared-only 合同。`docs/MINGLI_V51_WEB_INTEGRATION.md` 明确列出“免费八字概览”，共用 Worker 状态机按 Prepare → Prepared → Generate/Guard → Completing → Accepted 运行；Accepted 时同步固化 `AcceptedCopy` 与 `ReadingDocumentV1`。阶段 G 只看到 `prepared`，原因是当时只执行了一次 Worker claim，不代表产品合同止于 Prepared。

本阶段没有新造免费 Accepted 路径，只补了此前缺失的真实 PostgreSQL/API 纵链回归与证据。

## 真实纵链

测试通过正式 API 和 SQL repository 跑：

```text
guest session
  → confirmed ProfileVersion
  → POST /api/v1/readings/preview
  → signed V53 one-shot Runtime
  → Worker claim #1: Prepared
  → Worker claim #2: Completing
  → Worker claim #3: Accepted
  → AcceptedCopy + reading-document/v1 + bazi-chart/v1
```

PostgreSQL fixture 为独立随机 schema，结束后删除；Runtime release 复制到 pytest 临时目录并重新验签。最终关系绑定同时断言：

- `ReadingVersion.status=accepted`
- `ReadingJobRecord.status=complete`
- `ReadingDocument.versions.runtime_release=mingli-master-portable-core@5.3`
- SQL `RuntimeRelease.release_manifest_digest=c451de5e4390c2a264a49aed972057081c61cb74ada160df308ac7a2af993c4b`
- SQL `RuntimeRelease.source_commit=663543e65ae037843b03dca1dec9486293affc9d`

R4 原文写的 `7996b033…` 是 K 之前的重签版本；K 修复古籍抽屉后当前唯一准入制品已经更新为 `c451de5e…`，M 绑定当前制品，不倒退旧 manifest。

## Accepted 正文门禁

测试 Model 是仓库测试专用、确定性的 `_ExtractiveModel`，它不写新命理句子，只从 Prepared brief 机械抽取公开来源。免费合同本来最少允许 1 block；本测试主动生成 3 个 block，确保抽取与去重不是单条空转。

`vertical-result.json` 中 3 个 Accepted claim 分别逐字等于其唯一 `fact.display_text`：

1. `出生时间或四柱：1994-04-30T05:55:00+08:00`
2. `坐标来源：synthetic-fixture`
3. `性别：female`

测试逐块反查 `fact_refs / finding_refs / limit_refs`，要求恰好一个公开来源、`claim.text` 与来源逐字相等、source ref 不重复、text 不重复；文档 claim 顺序与候选一致。最终 `AcceptedCopy` 必须逐字等于这 3 块按双换行连接，再加固定披露「AI 辅助生成，仅供传统文化参考。」。这证明抽取式交付与字节一致，不代表真实模型内容质量已经验收。

## 引文复核

- [`vertical-result.json`](vertical-result.json)：Accepted owner result 与 Typed Document
- [`citations.txt`](citations.txt)：从上述 Accepted result 的 `fact_panel.evidence[*]` 中只按 `verification_status=verified_exact` 原样抽取

`citations.txt` 与 result 内 7 个 excerpt 逐行 `diff` 为零；未修改 `scripts/verify_citation.py`、阈值或 excerpt。全文模式当次返回：

```text
CITATION_VERIFICATION_EXIT=0 COUNT=7
```

## 定向门禁

- 真实 PostgreSQL + 签名 V53 免费纵链：`1 passed / 1 deselected`
- Ruff：通过
- 临时 55432 已停止且无监听

## 阶段门禁

最终从头执行 `PYTHONDONTWRITEBYTECODE=1 make check`，显式返回 `MAKE_CHECK_EXIT=0`：Backend `1061 passed / 132 skipped`（本阶段真实 PostgreSQL/V53 用例保持显式 opt-in，默认门禁如实 skip）、Ruff 全通过、mypy `147 source files` 无错误、Web `80 files / 501 passed`、Admin `33 files / 123 passed`，两端 lint/typecheck 与 production build 全绿。

阶段 M 状态：**证据就绪，待用户验收**。未 push、未上传测试机、未部署；`/liuyao`、`/meihua` 的 B 档与 `user_decision_pending=True` 未改。

# V53 Bazi preview Runtime evidence — citation gate remains open

本记录来自本机隔离 SQLite 的真实产品 API/Worker 链，不是 Web Fixture：

1. 以 `MINGLI_RUNTIME_ADAPTER=one-shot`、`v53-time-check` 已准入 manifest 启动 FastAPI。
2. 通过 `/api/v1/guest-sessions`、Profile draft/confirm、`POST /api/v1/readings/preview` 创建八字 preview。
3. 运行一次真实 Worker，再从 owner-scoped `GET /api/v1/readings/{id}/result` 读取结果。

结果摘要：`status=prepared`、`view_model.schema_version=bazi-chart/v1`、19 个事实、4 条 evidence、1 条 finding；能力投影为 A，Runtime active 规则 24 条，其中判断规则 19 条。此 preview 尚未形成 Accepted `ReadingDocument`，所以响应的 `document.versions.runtime_release` 为空；不把它写成 Accepted 或用户结果。

从 `fact_panel.evidence` 原样抽取的 4 条引文在 [2026-08-18-bazi-v53-preview-citations.txt](2026-08-18-bazi-v53-preview-citations.txt)。使用 Core 已锁定的 `zhconv==1.4.3` 补齐 Runtime venv 后执行：

```bash
PATH="$HOME/.local/share/mingli-master/venv/bin:$PATH" \
python3 scripts/verify_citation.py \
  --root "$HOME/.codex/skills/mingli-master" \
  --file artifacts/runtime-evidence/2026-08-18-bazi-v53-preview-citations.txt \
  --json
```

退出码为 `1`，逐条结果为：`not_found`、`partial_match`、`not_found`、`not_found`。失败原因和匹配位置保留在本次命令输出中；没有改阈值、挑样本或用全文库内容替换 Runtime excerpt。该记录完成了 D 的真实产出检查，但不能标记 G1 通过；C6 真实浏览器截图仍另行阻塞。

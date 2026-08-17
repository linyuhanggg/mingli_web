# classical-evidence-bindings-v1.json 基线

2026-08-17 谓词外包施工中，`references/matrices/classical-evidence-bindings-v1.json`
被改动（新增 `ziwei/ziwei-doushu-quanshu#ZW-01-01` 一条桩），导致文件哈希与
`scripts/build_evidence_index.py` / `scripts/reading_engine/evidence_rules.py`
两处 `CLASSICAL_EVIDENCE_BINDINGS_SHA256` pin 不符，编译与 Runtime 启动均失败。
仓库非 git 仓库，故在此保留两份可复原基线。

| 文件 | SHA-256 | 说明 |
|---|---|---|
| `pre-delivery-eb062cec.json` | `eb062cec…` | 施工前状态，等于当前代码 pin |
| `as-delivered-20260817.json` | `37582fed…` | 施工交付态，含 ZW-01-01 桩 |

`pre-delivery` 由交付态移除 ZW-01-01 后重新序列化复原，哈希精确等于代码 pin，
证明施工方对该文件的唯一改动就是那一条，无数据丢失。

**复原用的序列化格式必须是**（换任何一项都会改变哈希）：

    json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"

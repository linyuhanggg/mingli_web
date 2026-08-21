# 工作树 vs 签名制品 c451de5e 文件/哈希差集

Date: 2026-08-19 (CST). 只列表。未 resign，未覆盖 `.runtime/v53-time-check-release`，未改合同。

## 可复跑

```bash
python3 -B artifacts/runtime-evidence/2026-08-19-v53-core-signed-filediff.py
```

对照：签名 220 个文件的相对路径 ∩ `core/mingli-master`。跳过 `.git` / `__pycache__` / `.pyc`。

## 实测 totals

| 项 | 数 |
|---|---:|
| 签名 inspector `manifest_sha256` | `c451de5e4390c2a264a49aed972057081c61cb74ada160df308ac7a2af993c4b` |
| `source_commit` | `663543e65ae037843b03dca1dec9486293affc9d` |
| 签名 walk | 220（与 manifest files 一致） |
| core walk | 826 |
| 两边都有 | 220 |
| 哈希相同 | **216** |
| 哈希不同 | **4** |
| 只在签名 | **0** |
| 只在 core 的 scripts/references/adapters | 559（测试、文档、未打进制品的源；不是本刀 dirty 差） |

## 哈希不同（4，即脏树 Claim Unit 源码）

| 路径 | 签名 bytes | core bytes |
|---|---:|---:|
| `scripts/bazi_fact_adapter.py` | 78981 | 79186 |
| `scripts/bazi_reasoning_tools.py` | 39010 | 43861 |
| `scripts/fact_contracts/bazi.py` | 41901 | 45236 |
| `scripts/reading_engine/providers.py` | 278789 | 283781 |

这 4 个就是 `day-master-root-support-v1` 源码差。要进制品必须**新目录 resign**。现在禁止。

## 不扩进「必须 resign」的

- 559 条 core-only release-like：多数是测试 / 书目笔记 / fixtures，签名树本来就不收（C+B 无 `fulltext/` 等）。
- 签名 220 个文件都能在 core 找到对应路径（only_signed=0）。
- 未改、未覆盖当前 release。

# 准入钉死检查（c451de5e / 663543e / 220）

Date: 2026-08-19 (CST). 只读。未改 FastAPI / 合同 / .runtime，未 resign。

## 可复跑

python3 -B artifacts/runtime-evidence/2026-08-19-v53-admission-pin.py

exit 0 = 仍是准入树；非 0 = 被覆盖或混入 V52 / 源码泄漏。

## 本次实测 pin_ok=True

- inspector manifest_sha256 = c451de5e4390c2a264a49aed972057081c61cb74ada160df308ac7a2af993c4b
- source_commit = 663543e65ae037843b03dca1dec9486293affc9d
- manifest_files = 220，walk_files = 220
- turns.py 无 relationship_signals（不是 V52 混进来）
- providers.py 无 day-master-root-support-v1（源码没漏进制品）
- 旁边的 .runtime/v52-relationship-release 仍是另一份制品 bef3df25 / da46e7c0

覆盖或把 V52 哈希/关系层代码放进 v53-time-check-release 会 FAIL。

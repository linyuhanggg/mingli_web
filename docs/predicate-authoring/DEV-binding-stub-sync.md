# 开发文档 · binding 桩同步工具

> 目标读者：实现这个工具的开发者（人或模型）。
> 文档里标「已核验」的事实都是在本机 `core/mingli-master` 上实测过的，可以直接依赖；
> 没标的是设计选择，可以在满足验收标准的前提下自行决定。

---

## 1. 要解决的问题

给规则写谓词这件事**目前没有任何合法路径能完成**。

上一轮外包施工编辑 `evidence-scope-bindings-v1.yaml` 写了 9 条紫微谓词，然后：

```
$ python3 scripts/build_evidence_index.py --check
ValueError: classical evidence binding manifest hash mismatch
```

编译失败，Runtime 拒绝启动，14 个 Provider 全部不可用。

根因不是施工方写错，而是两条引擎约束互相咬住：

1. **有谓词的规则必须有 binding 条目**，且两个集合**完全相等**
2. **binding manifest 的 SHA-256 被硬编码在两处代码里**，改文件就对不上

于是「加一条谓词」必然要求「加一条 binding 条目」，而后者必然破坏 pin。施工方
手工补了 1 条桩（状态填得是对的），但 9 条谓词只补 1 条桩，键集仍不相等，且 pin
没同步。**这是工具链缺口，不是施工质量问题。**

你要补的就是这条路径。

---

## 2. 引擎侧约束（已核验）

### 2.1 键集必须完全相等

`scripts/build_evidence_index.py` `_apply_classical_evidence_bindings()`（约 1213 行）：

```python
predicate_rule_ids = {
    str(record["rule_id"])
    for record in records
    if record["required_fact_predicates"] or record["excluded_fact_predicates"]
}
if set(bindings) != predicate_rule_ids:
    missing = sorted(predicate_rule_ids - set(bindings))
    unknown = sorted(set(bindings) - predicate_rule_ids)
    raise ValueError(f"classical binding coverage mismatch: {...}")
```

注意是 `!=`，不是子集判断。**多一条和少一条都会失败。**所以工具必须双向同步：
补缺失的桩，也要删掉已经没有对应谓词的条目。

### 2.2 哈希 pin 在两处，且必须相同

| 位置 | 常量 |
|---|---|
| `scripts/build_evidence_index.py` | `CLASSICAL_EVIDENCE_BINDINGS_SHA256` |
| `scripts/reading_engine/evidence_rules.py` | `CLASSICAL_EVIDENCE_BINDINGS_SHA256` |

`build_evidence_index.py` 里的注释明确说这是故意重复的——构建期和运行期都必须
pin 同一份独立审计过的清单。运行期校验器 `evidence_rules._validate_rule()` 会检查：

```python
if BUILD_BINDINGS_SHA256 != CLASSICAL_EVIDENCE_BINDINGS_SHA256:
    raise ValueError("build/runtime classical evidence manifest pins differ")
```

**只改一处会在运行期炸，而且报错跟当前修改看不出关系。**

### 2.3 加载器支持覆盖期望哈希

`load_classical_evidence_bindings()`（206 行）签名：

```python
def load_classical_evidence_bindings(
    *, root: Path = ROOT,
    manifest_path: Path | None = None,
    expected_sha256: str | None = None,
) -> dict[str, Any]
```

`expected_sha256` 是显式覆盖参数。工具在「pin 还没更新」的中间态需要读 manifest 时，
可以传入文件实际哈希绕过 pin 检查。**这不是 hack，是加载器声明的接口。**

### 2.4 编译器支持跳过 binding 门禁

`compile_evidence_rules()`（1278 行）签名：

```python
def compile_evidence_rules(
    root: Path = ROOT, *,
    enforce_classical_bindings: bool = True,
    verify_research_sources: bool = False,
    research_root: Path | None = None,
) -> list[dict[str, Any]]
```

传 `enforce_classical_bindings=False` 就能拿到规则记录而不触发 §2.1 的键集检查。
**这是本工具的入口**——不需要 monkeypatch，也不需要重写解析逻辑。

### 2.5 三个摘要函数必须复用，不能重写

| 函数 | 位置 | 产出字段 |
|---|---|---|
| `canonical_predicate_signature(required, excluded)` | 146 行 | `applicability_signature` |
| `canonical_rule_record_digest(record)` | 156 行 | `rule_record_digest` |
| `_classical_binding_digest(binding)` | 172 行 | `binding_digest` |

`_classical_binding_digest` 对**除 `binding_digest` 本身以外**的所有字段计算：

```python
payload = {key: value for key, value in binding.items() if key != "binding_digest"}
```

自己重新实现规范化逻辑必然对不上，编译器会在 302 行拒绝：
`if binding.get("binding_digest") != _classical_binding_digest(binding)`。

### 2.6 序列化格式（已核验，实验确认）

```python
json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
```

**换任何一项都会改变哈希。**验证方法：取交付态 manifest，移除
`ziwei/ziwei-doushu-quanshu#ZW-01-01`，按上式重新序列化，SHA-256 精确等于
当前代码 pin 的 `eb062cec…`。试过的其他组合（`indent=None`/`4`、
`separators=(',',':')`、`sort_keys=False`、无尾换行）全部不匹配。

manifest 的顶层键是 `audit_note` / `bindings` / `policy` / `schema_version`，
`sort_keys=True` 会把它们按字母序排列——这已经是文件现状，不要改动顶层结构。

---

## 3. 目标

一条命令让「新增谓词后编译恢复通过」成为可重复操作：

```bash
python3 scripts/sync_binding_stubs.py
```

具体：

1. 找出「有谓词但 manifest 里没有条目」的规则 → 生成未核对状态的桩
2. 找出「manifest 里有条目但规则已无谓词」的 → 删除
3. 按 §2.6 格式重写 manifest
4. 把新哈希同步写入 §2.2 的两处 pin
5. 幂等：连续跑两次，第二次报告 0 变更且哈希不变

---

## 4. 设计

### 4.1 CLI

```
python3 scripts/sync_binding_stubs.py [--dry-run] [--tree PATH] [--python PATH]

--dry-run   只报告将新增/删除哪些条目，不写任何文件
--tree      源码树，默认 core/mingli-master
--python    Runtime venv 的 python，默认 ~/.local/share/mingli-master/venv/bin/python
```

退出码：`0` 成功（含 dry-run）；`1` 同步后自检未通过；`2` 环境问题。

### 4.2 算法

```
1  records = compile_evidence_rules(root=tree, enforce_classical_bindings=False)
2  needed  = {r["rule_id"] for r in records if r 有 required/excluded 谓词}
3  manifest = load_classical_evidence_bindings(
                root=tree, expected_sha256=<manifest 文件实际哈希>)
4  current = set(manifest["bindings"])
5  to_add    = needed - current
6  to_remove = current - needed
7  对 to_add 里每条：按 §4.3 生成桩（三个摘要用 §2.5 的函数算）
8  对 to_remove 里每条：从 bindings 删除
9  按 §2.6 序列化写回 manifest
10 计算新文件 SHA-256，写入两处 pin（§2.2）
11 自检：build_evidence_index.py --check 必须 pass
```

第 3 步为什么要传 `expected_sha256`：此刻 pin 还是旧值，不传会被 §2.2 的检查拦住。

第 7 步的 `rule_record_digest` 要用**该规则编译出的完整 record**去算，不是用桩本身。
参照 `_apply_classical_evidence_bindings` 里的用法。

### 4.3 桩条目形状

`references/matrices/classical-evidence-bindings-v1.json` 里现存的
`ziwei/ziwei-doushu-quanshu#ZW-01-01` 状态字段是正确的，可直接当模板：

```json
{
  "applicability_signature": "<canonical_predicate_signature 算出>",
  "binding_digest": "<_classical_binding_digest 算出>",
  "classical_sources": [],
  "mechanical_location_status": "unverified",
  "rule_id": "<规则 ID>",
  "rule_record_digest": "<canonical_rule_record_digest 算出>",
  "semantic_verification_status": "inactive_unverified",
  "verification_method": "runtime_inactive_pending_semantic_source_applicability_audit",
  "verification_status": "inactive_unverified"
}
```

三个状态字段的含义：

| 字段 | 桩的取值 | 什么时候才能变 |
|---|---|---|
| `mechanical_location_status` | `unverified` | 原文位置逐字校对通过后 → `verified_exact` |
| `semantic_verification_status` | `inactive_unverified` | 人工确认谓词忠实表达原文后 → `verified` |
| `verification_status` | `inactive_unverified` | 同上 |

**工具绝对不能生成 `verified`。**桩的语义是「谓词已写、原文核对未做」。
`verified` 是人工审计授予的，是这套系统唯一的人工门禁——工具越过它，
整个来源可追溯性就失效了。运行期靠这个字段决定 `runtime_active`：

```python
expected_active = binding["verification_status"] == "verified"
```

所以桩生成后规则保持不激活，这是预期行为，不是缺陷。

### 4.4 pin 同步

两处常量的当前写法是跨行的：

```python
CLASSICAL_EVIDENCE_BINDINGS_SHA256 = (
    "eb062cecfb1bafa065fa71ce3af1a6e13f41946f437d150bfe3a276262eb5d63"
)
```

替换时保留这个格式。建议用「定位常量名 → 替换紧随其后的 64 位十六进制串」的方式，
不要整行重写，避免破坏注释。`build_evidence_index.py` 里那段注释说明了为什么两处
重复，**不要删掉它**。

---

## 5. 边界与禁止项

| 允许 | 文件 |
|---|---|
| 新建 | `scripts/sync_binding_stubs.py` |
| 修改 | `references/matrices/classical-evidence-bindings-v1.json`（只经工具，按 §4.3 生成桩） |
| 修改 | 两处 `CLASSICAL_EVIDENCE_BINDINGS_SHA256` 常量值 |

| 禁止 | 原因 |
|---|---|
| 生成 `verified` / `verified_exact` 状态 | 越过唯一的人工审计门禁 |
| 改 `references/books/**`、`references/fulltext/**` | 原文，改一字破坏 `quote_hash` |
| 改 `references/index/evidence-rules.jsonl` | 编译产物，由 `build_evidence_index.py` 写 |
| 改 `evidence-scope-bindings-v1.yaml` 里已有的 9 条紫微谓词 | 上一轮成果，本轮只补工具不动内容 |
| 为了让编译通过而删除谓词 | 那是掩盖问题 |
| 改 `scripts/` 下其他引擎逻辑 | 超出范围 |

**这个仓库不是 git 仓库**，没有版本历史可回退。改 manifest 或 pin 前自己先备份。

---

## 6. 验收标准

六步全绿才算完成。所有调用 Runtime venv 的命令都要带 `PYTHONDONTWRITEBYTECODE=1`
（原因见 §8.2）。

```bash
# 1 干跑：看清将新增/删除哪些桩
python3 scripts/sync_binding_stubs.py --dry-run
```

```bash
# 2 实跑
python3 scripts/sync_binding_stubs.py
```

```bash
# 3 编译必须 pass（当前是 FAIL: classical evidence binding manifest hash mismatch）
cd core/mingli-master && PYTHONDONTWRITEBYTECODE=1 \
  ~/.local/share/mingli-master/venv/bin/python scripts/build_evidence_index.py --check
```

```bash
# 4 Runtime 必须能起来，capabilities 非空
cd core/mingli-master && echo '{"kind":"describe"}' | PYTHONDONTWRITEBYTECODE=1 \
  ~/.local/share/mingli-master/venv/bin/python scripts/runtime_launcher.py
```

```bash
# 5 上一轮 9 条紫微谓词现在必须能测出成立率
python3 scripts/verify_predicates.py --route ziwei --since snapshots/ziwei-before.json
```

```bash
# 6 幂等：再次干跑应报告 0 变更
python3 scripts/sync_binding_stubs.py --dry-run
```

判据说明：

- **第 3 步是核心目标。**当前是 FAIL，跑通它就是这个任务成立的标志。
- **第 5 步**跑通说明整条链路恢复。那 9 条谓词的成立率是多少**不是本轮的验收内容**，
  你只要让它能测出数字，原样贴出即可，不需要解读也不需要去改谓词。
- **第 6 步幂等性是硬要求。**如果工具每次跑都产出不同哈希（例如字典序不稳定、
  或时间戳混进内容），pin 就永远追不上，会变成隐性死循环。

---

## 7. 回滚

两份基线在
`docs/releases/evidence/2026-08-18-binding-manifest-baselines/`：

| 文件 | SHA-256 | 状态 |
|---|---|---|
| `pre-delivery-eb062cec.json` | `eb062cec…` | 施工前，等于当前代码 pin |
| `as-delivered-20260817.json` | `37582fed…` | 施工交付态，含 ZW-01-01 桩 |

回滚到「编译能过但没有那 9 条谓词」的状态：拷回 `pre-delivery-eb062cec.json`，
pin 保持 `eb062cec`，并从 YAML 移除 9 条紫微谓词。这是下策，只在工具做不出来时用。

---

## 8. 附录

### 8.1 代码位置索引

`core/mingli-master/scripts/build_evidence_index.py`

| 行 | 内容 |
|---|---|
| 146 | `canonical_predicate_signature` |
| 156 | `canonical_rule_record_digest` |
| 172 | `_classical_binding_digest` |
| 206 | `load_classical_evidence_bindings`（含 `expected_sha256` 覆盖） |
| 302 | `binding_digest` 一致性校验 |
| 1213 | `_apply_classical_evidence_bindings`（键集相等检查在此） |
| 1278 | `compile_evidence_rules`（含 `enforce_classical_bindings` 开关） |
| `main()` | `--check` 比对渲染结果与磁盘索引是否一致 |

`core/mingli-master/scripts/reading_engine/evidence_rules.py`

| 内容 |
|---|
| `CLASSICAL_EVIDENCE_BINDINGS_SHA256`（运行期 pin） |
| `_validate_rule`（校验 pin 一致、binding 存在、状态与 `runtime_active` 匹配） |

### 8.2 一个必踩的坑

所有调用 `~/.local/share/mingli-master/venv/bin/python` 的命令都要带
`PYTHONDONTWRITEBYTECODE=1`。漏了会往 venv 写 `__pycache__`，触发运行时完整性
校验，之后八字之类的 Provider 会以一个完全看不懂的错误失败：

```
"The V4 transaction did not produce a complete result."
```

补救：

```bash
find ~/.local/share/mingli-master/venv -type d -name __pycache__ -exec rm -rf {} +
```

### 8.3 相关文档

- `docs/predicate-authoring/SPEC.md` — 谓词施工规范（本工具服务的下游流程）
- 本工具做完后 SPEC.md 第 1 节需要改写：binding manifest 从「禁改」改为
  「只能经 `sync_binding_stubs.py` 生成桩，不能手写 verified」。这一条由算法侧改，
  不在本任务范围。

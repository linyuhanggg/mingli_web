# G1 可核验性路线调查

日期：2026-08-18。状态：**调查结论就绪，路线 B 待用户批准**。本文只记录阶段 I 的先行调查，不修改 `DESIGN.md` 规则，不宣称阶段 I 完成。

## 当前事实

- 签名 V53 release 的 manifest 管理 220 个文件，目录总占用约 9.14 MiB；`references/` 只含 `books / catalog / index / inference / matrices / source-excerpts`，没有 `references/fulltext/`。
- 本机已安装的独立全文语料位于 `~/.codex/skills/mingli-master/references/fulltext/`：57 个文件，其中 54 个 `fulltext.md`，约 13.53 MiB、181,131 行。
- `core/mingli-master` 源 checkout 没有 `references/fulltext/`；`.gitignore` 排除该目录，`README.md` 明确写着“本地研究语料，不进入发布包，也不上传仓库”，`scripts/test_v51_release_surface.py` 明确断言 release surface 不得包含它。
- `release_deploy.py` 的 `PRESERVE_PREFIXES` 会让同步器遍历、删除和 extra-file 校验都跳过 `references/fulltext`。它的含义是“保留目标机已经另行安装的外置语料”，不是“把 fulltext 纳入签名 manifest”。
- `scripts/verify_citation.py` 当前默认寻找 `~/.codex/skills/mingli-master` 或 `~/.claude/skills/mingli-master`；显式 `--root` 也要求 `<root>/references/fulltext` 存在。缺失时会非零退出，但只打印笼统的“找不到全文库”或“请用 --root 指定”，没有安装位置与可执行复核命令。

## 路线 A：全文纳入签名发行物

量化影响：约增加 57 个文件和 13.53 MiB，release 从约 9.14 MiB 增至约 22.67 MiB，体积约增加 148%，manifest 约从 220 项变成 277 项。之后必须重新生成 manifest、重签 V53、更新父仓冻结的 release manifest/describe/capability shape 准入值，并保留新的重签前备份。

真正的影响不在体积：当前 fulltext 不在 Core Git 源树，发布器只接受 Git 跟踪且列入 `release/runtime-closure-v1.json` 的文件。实施 A 必须改变“语料不进 Git/发行物”的既有来源与分发合同，修改 `.gitignore`、Core README、runtime closure、release surface 测试和发布工具输入边界；还要确认 54 部全文的再分发授权。`PRESERVE_PREFIXES` 也要重定义，否则签名文件和外置保留树会产生双重所有权。

对 G1 的效果最好：单独拿到签名 release 即可复核。但它不是局部修复，是 Core 发布合同与语料分发策略变更。

## 路线 B：显式声明独立语料依赖

发布影响：签名 V53、220 文件 manifest、Runtime 准入值和回滚副本都不变；保留当前“运行闭包”和“研究语料”分离。需要修改：

1. `docs/MINGLI_V51_WEB_INTEGRATION.md`：冻结核验环境由签名 Runtime 的引用锚点加独立授权的 `mingli-master` 全文语料组成；签名 release 本身不内置全文。
2. `DESIGN.md` §22 G1：明确 100% 指页面引文在已安装独立语料根下全部 `verified_exact`，并给出安装位置和命令；缺语料不算通过。
3. `scripts/verify_citation.py`：显式 `--root` 或默认根缺 `references/fulltext` 时 fail closed，并打印可执行修复指引。
4. 回归：对现有但没有 fulltext 的签名 release 根运行核验必须非零退出，错误中必须包含外置语料目标路径、`--root` 用法和复核命令。

可执行依赖说明拟定为：从项目授权的 `mingli-master` 研究语料源取得 `references/fulltext/`，安装到独立根（默认 `~/.codex/skills/mingli-master/references/fulltext/`；也可使用任意 `<research-root>/references/fulltext/`），然后运行：

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=.runtime/backups/2026-08-18-g1-resign/runtime-extras \
~/.local/share/mingli-master/venv/bin/python -B \
  scripts/verify_citation.py \
  --root ~/.codex/skills/mingli-master \
  --file artifacts/runtime-evidence/2026-08-18-bazi-v53-g1/citations.txt
```

对 G1 的实际效果：任何拥有签名 Runtime 但没有授权全文语料的人会得到明确的 fail-closed 指引，不再误以为 release 内锚点可直接打开；装好语料后仍要求每条引文 100% `verified_exact`，不降低阈值、不换 excerpt、不挑样本。代价是 G1 命题从“release 单体自证”明确为“签名 Runtime + 声明的独立语料依赖可当场证伪”。

## 选择与审批点

建议选择**路线 B**。理由：它符合 Core 已冻结的发布面、外置语料保留机制与当前授权边界；路线 A 会扩大到 Core 语料分发合同，不是阶段 I 所需的最小闭合。

路线 B 必须修改 `DESIGN.md` §22 G1 的规则表述。按本轮红线 7，实施在此停止，等待用户明确批准。批准后再改权威合同、核验器与回归，执行当阶段 `make check`，回写 CHECKLIST 并分组提交。

---

## 2026-08-18 追加：路线 C（原调查遗漏，用户已选定 C + B）

本节是 dated addendum，不覆盖上文原始调查结论。

### 遗漏的事实

签名 release 的 `references/index/evidence-rules.jsonl` **已经自带逐字原文与哈希**，无需 fulltext：

- 1328 条规则下共 478 条 `classical_sources` 条目，**478 条全部带 `verbatim_quote` 与 `verbatim_quote_sha256`，覆盖率 100%**
- 条目字段为 `anchor / location / path / sha256 / verbatim_quote / verbatim_quote_sha256`
- `verbatim_quote_sha256` 实测等于 `sha256(verbatim_quote.encode("utf-8"))`，无额外规范化
- `path` + `sha256` 锁定该引文所属语料文件的具体版本，`anchor` 给出行号
- 本轮 7 条页面引文在 release 自带记录中**逐字命中 7/7**

### 因此可核验链条可拆为四步

| 步 | 内容 | 需要 fulltext |
|---|---|---|
| 1 | 页面引文 == 签名发行物记录的 `verbatim_quote` | 否 |
| 2 | `verbatim_quote_sha256` 校验通过（防篡改） | 否 |
| 3 | `path` + `sha256` 锁定语料文件版本，`anchor` 给出行号 | 否 |
| 4 | 该原文确实位于该书该行 | **是** |

原调查把「可核验」整体等同于第 4 步，因而只看到 A/B 两条路。实际上第 1–3 步**仅凭签名 release 即可完成**。

### 路线 C 定义

新增一种仅依赖签名 release 的核验模式：按页面 evidence 的 `evidence_ref` 反查规则记录，
逐字比对 `excerpt` 与 `verbatim_quote`、比对 `locator` 与 `anchor`、校验哈希，任一不满足即 fail closed。
它证明「页面显示 == 签名发行物记录，且记录未被篡改」，不证明「记录 == 书上原文」——后者仍归第 4 步。

### 选定方案与理由

用户选定 **C + B，不做 A**：

- **C 立即实施**：零发行物改动、零授权风险，实测已 7/7 可通过，让任何拿到 release 的人当场完成第 1–3 步
- **B 同步落地**：把第 4 步的独立语料依赖显式写进权威合同，并让 `verify_citation.py` 缺语料时 fail closed 并给出可执行指引
- **A 暂不做**：阻力不在 13.53 MiB 体积，而在 54 部全文的再分发授权——语料中既有繁体白文，也有已标点整理的简体本，
  标点整理本通常另有著作权。在授权未确认前把它们打进签名发行物等于把法律风险固化进制品。
  且 C 已取得 A 的大部分实用价值；日后若确认授权，A 可增量补做，C 建立的核验模式届时成为 release 内快速通道。

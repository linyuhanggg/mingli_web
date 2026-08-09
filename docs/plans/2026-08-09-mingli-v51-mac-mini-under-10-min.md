# Mingli V5.1 Mac mini 双测试通道实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use `executing-plans` task by task. Use `codebase-design` for the public seam and `tdd` for every RED→GREEN slice.

**Goal:** 只用这台 M4 Mac mini 建立两个互不冒充的标准命令：`native-full` 是日常开发/合并门禁，完整 1584 项且硬限 600 秒；`linux-certify` 是最终 `linux/amd64` 制品的独立发布认证，也在同一台 Mac mini 上运行，但先通过 VZ+Rosetta tracer 和真实基线决定如何达到 600 秒，未达到就保持 RED。

**Architecture:** `LocalFullGate` 只暴露 profile、不可变 PreparedInputs 引用、输出父目录、期限和槽位。原生与 Linux 各有自己的命令、时钟、报告和证据域；不存在“一个 600 秒命令同时跑两套 1584”的承诺。Linux 路径复用并收敛现有 `run_lima_gate.py`、`audit_runtime.py`、`verify_release.py`，不另造平行准入实现。

**Tech Stack:** Python 3.14、Lima 2.2 VZ、Apple Rosetta/binfmt、rootless Docker、现有 mingli-master V5.1 release scripts、pytest、Ruff、mypy、CycloneDX。

---

## 已确认事实和精确断点

当前基线是分支 `feat/mingli-v51-web-integration` 的提交：

```text
1c0cf7ef852a871d390b2db96f2f5b9e150873c9
```

Task 8 现有实现仍是未提交 WIP。它没有合格的 `release-5.1.json`，不能叫准入完成。

被人工终止的 QEMU Gate 快照：

```text
time:                      2026-08-09T06:55:31Z
controller elapsed:        02:09:05
production command:        01:58:35
phase:                     provider-matrix-a，未完成；matrix-b 未开始
container:                 cc6cdcf388149c9f27df838aad27c2c7edaf8246ce42045da71db6357eb90c96
CPU / memory / PIDs:       106.61% / 534.4 MiB / 10
exit:                      130
release-5.1.json:          absent
status:                    ABORTED，绝不是 PASS
```

该容器和九个临时卷已明确清理；没有残留 `run_lima_gate.py`、`audit_runtime.py` 或 `audit_provider_completeness.py` 进程。

原生通道已有新鲜实测，不再把它当猜测：

```text
source:                    独立临时 clone，HEAD=494ce0bba174a77800daf9b9c38ce9c9166d9a94
host:                      Mac mini M4，10 cores，16 GiB
runtime:                   native CPython 3.14.6
jobs:                      10
research root:             原始只读 research root
targets/modules/tests:     126 / 93 / 1584
failed_modules:            0
suite elapsed:             434.62s
CanonicalMatrixSnapshot:  2 tests，415.25s
```

这证明 native lane 已经能在 600 秒内完整执行。正式 wrapper 仍要重新跑并绑定机器证据，但不要再拆 Provider、改 signed runner 或为了原生性能造复杂调度器。

硬合同不变：

- signed source commit `494ce0b...` 不修改、不打补丁；
- 完整制品始终是 217 个签名文件、13/13 Providers、55/55 reference packs、1328 evidence rows；
- `bazi/fortune/liuyao` 只是 P0 产品曝光白名单；
- native PASS 不能替代 Linux x86_64 PASS；
- 不删测试、不跳过测试、不降低断言，不手填 release evidence；
- QEMU 可以继续当慢速 release fallback，但不能冒充本地 600 秒通道。

## 两个命令和两个证据域

| 命令 | 用途 | 必跑内容 | 计时合同 | 主要报告 |
|---|---|---|---|---|
| `native-full` | 默认开发/合并门禁 | signed 完整 suite，126 targets / 93 modules / 1584 tests / 0 failed | 独立硬限 `<=600s`，已实测 434.62s | `native-full-5.1.json` |
| `linux-certify` | Linux 发布认证 | exact final `linux/amd64` image 的 1584、13/55/1328、A/B、P0、probes、restore、SBOM、verifier | 独立计时；先 tracer/基线，目标 `<=600s`，超时即 RED | `release-5.1.json` |

不要求一次命令同时跑 native 与 Linux。以后可以做一个便利协调器并行启动两个独立 profile，但它不能合并证据，也不能在未实测前声称总耗时小于 600 秒。

## 最小公开接口

调用者不再传可变的 release/research/python 路径，而是只传一个已哈希的 PreparedInputs manifest：

```python
LocalProfile = Literal["native-full", "linux-certify"]


@dataclass(frozen=True)
class PreparedInputsRef:
    path: Path
    sha256: str


@dataclass(frozen=True)
class LocalFullRequest:
    profile: LocalProfile
    prepared_inputs: PreparedInputsRef
    output_parent: Path
    deadline_seconds: int = 600
    slots: int = 10


@dataclass(frozen=True)
class TimelineEntry:
    command_id: str
    slots: int
    started_monotonic: float
    finished_monotonic: float
    exit_code: int


@dataclass(frozen=True)
class LocalFullResult:
    profile: LocalProfile
    profile_report: Path
    local_summary: Path | None
    timeline: tuple[TimelineEntry, ...]
    elapsed_seconds: float


class LocalFullGate:
    def run(self, request: LocalFullRequest) -> LocalFullResult: ...
```

`deadline_seconds` 只能在 `1..600`，`slots` 只能在 `1..10`；调用者不能把门槛调松。

CLI：

```bash
uv run --project backend python infra/mingli-runtime/local_gate.py native-full \
  --prepared-inputs /abs/prepared-inputs.json \
  --prepared-inputs-sha256 <sha256> \
  --output-parent /abs/gate-output

uv run --project backend python infra/mingli-runtime/local_gate.py linux-certify \
  --prepared-inputs /abs/prepared-inputs.json \
  --prepared-inputs-sha256 <sha256> \
  --output-parent /abs/gate-output
```

## PreparedInputs 绑定

manifest 自身的 SHA-256 由 `PreparedInputsRef.sha256` 外部固定，避免自引用哈希。manifest 至少绑定：

- clean source projection 的 commit、217-file release manifest SHA、投影树 digest；
- research Git HEAD/clean 状态、55 个全文资产清单与 digest；
- macOS runtime tree、CPython 3.14.6 executable digest、`runtime-integrity.json`；
- 同一个跨平台签名锁 `requirements-runtime.lock` 的 SHA；不存在另一个“macOS lock”；
- macOS sxtwl 由现有 `provision_runtime.py` 在隔离 venv 中按锁定 sdist、`--no-binary` 路径构建并验签；
- exact Linux OCI index、`linux/amd64` manifest、config、attestation manifest、
  ordered compressed layers、RootFS diff IDs、OCI archive SHA 与 immutable
  `repository@sha256:<index>` reference；
- `limactl template copy --fill` 生成的 effective VZ config SHA；
- Lima 版本以及 Docker Engine/CLI、containerd、rootlesskit 的固定版本/identity。

`full` 在计时开始前和原子发布前各重算一次 manifest 与相关树/文件。任何变化都 RED。准备阶段可以超过 600 秒，但必须显式执行，不能暗藏在 timed run 里。

每次运行生成全新 `run_id`，只在新的空临时目录写输出；最终验证完成后用同一文件系统上的 rename 原子发布到 `<output_parent>/<run_id>`。不得覆盖已有 run，也不得从旧 run 复用测试结果。

## 报告边界

- `release-5.1.json` 仍是纯 Linux release report，由 `verify_release.py` 验证。它不强制 Mac mini、600 秒或 10 槽字段，所以慢速 QEMU fallback 仍可合法验证。
- `native-full-5.1.json` 只装 native 完整回归和 native runtime/source identity。
- 每个 profile 另写一个 local SLA envelope，保存 run_id、机器、时钟、槽位、timeline、profile report SHA。
- 当两个 profile 都有同一 PreparedInputs SHA 下的合格结果时，独立 `verify_local_full.py` 可以原子生成 `local-full-5.1.json`，引用 native report SHA、Linux report SHA 和两个 SLA envelope；它不把两个 elapsed 相加后冒充单个 600 秒结果。

`verify_release.py` 不读取 native 报告或 local SLA；`verify_local_full.py` 才检查本机 600 秒/10 槽合同。

## 进程与输出安全合同

- 所有命令使用固定 argv 数组、`shell=False`，不接受拼接 shell 文本；
- stdout/stderr 各有固定字节上限，超过即 RED，原始 digest 仍记录；
- 容器和卷统一打 `run_id`、profile、command_id label；
- 每个子命令在独立进程组，超时杀整组并验证无残留；
- Docker 容器超时后按 exact ID 停止，卷按 exact label/名称清理；
- cleanup 在同一 deadline 内，失败不能发布 PASS；
- 机密、token、OTP、明文不得进入 argv、日志、fixture 或证据。

## Linux 唯一路径和 Matrix A/B

`local_gate.py linux-certify` 只能编排现有 Linux 组件：

```text
local_gate.py
  -> run_lima_gate.py / audit_runtime.py
  -> exact final image commands
  -> verify_release.py
```

不能复制一套 release verifier，也不能绕过现有报告合同。重构落点明确为：

1. 完整 1584 在 exact final image 中真实执行；其中通过的 `CanonicalMatrixSnapshotTests` 是 Matrix A；
2. 另起独立进程/容器执行一次 standalone matrix，作为 Matrix B；
3. 删除旧 audit 流程中的 standalone Matrix A；
4. 删除旧 finalizer 中重复执行的 1584；finalizer 只消费同一 run 的原始输出并验证 `1584/0`；
5. A 或 B 任一缺失、失败、identity 不一致，Linux certification 都 RED。

A 的绑定必须解析原始 regression stdout 中：

```text
[PASS] test_v51_provider_completeness.py::CanonicalMatrixSnapshotTests tests=2 elapsed=<seconds>s
```

并同时绑定 authoritative `targets=126/modules=93/tests=1584/failed_modules=0`、signed matrix SHA、signed matrix 中的 inputs fingerprint、source commit 和 exact image ID。

B stdout 不声称直接输出 `generator_input_fingerprint`。正确证据链是：

- B 前后重算只读 source/root fingerprint 与 signed matrix SHA；
- B `--check` 非零就失败；
- B 生成值逐字节等于 signed matrix；
- 因输入挂载只读且前后 fingerprint 一致，B 才绑定到 signed matrix 里记录的 inputs fingerprint。

必须有定向 mutation tests：A target 缺失/FAIL/tests!=2、B 非零、matrix bytes 不同、前后 root fingerprint 不同、source/image/run_id 不同都 fail closed。

## 性能策略：先量，再改

- `native-full` 保持 signed suite 整体运行，默认 `--jobs 10`；已有 434.62 秒证据，不做 Provider 分片重写。
- Linux 先做 VZ+Rosetta exact `linux/amd64` identity tracer，不先造调度器。
- tracer 通过后，先测 Linux regression/Matrix A、standalone B、其余 probes 的真实分项时间和嵌套子进程数。
- 如果 Linux 全 Gate 已在 600 秒内，就不引入额外调度复杂度。
- 只有真实基线仍超 600 秒，才按 TDD 引入一个总计不超过 10 个物理槽的最小并发调度；优先让 Linux A 与 B 隔离并行。
- 可选便利协调器可以在同一 10 槽池评估 native Canonical、Linux A、Linux B（例如实测后再决定 4/3/3），但不能预先冻结比例，且必须把 signed runner 的嵌套 workers 计入槽位；它不改变两个 profile 独立准入的事实。
- 如果 regression A 无法在不改 signed source 的前提下机器绑定，再退回三个真实 computation 并记录原因；不能用缓存伪造独立性。

---

### Task 0：先封存现有 Task 8 WIP，避免提交污染

**Files:** 只处理当前已知 Task 8 runtime WIP 和本计划；不碰用户的 UI/nginx/cert/SSH 未跟踪文件。

**Step 1: 完整审查当前差异**

```bash
git status --short
git diff --check
git diff --stat
git diff -- infra/mingli-runtime tests/contract/test_mingli_runtime_release.py
```

明确写下：无 `release-5.1.json`、无 PASS、QEMU 运行已中止。

**Step 2: 跑 WIP 聚焦门禁**

```bash
uv run --project backend ruff check infra/mingli-runtime tests/contract/test_mingli_runtime_release.py
uv run --project backend ruff format --check infra/mingli-runtime tests/contract/test_mingli_runtime_release.py
uv run --project backend pytest tests/contract/test_mingli_runtime_release.py -q
```

**Step 3: 精确 staging；禁止 `git add -A` 或整目录 staging**

```bash
git add -- \
  infra/mingli-runtime/Dockerfile \
  infra/mingli-runtime/README.md \
  infra/mingli-runtime/audit_runtime.py \
  infra/mingli-runtime/build_context.py \
  infra/mingli-runtime/dependency-provenance.json \
  infra/mingli-runtime/emit_sbom.py \
  infra/mingli-runtime/git-build-config.json \
  infra/mingli-runtime/requirements-linux-x86_64.lock \
  infra/mingli-runtime/run_lima_gate.py \
  infra/mingli-runtime/verify_release.py \
  tests/contract/test_mingli_runtime_release.py
git diff --cached --name-only
git diff --cached --check
```

缓存列表必须与上面完全一致，且不能出现生成报告或用户未跟踪路径。

**Step 4: 提交非准入 checkpoint**

```bash
git commit -m "wip: checkpoint non-admitted mingli runtime gate"
```

提交说明和交接都要写明 `ABORTED / no report / not admitted`。

**Step 5: 单独提交计划**

```bash
git add -- docs/plans/2026-08-09-mingli-v51-mac-mini-under-10-min.md
git commit -m "docs: plan mac mini native and linux gate lanes"
```

---

### Task 1：TDD 固化 `native-full` 最小标准命令

**Files:**

- Create: `infra/mingli-runtime/local_gate.py`
- Create: `infra/mingli-runtime/prepared_inputs.py`
- Create: `infra/mingli-runtime/verify_local_full.py`
- Create: `tests/contract/test_mingli_local_gate.py`

**Step 1: 先写并真实运行 RED**

公共测试必须经过 `LocalFullGate.run()`，不能只测私有 parser：

```python
def test_native_full_accepts_only_complete_suite_under_budget(tmp_path: Path) -> None:
    execution = ScriptedExecution.native_summary(
        targets=126,
        modules=93,
        tests=1584,
        failed_modules=0,
        elapsed_seconds=434.62,
    )
    result = LocalFullGate(execution, FakeClock()).run(native_request(tmp_path))
    assert result.profile == "native-full"
    assert result.elapsed_seconds <= 600
    assert result.timeline
```

再写参数化 RED，以下任一项必须拒绝且不发布报告：targets/modules/tests 缺失或不是 126/93/1584、failed_modules 非 0、elapsed `600.001`、deadline >600、slots >10、PreparedInputs SHA 不匹配、start/end 输入漂移、输出目录非空。

```bash
uv run --project backend pytest tests/contract/test_mingli_local_gate.py -k native_full -q
```

先确认因模块/接口不存在而 FAIL，再写实现。

**Step 2: 最小 GREEN**

只实现：profile/interface、PreparedInputs SHA/首尾校验、固定 native command spec、summary fail-closed parser、600/10 上限、run_id/空 staging/原子发布、timeline。先不写 Linux 调度器。

**Step 3: 安全 RED→GREEN**

增加固定 argv/`shell=False`、stdout/stderr 上限、进程组超时和残留清理测试；每项都先看到 RED。

**Step 4: 真实 native run**

使用同一个 `requirements-runtime.lock` 和现有 `provision_runtime.py` 准备隔离 venv；完整调用 signed suite，默认 jobs=10。要求：

```text
targets=126 modules=93 tests=1584 failed_modules=0 elapsed<=600
```

不拆 Provider，不改 signed source。发布 `native-full-5.1.json` 和 profile-local SLA envelope。

**Step 5: 质量门禁与小提交**

```bash
uv run --project backend pytest tests/contract/test_mingli_local_gate.py -q
uv run --project backend ruff check infra/mingli-runtime/local_gate.py infra/mingli-runtime/prepared_inputs.py infra/mingli-runtime/verify_local_full.py tests/contract/test_mingli_local_gate.py
uv run --project backend ruff format --check infra/mingli-runtime/local_gate.py infra/mingli-runtime/prepared_inputs.py infra/mingli-runtime/verify_local_full.py tests/contract/test_mingli_local_gate.py
git add -- infra/mingli-runtime/local_gate.py infra/mingli-runtime/prepared_inputs.py infra/mingli-runtime/verify_local_full.py tests/contract/test_mingli_local_gate.py
git commit -m "test: add fail-closed native full gate"
```

---

### Task 2：TDD 做 VZ+Rosetta exact amd64 tracer

**Files:**

- Create: `infra/mingli-runtime/lima-vz-rosetta.yaml`
- Modify: `infra/mingli-runtime/local_gate.py`
- Modify: `infra/mingli-runtime/prepared_inputs.py`
- Modify: `tests/contract/test_mingli_local_gate.py`
- Modify: `infra/mingli-runtime/README.md`

**Step 1: RED 锁 effective config，而不是只读原始 YAML**

测试必须要求：

```bash
limactl template validate --fill infra/mingli-runtime/lima-vz-rosetta.yaml
limactl template copy --fill infra/mingli-runtime/lima-vz-rosetta.yaml <temp-effective.yaml>
```

将 effective bytes SHA 写入 PreparedInputs。云镜像 URL/digest 必须来自本机 Lima 2.2.0 的 filled template 实测并冻结，不能猜。禁止 host mounts。

官方 `template:docker` 的浮动 `get.docker.com` 不可直接进入合同。prepare 必须使用受控、固定版本/来源的 Docker Engine/CLI、containerd、rootlesskit，或至少生成并固定这些实际 identity；`linux-certify` 开始和结束都拒绝漂移。

**Step 2: RED 锁 exact linux/amd64 identity**

逐项 mutation：OCI index、amd64 manifest、config、attestation subject、
compressed layers、RootFS diff IDs、image descriptor/`.Os/.Architecture`、
container platform、`uname -m`、`platform.machine()`、
Python/Node/Git/sxtwl/YAML ELF、ldd、Node libatomic、sxtwl import+最小调用。
任一不精确即 RED；同 tag 不构成 identity。

**Step 3: 最小 tracer GREEN**

创建 VZ profile，装载已准备好的 exact amd64 OCI archive，只跑身份 tracer，不跑 1584。所有命令仍用固定 argv、labels、进程组清理。

若 tracer 不满足 Linux x86_64 合同，停止 Linux 优化并保留 Task 8 RED；QEMU 仍是慢速 fallback。

**Step 4: 提交**

```bash
git add -- infra/mingli-runtime/lima-vz-rosetta.yaml infra/mingli-runtime/local_gate.py infra/mingli-runtime/prepared_inputs.py infra/mingli-runtime/README.md tests/contract/test_mingli_local_gate.py
git commit -m "test: add exact vz rosetta amd64 tracer"
```

---

### Task 3：只保留一条 Linux certification 路径

**Files:**

- Modify: `infra/mingli-runtime/audit_runtime.py`
- Modify: `infra/mingli-runtime/run_lima_gate.py`
- Modify: `infra/mingli-runtime/verify_release.py`
- Modify: `infra/mingli-runtime/local_gate.py`
- Modify: `tests/contract/test_mingli_runtime_release.py`
- Modify: `tests/contract/test_mingli_local_gate.py`

先写 RED，证明 old standalone A 与 finalizer duplicate 1584 仍存在；再把完整 regression 内 Canonical target 绑定为 A、只留下 standalone B。finalizer 只消费同 run 原始输出。`local_gate.py` 只调现有 audit/verifier seam，不复制准入逻辑。

`verify_release.py` 必须继续接受没有 local SLA 字段的合法 QEMU report。

---

### Task 4：TDD 锁 Matrix A/B 机器证据

针对 A target 缺失/失败/tests!=2、完整 summary 非 126/93/1584/0、B 非零、B 前后 root fingerprint 漂移、matrix byte mismatch、source/image/run_id mismatch 逐一 RED→GREEN。

不使用现有 `MINGLI_TEST_SESSION_DIR` 冒充外部缓存，不改 signed source，不调用私有 Provider partition 当新接口。

---

### Task 5：真实测 Linux 基线，再决定是否需要调度器

1. tracer 通过后，分别测 regression/A、standalone B、P0/probes/restore/SBOM/verifier；
2. 记录每项 elapsed、CPU/memory、嵌套 runner worker 数与真实最大并发；
3. 先跑完整 `linux-certify`，deadline 仍不许大于 600；
4. 如果已经 `<=600`，不写新调度器；
5. 如果超时，保持 RED，再写 scheduler RED，最小化并行 A/B；槽位总数和嵌套 workers 始终 `<=10`；
6. 只有实际测量支持时，才冻结 6/4、4/3/3 或其他比例。

---

### Task 6：分离 local SLA wrapper 与 Linux release verifier

新增 `local-full-5.1.json` 的本机 verifier/mutation tests。它引用两个 profile report 的 SHA 与各自 timeline，但保存两个独立 elapsed。同步篡改 outer SHA 也必须被语义校验拒绝。

Linux `release-5.1.json` 继续只由 `verify_release.py` 验证；不能把 Mac mini/600 秒字段塞成所有 release report 的必填项。

---

### Task 7：真实校准与最终质量门禁

`native-full` 至少再跑一次正式 wrapper：126/93/1584/0、`<=600s`、无残留。它成为默认开发/合并门禁。

`linux-certify` 必须满足完整 Linux 合同才可给 Task 8 GREEN：final image 1584/0、13/13、55/55、1328、A/B、P0、probes、restore、SBOM、source/image binding。VZ 若仍超 600，就如实保留 RED并继续 Task 5 的最小优化；不能提高上限或拿 native PASS 顶替。

最终运行：

```bash
cd backend
uv run ruff check .
uv run ruff format --check .
uv run mypy app worker
uv run pytest -q

cd ..
uv run --project backend ruff check infra/mingli-runtime tests/contract
uv run --project backend ruff format --check infra/mingli-runtime tests/contract
uv run --project backend pytest tests/contract/test_mingli_local_gate.py tests/contract/test_mingli_runtime_release.py -q
```

只有 verifier 从真实 bytes 生成并通过的报告可提交；禁止手工写 `release-5.1.json`。

## 当前执行入口

设计到此结束，不再扩 schema。接下来直接从 Task 0 开始，然后严格 TDD 执行 Task 1；每个行为先看到真实 RED，再写最小实现。Task 2 只做到 VZ+Rosetta exact amd64 tracer。在 tracer 和真实 Linux 分项基线出来前，不实现完整分布式调度。

# Mingli Test Suite Under Ten Minutes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在不删除测试、不降低断言强度、不改变生产命理逻辑的前提下，将 10 核开发机上的冷启动全量测试压到 600 秒以内，并保持任一子进程失败都会使总进程非零退出。

**Architecture:** 保留“每个测试目标一个独立 Python 解释器”的隔离模型。Provider completeness 只生成一次权威矩阵，并把该不可变结果传给多个断言；矩阵中的 13 个相互独立 Provider 审计由有界进程池并行执行，父进程按声明顺序合并。全量运行器将安全的长测试拆成 unittest class 目标并与普通模块共同调度，真正共享状态的测试仍在最后串行执行。

**Tech Stack:** Python 3.14、stdlib `unittest`、`concurrent.futures`、subprocess、YAML。

---

## 性能和正确性不变量

- 测试文件、测试方法和断言不得删除、跳过或改成弱断言。
- 权威矩阵必须由当前源码和制品生成；不允许用已提交快照冒充实时审计。
- 同一次测试进程中，权威矩阵只生成一次；变异测试复用同一不可变 canonical。
- Provider 并行结果必须按 `EXPECTED_SYSTEMS` 固定顺序合并，串行与并行输出逐字节一致。
- 任一 Provider worker 异常、任一 unittest 目标非零退出或无测试计数，都必须在总结果中可见并使运行失败。
- 并发必须有上限且可通过环境变量/CLI 调低，`jobs=1` 保留可复现串行路径。
- 不修改 Gateway、生产端口、Provider 算法、语料、命理 Interface 或运行时事务行为。

### Task 1: 锁定矩阵复用契约

**Files:**
- Modify: `scripts/test_v51_provider_completeness.py`
- Modify: `scripts/audit_provider_completeness.py`

1. 添加失败测试：向 `audit_matrix` 传入预生成 canonical 时不得再次调用 `build_matrix`。
2. 添加失败测试：canonical 参数必须被防御性读取，输入变异仍被识别。
3. 为 `audit_matrix` 增加仅供进程内复用的显式 `canonical` 参数；缺省行为保持兼容。
4. 将两个实时矩阵测试改为每个测试只生成一次并复用。

### Task 2: 并行化独立 Provider 审计

**Files:**
- Modify: `scripts/test_v51_provider_completeness.py`
- Modify: `scripts/audit_provider_completeness.py`

1. 添加失败测试：并行 worker 的乱序完成不得改变 Provider 输出顺序。
2. 添加失败测试：worker 异常必须传播，不能生成部分 ready 矩阵。
3. 把单 Provider 构建提取为顶层可序列化函数。
4. 使用有界进程池执行 13 个 Provider；父进程按 `EXPECTED_SYSTEMS` 顺序组装。
5. 提供 `MINGLI_MATRIX_JOBS`，默认值按 CPU 和外层 runner 预算限制；`1` 为串行诊断模式。
6. 比较串行/并行渲染结果及已提交快照，确保逐字节一致。

### Task 3: 改善全量调度的关键路径

**Files:**
- Modify: `scripts/test_parallel_test_runner.py`
- Modify: `scripts/run_test_suite.py`
- Modify: `README.md`

1. 添加失败测试：安全长模块可以按顶层 `unittest.TestCase` 类拆成独立目标。
2. 添加失败测试：Provider completeness 不再等所有普通并行测试结束后才启动。
3. 添加失败测试：共享状态模式仍保持串行，且失败聚合语义不变。
4. 运行器支持模块和 class 两种目标；子进程仍彼此隔离。
5. 只对白名单中的纯审计长模块分片，避免泛化 AST 魔法影响未知测试。
6. 文档记录默认并发、调低方式和十分钟验收命令。

### Task 4: 验证并记录真实耗时

**Files:**
- Modify if needed: `docs/plans/2026-08-06-mingli-test-suite-under-ten-minutes.md`

1. 运行测试运行器自身与矩阵复用契约测试。
2. 运行矩阵串行/并行等价性和快照校验。
3. 在 10 核机器、冷进程条件下运行完整套件一次，目标 `elapsed <= 600s`。
4. 核对模块/目标、测试总数、失败数；与基线相比不得少测。
5. 检查两个既有 worktree 状态，证明用户未提交资产未被触碰，且 Gateway 无改动。

## 回滚边界

- Commit 1：计划与 RED 契约测试。
- Commit 2：矩阵进程内复用。
- Commit 3：Provider 有界并行。
- Commit 4：运行器白名单分片与调度。
- Commit 5：文档和验收记录。

每个提交都只影响测试/审计基础设施，可单独回滚；任何阶段失败都可以退回上一阶段，不影响生产命理路径。

## 执行记录（2026-08-06 收口）

断点恢复后完成 Task 1-4，并在复跑中修复了三个断点未发现的问题：

1. `main()` 原先构建两次矩阵；现传入 `canonical=generated`，CLI 单次构建（新增 `test_main_audits_the_generated_matrix_without_rebuilding` 锁定）。
2. macOS spawn 的矩阵 worker 不继承 `-B`，会把 `.pyc` 写入受完整性校验的运行时 site-packages，导致后续 runtime probe 全部 fail-closed（表现为 bazi/fortune/liuren 审计偶发失败）。`build_matrix` 现在在构建窗口内强制 `PYTHONDONTWRITEBYTECODE=1` 并事后恢复（新增 `test_matrix_build_disables_and_restores_bytecode_writes` 锁定）。
3. `_run_dedicated_provider_audit` 原先无条件 `publish_report`，变异契约测试用桩 provider 以真实系统名调用时会向会话目录发布合成 report，污染 `DedicatedAuditLiveContractTests` 等消费端。发布点上移到 `_build_matrix_uncached`，仅矩阵构建路径发布（新增 `test_direct_audit_observation_does_not_publish_to_the_session` 锁定）。

关键路径调整：canonical 快照断言拆为独立 `CanonicalMatrixSnapshotTests`（每进程一次构建，预留 6 槽、内部 6 worker）；原 `ProviderCompletenessMatrixTests` 其余 66 个契约测试（约 230s）转入普通并行道。串行/并行矩阵渲染逐字节一致；已提交快照由 `--write` 重新发布。

验收（10 核 Mac mini，冷进程，`--research-root ~/.codex/skills/mingli-master`）：

- 全量：`targets=123 modules=90 tests=1497 failed_modules=0 elapsed=549.92s`（基线 4352.25s → 549.92s，约 7.9 倍）。
- 矩阵快照目标：466-517s（含一次 6-worker 并行构建）；DedicatedAuditLiveContractTests 复用会话 report 后 <1s。
- 测试总数 1497 ≥ 基线 1419，未删除/弱化任何测试；运行时 site-packages 全程零 `.pyc` 污染。
- 两个既有 worktree 与 Gateway、8642/8645 端口均未触碰。

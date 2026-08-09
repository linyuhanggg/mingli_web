# Mingli V5.1 Mac mini 原生门禁

Mac mini `native-full` 是唯一强制 Runtime Gate；正常开发、合并、发布和验收不得启动 VZ、Rosetta、QEMU 或 `linux-certify`。

## 唯一标准命令

准备一份已经绑定源码、研究资料、原生 Python 和完整性文件的 `prepared-inputs.json`，然后运行：

```bash
uv run --project backend python infra/mingli-runtime/local_gate.py native-full \
  --prepared-inputs /absolute/path/prepared-inputs.json \
  --prepared-inputs-sha256 <sha256> \
  --output-parent /absolute/new/empty/output-directory
```

公开命令只支持 `native-full`。它使用 PreparedInputs 按路径和 SHA-256 绑定的原生 Python（当前验收基线为 CPython 3.14.6）和最多 10 个进程槽，在 600 秒硬上限内运行签名 release 的完整测试套件。通过条件固定为：

`slots` 和 `max_slots` 表示 signed runner 的加权调度额度，不是操作系统 PID 数量上限。Canonical 等测试可创建父进程、资源跟踪器和休眠 worker，因此进程树中的 PID 总数可能超过 10；这不改变 runner 的 10 槽调度合同。

```text
targets=126
modules=93
tests=1584
failed_modules=0
```

成功目录必须同时包含：

- `native-full-5.1.json`
- `local-native-full-5.1.json`
- `native-release-regression.stdout`
- `native-release-regression.stderr`
- `prepared-inputs.json`

`verify_local_full.py` 会独立核验 PreparedInputs 摘要、固定命令、原始 stdout/stderr、1584/0 摘要、进程槽限制和计时边界。任何命令失败、输入漂移、报告缺失、输出被改动、超过 600 秒或独立验证失败都不得发布结果目录。

## 当前已接受基线

2026-08-09 在 M4 Mac mini、原生 CPython 3.14.6、10 槽上已取得 126 targets、93 modules、1584 tests、0 failed，完整门禁约 7 分多钟并低于 600 秒。每次正式验收以当次报告的精确计时和独立 verifier 结果为准。

## 历史 Linux 文件

目录中已有的 `Dockerfile`、`requirements-linux-x86_64.lock`、`prepare_linux_inputs.py`、`run_lima_gate.py`、`linux_identity.py`、`verify_release.py` 和 `lima-vz-rosetta.yaml` 是此前 Linux 模拟认证留下的历史实现。保留它们是为了 Git 追溯，不代表它们仍属于当前验收流程。

这些文件不得被 `make test`、`make check`、Task 8、Task 13、普通发布命令或后续自动任务调用。缺少 Linux 镜像、SBOM、OCI digest 或 `release-5.1.json` 不构成开发、合并、接入或发布阻塞。若未来所有者重新决定启用其他平台验证，必须先形成新的明确决策和独立计划，不能悄悄恢复旧 Gate。

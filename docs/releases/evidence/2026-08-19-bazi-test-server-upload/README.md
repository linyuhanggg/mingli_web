# 2026-08-19 八字验收版测试服务器发布证据

## 结论

当前 `codex/h-i-j-runtime-evidence` 的最新八字验收版已上传并切换到既有测试服务器：

- 公网首页：`http://106.14.10.235:18080/`
- 八字入口：`http://106.14.10.235:18080/bazi`
- 当前应用 release：`/opt/fateradar/releases/ui-preview-20260819-bazi-7822dd9`
- 当前 Runtime release：`/opt/fateradar/shared/mingli-master-v53-time-check-20260819-bazi-c451de5e`
- 回滚应用 release：`/opt/fateradar/releases/ui-preview-20260817-public-privacy`
- 切换前环境备份：`/opt/fateradar/shared/cache/bazi-acceptance-20260819-7822dd9/test.env.before-switch`

`/opt/fateradar/current` 已原子指向新应用 release。旧应用目录与切换前环境文件均保留，没有删除回滚材料。

## 版本身份

| 项目 | 值 |
|---|---|
| 父仓分支 | `codex/h-i-j-runtime-evidence` |
| 父仓 HEAD | `7822dd962f9dc5d49d51717d9e3211179874096c` |
| Core source commit | `663543e65ae037843b03dca1dec9486293affc9d` |
| Runtime manifest SHA-256 | `c451de5e4390c2a264a49aed972057081c61cb74ada160df308ac7a2af993c4b` |
| Runtime describe digest | `3403992cb31aebea19e69ec3b1280a5ef02718c5f9ca3e3f94448ef7b039facc` |
| Runtime capability-shape digest | `fb9da7fa1969e449e91222a0f10a2076da2e8cca43d1083b531aa218ff31e042` |
| Runtime inventory | `220 files / 14 providers / 55 packs / 1328 evidence` |

应用包只从父仓 HEAD 的运行目录生成，没有带入工作区未提交的文档和证据草稿。Runtime 使用本地已冻结、已签名的 V53 release；服务器端 `verify_frozen_runtime_release.py` 返回 `status=ok`。

## 构建与切换

- Backend 锁文件与服务器既有版本一致；复用服务器 Python venv 后重写新 release 的绝对入口路径，导入、`compileall`、应用启动和 Alembic `current=head=0039_export_ck_names` 均通过。
- Web 在新 release 内重新执行 `npm ci`、Next production build、TypeScript 检查和 standalone prepare，全部通过。
- Admin 在新 release 内重新执行 `npm ci`、Next production build、TypeScript 检查和 standalone prepare，全部通过。
- 正式切换前，独立候选端口验证 API `18001`、Web `13080`、Admin `13081`；`/api/openapi.json` 含 `/api/v1/readings/bazi-deep`。
- 以 `fateradar` 服务用户执行真实 one-shot Runtime 启动门禁，返回 `14 providers`，describe digest 与 capability-shape digest 均匹配。
- 原子切换脚本在停旧、启新期间出现短暂连接失败与 `502`，最终 readiness、Worker、Web、Admin 和整组终验均通过，脚本退出码为 `0`，没有触发回滚。

## 切换后证据

- `fateradar-test-api`、`fateradar-test-worker`、`fateradar-test-web`、`fateradar-test-admin` 均为 `active`，`NRestarts=0`。
- 最近十分钟四个服务的 error journal 为 `No entries`。
- `GET /api/v1/health/live = 200`。
- `GET /api/v1/health/ready = 200`。
- 动态 OpenAPI 中 `/api/v1/readings/bazi-deep` 存在。
- 服务器回环 Web `/`、`/bazi` 与 Admin `/login` 均为 `200`。
- 公网 `/` 与 `/bazi` 均为 `200`。
- 系统 Chrome 实测 `390×844` 与 `1440×900` 两档：页面标题为“八字｜命理工具”，正文和表单可见，横向溢出 `0 px`，无 page error，无 `5xx` response。
- 浏览器截图：[手机](../../../../artifacts/browser-evidence/2026-08-19-bazi-test-server-acceptance/bazi-mobile.png)、[桌面](../../../../artifacts/browser-evidence/2026-08-19-bazi-test-server-acceptance/bazi-desktop.png)。

## 边界

这次发布只修改现有测试服务器，没有修改生产域名，也没有 push Git。测试环境仍为 `MINGLI_ENVIRONMENT=local`：盘面使用已签名 V53 one-shot Runtime，Model、OTP 与支付仍是 Fake。本记录证明上传、构建、启动与基础浏览器呈现通过；不证明真实模型文案、真实短信、真实支付、生产准入或用户 P4-007 验收已经完成。P4-007 必须等用户亲自浏览并明确批准后才能改成已验收。

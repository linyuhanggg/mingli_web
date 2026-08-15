# P4-007 测试验收服务器上传（2026-08-15）

## 当前状态

`IN_PROGRESS`。当前 release 已上传并切换到测试验收服务器；用户逐页浏览和明确批准仍未完成。

2026-08-15 最新验收 release 已更新为 `ui-preview-20260815-public-products`，包含禄命/纳音、太乙、择日、风水产品输入/API/UI 纵切片和见相媒体数据库/API/前端上传接线；测试服务器仍是 `local + Fake`，只供虚构数据浏览。

2026-08-15 当前验收机热更新已完成：`current` 仍指向
`ui-preview-20260815-public-products`，本次没有伪造新的 archive SHA；在该 release
上备份并更新了私有 fortune 两个页面及 `web/next.config.ts` 的旧 redirect 表，修复
`/app/fortune/today`、`/app/fortune/week` 被错误送往公开 `/daily` 的问题。服务器
Web build/standalone prepare、全服务重启后的稳定健康检查均通过；旧源文件备份保留在
`/opt/fateradar/shared/cache/fortune-routes-hotfix-20260815/`。

```text
hotfix_backup: /opt/fateradar/shared/cache/fortune-routes-hotfix-20260815/
today_page_sha256: 985e4113f13911105c991e9a532f556c036b850896a01c1b15f77acd7335fe05
week_page_sha256: d2624093ae36cca4af640df0751a16ab9572f5ec2ead0447763941ef48aa54bc
next_config_sha256: 62d86bb01c21731f4a2b394b0000f07f6e971e2b8c971ee74a24ab212962ea8d
runtime: MINGLI_ENVIRONMENT=local + Fake OTP/Runtime/Model/Payment
```

2026-08-15 P10-013F 同盘事实比较已在同一 release 上完成可回滚热更新。更新前文件备份保留在
`/opt/fateradar/shared/cache/chart-similarity-hotfix-20260815/`；Web 重新构建和 standalone
prepare、后端 import、API/Worker/Web 重启及健康检查均通过。服务器仍是 `local + Fake`，只供
虚构数据浏览。

```text
hotfix_backup: /opt/fateradar/shared/cache/chart-similarity-hotfix-20260815/
chart_similarity_route: http://127.0.0.1:18080/tools/chart-similarity
runtime: MINGLI_ENVIRONMENT=local + Fake OTP/Runtime/Model/Payment
```

```text
archive_sha256: ba6ea69f9d3558ef0cd3f47b2cb4ce13780a57b0e6721bd9ea4ac87c4d2b47e1
database_schema_head: 0035_physiognomy_media
pre_migration_backup: /opt/fateradar/shared/backups/ui-preview-20260815-public-products-pre-migration.dump
pre_migration_backup_sha256: 0b5c4854a63a6058e3d7fa2245edee0437786929d0020669981cb36b6b6d3df4
```

## 服务器与 release

```text
server: fateradar-prod（代码联调与验收机，不是 production）
release: ui-preview-20260815-core-viewmodels
archive_sha256: 80318e018a20ef3a1606ebc1ac35e8fe8bb356f3baabd7e4ecae419eb258d682
source_git_head: bf5ab2aa1cc27c987b45b59652063b420ecc87da
source_kind: 当前工作树应用快照；不是干净 Git commit；包含四个内部 Provider 的 Web ViewModel 注册、事实表分派、状态文本边界修复及既有核心接线
environment: MINGLI_ENVIRONMENT=local + Fake OTP/Runtime/Model/Payment
uploaded_at: 2026-08-15
database_schema_head: 0034_reading_relationship
alembic_check: pass
preflight_import: pass（fateradar 用户导入 app.main）
backup: `/opt/fateradar/shared/backups/ui-preview-20260815-core-viewmodels-pre-migration.dump`；SHA-256 `2ed6ae87ae1eb40d1f4a3487a4cc22a17fdd3e0c8234add5c57c64d7de9d2195` 已记录
manifest: `/opt/fateradar/shared/backups/ui-preview-20260815-core-viewmodels-MANIFEST.txt`
dependency_strategy: 服务器已有相同 package/lock/uv 清单的依赖以只读硬链接复用；Web/Admin `.next` 在服务器重新构建
```

## 用户浏览入口

在本机保持 SSH 会话打开：

```bash
ssh -L 18080:127.0.0.1:8080 -L 13001:127.0.0.1:3001 fateradar-prod
```

- Web 公共页、产品页、账户页：<http://127.0.0.1:18080/>
- 八字同盘四柱事实比较：<http://127.0.0.1:18080/tools/chart-similarity>
- 本命音律事实：<http://127.0.0.1:18080/tools/rhythm>
- 五行事实与调候：<http://127.0.0.1:18080/tools/five-elements>
- 八字合盘：<http://127.0.0.1:18080/bazi/hepan>
- 紫微合盘：<http://127.0.0.1:18080/ziwei/hepan>
- 七政合盘：<http://127.0.0.1:18080/qizheng/hepan>
- Admin 登录页：<http://127.0.0.1:13001/login>
- 临时公网 Web 预览：<http://106.14.10.235:18080/>

Admin 只监听回环地址，不通过临时公网预览暴露。

## 服务器检查

- Nginx `/healthz`：200
- API `/api/v1/health/live`：200
- API `/api/v1/health/ready`：200
- Web `/`：200
- Admin `/login`：200
- `fateradar-test-api`、`worker`、`web`、`admin`、`nginx`：全部 `active`
- PostgreSQL 迁移前备份已生成并通过 SHA-256 核对；备份与 release manifest 在服务器 `shared/backups/`。
- 当前 release 的 PostgreSQL 0034 迁移已完成，`alembic check` 无新增操作；失败时的代码指针回滚路径已在切换脚本中验证。
- 本版服务器端 Web/Admin build、standalone 资产准备、后端 import、Fake Runtime Release 登记和权限归一化均通过；切换后两轮服务重启与健康检查均通过，旧 release 仍保留可回滚。
- 最终 release 的 `/`、`/hecan`、`/canwen`、独立 Admin `127.0.0.1:3001/login` 返回 200；`/api/openapi.json` 含 `startHecanReading`；API live/ready、Nginx healthz 和五个服务均通过；旧 release 仍保留可回滚。

## 发布过程记录

- 第一版最小归档缺少顶层 `ui/`，服务器 Web build 立即失败；未切换 `current`。
- 补齐 `ui/` 后 Web/Admin build 通过；API preflight 又发现运行时需要顶层 `contracts/`，两次切换尝试均由回滚脚本恢复旧 release。
- 补齐 `contracts/` 后以 `fateradar` 用户预启动导入通过，再原子切换并完成 live/ready、Web、Admin、systemd 检查。
- 旧 release `ui-preview-20260814-3eaf1511b84a` 保留在服务器 `releases/`，可按运行手册回滚；这不是生产发布。
- 本次归档首次切换时发现 macOS 目录权限和 `.venv/bin` 执行位会阻断 `fateradar` 启动，已归一化目录/文件权限、恢复启动脚本执行位，并把 Next `.next/server` 写目录纳入测试 unit；修复后第 4 次启动轮询通过。
- 本次问事合参 release 构建时测试机磁盘曾被历史 preview 产物占满；只清理了三个明确的旧 preview 目录，保留当前版本、核心版本和回滚版本。为适配测试机磁盘，Web/Admin 用服务器已有同版本依赖完成 Webpack 构建，并把完整 Next runtime 收入新 standalone；临时端口 smoke、正式服务重启和页面检查均通过。
- 本次 relationship release 先通过本机 Backend `823 passed/102 skipped`、Web `437`、Admin `121`、根合同 `185 passed/82 skipped` 与两端 production build，再以归档 SHA 核对后上传；服务器 Web/Admin 生产构建、迁移前备份、API live/ready、三条合盘路由、OpenAPI 和五个服务复核通过。
- 本次核心 ViewModel release 先通过本机 Web `70 files / 440 tests`、typecheck、lint、production build，再以归档 SHA 核对后上传；因测试机根盘 98% 使用且依赖清单未变，复用服务器已有依赖硬链接并只重建新 release 的 Web/Admin `.next`。服务器端 Web/Admin build、Fake Runtime Release、两轮重启、API live/ready、Web `/`、Admin `/login` 和五个服务复核通过；本版只支持虚构数据浏览。
- 本次 fortune 私有入口热更新先通过本机定向 `27 passed`、typecheck、lint、production build；服务器曾因旧 `.next/trace` 的 root 权限导致一次可恢复的 build EACCES，按 runbook 将当前 Web `.next` 归属归一化后重跑通过。Web `/app/fortune/today` 与 `/app/fortune/week` 均为 200、无 `Location`，正文分别含“今日解读/近七日解读”；`/daily` 仍为公开 CMS，私有页响应保持 `private, no-store` 与 `noindex`。全服务重启后第二轮 API/Web/Admin/Nginx 检查通过，所有服务 `NRestarts=0`。

## 验收边界

本次上传只支持测试服务器浏览和 P4-007 用户验收，不代表生产发布、真实身份/支付/模型、备案或 P12 外部门禁已经通过。测试数据必须是虚构数据；不要在聊天、截图或浏览器中输入真实个人资料或凭据。

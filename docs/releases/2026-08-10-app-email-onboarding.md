# `/app` 与邮箱注册测试发布记录

记录日期：2026-08-10（Asia/Shanghai）

状态：**公网代码测试服务器验收通过 / local + Fake / real staging blocked / production blocked**

本记录只证明 `/app` 私人区、邮箱身份流程和 Fake 阅读链路在代码测试环境可用。公网入口是未备案期间的临时 HTTP 预览，不发送真实邮件、不调用真实命理 Runtime/模型、不处理真实支付，也不得录入真实个人资料。

## 固定发布物

- 服务器：`fateradar-prod`
- 公网预览：`http://106.14.10.235:18080`
- 部署提交：`9bc2cd6bb19b2d30af2250108d9fabb4625db3d2`
- 归档 SHA-256：`422089b366905a3bde5c0f22a8e0346ed1ecf14334ed6446ae8052c05d62ef61`
- 数据库切换前备份：`9bc2cd6bb19b2d30af2250108d9fabb4625db3d2-pre-migration.dump`
- 备份 SHA-256：`6aa39984a0f5889d730fc2c6222491a656dc00412f5e8b86156b1545e60767e4`
- 即时应用回滚点：`67868c45ba8ddc24c898921a44a0aa99ec319ccb`。该版本可恢复页面和身份流程，但保留 fortune 空维度导致任务 `delayed` 的已知缺陷；回滚后必须重新跑 Fake E2E。

服务器使用每个提交独立的 release 目录；归档在本地与服务器端校验一致，依赖和 Next standalone 均在服务器重新构建。`/opt/fateradar/current` 原子切换到上述提交，release 除 Next runtime cache 外保持只读。

## 本地门禁

最终提交实际执行 `make check`，结果：

- 后端与合同：`499 passed, 90 skipped`
- Ruff：通过
- mypy：`60 source files` 无问题
- Web：`21` 个测试文件、`165` 个测试通过
- ESLint：通过
- TypeScript：通过
- Next.js production build：通过，静态页 `10/10` 生成完成
- `git diff --check`：通过

fortune 修复采用测试先行：旧代码在真实 Fake Runtime + Fake Model + Reading Orchestrator 组合下稳定得到 `required_dimension_missing`，今日任务最终 `delayed`；修复后今日与本周任务均一次尝试进入 `accepted / complete`。Narrative Guard、Fake 候选和 API schema 均未放宽。

## 服务器与浏览器验收

- Nginx 回环与公网 `/healthz`：200
- API live / ready：200，数据库 ready
- 首页与账户页：200
- `fateradar-test-api`、`fateradar-test-worker`、`fateradar-test-web`、Nginx：active
- 三个应用服务：`NRestarts=0`
- 原子切换后验收通过；随后完整人工 restart 并再次通过同一组检查

浏览器使用纯虚构 `@example.com` 邮箱和页面显示的 Fake 验证码 `246810`，完成：

1. 首次邮箱验证自动创建账户并进入 `/app`；
2. 创建虚构档案 v1；
3. 发起今日解读，Worker 最终交付 `accepted`；
4. 从解读历史重新打开同一结果；
5. 账户页只显示脱敏邮箱并可退出当前设备；
6. 使用同一邮箱再次登录，原档案和已交付历史仍存在；
7. 再次退出并回到公共首页。

最终 Accepted 阅读版本为 `16264250-d92c-4407-b497-8894a5ee3871`。热修前的失败版本 `7317f5cb-e7f2-4197-828d-f5be0c791e7e` 继续以 `delayed` 保留在测试历史中，用于证明旧缺陷没有被改库伪装成成功。桌面默认视口与手机 `390 × 844` 均完成 DOM 和视觉检查。

## 仍然阻塞真实邮件与正式上线的事项

- 当前测试服务器固定 `MINGLI_ENVIRONMENT=local`、OTP/Runtime/Model 均为 `fake`；验证码会显示在页面上。
- 真实邮箱投递只实现了 TLS SMTP Adapter；测试服务器尚未配置 SMTP 凭据。
- production 在持久化 OTP challenge、目的邮箱和网络级限流进入共享存储前保持 fail-closed；当前进程内限流会随重启清空，不是生产防滥用方案。
- 真实发信还需要独立发件域名、SPF、DKIM、DMARC、退信/投诉处理、Secret Manager 与凭据轮换。
- 公网入口只有 HTTP，没有 TLS，也不是备案域名入口；只能使用虚构数据。
- 真实命理 Runtime、固定模型质量评测、支付、告警和隔离 staging trajectory 仍未完成，本记录不是生产上线批准。

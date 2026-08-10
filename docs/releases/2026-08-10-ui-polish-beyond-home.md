# 除首页外 UI 修正发布记录

记录日期：2026-08-10（Asia/Shanghai）

状态：**公网代码测试服务器验收通过 / local + Fake / real staging blocked / production blocked**

本记录只证明除首页外的私人区与公共编辑页 UI/布局修正已在代码测试环境可用。公网入口仍是未备案期间的临时 HTTP 预览，不发送真实邮件、不调用真实命理 Runtime/模型、不处理真实支付，也不得录入真实个人资料。

## 固定发布物

- 服务器：`fateradar-prod`
- 公网预览：`http://106.14.10.235:18080`
- 部署提交：`8ef9ee909d64f06a72965a2bad24f63b09d8b339`
- 归档 SHA-256：`2c416e44b0332d0dd0b63bbf0b81cd79b6bcfac19c80b8f8367c2805bbd2adb6`
- 数据库切换前备份：`8ef9ee909d64f06a72965a2bad24f63b09d8b339-pre-migration.dump`
- 备份 SHA-256：`4aba4a5a1035f072e52deb05d337b0f13fa2cc9bead7589a1e158c04a9f5e933`
- 即时应用回滚点：`9bc2cd6bb19b2d30af2250108d9fabb4625db3d2`（上一版，原样保留）

## 本版改动

除首页外页面视觉与布局排版修正（commit `8ef9ee9`，26 文件 +298/-149）：

- 私人侧边栏改为书脊式贴边墨绿区，金色高亮当前导航，与象牙色页面背景衔接；
- 导航「今日」改名「首页」，消除与今日解读页的歧义；
- `/app` 与 `/account` 改用统一 paper/flowList 结构，去掉重复标题与厚重的禁用面板占位（订单/导出/删除归并为一条边界说明）；
- 账户文案更新为真实邮件已启用的口径：验证码发送到邮箱、仅开发/测试环境才可能额外显示调试码；
- 档案空状态、OTP 表单、六爻表单、公开编辑页（定价/支持/方法/隐私/条款）统一间距与层级；
- 测试断言同步更新，新增 44px 触控热区与键盘焦点可见性契约。

## 本地门禁

- Web：`21` 个测试文件、`167` 个测试通过
- ESLint：通过（--max-warnings=0）
- TypeScript：`tsc --noEmit` 通过
- Next.js production build：通过，静态页全部生成

## 服务器验收

- Nginx 回环与公网 `/healthz`：200
- API live / ready：200，数据库 ready
- Web `/`、`/account`（含「邮箱是你的默认登录入口」）、`/app`：200
- `fateradar-test-api`、`fateradar-test-worker`、`fateradar-test-web`、Nginx：active
- 三个应用服务：`NRestarts=0`
- 原子切换后验收通过；随后完整人工 restart 并再次通过同一组检查
- Alembic 无新迁移，head 仍为 `0007_api_idem_verify`

## 仍然阻塞真实邮件与正式上线的事项

- 当前测试服务器固定 `MINGLI_ENVIRONMENT=local`、OTP/Runtime/Model 均为 `fake`；验证码会显示在页面上。
- 真实邮箱投递只实现了 TLS SMTP Adapter，未在测试服务器接线真实 SMTP 凭据。
- production 在持久化 OTP challenge、目的邮箱和网络级限流进入共享存储前保持 fail-closed。
- 公网入口只有 HTTP，没有 TLS，也不是备案域名入口；只能使用虚构数据。
- 真实命理 Runtime、固定模型质量评测、支付、告警和隔离 staging trajectory 仍未完成，本记录不是生产上线批准。

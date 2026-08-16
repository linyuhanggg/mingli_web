# 测试服 UI 预览部署（2026-08-13）

## 访问

- 公网预览：`http://106.14.10.235:18080/`
- 只允许使用虚构测试数据；这是明文 HTTP 测试入口，不是生产环境。
- 本轮部署的是当前工作树的 Web/API/Worker，不包含 Admin 独立服务。

## 部署结果

- 测试服 release：`preview-20260813-1405`
- `current` 已原子切换到该 release；旧 release 保留，可回滚。
- API、Worker、Web、Nginx：全部 `active`。
- 数据库迁移：`0014_reading_delivery (head)`。
- 迁移前测试库备份已写入服务器 release 专属 backup 目录。
- Web 服务器端 Node 22 构建成功，standalone 产物和 `.next/cache` 已准备。

## 公网核验

以下入口均返回 HTTP 200：

- `/healthz`
- `/api/v1/health/live`
- `/api/v1/health/ready`
- `/`
- `/methodology`
- `/bazi`
- `/arts`
- `/auth/login`

## 限制

- 后端仍是测试服 `local + Fake` 配置，不调用真实模型、不产生真实支付事实。
- Admin 目前没有接入测试服的 systemd/Nginx 发布链路。
- 公网入口没有 TLS，只用于本轮 UI 预览和虚构数据验收；不能宣称生产上线。

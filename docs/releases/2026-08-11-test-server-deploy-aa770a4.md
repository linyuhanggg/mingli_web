# Test Server Deploy: aa770a4 (2026-08-11)

记录日期：2026-08-11（Asia/Shanghai）

状态：**代码测试服务器升级完成 / Figma Make 公开壳与首页已上线 / production blocked / real traffic disabled**

本记录不是 production 放量批准。

## 部署前后

- 前：`6ec15786ac8ce110bbf698b1c8578518123b1a2a`
- 后：`aa770a4c1c6c9951f935984e09b549f3fd41e066`
- 增量：公开深墨绿壳 + 首页按 Figma Make 视觉落地；入口接到现有八字/建档/方法模块；backend / alembic / infra 零改动

## 归档

- 文件：`fateradar-aa770a4c1c6c9951f935984e09b549f3fd41e066.tar.gz`
- SHA-256：`f80c91a557dbbfa6eb0fb515f12d01bcd16e99ad2c190264ccedc13534463226`
- 路径：`/opt/fateradar/releases/aa770a4c1c6c9951f935984e09b549f3fd41e066/`
- 备份：`/opt/fateradar/shared/backups/aa770a4...-pre-switch.dump` + MANIFEST

## 健康验收

- systemd api/worker/web/nginx：active，`NRestarts=0`
- API live/ready：200
- Web `/`、Nginx `8080`、公网 `18080`：200
- 外网 `http://106.14.10.235:18080/`：200
- 首页实锤标记：`把时间变成私密` / `免费体验起盘档案` / `八字命盘起盘` / `在线起盘` / `v2.4` / `ASTROLABE ID #2026-ARCH`
- 环境仍为：`local` + OTP `fake` + Runtime `one-shot` + Model `deepseek`

## 仍 blocked

- 固定模型质量评测 / Guard 红队
- Secret Manager、告警、恢复演练
- 真实公网放量

`production blocked / real traffic disabled`

# FateRadar production edge

首台阿里云 ECS 的基础入口配置。这里不保存密码、证书私钥或应用密钥。

- `nginx/fateradar.conf`：首次签发证书前使用的 HTTP 引导配置。
- `nginx/fateradar-tls.conf`：签发证书后使用的生产入口，并为 Certbot 保留独立的 ACME Webroot。
- `www/index.html`：正式 Next.js 网站上线前使用的临时状态页。
- `ssh/99-fateradar-hardening.conf`：只允许 SSH 公钥认证，禁止远程密码登录。
- `letsencrypt/reload-nginx.sh`：证书成功续期后校验并重新加载 Nginx。

正式应用默认约定：Web Next.js 监听 `127.0.0.1:3000`，独立 Admin Next.js 监听 `127.0.0.1:3001`，FastAPI 监听 `127.0.0.1:8000`，外部只开放经过单独授权的 Nginx 入口。现有配置不把 Admin 暴露到公共 Web 入口。

Admin 的可复验部署入口是 `docker/admin.Dockerfile`、`compose.local.yml` 中的 `admin` 服务和 `systemd/fateradar-test-admin.service`；三者都使用 standalone 产物，并把后端地址固定在构建期/回环运行期。

生产服务器使用 `/var/lib/letsencrypt` 完成 HTTP-01 验证；证书续期后由部署钩子重新加载 Nginx。

当前大陆 ECS 会在域名未完成 ICP 备案时由阿里云边缘层拦截 HTTP/HTTPS。备案完成后应立即执行一次 `certbot renew --dry-run --no-random-sleep-on-renew` 验收自动续期。

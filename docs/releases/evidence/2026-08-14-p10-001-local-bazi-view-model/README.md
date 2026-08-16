# P10-001 本地 Bazi Runtime → ViewModel 纵切片

日期：2026-08-14（Asia/Shanghai）  
环境：本机 macOS，专用 `mingli-master` Runtime venv；虚构 fixture，不含真实个人资料  
状态：本地技术切片通过；P10-001 仍为 `IN_PROGRESS`

## 通过项

- Runtime integrity check：Python 3.14.6、`sxtwl 2.0.7`、`astronomy 2.1.19`、`cnlunar 0.2.4`，通过。
- Runtime `describe → prepare`：真实 one-shot process adapter 返回 `Prepared`，23 个事实，Bazi capability，life horizon。
- 后端投影：只读取 Runtime 的 `/calculated/bazi/`（兼容旧 `/chart/`）事实；`/input/` 事实不会进入 ViewModel。
- `bazi-chart/v1`：四柱、可见干支计数和本命/流年/流月/流日可用性均经过 Pydantic 合同校验；没有逐层事实的时间层保持 disabled。
- 私有阅读结果页：有 `bazi-chart/v1` 时优先消费类型化 ViewModel；旧结果继续使用公开事实回退。

## 回归结果

```text
backend projector + public fact panel: 8 passed
web reading-display: 9 passed
make check: exit 0
backend: 732 passed, 92 skipped
web: 68 files, 432 passed
admin: 33 files, 121 passed
ruff / mypy / web lint+typecheck+build / admin lint+typecheck+build: PASS
```

## 边界

这份证据只证明本地 Runtime 到私有结果页的类型化接线，不证明公开 `/bazi` 已完成，也不替代 P4-007 用户逐页批准。公开 `/bazi` 仍保留诚实的录入—确认—未计算状态；P12-001 Mac mini native-full、P12-002 生产凭据、真实支付/合规/公开上线仍按原门禁执行。

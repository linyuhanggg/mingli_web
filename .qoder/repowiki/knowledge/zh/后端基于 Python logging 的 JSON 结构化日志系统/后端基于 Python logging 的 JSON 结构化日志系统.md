---
kind: logging_system
name: 后端基于 Python logging 的 JSON 结构化日志系统
category: logging_system
scope:
    - '**'
source_files:
    - backend/app/observability.py
    - backend/app/config.py
    - backend/app/main.py
    - backend/worker/readings.py
    - backend/app/adapters/model.py
    - backend/app/readings/alerts.py
    - backend/alembic/env.py
---

## 1. 使用的系统与框架

后端服务（FastAPI HTTP 进程与独立 Worker 进程）统一使用 Python 标准库 `logging` 模块，未引入第三方日志框架。所有日志输出为单行 JSON 字符串，由上层日志收集系统解析。

- 日志配置入口：`backend/app/observability.py::configure_logging(level)`，调用 `logging.basicConfig(level=level, format="%(message)s")`，即只输出消息体本身（JSON），不附加时间、级别等前缀。
- 日志级别来源：`backend/app/config.py::Settings.log_level`（默认 `"INFO"`），通过环境变量 `MINGLI_LOG_LEVEL` 注入。
- 敏感传输库降噪：`_SENSITIVE_TRANSPORT_LOGGERS = ("httpx", "httpcore", "h2", "hpack")` 被强制设为 `WARNING`，避免网络层产生大量噪声日志。

## 2. 关键文件与位置

| 文件 | 职责 |
|---|---|
| `backend/app/observability.py` | 全局日志初始化、HTTP 请求观测中间件 |
| `backend/app/config.py` | 提供 `log_level` 配置项（`MINGLI_LOG_LEVEL`） |
| `backend/app/main.py` | FastAPI 启动时调用 `configure_logging` 并安装请求观测中间件 |
| `backend/worker/readings.py` | Worker 进程启动时同样调用 `configure_logging(settings.log_level)` |
| `backend/app/adapters/model.py` | 模型适配器审计日志（`mingli.model` 命名空间） |
| `backend/app/readings/alerts.py` | 运维告警结构化日志（`mingli.alerts` 命名空间） |
| `backend/alembic/env.py` | Alembic 迁移通过 `fileConfig` 单独配置日志 |

## 3. 架构与约定

### 3.1 命名空间策略
每个子系统通过 `logging.getLogger("<domain>")` 获取独立 logger，形成清晰的命名空间：
- `mingli.api` — HTTP 请求/响应观测
- `mingli.model` — DeepSeek 模型调用审计
- `mingli.alerts` — 运维告警事件
- `mingli.model`（在 `adapters/model.py` 中）— 模型适配器内部日志

### 3.2 结构化字段约定
所有业务日志均为紧凑 JSON（`separators=(",", ":")`，可选 `sort_keys=True`），包含以下核心字段：

- **HTTP 请求日志**（`mingli.api`）：`event="http_request"`，附带 `request_id`、`method`、`path`、`status`、`duration_ms`。
- **模型审计日志**（`mingli.model`）：通过 `SafeModelAuditLogger.record()` 输出 `receipt.to_dict()`，仅包含计费/用量元数据，明确不包含请求或响应正文。
- **告警日志**（`mingli.alerts`）：`event="ops_alert"`，附带 `kind`、`at`、`job_id`、`reading_version_id`、`details`。

### 3.3 请求追踪
- 请求 ID 从 `X-Request-ID` 请求头读取（正则校验 `^[A-Za-z0-9._:-]{1,128}$`），否则生成 UUID hex。
- 请求 ID 写入 `request.state.request_id` 并在响应头 `X-Request-ID` 回写，贯穿整个请求链路。

### 3.4 进程级初始化
- HTTP 进程：`create_app()` → `configure_logging(resolved_settings.log_level)` → `install_request_observability(application)`。
- Worker 进程：`configured_reading_worker()` → `configure_logging(settings.log_level)`。
- 两个进程共享同一套日志格式和级别策略。

## 4. 约定与约束

- **日志格式约束**：所有业务日志必须输出为单行 JSON；非业务日志（如 transport 层）被降级至 WARNING。
- **安全约束**：`SafeModelAuditLogger` 明确“仅输出有界的计费/传输元数据，从不输出请求或响应正文”；告警 sink 也声明“no secret values”。
- **可观测性字段**：HTTP 日志必须包含 `request_id`、`method`、`path`、`status`、`duration_ms`；告警日志必须包含 `event`、`kind`、`at`。
- **配置约束**：`log_level` 通过 `MINGLI_LOG_LEVEL` 环境变量注入（`Settings` 的 `env_prefix="MINGLI_"`），默认 `INFO`。
- **测试友好**：告警系统提供 `NoopAlertSink` 与 `RecordingAlertSink` 两种替代实现，便于单元测试验证告警行为而不产生真实日志。
- **Alembic 隔离**：数据库迁移脚本通过独立的 `fileConfig` 配置日志，与主应用日志配置分离。

## 5. 前端与管理后台

仓库中的 Web 前端（Next.js）和管理后台（Next.js Admin）未发现集中式日志框架代码；其运行时日志由 Node.js 运行时及部署环境（Nginx/systemd/Docker）处理，不属于本仓库内定义的日志系统范畴。
---
kind: error_handling
name: 后端基于 RFC 7807 Problem Details 的统一错误体系与前端 ApiError 适配
category: error_handling
scope:
    - '**'
source_files:
    - backend/app/api/errors.py
    - backend/app/api/problems.py
    - backend/app/main.py
    - backend/app/readings/errors.py
    - backend/app/readings/rate_limit.py
    - web/src/lib/api.ts
    - admin/src/lib/api.ts
    - web/src/app/app/error.tsx
---

## 1. 整体方案

后端采用 FastAPI + 自定义异常 + RFC 7807 `application/problem+json` 响应体的统一错误处理模式；前端通过统一的 `ApiError` 类型解析后端返回的 problem document，并在 Next.js App Router 中提供页面级 error boundary。

核心思路：业务层抛出领域/HTTP 语义明确的异常 → FastAPI 全局 exception handler 将其转换为结构化的 JSON Problem 文档 → 前端根据 HTTP status 和 `title`/`detail` 字段决定用户可见提示或重试逻辑。

## 2. 关键文件与职责

- `backend/app/api/errors.py`：定义 `ApiProblem(Exception)`，携带 `status`、`title`、`problem_type`（默认 `about:blank`）、`detail`、`headers`。这是所有 HTTP 层错误的唯一抛出点。
- `backend/app/api/problems.py`：`problem_response(request, ...)` 将上述字段组装为 `application/problem+json` 响应体，并注入 `request.state.request_id` 作为 `request_id` 字段。
- `backend/app/main.py`：在 `create_app()` 中注册两个全局异常处理器——
  - `@application.exception_handler(ApiProblem)`：直接映射到 `problem_response`。
  - `@application.exception_handler(RequestValidationError)`：以 `urn:fateradar:problem:invalid-request` 问题类型返回 400。
  - 同时移除 OpenAPI 文档中的 422 响应声明，使客户端契约只依赖显式抛出的 `ApiProblem`。
- `backend/app/readings/errors.py`：定义阅读编排领域的异常层次——`ReadingOrchestratorError`（基类）→ `RuntimeTransportError`、`NarrativeGenerationError`、`NarrativeGenerationCancelled`、`OrchestratorInvariantError`。这些异常用于进程边界内传递模型运行时失败原因，不直接暴露给 HTTP 层。
- `backend/app/readings/rate_limit.py`：`WindowRateLimiter.check()` 超限后抛出 `RateLimitExceededError(RuntimeError)`，由调用方（如依赖注入层）转为 `ApiProblem(429, ...)`。
- `web/src/lib/api.ts`：定义 `ApiError extends Error`，包含 `status` 与可选 `detail`；`requestJson` 对非 `response.ok` 的情况读取 body 中的 `title`/`detail` 构造 `ApiError`；`jsonPost` 针对 403 `CSRF validation failed` 自动清理 CSRF 缓存并重试一次。
- `admin/src/lib/api.ts`：`adminFetch` 返回 `{ ok: true; data } | { ok: false; status; title }` 的联合类型，把后端 problem 的 `title` 透传给管理后台 UI 展示。
- `web/src/app/app/error.tsx`：Next.js App Router 页面级 error boundary，使用 `StatusPanel` 组件以 `state="error"` 展示“私人档案暂时无法载入”，并提供“重新载入”按钮触发 `reset()`。

## 3. 架构约定

### 3.1 后端异常分层
- **HTTP 层**：所有路由/依赖/中间件只能抛出 `ApiProblem`，禁止直接 `raise HTTPException`。认证失败、CSRF 校验失败、会话缺失等统一通过 `ApiProblem(status=401|403, title=...)` 表达。
- **领域/编排层**：阅读编排相关失败使用 `ReadingOrchestratorError` 及其子类，例如 `NarrativeGenerationError(code, receipt=...)` 用短码描述模型侧失败（如 `model_redirect_forbidden`、`model_rate_limited`、`model_upstream_error`、`model_http_error`、`model_encoding_forbidden`、`model_response_too_large`、`model_policy_not_approved`、`model_invalid_response`），便于测试断言与监控分类。
- **基础设施层**：配置校验使用 Python 内置 `ValueError`（如 `rate_limit must be positive`、`model price snapshot version must be a bounded safe identifier`），这类错误通常不应被 API 捕获，会走 Python 未处理异常路径。

### 3.2 Problem Details 格式
所有 HTTP 错误响应遵循 RFC 7807：
```json
{
  "type": "...",
  "title": "...",
  "status": 400,
  "request_id": "...",
  "detail": "..."
}
```
媒体类型为 `application/problem+json`，且每个响应都附带 `request.state.request_id`，便于跨请求链路追踪。

### 3.3 前端错误处理策略
- `ApiError` 是前端唯一的网络错误类型，携带 `status` 与 `detail`。
- 写操作使用 `jsonPost`，遇到 403 `CSRF validation failed` 时自动清空本地 CSRF 缓存并重发一次，避免重复弹窗。
- 管理后台使用结果联合类型 `{ok, data}` / `{ok: false, status, title}`，让 UI 自行决定如何渲染错误卡片。
- 页面级 `error.tsx` 作为兜底，当 React 渲染阶段抛出未捕获异常时显示友好提示并引导至支持页。

### 3.4 速率限制错误
`WindowRateLimiter` 内部抛出 `RateLimitExceededError(retry_after_seconds=...)`，调用方应将其包装为 `ApiProblem(status=429, detail=..., headers={"Retry-After": str(retry)})`，从而向前端传递可恢复的限流信息。

## 4. 约定与约束

- **HTTP 错误必须通过 `ApiProblem` 抛出**：`main.py` 仅注册了 `ApiProblem` 和 `RequestValidationError` 的全局处理器，其他异常不会自动转换为结构化响应。
- **问题类型命名空间**：业务问题使用 `urn:fateradar:problem:*` 形式的 URI（如 `urn:fateradar:problem:invalid-request`），通用问题使用 `about:blank` 占位。
- **请求 ID 注入**：`problem_response` 强制写入 `request_id` 字段，要求上游日志系统通过 `install_request_observability` 设置 `request.state.request_id`。
- **OpenAPI 契约一致性**：`create_app` 主动删除 OpenAPI 文档中的 422 响应，表明 422 不再出现在公开契约中，客户端不应依赖 Pydantic 自动验证错误。
- **领域异常不泄漏**：`ReadingOrchestratorError` 及其子类仅在进程内传播，最终由编排器/适配器层转换为 `ApiProblem` 或记录日志后再向上抛出明确 HTTP 语义的异常。
- **前端 CSRF 重试**：`jsonPost` 对 403 `CSRF validation failed` 做透明重试，属于前端特有的容错约定，不应在业务代码中手动判断该字符串。
- **管理后台统一错误形态**：`adminFetch` 始终返回 `{ok, ...}` 联合类型，UI 层不得假设 fetch 成功才存在 `data`。

## 5. 适用范围

该错误处理体系覆盖后端 FastAPI HTTP 入口、阅读编排领域层、以及 Web 与管理后台两个前端应用。Worker 进程（`worker/readings.py`）与原生 Mingli 运行时之间的错误通过 `RuntimeTransportError` / `NarrativeGenerationError` 等进程内异常表示，不直接产生 HTTP 响应。
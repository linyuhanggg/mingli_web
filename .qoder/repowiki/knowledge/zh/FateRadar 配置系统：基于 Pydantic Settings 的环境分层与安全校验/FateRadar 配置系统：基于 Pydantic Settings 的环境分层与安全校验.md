---
kind: configuration_system
name: FateRadar 配置系统：基于 Pydantic Settings 的环境分层与安全校验
category: configuration_system
scope:
    - '**'
source_files:
    - backend/app/config.py
    - backend/.env.example
    - infra/fateradar-test.env.example
    - web/.env.example
    - admin/src/lib/env.ts
    - backend/app/main.py
    - web/next.config.ts
    - infra/docker/backend.Dockerfile
    - backend/tests/test_config.py
---

## 1. 使用的系统与框架

后端采用 pydantic-settings（BaseSettings + SettingsConfigDict）作为统一的配置加载与校验中心，所有运行时参数集中在 backend/app/config.py 的 Settings 类中声明。前端（Web 与管理后台）使用 Next.js 的 process.env 读取构建期/运行期环境变量。

## 2. 关键文件与包

- backend/app/config.py：核心配置模型、来源编排、生产安全校验、单例 get_settings()。
- backend/.env.example：本地开发默认 .env 模板。
- infra/fateradar-test.env.example：代码测试环境（systemd + Nginx 部署）共享的环境变量清单。
- web/.env.example：Next.js 前端仅需要的 BACKEND_INTERNAL_URL。
- admin/src/lib/env.ts：管理后台的 NEXT_PUBLIC_MINGLI_ENV 解析器。
- backend/tests/test_config.py：覆盖生产安全规则、SMTP 必填字段、默认值等配置的单元测试。
- backend/app/main.py：通过 create_app(settings=...) 注入 Settings，并据此装配 OTP、速率限制、日志级别等组件。
- web/next.config.ts：构建期读取 BACKEND_INTERNAL_URL 重写 /api/* 到后端。
- infra/docker/backend.Dockerfile：容器镜像不复制 .env，依赖外部注入的 MINGLI_* 环境变量。

## 3. 架构与约定

### 3.1 单一来源 + 多源合并
Settings.settings_customise_sources 自定义了 5 个配置源的优先级（从高到低）：
1. init_settings — 测试/工厂直接传入的字典。
2. _MappingSettingsSource(exact_deepseek_secret) — 单独从 DEEPSEEK_API_KEY 环境变量读取 DeepSeek API Key。
3. _MappingSettingsSource(filtered_environment) — 其余 os.environ，但会剔除 DEEPSEEK_API_KEY / deepseek_api_key。
4. _MappingSettingsSource(filtered_dotenv) — dotenv 文件，同样剔除 DeepSeek 密钥。
5. _MappingSettingsSource(filtered_file_secrets) — pydantic file secrets 源，也剔除 DeepSeek 密钥。

这样做的目的是让 DEEPSEEK_API_KEY 走独立路径，避免被其他过滤逻辑污染；同时确保该密钥不会出现在普通 environment/dotenv/file-secrets 的快照中。

### 3.2 命名与可见性
- 后端配置统一以 MINGLI_ 为前缀（env_prefix="MINGLI_"），如 MINGLI_DATABASE_URL、MINGLI_OTP_ADAPTER、MINGLI_COOKIE_SECURE 等。
- 敏感字段使用 SecretStr（如 smtp_username、smtp_password、identity_hash_key、content_encryption_key_b64、deepseek_api_key），其 repr 会被遮蔽。
- 前端仅暴露 NEXT_PUBLIC_MINGLI_ENV 给管理后台；Web 前端只读 BACKEND_INTERNAL_URL。

### 3.3 启动时装配
main.create_app 在应用生命周期内根据 Settings 选择 OTP 适配器（fake / smtp / disabled / production-fail-closed）、创建速率限制器、解析可信代理 CIDR、配置日志级别，并将 settings 挂到 application.state.settings 供后续依赖注入使用。Worker 进程通过相同的 get_settings() 获取一致配置。

### 3.4 环境与部署分层
| 层级 | 配置文件 | 说明 |
|---|---|---|
| 本地开发 | backend/.env.example | 全部使用 fake 适配器、loopback DB、非 secure cookie |
| 代码测试 | infra/fateradar-test.env.example | systemd EnvironmentFile，API/Worker 共享，Web 不读取 |
| 容器镜像 | Dockerfile | 不拷贝 .env，由编排层注入 MINGLI_* |
| 前端 | web/.env.example | 仅 BACKEND_INTERNAL_URL，构建期生效 |
| 管理后台 | NEXT_PUBLIC_MINGLI_ENV | 用于 UI 显示当前部署环境 |

## 4. 约定与约束

以下约束由 Settings.enforce_production_safety 的 @model_validator(mode="after") 在实例化时强制校验，违反即抛出 ValidationError，并被 test_config.py 断言覆盖：

- 生产环境安全开关：environment == "production" 时必须 cookie_secure=True；禁止 otp_adapter="fake"；禁止 runtime_adapter="fake"；禁止 model_adapter="fake"。
- SMTP OTP 必填字段：启用 smtp 时必须提供 smtp_host、smtp_username、smtp_password、smtp_sender；且生产环境禁用 SMTP OTP（需要持久化挑战存储）。
- 密钥不可复用/不可本地：identity_hash_key 不得以 local-only- 开头；content_encryption_key_b64 必须是恰好 32 字节的 base64；两者不得相同；生产环境必须注入真实密钥。
- P0 模型白名单冻结：model_provider、model_profile_id、model_id、model_base_url、model_endpoint_path、model_thinking_mode 必须等于内置常量；DeepSeek 模式下 temperature 固定为 0.2、max_output_tokens 固定为 4096；model_price_currency 必须为 CNY；token 价格必须为非负整数且不超过 10^12。
- 超时与大小边界：connect/read/overall 超时必须在 0~上限范围内，且 overall >= max(connect, read)；model_max_response_bytes 必须在 1MB 以内；model_temperature 必须在 [0,2]；model_max_output_tokens 必须在 [1,8192]。
- Runtime 路径锁定：生产环境要求 runtime_launcher_path、runtime_python_path、runtime_release_root、runtime_state_root 为绝对路径，且必须等于内置常量；runtime_expected_manifest_digest 和 runtime_expected_capability_shape_sha256 必须匹配冻结值。
- 流量门控：real_traffic_enabled 在生产环境默认为 False，且即使开启也会因 Phase 0 gates 未关闭而拒绝；若开启则必须同时设置 alert_sink_enabled=True。
- 路径合法性：任何 runtime 相关 Path 字段不能是相对路径。

此外，web/next.config.ts 将 BACKEND_INTERNAL_URL 在构建期拼入 rewrite 目标，意味着前端对后端的访问地址是编译期绑定而非运行期可变的——这是前端侧的配置约束。

## 5. 总结

FateRadar 的配置系统以 backend/app/config.py 中的 Settings 为中心，用 pydantic-settings 完成类型化、来源合并与集中式安全校验；通过 MINGLI_* 环境变量驱动后端行为，通过 BACKEND_INTERNAL_URL 与 NEXT_PUBLIC_MINGLI_ENV 驱动前端与管理后台。所有生产级安全策略（Cookie、OTP、Runtime、Model、密钥、流量门控）都在配置实例化阶段强制执行，并由单元测试持续回归，从而把部署配置错误提前到应用启动阶段暴露出来。
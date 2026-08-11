---
kind: external_dependency
name: DeepSeek 模型通过 DashScope 接入
slug: deepseek-dashscope
category: external_dependency
category_hints:
    - vendor_identity
    - auth_protocol
scope:
    - '**'
---

真实模型联调使用 DeepSeek，经由阿里云 DashScope 平台调用；测试环境通过 `MINGLI_MODEL_ADAPTER=fake` 关闭真实模型调用，且明确禁止在测试文件中写入 `DEEPSEEK_API_KEY`。生产密钥必须通过 Secret Manager/运行环境注入，仓库内不得包含真实 API Key。
---
status: accepted
date: 2026-08-17
---

# 分离可见核心源码与本机 Runtime 安装

`mingli-master` 的权威源码使用 `core/mingli-master` 下可见、可被 NAS
同步的独立 Git 工作树。`mingli_web` 不 vendor、不 import、也不拥有该
工作树的 Git 历史；两者仍只通过既有 JSON Adapter seam 协作。

`.runtime` 只保存签名 Runtime Release、状态目录和可重新生成的本机
运行产物。算法、规则和证据不得只修改在 `.runtime` 中。核心修改必须先
进入可见源码工作树，再经过核心发布门禁生成 Runtime Release。

## Consequences

- MacBook 与 NAS 同步 `core/mingli-master`，不会再依赖 Finder 默认隐藏的
  `.runtime` 才能获得最新核心源码。
- 网站父仓库忽略 `core/mingli-master`，但核心工作树由自己的 Git 管理；
  Git 忽略不参与 Synology 的文件同步判断。
- 源码测试默认跨 `core/mingli-master/scripts` seam；只有发布准入、Worker
  和回滚测试读取 `.runtime` 中的签名制品。
- 源码工作树未提交或发布门禁未通过时，不得把它冒充 Runtime Release。

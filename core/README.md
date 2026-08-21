# Mingli Core workspace

`core/mingli-master/` 是从原版仓库 `mingli-master-skill` 移植进本仓库的算法源码。
它是 `mingli_web` 的一部分，随本仓库一起版本管理；不是另一个独立网站仓库。

原版 skill 仓库仍在 `https://github.com/linyuhanggg/mingli-master-skill`。
移植时留下的原版 `.git` 已挪到 `core/.mingli-master-skill.git/`，只作本地备份，
不入库，也不再让 `core/mingli-master` 看起来像另一个仓库。

两个目录职责不同：

- `core/mingli-master/`：编辑、审查、测试算法源码。
- `.runtime/v53-time-check-release/`：本机签名 Runtime，由发布门禁生成，不入库。

从网站根目录运行 `make mingli-core-status`，确认源码在、并且已安装 Runtime
没有相对受管源码发生漂移。不要把手改写进 `.runtime`。

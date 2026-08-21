# 命理大师 V5.1 便携核心重构验收记录

日期：2026-07-29

## 验收结论

本次重构已经达到目标架构：同一份 `mingli-master` 可由 Codex、Hermes 或其他宿主通过相同事务接口调用；Hermes 仅做普通消息收发，不再理解、复核或拦截命理结果；`Accepted.public_copy` 是唯一最终交付内容。

生产接口收敛为三个命令和四类结果：

- `describe`、`prepare`、`complete`
- `Described`、`Prepared`、`Accepted`、`Stopped`

旧的外部 observer、独立验签、摘要重建、交付 guard、命理意图/续问正则和第二套事务账本均不再参与目标运行路径。核心保留输入、状态、reading lineage、引用和原子存储一致性校验，但这些校验不再是 Skill 与宿主之间的信任协议。

## 实现提交

Skill 工作树的功能与文档提交：

- `714d85b` `feat: compose portable reading transactions`
- `2017eda` `refactor: derive provider capabilities from manifests`
- `232ca0e` `refactor: delete the cross-check review ledger`
- `9a49932` `refactor: remove retired calculator delivery pipelines`
- `947ed05` `refactor: remove legacy capability authority`
- `6057427` `fix: stabilize provider release evidence`
- `2b1beab` `fix: align provider seams with portable contracts`
- `10a75a5` `chore: refresh portable provider snapshot`
- `42fa2d2` `docs: finalize portable core architecture`
- `96c1aa6` `fix: keep audit capabilities manifest-driven`

Hermes 工作树的去命理化提交：

- `e39a121ab7` `refactor(gateway): remove domain-specific API delivery path`
- `6cbd0d997a` `refactor(gateway): remove domain-specific message loop path`
- `965bc8b4c8` `refactor(gateway): delete domain-specific modules and tests`
- `0b7aab32a3` `test(gateway): cover plain delivery and profile isolation`

## 可复现验收证据

### Skill 全量回归

在固定 Python 环境、禁用字节码写入并显式指定研究资料根目录的条件下，执行 `unittest discover -s scripts -p 'test_*.py'`：

```text
Ran 1142 tests in 5255.922s

OK
```

测试结尾出现的 `mutation probe` 与 `provider_ready: false` 是篡改探针的预期输出：测试故意令能力清单不可用，并验证审计会 fail-closed；命令退出码为 0。

### Provider 与制品

- Provider 完整性矩阵：13 个 Provider，`findings: []`，`provider_ready: true`。
- 生理相审计能力从 manifest 动态读取；运行期篡改能力清单时正确 fail-closed。
- 词汇本地性审计：`findings: []`，`ok: true`。
- 发布归档审计：782 个文件，`errors: []`，`ok: true`。

### Hermes

Hermes 官方测试脚本对五个受影响测试文件执行 288 项测试：

```text
5 files, 288 tests passed, 0 failed
```

静态扫描 `gateway`、`tools`、`tests` 和顶层 README 后，不存在 `mingli`、`命理` 或 `玄枢` 引用。Gateway 源码不 import 命理模块，也没有命理专用 delivery guard、observer、runtime 或会话判定路径。

这些测试使用 fake runner 和隔离 profile，没有启动真实 Gateway，没有连接消息渠道。

## 目标行为

- 普通消息：Hermes 按普通消息路径收发，不调用 Skill。
- 命理首问：宿主选择 Skill，调用 `prepare`；资料充分时获得不透明 token 和受限 brief。
- 补资料：宿主把用户补充内容作为新的 `prepare` 输入；核心恢复同一 intake/reading 上下文。
- 续问与纠正：宿主显式传入先前公开的 `reading_id` 和关系类型；核心维护 lineage 与版本。
- 重起：宿主显式要求新 reading；核心分配新的 `reading_id`，不复用旧 reading 的隐式上下文。
- 完成：宿主依据 `Prepared` 的受限 brief 自然撰写草稿，再调用 `complete`；核心仅验证不透明 token、非空内容和原子提交条件。
- 成功：核心返回 `Accepted.public_copy`，宿主原样展示，不存在第二层复核或拦截。
- 失败：资料不足、体系不支持、证据为空、草稿为空、token 失效、并发冲突和内部故障均返回非空 `Stopped.public_copy` 与机器可读 reason，不产生空回复。

## 关键边界

“核心不硬编码术语”指：通用事务核心、Skill 路由说明和宿主 Adapter 不维护领域术语清单；Provider 的算法、manifest 和语料仍必须拥有自身领域词汇，否则现有 13 个确定性 Provider 无法工作。术语、支持维度、claim policy 和证据能力由 Provider manifest/data 提供，通用核心只组合结构化字段。

本次没有试图用新的正则或第二个模型机械证明自然语言语义绝不越界。防污染机制是闭世界的 `caller_view`/`claim_policy`：只携带 requested dimensions、allowed subjects/domains、specific-event policy、maximum certainty、supported claims、unresolved boundaries 和 source gaps；宿主环境记忆不进入该视图。语义高对抗审查可在未来作为可选 Adapter，但不是默认交付前置条件。

## 未执行的动作

本次验收没有：

- 部署或安装 Skill；
- 安装或升级依赖；
- 启动、停止或重启 Gateway；
- 连接生产消息渠道；
- 访问生产端口 8642 或 8645；
- push 分支或修改用户的权威源码工作树。

上线与宿主安装属于后续独立变更，应使用本验收通过的提交作为固定输入，并继续保持 Gateway 零命理 import。

## 参考文档

完整架构、状态机、文件迁移映射、deletion test 和需求漏洞修正版见：

- `docs/plans/2026-07-29-mingli-v51-portable-core-final.md`

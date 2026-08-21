# mingli_web Codex 顶层任务通讯录

生成时间：2026-08-20（Asia/Shanghai）
协议版本：`top-level-team-v1`
宿主：`remote-ssh-discovered:macmini-fate`
项目：`/Volumes/Lexar/code/mingli_web`

这是本机运行时通讯录，不是产品需求。岗位发送消息必须使用精确 thread id，不凭标题猜测。

| key | 标题 | 模型 / effort | thread id | 工作目录 |
| --- | --- | --- | --- | --- |
| `project_manager` | `mingli · 项目经理` | Sol / high | `01a01f28-3e2c-75b2-93c7-a28d50cfaf1f` | `/Volumes/Lexar/code/mingli_web` |
| `execution_producer` | `mingli · 执行制作` | Luna / high | `01a01f5f-48bc-73c3-822e-0ea8f9c71f7c` | `/Users/yuhanglin/.codex/worktrees/cfc6/mingli_web` |
| `frontend_developer` | `mingli · 前端开发` | Sol / medium | `01a01f5f-4323-7ef3-b312-ed60632dd63d` | `/Users/yuhanglin/.codex/worktrees/cc6a/mingli_web` |
| `backend_developer` | `mingli · 后端开发` | Sol / medium | `01a01f5f-4210-7cf3-9cfd-5159aab648a5` | `/Users/yuhanglin/.codex/worktrees/5cbf/mingli_web` |
| `core_algorithm_developer` | `mingli · 核心算法` | Sol / high | `01a01f5f-4213-7e12-947d-31da5967bcb9` | `/Users/yuhanglin/.codex/worktrees/5591/mingli_web` |
| `ui_designer` | `mingli · UI 设计师` | Sol / high | `01a01f5f-4122-7d92-b5d7-4604a2de9740` | `/Users/yuhanglin/.codex/worktrees/06bf/mingli_web` |
| `test_engineer` | `mingli · 测试工程师` | Luna / high | `01a01f5f-4204-7333-b1f3-59242e2071c9` | `/Users/yuhanglin/.codex/worktrees/32bf/mingli_web` |
| `user_tester` | `mingli · 用户测试` | Sol / high | `01a01f5f-47a6-71a3-9794-fef97a2c69af` | `/Users/yuhanglin/.codex/worktrees/5f00/mingli_web` |
| `project_assistant` | `mingli · 小助理` | Luna / medium | `01a01f5f-4122-7d92-b5d7-45ef910a49bf` | `/Users/yuhanglin/.codex/worktrees/093c/mingli_web` |

所有任务的 `hostId` 均为 `remote-ssh-discovered:macmini-fate`。

## 确定性直达路由

- `user_tester` UI/UX finding → `ui_designer`，抄送 `project_manager`、`execution_producer`。
- `ui_designer` UI_UX_HANDOFF → `frontend_developer`，抄送 `project_manager`、原 `user_tester`。
- 开发 DONE → `test_engineer`，抄送 `project_manager`。
- `test_engineer` FAIL → 原开发 Owner，抄送 `project_manager`。
- `test_engineer` PASS（用户可见）→ `user_tester`，抄送 `project_manager`。
- `user_tester` PASS → `project_manager` 关单。
- 归属不清、文件冲突、范围变化 → 只交 `project_manager` 裁决。

消息使用根 `AGENTS.md` 的 `TEAM_EVENT` 头部，同一问题全程复用一个事件编号。

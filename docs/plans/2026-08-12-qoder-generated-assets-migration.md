# `.qoder/**` 生成物非破坏迁移计划

日期：2026-08-12。状态：**待用户批准后执行**（批准前不改动任何文件）。

## 裁决

用户已于 2026-08-12 裁决：`.qoder/**` 是**生成物**，不是正式知识资产。

事实基线：`.qoder/` 共 416MB、338 个被跟踪文件。其中 `repowiki/` 409MB（工具生成的仓库知识库，可随时重新生成），`better-harness/` 6MB（2026-08-11 harness 运行产物：canvas/findings/report）。正式项目知识继续保存在 `docs/`、`CONTEXT.md`、`design-system/` 与 Nowledge Mem，不依赖 `.qoder`。

## 原则

1. 非破坏：先备份、后摘跟踪；本地磁盘文件在备份验证前不删除。
2. 不改写历史：`git filter-repo` 之类的历史瘦身属破坏性操作，默认不做；如未来要做，需单独批准且先在备份仓库上演练。
3. 可回滚：每一步都有反向操作。

## 步骤（批准后立即执行，约 30 分钟）

1. **冻结**：本计划批准前，不再向 `.qoder/` 提交任何新内容。（已通过 `.qoder/worktrees/` 作为 worktree 目录的惯例保持不跟踪。）
2. **备份**：`tar -czf <仓库外路径>/qoder-backup-2026-08-12.tar.gz .qoder`，核对文件数（338）与解压抽查；备份位置执行时由用户指定（默认 `~/backups/mingli_web/`）。
3. **摘除跟踪**：单独一个提交——`git rm -r --cached .qoder` + 在 `.gitignore` 增加 `.qoder/`。文件保留在磁盘，仓库停止跟踪。提交信息：`chore: stop tracking generated .qoder artifacts`。
4. **磁盘清理（可选，单独确认）**：确认备份可用后，删除 `.qoder/repowiki` 与 `.qoder/better-harness` 的本地副本（保留 `.qoder/worktrees`）。需要历史报告时从备份或重新生成恢复。
5. **验证**：`git status` 干净；`make check` 不受影响；`git ls-files .qoder` 为空。

## 回滚

- 第 3 步后反悔：`git revert` 该提交即可恢复跟踪；磁盘文件未动。
- 第 4 步后反悔：从第 2 步备份解包恢复。

## 明确不做

- 不删除 `docs/` 内任何人写文档。
- 不在本次改写 git 历史（仓库无 remote，历史瘦身收益低、风险高）。
- 不把 repowiki 内容当作权威知识引用；任何有长期价值的结论先人工提炼进 `docs/` 或 Nowledge Mem 再丢弃生成物。

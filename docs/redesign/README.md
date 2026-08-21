# redesign 目录：历史记录，不再是有效合同

本目录保存 2026-08-14 起「方向 C 现代 SaaS 锐感」全站换皮期间的决策记录、阶段报告、视觉审计和施工提示词。

**这些文件不再是有效合同。** 它们是当时的决策依据和施工快照，保留用于追溯，不用于指导当前工作。

## 当前权威在哪里

| 想找什么 | 去哪里 |
|---|---|
| 视觉、组件、交互、响应式、可访问性合同 | `DESIGN.md` |
| 范围、路由、状态、依赖、进度、门禁、当前断点与下一步 | `docs/CHECKLIST.md` |
| 统一领域名词 | `CONTEXT.md` |
| Runtime、Provider、Orchestrator、Guard、ReadingDocument | `docs/MINGLI_V51_WEB_INTEGRATION.md` |
| 真实浏览器、机器、测试和发布证据 | `docs/releases/evidence/**` |

其中两份规格已在正文首部明确标注不再是有效合同，并由 `tests/contract/test_document_authority.py` 锁定：

- `2026-08-17-bazi-result-page-dev-spec.md`
- `2026-08-17-ux-differentiation-spec.md`

## 内容分类

- **决策记录**：`2026-08-14-direction-c-decision.md`、`2026-08-16-homepage-liquid-glass-prototype-decision.md`。方向 C 的批准记录同时写在 `docs/CHECKLIST.md` §15。
- **阶段报告与视觉审计**：`2026-08-14-visual-audit.md`、`2026-08-14-phase{1..5}-report.md`、`2026-08-14-final-report.md`。报告中的测试数字是当时的快照，不代表当前构建。
- **施工提示词**：`2026-08-14-codex-goal-prompt.md`、`2026-08-18-codex-goal-prompt{,-r2,-r3,-r4}.md`、`2026-08-19-codex-goal-prompt-r5.md`。这些是历史派工输入，其中的红线只对当轮有效，不构成当前授权范围；当前授权边界见 `AGENTS.md`。

## 纪律

按 `docs/CHECKLIST.md` §0 规则 1，不得在本目录新增施工叙事日志；§0 规则 7 要求施工过程记录写进 `docs/releases/evidence/**`。按 §0 规则 4，本目录内容纠错请新增 dated addendum，不覆盖原文。

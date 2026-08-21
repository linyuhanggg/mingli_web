# 2026-08-16 首页液态玻璃动态原型 Design QA

`design-qa.md` 原先散落在仓库根目录，2026-08-21 按 `docs/CHECKLIST.md` §0 的证据纪律迁入本目录，内容逐字未改。

记录的是 2026-08-16 对公共首页 `/` 液态玻璃原型的浏览器对照 QA：参考图与实装同屏对照、四档视口无横向溢出、动效证据、`prefers-reduced-motion` 行为，以及六条修正记录和剩余差异。

对应的方向决策记录在 `docs/redesign/2026-08-16-homepage-liquid-glass-prototype-decision.md`。

## 边界

这是**单页视觉对照证据**，不是 P4 门禁结果。它不构成 `BROWSER_VERIFIED`，更不构成 `USER_ACCEPTED`；首页的用户验收仍须走 `docs/CHECKLIST.md` §14.1 的逐页清单。

文中引用的参考图与截图路径位于本机 `~/.codex/generated_images/` 与 `web/e2e/screenshots/audit-2026-08-16/`，不在本目录内。

# Bazi G5 density evidence — blocked

日期：2026-08-18

本目录暂不包含截图。按浏览器技能要求选择本机真实浏览器后，浏览器连接返回无可用实例，`agent.browsers.list()` 返回空列表；因此没有用 Playwright、Fixture 或静态 HTML 冒充 G5 真实浏览器证据。

已完成的非浏览器证据：

- `web/src/test/bazi-chart-density.test.tsx`：关系图/语义表、五行计数、大运三态、五层面板和过渡约束的 6 项测试全部通过；B/C 阶段定向回归共 `35 passed`，C5 最终目标测试为 `6 passed`。
- 全量 `make check`：Backend `1058 passed / 131 skipped`，Web `80 files / 500 passed`，Admin `33 files / 123 passed`，Ruff、mypy、两端 lint/typecheck/production build 全部通过。目标回归覆盖十神标签与关联 stem、藏干元素贡献的联动高亮，并约束高亮样式不使用 box-shadow 或前景色。

仍缺：1440/768 并排真实 Chrome 截图、360/1024 四视口补证、页面级横向溢出实测，以及与 `qingnang/site` 的结构化事实计数。此文件是阻塞记录，不是 `BROWSER_VERIFIED` 或用户验收声明。

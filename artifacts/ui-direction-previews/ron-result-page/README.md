# RON 风格八字结果页方向探索（2026-08-19 归档）

暗底 + 荧光玉绿 + 玻璃面的结果页方向,只做过视觉比较,**未经批准,未进入任何正式路由**。

## 归档原因

该原型原先落在 `web/src/app/%5Fui-lab/rondesign-prototype/`,作为 `/_ui-lab` 路由可在开发态浏览。
但 `tests/contract/test_ui_token_authority.py` 按目录扫描 `web/src/**/*.css`,`/_ui-lab` 不在任何豁免名单内,
因此该原型触发 31 条违规:27 条颜色字面量、多处渐变与 mask、1 条无限装饰动效(`ronDash`)、
3 处 `var(--font-domain)` 越出两个盘面白名单文件。

它回答的是**结果页**的问题,与同期首页/录入页的调整不是同一件事,所以按单独立项处理:
源码在此原样归档(加 `.archived` 后缀,不参与构建、lint 与 typecheck),截图留档,
`web/src` 恢复干净,冻结的视觉合同一条未改。

## 文件

| 文件 | 说明 |
|---|---|
| `page.tsx.archived` | 原型页,数据取自 `@/fixtures/bazi-evidence-result` 合成 Fixture |
| `pillar-fan.tsx.archived` | 四柱牌面展开 |
| `evidence-graph.tsx.archived` | 事实路径与古籍锚点的连线视图 |
| `page.module.css.archived` | 暗底荧光绿玻璃皮肤 |
| `ron-1440.png` / `ron-1440-full.png` / `ron-360.png` | 系统 Chrome 实拍,1440 第一屏 / 1440 整页 / 360 第一屏 |

## 与当前生产结果页的差异

原型把四柱做成大字牌面,天干十神、藏干、纳音直接排在牌面内;当前生产渲染器
(`/_ui-lab/bazi-result` 与真实 `/bazi` 结果页)是紧凑柱位加密集事实表。
同视口对照图见 `../../../snapshots/direction-compare-20260819/`(该目录为可再生产物,已 gitignore)。

## 若要恢复为可浏览路由

需要先决定它是否成为方向,并至少处理:

1. `DESIGN.md` 的皮肤规则本身要不要改(§0 纪律第 3 条:须先写影响范围、迁移与重新验收项并由用户批准);
2. 若只作为 UI Lab 原型长期保留,需要给 `test_ui_token_authority.py` 加一条**限定到该目录**的豁免并记录理由
   ——不能豁免整个 `/_ui-lab`,因为同目录下的 `bazi-result` 是必须与生产渲染器同皮肤的验收 Fixture;
3. 暗底方案要另做对比度与 `prefers-reduced-motion` 复核,`ronDash` 无限动效需改为有界或可关闭。

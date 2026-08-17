# design-sync NOTES（mingli_web → claude.ai/design 项目 FateRadar）

首次同步：2026-08-18，范围＝`web/src/components/ui/` 的 8 个基元。同日第二批：加了 11 个页面外壳/布局组件（`Container`、`BrandMark`、`ButtonLink`、`AppPageHeader`、`SiteHeader`、`SiteFooter`、`PublicPageShell`、`PrivateShell`、`StatusPanel`、`TaskCard`、`EditorialPage`），其中 5 个因为下面的 next/image bug 目前只能停在 floor card。

## 仓库特有的坑

- **这不是一个组件库包**：`web/` 是 Next.js 应用，没有 `dist/`、没有 Storybook。走 package 形态的 **synth-entry** 模式，组件靠 `cfg.componentSrcMap` 逐个指定源码路径。
- **PKG_DIR 现在锚定在 `.design-sync/`，不是 `web/`**：仓库没有根 `package.json`，而 JS bundle 的实际导出内容只看 `--entry` 指向的文件（`cfg.componentSrcMap` 只喂 `.d.ts`/预览流水线，**不会**改变 bundle 里真正 export 了什么——第二批一开始踩了这个坑：11 个新组件的 `.d.ts`/`.html`/`.prompt.md` 都生成了，但 `window.MingliWeb` 上根本没有这些名字，`[BUNDLE_EXPORT]` 报错）。解法是 `.design-sync/ds-entry.ts`：一个手写的 barrel，`export *`/具名 `export` 出所有要同步的组件，`--entry` 指到它。因为 `.design-sync/` 本身没有 `package.json`，而 PKG_DIR 解析逻辑是"从 entry 文件所在目录往上找第一个有 `name` 字段的 `package.json`"——不给它一个会一路走到仓库根之外报 ENOENT。所以 `.design-sync/package.json`（`{"name":"mingli-web","version":"0.1.0"}`）也是必需文件，**不要删**。
  - 连带后果：`componentSrcMap`、`extraEntries`、`tsconfig`、`extraFonts` 里所有路径都要相对 `.design-sync/` 写（例如 `../web/src/components/ui/button.tsx`），不再相对 `web/`。
  - **`.design-sync/node_modules` 是指向 `../web/node_modules` 的符号链接**（已 gitignore，靠 `ln -sfn ../web/node_modules .design-sync/node_modules` 在新 clone 上重建一次）。ts-morph 的 `.d.ts` 类型解析（找 `@types/react`）会从 PKG_DIR 自己往上找 `node_modules/@types/react`，找不到就整批 `.d.ts` body 塌成空对象（`[DTS_REACT]` 警告）；这个符号链接让它在第一层就找到。
- **`cfg.cssEntry` / `cfg.tokensGlob` 在这里都用不了**：token 层在仓库根的 `ui/tokens.css` + `ui/base.css`，两个字段都够不到。解法是 `.design-sync/ds-global-styles.ts`：只 `import "../ui/tokens.css"` 和 `"../ui/base.css"` 的模块，通过 `cfg.extraEntries` 把两份全局 CSS 内联进 `_ds_bundle.css`。**不要删这个文件**。
- **next/image 在这套打包链路下是坏的（已确认根因，非环境问题）**：`BrandMark` 用 `import Image from "next/image"`，esbuild 把这个默认导入解析成了 `next/image` 的整个模块命名空间对象（`{default, getImageProps}`），而不是解包出 `.default`（真正的 forwardRef 组件）；同一个 bundle 里若改成 `export {default as X} from "next/image"` 这种纯重导出写法，解析是对的——说明是 esbuild 对"套了一层 `module.exports = require(...)` 转发的 CJS 模块 + 默认导入（非重导出）"这个组合的边界情况，不是配置问题，也不该为此去 fork `lib/bundle.mjs`（SKILL 明确禁止）。
  - 受影响：`BrandMark`（直接用 `next/image`）、`SiteHeader`（渲染 `BrandMark`）、`PublicPageShell`（渲染 `SiteHeader`）、`PrivateShell`（渲染 `BrandMark`）、`EditorialPage`（渲染 `PublicPageShell`）——这 5 个组件的**真实渲染**会抛 `Element type is invalid`。
  - **这 5 个组件故意不写 authored preview**：floor card 机制会把渲染崩溃悄悄兜底成占位卡（`fallbackCard`），这是唯一让它们通过 gate 的方式；一旦写了 preview，崩溃就会变成 `bad:true` 的硬失败（因为 authored preview 没有 floor card 的兜底）。**不要给这 5 个组件加 `.design-sync/previews/<Name>.tsx`**，除非 next/image 的问题先被解决。
  - `next/link`、`next/navigation`（`usePathname`）本身是好的，已验证：`SiteFooter`、`ButtonLink`、`TaskCard` 等用 `next/link` 的组件渲染正常。
- **框架内部代码在浏览器沙箱里访问 `process.env.*` 会整个 bundle 崩掉**：next/link 的内部代码在模块顶层探测 `process.env.__NEXT_*` 系列 feature flag，而 IIFE bundle 跑在没有 `process` 全局的浏览器里，未定义的 `process.env.X` 访问会抛 `ReferenceError: process is not defined`——因为是模块顶层执行，这会让**整个** `window.MingliWeb` 赋值失败，牵连所有组件，不只是用了 `next/link` 的那些。解法是 `.design-sync/process-shim.ts`，作为 `ds-entry.ts` **第一行 import**（顺序关键——必须在任何可能间接引入 next/* 内部代码的 export 之前），运行时挂一个 `globalThis.process = {env:{}}`。**不要删、不要挪到 entry 文件的非首行位置**。
- **playwright 要单独装在 `.ds-sync/`**：仓库只有 `@playwright/test`（在 `web/node_modules`），validate 需要能 `require('playwright')`。装 `playwright@1.62.1`（与仓库钉的版本一致，对应缓存里的 chromium-headless-shell build 1234），运行时带 `NODE_PATH=./.ds-sync/node_modules`。chromium 用 `cd web && npx playwright install chromium` 装。
- **`du` 的体积数字会吓人**：仓库在 Lexar 卷上，块大小 1MB，`du` 报的目录大小比实际字节大几十倍。别据此裁字体或组件。

## 已知的 render warn（下次 re-sync 若再出现属正常，不用追）

- `[FONT_MISSING] "Hiragino Sans GB" / "Microsoft YaHei" / "Songti SC" / "STSong"`：`--font-sans` 与 `--font-domain` 字体栈里的**系统字体回退项**，本来就不该随包发。品牌字体 Noto Sans SC Variable / Noto Serif SC Variable 已通过 `cfg.extraFonts` 打进 `fonts/`，203 个 woff2 子集。

## 预览与覆盖

- 14/19 个组件有 authored preview，全部评为 good：8 个基元 + `Container`/`AppPageHeader`/`ButtonLink`/`SiteFooter`/`StatusPanel`/`TaskCard`。
- 5 个组件（`BrandMark`/`SiteHeader`/`PublicPageShell`/`PrivateShell`/`EditorialPage`）停在 floor card，原因见上面的 next/image 坑，**这是预期状态，不是要修的 bug**。
- `cfg.overrides`：Dialog / Drawer 用 `cardMode: single`（radix portal 会逃出卡片格）；Table / TaskCard / AppPageHeader 用 `cardMode: column`（AppPageHeader 的 `<h1>` 用了 `--font-size-page`，标准网格格宽会把标题挤成竖排逐字换行——这个 override 不是可选项，删了会看起来像 bug）。
- Table 里可排序表头是 `<button>`、不可排序的是纯文本，二者基线略有错位——组件本身行为，不是预览问题。

## Re-sync risks（下次跑之前先看这里）

- **`ds-global-styles.ts` 与 `ui/` 是隐式耦合**：`ui/tokens.css`、`ui/base.css` 改名或挪位置，构建不报错，只会安静少掉 token。
- **conventions.md 里逐条列了真实 token 名和组件 API**：`ui/tokens.css` 改 token 名、或这批组件的 props 变化后，header 会开始撒谎。re-sync 按 SKILL 的 validation pass 重新核对。
- **组件清单是硬编码的**：`cfg.componentSrcMap`（.d.ts/预览用）和 `ds-entry.ts`（JS bundle 实际导出用）要**同步维护**——两者不一致就会出现"有文档没导出"或"能导出没文档"。新增/移除组件时两处都要改。
- **next/image 问题如果哪天在 esbuild 或 Next 版本升级后消失**：可以把 `BrandMark`/`SiteHeader`/`PublicPageShell`/`PrivateShell`/`EditorialPage` 加回 `.design-sync/previews/`，同时把 conventions.md 里"已知限制"那一节删掉。判断方法：重跑 `.ds-sync/package-validate.mjs`，如果 `render check` 里这 5 个不再是 `floor card` 而是干净渲染，说明修好了。
- **本次没有同步 `surfaces/`（16 个）与 `readings/`、业务 flow 组件**（后者绑 API 调用，静态渲染没意义）。要扩范围就往 `componentSrcMap` **和** `ds-entry.ts` 两处加。
- 本次构建假设：node 26 / esbuild 0.28 / ts-morph（装在 `.ds-sync/`）、playwright 1.62.1 + 本地 chromium 缓存。字体全部来自本地 node_modules，无网络抓取。

## 完整命令

```sh
# 一次性：暂存脚本 + 装依赖（.ds-sync/ 已 gitignore）
mkdir -p .ds-sync && cp -r <skill-dir>/{package-build,package-validate,package-capture,resync}.mjs <skill-dir>/lib <skill-dir>/storybook .ds-sync/
echo '{"name":"ds-sync-deps","private":true}' > .ds-sync/package.json
(cd .ds-sync && npm i esbuild ts-morph @types/react playwright@1.62.1)

# 新 clone 上重建符号链接（.design-sync/node_modules 已 gitignore）
ln -sfn ../web/node_modules .design-sync/node_modules

# re-sync（先把项目的 _ds_sync.json 抓到 .design-sync/.cache/remote-sync.json）
NODE_PATH=./.ds-sync/node_modules node .ds-sync/resync.mjs \
  --config .design-sync/config.json --node-modules web/node_modules \
  --entry ./.design-sync/ds-entry.ts --out ./ds-bundle \
  --remote .design-sync/.cache/remote-sync.json
```

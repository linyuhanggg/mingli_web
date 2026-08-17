# design-sync NOTES（mingli_web → claude.ai/design 项目 FateRadar）

首次同步：2026-08-18。范围＝`web/src/components/ui/` 的 8 个基元（Button / Field / Segmented / Tabs / Dialog / Drawer / Status / Table）。

## 仓库特有的坑

- **这不是一个组件库包**：`web/` 是 Next.js 应用，没有 `dist/`、没有 Storybook。走 package 形态的 **synth-entry** 模式，组件靠 `cfg.componentSrcMap` 逐个指定源码路径。
- **必须传 `--entry`**：不传的话 `PKG_DIR` 会解析成 `web/node_modules/mingli-web`（不存在，直接 ENOENT）。传 `--entry ./web/src/components/ui/index.ts`，脚本会向上走到 `web/package.json`。完整命令见文末。
- **`cfg.cssEntry` / `cfg.tokensGlob` 在这里都用不了**：token 层在仓库根的 `ui/tokens.css` + `ui/base.css`，而 `cssEntry` 被硬绑定在包目录（`web/`）内，`tokensGlob` 只对 node_modules 里的 `tokensPkg` 生效——两者都会打印 “resolves outside the package — skipped”，`tokens/` 目录会是空的。解法是 `.design-sync/ds-global-styles.ts`：一个只 `import "../ui/tokens.css"` 和 `"../ui/base.css"` 的模块，通过 `cfg.extraEntries` 进来，让 esbuild 把两份全局 CSS 直接内联进 `_ds_bundle.css`。**不要删这个文件**，删了组件就只剩没有 token 定义的 CSS Module 类。
- **playwright 要单独装在 `.ds-sync/`**：仓库只有 `@playwright/test`（在 `web/node_modules`），validate 需要能 `require('playwright')`。装 `playwright@1.62.1`（与仓库钉的版本一致，对应缓存里的 chromium-headless-shell build 1234），运行时带 `NODE_PATH=./.ds-sync/node_modules`。chromium 用 `cd web && npx playwright install chromium` 装。
- **`du` 的体积数字会吓人**：仓库在 Lexar 卷上，块大小 1MB，`du` 报 `ds-bundle` 327MB，实际字节只有 11.6MB（fonts 10.2MB）。别据此裁字体。

## 已知的 render warn（下次 re-sync 若再出现属正常，不用追）

- `[FONT_MISSING] "Hiragino Sans GB" / "Microsoft YaHei" / "Songti SC" / "STSong"`：这些是 `--font-sans` 与 `--font-domain` 字体栈里的**系统字体回退项**，本来就不该随包发。栈里真正的品牌字体 Noto Sans SC Variable / Noto Serif SC Variable 已经通过 `cfg.extraFonts`（@fontsource-variable）打进 `fonts/`，共 203 个 woff2 子集。`--font-domain` 在设计工具里会落到 Noto Serif SC，与线上 macOS 上的 Songti SC 略有差异，属预期。

## 预览与覆盖

- 8 个组件全部有 authored preview（`.design-sync/previews/*.tsx`），共 19 个 cell，全部评为 good。素材来自 `web/src/components/ui/primitives.test.tsx` 里的真实用法（Segmented 的历法选项、Tabs 的盘面/报告/核对、Table 的列定义）。
- `cfg.overrides`：Dialog / Drawer 用 `cardMode: single` + 固定 viewport（radix portal 会逃出卡片格），Table 用 `cardMode: column`（表格比多列格宽）。
- Table 里可排序表头是 `<button>`、不可排序的是纯文本，二者基线略有错位——这是组件本身的行为，不是预览问题。

## Re-sync risks（下次跑之前先看这里）

- **`ds-global-styles.ts` 与 `ui/` 是隐式耦合**：如果 `ui/tokens.css`、`ui/base.css` 改名或挪位置，构建不会报错，只会安静地少掉 token（validate 里 `tokens: N defined` 会掉下来）。改动 `ui/` 时同步检查这个文件。
- **conventions.md 里逐条列了真实 token 名**：`ui/tokens.css` 改 token 名后，header 会开始撒谎。re-sync 时按 SKILL 的 validation pass 重新 grep 一遍 `_ds_bundle.css`。
- **组件清单是硬编码的**：`cfg.componentSrcMap` 手写了 8 条路径。`web/src/components/ui/index.ts` 新增导出后，不改 config 就不会同步进来。
- **本次没有同步 `surfaces/` 与页面级 flow 组件**（用户明确只要 ui 基元）。要扩范围就往 `componentSrcMap` 加。
- 本次构建假设：node 26 / esbuild 0.28 / ts-morph（装在 `.ds-sync/`）、playwright 1.62.1 + 本地 chromium 缓存。字体全部来自本地 node_modules，无网络抓取。

## 完整命令

```sh
# 一次性：暂存脚本 + 装依赖（.ds-sync/ 已 gitignore）
mkdir -p .ds-sync && cp -r <skill-dir>/{package-build,package-validate,package-capture,resync}.mjs <skill-dir>/lib <skill-dir>/storybook .ds-sync/
echo '{"name":"ds-sync-deps","private":true}' > .ds-sync/package.json
(cd .ds-sync && npm i esbuild ts-morph @types/react playwright@1.62.1)

# re-sync（先把项目的 _ds_sync.json 抓到 .design-sync/.cache/remote-sync.json）
NODE_PATH=./.ds-sync/node_modules node .ds-sync/resync.mjs \
  --config .design-sync/config.json --node-modules web/node_modules \
  --entry ./web/src/components/ui/index.ts --out ./ds-bundle \
  --remote .design-sync/.cache/remote-sync.json
```

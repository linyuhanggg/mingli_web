# Conventions

Mingli Web 的 UI 基元层。8 个组件：`Button`、`Field`、`Segmented`、`Tabs`、`Dialog`、`Drawer`、`Status`、`Table`。产品语言是简体中文——所有示例文案都用中文写。

## 无需 Provider

组件不读任何 React context，直接渲染即可，不要包 ThemeProvider / Router / i18n 之类的外壳。样式全部来自 `styles.css` 的 `@import` 闭包（`fonts/fonts.css` + `_ds_bundle.css`，后者含 tokens、全局 base 层与各组件的 CSS Module 类）。只要那份 `styles.css` 生效，组件就是完整样式的。

单一亮色主题：`:root` 上写死 `color-scheme: light`，没有暗色 token 集，不要造 `dark:` 变体或自行反转配色。

## 样式写法：CSS 变量，不是 utility class

这套系统**没有** utility class 词表（没有 Tailwind，没有 `bg-*`/`p-*`）。组件自身的 class 由 CSS Modules 生成、是实现细节，不要去引用或覆写。你自己写布局胶水时，直接用 `var(--*)` token：

| 类别 | 真实 token |
|---|---|
| 面 | `--color-canvas`、`--color-surface`、`--color-surface-subtle`、`--color-surface-muted`、`--color-surface-inverse` |
| 文字 | `--color-text`、`--color-text-secondary`、`--color-text-muted`、`--color-text-inverse` |
| 描边/遮罩 | `--color-border`、`--color-border-strong`、`--color-overlay` |
| 动作 | `--color-action`、`--color-action-hover`、`--color-on-action`、`--color-accent`、`--color-accent-hover`、`--color-on-accent`、`--color-focus` |
| 语义 | `--color-info/success/warning/danger` 与配套面色 `--surface-info/success/warning/danger` |
| 圆角 | `--radius-control`、`--radius-card`、`--radius-panel`、`--radius-pill` |
| 阴影 | `--shadow-card-hover`、`--shadow-float`、`--shadow-overlay` |
| 字体 | `--font-sans`（正文/UI）、`--font-domain`（命理术语、盘面等古典语境） |
| 字号 | `--font-size-meta/aux/label/body/emphasis/card/section/page/hero` |
| 行高 | `--line-height-ui`、`--line-height-body`、`--line-height-title` |
| 间距 | `--space-xs/sm/md/lg/xl/2xl/3xl`，页面留白 `--space-page-mobile/tablet/desktop/wide` |
| 容器宽 | `--container-page`、`--container-form`、`--container-prose`、`--container-chart` |
| 触达 | `--target-min`（44px，交互元素最小尺寸）、`--target-submit`（48px） |
| 层级 | `--z-sticky/nav/dropdown/overlay/modal/toast` |
| 动效 | `--duration-feedback/overlay/page`、`--ease-out`、`--ease-in` |

全局 base 层已经处理了元素默认值：`h1–h3`、`p`、`li`、`small`、链接、原生表单控件的外观、`:focus-visible` 焦点环、`::selection`，以及 `.sr-only`（唯一可以直接用的全局 class）和 `prefers-reduced-motion` 降级。裸写 `<h2>`、`<p>`、`<input>` 就已经在系统里了，不需要再补样式。

## 组件用法要点

- `Button`：`variant` 取 `primary | secondary | ghost | destructive | icon`。`variant="icon"` **必须**给 `aria-label`（缺了会抛错）。`loading` 自带 spinner；`asChild` 把样式套到子元素上（做链接按钮用 `<Button asChild><a href="…">…</a></Button>`）。
- `Field`：只接受**一个**控件子元素，自动接管 `id`、`aria-describedby`、`aria-invalid`、`required`。表单一律走 `Field`，不要手写 `<label>`。
- `Segmented` / `Tabs`：受控组件，必传 `value` + `onValueChange` + `aria-label`。`Tabs` 的 `items` 里每项自带 `panel`。
- `Dialog` / `Drawer`：受控 `open` + `onOpenChange`，且 `trigger` 是**必填**的（焦点关闭后要还给它）。`Drawer` 的 `side` 取 `bottom`（默认）或 `right`。
- `Status`：八种状态 `loading | empty | error | processing | success | unavailable | locked | unauthorized`，自带中文默认文案与图标，`title` / `description` 可覆写。缺省态、错误态、加载态一律用它，不要自己拼空状态。
- `Table`：`caption` 必填；可选开筛选（`filterLabel`）、多选（`selectable`）、分页（`pageSize`）、行详情（`onRowActivate`）、空态（`emptyState`）。排序由 `columns[].sortable` 打开。

真正的样式源在 `_ds/<folder>/styles.css` 及其 import 闭包，逐组件 API 见各自的 `.d.ts` 与 `.prompt.md`——拿不准时直接读这些文件。

## 一个惯用片段

```jsx
<section style={{
  display: "grid", gap: "var(--space-lg)",
  maxWidth: "var(--container-form)",
  padding: "var(--space-xl)",
  background: "var(--color-surface)",
  border: "1px solid var(--color-border)",
  borderRadius: "var(--radius-panel)",
}}>
  <h2>校正出生时刻</h2>
  <Field label="出生时刻" description="24 小时制，精确到分钟。" required>
    <input type="text" name="birth-time" defaultValue="07:35" />
  </Field>
  <Status state="success" title="已完成" description="时柱未跨界，定盘可用。" />
  <div style={{ display: "flex", gap: "var(--space-md)" }}>
    <Button variant="primary">保存并重排</Button>
    <Button variant="ghost">取消</Button>
  </div>
</section>
```

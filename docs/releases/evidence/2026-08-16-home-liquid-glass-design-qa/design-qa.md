# 首页液态玻璃动态原型 — Design QA

- 日期：2026-08-16
- 路由：`/`
- 参考图：`/Users/yuhanglin/.codex/generated_images/01a001f0-a20d-7b40-b1d3-46506ae0db07/exec-15b6d566-0665-43bb-aac2-eedea022b021.png`
- 实装截图：`/Volumes/Lexar/code/mingli_web/web/e2e/screenshots/audit-2026-08-16/home-liquid-prototype/1484/home.jpg`
- 同屏对照：`/Volumes/Lexar/code/mingli_web/web/e2e/screenshots/audit-2026-08-16/home-liquid-prototype/comparison/reference-left-implementation-right.jpg`（左参考，右实装）
- 动效证据：`/Volumes/Lexar/code/mingli_web/web/e2e/screenshots/audit-2026-08-16/home-liquid-prototype/motion-proof/home-motion-proof.gif`
- 视口：CSS viewport `1484 × 1060`；页面截图因浏览器滚动条占位为 `1473 × 1060`
- 像素密度：`1x`
- 页面状态：未登录；身份接口无有效结果时如实显示“身份未知”

## 可见对照结论

- 保留了参考图的暖宣纸底、水墨远山、左侧符箓、右下水滴涟漪、两行主标题、双 CTA、悬浮毛玻璃导航和首屏下沿快捷入口。
- 按用户确认，去掉了参考图左侧固定玻璃立柱；符箓改为独立图层缓慢漂移，水墨背景独立缓动。
- 右侧不再重复符箓，改为低干扰的水滴涟漪；主视觉焦点保持在标题和“开始排盘”。
- 实装额外保留真实产品证据数字与现有路由，不用虚构内容替代产品事实。
- 360、768、1024、1484 四档均无横向溢出；移动端标题允许三行，桌面和平板保持两行。

## 修正记录

1. 首次浏览器对照发现桌面标题被自身宽度拆成三行，已扩大正文列并在非手机断点锁定两行。
2. 1024 宽度发现标题与符箓发生重叠，已把平板断点覆盖到 `64rem`，正文列收至 `56%`，符箓收至 `40vw`；复拍后两者边界分离。
3. 验证滚动后顶部导航仍固定且内容条宽 `1100px` 居中；动效离屏后自动暂停。
4. 验证 `prefers-reduced-motion: reduce` 时水墨和符箓动画均为 `none`，且 `will-change` 回落为 `auto`。
5. 用户实测反馈动效不可见后，复现出负层级装饰画布被 `IntersectionObserver` 误判为离屏，约一两秒后动画会暂停；现改为观察真实占位的 Hero section。修复后持续观察 4 秒及录制 3.6 秒期间均保持 `data-active="true"`、`animation-play-state: running`。
6. 同时将水墨周期收至 28 秒，三层符箓分别使用 16、11、13 秒错相运动；两次浏览器取样间隔 2.2 秒时，所有图层的 transform/opacity 均发生可见变化。

## 剩余差异

- 参考图是静态概念图，实装按用户后续要求移除了左侧固定玻璃轨道，并增强了符箓的漂浮层次；这是有意差异。
- 浏览器截图显示鼠标指针和本地 Next.js 开发工具悬浮按钮；二者不属于页面 UI，生产构建不会出现开发工具按钮。

## 最终结果

passed

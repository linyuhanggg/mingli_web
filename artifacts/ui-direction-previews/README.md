# UI 方向预览（2026-08-16，v2 增加 C4）

- 入口：打开 `index.html`；原型 c1/c2/c3/c4.html 可拖宽度看响应式。
- PNG：每套 1440 / 768 / 360 三档，如 `c4-1440.png`。

## 四套方向
| 代号 | 方向 | 一句话 |
|---|---|---|
| C1 | 锐感数据工坊 | 数据 SaaS 锐感，风险低、辨识度低 |
| C2 | 纸上术数档案 | 古籍善本编辑部，最贴合“证据可核” |
| C3 | 星历精密仪器 | 天文台终端，最大胆 |
| C4 | 液体玻璃（新） | iOS 风格悬浮玻璃，最“高级感” |

## C4 配方来源（均为 MIT）
- einui/einui：Tailwind/Radix 玻璃组件配方（bg-white/10、backdrop-blur-xl、border-white/20、from-white/20 顶部高光、inset 高光、0_8px_32px 阴影）
- iyinchao/liquid-glass-studio（595★）：WebGL2/WebGPU 高保真引擎（折射/色散/菲涅尔/超椭圆/Spring），正式落地高保真盘面玻璃候选
- dashersw/liquid-glass-js（688★）：WebGL 玻璃形状库（圆角矩形/胶囊、嵌套玻璃采样）
- 其他参考：themesberg/glass-ui、sdegenaar/liquid_glass_widgets（Flutter）

## 落地时的技术注意
1. 苹果官方液体玻璃只有 SwiftUI 实现；Web 为 backdrop-filter 近似，需标注“近似，非 Apple 官方”。
2. 玻璃要有彩色渐变/光斑背景才成立；我们给 C4 配了 iOS 风浅色光斑场景。
3. backdrop-filter 性能成本高：卡片数量 ≤ 2 层、hover 不额外叠加 blur（本次卡片均单层 + 白色高光渐变）。
4. 无 backdrop-filter / 用户开启减少透明时自动回退实体面板；落库后按 `prefers-reduced-transparency` 与 `@supports` 双保险实现。

## 预检
9 组（C4 三档）+ 原 C1-C3 九组全部通过：无横向溢出、导航单行、CTA 首屏内、primary CTA 对比度 ≥5.7:1、零 em-dash。

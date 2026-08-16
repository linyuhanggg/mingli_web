# GitHub 对当前项目可能有帮助的 UI / 架构仓库（2026-08-16 调研）

> 调研方式：agent-reach / GitHub API（stars/license）。都还未改动源码，仅作选型材料。

## 一、UI 组件与设计系统（优先）
| 仓库 | Stars | License | 对项目的价值 |
|---|---|---|---|
| [shadcn/ui](https://github.com/shadcn-ui/ui) | 121k | MIT | 复制粘贴式组件注册表，最适合解决 web/admin 双份组件库漂移；可搭 einui 玻璃组件 |
| [radix-ui/primitives](https://github.com/radix-ui/primitives) | 19.2k | MIT | 无头可访问组件（弹层/菜单/命令面板），项目已部分在用 |
| [radix-ui/themes](https://github.com/radix-ui/themes) | 8.6k | MIT | 如果未来不想自己维护全部视觉，可直接上 Radix 主题系统 |
| [heroui-inc/heroui](https://github.com/heroui-inc/heroui) | 30.4k | Apache-2.0 | 现代 React UI 库（前 NextUI），表单/表格/深色/玻璃质感强，适合产品界面 |
| [mantinedev/mantine](https://github.com/mantinedev/mantine) | 31.6k | MIT | 全家桶（表单/日期/表格/通知），对八字 12 字段表单与 admin 很有用；但引入较大 |
| [mui/base-ui](https://github.com/mui/base-ui) | 10.6k | MIT | 无头可访问组件（Radix 团队新家），想要完全自管视觉时选它 |
| [tanstack/table](https://github.com/TanStack/table) | 28.3k | MIT | 无头表格/数据网格，适合证据索引、admin 数据管理 |
| [motion](https://github.com/motiondivision/motion) | 33.3k | MIT | Apple 式 spring/jelly 动效，液体玻璃方向的高质量过渡引擎 |
| [einui/einui](https://github.com/einui/einui) | 136 | MIT | 现成 Tailwind/Radix 液体玻璃组件，C4 配方的来源 |

## 二、架构与项目组织（优先）
| 仓库 | Stars | License | 对项目的价值 |
|---|---|---|---|
| [alan2207/bulletproof-react](https://github.com/alan2207/bulletproof-react) | 35.7k | MIT | 生产级 React 架构模式：feature-based、API 层、guard、测试策略，直接对治“上帝组件/代码堆积” |
| [shadcn-ui/taxonomy](https://github.com/shadcn-ui/taxonomy) | 19.3k | MIT | Next.js App Router + 认证 + 订阅 + 内容目录的规范示例，适合当本站/后台骨架参考 |
| [refinedev/refine](https://github.com/refinedev/refine) | 35.5k | MIT | React 管理后台/内部工具框架：CRUD、认证、审计、RBAC；未来 admin 复杂化可重构成它 |
| [Kiranism/next-shadcn-dashboard-starter](https://github.com/Kiranism/next-shadcn-dashboard-starter) | 6.8k | MIT | Next.js + shadcn 的 admin 后台模板，表格/表单/auth/billing 都齐，适合对照 admin 改造 |
| [feature-sliced/skills](https://github.com/feature-sliced/skills) | 80 | ? | FSD 方法论 AI skill，适合把大路由拆成 feature 切片（比直接搬模板轻） |
| [TanStack/query](https://github.com/TanStack/query) | 50.1k | MIT | 服务端状态/缓存/重试，替代页面里手写 fetch/useEffect，对 API 层帮助大 |

## 三、不推荐现在就引入（记录原因）
- **react-admin**（26.9k）：基于 MUI 的重框架，和当前 Next.js App Router/自研 token 体系冲突大，适合“从零做后台”而非“重构现有”。
- **tRPC**（40.5k）：如果后端是 Python（当前仓库看起来是），端到端类型安全收益接不上；除非后端计划换 TS 栈再考虑。
- **Mantine / Refine**：价值高但不是必需品；先做组件注册表和 feature 重构，能覆盖 80% 问题，且不引入框架锁定。

## 四、建议组合（按投入从小到大）
1. **低配**：shadcn/ui（只抄需要的组件）+ Radix + TanStack Query/Table + Motion
2. **中配**：低配 + Bulletproof-React 风格 feature 目录 + next-shadcn-dashboard-starter 当 admin 参照
3. **高配**：中配 + einui 玻璃组件（或 liquid-glass-studio 做盘面真玻璃）+ Mantine 表单体验

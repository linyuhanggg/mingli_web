# 八字盘面工作区与档案入口

记录日期：2026-08-11（Asia/Shanghai）

状态：**代码已进入 main / 依赖真实 Runtime+模型联调环境验证 / production blocked / real traffic disabled**

## 固定代码

- 功能提交：`6f77658`（`feat(web): ship bazi chart workspace and archive entry points`）
- 热修提交：`3446061`（`fix(web): send career dimension for free bazi preview`）
- 当前 HEAD：`3446061`

## 本版改动

- 新增 `/app/bazi` 八字工作区入口与 `bazi-flow`
- 档案页补齐继续解读/预览入口
- 结果页强化八字盘面、事实面板与阅读展示
- 免费八字 preview 默认携带 `career` 维度，对齐 preview Guard 必需范围

## 边界

- 本记录只证明前端产品入口和展示层推进，不替代 Task 13 staging 全轨迹
- 真实计算与成稿仍依赖服务器 Runtime / 模型配置；仓库默认仍可回退 Fake
- 不开放支付、不宣称正式上线

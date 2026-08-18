# 八字已保存档案复用修复证据

日期：2026-08-19

状态：证据就绪，待用户验收

## 用户问题与根因

登录用户已经确认过出生资料并生成 `ProfileVersion`，但再次进入 `/bazi` 等出生类产品页时，页面仍只提供空白出生表单。提交逻辑也总是走 `createProfileDraft` → `confirmProfileDraft`，因此用户必须重复录入，并会产生不必要的新档案版本。

## 修复

- 出生类产品页进入后读取当前 owner 的 `GET /api/v1/profiles`，默认选择最近返回的已确认档案；带有效 `?profile=` 时优先使用该版本。
- 选中已有档案时隐藏出生资料表单，提交直接使用该 `profile_version_id`，不调用档案草稿或确认接口。
- 只有用户明确选择「重新录入并建立新档案」时，才恢复原出生表单与建档路径。
- 资料读取中禁止提前提交；读取失败时保留重试和重新录入两条可达路径。
- 使用原生、带可见标签的 `select`，并验证键盘聚焦与 `Home` 操作。
- `useSearchParams` 放入共享 `Suspense` 边界，保证所有静态产品路由可以通过 production build。

## 自动化与浏览器证据

定向组件合同：`web/src/test/product-route-contract.test.tsx`，`11 passed`。新增回归断言已保存档案被默认选择、出生年份控件不存在、预览请求携带既有版本 ID，且不发生 profile draft/confirm 写入。

系统 Chrome + production build，受控的「已登录且有一个已确认档案」API 状态：

- 360：[`saved-profile-selected.png`](../../../../artifacts/browser-evidence/2026-08-19-bazi-saved-profile-reuse/360/saved-profile-selected.png)
- 768：[`saved-profile-selected.png`](../../../../artifacts/browser-evidence/2026-08-19-bazi-saved-profile-reuse/768/saved-profile-selected.png)
- 1024：[`saved-profile-selected.png`](../../../../artifacts/browser-evidence/2026-08-19-bazi-saved-profile-reuse/1024/saved-profile-selected.png)
- 1440：[`saved-profile-selected.png`](../../../../artifacts/browser-evidence/2026-08-19-bazi-saved-profile-reuse/1440/saved-profile-selected.png)

`bazi-saved-profile-reuse.spec.ts` 与既有 `bazi-deep-authority.spec.ts` 合跑四视口，实测 `8 passed`。每档均验证页面级横向溢出为 `0`、已有档案选择器可键盘到达、提交复用既有版本、没有新建档案请求；无档案的新建流程与深读支付 fail-closed 路径仍通过。

这里的登录态与档案响应是受控 API 状态，只用于稳定复现本次回归，不计入 R5 阶段 Q 的正常路由通过项，也不冒充用户验收。

## 完整门禁

当次 `make check` 退出码为 `0`：

- Backend：`1066 passed / 132 skipped`
- Ruff：通过
- mypy：`147 source files` 无错误
- Web：`82 files / 519 passed`
- Admin：`33 files / 123 passed`
- Web/Admin lint、typecheck、production build：全部通过

未 push、未上传测试机、未部署。用户仍需在自己的真实登录账户下确认档案是否正确默认选中，以及提交后的盘面是否对应所选档案。

# Assessment B — 浏览器/检测器确定性证据（独立取证）

> 角色：Assessment B 证据子代理。只为 mingli_web 收集确定性证据，不做设计点评（设计结论归 Assessment A）。
> 纪律：只读源码；仅写本目录与 /tmp；无 git 操作。后端未运行，私有页按降级态记录。
> 取证时间：2026-08-16 17:14–17:22。环境：web http://127.0.0.1:3000（200）、admin http://127.0.0.1:3001（200），均未重启/未新建。

---

## 0. 结论速览

| 维度 | 结果 |
|---|---|
| 检测器（静态） | **0 findings，exit 0（干净）**，无超时、无需拆分扫描 |
| 页面可用性 | 94 页全部 HTTP 200，无路由 404/500，无 >30s 挂起（max 2.4s） |
| JS 运行时异常 | **pageerror 全站 0**，console warning 全站 0 |
| console error | 250 条 = 248 条「API 500」+ 2 条「favicon 404」，去重后仅 2 类文本 |
| 失败请求 | 248 条，**100% 为 /api/v1/* → HTTP 500**（后端未运行的预期降级） |
| 旧品牌关键词 | 温象牙/象牙/星轨/深墨绿/金色/FateRadar 等：**0 命中**（含 bodyText 独立复核） |
| overlay（检测器叠加） | 跳过（本会话无浏览器注入通道；live-server.mjs 事实核查见 §4） |

---

## 1. 检测器（确定性扫描，任务 A）

执行：

```bash
timeout 300 node /Users/yuhanglin/.agents/skills/impeccable/scripts/detect.mjs --json web/src \
  > artifacts/ui-diagnosis-20260816/detector.json 2>/tmp/diag-b-detector-stderr.log
```

- 退出码：**0**（0=干净；2=有 finding 亦属正常，本次为 0）
- stderr：空
- 原始 JSON 已按原样保留于 `detector.json`（内容 `[]`，0 findings，无需截断）
- 在 300s 超时内完成（多次运行均 < 数分钟），**未触发**拆分扫描

**finding 总数：0**（规则 x 文件 Top 列表：无，无 finding 可列）

### 1.1 扫描覆盖复核（避免"静默空跑"假干净）

用 find/wc 独立统计 + 用检测器自身 walkDir/shouldIgnoreDetectionFile 复算，两者一致：

| 口径 | 文件数 |
|---|---|
| `find web/src -type f`（独立复核） | **330** = tsx 221 + css 60 + ts 49 |
| 检测器 `walkDir(web/src)` 枚举 | **330** |
| 经 `shouldIgnoreDetectionFile` 过滤后实际进入扫描 | **330（0 忽略）** |

即：330 个文件全部被扫描，`[]` 不是路径没进或文件被忽略的结果。

### 1.2 阳性对照（验证检测器本身能查出问题）

对含刻意反模式样本的 /tmp 文件扫描，命中正常，证实 `[]` 非检测器失灵：

- `diag-b-ctrl.tsx` → **5 findings**：side-tab×1、gradient-text×1、ai-color-palette×2、bounce-easing×1
- `diag-b-ctrl.css` → **1 finding**：side-tab×1

### 1.3 范围限制（如实记录）

- 本次为**静态/正则引擎**扫描（文件级，TSX/CSS/TS）；部分规则（如真实渲染对比度、布局计算）属浏览器引擎，需对 URL 扫描（detector 对 web 目录检测到 dev server 时也仅提示"URL 扫更准"）。
- 未并行跑 URL 级浏览器检测（不干扰主会话捕证），如需可补 `detect.mjs http://127.0.0.1:3000`。

---

## 2. 浏览器证据矩阵（任务 B，数据来自主会话 browser-evidence.json/md，94 页 = 23 路由 × 4 视口）

视口档：1440x900 / 1024x768 / 768x1024 / 360x800。表内「错误/失败」为该路由 4 档的取值范围；除标注外 4 档一致。

| 路由 | 状态 | console 错误 | 失败请求 | pageerror | 旧品牌词命中 |
|---|---|---|---|---|---|
| / (home) | 200 | 4–5（仅@1440为5） | 4 | 0 | 0 |
| /bazi | 200 | 2 | 2 | 0 | 0 |
| /ziwei | 200 | 2 | 2 | 0 | 0 |
| /qizheng | 200 | 2 | 2 | 0 | 0 |
| /daliuren | 200 | 2 | 2 | 0 | 0 |
| /liuyao | 200 | 2 | 2 | 0 | 0 |
| /qimen | 200 | 2 | 2 | 0 | 0 |
| /tools | 200 | 4 | 4 | 0 | 0 |
| /tools/time-check | 200 | 3 | 3 | 0 | 0 |
| /pricing | 200 | 2 | 2 | 0 | 0 |
| /about | 200 | 4 | 4 | 0 | 0 |
| /library | 200 | 4 | 4 | 0 | 0 |
| /daily | 200 | 4 | 4 | 0 | 0 |
| admin /login (3001) | 200 | 0–1（仅@1440为1，为favicon 404） | 0 | 0 | 0 |

主会话额外覆盖（同 4 视口，均 200）：/meihua、/wenshi、/hecan、/jianxiang、/account、/arts、/methodology、/tools/chart-similarity、/tools/five-elements、/tools/rhythm。

失败请求明细（按独有端点聚合）：

| 端点 | 出现次数 | 命中页面 |
|---|---|---|
| /api/v1/account | 184 | 全部 23 个站点路由（每路由 4 视口 × 每页 2 次） |
| /api/v1/guest-sessions | 16 | 仅 4 个工具子页：time-check / chart-similarity / five-elements / rhythm |
| /api/v1/content?prefix=notice | 8 | 仅 / |
| /api/v1/content?prefix=tools. | 8 | 仅 /tools |
| /api/v1/content/daily | 8 | 仅 /daily |
| /api/v1/content?prefix=library. | 8 | 仅 /library |
| /api/v1/content/page.about | 8 | 仅 /about |
| /api/v1/content/page.methodology | 8 | 仅 /methodology |

**所有失败请求均为 HTTP 500，全部来自 /api/v1/\*，无任何静态资源（/_next、css、js、图片）失败。**

---

## 3. 最值得看的 10 条控制台/网络证据（按重要度）

1. **全站统一根因：后端未运行 → 8 个 /api/v1/* 端点全 500，累计 248 条失败**。不是前端缺陷，但当前降级态下是唯一的错误来源，也是 console 噪音的全部。
2. **/api/v1/account 每页、每次加载都拉 2 次**（184 = 23 路由 × 4 视口 × 2）：静态页（pricing/about/arts/account）也发。与 Next dev StrictMode 双调用特征一致（见 §5 假阳性），但值得在后端恢复后复核是否重复。
3. **/api/v1/guest-sessions 仅 4 个工具计算页发起**：time-check/chart-similarity/five-elements/rhythm——降级态下工具计算类功能必然不可用，且这类页的"3 条 500 错误"结构为 account×2 + guest-sessions×1。
4. **首页公告区数据缺失**：/api/v1/content?prefix=notice 500，主页@1440 是全站 console 错误最多的单页（5）。
5. **/tools 工具目录内容缺失**：/api/v1/content?prefix=tools. 500（工具列表依赖后端内容，目录可能渲染为空壳）。
6. **/daily 每日内容缺失**：/api/v1/content/daily 500。
7. **/library 知识内容列表缺失**：/api/v1/content?prefix=library. 500。
8. **/about 与 /methodology 正文走后端直连**：page.about / page.methodology 500——后端恢复前这两类内容页无正文。
9. **favicon 404 ×2**（home@1440、admin-login@1440）：`web/public/` 仅 sw.js，全站无任何图标文件，HTML 无 `<link rel="icon">`，浏览器默认请求 /favicon.ico → 404。cosmetic，非故障。
10. **健康面证据（同样值得记录）**：pageerror 0、console warning 0、94 页全 200、最大加载 2,418ms（meihua@1440），无任何 >30s 挂起；`document.title` 每页均有业务语义（如「八字｜命理工具」）；旧品牌关键词 0 命中——渲染层无 JS 崩溃、无残留旧视觉文案。

---

## 4. overlay（任务 C）——如实记录：跳过

- 本会话**未运行** impeccable overlay：无原生浏览器注入通道，Playwright 浏览器捕证由主会话统一执行，未并行开第二条浏览器链路，因此**未声称有任何 overlay 证据/结果**。
- 事实核查（与任务指令括号中"脚本不存在"的表述不同，如实记录）：`/Users/yuhanglin/.agents/skills/impeccable/scripts/live-server.mjs` **存在**（68KB），其文档明示服务 `/detect.js`（"Detection overlay"）端点。若后续需要 overlay 捕获，可在不干扰主会话捕证的前提下以独立端口启动并 addScriptTag 注入；本次未执行、未发明替代方案。

---

## 5. 可能假阳性 / 需谨慎解读处

1. **248 条 500 均为后端未运行的预期降级**（任务简报与工作记忆均已知后端不在线）：据此**不能**下"前端 API 层有缺陷"的结论；但可作为后端恢复后的回归基线。
2. **"每页 2 次重复请求"**：与 Next.js dev 模式 StrictMode 双调用 React effect 特征一致，生产构建未必复现——标注为待复核，不作缺陷定论。
3. **favicon 404**：浏览器缺省请求行为 + 项目未设自定义图标，界面无关，属 cosmetic（可能是有意如此，未下结论）。
4. **console 错误文本去重后仅 2 类**（"Failed to load resource: 500" ×248、"… 404" ×2）：任何"按消息文本计 250 种错误"的误读都应避免。
5. **检测器 0 finding 的边界**：仅静态引擎覆盖范围；且本仓库可能带 impeccable 内联豁免（`impeccable-disable*`），未逐条审计豁免理由（如需可另查）。
6. **旧品牌词 0 命中基于渲染后 bodyText**：视觉残留若只存在于 CSS（颜色 token 名、未引用的 class）不会被 bodyText 捕获；CSS 级残留需另做源码 grep，超出本次浏览器证据范围（提示给结构盘点，非本文结论）。

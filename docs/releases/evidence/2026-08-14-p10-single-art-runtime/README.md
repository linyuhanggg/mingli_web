# P10 单术 Runtime → Reading → ViewModel 技术切片

日期：2026-08-14（Asia/Shanghai）  
环境：本机 macOS；专用 `mingli-master` Runtime venv；合成 fixture，不含真实个人资料  
状态：技术切片通过；P10-001/002/003/006/007/008/012 仍保持 `IN_PROGRESS`

## 已接入的六类单术

| 术数 | Runtime capability | 创建动作 | ViewModel | Runtime 合成 probe |
|---|---|---|---|---:|
| 八字 | `bazi` | `profile_preview` | `bazi-chart/v1` | 23 facts |
| 紫微 | `ziwei` | `ziwei_preview` | `ziwei-chart/v1` | 30 facts |
| 七政 | `xingming` | `qizheng_preview` | `qizheng-chart/v1` | 21 facts |
| 六爻 | `liuyao` | `liuyao_one_question` | `liuyao-chart/v1` | 28 facts |
| 奇门 | `qimen` | `qimen_one_question` | `qimen-chart/v1` | 24 facts |
| 大六壬 | `liuren` | `liuren_one_question` | `daliuren-chart/v1` | 18 facts |

每一类都经过 `describe → prepare`，并由后端严格投影到对应 ViewModel。投影器只读取 Runtime 的计算事实，跳过 `/input/` 事实；浏览器只展示 ViewModel，不重新排盘。七政要求确认经纬度和坐标来源；奇门、大六壬要求事件时区和地点；命盘类先建立不可变 ProfileVersion，再创建 Reading。

## HTTP / Web 接线

- 新增 `POST /api/v1/readings/ziwei`、`/qizheng`、`/qimen`、`/daliuren`。
- Web API 客户端使用同一套 Guest Session、CSRF 和 Idempotency-Key。
- `/ziwei`、`/qizheng`、`/qimen`、`/daliuren` 产品任务页已从占位工作台进入私有 Reading 结果页；`/bazi`、`/liuyao` 也复用同一接线。
- 私有结果页按 `schema_version` 渲染紫微十二宫、七政星体/宫头、六爻六线、奇门九宫、六壬四课三传；中宫缺失字段保留为 `null`，不伪造盘面事实。
- OpenAPI 冻结合同已同步，结果页的盘面/事实/依据编号不会重复。

## 回归

```text
backend 新术数 API + compiler + projector + OpenAPI 定向：91 passed；相术 projector 定向：8 passed
web 新任务入口、产品路由、API 客户端、结果页定向：45 passed
backend ruff：PASS
backend mypy（readings/charts/readings API）：PASS
web typecheck + eslint：PASS

本轮完成后的全仓回归：Backend `754 passed, 92 skipped`；Backend Ruff、mypy（132 source files）通过；Web `68 files / 433 tests`、lint、typecheck、production build 通过；Admin `33 files / 121 tests`、lint、typecheck、production build 通过。
```

## 本地浏览器冒烟（自动化，不替代用户批准）

在当前工作树启动本机 Web 服务后，逐一访问 `/bazi`、`/ziwei`、`/qizheng`、`/liuyao`、`/qimen`、`/daliuren`。六个页面均出现各自的输入表单、`确定性盘面已接入` 状态和 Runtime 提交说明。按 360×800、768×900、1024×900、1440×1000 四档视口共检查 24 个组合：横向溢出 0，运行态缺失 0，时区/地点字段缺失 0；360px 窄屏的 `scrollWidth` 为 349px，未超过视口。该结果只证明当前页面结构和响应式边界可用，不证明后端真实 Worker 已完成，也不替代用户逐页浏览批准。

## 结构化相术投影（不含媒体适配）

本轮用无个人资料、无原始图片的合成结构化观察调用专用 Runtime `describe → prepare`。Runtime 返回了可见观察、缺失目标、冲突、来源比较和不确定性事实；后端新增严格 `physiognomy-view/v1` 投影，过滤 `/input/` 事实与媒体/来源私有字段，结果页增加中性观察表格。这个证据只推进 P10-012 的 Provider/ViewModel 接线；P10-011 的图片/掌纹/姿态媒体入口、质量门禁、授权审计，以及四模式真实产品链路仍未完成。

## 未完成边界

Runtime manifest 还包含风水、禄命/纳音、梅花、相法、择日、太乙六项能力，以及日运既有链路。相法现在已有结构化 Provider probe、严格 ViewModel 投影和中性渲染起点；随后 P10-013B 又把风水、禄命/纳音、择日、太乙、相法的 manifest 对齐 compiler、真实 Runtime prepare 和严格 projector 补齐，但它们仍没有媒体 Adapter、公开产品入口和完整黄金样例。紫微/七政合盘、三术合参、问事合参、多盘问答、深读/导出也不能因单术盘面可见而提前标记完成。

本证据不替代四视口真实浏览器验收和用户批准，也不替代 Mac mini native-full、生产 Runtime、真实支付、凭据、备份恢复、告警容量、合规及公开上线门禁。

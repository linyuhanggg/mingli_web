# mingli_web Codex Agent 模型路由报告

更新日期：2026-08-20（Asia/Shanghai）

## 结论

这次复核不再按“岗位名字听起来像什么”分模型，而是同时参考：

- Codex Radar 的 DeepSWE 软件工程实测；
- Codex Radar 的庞贝壁画邻接恢复视觉推理实测；
- 每个岗位的歧义、耦合、验证方式、错误后果和运行频率；
- 用户明确要求：全部保持 Standard，不开启 Fast mode。

最终分配如下：

| Agent | 原配置 | 新配置 | 判断 |
| --- | --- | --- | --- |
| 项目经理（当前主任务） | 继承当前选择 | Sol / high | 跨岗位拆单、裁决和验收耦合高；固定日常开发强档，避免无意继承到更耗额度的 max |
| `execution_producer` | Luna / low | Luna / high | 协调虽然不写代码，但漏报阻塞或错收口会影响整批；使用 Radar 的低成本自动化强档 |
| `frontend_developer` | Sol / medium | Sol / medium | 项目经理已把任务拆成有边界的前端实现，medium 足够；复杂 UI 方向由强 UI/UX 岗位先收敛 |
| `backend_developer` | Sol / medium | Sol / medium | 有明确 API/服务边界和测试，属于 bounded complex，不需要每次 high |
| `core_algorithm_developer` | Sol / high | Sol / high | 算法、独立 Git 工作树和运行时合同耦合高，错误后果高 |
| `ui_designer` | Terra / medium | Sol / high | 需要挑战现状、综合视觉证据与用户问题；是高歧义、判断型任务 |
| `test_engineer` | Terra / high | Luna / high | 技术测试有明确验收和确定性工具；Radar 中 Luna/high 比原 Terra/high 更合适，且成本低很多 |
| `user_tester` | Luna / medium | Sol / high | 现在是 UI/UX 独立质量门和返工触发器，判断质量比省一次测试额度更重要 |
| `project_assistant` | Luna / low | Luna / medium | 机械查询保留低成本模型，但移除当前表现过弱的 low 档 |

没有自动选择 `ultra`，也没有把全部岗位堆到 `max`。这些档位在榜单里更强，但延迟、步骤和额度明显增大，不适合每次日常派单。

## Codex Radar 证据

数据来源：

- [分布式雷达主站](https://deng.codexradar.com/)
- [DeepSWE 当前模型矩阵](https://api.codexradar.com/)
- [DeepSWE 智能/效率数据](https://api.codexradar.com/api/v1/intelligence-efficiency?v=20260815-equal-iq-v2&benchmark=deep-swe)
- [DeepSWE 当前推荐](https://api.codexradar.com/api/v1/radar-insights?v=20260815-equal-iq-v2&benchmark=deep-swe)
- [视觉推理当前推荐](https://api.codexradar.com/api/v1/radar-insights?v=20260815-equal-iq-v2&benchmark=pompeii-adjacency)

### DeepSWE 快照

抓取时间约为 2026-08-20 20:16（北京时间），`equal_latest_3` 数据累计约 34,766 次运行。与本次分配直接相关的点：

| 模型/effort | IQ | 平均 API 等价成本 | 平均时间 |
| --- | ---: | ---: | ---: |
| Sol / medium | 87.05 | $3.47 | 17.41 分钟 |
| Sol / high | 90.62 | $4.37 | 19.73 分钟 |
| Terra / high | 72.77 | $1.07 | 13.20 分钟 |
| Luna / low | 6.25 | $0.03 | 6.89 分钟 |
| Luna / medium | 33.48 | $0.09 | 10.66 分钟 |
| Luna / high | 79.02 | $0.20 | 17.68 分钟 |
| Luna / xhigh | 86.16 | $0.32 | 24.00 分钟 |

站点的当前“日常开发”推荐包含 Sol/high；“后台自动化”推荐 Luna/high 和 Luna/xhigh。这支持保留 Sol/medium 处理已拆清的前后端任务，把关键判断提升到 Sol/high，并把低成本确定性工作放到 Luna/high。

### 视觉推理快照

庞贝壁画频道不是 UI 审美测试，但比纯编码题更接近页面观察、图像关系和视觉证据理解。2026-08-20 20:19（北京时间）的当前推荐中：

- 日常高质量档首选 Sol/high，IQ 约 99.46，86 个样本；
- 同组还推荐 Sol/xhigh，IQ 约 97.22；
- 低成本自动化首选 Luna/high，IQ 约 81.08。

因此项目经理、UI 设计师和用户测试使用 Sol/high；执行制作和确定性技术测试使用 Luna/high。没有使用 xhigh，是因为 Sol/high 已达到关键判断需要，而 xhigh 会增加运行时间和额度。

## UI/UX 路由改变

`DESIGN.md` 不再是视觉验收权威。它仍要读，因为里面包含历史决策、页面状态和技术约束；但真实浏览器证据、用户当前目标、用户测试 finding 和项目经理接受的 UI 设计交接优先。

新闭环：

```text
user_tester 发现并记录用户问题
  → ui_designer 把 finding 转成 UI_UX_HANDOFF
  → frontend_developer 作为唯一写 Owner 实现
  → test_engineer 做技术回归
  → 原 user_tester 用同一旅程复测
  → PASS 后项目经理才关单
```

用户测试不直接设计 CSS，UI 设计师不直接写代码，前端开发不自行推翻验收问题。这样每个岗位仍然只做自己的事，同时让用户反馈真正改变 UI/UX。

## 局限

- DeepSWE 测软件工程，庞贝频道测视觉邻接；两者都不是完整的审美、产品策略或可用性基准。UI/UX 模型分配是“实测能力先验 + 岗位风险”的判断，不是假装网站直接测过本项目页面。
- 页面展示的美元是统一比较用的 API 等价成本，不等于用户订阅实际扣费；本项目只用它比较相对消耗。
- 雷达数据会变化。本报告是日期化快照，不让 Agent 在每次派单时联网自动换模型，避免配置随短期波动失控。
- 所有岗位继续使用 `service_tier = "default"` 和 `fast_mode = false`；模型 reasoning 提升不等于开启 Fast mode。

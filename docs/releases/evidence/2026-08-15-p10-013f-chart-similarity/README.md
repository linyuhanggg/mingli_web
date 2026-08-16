# P10-013F 八字同盘四柱事实比较

## 本次完成

- 新增 `chart_similarity_preview` 输入合同：只接受两份不同的已确认 `ProfileVersion`，固定绑定八字 Runtime 和 `state` 维度。
- 新增 `chart-similarity-view/v1`：逐柱比较 Runtime 已计算的年、月、日、时四柱原值，保留两条 calculated fact ref。
- 明确不输出相似度百分比、合婚、缘分、性格相似度或现实决定。
- Web `/tools/chart-similarity` 已从只读占位入口改为选择两份确认档案并启动真实 API 任务；结果页显示逐柱比较表。
- `reading-document-v1` JSON Schema、前端 ViewModel Registry、Runtime Chart、导出产品标签和 OpenAPI 均已同步。

## 验证

- Backend 同盘算法、编译器、投影、API、Fake Worker 和文档合同定向回归通过。
- 冻结 Runtime opt-in 回归使用合成档案，真实跑通 `Prepared → calculated/bazi/four_pillars → Accepted → typed ReadingDocumentV1`。
- Web 流程验证了两份档案选择、重复档案拒绝、幂等键和 `/api/v1/readings/chart-similarity` 路由。
- 本证据不包含个人出生资料、姓名、密码、邮箱凭据、API key 或其他秘密。

## 边界

这仍是“八字四柱原值比较”切片，不是合婚算法，也不是通用相似度模型。寻时定盘、解梦和姓名分析仍没有足够的规则包、黄金样例和正式 Provider，继续保持不可用；五行仍是事实/调候边界，不宣称旺衰、喜忌或用神完成。测试服务器发布和用户逐页浏览批准另行记录。

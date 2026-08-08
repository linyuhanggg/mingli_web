# mingli_web

当前权威方向是：**先做响应式网站，后做原生 iOS App，共用同一套账户、商品、权益和命理解读后端。**

- 产品方向：[docs/PRODUCT_DIRECTION.md](./docs/PRODUCT_DIRECTION.md)
- 商业化与技术蓝图：[docs/PRODUCT_BLUEPRINT_WEB_IOS_V2.md](./docs/PRODUCT_BLUEPRINT_WEB_IOS_V2.md)
- Metis 参考审计：[docs/METIS_REFERENCE_AUDIT_2026-08-09.md](./docs/METIS_REFERENCE_AUDIT_2026-08-09.md)
- 共同语言：[CONTEXT.md](./CONTEXT.md)
- 架构决策：[docs/adr](./docs/adr)

仓库根目录现有 app.js、app.json、pages 等文件是早期小程序骨架，只保留作历史参考，不是新版网站的实现起点。后续网站代码应按新版蓝图建立独立的 Web、API、Worker 和共享领域模块；在迁移确认前不删除旧文件。

Metis紫薇及其开源仓库只作为 UI、排盘交互和公开支付路径的参考。不得复制其品牌资产；其账户、会员、支付和后端 API 未开源，不能被当作本项目的现成后台。

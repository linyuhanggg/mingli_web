---
status: accepted
---

# 成稿校验发生在 complete 之前

模型候选稿必须先通过商品结构、事实引用、隐私和平台内容安全合同，合格后才提交 mingli-master complete。核心一旦返回 Accepted，后端原样保存和交付该正文，不再做第二次改写、截断或命理正确性判断；这同时守住平台安全和核心“首次提交胜出”的事务语义。

## Consequences

修复重写、备用模型和模板降级只能发生在 Accepted 之前，且始终复用同一 Fact Brief，不能重新起盘。Accepted 后的展示问题只能通过新的 Reading Version 纠正，不能覆盖旧正文。

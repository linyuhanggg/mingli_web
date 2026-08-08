---
status: accepted
---

# 档案与解读全部不可变版本化

出生资料、事实简报和已接纳正文都不允许覆盖更新：修改出生资料产生新的 Profile Version，追问或表达纠正产生新的 Reading Version，新的卦象或问题范围产生新的 Reading Root。此选择牺牲了简单 CRUD，换来可复现、可退款审计和不会被用户反馈悄悄改盘的结果。

## Consequences

每份商品绑定明确的 Purchase Target。核对反馈独立保存；删除账号时可以按隐私规则清除用户可识别数据，但退款和审计所需的最小财务记录按法定义务单独保留。

# Section Map Compatibility Note

旧版 `section-map.md` 用短裸标题正则把全文切成 261 个片段，并把每个片段标为 `done`。该数字只能表示机器切片，不能表示 261 节已经语义蒸馏或校勘，因此旧表已撤销。

当前权威结构入口是：

- `chapter-map.md`：normalized 十二容器、Kanripo/WYG 十二卷及交叉映射。
- `quote-index.md`：精确短引和 normalized 行号。
- `rules.md`：通过来源、前置条件、执行、停止与 adapter 字段门的选择性规则卡。
- `validation.md`：真实覆盖与未完成项。

兼容调用方若请求 `section-map.md`，应转读 `chapter-map.md`，不得恢复或引用“261/261 done”。

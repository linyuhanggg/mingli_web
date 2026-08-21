# validation: 命理约言

## D2 状态

- normalized_source: ready
- chapter_units: 49
- chapter-map coverage: 49/49 done
- quote-index: 49 条短引，均从 `fulltext.md` 抽取
- raw_html_pages: 49 篇正文 + 2 个目录页
- scan_anchor_status: downloaded 4471099 bytes

## 版本边界

本 pack 按“精选/通行四卷本”入库。Wikimedia/NLC PDF 文件名为《精选命理约言》，共 185 页；算准网目录为序 + 卷一/卷二/卷三/卷四 49 篇。后续若取得清刻全本或其他抄本，应新增校勘层，不直接覆盖本文件。

## 风险

- 算准网 HTML 属整理文本，存在错字、断句与现代录入误差。
- PDF 为影印锚点但本轮未逐页 OCR 校对。
- 生成 skill 时必须保留 `version_scope=精选/通行四卷本`。

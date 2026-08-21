# 奇门遁甲统宗大全 — Validation

## Local Source Checks

- raw_extract: `sources/raw/san-shi/qimen-dunjia-tongzhi/taiyi/taiyi-qimen-tongzong-daquan_extracted.md`
- normalized_fulltext: `references/fulltext/san-shi/qimen-dunjia-tongzhi/fulltext.md`
- sections_extracted: 9
- total_blocks: 736
- raw_sha256: `0c4e5947f43404cca6fc2ae7747c7148a8e0fcacc4a21b9c09206cc6728a4f34`
- normalized_sha256: `f4feb5c389f0ac8bc8dfd0d3f011b088576bc5510248e8d8663e01e2d0b0c140`

## Coverage

| check | status | note |
|---|---|---|
| Taiyi HTML parse | pass | `.vp-doc` 章节正文已抽取。 |
| chapter count | pass | 9 个章节段落：源流、凡例、卷一至三、合并卷四至九、卷十至十二。 |
| quote exact-ish match | pass_pending_audit | `quote-index.md` 短引来自本地 fulltext。 |
| scan collation | pending | NLC/Wikimedia PDF 已下载，但本次未逐页影印校勘。 |
| CTP collation | partial | CTP 只作部分卷次章节锚点。 |

## Known Limits

- 卷四至九为 Taiyi 合并文本，不能拆成独立卷次证据。
- 当前 pack 已足够进入 D3 skill 蒸馏草稿；若要做“严校原典 skill”，需继续对 NLC/Wikimedia 影印本逐页校勘。

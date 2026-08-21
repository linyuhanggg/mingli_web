# 蘭臺妙選 — Validation

## Local Source

- normalized_path: `references/fulltext/luming-nayin/lantai-miaoxuan/fulltext.md`
- normalized_sha256: `ae30d81ed02dc99dd227f2ca7b0e6daf34bea9776c8a531f042b8e59bd80346e`
- raw_dir: `sources/raw/luming-nayin/lantai-miaoxuan/`
- raw_files:
  - `ctext_lantai_miaoxuan.html` sha256 `8b9d6b063327779c093fcfe48e66006a5cbcb668360dee0daccb004f3867b845`
  - `dongli_3764_shangpian.html` sha256 `3cd1249f7963660b78eb460db6a5d018589e9cae3c51c1ca549a63c352eff2f3`
  - `dongli_3765_zhongpian.html` sha256 `db064fd456b9e439463e9550359790eead0472f5a45cb2c99a5c3d69c343201e`
  - `dongli_3766_xiapian.html` sha256 `3900a09f39e7482d91a7cda7aa56f9b5b85670a19998028d6cfbbf64b52214fc`

## Coverage

| unit | status | evidence |
|---|---|---|
| 上篇 | done | chapter-map `LT-01-shangpian`; quote-index LT-Q001+ |
| 中篇 | done | chapter-map `LT-02-zhongpian`; quote-index LT-Q011+ |
| 下篇 | done | chapter-map `LT-03-xiapian`; quote-index LT-Q021+ |

## Known Risks

- 东里 HTML 是现代整理本，虽便于采集，但仍需与 CTP/Wikisource/影印本逐字校。
- 第591卷 Wikisource proofread 页面前半有《磨鑴賦》，不能误并入《蘭臺妙選》。
- 中篇含疾病、夭折、刑伤、贫愚等高风险断语，skill 只能作文化文本解释。

## D2 Gate

- required_files: present
- chapter_status_values: `done` only
- quote_index: exact-ish local matches expected
- line_anchors: within fulltext line range expected

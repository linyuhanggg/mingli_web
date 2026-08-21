# 柳庄相法 — Validation

## Local Source

- normalized_path: `references/fulltext/physiognomy/liuzhuang-xiangfa/fulltext.md`
- normalized_sha256: `04459fbe4f5d48e0810a8f0290c6f8f851754db02a2344fc109380aee6059af8`
- raw_ctext: `sources/raw/physiognomy/liuzhuang-xiangfa/ctext_liuzhuang_xiangfa.html`
- raw_ctext_sha256: `19c9441c6d7939965ed365dd48334a5efe77a122c9279823b94b9e6cd6471679`
- raw_pdf: `sources/raw/physiognomy/liuzhuang-xiangfa/wikimedia_nlc_liuzhuang_xiangfa.pdf`
- raw_pdf_sha256: `e75f6fbad4336dfeb62e50d54507c2c3e4bf8f69b4b93f89062b868ddae90eac`

## Coverage

| unit | status | evidence |
|---|---|---|
| CTP row table | done | 618 rows extracted |
| heading units | done | 136 done rows in chapter-map |
| quote index | done | 80 exact short quotes |

## Risks

- PDF is image-only in local extraction; CTP text is used as normalized底本 and still needs image校对.
- Text contains high-risk body/health/sex/gender/class judgments; all use must be reframed as historical text.
- CTP page gives a continuous line table; original printed卷册结构 may differ.

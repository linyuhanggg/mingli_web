# validation: 阳宅三要

## D2 状态

- normalized_source: ready
- line_units: 1351
- chapter-map coverage: 1351/1351 done
- quote-index: 180 条短引，均从 `fulltext.md` 抽取
- text_html_sha256: `f1d9fc87a0c61ccaef8b6b0cc7972610a30179805ca0efded5bda4e8cb75c0d1`
- scan_pdf_sha256: `96a37982c0e02e1daf0ab9b033cba1a04ce25a7ee1ec4f55731674ac6cd1e202`
- normalized_sha256: `56128f671f3b75fc05f04987a9445a57cef9058825442349c0d216d3cc364735`

## 版本边界

本轮 normalized 不是清光绪 PDF 的 OCR，而是 1989 李德明翻印文字页。PDF 已下载为影印锚点，但 pypdf 抽取文字为 0，说明无可用文字层。后续若执行 OCR，应以 PDF 前半部《阳宅三要》四卷替换/校正文本文字。

## 风险

- 文本含“补充”“经验总结”等后出内容，应在 skill 中标为注释层。
- HTML 文字可能有错字、简繁转换、断行错误。
- PDF 同文件还含《地理五诀》，蒸馏时不要把《地理五诀》内容混入本 pack。

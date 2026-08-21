# SS-B6 《星平会海/命海全编》OCR 校勘计划

generated_at: 2026-07-05  
matrix_version: v0.3  
source_status: ocr_pipeline_initialized_not_distillable  
scope: `xingming/minghai-quanbian` 的 OCR、页图、校勘和晋级门槛。

本文件推进 SS-B6，但不把《星平会海/命海全编》升为可断事来源。当前结论很硬：这本书已下载到本地，但仍是 image-only；没有 reviewed fulltext 前，不得进入 `rules.md`、`procedures.md`、`quote-index.md` 或回答层。

## 当前状态

| Item | Value |
|---|---|
| Source | 《新刻星平總會命海全編 / 星平会海》 |
| Slug | `xingming/minghai-quanbian` |
| Raw scans | 6 PDFs |
| Total PDF pages | 437 |
| Manifest | `~/Desktop/mingli-corpus-plan/qoder-distillation/sources/manifests/minghai-quanbian.yaml` |
| Page map | `~/Desktop/mingli-corpus-plan/qoder-distillation/sources/derived/xingming/minghai-quanbian/ocr/page-map.csv` |
| Source status | `image_only` |
| Normalized status | `blocked` |
| Distillation allowed | `false` |

## 已验证事实

- 6 册 Harvard/Commons PDF 已在本地，manifest 记录了 Commons SHA1 与本地 SHA256。
- `page-map.csv` 已有 437 行，每一 PDF 页都进了队列。
- PDF 无可抽取文字层。
- v.1 page 14 目检可见 `論諸吉神起例`，证明它确实是神煞补源候选。
- Tesseract `chi_tra_vert --psm 5` 对 page 14 叶图输出严重噪声，不能当正文。
- macOS Vision OCR 对同一 page 14 右叶 crop 没有返回可用文本。
- `render_minghai_ocr_assets.py` 已支持 `--columns 8 --column-overlap 70`，page 14 已生成左右叶共 16 张 column tiles，并写入 per-leaf index。列图只作校勘输入，不是 canonical text。
- review batch 001 已扩展到 v.1 pages 13-24：12 页、264 个图像校勘资产；page 15 直接 `pdftoppm` 渲染超时，因此 `render_minghai_ocr_assets.py` 现在支持 `--render-timeout` 和 `--prefer-existing-render`。
- batch 001 已创建 12 个 reviewed-page 草稿位：`reviewed-pages/page-013.md` 到 `page-024.md`；当前 page 013、page 014、page 015、page 016、page 017、page 018、page 019、page 020、page 021、page 022、page 023、page 024 均為 `in_review` 模型辅助初校；它们只是转写落点，不是 final reviewed text。
- `validate_minghai_review_pages.py --pages 13-24` 为 batch 001 历史验证结果：`OK draft_empty=0, in_review=12`，并会阻止空转写或缺 reviewer 的页面被误标为 `reviewed`。
- review batch 002 已新增 v.1 page 25：page 025 的图像资产、列级 OCR 草稿、`reviewed-pages/page-025.md` 初校稿已生成。
- page 25 继续 page 24 末尾 `三刑歌`，并初校到 `吞啖煞歌`、`流霞煞歌`、`返伏吟`、`孤辰寡宿歌`、`論黃幡豹尾`、`紅艷煞歌`、`陰錯陽差歌` 开头；仍不得用于规则或回答层。
- review batch 003 已新增 v.1 page 26：page 026 的图像资产、列级 OCR 草稿、`reviewed-pages/page-026.md` 初校稿已生成；当前 page 013-026 共 14 页均为 `in_review`，验证结果为 `OK in_review=14`。
- page 26 继续 `陰錯陽差歌` 后半，并初校到 `呻吟煞一名孤鸞煞歌`、`總論駕前神煞歌`、`總論駕後神煞歌`、`地煞賦總斷` 开头；仍不得用于规则或回答层。
- `ocr_minghai_column_tiles.py` 已支持从 column tiles 生成列级 Tesseract 草稿。page 14 生成 16 个 `ocr_unreviewed_draft` 文本文件，但 `論諸吉神起例`、`論祿勳`、`論玉堂`、`祿者`、`天元祿` 均未在未校 OCR 中稳定命中。
- 2026-07-05 线上 spot check 发现识典古籍渲染文本候选页能见 `論諸吉神起例`、`論玉堂`、`論文昌`、`論禄神` 等 page-14-relevant anchors；随后审核确认 robots/协议/覆盖率均未通过 normalized source 门槛，仍只能作小范围 comparison lead。

## 可做与不可做

可做：

- 页码/叶面/版心/卷次 accounting。
- 渲染页面图、内容裁切、左右叶拆分。
- OCR 草稿实验。
- 人工或模型辅助转写。
- 建 reviewed-pages，并在全部页面 accounting 完成后组装 `fulltext.reviewed.md`。

不可做：

- 不得把未校 OCR 写进 `rules.md`。
- 不得把这本书作为 answer-time 一线来源。
- 不得把星命/子平混合神煞直接合并到八字、择日、六壬或风水条目。
- 不得因识典或其他网页有渲染文本，就绕过完整性和使用条款核验。

## 当前产物

| Path | Purpose |
|---|---|
| `sources/derived/xingming/minghai-quanbian/SS_B6_OCR_STATUS.md` | SS-B6 状态报告 |
| `sources/derived/xingming/minghai-quanbian/OCR_COLLATION_PROTOCOL.md` | OCR/校勘协议 |
| `sources/derived/xingming/minghai-quanbian/ocr/OCR_SAMPLE_REPORT.md` | page 14 OCR 样本报告 |
| `sources/scripts/render_minghai_ocr_assets.py` | 生成页面/裁切/左右叶校勘图 |
| `sources/scripts/ocr_minghai_column_tiles.py` | 从列级校勘图生成未校 OCR 草稿 |
| `sources/scripts/create_minghai_review_page_stubs.py` | 生成逐页 reviewed-pages 草稿位 |
| `sources/scripts/validate_minghai_review_pages.py` | 校验逐页草稿状态，防止未校文本晋级 |
| `sources/derived/xingming/minghai-quanbian/ocr/VISION_REVIEW_QUEUE.md` | 视觉校勘队列 |
| `sources/derived/xingming/minghai-quanbian/ocr/review-batch-001-v1-pages-013-024.md` | v.1 pages 13-24 首批图像/列切校勘资产清单 |
| `sources/derived/xingming/minghai-quanbian/ocr/review-batch-002-v1-page-025.md` | v.1 page 25 增量图像/列切校勘资产清单 |
| `sources/derived/xingming/minghai-quanbian/ocr/review-batch-003-v1-page-026.md` | v.1 page 26 增量图像/列切校勘资产清单 |
| `sources/derived/xingming/minghai-quanbian/ocr/reviewed-pages/REVIEWED_PAGES_STATUS.md` | batch 001-003 逐页转写草稿状态 |
| `sources/derived/xingming/minghai-quanbian/ocr/vision-assets/page-014/column-tiles/` | page 14 左右叶列级校勘图 |
| `sources/derived/xingming/minghai-quanbian/ocr/ocr-drafts/page-014-column-tiles/COLUMN_OCR_DRAFT_REPORT.md` | page 14 列级未校 OCR 草稿报告 |
| `sources/derived/xingming/minghai-quanbian/SHIDIAN_CANDIDATE_REVIEW.md` | 识典 HY1442 候选源 robots/协议/覆盖率审核 |
| `https://www.shidianguji.com/zh/book/HY1442/chapter/1koboy2q7bbws` | 识典渲染文本候选；仅作对照线索 |

## 使用脚本

```bash
cd ~/Desktop/mingli-corpus-plan/qoder-distillation
python sources/scripts/render_minghai_ocr_assets.py --pages 14 --dpi 300 --columns 8 --column-overlap 70
```

脚本产物只作校勘输入，不是 canonical text。

首批连续页资产已用：

```bash
cd ~/Desktop/mingli-corpus-plan/qoder-distillation
python sources/scripts/render_minghai_ocr_assets.py --pages 15-24 --dpi 220 --columns 8 --column-overlap 50 --render-timeout 25 --prefer-existing-render
```

该批次与 page 13-14 合成 review batch 001，覆盖 v.1 pages 13-24。它只创建图像/列切校勘资产，不创建 reviewed text。

创建逐页转写草稿位：

```bash
cd ~/Desktop/mingli-corpus-plan/qoder-distillation
python sources/scripts/create_minghai_review_page_stubs.py --pages 13-24
```

校验逐页草稿：

```bash
cd ~/Desktop/mingli-corpus-plan/qoder-distillation
python sources/scripts/validate_minghai_review_pages.py --pages 13-24
```

当前 page 013-026 验证输出是 `OK in_review=14`。只有人工或模型辅助校对后，才可以把单页从 `draft_empty` 改成 `in_review`，再经完整复核后改成 `reviewed`；即便如此，页级 `distillation_allowed` 仍保持 `false`，直到整本 reviewed fulltext 组装并回写 checksum。

列级 OCR 草稿可用：

```bash
cd ~/Desktop/mingli-corpus-plan/qoder-distillation
python sources/scripts/ocr_minghai_column_tiles.py --page 14 --leaf both --force
```

该脚本产物是 `ocr_unreviewed_draft`，只用于辅助人工或图像模型复核。当前 page 14 运行结果未通过标题/术语锚点检查，不得进入 `rules.md`、`procedures.md`、`quote-index.md` 或回答层。

识典文本候选的当前审核结论：

1. 2026-07-05 已确认 robots.txt 对 generic user-agent 为 `Disallow: /`。
2. 识典用户协议限制未经书面许可的复制、整理、非法抓取、模拟下载、机器人监视/复制/下载等行为。
3. sitemap 能见 HY1442 book URL 和 9 个 chapter URL，但不能证明覆盖本地十卷、首一卷。
4. 因此识典只能小范围作人工校勘旁证；不得批量抓取、不得作为 `complete_chapter_set`、不得生成 D2 pack。

未来如果要重新评估，必须先取得明确授权或官方允许的导出路径，再核章节覆盖、质量标签，并抽样对齐 Harvard/Commons 影印本 page 14 及后续 5-10 页。

## 晋级门槛

1. 437 页全部完成 page type、layout、visible folio/section accounting。
2. 每个有正文的页/叶都有 reviewed transcription，或明确标为 unreadable/non-text。
3. 神煞相关段落至少双重复核页面图。
4. `fulltext.reviewed.md` 带页锚。
5. reviewed fulltext SHA256 写回 manifest。
6. `sources/scripts/validate_sources.py` 通过。
7. D2 pack 保留边界：本书是星命/子平混合来源，不能覆盖八字格局、调候、旺衰，也不能替代七政四余天文排盘 adapter。

## 下一步

继续 SS-B6，不转入 SS-B7。先围绕 v.1 page 14 附近做高价值神煞页面的 reviewed-page 转写与校勘，等小段可稳定校对后再扩大到 437 页；后续“顺便看神煞相关书籍”仍走 SS-B10 书目核验和 source_status gate。

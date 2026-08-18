from __future__ import annotations

from pathlib import Path

from app.readings.export import _document_lines, _pdf_font_name, render_reading_export
from app.readings.presentation import ReadingDocumentV1, build_reading_document
from reportlab.pdfbase.ttfonts import TTFError
from test_reading_delivery import _document_payload, _presentation_contract


def _preview_document() -> ReadingDocumentV1:
    payload = _document_payload(
        "33333333-3333-4333-8333-333333333333",
        "accepted-copy:fixture",
    )
    payload["product_version"] = "bazi-reading/v1"
    payload["answer_summary"] = "这是合同测试候选稿，不是正式命理解读。"
    payload["claims"] = [
        {
            **payload["claims"][0],  # type: ignore[index]
            "text": "这是合同测试候选稿，不是正式命理解读。",
        }
    ]
    contract = _presentation_contract().model_copy(
        update={"product_version": "bazi-reading/v1"}
    )
    return build_reading_document(contract, payload)


def test_bazi_preview_export_uses_a_dedicated_chinese_report_without_fake_copy() -> None:
    document = _preview_document()

    lines = _document_lines(document)

    assert lines[:2] == ("私密报告", "八字命盘报告")
    assert "四柱" in lines
    assert "年柱 甲子" in lines
    assert "月柱 乙丑" in lines
    assert "日柱 丙寅" in lines
    assert "时柱 丁卯" in lines
    assert any("免费排盘预览" in line for line in lines)
    joined = "\n".join(lines)
    assert "这是合同测试候选稿" not in joined
    assert "reading-document/v1" not in joined
    assert "reading-version:" not in joined
    assert "命理档案" not in joined
    assert "·" not in joined
    assert "•" not in joined


def test_pdf_uses_a_chinese_font_even_when_no_local_font_file_exists(monkeypatch) -> None:
    monkeypatch.setattr("app.readings.export._font_path", lambda: None)
    document = _preview_document()

    assert _pdf_font_name() == "STSong-Light"
    rendered = render_reading_export(document, "pdf")
    assert rendered.payload.startswith(b"%PDF-")
    assert b"STSong" in rendered.payload


def test_pdf_falls_back_when_the_linux_cjk_collection_has_postscript_outlines(
    monkeypatch,
) -> None:
    monkeypatch.setattr("app.readings.export._font_path", lambda: Path("NotoSansCJK.ttc"))
    monkeypatch.setattr(
        "app.readings.export.pdfmetrics.getRegisteredFontNames",
        lambda: ["STSong-Light"],
    )

    def reject_postscript_collection(*_args, **_kwargs):
        raise TTFError("postscript outlines are not supported")

    monkeypatch.setattr("app.readings.export.TTFont", reject_postscript_collection)

    assert _pdf_font_name() == "STSong-Light"

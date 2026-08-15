from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Literal

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.colors import HexColor  # type: ignore[import-untyped]
from reportlab.lib.pagesizes import A4  # type: ignore[import-untyped]
from reportlab.pdfbase import pdfmetrics  # type: ignore[import-untyped]
from reportlab.pdfbase.ttfonts import TTFont  # type: ignore[import-untyped]
from reportlab.pdfgen import canvas  # type: ignore[import-untyped]

from app.readings.presentation import ReadingDocumentV1

ExportFormat = Literal["png", "pdf"]

_FONT_CANDIDATES = (
    Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
    Path("/System/Library/Fonts/STHeiti Medium.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/google-noto/NotoSansCJK-Regular.ttf"),
    Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
)
_PRODUCT_LABELS = {
    "bazi-chart/v1": "八字命盘",
    "five-elements-facts-view/v1": "五行事实与调候依据",
    "ziwei-chart/v1": "紫微斗数",
    "qizheng-chart/v1": "七政四余",
    "liuyao-chart/v1": "六爻问事",
    "meihua-chart/v1": "梅花易数",
    "luming-nayin-chart/v1": "禄命纳音",
    "rhythm-facts-view/v1": "本命音律纳音事实",
    "chart-similarity-view/v1": "八字四柱同盘事实比较",
    "time-check-view/v1": "寻时定盘",
    "taiyi-chart/v1": "太乙神数",
    "selection-chart/v1": "择日",
    "fengshui-view/v1": "风水",
    "qimen-chart/v1": "奇门遁甲",
    "daliuren-chart/v1": "大六壬",
    "physiognomy-view/v1": "见相",
    "canwen-view/v1": "多盘问答",
    "hecan-view/v1": "命盘合参",
    "bazi-relationship/v1": "八字合盘",
    "ziwei-relationship/v1": "紫微合盘",
    "qizheng-relationship/v1": "七政合盘",
}


@dataclass(frozen=True, slots=True)
class RenderedExport:
    format: ExportFormat
    content_type: str
    file_name: str
    payload: bytes


def _font_path() -> Path | None:
    return next((candidate for candidate in _FONT_CANDIDATES if candidate.is_file()), None)


def _font_or_default(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = _font_path()
    if path is not None:
        try:
            return ImageFont.truetype(str(path), size=size)
        except OSError:
            pass
    return ImageFont.load_default()


def _text(value: object) -> str:
    return " ".join(str(value).split())


def _wrap(value: object, width: int) -> tuple[str, ...]:
    text = _text(value)
    if not text:
        return ("",)
    return tuple(text[index : index + width] for index in range(0, len(text), width))


def _document_lines(document: ReadingDocumentV1) -> tuple[str, ...]:
    label = _PRODUCT_LABELS.get(document.view_model.schema_version, "命理解读")
    lines: list[str] = [
        "FateRadar · 私密报告",
        label,
        f"版本 {document.versions.view_model_schema}",
        "",
        "一句话回答",
    ]
    lines.extend(_wrap(document.answer_summary, 34))
    lines.extend(("", "判断"))
    for claim in document.claims:
        lines.extend(_wrap(f"· {claim.text}", 34))
    lines.extend(("", "依据"))
    for evidence in document.evidence:
        lines.extend(_wrap(f"· {evidence.title}", 34))
    lines.extend(("", "边界"))
    for boundary in document.boundaries:
        lines.extend(_wrap(f"· {boundary.text}", 34))
    lines.extend(("", "报告版本", f"{document.schema_version} · {document.document_id}"))
    return tuple(lines)


def _render_png(document: ReadingDocumentV1) -> bytes:
    lines = _document_lines(document)
    line_height = 54
    top = 96
    bottom = 96
    height = max(900, top + bottom + line_height * len(lines))
    image = Image.new("RGB", (1600, height), "#f6f1e8")
    draw = ImageDraw.Draw(image)
    title_font = _font_or_default(50)
    body_font = _font_or_default(30)
    draw.rounded_rectangle(
        (72, 64, 1528, height - 64),
        radius=28,
        fill="#fffdf8",
        outline="#d8c8ae",
        width=3,
    )
    draw.rectangle((72, 64, 1528, 78), fill="#1f4f4a")
    y = top
    for index, line in enumerate(lines):
        font = title_font if index in (0, 1) else body_font
        fill = "#1f4f4a" if index in (0, 1, 4) else "#2d2b28"
        draw.text((126, y), line, font=font, fill=fill)
        y += line_height
    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()


def _pdf_font_name() -> str:
    path = _font_path()
    if path is None:
        return "Helvetica"
    name = "FateRadarCJK"
    try:
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(path), subfontIndex=0))
    except (OSError, TypeError, ValueError):
        return "Helvetica"
    return name


def _render_pdf(document: ReadingDocumentV1) -> bytes:
    output = BytesIO()
    page_width, page_height = A4
    margin = 54
    line_height = 18
    report = canvas.Canvas(output, pagesize=A4)
    report.setTitle("FateRadar Reading")
    font_name = _pdf_font_name()
    y = page_height - margin
    for index, line in enumerate(_document_lines(document)):
        if y < margin:
            report.showPage()
            y = page_height - margin
        report.setFont(font_name, 19 if index in (0, 1) else 10.5)
        report.setFillColor(HexColor("#1f4f4a" if index in (0, 1, 4) else "#2d2b28"))
        report.drawString(margin, y, line)
        y -= line_height if index not in (0, 1) else 26
    report.save()
    return output.getvalue()


def render_reading_export(
    document: ReadingDocumentV1,
    export_format: ExportFormat,
) -> RenderedExport:
    schema_slug = document.view_model.schema_version.replace("/", "-")
    slug = "".join(
        character.lower() if character.isascii() and character.isalnum() else "-"
        for character in schema_slug
    ).strip("-") or "reading"
    if export_format == "png":
        return RenderedExport(
            format="png",
            content_type="image/png",
            file_name=f"mingli-{slug}-report.png",
            payload=_render_png(document),
        )
    return RenderedExport(
        format="pdf",
        content_type="application/pdf",
        file_name=f"mingli-{slug}-report.pdf",
        payload=_render_pdf(document),
    )

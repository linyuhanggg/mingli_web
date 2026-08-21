from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Literal

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.colors import HexColor  # type: ignore[import-untyped]
from reportlab.lib.pagesizes import A4  # type: ignore[import-untyped]
from reportlab.pdfbase import pdfmetrics  # type: ignore[import-untyped]
from reportlab.pdfbase.cidfonts import UnicodeCIDFont  # type: ignore[import-untyped]
from reportlab.pdfbase.ttfonts import TTFError, TTFont  # type: ignore[import-untyped]
from reportlab.pdfgen import canvas  # type: ignore[import-untyped]

from app.charts.contracts import BaziChartV1
from app.readings.presentation import ReadingDocumentV1

ExportFormat = Literal["png", "pdf"]
ElementId = Literal["wood", "fire", "earth", "metal", "water"]

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
_POSITION_LABELS = {
    "year": "年柱",
    "month": "月柱",
    "day": "日柱",
    "hour": "时柱",
}
_ELEMENT_LABELS: dict[ElementId, str] = {
    "wood": "木",
    "fire": "火",
    "earth": "土",
    "metal": "金",
    "water": "水",
}
_REPORT_HEADINGS = frozenset(
    {
        "解读摘要",
        "判断",
        "四柱",
        "盘面要点",
        "五行计数",
        "地支关系",
        "大运",
        "古籍依据",
        "说明",
    }
)


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


def _safe_report_line(value: str, *, preserve_middle_dot: bool = False) -> str:
    """Keep punctuation inside the glyph set shared by PNG and CID-font PDFs."""
    normalized = value.replace("•", "-")
    if normalized.startswith("· "):
        normalized = f"- {normalized[2:]}"
    if preserve_middle_dot:
        return normalized
    return normalized.replace(" · ", "：").replace("·", "，")


def _bazi_document_lines(
    document: ReadingDocumentV1,
    chart: BaziChartV1,
) -> tuple[str, ...]:
    lines: list[tuple[str, bool]] = []

    def add(value: str, *, preserve_middle_dot: bool = False) -> None:
        lines.append((value, preserve_middle_dot))

    def add_many(*values: str) -> None:
        for value in values:
            add(value)

    def add_wrapped(
        value: object,
        width: int,
        *,
        preserve_middle_dot: bool = False,
    ) -> None:
        for line in _wrap(value, width):
            add(line, preserve_middle_dot=preserve_middle_dot)

    add_many("私密报告", "八字命盘报告", "", "四柱")
    for pillar in chart.pillars:
        label = _POSITION_LABELS[pillar.position]
        add(f"{label} {pillar.stem}{pillar.branch}")

    core = chart.core_facts
    if core is not None:
        add_many("", "盘面要点")
        if core.day_master is not None:
            element = _ELEMENT_LABELS[core.day_master.element]
            add(f"日主 {core.day_master.stem} · {core.day_master.polarity}{element}")
        if core.month_command is not None:
            add(
                f"月令 {core.month_command.branch} · 主气{core.month_command.main_qi}"
                f"（{_ELEMENT_LABELS[core.month_command.main_qi_element]}）"
            )
        if core.seasonal_profile is not None:
            add(
                f"时令 {core.seasonal_profile.season} · "
                f"{core.seasonal_profile.temperature} · {core.seasonal_profile.moisture}"
            )
        if core.element_inventory is not None:
            add_many("", "五行计数")
            visible = {
                item.element: item.value
                for item in core.element_inventory.visible_stem_branch_counts
            }
            hidden = {
                item.element: item.value
                for item in core.element_inventory.hidden_stem_occurrence_counts
            }
            for element, label in _ELEMENT_LABELS.items():
                add(
                    f"{label}：表层 {visible.get(element, 0)}，藏干 {hidden.get(element, 0)}"
                )
        if core.branch_relations:
            add_many("", "地支关系")
            for relation in core.branch_relations:
                add(f"{'、'.join(relation.branches)} · {relation.relation_type}")
        if core.luck_cycles is not None:
            add_many("", "大运")
            direction = {"forward": "顺行", "reverse": "逆行"}.get(
                core.luck_cycles.direction or "",
                "方向未返回",
            )
            start_age = (
                f"，约 {core.luck_cycles.start_age_years:g} 岁起运"
                if core.luck_cycles.start_age_years is not None
                else ""
            )
            add(f"{direction}{start_age}")
            for cycle in core.luck_cycles.cycles:
                age = ""
                if cycle.start_age_years is not None and cycle.end_age_years is not None:
                    age = f" · {cycle.start_age_years:g} 至 {cycle.end_age_years:g} 岁"
                add(f"第 {cycle.sequence} 运 {cycle.pillar}{age}")

    if document.product_version.startswith("bazi-deep"):
        add_many("", "解读摘要")
        add_wrapped(document.answer_summary, 34)
        if document.claims:
            add_many("", "判断")
            for claim in document.claims:
                add_wrapped(f"· {claim.text}", 34)
    else:
        add_many("", "说明", "这是免费排盘预览，展示命盘与确定性事实，不含完整深度解读。")

    if document.evidence:
        add_many("", "古籍依据")
        for evidence in document.evidence:
            add_wrapped(f"· {evidence.title}", 34, preserve_middle_dot=True)
    if document.boundaries:
        add_many("", "说明")
        for boundary in document.boundaries:
            add_wrapped(f"· {boundary.text}", 34)
    return tuple(
        _safe_report_line(line, preserve_middle_dot=preserve_middle_dot)
        for line, preserve_middle_dot in lines
    )


def _document_lines(document: ReadingDocumentV1) -> tuple[str, ...]:
    if isinstance(document.view_model, BaziChartV1):
        return _bazi_document_lines(document, document.view_model)

    label = _PRODUCT_LABELS.get(document.view_model.schema_version, "命理解读")
    lines: list[tuple[str, bool]] = []

    def add(value: str, *, preserve_middle_dot: bool = False) -> None:
        lines.append((value, preserve_middle_dot))

    def add_many(*values: str) -> None:
        for value in values:
            add(value)

    def add_wrapped(
        value: object,
        width: int,
        *,
        preserve_middle_dot: bool = False,
    ) -> None:
        for line in _wrap(value, width):
            add(line, preserve_middle_dot=preserve_middle_dot)

    add_many("私密报告", label, "", "解读摘要")
    add_wrapped(document.answer_summary, 34)
    if document.claims:
        add_many("", "判断")
        for claim in document.claims:
            add_wrapped(f"· {claim.text}", 34)
    if document.evidence:
        add_many("", "古籍依据")
        for evidence in document.evidence:
            add_wrapped(f"· {evidence.title}", 34, preserve_middle_dot=True)
    if document.boundaries:
        add_many("", "说明")
    for boundary in document.boundaries:
        add_wrapped(f"· {boundary.text}", 34)
    return tuple(
        _safe_report_line(line, preserve_middle_dot=preserve_middle_dot)
        for line, preserve_middle_dot in lines
    )


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
        is_heading = line in _REPORT_HEADINGS
        font = title_font if index in (0, 1) else body_font
        fill = "#1f4f4a" if index in (0, 1) or is_heading else "#2d2b28"
        draw.text((126, y), line, font=font, fill=fill)
        y += line_height
    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()


def _pdf_font_name() -> str:
    path = _font_path()
    if path is not None:
        name = "MingliReportCJK"
        try:
            if name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(name, str(path), subfontIndex=0))
            return name
        except (OSError, TTFError, TypeError, ValueError):
            pass

    fallback = "STSong-Light"
    if fallback not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(UnicodeCIDFont(fallback))
    return fallback


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
        report.setFillColor(
            HexColor(
                "#1f4f4a"
                if index in (0, 1) or line in _REPORT_HEADINGS
                else "#2d2b28"
            )
        )
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

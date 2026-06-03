from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas

from .config import Settings
from .layout import PageLayout, RenderLayout


def hex_to_color(hex_str: str, default: str = "#000000"):
    try:
        return HexColor(hex_str)
    except Exception:
        return HexColor(default)


def _draw_highlights(c: canvas.Canvas, page_layout: PageLayout) -> None:
    for item in page_layout.highlights:
        c.saveState()
        c.setFillColor(hex_to_color(item.color))
        c.setFillAlpha(item.opacity)
        c.rect(item.x, item.y, item.width, item.height, fill=1, stroke=0)
        c.restoreState()


def _draw_source_text(
    c: canvas.Canvas,
    page_layout: PageLayout,
    settings: Settings,
    font_name: str,
    font_size: int | float,
    margin,
) -> None:
    c.setFont(font_name, font_size)
    c.setFillColor(HexColor("#333333"))

    for line_item in page_layout.lines:
        if settings.show_line_numbers and line_item.line_num_str.strip():
            c.saveState()
            c.setFillColor(HexColor("#888888"))
            c.drawString(margin.left, line_item.y, line_item.line_num_str)
            c.restoreState()
        c.drawString(line_item.x, line_item.y, line_item.text)


def _draw_inline_annotations(c: canvas.Canvas, page_layout: PageLayout, font_name: str) -> None:
    for item in page_layout.inline_annotations:
        c.saveState()
        c.setFont(font_name, 7)
        c.setFillColor(hex_to_color(item.color))
        c.drawString(item.x, item.y, item.text)
        c.restoreState()


def _draw_margin_comments(
    c: canvas.Canvas,
    page_layout: PageLayout,
    font_name: str,
    font_size: int | float,
    page_width: float,
    margin,
) -> None:
    box_width = margin.right - 30
    box_x = page_width - margin.right + 15

    for item in page_layout.margin_comments:
        ann = item.annotation
        y_top = item.y_top
        y_bottom = item.y_bottom
        h = item.height

        c.saveState()
        c.setLineWidth(0.75)
        c.setStrokeColor(hex_to_color(ann.color))
        c.setFillColor(hex_to_color(ann.bg_color))
        c.roundRect(box_x, y_bottom, box_width, h, 4, fill=1, stroke=1)

        c.setFillColor(hex_to_color(ann.color))
        c.setFont(font_name, 8)
        text_y = y_top - 8 - 6
        for cl in item.lines:
            c.drawString(box_x + 8, text_y, cl)
            text_y -= 9.6
        c.restoreState()

        c.saveState()
        c.setStrokeColor(hex_to_color(ann.color))
        c.setLineWidth(0.5)
        cx1 = item.target_x_end
        cy1 = item.target_y + font_size / 2
        cx2 = box_x
        cy2 = (y_top + y_bottom) / 2
        c.line(cx1, cy1, cx2, cy2)
        c.setFillColor(hex_to_color(ann.color))
        c.circle(cx1, cy1, 1.5, fill=1, stroke=0)
        c.restoreState()


def _draw_header(
    c: canvas.Canvas,
    settings: Settings,
    font_name: str,
    filename: str,
    margin,
    page_width: float,
    page_height: float,
) -> None:
    if not settings.show_filename:
        return

    c.saveState()
    c.setFont(font_name, 8)
    c.setFillColor(HexColor("#888888"))
    c.drawString(margin.left, page_height - margin.top + 15, filename)
    c.setStrokeColor(HexColor("#DDDDDD"))
    c.setLineWidth(0.5)
    c.line(margin.left, page_height - margin.top + 10, page_width - margin.left, page_height - margin.top + 10)
    c.restoreState()


def _draw_footer(
    c: canvas.Canvas,
    settings: Settings,
    font_name: str,
    page_idx: int,
    total_pages: int,
    margin,
    page_width: float,
) -> None:
    if not settings.show_page_numbers:
        return

    c.saveState()
    c.setFont(font_name, 8)
    c.setFillColor(HexColor("#888888"))
    page_str = f"{page_idx} / {total_pages}"
    text_w = pdfmetrics.stringWidth(page_str, font_name, 8)
    c.drawString(page_width - margin.left - text_w, margin.bottom - 20, page_str)
    c.setStrokeColor(HexColor("#DDDDDD"))
    c.setLineWidth(0.5)
    c.line(margin.left, margin.bottom - 10, page_width - margin.left, margin.bottom - 10)
    c.restoreState()


def draw_render_layout(
    layout: RenderLayout,
    settings: Settings,
    font_name: str,
    output_path: str,
    filename: str,
) -> None:
    c = canvas.Canvas(output_path, pagesize=(layout.page_width, layout.page_height))
    total_pages = len(layout.pages)

    for page_idx, page_layout in enumerate(layout.pages, 1):
        _draw_highlights(c, page_layout)
        _draw_source_text(c, page_layout, settings, font_name, settings.font_size, settings.margin)
        _draw_inline_annotations(c, page_layout, font_name)
        _draw_margin_comments(c, page_layout, font_name, settings.font_size, layout.page_width, settings.margin)
        _draw_header(c, settings, font_name, filename, settings.margin, layout.page_width, layout.page_height)
        _draw_footer(c, settings, font_name, page_idx, total_pages, settings.margin, layout.page_width)
        c.showPage()

    c.save()

from dataclasses import dataclass

from reportlab.lib.pagesizes import A4, letter
from reportlab.pdfbase import pdfmetrics

from .config import Annotation, RenderConfig, Settings


@dataclass
class Segment:
    text: str
    char_start: int
    char_end: int


@dataclass
class PageLine:
    text: str
    line_num_str: str
    source_line_num: int
    char_start: int
    char_end: int
    x: float
    y: float


@dataclass
class HighlightRect:
    x: float
    y: float
    width: float
    height: float
    color: str
    opacity: float


@dataclass
class InlineAnnotation:
    text: str
    x: float
    y: float
    color: str


@dataclass
class MarginComment:
    annotation: Annotation
    lines: list[str]
    height: float
    target_y: float
    target_x_end: float
    y_ideal: float
    y_top: float = 0.0
    y_bottom: float = 0.0


@dataclass
class PageLayout:
    lines: list[PageLine]
    highlights: list[HighlightRect]
    inline_annotations: list[InlineAnnotation]
    margin_comments: list[MarginComment]


@dataclass
class RenderLayout:
    pages: list[PageLayout]
    text_x: float
    page_width: float
    page_height: float


def resolve_page_dimensions(settings: Settings) -> tuple[float, float]:
    base_size = A4 if settings.page_size == "A4" else letter
    if settings.orientation == "landscape":
        return base_size[1], base_size[0]
    return base_size[0], base_size[1]


def line_number_column_width(
    total_lines: int,
    font_name: str,
    font_size: int | float,
    show_line_numbers: bool,
) -> float:
    if not show_line_numbers:
        return 0

    line_num_width_chars = len(str(total_lines))
    line_num_prefix_example = "0" * line_num_width_chars + ": "
    return pdfmetrics.stringWidth(line_num_prefix_example, font_name, font_size) + 5


def wrap_comment_text(text: str, font_name: str, font_size: int | float, max_width: int | float) -> list[str]:
    """Wrap comment text to fit within max_width. Handles Japanese char-by-char wrapping."""
    words = text.split()
    if len(words) == 1 and any(ord(c) > 255 for c in text):
        lines = []
        current_line = ""
        for char in text:
            test_line = current_line + char
            if pdfmetrics.stringWidth(test_line, font_name, font_size) > max_width:
                if current_line:
                    lines.append(current_line)
                current_line = char
            else:
                current_line = test_line
        if current_line:
            lines.append(current_line)
        return lines

    lines = []
    current_line = ""
    for word in words:
        test_line = current_line + " " + word if current_line else word
        if pdfmetrics.stringWidth(test_line, font_name, font_size) > max_width:
            if current_line:
                lines.append(current_line)
            current_line = word
        else:
            current_line = test_line
    if current_line:
        lines.append(current_line)
    return lines


def wrap_line(line_text: str, font_name: str, font_size: int | float, max_text_width: int | float) -> list[Segment]:
    """Wrap a single source line to fit max_text_width."""
    segments: list[Segment] = []
    current_segment = ""
    current_width = 0
    char_start = 0

    for idx, char in enumerate(line_text):
        char_width = pdfmetrics.stringWidth(char, font_name, font_size)
        if current_width + char_width > max_text_width and current_segment:
            segments.append(Segment(text=current_segment, char_start=char_start, char_end=idx))
            current_segment = char
            current_width = char_width
            char_start = idx
        else:
            current_segment += char
            current_width += char_width

    segments.append(Segment(text=current_segment, char_start=char_start, char_end=len(line_text)))
    return segments


def _find_annotation_target(
    page_lines: list[PageLine],
    ann: Annotation,
    font_name: str,
    font_size: int | float,
) -> tuple[float, float] | None:
    target_line = ann.line
    target_start = ann.col_start - 1
    target_end = ann.col_end

    for item in page_lines:
        if item.source_line_num != target_line:
            continue
        if item.char_start <= target_start <= item.char_end:
            target_y = item.y
            e_idx = min(target_end, item.char_end) - item.char_start
            target_x_end = item.x + pdfmetrics.stringWidth(item.text[:e_idx], font_name, font_size)
            return target_y, target_x_end

    for item in page_lines:
        if item.source_line_num == target_line:
            target_y = item.y
            target_x_end = item.x + pdfmetrics.stringWidth(item.text, font_name, font_size)
            return target_y, target_x_end

    return None


def _build_margin_comments(
    page_lines: list[PageLine],
    annotations: list[Annotation],
    font_name: str,
    font_size: int | float,
    box_width: float,
) -> list[MarginComment]:
    comments_to_draw: list[MarginComment] = []

    for ann in annotations:
        if ann.type != "text" or ann.position != "margin":
            continue

        target = _find_annotation_target(page_lines, ann, font_name, font_size)
        if target is None:
            continue

        target_y, target_x_end = target
        c_lines = wrap_comment_text(ann.content, font_name, 8, box_width - 16)
        b_height = len(c_lines) * 9.6 + 16
        comments_to_draw.append(
            MarginComment(
                annotation=ann,
                lines=c_lines,
                height=b_height,
                target_y=target_y,
                target_x_end=target_x_end,
                y_ideal=target_y + font_size / 2,
            )
        )

    return comments_to_draw


def _position_margin_comments(
    comments_to_draw: list[MarginComment],
    page_height: float,
    margin,
) -> None:
    if not comments_to_draw:
        return

    comments_to_draw.sort(key=lambda c: c.y_ideal, reverse=True)

    current_top = page_height - margin.top
    for item in comments_to_draw:
        item_top = min(item.y_ideal + item.height / 2, current_top)
        item.y_top = item_top
        item.y_bottom = item_top - item.height
        current_top = item.y_bottom - 8

    if comments_to_draw[-1].y_bottom < margin.bottom:
        current_bottom = margin.bottom
        for item in reversed(comments_to_draw):
            if item.y_bottom < current_bottom:
                diff = current_bottom - item.y_bottom
                item.y_bottom += diff
                item.y_top += diff
            current_bottom = item.y_top + 8


def _build_page_layout(
    page_lines: list[PageLine],
    annotations: list[Annotation],
    settings: Settings,
    font_name: str,
    font_size: int | float,
    margin,
    page_width: float,
    page_height: float,
    text_x: float,
) -> PageLayout:
    highlights: list[HighlightRect] = []
    inline_annotations: list[InlineAnnotation] = []

    for line_item in page_lines:
        source_line = line_item.source_line_num
        char_start = line_item.char_start
        char_end = line_item.char_end
        y = line_item.y

        for ann in annotations:
            if ann.line != source_line:
                continue

            if ann.type == "highlight":
                target_start = ann.col_start - 1
                target_end = ann.col_end
                overlap_start = max(target_start, char_start)
                overlap_end = min(target_end, char_end)

                if overlap_start < overlap_end:
                    s_idx = overlap_start - char_start
                    e_idx = overlap_end - char_start
                    x_start = text_x + pdfmetrics.stringWidth(line_item.text[:s_idx], font_name, font_size)
                    x_end = text_x + pdfmetrics.stringWidth(line_item.text[:e_idx], font_name, font_size)
                    rect_y = y - (font_size * (settings.line_spacing - 1) / 2)
                    rect_height = font_size * settings.line_spacing
                    highlights.append(
                        HighlightRect(
                            x=x_start,
                            y=rect_y,
                            width=x_end - x_start,
                            height=rect_height,
                            color=ann.color,
                            opacity=ann.opacity,
                        )
                    )

            if ann.type == "text" and ann.position == "inline":
                if line_item.char_start != 0:
                    continue
                target_start = ann.col_start - 1
                target_end = ann.col_end
                s_idx = min(max(target_start - line_item.char_start, 0), len(line_item.text))
                e_idx = min(max(target_end - line_item.char_start, 0), len(line_item.text))
                x_start = text_x + pdfmetrics.stringWidth(line_item.text[:s_idx], font_name, font_size)
                x_end = text_x + pdfmetrics.stringWidth(line_item.text[:e_idx], font_name, font_size)
                center_x = (x_start + x_end) / 2
                text_w = pdfmetrics.stringWidth(ann.content, font_name, 7)
                inline_annotations.append(
                    InlineAnnotation(
                        text=ann.content,
                        x=max(center_x - text_w / 2, margin.left),
                        y=line_item.y + font_size + 2,
                        color=ann.color,
                    )
                )

    box_width = margin.right - 30
    comments_to_draw = _build_margin_comments(page_lines, annotations, font_name, font_size, box_width)
    _position_margin_comments(comments_to_draw, page_height, margin)

    return PageLayout(
        lines=page_lines,
        highlights=highlights,
        inline_annotations=inline_annotations,
        margin_comments=comments_to_draw,
    )


def build_render_layout(
    source_text: str,
    config: RenderConfig,
    font_name: str,
) -> RenderLayout:
    source_text = source_text.replace("\t", "    ")

    settings = config.settings
    font_size = settings.font_size
    margin = settings.margin
    page_width, page_height = resolve_page_dimensions(settings)

    source_lines = source_text.splitlines()
    annotations = config.annotations
    total_lines = len(source_lines)
    line_num_width = line_number_column_width(total_lines, font_name, font_size, settings.show_line_numbers)
    text_x = margin.left + line_num_width
    max_text_width = page_width - margin.left - margin.right - line_num_width
    line_height = font_size * settings.line_spacing

    pages: list[PageLayout] = []
    current_page_lines: list[PageLine] = []
    current_y = page_height - margin.top - font_size

    for source_line_idx, line_content in enumerate(source_lines, 1):
        inline_anns = [
            a for a in annotations if a.line == source_line_idx and a.type == "text" and a.position == "inline"
        ]
        if inline_anns:
            current_y -= (8 * len(inline_anns) + 4)

        segments = wrap_line(line_content, font_name, font_size, max_text_width)
        for seg_idx, seg in enumerate(segments):
            if current_y < margin.bottom:
                pages.append(
                    _build_page_layout(
                        page_lines=current_page_lines,
                        annotations=annotations,
                        settings=settings,
                        font_name=font_name,
                        font_size=font_size,
                        margin=margin,
                        page_width=page_width,
                        page_height=page_height,
                        text_x=text_x,
                    )
                )
                current_page_lines = []
                current_y = page_height - margin.top - font_size
                if seg_idx == 0 and inline_anns:
                    current_y -= (8 * len(inline_anns) + 4)

            if seg_idx == 0 and settings.show_line_numbers:
                line_num_str = f"{source_line_idx:>{len(str(total_lines))}}: "
            else:
                line_num_str = " " * (len(str(total_lines)) + 2) if settings.show_line_numbers else ""

            current_page_lines.append(
                PageLine(
                    text=seg.text,
                    line_num_str=line_num_str,
                    source_line_num=source_line_idx,
                    char_start=seg.char_start,
                    char_end=seg.char_end,
                    x=text_x,
                    y=current_y,
                )
            )
            current_y -= line_height

    if current_page_lines:
        pages.append(
            _build_page_layout(
                page_lines=current_page_lines,
                annotations=annotations,
                settings=settings,
                font_name=font_name,
                font_size=font_size,
                margin=margin,
                page_width=page_width,
                page_height=page_height,
                text_x=text_x,
            )
        )

    return RenderLayout(
        pages=pages,
        text_x=text_x,
        page_width=page_width,
        page_height=page_height,
    )

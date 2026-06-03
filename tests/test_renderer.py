"""Tests for annotator renderer, layout, and draw modules."""

from types import SimpleNamespace

from annotator.config import RenderConfig
from annotator import draw as draw_module
from annotator import layout as layout_module
from annotator import renderer as renderer_module


def _minimal_config(**overrides) -> RenderConfig:
    data = {
        "settings": {
            "page_size": "A4",
            "orientation": "portrait",
            "font_size": 10,
            "line_spacing": 1.0,
            "margin": {"top": 10, "bottom": 10, "left": 10, "right": 40},
            "show_line_numbers": True,
            "show_filename": True,
            "show_page_numbers": True,
        },
        "annotations": [],
    }
    data.update(overrides)
    return RenderConfig.model_validate(data)


def test_render_pdf_uses_default_font_and_delegates(monkeypatch, tmp_path):
    calls = {}

    monkeypatch.setattr(renderer_module, "ensure_font_loaded", lambda: None)
    monkeypatch.setattr(
        renderer_module,
        "build_render_layout",
        lambda source_text, config, font_name: SimpleNamespace(
            pages=[object(), object()], source_text=source_text, config=config, font_name=font_name
        ),
    )

    def fake_draw_render_layout(layout, settings, font_name, output_path, filename):
        calls["layout"] = layout
        calls["settings"] = settings
        calls["font_name"] = font_name
        calls["output_path"] = output_path
        calls["filename"] = filename

    monkeypatch.setattr(renderer_module, "draw_render_layout", fake_draw_render_layout)

    config = _minimal_config()
    output_path = tmp_path / "out.pdf"
    renderer_module.render_pdf("hello", config, str(output_path), filename="sample.txt")

    assert calls["font_name"] == renderer_module.DEFAULT_CID_FONT
    assert calls["output_path"] == str(output_path)
    assert calls["filename"] == "sample.txt"
    assert calls["layout"].font_name == renderer_module.DEFAULT_CID_FONT


def test_render_pdf_uses_loaded_font(monkeypatch, tmp_path):
    calls = {}

    monkeypatch.setattr(renderer_module, "ensure_font_loaded", lambda: "MPLUS1Code")
    monkeypatch.setattr(
        renderer_module,
        "build_render_layout",
        lambda source_text, config, font_name: SimpleNamespace(pages=[object()], font_name=font_name),
    )
    monkeypatch.setattr(
        renderer_module,
        "draw_render_layout",
        lambda layout, settings, font_name, output_path, filename: calls.update(
            layout=layout, font_name=font_name, output_path=output_path, filename=filename
        ),
    )

    config = _minimal_config()
    output_path = tmp_path / "out.pdf"
    renderer_module.render_pdf("hello", config, str(output_path))

    assert calls["font_name"] == "MPLUS1Code"
    assert calls["layout"].font_name == "MPLUS1Code"


def test_build_render_layout_creates_pages_and_margin_comments(monkeypatch):
    monkeypatch.setattr(layout_module.pdfmetrics, "stringWidth", lambda text, font_name, font_size: len(text))

    config = _minimal_config(
        annotations=[
            {
                "line": 1,
                "col_start": 2,
                "col_end": 3,
                "type": "highlight",
                "color": "#FF0000",
                "opacity": 0.5,
            },
            {
                "line": 1,
                "col_start": 1,
                "col_end": 2,
                "type": "text",
                "position": "inline",
                "content": "note",
            },
            {
                "line": 1,
                "col_start": 1,
                "col_end": 2,
                "type": "text",
                "position": "margin",
                "content": "margin note",
            },
        ]
    )

    layout = layout_module.build_render_layout("abcd", config, font_name="FakeFont")

    assert layout.page_width > 0
    assert layout.page_height > 0
    assert layout.text_x == 18
    assert len(layout.pages) == 1

    page = layout.pages[0]
    assert len(page.lines) == 1
    assert page.lines[0].line_num_str == "1: "
    assert len(page.highlights) == 1
    assert page.highlights[0].width == 2
    assert len(page.inline_annotations) == 1
    assert page.inline_annotations[0].text == "note"
    assert len(page.margin_comments) == 1
    assert page.margin_comments[0].annotation.content == "margin note"


def test_draw_render_layout_creates_canvas_and_saves(monkeypatch, tmp_path):
    events = []
    monkeypatch.setattr(draw_module.pdfmetrics, "stringWidth", lambda text, font_name, font_size: len(text))

    class FakeCanvas:
        def __init__(self, output_path, pagesize):
            events.append(("canvas", output_path, pagesize))

        def saveState(self):
            events.append(("saveState",))

        def restoreState(self):
            events.append(("restoreState",))

        def setFillColor(self, value):
            events.append(("setFillColor", value))

        def setFillAlpha(self, value):
            events.append(("setFillAlpha", value))

        def rect(self, *args, **kwargs):
            events.append(("rect", args, kwargs))

        def setFont(self, *args, **kwargs):
            events.append(("setFont", args, kwargs))

        def drawString(self, *args, **kwargs):
            events.append(("drawString", args, kwargs))

        def setLineWidth(self, *args, **kwargs):
            events.append(("setLineWidth", args, kwargs))

        def setStrokeColor(self, *args, **kwargs):
            events.append(("setStrokeColor", args, kwargs))

        def roundRect(self, *args, **kwargs):
            events.append(("roundRect", args, kwargs))

        def line(self, *args, **kwargs):
            events.append(("line", args, kwargs))

        def circle(self, *args, **kwargs):
            events.append(("circle", args, kwargs))

        def showPage(self):
            events.append(("showPage",))

        def save(self):
            events.append(("save",))

    monkeypatch.setattr(draw_module.canvas, "Canvas", FakeCanvas)

    config = _minimal_config()
    page_layout = layout_module.PageLayout(
        lines=[layout_module.PageLine("abc", "1: ", 1, 0, 3, 10, 20)],
        highlights=[],
        inline_annotations=[],
        margin_comments=[],
    )
    render_layout = layout_module.RenderLayout(
        pages=[page_layout],
        text_x=10,
        page_width=100,
        page_height=200,
    )

    draw_module.draw_render_layout(
        render_layout,
        config.settings,
        font_name="FakeFont",
        output_path=str(tmp_path / "out.pdf"),
        filename="sample.txt",
    )

    assert events[0][0] == "canvas"
    assert events[-2][0] == "showPage"
    assert events[-1][0] == "save"

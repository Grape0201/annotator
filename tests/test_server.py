"""Tests for annotator/server.py."""

import os

import pytest
from fastapi.testclient import TestClient

from annotator.server import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MINIMAL_TEXT = "Hello, world!"
MINIMAL_CONFIG_YAML = ""


def _render_payload(
    text: str = MINIMAL_TEXT,
    config_yaml: str = MINIMAL_CONFIG_YAML,
    filename: str | None = "test.txt",
) -> dict:
    return {"text": text, "config_yaml": config_yaml, "filename": filename}


def _fake_render_pdf(source_text, config, output_path, filename):
    """Writes a minimal dummy PDF so FileResponse can read it."""
    with open(output_path, "wb") as f:
        f.write(b"%PDF-1.4 dummy")


# ---------------------------------------------------------------------------
# POST /api/render – success cases
# ---------------------------------------------------------------------------


class TestRenderApiSuccess:
    # render_pdf is imported locally inside render_api(), so we patch the
    # original definition in annotator.renderer rather than annotator.server.
    def test_returns_pdf_content_type(self, mocker):
        mocker.patch("annotator.renderer.render_pdf", side_effect=_fake_render_pdf)
        resp = client.post("/api/render", json=_render_payload())
        assert resp.status_code == 200
        assert "application/pdf" in resp.headers["content-type"]

    def test_returns_binary_body(self, mocker):
        mocker.patch("annotator.renderer.render_pdf", side_effect=_fake_render_pdf)
        resp = client.post("/api/render", json=_render_payload())
        assert len(resp.content) > 0

    def test_content_disposition_filename(self, mocker):
        mocker.patch("annotator.renderer.render_pdf", side_effect=_fake_render_pdf)
        resp = client.post("/api/render", json=_render_payload())
        assert "annotated.pdf" in resp.headers.get("content-disposition", "")

    def test_render_pdf_called_with_correct_args(self, mocker):
        mock = mocker.patch(
            "annotator.renderer.render_pdf", side_effect=_fake_render_pdf
        )
        payload = _render_payload(text="Sample text", filename="myfile.py")
        client.post("/api/render", json=payload)
        mock.assert_called_once()
        call_kwargs = mock.call_args.kwargs
        assert call_kwargs["source_text"] == "Sample text"
        assert call_kwargs["filename"] == "myfile.py"

    def test_none_filename_falls_back_to_default(self, mocker):
        mock = mocker.patch(
            "annotator.renderer.render_pdf", side_effect=_fake_render_pdf
        )
        payload = _render_payload(filename=None)
        resp = client.post("/api/render", json=payload)
        assert resp.status_code == 200
        call_kwargs = mock.call_args.kwargs
        # server falls back to "output.pdf" when filename is None
        assert call_kwargs["filename"] == "output.pdf"

    def test_with_valid_config_yaml(self, mocker):
        mocker.patch("annotator.renderer.render_pdf", side_effect=_fake_render_pdf)
        config_yaml = "settings:\n  font_size: 12\n  page_size: A4\n"
        resp = client.post("/api/render", json=_render_payload(config_yaml=config_yaml))
        assert resp.status_code == 200

    def test_with_annotation_in_config(self, mocker):
        mocker.patch("annotator.renderer.render_pdf", side_effect=_fake_render_pdf)
        config_yaml = (
            "annotations:\n"
            "  - line: 1\n"
            "    type: text\n"
            "    content: Note here\n"
        )
        resp = client.post("/api/render", json=_render_payload(config_yaml=config_yaml))
        assert resp.status_code == 200

    def test_temp_file_cleaned_up(self, mocker):
        """Temp PDF file should not persist after the response is consumed."""
        captured_path: list[str] = []

        def capturing_render(source_text, config, output_path, filename):
            captured_path.append(output_path)
            _fake_render_pdf(source_text, config, output_path, filename)

        mocker.patch("annotator.renderer.render_pdf", side_effect=capturing_render)
        client.post("/api/render", json=_render_payload())

        assert len(captured_path) == 1
        assert not os.path.exists(captured_path[0]), (
            "Temporary PDF file was not cleaned up after the response."
        )


# ---------------------------------------------------------------------------
# POST /api/render – error cases
# ---------------------------------------------------------------------------


class TestRenderApiErrors:
    def test_invalid_yaml_returns_400(self):
        bad_yaml = "settings: [\nunclosed"
        resp = client.post("/api/render", json=_render_payload(config_yaml=bad_yaml))
        assert resp.status_code == 400
        assert "YAML" in resp.json()["detail"]

    def test_invalid_config_schema_returns_400(self):
        # page_size must be 'A4' or 'LETTER'
        bad_config = "settings:\n  page_size: INVALID_SIZE\n"
        resp = client.post("/api/render", json=_render_payload(config_yaml=bad_config))
        assert resp.status_code == 400

    def test_missing_text_field_returns_422(self):
        resp = client.post("/api/render", json={"config_yaml": ""})
        assert resp.status_code == 422

    def test_renderer_exception_returns_500(self, mocker):
        mocker.patch(
            "annotator.renderer.render_pdf", side_effect=RuntimeError("render boom")
        )
        resp = client.post("/api/render", json=_render_payload())
        assert resp.status_code == 500
        assert "PDF Generation failed" in resp.json()["detail"]

    def test_temp_file_cleaned_up_on_error(self, mocker):
        """Temp PDF file must be removed even when renderer raises an exception."""
        captured_path: list[str] = []

        def side_effect(source_text, config, output_path, filename):
            # Create the file so the cleanup code can find it
            open(output_path, "wb").close()
            captured_path.append(output_path)
            raise RuntimeError("render boom")

        mocker.patch("annotator.renderer.render_pdf", side_effect=side_effect)
        client.post("/api/render", json=_render_payload())

        assert len(captured_path) == 1
        assert not os.path.exists(captured_path[0]), (
            "Temporary PDF file was not removed after a render error."
        )

    def test_annotation_col_end_less_than_col_start_returns_400(self):
        bad_config = (
            "annotations:\n"
            "  - line: 1\n"
            "    type: text\n"
            "    content: test\n"
            "    col_start: 5\n"
            "    col_end: 2\n"  # invalid: col_end < col_start
        )
        resp = client.post("/api/render", json=_render_payload(config_yaml=bad_config))
        assert resp.status_code == 400

    def test_text_annotation_without_content_returns_400(self):
        bad_config = (
            "annotations:\n"
            "  - line: 1\n"
            "    type: text\n"
            "    content: ''\n"  # empty content is invalid for type=text
        )
        resp = client.post("/api/render", json=_render_payload(config_yaml=bad_config))
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# GET / – UI endpoint
# ---------------------------------------------------------------------------


class TestGetUi:
    def test_missing_index_html_returns_404(self, tmp_path, monkeypatch):
        """When static/index.html does not exist the endpoint returns 404."""
        import annotator.server as server_module

        monkeypatch.setattr(server_module, "STATIC_DIR", str(tmp_path))
        resp = client.get("/")
        assert resp.status_code == 404

    def test_existing_index_html_returns_200(self, tmp_path, monkeypatch):
        """When static/index.html exists the endpoint serves it."""
        import annotator.server as server_module

        index = tmp_path / "index.html"
        index.write_text("<html><body>Hello</body></html>")
        monkeypatch.setattr(server_module, "STATIC_DIR", str(tmp_path))
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

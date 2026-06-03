import os
import urllib.request
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont

from .config import RenderConfig
from .draw import draw_render_layout
from .layout import build_render_layout

FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/mplus1code/MPLUS1Code%5Bwght%5D.ttf"
DEFAULT_CID_FONT = "HeiseiKakuGo-W5"

try:
    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))
    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
except Exception as e:
    print(f"Warning: Failed to register Japanese CID fonts: {e}")

def get_cache_dir():
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        return os.path.join(base, "annotator", "Cache")
    else:
        base = os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))
        return os.path.join(base, "annotator")

def ensure_font_loaded() -> str | None:
    """Ensure that the M PLUS 1 Code monospace CJK font is downloaded and registered."""
    cache_dir = get_cache_dir()
    os.makedirs(cache_dir, exist_ok=True)
    font_path = os.path.join(cache_dir, "MPLUS1Code-Regular.ttf")
    
    # Try downloading if not exists
    if not os.path.exists(font_path):
        try:
            print("Downloading monospace CJK font (M PLUS 1 Code) from Google Fonts...")
            urllib.request.urlretrieve(FONT_URL, font_path)
            print("Download complete!")
        except Exception as e:
            print(f"Warning: Failed to download monospace CJK font: {e}")
            if os.path.exists(font_path):
                try:
                    os.remove(font_path)
                except:  # noqa: E722
                    pass
            return None
            
    # Try registering font in ReportLab
    try:
        pdfmetrics.registerFont(TTFont("MPLUS1Code", font_path))
        return "MPLUS1Code"
    except Exception as e:
        print(f"Warning: Failed to register MPLUS1Code font: {e}")
        return None


def render_pdf(source_text: str, config: RenderConfig, output_path: str, filename: str = "source.txt"):
    settings = config.settings
    font_name = ensure_font_loaded() or DEFAULT_CID_FONT
    layout = build_render_layout(source_text, config, font_name)
    draw_render_layout(layout, settings, font_name, output_path, filename)
    print(f"Successfully generated annotated PDF: {output_path} (Pages: {len(layout.pages)})")

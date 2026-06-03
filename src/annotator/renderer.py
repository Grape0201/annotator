import os
import yaml
import urllib.request
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter, A4

# Font Constants
FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/mplus1code/MPLUS1Code%5Bwght%5D.ttf"
DEFAULT_CID_FONT = 'HeiseiKakuGo-W5'

# Register standard Japanese CID fonts (no embedding needed, fallback)
try:
    pdfmetrics.registerFont(UnicodeCIDFont('HeiseiMin-W3'))
    pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
except Exception as e:
    print(f"Warning: Failed to register Japanese CID fonts: {e}")

def get_cache_dir():
    if os.name == 'nt':
        base = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
        return os.path.join(base, 'annotator', 'Cache')
    else:
        base = os.environ.get('XDG_CACHE_HOME', os.path.expanduser('~/.cache'))
        return os.path.join(base, 'annotator')

def ensure_font_loaded():
    """Ensure that the M PLUS 1 Code monospace CJK font is downloaded and registered."""
    cache_dir = get_cache_dir()
    os.makedirs(cache_dir, exist_ok=True)
    font_path = os.path.join(cache_dir, "MPLUS1Code-Regular.ttf")
    
    # Try downloading if not exists
    if not os.path.exists(font_path):
        try:
            print(f"Downloading monospace CJK font (M PLUS 1 Code) from Google Fonts...")
            urllib.request.urlretrieve(FONT_URL, font_path)
            print("Download complete!")
        except Exception as e:
            print(f"Warning: Failed to download monospace CJK font: {e}")
            if os.path.exists(font_path):
                try:
                    os.remove(font_path)
                except:
                    pass
            return None
            
    # Try registering font in ReportLab
    try:
        pdfmetrics.registerFont(TTFont('MPLUS1Code', font_path))
        return 'MPLUS1Code'
    except Exception as e:
        print(f"Warning: Failed to register MPLUS1Code font: {e}")
        return None


def hex_to_color(hex_str, default="#000000"):
    try:
        return HexColor(hex_str)
    except Exception:
        return HexColor(default)

def wrap_comment_text(text, font_name, font_size, max_width):
    """Wrap comment text to fit within max_width. Handles Japanese char-by-char wrapping."""
    words = text.split()
    # Check if it looks like CJK text (no spaces, containing high code points)
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
    else:
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

def wrap_line(line_text, font_name, font_size, max_text_width):
    """Wrap a single source line to fit max_text_width."""
    segments = []
    current_segment = ""
    current_width = 0
    char_start = 0
    
    # Standard stringWidth check
    for idx, char in enumerate(line_text):
        char_width = pdfmetrics.stringWidth(char, font_name, font_size)
        if current_width + char_width > max_text_width and current_segment:
            segments.append({
                "text": current_segment,
                "char_start": char_start,
                "char_end": idx
            })
            current_segment = char
            current_width = char_width
            char_start = idx
        else:
            current_segment += char
            current_width += char_width
            
    # Always append the remainder
    segments.append({
        "text": current_segment,
        "char_start": char_start,
        "char_end": len(line_text)
    })
    return segments

def render_pdf(source_text: str, config_data: dict, output_path: str, filename: str = "source.txt"):
    """
    Renders source text as a monospace PDF with annotations applied.
    """
    # Replace tabs with spaces
    source_text = source_text.replace('\t', '    ')
    
    # 1. Parse settings & merge with defaults
    settings = config_data.get("settings", {})
    page_size_str = settings.get("page_size", "A4").upper()
    orientation = settings.get("orientation", "portrait").lower()
    font_size = settings.get("font_size", 9)
    line_spacing = settings.get("line_spacing", 1.3)
    
    margin_config = settings.get("margin", {})
    margin_top = margin_config.get("top", 50)
    margin_bottom = margin_config.get("bottom", 50)
    margin_left = margin_config.get("left", 50)
    margin_right = margin_config.get("right", 180)
    
    show_line_numbers = settings.get("show_line_numbers", True)
    show_filename = settings.get("show_filename", True)
    show_page_numbers = settings.get("show_page_numbers", True)
    
    # Page dimensions setup
    base_size = A4 if page_size_str == "A4" else letter
    if orientation == "landscape":
        page_width, page_height = base_size[1], base_size[0]
    else:
        page_width, page_height = base_size[0], base_size[1]
        
    font_name = ensure_font_loaded() or DEFAULT_CID_FONT
    line_height = font_size * line_spacing
    
    # Parse source lines
    source_lines = source_text.splitlines()
    total_lines = len(source_lines)
    
    # Calculate line numbers column width
    line_num_width_chars = len(str(total_lines))
    if show_line_numbers:
        line_num_prefix_example = "0" * line_num_width_chars + ": "
        line_num_width = pdfmetrics.stringWidth(line_num_prefix_example, font_name, font_size) + 5
    else:
        line_num_width = 0
        
    text_x = margin_left + line_num_width
    max_text_width = page_width - margin_left - margin_right - line_num_width
    
    # Gather annotations
    annotations = config_data.get("annotations", [])
    
    # 2. Layout execution phase
    pages = []
    current_page_lines = []
    current_y = page_height - margin_top - font_size
    
    for source_line_idx, line_content in enumerate(source_lines, 1):
        # Check if this line has any inline annotations.
        # If it does, we add extra spacing BEFORE the line to make room for inline text comments.
        inline_anns = [a for a in annotations if a.get("line") == source_line_idx and a.get("type") == "text" and a.get("position") == "inline"]
        if inline_anns:
            # Shift down to reserve 10 points space for the inline text comment
            current_y -= (8 * len(inline_anns) + 4)
            
        segments = wrap_line(line_content, font_name, font_size, max_text_width)
        for seg_idx, seg in enumerate(segments):
            # Check page overflow
            if current_y < margin_bottom:
                pages.append(current_page_lines)
                current_page_lines = []
                current_y = page_height - margin_top - font_size
                # If overflow occurred and we shifted for inline annotations, apply spacing on new page too if line starts
                if seg_idx == 0 and inline_anns:
                    current_y -= (8 * len(inline_anns) + 4)
                    
            if seg_idx == 0 and show_line_numbers:
                line_num_str = f"{source_line_idx:>{line_num_width_chars}}: "
            else:
                line_num_str = " " * (line_num_width_chars + 2) if show_line_numbers else ""
                
            current_page_lines.append({
                "text": seg["text"],
                "line_num_str": line_num_str,
                "source_line_num": source_line_idx,
                "char_start": seg["char_start"],
                "char_end": seg["char_end"],
                "x": text_x,
                "y": current_y,
                "inline_annotations": inline_anns if seg_idx == 0 else []
            })
            current_y -= line_height
            
    if current_page_lines:
        pages.append(current_page_lines)
        
    # 3. Canvas rendering phase
    c = canvas.Canvas(output_path, pagesize=(page_width, page_height))
    total_pages = len(pages)
    
    for page_idx, page_lines in enumerate(pages, 1):
        # Draw Highlights (under the text)
        for line_item in page_lines:
            source_line = line_item["source_line_num"]
            char_start = line_item["char_start"]
            char_end = line_item["char_end"]
            y = line_item["y"]
            
            # Find annotations that overlap with this segment
            for ann in annotations:
                if ann.get("line") != source_line:
                    continue
                    
                target_start = ann.get("col_start", 1) - 1
                target_end = ann.get("col_end", 1)
                
                # Check character overlap
                overlap_start = max(target_start, char_start)
                overlap_end = min(target_end, char_end)
                
                if overlap_start < overlap_end:
                    s_idx = overlap_start - char_start
                    e_idx = overlap_end - char_start
                    
                    x_start = text_x + pdfmetrics.stringWidth(line_item["text"][:s_idx], font_name, font_size)
                    x_end = text_x + pdfmetrics.stringWidth(line_item["text"][:e_idx], font_name, font_size)
                    
                    rect_x = x_start
                    rect_width = x_end - x_start
                    rect_y = y - (font_size * (line_spacing - 1) / 2)
                    rect_height = font_size * line_spacing
                    
                    # Highlight style defaults
                    color_hex = ann.get("color", "#FFD700")
                    opacity = ann.get("opacity", 0.4)
                    
                    c.saveState()
                    c.setFillColor(hex_to_color(color_hex))
                    c.setFillAlpha(opacity)
                    c.rect(rect_x, rect_y, rect_width, rect_height, fill=1, stroke=0)
                    c.restoreState()
                    
        # Draw Source Text
        c.setFont(font_name, font_size)
        c.setFillColor(HexColor("#333333"))
        for line_item in page_lines:
            # Draw line number if config requires it
            if show_line_numbers and line_item["line_num_str"].strip():
                c.saveState()
                c.setFillColor(HexColor("#888888"))
                c.drawString(margin_left, line_item["y"], line_item["line_num_str"])
                c.restoreState()
                
            c.drawString(line_item["x"], line_item["y"], line_item["text"])
            
        # Draw Inline Text Annotations (above target range)
        for line_item in page_lines:
            for ann in line_item["inline_annotations"]:
                target_start = ann.get("col_start", 1) - 1
                target_end = ann.get("col_end", 1)
                
                # Find visual center of the range in the first segment
                s_idx = min(max(target_start - line_item["char_start"], 0), len(line_item["text"]))
                e_idx = min(max(target_end - line_item["char_start"], 0), len(line_item["text"]))
                
                x_start = text_x + pdfmetrics.stringWidth(line_item["text"][:s_idx], font_name, font_size)
                x_end = text_x + pdfmetrics.stringWidth(line_item["text"][:e_idx], font_name, font_size)
                
                center_x = (x_start + x_end) / 2
                comment_text = ann.get("content", "")
                
                c.saveState()
                c.setFont(font_name, 7)
                c.setFillColor(hex_to_color(ann.get("color", "#3182CE")))
                
                # Center-align comment
                text_w = pdfmetrics.stringWidth(comment_text, font_name, 7)
                draw_x = max(center_x - text_w / 2, margin_left)
                draw_y = line_item["y"] + font_size + 2
                
                c.drawString(draw_x, draw_y, comment_text)
                c.restoreState()

        # Draw Right Margin Callouts
        page_annotations = []
        for ann in annotations:
            if ann.get("type") == "text" and ann.get("position", "margin") == "margin":
                # Check if the line of this annotation is rendered on this page
                if any(item["source_line_num"] == ann.get("line") for item in page_lines):
                    page_annotations.append(ann)
                    
        # Process and lay out right margin comments
        box_width = margin_right - 30
        box_x = page_width - margin_right + 15
        
        comments_to_draw = []
        for ann in page_annotations:
            # Find exact position of the annotation target in page lines
            target_line = ann.get("line")
            target_start = ann.get("col_start", 1) - 1
            target_end = ann.get("col_end", 1)
            
            target_y = None
            target_x_start = None
            target_x_end = None
            
            for item in page_lines:
                if item["source_line_num"] == target_line:
                    # Prefer the segment containing the col_start
                    if item["char_start"] <= target_start <= item["char_end"]:
                        target_y = item["y"]
                        s_idx = target_start - item["char_start"]
                        e_idx = min(target_end, item["char_end"]) - item["char_start"]
                        target_x_start = item["x"] + pdfmetrics.stringWidth(item["text"][:s_idx], font_name, font_size)
                        target_x_end = item["x"] + pdfmetrics.stringWidth(item["text"][:e_idx], font_name, font_size)
                        break
                        
            # Fallback if start col is not in segments
            if target_y is None:
                for item in page_lines:
                    if item["source_line_num"] == target_line:
                        target_y = item["y"]
                        target_x_start = item["x"]
                        target_x_end = item["x"] + pdfmetrics.stringWidth(item["text"], font_name, font_size)
                        break
                        
            if target_y is not None:
                c_lines = wrap_comment_text(ann.get("content", ""), font_name, 8, box_width - 16)
                b_height = len(c_lines) * 9.6 + 16 # 8pt top & bottom padding
                
                comments_to_draw.append({
                    "annotation": ann,
                    "lines": c_lines,
                    "height": b_height,
                    "target_y": target_y,
                    "target_x_start": target_x_start,
                    "target_x_end": target_x_end,
                    "y_ideal": target_y + font_size / 2
                })
                
        # Collision avoidance for margin comment positioning
        if comments_to_draw:
            # Sort highest ideal y first (top of page down)
            comments_to_draw.sort(key=lambda c: c["y_ideal"], reverse=True)
            
            # Pass 1: Top-to-bottom push-down
            current_top = page_height - margin_top
            for item in comments_to_draw:
                item_top = min(item["y_ideal"] + item["height"]/2, current_top)
                item["y_top"] = item_top
                item["y_bottom"] = item_top - item["height"]
                current_top = item["y_bottom"] - 8 # 8pt spacing
                
            # Pass 2: Bottom-to-top push-up
            if comments_to_draw[-1]["y_bottom"] < margin_bottom:
                current_bottom = margin_bottom
                for item in reversed(comments_to_draw):
                    if item["y_bottom"] < current_bottom:
                        diff = current_bottom - item["y_bottom"]
                        item["y_bottom"] += diff
                        item["y_top"] += diff
                    current_bottom = item["y_top"] + 8
                    
            # Draw comments and connector lines
            for item in comments_to_draw:
                ann = item["annotation"]
                bg_color = ann.get("bg_color", "#FFF5F5")
                border_color = ann.get("color", "#E53E3E")
                text_color = ann.get("color", "#E53E3E")
                
                y_top = item["y_top"]
                y_bottom = item["y_bottom"]
                h = item["height"]
                
                c.saveState()
                c.setLineWidth(0.75)
                c.setStrokeColor(hex_to_color(border_color))
                c.setFillColor(hex_to_color(bg_color))
                # Draw rounded rectangle for the comment card
                c.roundRect(box_x, y_bottom, box_width, h, 4, fill=1, stroke=1)
                
                # Draw comment text lines
                c.setFillColor(hex_to_color(text_color))
                c.setFont(font_name, 8)
                text_y = y_top - 8 - 6 # 8pt top padding + line baseline adjust
                for cl in item["lines"]:
                    c.drawString(box_x + 8, text_y, cl)
                    text_y -= 9.6
                c.restoreState()
                
                # Draw connector line
                c.saveState()
                c.setStrokeColor(hex_to_color(border_color))
                c.setLineWidth(0.5)
                # Line goes from right end of highlighted range to center-left of the callout card
                cx1 = item["target_x_end"]
                cy1 = item["target_y"] + font_size / 2
                cx2 = box_x
                cy2 = (y_top + y_bottom) / 2
                
                c.line(cx1, cy1, cx2, cy2)
                # Small terminal dot on the highlighted text
                c.setFillColor(hex_to_color(border_color))
                c.circle(cx1, cy1, 1.5, fill=1, stroke=0)
                c.restoreState()

        # Draw Header
        if show_filename:
            c.saveState()
            c.setFont(font_name, 8)
            c.setFillColor(HexColor("#888888"))
            c.drawString(margin_left, page_height - margin_top + 15, filename)
            # Draw line divider
            c.setStrokeColor(HexColor("#DDDDDD"))
            c.setLineWidth(0.5)
            c.line(margin_left, page_height - margin_top + 10, page_width - margin_left, page_height - margin_top + 10)
            c.restoreState()
            
        # Draw Footer
        if show_page_numbers:
            c.saveState()
            c.setFont(font_name, 8)
            c.setFillColor(HexColor("#888888"))
            page_str = f"{page_idx} / {total_pages}"
            # Right align page number
            text_w = pdfmetrics.stringWidth(page_str, font_name, 8)
            c.drawString(page_width - margin_left - text_w, margin_bottom - 20, page_str)
            # Draw divider line
            c.setStrokeColor(HexColor("#DDDDDD"))
            c.setLineWidth(0.5)
            c.line(margin_left, margin_bottom - 10, page_width - margin_left, margin_bottom - 10)
            c.restoreState()
            
        c.showPage()
        
    c.save()
    print(f"Successfully generated annotated PDF: {output_path} (Pages: {total_pages})")

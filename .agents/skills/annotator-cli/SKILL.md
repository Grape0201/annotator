---
name: annotator-cli
description: Annotator CLI skill for rendering annotated PDFs from text and YAML configuration using the `annotator` command.
---

# Annotator CLI

Use this skill when working with the command-line `annotator` tool to generate annotated PDF documents from plaintext input and YAML annotation settings.

## Use the `annotator` CLI

Render a text file to PDF with optional annotation configuration:

```bash
annotator render source.txt --config annotation.yaml --output output.pdf
```

- `source.txt`: the plain text source file.
- `--config annotation.yaml` or `-c annotation.yaml`: YAML file containing global settings and annotation definitions.
- `--output output.pdf` or `-o output.pdf`: destination PDF path.

### Command behavior

- If `--config` is omitted, default rendering settings are used.
- The CLI reads text in UTF-8 and supports Japanese text rendering.
- The output file is a PDF with the rendered text, highlights, margins, and annotation callouts.

## Example usage

```bash
annotator render example/input.txt --config example/config.yaml --output result.pdf
```

If validation of the YAML config fails, the command exits with a descriptive error.

## Configuration file pattern

The annotation YAML supports:
- `settings`: page size, orientation, font size, margins, line spacing, header/footer options.
- `annotations`: highlight and text-note definitions.

Example:

```yaml
settings:
  page_size: A4
  orientation: portrait
  font_size: 9
  line_spacing: 1.3
  margin:
    top: 50
    bottom: 50
    left: 50
    right: 180
  show_line_numbers: true
  show_filename: true
  show_page_numbers: true
annotations:
  - line: 12
    col_start: 5
    col_end: 15
    type: highlight
    color: "#FFD700"
    opacity: 0.4
  - line: 15
    col_start: 10
    col_end: 20
    type: text
    content: "ここでエラー処理を行う必要があります。"
    position: margin
    color: "#E53E3E"
    bg_color: "#FFF5F5"
```

## Best practices

- Use a wider right margin when you plan to place text annotations in the margin.
- Keep line length moderate so annotations align cleanly with the target text.
- Validate YAML syntax before rendering to avoid startup errors.

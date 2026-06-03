---
name: annotator-api
description: Annotator API skill for `/api/render` HTTP integration, including request fields and YAML annotation format.
---

# Annotator API

Use this skill when integrating with the Annotator API via its HTTP endpoint.

## POST `/api/render`

Use a placeholder endpoint to document the expected API contract. Replace `http://api.example.com` with the real server URL.

```bash
curl -X POST http://api.example.com/api/render \
  -H "Content-Type: application/json" \
  -H "Accept: application/pdf" \
  -d '{
    "text": "Example text content...",
    "config_yaml": "settings:\n  page_size: A4\n  orientation: portrait\nannotations: []\n",
    "filename": "source.txt"
  }' --output annotated.pdf
```

Request fields:
- `text`: plain text content to render.
- `config_yaml`: annotation settings and annotations as raw YAML string.
- `filename`: optional display filename used in the PDF header.

#### `config_yaml` details

The `config_yaml` string must contain a YAML document with two top-level sections:

- `settings`: global rendering options such as `page_size`, `orientation`, `font_size`, `line_spacing`, and `margin`.
- `annotations`: a list of annotation objects.

There are three supported annotation types:

1. `highlight`: mark a text span with a colored background.
2. `text` with `position: margin`: place a note in the margin and connect it to the target text.
3. `text` with `position: inline`: insert an inline text note in the line spacing.

Example structure:

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
    position: margin
    content: "ここでエラー処理を行う必要があります。"
    color: "#E53E3E"
    bg_color: "#FFF5F5"
```

### Response

- Returns `application/pdf` with the generated annotated document.
- The returned file is typically downloaded or saved as the client-specified output file.

## Common integration patterns

- Use the API to render local text files that are converted into request payloads.
- Embed `config_yaml` as a YAML string when the client cannot provide a direct file upload.
- Validate YAML syntax before sending the request to avoid server-side errors.

## Error handling

- Invalid YAML syntax should return HTTP 400 with a descriptive error message.
- Configuration validation failures should return HTTP 400.
- PDF generation issues should return HTTP 500.

# Annotator

テキストファイル（ASCII/UTF-8）を入力とし、指定された箇所にハイライトやテキスト注記（アノテーション）を追加したビジュアルなPDFファイルを生成するコマンドラインツールおよびAPIサーバです。

## 特徴

- **日本語対応**: 日本語テキストの描画に対応。
- **軽量PDF**: PDFフォントを埋め込まず、標準CIDフォント（`HeiseiMin-W3`, `HeiseiKakuGo-W5`など）を使用するため、ファイルサイズが非常に軽量。
- **レイアウト崩れ・重なり防止**:
  - **ハイライト**: 文字列の背景に半透明で描画。
  - **テキスト注記**: 右側の余白エリア（マージン）に吹き出しとして配置し、対象箇所と線で結ぶデザイン（推奨）、または行間に挿入するインライン配置。
- **メタデータ・ヘッダー**: ファイル名、ページ番号、印刷方向（縦・横）、余白の設定、行番号の表示に対応。
- **CLI & Web API**: ローカルでのバッチ処理と、Web API経由での動的生成の両方をサポート。シンプルなプレビュー画面（Web UI）も内蔵。

## 入出力仕様

### 入力

1. **ソーステキストファイル** (e.g., `source.txt`): アノテーション対象のテキスト。
2. **アノテーション設定ファイル** (e.g., `annotation.yaml`):

```yaml
# グローバル設定（オプション、CLI引数でオーバーライド可能）
settings:
  page_size: A4              # A4, Letter, etc.
  orientation: portrait      # portrait, landscape
  font_size: 9               # ソーステキストのフォントサイズ
  line_spacing: 1.3          # 行間
  margin:
    top: 50
    bottom: 50
    left: 50
    right: 180               # アノテーション領域を確保するため右マージンを広めにするのがおすすめ
  show_line_numbers: true    # 行番号を表示するか
  show_filename: true        # ヘッダーにファイル名を表示するか
  show_page_numbers: true    # フッターにページ番号を表示するか

# アノテーションリスト
annotations:
  # 1. ハイライトの例
  - line: 12                 # 1から始まる行番号
    col_start: 5             # 1から始まる開始文字位置
    col_end: 15              # 終了文字位置（含む）
    type: highlight
    color: "#FFD700"         # 16進数カラーコード
    opacity: 0.4             # 不透明度 (0.0 ~ 1.0)

  # 2. テキスト注記（マージン配置）の例
  - line: 15
    col_start: 10
    col_end: 20
    type: text
    content: "ここでエラー処理を行う必要があります。"
    position: margin         # margin (右マージンに表示) または inline (行間に表示)
    color: "#E53E3E"         # 注記テキスト・枠線の色
    bg_color: "#FFF5F5"      # 吹き出し背景色

  # 3. テキスト注記（インライン）の例
  - line: 20
    col_start: 1
    col_end: 5
    type: text
    content: "TODO: リファクタリング"
    position: inline
    color: "#3182CE"
```

### 出力

- **PDFファイル**: 指定したレイアウトでアノテーションされたPDF。

## クイックスタート

### インストール (Python 3.12以上)

```bash
uv sync
```

### コマンドラインでの利用 (CLI)

```bash
# PDFの生成
annotator render source.txt --config annotation.yaml --output output.pdf
```

### APIサーバの起動

```bash
# サーバ起動 (デフォルト: http://localhost:8000)
annotator start-server --port 8000
```

- `POST /api/render`: テキストとYAMLを送り、PDFバイナリを受け取るエンドポイント。
- `GET /`: ブラウザで動的にテキストとYAMLを入力してPDFプレビューを確認できるインタラクティブUI。

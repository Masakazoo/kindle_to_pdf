# Kindle to PDF Converter

MacBook AirでKindle for Macの書籍を自動的にスクリーンショット撮影し、PDFに変換するツールです。
開発者向け（自分用）として、ブラウザベースのGUIで動作するように設計されています。

## 特徴
- **完全自動化**: ページめくりとスクリーンショット撮影を自動で行います。
- **PDF変換**: 撮影した画像を結合してPDFを作成します。
- **OCR対応**: オプションで `OCRmyPDF` (Tesseract) を使用して透明テキスト埋め込みPDFを作成可能。
- **ブラウザGUI**: Fletを使用したWeb UIで操作可能。

## 前提条件
- macOS (Apple Silicon 動作確認済み)
- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (推奨パッケージマネージャ)
- Kindle for Mac
- Tesseract & Ghostscript (OCR機能を利用する場合)

### 外部依存ツールのインストール (OCR用)
```bash
brew install tesseract tesseract-lang ghostscript
```

## インストール手順

1. リポジトリをクローン
```bash
git clone https://github.com/YOUR_USERNAME/kindle_to_pdf.git
cd kindle_to_pdf
```

2. 依存関係のインストール
```bash
uv sync
```

## 使い方

1. Kindleアプリを起動し、変換したい書籍を開いておきます。
2. アプリを起動します。
```bash
./run_web_app.sh
```
3. ブラウザが立ち上がるので、書籍名やページ数を入力して「変換開始」を押します。
4. ログに従い、Kindleウィンドウをアクティブにしてください。

## 注意事項: アクセシビリティ権限
このアプリはキーボード操作（ページめくり）を自動化するため、ターミナル（iTerm2やTerminal.app）に **「コンピュータの制御」** または **「アクセシビリティ」** 権限が必要です。
エラーが出る場合は、`システム設定 > プライバシーとセキュリティ > アクセシビリティ` から、使用しているターミナルアプリの権限を許可（または一度削除して再登録）してください。

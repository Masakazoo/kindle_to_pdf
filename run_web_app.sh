#!/bin/bash
cd "$(dirname "$0")"
# UVなどがパスに通っていない可能性を考慮し、フルパス指定または環境変数を読み込む
# ここではシンプルに uv run で実行する
if ! command -v uv &> /dev/null; then
    echo "Error: 'uv' command not found. Please install uv or make sure it's in your PATH."
    exit 1
fi

echo "Starting KindleToPDF Web App..."
echo "Press Ctrl+C to stop."
uv run python -m kindle_to_pdf.web

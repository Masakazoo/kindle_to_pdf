# Developer Setup / GitHub運用

## 概要

現時点のコードはmacOS用のKindle PDFコンバータ。Kindle Library Syncの設計資料はPR #1 (未マージ時) / docs/phase0 に置く。CodexはAGENTS.mdと関連Issueを先に読む。

## macOSローカルセットアップ

~~~sh
git clone https://github.com/Masakazoo/kindle_to_pdf.git
cd kindle_to_pdf
uv python install 3.12
uv sync --group dev
uv run ruff check .
uv run pytest -q
./run_web_app.sh
~~~

初回OCRにはbrew install tesseract tesseract-lang ghostscript が必要。既存コンバータの撮影動作にはmacOSの画面収録/アクセシビリティ権限が必要で、CIでは試験しない。

## CIの意図

- Linux lint-and-syntax: ruff + ソースのコンパイル（依存をインストールしない）。
- macOS pytest-macos: pyobjc-framework-quartzを含む依存をuv.lockでインストールしてpytest。
- **CIが通ってもKindle DBとAmazonアカウントの実機PoCや法規・利用条件チェックは未実施**。
- GitHub Actionsの初回起動/権限/分単位のコストを確認し、必要に応じてmacOSジョブを手動実行へ変更する。

## Issues / PR

- Epic: https://github.com/Masakazoo/kindle_to_pdf/issues/2
- 1 Issue = 原則1 Draft PR。小さな変更・チェック可能な受け入れ条件を持つ。
- SPIKEは根拠とGo/No-Go・手動操作箇所・匿名化された測定結果が成果。
- 完了したPRはレビュー・CIを確認してからmerge。mainに直接pushしない。
- mainの保護はGitHub Settings > Branches / Rulesetsから、PR必須・force push禁止・CI必須を設定する。単独開発者では他者承認必須の有無を運用可能性と合わせて決める。
- 保護ルールの状態を読み取るAPIで権限不足になる場合、設定が有効であると推測しない。

## セキュリティ

- .gitignoreは事故防止用であり、追跡済みファイルを自動削除しない。コミット内容を必ず確認。
- 本物のKindle DB/書籍内容、個人の購入履歴、OAuth/ブラウザ資格情報はGitHubに入れない。
- このリポジトリは公開。書籍本文や第三者著作物をCI fixtureにしない。
- Amazonの公式ダウンロード自動化はSPIKE-03で技術と規約両方を検証するまでは無効。

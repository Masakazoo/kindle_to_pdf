# Test Strategy — acceptance and failure injection

状態: Phase 0 v0.1

## 1. テストレイヤー

1. **Unit（Linux CI）**: domainの購入判定、ASIN同一性、差分アルゴリズム、状態遷移。Fake clock/Drive/Kindle/Amazon。
2. **Contract（Linux CI）**: Portの成功/部分成功/失敗、形式検証、API 409/401/403/429/5xx、マイグレーション、in-memoryおよび一時SQLite。
3. **Integration（Linux CI + mock service）**: SQLiteトランザクション、同期計画、upload idempotency、強制終了から復旧、並列起動ロック。
4. **macOS実機E2E（手動/限定自動）**: Kindle DB読み取り、OS権限、OAuth、Google Drive実フォルダ、公式DLの適切な操作、EPUB→PDF。
5. **セキュリティ**: ログにパスワード/Cookie/token/セッションURI/書籍本文が残らないこと。

## 2. 受け入れテストケース

| ID | 前提/操作 | 期待 |
|---|---|---|
| AC-01 | 100冊を2回同期 | 2回目は新規ファイル0、重複0 |
| AC-02 | ASINが1冊増加 | 新規候補1、既存台帳を変更しない |
| AC-03 | KU/サンプル/購入証拠なしを混在 | 取得対象に含めず理由表示 |
| AC-04 | 公式DL非対応 | DEFERRED_UNAVAILABLE、失敗数に入れない |
| AC-05 | ダウンロードPDF/EPUB破損 | アップロードせず元データを保持 |
| AC-06 | Drive create成功直後にプロセス停止 | 予約IDで同じファイルを検出し二重送信しない |
| AC-07 | 既存Driveファイルをリネーム/移動 | fileIdで追跡、勝手に新規作成しない |
| AC-08 | OAuth期限切れ/権限不足 | 再認証・アクセス回復導線。誤削除判定なし |
| AC-09 | 10冊中1冊だけネットワーク失敗 | 残りを継続し部分失敗として表示 |
| AC-10 | 入力ソースのスキャンが失敗 | 0冊として同期済み扱いにしない |
| AC-11 | 途中キャンセル→再開 | 完了工程を保持、整合性検査後に残りから再開 |
| AC-12 | Drive既存ファイルと同名/異ハッシュ | 明示的CONFLICT。既存を上書きしない |
| AC-13 | 全件購入ではなく一部をローカルDBのみ認識 | 網羅率不明と表示。全件済みを表示しない |
| AC-14 | ログ収集 | 秘密情報と書籍本文がない |

## 3. 障害注入パターン

- Kindle DBアクセス拒否/ファイルロック/スキーマ差異/部分スキャン。
- Amazonログイン失効/購入根拠未取得/公式DL可否の一時不明/手動操作待ち。
- Drive 401/403/404/409/429/5xx、一覧の部分ページ取得、レスポンス喪失、upload session期限切れ。
- ローカルディスク満杯、変換プロセス異常終了、PDFサイズ0、EPUB ZIP破損、チェックサム不一致。
- 完了メタデータをDB保存する前のクラッシュ、DB migration途中失敗。
- 同期ボタン連打/アプリ2プロセス同時起動、同名別ASIN。
- 親フォルダ移動、ファイルの手動削除（「権限失効」と区別）。

## 4. 品質ゲート

- domain/applicationに実機依存importがない。
- lint/型検査/単体テストがCIで実行可能。
- 状態遷移の禁止パスと冪等処理をテストで保護。
- スクリーンショット自動取得は標準同期のE2Eから除外。
- Kindle/Driveの実ユーザー情報・公式ファイル本文をfixtureとしてcommitしない。
- performance targetはPoC後に確定し、回帰ベンチマークを追加。

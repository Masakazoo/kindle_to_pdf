# Data Model & State Machine — SQLite v0.1

状態: 概念設計／PoC後にDDL確定。全タイムスタンプはUTC ISO 8601、UI表示時だけローカルタイム変換。

## 1. IDと書籍の同一性

- book_id: アプリ内部の不変UUID。UI、工程、成果物間の参照キー。
- account_id: Amazonアカウントのローカル代理ID。パスワード/メール本文/セッションはDB保存しない。
- storefront: Amazon.co.jp等のストア識別子。
- ASIN: nullを許す。book_idとは別管理。**account_id, storefront, asin** の組み合わせに部分ユニーク制約（asin is not null）。
- 同じタイトル/著者でもASINが異なれば自動統合しない。異なるアカウントの同じASINも自動統合しない。
- 公式ファイルとASINの対応が証明できない場合はユーザー確認に回す。

## 2. 概念テーブル

| テーブル | 主要カラム | 制約・目的 |
|---|---|---|
| accounts | id, storefront, account_hint_hash, created_at | アカウント/ストア境界。秘密情報を保存しない |
| books | id, account_id, storefront, asin?, title, authors_json, first_seen_at, last_seen_at | unique(account_id, storefront, asin) where asin not null |
| book_observations | id, book_id, source, source_ref?, scan_id, observed_at, payload_json | 取得元、検出日時、スキャン単位で履歴保持 |
| purchase_evidence | id, book_id, verdict, evidence_type, reference?, observed_at, provenance | 購入確認/否定/未確認を証跡ごとに記録 |
| download_options | id, book_id, format, availability, checked_at, method, reason | BOOK×形式×確認時点の公式可否 |
| artifacts | id, book_id, format, source, parent_artifact_id?, sha256, bytes, local_path, validation_state | 原本・変換物別。sha256はバイト同一性、版も区別 |
| drive_files | id, artifact_id?, drive_file_id, parent_folder_id, name, size, sha256?, md5?, last_checked_at, availability | unique(drive_file_id)、不可視と削除を区別 |
| sync_runs | id, started_at, ended_at?, status, trigger, source_health_json, counts_json | 同期セッション。triggerは初期MANUALのみ |
| sync_tasks | id, run_id, book_id?, artifact_id?, task_type, idempotency_key, status, attempts, checkpoint_json, reserved_drive_id?, error_code?, updated_at | 再試行/復旧。idempotency_keyの意味をタスク種別ごとに固定 |

各テーブルには作成/更新日時、必要な外部キーと索引を付ける。JSONは不定形取得元データやメタ情報に限定し、検索する重要状態は列として持つ。SQLiteの foreign_keys=ON、WAL、スキーママイグレーションを採用する。

## 3. 正規化された状態

### 購入判定（bookの画面用導出値）
UNVERIFIED / VERIFIED / EXCLUDED。
- ローカルDBで書籍が見えることだけではVERIFIEDにはしない。
- VERIFIEDにはAmazon購入一覧、購入証跡、ユーザー確認等のevidenceを必須にする。
- 検出元の取得失敗でVERIFIEDからEXCLUDEDに自動変更しない。
- 返品などで権利がなくなった場合は、確認根拠を保存しEXCLUDEDへ遷移可能。

### DL可否（book×format）
UNKNOWN / AVAILABLE / UNAVAILABLE。
- 未確認と「現在Amazon公式DL不可」は違う。
- 最終確認日時が古ければSTALENESSを別フラグで計算し、次回同期で再確認候補とする。
- 対象外の本のDL可否を問い合わせない。

### 成果物品質
DISCOVERED → VALIDATING → VALID / INVALID。
- EPUBならZIP構造/MIME/manifest/必要ファイルを確認。PDFならヘッダ/読めるページ/暗号化有無/頁数/レンダリング可否等を確認。
- ファイルサイズが0、途中生成、不完全なファイルはINVALID。
- EPUB→PDF変換結果は別 artifact とし、parent_artifact_idで追跡。
- OCR結果は原本に上書きしない。

### 同期タスク
QUEUED → RUNNING → VERIFIED_DONE。
例外分岐: RETRYABLE_FAILURE / BLOCKED_USER_ACTION / DEFERRED_UNAVAILABLE / TERMINAL_FAILURE / CANCELLED。
- RETRYABLE_FAILUREは適切な上限付きで再試行する。
- DEFERRED_UNAVAILABLEは不具合ではなく、購入台帳に残る業務状態。
- ネットワーク断で結果不明なら RESERVED_ID_RECONCILIATION を先行。
- 途中でアプリ終了した RUNNING は、再起動後にRECONCILINGを経由して安全な処理から再開。

### 実行結果
COMPLETED（技術エラーなし） / COMPLETED_WITH_ERRORS（部分失敗） / FAILED（開始不能等の全体失敗） / CANCELLED。
保留・要確認は各内訳に別計上する。

## 4. 冪等キーの考え方

例: upload の idempotency_key = hash(account_id + artifact_id + destination_folder_id + operation_kind)。

- idempotency_keyごとに予約fileIdをDBへ永続化してからGoogle Drive create。
- 強制終了後は最初に予約IDを照会し、内容ハッシュとサイズを照合。
- 既に同じファイルがあれば再アップロードしない。内容不一致はCONFLICT。
- 「同名PDF」は冪等キーに使わない。
- 新版のPDFを作ったら別artifactになり、旧版の自動上書きはしない。

## 5. 破壊的変更の防止

不変条件:
1. ソース一覧が取得できないことは、書籍やDriveファイルの削除証拠ではない。
2. Kindle本が見えなくなってもbooksを消さない。
3. 検証できない購入本は自動DLしない。
4. 検証できないファイルはDriveアップロードしない。
5. 強制終了/再試行はファイル重複を増やさない。
6. ユーザー確認なしの既存Driveの削除・置換をしない。
7. チェックサム未提供時は「完全一致検証」と表現しない。

## 6. 代表的な問い合わせ

- 未同期の購入本: VERIFIEDかつDriveに検証済み対象成果物がない。取得不可/未確認/操作待ちを分類する。
- 今回の新着: 直近scan_idで初検出されたbooks。ただし「Amazonアカウントの全新着購入」とは限らない。
- 要対応: UNVERIFIED、ファイル内容不一致、OAuth失効、操作待ちなど。
- Drive差分: drive_file_idの不可視/ハッシュ差異/管理フォルダ不一致。API障害と実削除を混同しない。

## 7. DB運用

- DBはアプリ専用ディレクトリに置く。Kindle側DBを更新しない。
- スキーマ変更にはバージョン付きmigrationとテストを必須にする。
- バックアップにはSQLite backup APIを利用し、バックアップの復元E2Eを用意する。
- SQLiteに認証トークンや生の購入証跡スクリーンショットを格納しない（必要な参照/ハッシュのみ）。

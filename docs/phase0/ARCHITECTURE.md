# Architecture — ローカル同期エンジン

状態: Phase 0 設計案

## 1. 選択

- **macOSローカルの単一プロセス・モジュラーモノリス**を採用する。分散ジョブキュー・Cloud Run・外部DBは導入しない。
- UIは既存のFletを当面維持するが、ビジネスロジックをFletから独立させる。
- 永続ストアはSQLite、成果物はローカル作業ディレクトリに置き、アップロード後に検証。原本の保持期限は設定可能にする。
- Amazon連携、Kindle DB連携、Drive連携、PDF処理をアダプタで切り替え可能にする。
- 初期バージョンは**同期セッション1件/ワーカー1件**。重複起動時は拒否し、処理競合を避ける。

## 2. モジュール境界

~~~text
src/kindle_to_pdf/
  domain/          # BookIdentity, Evidence, DownloadAvailability, Artifact, SyncPlan, States
  application/     # ScanService, ReconcileService, SyncOrchestrator, RetryPolicy
  ports/           # KindleLibraryPort, PurchaseEvidencePort, OfficialDownloadPort,
                   # ArtifactProcessorPort, DrivePort, RepositoryPort, Clock
  adapters/
    kindle_local/  # readonly metadata snapshot reader
    amazon/        # official purchase/availability observation; browser PoC isolated
    files/         # official import, EPUB/PDF validation/conversion, OCR
    google_drive/  # OAuth, list/get/create, resumable upload, hash check
    sqlite/        # schema, migrations, repository, transactions
  ui/              # Flet views and presentation state only
  legacy/          # current screenshot converter, default sync disabled
~~~

既存ファイル:
- converter.py: activate, resize, capture, convert, OCR が密結合。移行まで残すが通常の同期コースから呼び出さない。
- gui.py: 現在は1冊変換フォーム。Phase 3で上記 application サービスを利用するビューへ段階置換。
- app.py/web.py: 入口として利用し、GUI依存の差し替えを可能にする。
- tests/test_converter.py: Quartzをトップレベルimportする実装に依存。CI（非macOS）ではドメイン/アプリ層にQuartzが波及しないよう分離する。

## 3. Port契約案

| Port | 入力 | 出力/性質 |
|---|---|---|
| KindleLibraryPort.scan | ローカル設定 | 観測された書籍、source_status、timestamp。readonly |
| PurchaseEvidencePort.collect | アカウント/書籍候補 | 購入の根拠/取得不能。失敗時に旧証拠を消さない |
| OfficialDownloadPort.check | 書籍 | AVAILABLE/UNAVAILABLE/UNKNOWN、形式、根拠と日時 |
| OfficialDownloadPort.download | 取得可能書籍 | 公式ファイルまたは USER_ACTION_REQUIRED/UNAVAILABLE |
| ArtifactProcessorPort.validate/convert | ファイル | MIME判定、実バイト検証、ハッシュ、品質結果 |
| DrivePort.list/get/upload | アプリ許可範囲/ファイル | fileId、etag、ハッシュ、可視性、確定状態 |
| RepositoryPort | ドメイン集約 | 一意制約・トランザクション・チェックポイント |

各Portは詳細型を定義し、テスト用Fakeアダプタを用意する。UIはAPIレスポンスやSQLite表を直接読むことを禁止する。

## 4. 同期アルゴリズム

1. ロック取得。前回の不完全ジョブを読み込む。環境・認証・権限を検査。
2. Kindle側の観測結果を**新規スナップショット**として保存。取得失敗時はスナップショットを未完成とし、未検出を欠落扱いしない。
3. 購入確認根拠を更新。書誌のタイトル変更と書籍ID同一性を切り分ける。
4. 公式DL可否を再確認できる場合は更新。不明・エラーは UNKNOWN/STALE と区別。
5. Driveの許可範囲をページングで列挙し、fileId・メタデータ・ハッシュを照合。権限エラーでは削除を確定しない。
6. 差分から不変な SyncPlan を作成。対象と理由をUIに提示（初回一括なら明示確認）。
7. ジョブに一意な idempotency_key を振り、取得→検証→変換→アップロード→照合を逐次実行。
8. 各境界で DB トランザクションでチェックポイントを確定し、キャンセルは工程境界で受理。
9. 成功応答を受け取れず状態不明なアップロードは、保存済み予約fileIdで先にDrive照会。バイト一致なら成功扱い、異なるなら CONFLICT として停止。
10. 結果を COMPLETED / COMPLETED_WITH_ERRORS / FAILED / CANCELLED に分類。取得保留は成功ジョブとは別件数。

## 5. Driveの冪等化・整合性

- アプリ作成のバイナリファイルはDrive files.generateIdsでファイルIDを事前確保し、**API呼び出し前にSQLiteへ保存**する。
- アップロードは resumable を使用。セッションURIは認証情報に準ずるものとして扱い、ログへ出さない。
- 409 Conflict等では、予約IDのDriveファイルとローカルのハッシュを比較。正しければ完了として復旧。IDだけの一致を成功証拠としない。
- ローカルSHA-256とDriveのsha256Checksum（取得可能な場合）を比較。未提供ならmd5Checksumやsizeで暫定照合し、必要なら内容再ダウンロードを実施。照合水準を記録する。
- 任意のDrive上の同名ファイルと一致とはみなさない。既存ファイルはPicker等で利用者が指定した可視範囲のみ照合する。
- 対象外への改名・移動などを検出しても、ユーザーのDriveファイルを自動復元・削除しない。

参考: https://developers.google.com/workspace/drive/api/guides/create-file
参考: https://developers.google.com/workspace/drive/api/guides/manage-uploads

## 6. Kindle/Amazonの不確実性の隔離

- Kindle DBは既存アプリの内部実装であり変化しうるため、取得元・バージョン・スキーマ対応をアダプタ内で管理。
- 読み取り対象DBはreadonlyアクセス。必要ならSQLiteの安全なスナップショット取得方法をPoCで確認。アプリ管理DBと混在させない。
- Amazon公式Web UIを操作するアダプタは feature flag OFF から開始し、PoCと利用条件確認後にのみ有効化。
- Amazonにログインする処理は利用者本人の通常ブラウザ上で行う。資格情報/セッションCookieの採取や迂回手段は設計に含めない。
- 自動ブラウザ操作が不適切/不安定であればユーザーの手動DLを案内する。非DL対象は取得保留。

## 7. エラーの型

AUTH_REQUIRED, PERMISSION_DENIED, LOCAL_DB_UNAVAILABLE, SOURCE_PARTIAL,
PURCHASE_UNVERIFIED, DOWNLOAD_UNAVAILABLE, DOWNLOAD_UNKNOWN,
USER_ACTION_REQUIRED, ARTIFACT_INVALID, DRIVE_INACCESSIBLE, DRIVE_CONFLICT,
TRANSIENT_NETWORK, RATE_LIMITED, CANCELLED。

技術エラー、ビジネス上の保留、ユーザー操作待ちを同じERRORにまとめない。

## 8. 段階移行

Phase 0.5: src移動前に依存グラフ整理とdomain/portsのテスト実行可能化。
Phase 1: Kindle・AmazonアダプタのPoC。実データをコミットしない。
Phase 2: 台帳・Driveアダプタ・同期計画とジョブ管理。
Phase 3: 公式ファイル処理/変換と新UI、Mac E2E、既存converterの隔離。

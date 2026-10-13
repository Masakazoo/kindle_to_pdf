# Decisions, Open Questions & Delivery Plan

更新: 2026-10-13

## 確定済み決定事項

- D-01 取得対象は購入済みKindle本のみ。有料および0円購入を含む。
- D-02 Kindle Unlimited/Prime Reading/サンプル/返品済みは非対象。
- D-03 実行はユーザーが押す手動同期。常駐/定期実行はない。
- D-04 公式ダウンロードに非対応の本は購入台帳に残し、取得保留。
- D-05 Amazon正規DLについてブラウザ操作を含む自動化可能性をPoC検証。技術的に動くだけでは採用しない。
- D-06 Google DriveへPDFを主形式として保存。EPUB原本は可能な範囲で保持。
- D-07 既存Driveファイルを無断削除/上書きしない。
- D-08 Phase 0でUI/UX基本設計まで行い、本格UI実装はPhase 3。
- D-09 Phase 0の後にCodex/GitHubの開発基盤を整備し、PoC・実装へ進む。
- D-10 既存の自動スクリーンショット処理はデフォルト同期経路には含めない。

## 未確定・PoCゲート付き

| Key | 論点 | 当面の安全な既定値 | 解除条件 |
|---|---|---|---|
| Q-01 | ローカルDBで全購入本が見えるか | 網羅性不明と表示 | 実購入履歴との一致率の検証 |
| Q-02 | Amazon購入情報を安定して確認できるか | 未確認のまま台帳に残す | 公式UI/エクスポートのPoC |
| Q-03 | 公式DLの一括自動化は規約に適合するか | 自動操作OFF | 適用規約とブラウザPoC双方に合格 |
| Q-04 | Google Pickerで既存フォルダ内全件が見えるか | 明示選択されたファイルだけ照合 | drive.file権限の実機PoC |
| Q-05 | 縦書き/固定レイアウトEPUBを適切にPDF化できるか | 変換保留・原本保持 | サンプルで品質合格 |
| Q-06 | 性能・容量の適切なSLO | 実測値は未定 | 書籍件数とファイルサイズのベンチマーク |
| Q-07 | Fletを維持すべきか | 維持 | macOS/UIテスト・配布性の比較 |

## 開発順序

1. **Phase 0（現状）**: PRD / Architecture / Data Model / UX / NFR / PoC / Test の整合性レビューと合意。
2. **Phase 0.5**: Codex用AGENTS.md、uv、ruff、pytest、CI、Issue/PRテンプレート、branch protection方針を整備。
3. **Phase 1**: SPIKE-01/02/03でAmazon/Kindleの未知点を解消。同時にSPIKE-04/05/06の限定PoC。
4. **Phase 2**: ドメイン/SQLite/Drive同期の安定基盤、Fake Portを使った冪等性の検証。
5. **Phase 3**: 条件付き公式DL/ファイル処理、Flet UI、Mac実機E2EとUX仕上げ。
6. **Phase 4**: 実測に基づく品質・性能の改善とリリース。

## Codex作業の原則

- IssueごとにブランチとDraft PR、作業中の学びをPR本文に記載。
- まず調査し、結果をPoCレポートに残してから本体の実装可否を判断する。
- データ収集部分はread-only、秘密情報や書籍本文のコミットはしない。
- No-Goの結論でも、失敗理由・検証方法・代替案を成果とみなす。
- Phase 0の設計ファイルは既知の制約と暫定仮説を区別する。

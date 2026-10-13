# Kindle Library Sync — Phase 0 設計インデックス

更新日: 2026-10-13
状態: **設計案／PoC未実施**。実装開始前にSPIKEを行い、未確認の事項は確定事項として扱わない。

## プロダクトの目的

macOS上でユーザーが「同期開始」を押すと、購入済みKindle本の候補を照合し、Amazonが公式に提供する取得可能なEPUB/PDFとGoogle Driveの保存状況を比較する。新しい公式ファイルが取得できた場合に、検証・必要なPDF変換・アップロードを行い、取得できない本は台帳に「取得保留」として残す。

**購入済み蔵書の全件認識と、全件のPDF化は別の目標である。** Amazon側の一般公開APIによる購入履歴全件取得／一括ファイル取得は確認できていない。

## ドキュメント

- [PRD.md](./PRD.md): スコープ、機能要件、ユーザーフロー、受け入れ基準
- [ARCHITECTURE.md](./ARCHITECTURE.md): モジュール、ポート、処理順、既存実装からの移行
- [DATA_MODEL.md](./DATA_MODEL.md): SQLiteスキーマ案、状態遷移、整合性・冪等性
- [UX_SPEC.md](./UX_SPEC.md): 画面構成、初回/通常/例外フロー
- [NFR_SECURITY.md](./NFR_SECURITY.md): セキュリティ、運用、性能、法務・利用条件
- [POC_PLAN.md](./POC_PLAN.md): 技術調査の手順、検証データ、Go/No-Go
- [TEST_STRATEGY.md](./TEST_STRATEGY.md): 自動・実機テスト、受け入れケース
- [DECISIONS.md](./DECISIONS.md): 確定事項、保留事項、開発フェーズ

## 設計原則

1. 利用者による**手動同期開始**。常駐/定期実行は初期スコープ外。
2. 購入確認できない候補は処理しない。0円購入は対象、KU/Prime Reading/サンプルは対象外。
3. 公式取得可能なDRMフリーEPUB/PDFを優先。公式取得に非対応の本は取得保留。DRM回避や制限の迂回は実装しない。
4. Kindleの「認識」、Amazonの「購入確認」、公式DL可否、Google Driveの「保存状態」を独立管理する。
5. AmazonまたはGoogle Driveの取得が失敗しても削除・欠落と断定しない。自動削除・自動上書きはしない。
6. 変換・同期は1冊単位で永続化し、リトライ可能かつ冪等にする。
7. 既存のスクリーンショット方式は**通常同期経路から切り離す**。権利・利用規約の確認なしに非対応本へ自動適用しない。
8. 画面設計はPhase 0で定義し、本格実装はPhase 3。

## 一次資料／先行実装

- Amazon KDP DRM: https://kdp.amazon.com/en_US/help/topic/GDDXGH9VR22ACM8U
- Google Drive API OAuth scope: https://developers.google.com/workspace/drive/api/guides/api-specific-auth
- Google Drive custom properties: https://developers.google.com/workspace/drive/api/guides/properties
- Google Drive resumable upload: https://developers.google.com/workspace/drive/api/guides/manage-uploads
- Kindle for macOS metadataの先行例: https://github.com/rok-git/listKindleBooks2
- 既存コード: src/kindle_to_pdf/{converter,gui,web}.py

注: 公式取得仕様はAmazon KDP向け資料に基づく。Amazon.co.jpでの個別書籍・アカウントの表示および適用規約はPoCで別途確認する。

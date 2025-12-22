#!/usr/bin/env python3
"""
Kindle自動スクリーンショット→PDF変換ツール

MacBook AirでKindle for Macの書籍を自動的にスクリーンショットし、
PDFに変換するスクリプト。Adobe AcrobatでOCR処理後、NotebookLMで利用可能。
"""

import os
import time
import subprocess
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageFile
from Quartz import (
    CGWindowListCopyWindowInfo,
    kCGWindowListOptionOnScreenOnly,
    kCGNullWindowID,
    kCGWindowOwnerName,
    kCGWindowNumber,
    kCGWindowLayer,
)
import ocrmypdf

# 途切れた画像も許容する設定
ImageFile.LOAD_TRUNCATED_IMAGES = True

# Tesseract/Ghostscriptのパスを通す（Mac Homebrew用）
os.environ["PATH"] += os.pathsep + "/opt/homebrew/bin"


class KindleToPDF:
    def __init__(
        self,
        book_name,
        total_pages,
        page_turn_direction="left",
        output_dir="~/Desktop/kindle_exports",
        enable_ocr=False,
    ):
        """
        初期化

        Args:
            book_name: 書籍名（ファイル名に使用）
            total_pages: 総ページ数
            page_turn_direction: ページめくり方向 ('left' or 'right')
                                'left' (左開き/横書き) -> 右矢印キー(124)
                                'right' (右開き/縦書き) -> 左矢印キー(123)
            output_dir: 出力先ディレクトリ
        """
        self.book_name = book_name
        self.total_pages = total_pages
        self.page_turn_direction = page_turn_direction
        self.enable_ocr = enable_ocr

        # 出力ディレクトリの設定
        if output_dir:
            self.base_dir = Path(output_dir).expanduser()
        else:
            self.base_dir = Path("~/Desktop/kindle_exports").expanduser()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.work_dir = self.base_dir / f"{book_name}_{timestamp}"
        self.screenshots_dir = self.work_dir / "screenshots"

        # ディレクトリ作成
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

        self.log_queue = None  # GUI用

        # 設定
        self.page_delay = 1.5  # ページめくり後の待機時間（秒）
        self.initial_delay = 1.5  # 最初の待機時間（秒）

    def log(self, message, is_important=False):
        """ログ出力"""
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        formatted_message = f"{timestamp} {message}"
        print(formatted_message)

        # GUIログ連携用
        # GUI側で converter.log = gui_logger のように上書きされることを想定
        # または、GUI側で標準出力をキャプチャするか

    def _run_applescript(self, script, description):
        """AppleScriptを実行し、エラー時は詳細なメッセージを出す"""
        try:
            subprocess.run(["osascript", "-e", script], check=True)
            return True
        except subprocess.CalledProcessError as e:
            error_msg = (
                f"❌ {description} に失敗しました。\n"
                "macOSのアクシビリティ権限が不足している可能性があります。\n"
                "1. システム設定 > プライバシーとセキュリティ > アクセシビリティ を開く\n"
                "2. 既存の 'KindleToPDF' をリストから削除する (-ボタン)\n"
                "3. アプリを再度リストに追加し、スイッチをONにする"
            )
            self.log(error_msg, is_important=True)
            raise RuntimeError(error_msg) from e

    def activate_kindle(self):
        """Kindle for Macをアクティブ化"""
        script = 'tell application "Kindle" to activate'
        self._run_applescript(script, "Kindleのアクティブ化")
        time.sleep(1)

    def resize_window(self):
        """ウィンドウを縦長にリサイズして単ページ表示を強制"""
        # 幅 1080, 高さ 1440 (縦長)
        # 左上の座標 {50, 50}
        applescript = """
        tell application "System Events"
            tell process "Kindle"
                set frontWindow to first window
                
                -- フルスクリーン状態を確認してから解除
                try
                    set isFullScreen to value of attribute "AXFullScreen" of frontWindow
                    if isFullScreen is true then
                        keystroke "f" using {command down, control down}
                        delay 2 -- アニメーション完了待ち
                    end if
                end try
                
                -- サイズ変更を再試行
                try
                    set position of frontWindow to {50, 50}
                    set size of frontWindow to {800, 1200}
                end try
            end tell
        end tell
        """
        try:
            self._run_applescript(applescript, "ウィンドウリサイズ")
            self.log("ウィンドウを縦長にリサイズしました (単ページ表示強制)")
        except RuntimeError:
            self.log("⚠️ ウィンドウリサイズに失敗しました（続行します）")

    def get_window_id(self):
        """KindleのウィンドウIDをQuartzを使用して取得"""
        options = kCGWindowListOptionOnScreenOnly
        window_list = CGWindowListCopyWindowInfo(options, kCGNullWindowID)

        for window in window_list:
            owner_name = window.get(kCGWindowOwnerName, "")
            # Kindleプロセス名は "Kindle" または "Amazon Kindle" の可能性がある
            if "Kindle" in owner_name:
                # レイヤー0は通常のウィンドウ
                if window.get(kCGWindowLayer, 0) == 0:
                    window_id = window.get(kCGWindowNumber)
                    self.log(f"Found Kindle Window: ID={window_id}, Name={owner_name}")
                    return window_id

        self.log("❌ Kindleのウィンドウが見つかりません (Quartz)")
        return None

    def turn_page(self):
        """ページをめくる（設定された方向に応じてキーを送信）"""
        # left(横書き) -> 右矢印(124)で次へ
        # right(縦書き) -> 左矢印(123)で次へ
        key_code = 124 if self.page_turn_direction == "left" else 123

        self.log(
            f"DEBUG: turn_page - Direction: {self.page_turn_direction}, KeyCode: {key_code}"
        )

        applescript = f"""
        tell application "Kindle" to activate
        delay 0.5
        tell application "System Events"
            key code {key_code}
        end tell
        """
        self._run_applescript(applescript, "ページめくり")

    def take_screenshot(self, page_num, window_id=None):
        """
        スクリーンショットを撮影

        Args:
            page_num: ページ番号
            window_id: キャプチャ対象のウィンドウID
        """
        output_path = self.screenshots_dir / f"page_{page_num:04d}.png"
        if window_id:
            # ウィンドウIDを指定してキャプチャ（非対話モード）
            cmd = ["screencapture", "-x", "-l", str(window_id), str(output_path)]
        else:
            # フォールバック（通常発生しないはずだが、IDなしなら全体or対話）
            # -w は対話モードになるため避ける。画面全体を撮るかエラーにする。
            self.log("⚠️ ウィンドウIDがないため、画面全体をキャプチャします")
            cmd = ["screencapture", "-x", str(output_path)]

        try:
            subprocess.run(cmd, check=True, timeout=10)
            self.log(f"ページ {page_num}/{self.total_pages} をキャプチャしました")
            return True
        except subprocess.TimeoutExpired:
            self.log(f"⚠️ ページ {page_num} のキャプチャがタイムアウトしました")
            return False
        except subprocess.CalledProcessError as e:
            self.log(f"⚠️ ページ {page_num} のキャプチャに失敗しました: {e}")
            return False

    def capture_all_pages(self):
        """全ページをキャプチャ"""
        self.log(f"📖 '{self.book_name}' の自動キャプチャを開始します")
        self.log(f"総ページ数: {self.total_pages}")
        self.log(f"ページめくり間隔: {self.page_delay}秒")
        self.log("")
        self.log(
            "⚠️ 重要: Kindle for Macのウィンドウをクリックしてアクティブにしてください"
        )
        self.log(f"{self.initial_delay}秒後に開始します...")

        time.sleep(self.initial_delay)

        # Kindleをアクティブ化
        self.activate_kindle()
        time.sleep(1)

        # ウィンドウサイズを調整（単ページ強制）
        self.resize_window()
        time.sleep(1)

        success_count = 0

        # ウィンドウIDを取得（ループ外で一度だけ取得しても良いが、安全のため確認）
        # ただし頻繁なAppleScript呼び出しは遅いので、ループ前に取得する
        window_id = self.get_window_id()
        if not window_id:
            self.log(
                "⚠️ ウィンドウIDが取得できませんでした。権限エラーの可能性があります。"
            )
            self.log(
                "⚠️ 全画面キャプチャモードで続行します。Kindleを最前面に保ってください。"
            )
            # return 0 を削除し、Noneのまま続行させる

        self.log(f"Target Window ID: {window_id}")

        for page in range(1, self.total_pages + 1):
            # スクリーンショット撮影
            if self.take_screenshot(page, window_id):
                success_count += 1

            # 最後のページでなければページめくり
            if page < self.total_pages:
                self.turn_page()
                time.sleep(self.page_delay)

        self.log("")
        self.log(f"✅ キャプチャ完了: {success_count}/{self.total_pages} ページ")
        return success_count

    def convert_to_pdf(self):
        """画像をPDFに変換"""
        self.log("")
        self.log("📄 PDFに変換中...")

        # スクリーンショットファイルを取得
        image_files = sorted(self.screenshots_dir.glob("page_*.png"))

        if not image_files:
            self.log("❌ スクリーンショットが見つかりません")
            return None

        self.log(f"画像ファイル数: {len(image_files)}")

        # 画像を読み込み
        images = []
        for img_path in image_files:
            try:
                img = Image.open(img_path)
                # RGBモードに変換（PDFはRGBAをサポートしない）
                if img.mode == "RGBA":
                    img = img.convert("RGB")
                images.append(img)
            except Exception as e:
                self.log(f"⚠️ {img_path.name} の読み込みに失敗: {e}")

        if not images:
            self.log("❌ 有効な画像がありません")
            return None

        # PDFとして保存
        pdf_path = self.work_dir / f"{self.book_name}.pdf"

        try:
            # 最初の画像をベースに、残りを追加
            images[0].save(
                pdf_path,
                save_all=True,
                append_images=images[1:],
                resolution=100.0,
                quality=85,
                optimize=False,
            )

            file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
            self.log(f"✅ PDF作成完了: {pdf_path}")
            self.log(f"ファイルサイズ: {file_size_mb:.2f} MB")

            if file_size_mb > 200:
                self.log("⚠️ 警告: ファイルサイズが200MBを超えています")
                self.log("   NotebookLMの制限を超える可能性があります")

            return pdf_path

        except Exception as e:
            self.log(f"❌ PDF作成に失敗: {e}")
            return None

    def run(self):
        """メイン処理"""
        self.log("=" * 60)
        self.log("Kindle to PDF Converter")
        self.log("=" * 60)
        self.log(
            f"DEBUG: Params - Book: {self.book_name}, Pages: {self.total_pages}, Direction: {self.page_turn_direction}"
        )

        # スクリーンショット撮影
        success_count = self.capture_all_pages()

        if success_count == 0:
            self.log("❌ スクリーンショットが1枚も撮影できませんでした")
            return None

        # PDF変換
        pdf_path = self.convert_to_pdf()

        if pdf_path:
            self.log("")
            self.log("=" * 60)
            self.log("🎉 PDF作成処理完了！")
            self.log("=" * 60)
            self.log(f"出力先: {pdf_path}")

            # OCR処理の実行
            if self.enable_ocr:
                ocr_pdf_path = self.perform_ocr(pdf_path)
                return ocr_pdf_path if ocr_pdf_path else pdf_path
            else:
                self.log("ℹ️ OCR処理はスキップされました")
                return pdf_path

        return None

    def perform_ocr(self, pdf_path):
        """OCRmyPDFを使用してOCRを実行"""
        self.log("")
        self.log("🔍 OCRmyPDFでOCR処理を開始します...")

        output_path = pdf_path.parent / f"{pdf_path.stem}_ocr.pdf"

        try:
            # 言語データの有無をチェック（簡易的）
            import subprocess

            res = subprocess.run(
                ["tesseract", "--list-langs"], capture_output=True, text=True
            )
            if "jpn" not in res.stdout:
                self.log("❌ Tesseractの日本語データ(jpn)が見つかりません。")
                self.log("   `brew install tesseract-lang` を実行してください。")
                return None

            # ocrmypdf.ocr(input_file, output_file, language="jpn", ...)
            # deskew=True: 傾き補正
            # use_threads=True: マルチスレッド
            exit_code = ocrmypdf.ocr(
                input_file=str(pdf_path),
                output_file=str(output_path),
                language="jpn",
                deskew=False,  # デジタルスクショなので補正不要（誤補正防止）
                use_threads=True,
                force_ocr=True,  # 画像のみのPDFとして扱う
            )

            if exit_code == 0:
                self.log(f"✅ OCR処理完了: {output_path}")
                return output_path
            else:
                self.log(f"❌ OCR処理が終了コード {exit_code} で終了しました")
                return None

        except ocrmypdf.exceptions.MissingDependencyError:
            self.log(
                "❌ 依存関係エラー: Tesseract または Ghostscript が見つかりません。"
            )
            self.log("   `brew install tesseract ghostscript` を実行してください。")
            return None
        except Exception as e:
            self.log(f"❌ OCR処理中にエラーが発生しました: {e}")
            return None

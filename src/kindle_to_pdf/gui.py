import flet as ft
import threading
import queue
from .converter import KindleToPDF


class KindleToPDFApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Kindle to PDF Converter"
        self.page.window_width = 800
        self.page.window_height = 1100
        self.page.window_resizable = True
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.padding = 20

        self.log_queue = queue.Queue()
        self.running = False

        self.setup_ui()

    def setup_ui(self):
        # Header
        header = ft.Text("Kindle to PDF Converter", size=30, weight=ft.FontWeight.BOLD)

        # Inputs
        self.book_name = ft.TextField(
            label="書籍名 (出力ファイル名)", value="kindle_book"
        )
        self.total_pages = ft.TextField(
            label="総ページ数", value="100", keyboard_type=ft.KeyboardType.NUMBER
        )

        # Radio Group for Direction
        self.direction = ft.RadioGroup(
            content=ft.Row(
                [
                    ft.Radio(value="left", label="左開き (横書き) [→]"),
                    ft.Radio(value="right", label="右開き (縦書き) [←]"),
                ]
            ),
            value="left",
        )

        # Output Directory
        self.output_dir = ft.TextField(
            label="出力先フォルダ (空欄の場合はデスクトップ)",
            value="",
            read_only=True,
            expand=True,
        )
        self.pick_dir_dialog = ft.FilePicker(on_result=self.on_dir_result)
        self.page.overlay.append(self.pick_dir_dialog)

        def pick_dir_native(e):
            # WebブラウザモードではFletのFilePicker(ディレクトリ)が動作しないため、
            # AppleScriptを使ってネイティブのフォルダ選択ダイアログを表示する
            try:
                import subprocess

                # System Eventsをアクティブにして最前面に出す
                script = """
                tell application "System Events"
                    activate
                    set p to POSIX path of (choose folder with prompt "出力先フォルダを選択してください")
                end tell
                return p
                """
                res = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                path = res.stdout.strip()
                if path:
                    self.output_dir.value = path
                    self.page.update()
            except Exception as err:
                print(f"Directory pick failed: {err}")
                self.status_text.value = f"フォルダ選択エラー: {err}"
                self.page.update()

        pick_dir_btn = ft.IconButton(
            icon=ft.Icons.FOLDER_OPEN, on_click=pick_dir_native, tooltip="出力先を選択"
        )

        # Progress
        self.progress_bar = ft.ProgressBar(width=560, value=0)
        self.status_text = ft.Text("待機中...", selectable=True)

        # Log Area
        self.log_view = ft.ListView(
            expand=True,
            spacing=10,
            padding=10,
            auto_scroll=True,
            height=300,
        )
        log_container = ft.Container(
            content=self.log_view,
            border=ft.border.all(1, "grey300"),
            border_radius=5,
            padding=5,
            bgcolor="grey50",
            expand=True,
        )

        # Buttons
        self.start_btn = ft.ElevatedButton(
            "変換開始",
            icon=ft.Icons.PLAY_ARROW,
            on_click=self.start_process,
            style=ft.ButtonStyle(
                color="white",
                bgcolor="blue",
                padding=15,
            ),
        )

        # Instructions
        instructions = ft.Column(
            [
                ft.Text("⚠️ 重要な準備:", weight=ft.FontWeight.BOLD),
                ft.Text("1. Kindle for Macで対象の書籍を開いてください"),
                ft.Text("2. ウィンドウサイズは自動調整されます (フルスクリーン解除)"),
                ft.Text("3. 最初のページを表示してください"),
            ]
        )

        # Layout

        # OCR Checkbox
        self.ocr_checkbox = ft.Checkbox(
            label="OCR処理を実行する (時間がかかります)", value=False
        )

        # Layout
        self.page.add(
            ft.Column(
                [
                    header,
                    ft.Divider(),
                    self.book_name,
                    self.total_pages,
                    ft.Row([self.output_dir, pick_dir_btn]),
                    ft.Text("ページめくり方向:"),
                    self.direction,
                    self.ocr_checkbox,
                    ft.Divider(),
                    instructions,
                    ft.Divider(),
                    ft.Row([self.start_btn], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Divider(),
                    self.status_text,
                    self.progress_bar,
                    ft.Text("ログ出力:"),
                    log_container,
                ],
                expand=True,
            )
        )

    def on_dir_result(self, e: ft.FilePickerResultEvent):
        if e.path:
            self.output_dir.value = e.path
            self.page.update()

    def log(self, message: str):
        self.log_queue.put(message)
        self.page.update()

    def process_logs(self):
        while not self.log_queue.empty():
            msg = self.log_queue.get()
            self.log_view.controls.append(
                ft.Text(msg, size=12, font_family="monospace")
            )
            self.page.update()

    def start_process(self, e):
        if self.running:
            return

        try:
            pages = int(self.total_pages.value)
            if pages <= 0:
                raise ValueError
        except ValueError:
            self.status_text.value = "❌ 有効なページ数を入力してください"
            self.page.update()
            return

        self.running = True
        self.start_btn.disabled = True
        self.progress_bar.value = None  # Indeterminate
        self.status_text.value = "準備中... 3秒以内にKindleをアクティブにしてください"
        self.log_view.controls.clear()
        self.page.update()

        output_path_val = self.output_dir.value if self.output_dir.value else None
        enable_ocr = self.ocr_checkbox.value

        print(
            f"DEBUG: GUI Sending - Name: {self.book_name.value}, Pages: {pages}, Direction: {self.direction.value}, Output: {output_path_val}, OCR: {enable_ocr}"
        )

        # Run within a thread to prevent UI freezing
        thread = threading.Thread(
            target=self.run_conversion,
            args=(
                self.book_name.value,
                pages,
                self.direction.value,
                output_path_val,
                enable_ocr,
            ),
            daemon=True,
        )
        thread.start()

        # Set up a timer to poll logs
        # Note: In Flet, we usually update UI via page.update() inside the main thread or use thread-safe calls.
        # For simplicity here, we'll assume direct update works or we might need pubsub.
        # But actually, best practice is ensuring updates happen on the loop.
        # Since Flet's page.update() is thread-safe, we can call it directly from the thread?
        # Let's verify. Flet docs say page.update() is generally thread-safe for basic updates.

    def run_conversion(self, name, pages, direction, output_dir_path, enable_ocr):
        try:
            # Custom logger to redirect to GUI
            def gui_logger(msg, is_important=False):
                # Important messages could be highlighted or handled differently
                control = ft.Text(str(msg), size=12, font_family="monospace")
                if is_important:
                    control.color = "red"
                    control.weight = ft.FontWeight.BOLD

                self.log_view.controls.append(control)
                self.page.update()

            converter = KindleToPDF(
                name,
                pages,
                direction,
                output_dir=output_dir_path,
                enable_ocr=enable_ocr,
            )
            # Inject custom logger (We need to modify KindleToPDF to accept a logger or override log method)
            # Monkey patching for now since we don't want to break the CLI immediately or modify converter deeply yet
            converter.log = gui_logger

            self.status_text.value = "実行中..."
            self.page.update()

            output_path = converter.run()

            if output_path:
                self.status_text.value = "✅ 完了しました！"
                self.log_view.controls.append(
                    ft.Text(
                        f"保存先: {output_path}",
                        color="green",
                        weight=ft.FontWeight.BOLD,
                    )
                )
                # Open Finder
                import subprocess

                subprocess.run(["open", str(output_path.parent)])
            else:
                self.status_text.value = "❌ 処理が中断されました"

        except Exception as e:
            self.status_text.value = f"エラーが発生しました: {e}"
            self.log_view.controls.append(ft.Text(f"Error: {e}", color="red"))

        finally:
            self.running = False
            self.start_btn.disabled = False
            self.progress_bar.value = 0
            self.page.update()


def main(page: ft.Page):
    KindleToPDFApp(page)


if __name__ == "__main__":
    ft.app(target=main)

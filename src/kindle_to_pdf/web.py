import os

import flet as ft

from .gui import main


def run_web_app():
    # 個人利用のmacOSローカルアプリ。LANからの操作を許可しない。
    os.environ["FLET_SERVER_IP"] = "127.0.0.1"
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=8080)


if __name__ == "__main__":
    run_web_app()

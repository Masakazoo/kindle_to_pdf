import flet as ft
from .gui import main

if __name__ == "__main__":
    # view=ft.AppView.WEB_BROWSER でブラウザ起動
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=8080)

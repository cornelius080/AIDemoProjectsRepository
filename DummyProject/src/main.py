import flet as ft
import os

def main(page: ft.Page):
    page.title = "Flet counter example"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    input = ft.TextField(value="0", text_align=ft.TextAlign.RIGHT, width=100)

    def minus_click(e):
        input.value = str(int(input.value) - 1)
        input.update()

    def plus_click(e):
        input.value = str(int(input.value) + 1)
        input.update()

    page.add(
        ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.IconButton(ft.Icons.REMOVE, on_click=minus_click),
                input,
                ft.IconButton(ft.Icons.ADD, on_click=plus_click),
            ],
        )
    )

is_docker = os.getenv("DOCKER_RUNNING") == "true"
ft.app(
    target=main, 
    view=ft.AppView.WEB_BROWSER, 
    host="0.0.0.0" if is_docker else "127.0.0.1",
    port=8080
)
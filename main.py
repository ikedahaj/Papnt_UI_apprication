import flet as ft
import UI_input_doi
import UI_make_bibfile

def main(page: ft.Page):
    class Button_move_window(ft.FilledButton):
        def __init__(self):
            super().__init__()
            self.text="bibtex 出力ページ"
            def to_test(e):
                page.views.append(view_make_bib)
                page.go(view_make_bib.route)
                print(page.route)
            self.on_click=to_test
    button_move_window=Button_move_window()
    view_input=UI_input_doi.View_input_doi()
    view_input.set_button_to_appbar(button_move_window)
    page.views.append(view_input)
    view_make_bib=UI_make_bibfile.view_bib_maker()
    page.update()
    def view_pop(e):
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)
    def route_change(route):
        pass
            

    page.on_view_pop=view_pop
    page.on_route_change=route_change
    page.update()
ft.app(main)

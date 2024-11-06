import flet as ft
import UI_input_doi
import UI_make_bibfile

#TODO:arXiv対応
#     候補消去
#     classに書き出し
def main(page: ft.Page):
    class Button_move_window(ft.FilledButton):
        def __init__(self):
            super().__init__()
            self.text="bibtex 出力ページ"
            self.__view_make_bib=None
            def to_test(e):
                if self.__view_make_bib is None:
                    self.text="ページ作成中..."
                    self.update()
                    self.style=ft.ButtonStyle(bgcolor=ft.colors.GREEN,side=ft.BorderSide(2, ft.colors.BLUE),shape=ft.RoundedRectangleBorder(radius=1))
                    self.update()
                    self.__view_make_bib=UI_make_bibfile.view_bib_maker()
                page.views.append(self.__view_make_bib)
                page.go(self.__view_make_bib.route)
                print(page.route)
                self.text="bibtex 出力ページ"
                self.style=None
            self.on_click=to_test
    button_move_window=Button_move_window()
    view_input=UI_input_doi.View_input_doi()
    view_input.set_button_to_appbar(button_move_window)
    page.views.append(view_input)
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

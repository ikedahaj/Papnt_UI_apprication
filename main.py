import flet as ft
import UI_input_doi
import UI_make_bibfile


# TODO:arXiv対応
#     候補消去
#     classに書き出し
def main(page: ft.Page):
    class Button_move_window(ft.FilledButton):
        def __init__(self):
            super().__init__()
            self.text = "bibtex 出力ページ"
            self.__view_make_bib: type[UI_make_bibfile.view_bib_maker] | None = None
            # self.BW_list_un_added_papers: list[dict] = []

            def to_bib_maker(e):
                self.text = "ページ作成中..."
                self.style = ft.ButtonStyle(
                    bgcolor=ft.colors.GREEN,
                    side=ft.BorderSide(2, ft.colors.BLUE),
                    shape=ft.RoundedRectangleBorder(radius=1),
                )
                self.update()
                if self.__view_make_bib is None:
                    self.__view_make_bib = UI_make_bibfile.view_bib_maker()
                else:
                    while len(UI_input_doi.list_un_added_papers)>0:
                        self.__view_make_bib.add_new_paper_from_out(UI_input_doi.list_un_added_papers.pop())

                page.views.append(self.__view_make_bib)
                page.go(self.__view_make_bib.route)
                print(page.route)
                self.text = "bibtex 出力ページ"
                self.style = None
                self.update()

            self.on_click = to_bib_maker

    button_move_window = Button_move_window()
    view_input = UI_input_doi.View_input_doi()
    view_input.set_button_to_appbar(button_move_window)
    page.views.append(view_input)
    page.update()

    def view_pop(e):
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)

    def route_change(route):
        pass

    page.on_view_pop = view_pop
    page.on_route_change = route_change
    page.update()


ft.app(main)

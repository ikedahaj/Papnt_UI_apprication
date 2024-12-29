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
                    self.__view_make_bib = UI_make_bibfile.view_bib_maker(
                        [button_change_theme]
                    )
                else:
                    while len(UI_input_doi.list_un_added_papers) > 0:
                        self.__view_make_bib.add_new_paper_from_out(
                            UI_input_doi.list_un_added_papers.pop()
                        )

                page.views.append(self.__view_make_bib)
                page.go(self.__view_make_bib.route)
                print(page.route)
                self.text = "bibtex 出力ページ"
                self.style = None
                self.update()

            self.on_click = to_bib_maker

    class Dialog(ft.AlertDialog):
        def __init__(
            self,
            modal=False,
            title=None,
            content=None,
            actions=None,
            bgcolor=None,
            elevation=None,
            icon=None,
            open=False,
            title_padding=None,
            content_padding=None,
            actions_padding=None,
            actions_alignment=None,
            shape=None,
            inset_padding=None,
            icon_padding=None,
            action_button_padding=None,
            surface_tint_color=None,
            shadow_color=None,
            icon_color=None,
            scrollable=None,
            actions_overflow_button_spacing=None,
            alignment=None,
            content_text_style=None,
            title_text_style=None,
            clip_behavior=None,
            semantics_label=None,
            on_dismiss=None,
            ref=None,
            disabled=None,
            visible=None,
            data=None,
            adaptive=None,
        ):
            super().__init__(
                modal,
                title,
                content,
                actions,
                bgcolor,
                elevation,
                icon,
                open,
                title_padding,
                content_padding,
                actions_padding,
                actions_alignment,
                shape,
                inset_padding,
                icon_padding,
                action_button_padding,
                surface_tint_color,
                shadow_color,
                icon_color,
                scrollable,
                actions_overflow_button_spacing,
                alignment,
                content_text_style,
                title_text_style,
                clip_behavior,
                semantics_label,
                on_dismiss,
                ref,
                disabled,
                visible,
                data,
                adaptive,
            )
            self.on_dismiss = self.clean_dismissed

        def open_dialog(self):
            page.open(self)

        def clean_dismissed(self, e):
            self.content = ft.Column()

    class switch_light_dark_theme(ft.FloatingActionButton):
        def __init__(self):
            super().__init__()
            self._theme = page.theme_mode
            self.icon = (
                ft.icons.LIGHT_MODE
                if self._theme == ft.ThemeMode.LIGHT
                else ft.icons.DARK_MODE
            )
            self.tooltip = (
                "ダークモードへ変更"
                if self._theme == ft.ThemeMode.LIGHT
                else "ライトモードへ変更"
            )
            self.on_click = self.__on_click_switch_light_dark

        def __on_click_switch_light_dark(self, e):
            if page.theme_mode == ft.ThemeMode.LIGHT:
                page.theme_mode = ft.ThemeMode.DARK
                self.icon = ft.icons.DARK_MODE
                self.tooltip = "ライトモードへ変更"
            else:
                page.theme_mode = ft.ThemeMode.LIGHT
                self.icon = ft.icons.LIGHT_MODE
                self.tooltip = "ダークモードへ変更"
            # self.update()
            page.update()

    button_change_theme = switch_light_dark_theme()
    dialog_arXiv_check = Dialog(
        title=ft.Text("arXiv論文の出版チェック"),
        adaptive=True,
        actions=[
            ft.TextButton("close", on_click=lambda e: page.close(dialog_arXiv_check))
        ],
        content=ft.Column(),
    )
    button_move_window = Button_move_window()
    view_input = UI_input_doi.View_input_doi(dialog_arXiv_check, [button_change_theme])
    view_input.set_button_to_appbar(button_move_window)
    page.views.append(view_input)
    page.update()

    # page.theme_mode=ft.ThemeMode.LIGHT
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

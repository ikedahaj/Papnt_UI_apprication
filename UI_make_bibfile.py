from operator import truediv
from re import split
import typing
import os
import time
from anyio import value
import flet as ft
import configparser
import bibtexparser.bwriter
import bibtexparser.bibdatabase
import arxiv
import papnt

import papnt.database
import papnt.cli
import papnt.misc
import papnt.mainfunc
import papnt.notionprop as pap_prop
import papnt.prop2entry as pap_pr2en

import expand_papnt


# -----------------------------------------------------------------------------
class _Papers_List(ft.SearchBar):
    def __init__(self, input_list: list, add_list):
        """bibに追加する論文を選択するための入力フォーム

        Args:
            input_list (list): 未選択の要素。notionの"results"をそのまま入れる
            add_list (function): 要素を下に追加する関数。第一引数に表示するテキスト、第二引数にnotionのresultをとる
        """
        super().__init__()
        # anchor=ft.SearchBar()
        self.__PL_init_list = input_list
        self.__PL_select_flag = "Name"
        self.__PL_listview = ft.ListView(
            controls=[
                ft.ListTile(
                    title=ft.Text(
                        expand_papnt.access_notion_prop_value(
                            name, self.__PL_select_flag
                        )
                    ),
                    data=name,
                    on_click=self.__close_anchor,
                )
                for name in input_list
            ]
        )
        self.view_elevation = 4
        self.controls = [self.__PL_listview]
        self.bar_hint_text = "bibファイルに加える論文を選択"
        self.view_hint_text = self.bar_hint_text
        self.autofocus = False
        self.on_tap = self.__handle_tap
        self.on_change = self.__PL_handle_change
        self.__PL_add_list_to_out = add_list

    def __PL_sort_strings(self, B):
        starts_with_B = []
        includes_B = []
        does_not_start_with_B = []
        for str in self.__PL_listview.controls:
            if str.title.value.lower().startswith(B.lower()):
                starts_with_B.append(str)
            elif B.lower() in str.title.value.lower():
                includes_B.append(str)
            else:
                does_not_start_with_B.append(str)
        self.__PL_listview.controls = starts_with_B + includes_B + does_not_start_with_B

    def __PL_update_listview(self, texts_list):
        self.__PL_listview.clean()
        new_controls = []
        for name in texts_list:
            new_controls.append(
                ft.ListTile(
                    title=ft.Text(
                        expand_papnt.access_notion_prop_value(
                            name, self.__PL_select_flag
                        )
                    ),
                    on_click=self.__close_anchor,
                    data=name,
                )
            )
        self.__PL_listview.controls = new_controls

    def __close_anchor(self, e):
        text = e.control.title.value
        self.close_view(text)
        time.sleep(0.05)
        datas = e.control.data
        # print(datas)
        self.__PL_add_list_to_out(text, datas)
        self.__PL_listview.controls.remove(e.control)
        self.__PL_init_list.remove(datas)
        self.value = None
        self.update()

    def __handle_tap(self, e):
        self.open_view()

    def __PL_handle_change(self, e):
        self.__PL_sort_strings(e.data)
        if e.data == "":
            self.__PL_update_listview(self.__PL_init_list)
        self.update()

    def PL_change_prop_name(self, propname):
        self.__PL_select_flag = propname
        for name in self.__PL_listview.controls:
            name.title.value = expand_papnt.access_notion_prop_value(
                name.data, propname
            )
        self.update()

    def add_new_props(self, new_prop: dict):
        self.__PL_init_list.insert(0, new_prop)
        self.__PL_listview.controls.insert(
            0,
            ft.ListTile(
                title=ft.Text(
                    expand_papnt.access_notion_prop_value(
                        new_prop, self.__PL_select_flag
                    )
                ),
                on_click=self.__close_anchor,
                data=new_prop,
            ),
        )

    def PL_get_init_list(self) -> typing.List[dict]:
        return self.__PL_init_list


class _Bib_File_Name(ft.Row):
    def __init__(
        self,
        text_list: list,
        add_Paper_List_New_Cite_in_prop,
        config,
        funk_enable_input,
    ):
        """出力するbibファイルの候補を出して、ファイル名を入れる関数。

        Args:
            text_list (list): 最初に提示するファイル名の候補
            add_Paper_List_New_Cite_in_prop (function(str)): prop名を入力したときに、元から指定されていた論文を候補に表示する関数。
                                                                引数はbibファイル名
        """
        super().__init__()
        # anchor=ft.SearchBar()
        self.__text_if_no_input="bibファイル名を入力してください"
        self.BFN_path_config = papnt.__path__[0] + "/config.ini"
        self._config = config
        self._config.read(self.BFN_path_config)
        saved_filename = self._config["misc"].get("filename_save_bib")
        self.value = saved_filename
        self.__funk_add_Paper_List_update_prop = add_Paper_List_New_Cite_in_prop
        self.__BFN_listview = ft.ListView()
        self.__text_list = text_list
        self.__BFN_listview = ft.ListView(
            controls=[
                ft.ListTile(title=ft.Text(name), on_click=self.__close_anchor)
                for name in text_list
            ]
        )
        self.__BFN_serBar = ft.SearchBar(
            view_elevation=4,
            divider_color=ft.colors.AMBER,
            bar_hint_text=self.__text_if_no_input,
            view_hint_text=self.__text_if_no_input,
            on_change=self.__handle_change,
            on_submit=self.__handle_submit,
            on_tap=self.__handle_tap,
            controls=[self.__BFN_listview],
            value=self.value
        )
        text = ft.Text(visible=False, value=self.value)
        button = ft.FloatingActionButton(
            icon=ft.icons.EDIT, mini=True, on_click=self.__reset_anchor, visible=False
        )
        self.controls = [self.__BFN_serBar, text, button]
        self.BFN_flag_decided_file_name = (
            (saved_filename is not None)
            and (saved_filename != "''")
            and (saved_filename != "")
        )
        # print(self.BFN_flag_decided_file_name)
        if self.BFN_flag_decided_file_name:
            self.__BFN_invisible_input()
        else:
            self.__BFN_visible_input()
        self.BFN_funk_enable_input = funk_enable_input

    def __BFN_visible_input(self):
        # 入力を受け入れる状態;
        self.controls[0].visible = True
        self.controls[1].visible = False
        self.controls[2].visible = False

    def __BFN_invisible_input(self):
        # 入力を受け付けない状態;
        self.controls[0].visible = False
        self.controls[1].visible = True
        self.controls[2].visible = True

    def __BFN_update_listview(self, texts_list):
        # 入力候補を更新;
        new_controls = []
        for name in texts_list:
            new_controls.append(
                ft.ListTile(title=ft.Text(name), on_click=self.__close_anchor)
            )
        self.__BFN_listview.controls = new_controls

    def __close_anchor(self, e):
        text = e.control.title.value
        self.__BFN_serBar.close_view(text)
        self.__BFN_serBar.data = False
        import time

        time.sleep(0.05)
        self.__handle_submit(e)

    def __handle_tap(self, e):
        self.__BFN_serBar.open_view()
        self.__BFN_serBar.data = True

    def __handle_change(self, e):
        def divide_lists(list, head_text: str):
            match_head = []
            not_match_head = []
            for name in list:
                if name.lower().startswith(head_text.lower()):
                    match_head.append(name)
                else:
                    not_match_head.append(name)
            return match_head + not_match_head

        if e.data == "":
            strings2 = self.__text_list
        else:
            strings2 = divide_lists(self.__text_list, e.data)
        self.__BFN_update_listview(strings2)
        self.update()

    def __handle_submit(self, e):
        new_text = self.controls[0].value
        if new_text not in self.__text_list and new_text is not None and new_text != "":
            self.__text_list.insert(0, new_text)
            self.__BFN_listview.controls.insert(
                0, ft.ListTile(title=ft.Text(new_text), on_click=self.__close_anchor)
            )
            # self.controls[0].controls=[self.__BFN_listview]
        if self.__BFN_serBar.data:
            # self.__BFN_serBar.close_view(new_text)
            self.controls[0].close_view(new_text)
            self.__BFN_serBar.data = False
            self.update()
            import time

            time.sleep(0.05)
            self.__handle_submit(e)
            return
        self.__BFN_invisible_input()
        self.controls[1].value =self.__text_if_no_input if new_text==""else new_text
        self.update()
        self.value = new_text
        self.__funk_add_Paper_List_update_prop(self.value)
        if new_text is None or new_text == "''" or new_text == "":
            self.BFN_flag_decided_file_name = False
        else:
            self.BFN_flag_decided_file_name = True
        self._config["misc"]["filename_save_bib"] = new_text
        with open(self.BFN_path_config, "w") as configfile:
            self._config.write(configfile, True)
        self.BFN_funk_enable_input()
        self.update()

    def __reset_anchor(self, e):
        # self.__BFN_serBar.controls=[self.__BFN_listview]
        self.__BFN_visible_input()
        self.update()
        # self.__BFN_update_listview(self.__text_list)
        self.__BFN_serBar.open_view()
        self.__BFN_serBar.data = True


class _Get_Folder_Name(ft.SearchBar):
    def __init__(self, foldername_init: str | None, funk_decide):
        """bibファイルを出すフォルダー名を入力する

        Args:
            foldername_init (str | None): フォルダ名の初期値
            funk_decide (function): submitするときに呼ぶ関数。引数はなし
        """
        super().__init__()
        # anchor=ft.SearchBar()
        self.value = None if foldername_init == "''" else foldername_init
        self.GFN_folder_name = self.value
        self.__GFN_listview = ft.ListView(controls=[])
        self.view_elevation = 4
        self.controls = [self.__GFN_listview]
        self.bar_hint_text = "bibファイルを出力するフォルダ名を入力"
        self.view_hint_text = self.bar_hint_text + "/を入力することで次の候補が出現"
        self.on_tap = self.__handle_tap
        self.on_change = self.__GFN_handle_change
        self.on_submit = self.__handle_submit
        self.view_trailing = [
            ft.FloatingActionButton(icon=ft.icons.DONE, on_click=self.__clicked_submit)
        ]
        self.__GFN_list_suggest_folder = []
        self.__function_decide = funk_decide

    def __GFN_sort_strings(self, B):
        starts_with_B = []
        includes_B = []
        does_not_start_with_B = []
        for str in self.__GFN_list_suggest_folder:
            if str.lower().startswith(B.lower()):
                starts_with_B.append(str)
            elif B.lower() in str.lower():
                includes_B.append(str)
            else:
                does_not_start_with_B.append(str)
        starts_with_B.sort()
        includes_B.sort()
        does_not_start_with_B.sort()
        self.__GFN_list_suggest_folder = (
            starts_with_B + includes_B + does_not_start_with_B
        )

    def __GFN_update_listview(self, texts_list):
        # self.__GFN_listview.clean()
        new_controls = []
        for name in texts_list:
            new_controls.append(
                ft.ListTile(title=ft.Text(name), on_click=self.__tiles_clicked)
            )
        self.__GFN_listview.controls = new_controls

    def __GFN_update_suggest_folder(self, path_dir):
        self.__GFN_list_suggest_folder = [
            f for f in os.listdir(path_dir) if os.path.isdir(os.path.join(path_dir, f))
        ]
        self.__GFN_update_listview(self.__GFN_list_suggest_folder)

    def __tiles_clicked(self, e):
        text = e.control.title.value
        self.GFN_folder_name += text + "/"
        self.value = self.GFN_folder_name
        self.__GFN_update_suggest_folder(self.value)
        self.focus()
        self.update()

    def GFN_update_value(self, new_value: str):
        """表示さてれている文字列を変更する

        Args:
            new_value (str): 変更後の文字列
        """
        # print(new_value)
        if new_value is None:
            self.__GFN_listview.clean()
        elif new_value == "":
            self.__GFN_listview.clean()
        elif new_value[-1] == "/":
            self.GFN_folder_name = new_value
            self.__GFN_update_suggest_folder(new_value)
        else:
            split_value = new_value.split("/")
            now_folder = ""
            for i in range(len(split_value) - 1):
                now_folder += split_value[i] + "/"
            self.GFN_folder_name = now_folder
            self.__GFN_update_suggest_folder(now_folder)
            # print(split_value)
            next_folder = split_value[-1]
            # print(next_folder)
            self.__GFN_sort_strings(next_folder)
            self.__GFN_update_listview(self.__GFN_list_suggest_folder)
        self.update()

    def __GFN_handle_change(self, e):
        now_value: str | None = e.data
        self.GFN_update_value(now_value)

    def __handle_tap(self, e):
        self.open_view()

    def __GFN_Confirm_name(self):
        self.close_view(self.value)
        time.sleep(0.05)
        self.__function_decide()

    def __handle_submit(self, e):
        self.__GFN_Confirm_name()

    def __clicked_submit(self, e):
        self.__GFN_Confirm_name()


class _Edit_Database(ft.Row):
    def __init__(self, config, funk_enable_input):
        """bibファイルを出力するフォルダ名を入手する
        初期値はpapnt/config.iniから持ってくる
        """
        super().__init__()
        self.__text_if_no_input="bibファイルを出力するフォルダ名を入力してください"
        self.ED_path_config = papnt.__path__[0] + "/config.ini"
        self._config = config
        self._config.read(self.ED_path_config)
        saved_dirname = self._config["misc"]["dir_save_bib"]
        saved_dirname = None if saved_dirname=="''" else saved_dirname
        self.ED_text_dir_save_bibfile_decided = ft.Text(
            value=saved_dirname, expand=True
        )
        self.ED_button_open_edit = ft.FloatingActionButton(
            icon=ft.icons.EDIT, on_click=self.__ED_clicked_open_edit_view, mini=True
        )
        self.ED_text_dir_save_bibfile_input = _Get_Folder_Name(
            saved_dirname, self.__ED_clicked_done_edit
        )
        self.controls = [
            self.ED_text_dir_save_bibfile_decided,
            self.ED_button_open_edit,
            self.ED_text_dir_save_bibfile_input,
        ]
        self.ED_text_dir_save_bibfile_input.visible = False
        self.ED_flag_decided_folder_name = (
            (saved_dirname is not None)
            and (saved_dirname != "''")
            and (saved_dirname != "")
        )
        if not self.ED_flag_decided_folder_name:
            self.ED_text_dir_save_bibfile_decided.visible=False
            self.ED_button_open_edit.visible=False
            self.ED_text_dir_save_bibfile_input.visible=True
        self.ED_enable_input = funk_enable_input

    def __ED_clicked_open_edit_view(self, e):
        self.ED_text_dir_save_bibfile_decided.visible = False
        self.ED_button_open_edit.visible = False
        self.ED_text_dir_save_bibfile_input.visible = True
        now_text=None if self.ED_text_dir_save_bibfile_decided.value==self.__text_if_no_input else self.ED_text_dir_save_bibfile_decided.value
        self.ED_text_dir_save_bibfile_input.GFN_update_value(
            now_text
        )
        self.ED_text_dir_save_bibfile_input.open_view()
        self.update()

    def __ED_clicked_done_edit(self):
        self.ED_text_dir_save_bibfile_decided.visible = True
        self.ED_button_open_edit.visible = True
        self.ED_text_dir_save_bibfile_input.visible = False
        new_text = self.ED_text_dir_save_bibfile_input.value
        self.ED_text_dir_save_bibfile_decided.value = new_text
        self._config["misc"]["dir_save_bib"] = new_text
        with open(self.ED_path_config, "w") as configfile:
            self._config.write(configfile, True)
        if new_text is not None:
            self.ED_flag_decided_folder_name = True
        self.ED_enable_input()
        if new_text =="":
            self.ED_text_dir_save_bibfile_decided.value=self.__text_if_no_input
        print(self.ED_text_dir_save_bibfile_input.value)
        self.update()


class _Text_Paper(ft.Row):
    def __init__(self, text: str, notion_result: dict, add_to_input_list):
        """候補として追加するテキスト。notionに追加するのは実行する時

        Args:
            text (str): 最初に表示するテキスト
            notion_result (dict): 追加する論文のpage_prop
            add_to_input_list (function): 消す時に呼ぶ関数。引数は(dict:notion_result)
        """
        super().__init__()
        self.value = text
        self.data = notion_result
        self.__TP_add_to_input_list = add_to_input_list
        self.__TP_display_text = ft.Text(value=self.value)
        self.__TP_delete_button = ft.FloatingActionButton(
            icon=ft.icons.DELETE, on_click=self.__delete_clicked
        )
        self.controls = [self.__TP_display_text, self.__TP_delete_button]

    def change_text(self, propname):
        new_text = expand_papnt.access_notion_prop_value(self.data, propname)
        self.value = new_text
        self.__TP_display_text.value = new_text
        self.update()

    def get_notion_page(self) -> dict:
        return self.data

    def __delete_clicked(self, e):
        self.__TP_delete_button.shape = ft.ContinuousRectangleBorder()
        self.__TP_delete_button.bgcolor = ft.colors.GREEN
        self.__TP_delete_button.icon = ft.icons.RUN_CIRCLE
        self.update()
        self.__TP_add_to_input_list(self.data, self)


class view_bib_maker(ft.View):
    def __init__(self, appbar_actions: list,dialog):
        super().__init__()
        self.route = "/make_bib_file"
        self.appbar = ft.AppBar(title=ft.Text("make_bib_file"), actions=appbar_actions)

        # コンフィグファイルとnotionデータベースの準備;
        path_config = papnt.__path__[0] + "/config.ini"
        self.__notion_configs = papnt.misc.load_config(path_config)
        self._notion_config_simple = configparser.ConfigParser(
            comment_prefixes="/", allow_no_value=True
        )

        self.database = papnt.database.Database(papnt.database.DatabaseInfo())
        response = self.database.notion.databases.query(self.database.database_id)
        self.results = response["results"]

        # モジュールの宣言;
        self.select_prop_flag = ft.Dropdown(value="Name", width=150)
        self.Paper_list = ft.Column(scroll=ft.ScrollMode.HIDDEN, expand=True)
        self._input_Paper_List = _Papers_List(self.results, self._add_Paper_list)
        self.run_button = ft.ElevatedButton(
            "bibファイルを出力する", on_click=self.__onclick_makebib
        )

        # 基礎設定:データベースの設定;
        # bibファイル名の候補を出す;
        filename_list = []
        for name in self.results:
            next_list = name["properties"][
                self.__notion_configs["propnames"]["output_target"]
            ]["multi_select"]
            for next_name in next_list:
                if not next_name["name"] in filename_list:
                    filename_list.append(next_name["name"])
        self._Bib_Name = _Bib_File_Name(
            filename_list,
            self.add_Paper_List_New_Cite_in_prop,
            self._notion_config_simple,
            self.enable_if_folder_and_file_name_are_decided,
        )
        self.edit_database = _Edit_Database(
            self._notion_config_simple,
            self.enable_if_folder_and_file_name_are_decided,
        )
        self.controls.append(
            ft.Row(
                controls=[self.edit_database, self._Bib_Name],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            )
        )
        # self.scroll=ft.ScrollMode.HIDDEN
        # 構成要素：入力とか;
        self.select_prop_flag.on_change = self._dropdown_changed
        self.select_prop_flag.options = [
            ft.dropdown.Option(key=propname)
            for propname in self.__notion_configs["propnames"].values()
        ]
        self.select_prop_flag.options.insert(0, ft.dropdown.Option(key="Name"))
        self._input_Paper_List.bar_leading = self.select_prop_flag
        self._input_Paper_List.disabled = True
        # self.cnt_button=ft.TextButton("cnt",on_click=self.on_click_cnt)
        # 要素を画面に追加;
        self.controls.append(self._input_Paper_List)
        self.controls.append(self.run_button)
        self.controls.append(self.Paper_list)
        self.dialog_app=dialog
    def do_after_added_this_Control(self):
        # view_bib_makerを宣言した後最初に呼ぶ関数;
        self.change_button_style("init")
        self.enable_if_folder_and_file_name_are_decided()
        if (
            self.edit_database.ED_flag_decided_folder_name
            and self._Bib_Name.BFN_flag_decided_file_name
        ):
            self.add_Paper_List_New_Cite_in_prop(self._Bib_Name.value)

    def enable_if_folder_and_file_name_are_decided(self):
        # フォルダ名とファイル名が決まったら有効化する;
        if (
            self.edit_database.ED_flag_decided_folder_name
            and self._Bib_Name.BFN_flag_decided_file_name
        ):
            self._input_Paper_List.disabled = False
            self.run_button.disabled = False
        else:
            self._input_Paper_List.disabled = True
            self.run_button.disabled = True
        self.update()

    # ----------------------------------------
    # 外から新しいpropを渡す;
    def add_new_paper_from_out(self, new_paper: dict):
        """bib_makeクラスの外から新しいpropを渡す

        Args:
            new_paper (dict): 追加する論文の情報。notion.createに渡す辞書
        """
        self._input_Paper_List.add_new_props(new_paper)

    # --------------------------------------------------
    # select_prop_flag用の関数;
    def _change_prop_name(self, propname: str) -> None:
        item: type[_Text_Paper]
        for item in self.Paper_list.controls:
            item.change_text(propname)
        self._input_Paper_List.PL_change_prop_name(propname)
        self.Paper_list.update()

    def _dropdown_changed(self, e):
        self._change_prop_name(e.data)

    def _add_prop_to_input_list(self, notion_page):
        self._input_Paper_List.add_new_props(notion_page)

    # ---------------------------------------------------
    # 候補のテキストを追加する;
    def _add_Paper_list(self, text_value, notion_result: dict):
        def __clicked_delete_text(page_prop: dict, item_self: _Text_Paper):
            self._input_Paper_List.add_new_props(page_prop)
            self._delete_Cite_in_prop_from_notion(page_prop)
            self.Paper_list.controls.remove(item_self)
            self.update()

        new_text_cl = _Text_Paper(text_value, notion_result, __clicked_delete_text)
        self.Paper_list.controls.insert(0, new_text_cl)
        self.Paper_list.update()

    # _add_Paper_list内のdeleteボタン用の関数;
    # 候補に挙げていた論文を候補から消すときに、notion側のものも消す;
    def _delete_Cite_in_prop_from_notion(self, page_prop: dict):
        for bib_filename_prev in page_prop["properties"][
            self.__notion_configs["propnames"]["output_target"]
        ]["multi_select"]:
            if bib_filename_prev["name"] == self._Bib_Name.value:
                page_prop["properties"][
                    self.__notion_configs["propnames"]["output_target"]
                ]["multi_select"].remove(bib_filename_prev)
                cite_in_items = [
                    {"name": each_filename["name"]}
                    for each_filename in page_prop["properties"][
                        self.__notion_configs["propnames"]["output_target"]
                    ]["multi_select"]
                    if each_filename["name"] != self._Bib_Name.value
                ]
                next_prop = {
                    self.__notion_configs["propnames"]["output_target"]: {
                        "multi_select": cite_in_items
                    }
                }
                try:
                    self.database.update(page_prop["id"], next_prop)
                except:
                    import sys

                    exc = sys.exc_info()
                    print(str(exc[1]))
                    self.run_button.text = str(exc[1])
                    self.run_button.style = ft.ButtonStyle(bgcolor=ft.colors.RED)
                    self.update()
                break

    def add_Paper_List_New_Cite_in_prop(self, new_cite_in_value: str):
        """
        bibファイル名を変えた時に呼ばれる。
        _input_Paper_List の中から、新しいbibファイル名を登録されているものを探して、それを
        候補の列に入れる。

        Args:
            new_cite_in_value (str): 新しいbibファイルの名前
        """
        # 全てのリストから加えていないものを見つける
        # bibファイル名を変えたときに呼ぶ;
        un_added_list = self._input_Paper_List.PL_get_init_list()
        for un_added_paper in un_added_list:
            if any(
                [
                    cite_in_item["name"] == new_cite_in_value
                    for cite_in_item in un_added_paper["properties"][
                        self.__notion_configs["propnames"]["output_target"]
                    ]["multi_select"]
                ]
            ):
                self._add_Paper_list(
                    expand_papnt.access_notion_prop_value(
                        un_added_paper, self.select_prop_flag.value
                    ),
                    un_added_paper,
                )


    def change_button_style(
        self,
        process: typing.Literal["init", "processing", "warn", "done"],
        warn_text=None,
    ):
        match process:
            case "init":
                self.run_button.text = "bibファイルを出力する"
                self.run_button.bgcolor=ft.colors.BLUE
                self.run_button.style = None
                self.run_button.on_click = self.__onclick_makebib
                self.run_button.disabled = False
            case "processing":
                self.run_button.text = "実行中..."
                self.run_button.style = ft.ButtonStyle(
                    bgcolor=ft.colors.PURPLE,
                    shape=None,
                    # color=ft.colors.DEEP_PURPLE,
                )
                self.run_button.icon=ft.ProgressRing(width=16, height=16)
                self.run_button.disabled = True
            case "warn":
                self.run_button.text = warn_text + "\n クリックして戻る"
                self.run_button.style = ft.ButtonStyle(bgcolor=ft.colors.RED)
                self.run_button.disabled = False
                self.run_button.on_click = lambda e: self.change_button_style("init")
            case "done":
                self.run_button.disabled = False
                self.run_button.text = "出力成功\nクリックして次の出力へ"
                self.run_button.style = ft.ButtonStyle(
                    # color=ft.colors.GREEN,
                    bgcolor=ft.colors.GREEN_100,
                    shape=ft.BeveledRectangleBorder(radius=0),
                    side=ft.BorderSide(2, ft.colors.GREEN_500),
                )
                self.run_button.on_click = lambda e: self.change_button_style("init")
        self.update()
    def __add_dialog_titles(self,titles):
        self.dialog_app.open_dialog("出版されたarXiv論文が\n存在します。\n追加ページで更新して下さい")
        for title in titles:
            self.dialog_app.content.controls.append(ft.Text(title))
        self.update()
        self.dialog_app.update()
    def __onclick_makebib(self, e):
        # 実行中を表すUIの変更;
        self.change_button_style("processing")
        bib_name = self._Bib_Name.value
        list_papers = [items.get_notion_page() for items in self.Paper_list.controls]
        try:
            list_published_arXiv_papers= expand_papnt.makebib(
                bib_name, list_papers, self.__notion_configs, self.database
            )
        except:
            import sys

            exc = sys.exc_info()
            self.change_button_style("warn", str(exc[1]))
            return
        self.change_button_style("done")
        if len(list_published_arXiv_papers)>0:
            self.__add_dialog_titles(list_published_arXiv_papers)


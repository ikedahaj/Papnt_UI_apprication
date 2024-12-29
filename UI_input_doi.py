# doiを入力する画面;
import time
import typing
import sys
import os

import flet as ft
import configparser

import papnt

import papnt.mainfunc
import papnt.misc
import papnt.database
import papnt.notionprop

import UI_make_bibfile as uibib
import expand_papnt

# global list of added papers
list_un_added_papers: list[dict] = []

_dbinfo = papnt.database.DatabaseInfo()
_database = papnt.database.Database(_dbinfo)
_path_config = papnt.__path__[0] + "/config.ini"
_config = papnt.misc.load_config(_path_config)


# doiからnotionに論文情報を追加する;
def __create_records_from_doi(doi: str):
    prop = papnt.notionprop.NotionPropMaker().from_doi(doi, _config["propnames"])
    prop |= {"info": {"checkbox": True}}
    try:
        result_create = _database.notion.pages.create(
            parent={"database_id": _database.database_id}, properties=prop
        )
    except Exception as e:
        print(str(e))
        name = prop["Name"]["title"][0]["text"]["content"]
        raise ValueError(f"Error while updating record: {name}")
    else:
        list_un_added_papers.append(result_create)


# doiをフォーマットして、notion内の形式と合わせる;
def __format_doi(doi: str) -> str:
    if "https://" in doi:
        doi = doi.replace("https://", "")
    if "doi.org" in doi:
        doi = doi.replace("doi.org/", "")
    if " " in doi:
        doi = doi.replace(" ", "")
    if ("arXiv" in doi) and doi[-2] == "v":

        doi = doi[:-2]
    elif ("arXiv" in doi) and doi[-3] == "v":
        doi = doi[:-3]
    return doi


# データベースにトークンキーとデータベースIDを追加するところ;
class _Edit_Database(ft.Row):
    def __init__(self):
        super().__init__()
        self.__ED_config = configparser.ConfigParser(
            comment_prefixes="/", allow_no_value=True
        )
        self.__ED_config.read(_path_config)
        self.__ED_text_tokenkey = ft.Text(
            value=(
                None
                if self.__ED_config["database"]["tokenkey"] == "''"
                else self.__ED_config["database"]["tokenkey"]
            )
        )
        self.__ED_text_database_id = ft.Text(
            value=(
                None
                if self.__ED_config["database"]["database_id"] == "''"
                else self.__ED_config["database"]["database_id"]
            )
        )
        self.__ED_buttun_edit = ft.FloatingActionButton(
            icon=ft.icons.EDIT, on_click=self.__ED_clicked_text_edit
        )
        self.__ED_buttun_edit.mini = True
        self.__ED_text_input_database_id = ft.TextField(
            value=self.__ED_text_database_id.value,
            hint_text="database_id",
            visible=False,
        )
        self.__ED_text_input_tokenkey = ft.TextField(
            value=self.__ED_text_tokenkey.value, hint_text="tokenkey", visible=False
        )
        self.__ED_buttun_done_edit = ft.FloatingActionButton(
            icon=ft.icons.DONE, on_click=self.__ED_clicked_done_edit, visible=False
        )
        self.controls = [
            self.__ED_buttun_edit,
            self.__ED_text_tokenkey,
            self.__ED_text_database_id,
            self.__ED_buttun_done_edit,
            self.__ED_text_input_tokenkey,
            self.__ED_text_input_database_id,
        ]

    def __ED_clicked_text_edit(self, e):
        self.__ED_text_input_database_id.visible = True
        self.__ED_text_input_tokenkey.visible = True
        self.__ED_buttun_done_edit.visible = True
        self.__ED_text_database_id.visible = False
        self.__ED_text_tokenkey.visible = False
        self.__ED_buttun_edit.visible = False
        self.update()

    def __ED_clicked_done_edit(self, e):
        self.__ED_text_database_id.value = self.__ED_text_input_database_id.value
        self.__ED_text_tokenkey.value = self.__ED_text_input_tokenkey.value
        self.__ED_text_input_database_id.visible = False
        self.__ED_text_input_tokenkey.visible = False
        self.__ED_buttun_done_edit.visible = False
        self.__ED_text_database_id.visible = True
        self.__ED_text_tokenkey.visible = True
        self.__ED_buttun_edit.visible = True
        self.__ED_config["database"]["database_id"] = self.__ED_text_database_id.value
        self.__ED_config["database"]["tokenkey"] = self.__ED_text_tokenkey.value
        with open(self._path_config, "w") as configfile:
            self.__ED_config.write(configfile, True)
        self.update()


# 編集可能なテキスト。
# ボタンには、
#       1.編集するためのボタン
#       2.テキストを消すボタン
#       3.１行だけ実行するボタン　がある;
class _Editable_Text(ft.Row):
    def __init__(
        self,
        input_value: str,
        page_id: str | None = None,
        flag_show_button: bool = True,
    ):
        super().__init__()
        self.value = input_value
        self.content_page_id = page_id
        self.__ET_text = ft.Text()
        self.__ET_text.value = input_value
        self.__ET_state_icon = ft.Icon()
        __ET_button_edit = ft.IconButton(
            icon=ft.icons.EDIT, on_click=self.__ET_clicked_text_edit, icon_size=20
        )
        __ET_button_run = ft.IconButton(
            icon=ft.icons.RUN_CIRCLE, on_click=self.__ET_clicked_run_papnt, icon_size=20
        )
        __ET_button_delete = ft.IconButton(
            icon=ft.icons.DELETE, on_click=self.__ET_clicked_text_delete, icon_size=20
        )
        self.__ET_buttons_plain_text = ft.Row(
            controls=[__ET_button_edit, __ET_button_run, __ET_button_delete]
        )
        self.__ET_button_done_edit = ft.FloatingActionButton(
            icon=ft.icons.DONE, on_click=self.__ET_clicked_done_edit, visible=False
        )
        self.__ET_text_input = ft.TextField(
            value=self.value, on_submit=self.__ET_clicked_done_edit, visible=False
        )
        if flag_show_button:
            self.controls = [
                self.__ET_state_icon,
                self.__ET_text,
                self.__ET_buttons_plain_text,
                self.__ET_text_input,
                self.__ET_button_done_edit,
            ]
        else:
            self.controls = [self.__ET_state_icon, self.__ET_text]

    def __ET_switch_icon_and_progress(
        self, mode: typing.Literal["Icon", "Progress bar"]
    ):
        match mode:
            case "Icon":
                self.controls[0] = self.__ET_state_icon
            case "Progress bar":
                self.controls[0] = ft.ProgressRing(width=16, height=16)

    def __ET_clicked_text_edit(self, e):
        self.__ET_state_icon.visible = False
        self.__ET_text.visible = False
        self.__ET_buttons_plain_text.visible = False
        self.__ET_text_input.visible = True
        self.__ET_button_done_edit.visible = True
        self.__ET_text_input.value = self.__ET_text.value
        self.update()

    def __ET_clicked_text_delete(self, e):
        self.clean()

    def __ET_clicked_run_papnt(self, e):
        _run_papnt_doi(self)

    def __ET_clicked_done_edit(self, e):
        self.__ET_state_icon.visible = True
        self.__ET_text.visible = True
        self.__ET_buttons_plain_text.visible = True
        self.__ET_text_input.visible = False
        self.__ET_button_done_edit.visible = False
        self.__ET_text.value = self.__ET_text_input.value
        self.value = self.__ET_text.value
        self.update()

    def update_value(
        self,
        mode: typing.Literal["processing", "error", "succeed", "warn", "new"],
        input_value: str = "",
    ):
        """ETの文章を実行時に変える

        Args:
            mode (typing.Literal[&quot;processing&quot;,&quot;error&quot;,&quot;succeed&quot;,&quot;warn&quot;]): 状態：進行中、エラー発生、成功、警告
            input_value (str, optional): 表示する文字列. Defaults to "".
        """

        def change_bgcolor(color):
            self.__ET_text.bgcolor = color

        def change_text(input_value: str):
            self.value = input_value
            self.__ET_text.value = input_value

        self.__ET_switch_icon_and_progress("Icon")
        match mode:
            case "processing":
                self.__ET_switch_icon_and_progress("Progress bar")
                if input_value == "":
                    change_text("processing...")
                else:
                    change_text(input_value)
                # change_bgcolor(None)
            case "error":
                change_text(input_value)
                self.__ET_state_icon.name = ft.icons.ERROR
                self.__ET_state_icon.color = ft.colors.RED
            case "succeed":
                change_text(input_value)
                self.__ET_state_icon.name = ft.icons.DONE
                self.__ET_state_icon.color = ft.colors.GREEN
            case "warn":
                change_text(input_value)
                self.__ET_state_icon.name = ft.icons.WARNING
                self.__ET_state_icon.color = ft.colors.YELLOW
            case "new":
                change_text(input_value)
                self.__ET_state_icon.name = ft.icons.FIBER_NEW
                self.__ET_state_icon.color = ft.colors.GREEN
        self.update()


# テキスト１行のdoiからnotionに情報を追加する;
def _run_papnt_doi(now_text: _Editable_Text):
    doi = now_text.value
    if (
        "Already added" in doi
        or "Done" in doi
        or "processing..." in doi
        or "Error" in doi
    ):
        return
    doi = __format_doi(doi)
    now_text.value = doi
    now_text.update()
    now_text.update_value("processing")
    now_text.update()
    serch_flag = {"filter": {"property": "DOI", "rich_text": {"equals": doi}}}
    serch_flag["database_id"] = _database.database_id
    response = _database.notion.databases.query(**serch_flag)
    if len(response["results"]) != 0:
        now_text.update_value("warn", "Already added! " + doi)
        return
    time.sleep(0.1)
    try:
        __create_records_from_doi(doi)
    except:
        exc = sys.exc_info()
        now_text.update_value("error", "Error: " + str(exc[1]))
    else:
        now_text.update_value("succeed", "Done " + doi)


def _update_accepted_arXiv_paper(new_text: type[_Editable_Text]):
    """
    arXivの論文が他で出版されている場合、notionの値を更新する
    入力の .data に page_id を入れておく。

    Args:
        new_text (type[_Editable_Text]): アップデートするarXivの論文が入った
    """
    doi = new_text.value
    new_text.update_value("processing")
    try:
        print(new_text.value)
        new_doi =expand_papnt.check_arXiv_paper_accepted(doi)
    except:
        exc = sys.exc_info()
        new_text.update_value(mode="error", input_value="Error: " + str(exc[1]))
        print(str(exc[1]))
        return
    if new_doi is None:
        new_text.update_value(mode="succeed", input_value="no change: " + doi)
        return
    else:
        try:
            papnt.mainfunc._update_record_from_doi(_database,new_doi,new_text.content_page_id, _config["propnames"])
            new_text.update_value(mode="new", input_value="出版論文: " + new_doi)
        except:
            exc = sys.exc_info()
            new_text.update_value(mode="error", input_value="Error: " + str(exc[1]))
            print(str(exc[1]))


def _check_arXiv_published(dialog_arXiv_check):
    """arXivの論文のうちpublishされたものの情報を更新する

    Args:
        dialog_arXiv_check (ft.Dialog): ここで得た結果を載せる領域
    """
    filters = {
        "property": _config["propnames"]["journal"],
        "select": {"equals": "arXiv"},
    }
    response = _database.notion.databases.query(
        database_id=_database.database_id, filter=filters
    )
    if len(response["results"]) == 0:
        dialog_arXiv_check.content.controls.append(ft.Text("No arXiv paper"))
        dialog_arXiv_check.update()
        return
    # print(response)
    for pages in response["results"]:
        doi = expand_papnt.access_notion_prop_value(pages, _config["propnames"]["doi"])
        page_id = pages["id"]
        dialog_arXiv_check.content.controls.append(_Editable_Text(doi, page_id, False))
    dialog_arXiv_check.update()
    for each_text in dialog_arXiv_check.content.controls:
        _update_accepted_arXiv_paper(each_text)
    pass


# このページの内容;
class View_input_doi(ft.View):
    def __init__(self, dialog_arXiv_check, appbar_actions: list):
        super().__init__()

        def add_clicked(e):
            list_doi.controls.insert(
                0, _Editable_Text(input_value=input_text_doi.value)
            )
            input_text_doi.value = ""
            list_doi.update()
            self.update()
            input_text_doi.focus()

        def delete_clicked(e):
            list_doi.clean()
            self.update()
            input_text_doi.focus()

        # Enterキーを押されたら文字を加える.
        def add_entered(e):
            add_clicked(e)

        def run_clicked(e):
            for input_doi in list_doi.controls:
                _run_papnt_doi(input_doi)

        def on_clicked_check_arXiv(e):
            dialog_arXiv_check.open_dialog()
            # self.update()
            _check_arXiv_published(dialog_arXiv_check)

        self.route = "/"
        self.auto_scroll = True
        input_text_doi = ft.TextField(
            hint_text="Please input DOI",
            on_submit=add_entered,
            autofocus=True,
            expand=True,
        )
        add_button = ft.FloatingActionButton(icon=ft.icons.ADD, on_click=add_clicked)
        run_button = ft.FloatingActionButton(
            icon=ft.icons.RUN_CIRCLE, on_click=run_clicked
        )
        delete_button = ft.FloatingActionButton(
            icon=ft.icons.DELETE, on_click=delete_clicked
        )
        img = ft.Image(
            src=os.path.dirname(os.path.abspath(__file__))
            + "/arxiv-logomark-small.svg",
            fit=ft.ImageFit.CONTAIN,
            width=30,
            height=30,
        )
        arXiv_check_button = ft.FloatingActionButton(
            content=ft.Container(img),
            tooltip="arXivの論文が出版されている場合、notionの情報を更新する",
            on_click=on_clicked_check_arXiv,
        )
        # arXiv_check_button=ft.IconButton(icon=ft.icons.ABC)
        list_doi = ft.Column(scroll=ft.ScrollMode.HIDDEN, expand=True)
        # 画面に追加する;

        self.appbar = ft.AppBar(
            leading=ft.Icon(ft.icons.INPUT),
            title=ft.Text("論文追加"),
            bgcolor=ft.colors.SURFACE_VARIANT,
            actions=appbar_actions,
        )
        self.controls.append(_Edit_Database())
        self.controls.append(
            ft.Row(
                [input_text_doi, add_button],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            )
        )
        self.controls.append(ft.Row([run_button, delete_button, arXiv_check_button]))
        self.controls.append(list_doi)

    def set_button_to_appbar(self, button):
        if len(self.appbar.actions) == 0:
            self.appbar.actions = [button]
        else:
            self.appbar.actions.append(button)

# doiを入力する画面;
import time
import typing
import sys

import flet as ft
import configparser

import papnt

import papnt.misc
import papnt.database
import papnt.notionprop

# doiからnotionに論文情報を追加する;
def __create_records_from_doi(doi:str):
    dbinfo=papnt.database.DatabaseInfo()
    database=papnt.database.Database(dbinfo)
    path_config=papnt.__path__[0]+"/config.ini"
    config = papnt.misc.load_config(path_config)
    prop=papnt.notionprop.NotionPropMaker().from_doi(doi,config["propnames"])
    prop |= {'info': {'checkbox': True}}
    try:
        database.create(prop)
    except Exception as e:
        print(str(e))
        name = prop['Name']['title'][0]['text']['content']
        raise ValueError(f'Error while updating record: {name}')

# doiをフォーマットして、notion内の形式と合わせる;
def __format_doi(doi:str)->str:
    if "https://" in doi:
        doi=doi.replace("https://","")
    if "doi.org" in doi:
        doi=doi.replace("doi.org/","")
    if " " in doi:
        doi=doi.replace(" ","")
    if ("arXiv" in doi) and doi[-2]=="v":

        doi=doi[:-2]
    elif ("arXiv" in doi) and doi[-3]=="v":
        doi=doi[:-3]
    return doi

# データベースにトークンキーとデータベースIDを追加するところ;
class _Edit_Database(ft.Row):
    def __init__(self):
        super().__init__()
        self.__ED_path_config=papnt.__path__[0]+"/config.ini"
        self.config=configparser.ConfigParser(comment_prefixes='/', allow_no_value=True)
        self.config.read(self.__ED_path_config)
        self.__ED_text_tokenkey=ft.Text(value=(None if self.config["database"]["tokenkey"] =="''" else self.config["database"]["tokenkey"]) )
        self.__ED_text_database_id=ft.Text(value=(None if self.config["database"]["database_id"]=="''" else self.config["database"]["database_id"]))
        self.__ED_buttun_edit=ft.FloatingActionButton(icon=ft.icons.EDIT,on_click=self.__ED_clicked_text_edit)
        self.__ED_buttun_edit.mini=True
        self.__ED_text_input_database_id=ft.TextField(value=self.__ED_text_database_id.value,hint_text="database_id",visible=False)
        self.__ED_text_input_tokenkey=ft.TextField(value=self.__ED_text_tokenkey.value,hint_text="tokenkey",visible=False)
        self.__ED_buttun_done_edit=ft.FloatingActionButton(icon=ft.icons.DONE,on_click=self.__ED_clicked_done_edit,visible=False)
        self.controls=[self.__ED_buttun_edit,self.__ED_text_tokenkey,self.__ED_text_database_id,self.__ED_buttun_done_edit,self.__ED_text_input_tokenkey,self.__ED_text_input_database_id]
    def __ED_clicked_text_edit(self,e):
        self.__ED_text_input_database_id.visible=True
        self.__ED_text_input_tokenkey.visible=True
        self.__ED_buttun_done_edit.visible=True
        self.__ED_text_database_id.visible=False
        self.__ED_text_tokenkey.visible=False
        self.__ED_buttun_edit.visible=False
        self.update()

    def __ED_clicked_done_edit(self,e):
        self.__ED_text_database_id.value=self.__ED_text_input_database_id.value
        self.__ED_text_tokenkey.value=self.__ED_text_input_tokenkey.value
        self.__ED_text_input_database_id.visible=False
        self.__ED_text_input_tokenkey.visible=False
        self.__ED_buttun_done_edit.visible=False
        self.__ED_text_database_id.visible=True
        self.__ED_text_tokenkey.visible=True
        self.__ED_buttun_edit.visible=True
        self.config["database"]["database_id"]=self.__ED_text_database_id.value
        self.config["database"]["tokenkey"]=self.__ED_text_tokenkey.value
        with open(self.__ED_path_config, "w") as configfile:
            self.config.write(configfile, True)
        self.update()

# 編集可能なテキスト。
# ボタンには、
#       1.編集するためのボタン
#       2.テキストを消すボタン
#       3.１行だけ実行するボタン　がある;
class _Editable_Text(ft.Row):
    def __init__(self,input_value:str):
        super().__init__()
        self.value=input_value
        self.__ET_text=ft.Text()
        self.__ET_text.value=input_value
        self.__ET_state_icon=ft.Icon()
        __ET_button_edit=ft.IconButton(icon=ft.icons.EDIT,on_click=self.__ET_clicked_text_edit,icon_size=20)
        __ET_button_run=ft.IconButton(icon=ft.icons.RUN_CIRCLE,on_click=self.__ET_clicked_run_papnt,icon_size=20)
        __ET_button_delete=ft.IconButton(icon=ft.icons.DELETE,on_click=self.__ET_clicked_text_delete,icon_size=20)
        self.__ET_buttons_plain_text=ft.Row(controls=[__ET_button_edit,__ET_button_run,__ET_button_delete])
        self.__ET_button_done_edit=ft.FloatingActionButton(icon=ft.icons.DONE,on_click=self.__ET_clicked_done_edit,visible=False)
        self.__ET_text_input=ft.TextField(value=self.value,on_submit=self.__ET_clicked_done_edit,visible=False)
        self.controls=[self.__ET_state_icon,self.__ET_text,self.__ET_buttons_plain_text,self.__ET_text_input,self.__ET_button_done_edit]
    def __ET_clicked_text_edit(self,e):
        self.__ET_state_icon=False
        self.__ET_text.visible=False
        self.__ET_buttons_plain_text.visible=False
        self.__ET_text_input.visible=True
        self.__ET_button_done_edit.visible=True
    def __ET_clicked_text_delete(self,e):
        self.clean()

    def __ET_clicked_run_papnt(self,e):
        _run_papnt_doi(self)

    def __ET_clicked_done_edit(self,e):
        self.__ET_state_icon.visible=True
        self.__ET_text.visible=True
        self.__ET_buttons_plain_text.visible=True
        self.__ET_text_input.visible=False
        self.__ET_button_done_edit.visible=False
        self.__ET_text.value=self.__ET_text_input.value
        self.value=self.__ET_text.value
        self.update()
    def update_value(self,mode:typing.Literal["processing","error","succeed","warn"],input_value:str=""):
        def change_bgcolor(color):
            self.__ET_text.bgcolor=color
        def change_text(input_value:str):
            self.value=input_value
            self.__ET_text.value=input_value
        match mode:
            case "processing":
                if input_value=="":
                    change_text("processing...")
                else:
                    change_text(input_value)
                change_bgcolor(None)
            case "error":
                change_text(input_value)
                self.__ET_state_icon.name=ft.icons.ERROR
                self.__ET_state_icon.color=ft.colors.RED
            case "succeed":
                change_text(input_value)
                self.__ET_state_icon.name=ft.icons.DONE
                self.__ET_state_icon.color=ft.colors.GREEN
            case "warn":
                change_text(input_value)
                self.__ET_state_icon.name=ft.icons.WARNING
                self.__ET_state_icon.color=ft.colors.YELLOW
        self.update()

# テキスト１行のdoiからnotionに情報を追加する;
def _run_papnt_doi(now_text:_Editable_Text):
    doi=now_text.value
    if "Already added" in doi or "Done" in doi or "processing..." in doi or "Error" in doi:
        return
    doi=__format_doi(doi)
    now_text.value=doi
    now_text.update()
    now_text.update_value("processing")
    now_text.update()
    database=papnt.database.Database(papnt.database.DatabaseInfo())
    serch_flag={"filter":{"property":"DOI","rich_text":{"equals":doi}}}
    serch_flag["database_id"]=database.database_id
    print("fst")
    response=database.notion.databases.query(**serch_flag)
    print("scd")
    if len(response["results"])!=0:
        now_text.update_value("warn","Already added! "+doi)
        return
    time.sleep(0.1)
    try:
        __create_records_from_doi(doi)
    except:
        exc= sys.exc_info()
        now_text.update_value("error","Error: "+str(exc[1]))
    else:
        now_text.update_value("succeed","Done "+doi)

#このページの内容;
class View_input_doi(ft.View):
    def __init__(self):
        super().__init__()
        def add_clicked(e):
            list_doi.controls.insert(0,_Editable_Text(input_value=input_text_doi.value))
            input_text_doi.value = ""
            list_doi.update()
            self.update()
            input_text_doi.focus()
        def delete_clicked(e):
            list_doi.clean()
            self.update()
            input_text_doi.focus()
        #Enterキーを押されたら文字を加える.
        def add_entered(e):
            add_clicked(e)
        def run_clicked(e):
            for input_doi in list_doi.controls:
                _run_papnt_doi(input_doi)

        self.route="/"
        self.auto_scroll=True
        input_text_doi=ft.TextField(hint_text="Please input DOI",on_submit=add_entered,autofocus=True,expand=True)
        add_button=ft.FloatingActionButton(icon=ft.icons.ADD, on_click=add_clicked)
        run_button=ft.FloatingActionButton(icon=ft.icons.RUN_CIRCLE, on_click=run_clicked)
        delete_button=ft.FloatingActionButton(icon=ft.icons.DELETE, on_click=delete_clicked)
        list_doi=ft.Column(scroll=ft.ScrollMode.HIDDEN,expand=True)
        # 画面に追加する;
        self.controls.append(ft.Row([ft.Text("論文追加",theme_style=ft.TextThemeStyle.HEADLINE_LARGE)],alignment=ft.MainAxisAlignment.SPACE_BETWEEN,height=50))
        self.controls.append(_Edit_Database())
        self.controls.append(ft.Row([input_text_doi,add_button],alignment=ft.MainAxisAlignment.SPACE_BETWEEN))
        self.controls.append(ft.Row([run_button,delete_button]))
        self.controls.append(list_doi)
    def set_button_to_appbar(self,button):
        self.controls[0].controls.append(button)


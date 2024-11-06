from operator import truediv
from re import split
import typing
import os
import time
from anyio import value
import flet as ft
import configparser
import papnt

import papnt.database
import papnt.cli
import papnt.misc
import papnt.mainfunc


# Python code to sort a list of strings A based on the rules provided
def _access_notion_prop(value_props):
    mode=value_props["type"]
    match mode:
        case "title":
            return value_props["title"][0]["text"]["content"]
        case "select":
            return value_props["select"]["name"]
        case "multi_select":
            connected_lists=""
            for name in value_props["multi_select"]:
                connected_lists+=name["name"]
                connected_lists+=","
            return connected_lists
        case "rich_text":
            return value_props["rich_text"][0]["plain_text"]
        case "number":
            return value_props["number"]
        case "url":
            return value_props["url"]
        case _:
            raise ValueError('Invalid mode')

def _access_notion_prop_value(prop_page:dict,prop:str)->str:
    """notionのページから、propの値を返す

    Args:
        prop_page (dict): notionのページ."results"の値
        prop (string): notionのプロパティ名

    Returns:
        string: 入力したページの値
    """
    page_prop=prop_page["properties"]
    return _access_notion_prop(page_prop[prop])

class _Papers_List(ft.SearchBar):
    def __init__(self,input_list:list,add_list):
        """bibに追加する論文を選択するための入力フォーム

        Args:
            input_list (list): 未選択の要素。notionの"results"をそのまま入れる
            add_list (function): 要素を下に追加する関数。第一引数に表示するテキスト、第二引数にnotionのresultをとる
        """
        super().__init__()
        # anchor=ft.SearchBar()
        self.__PL_init_list=input_list
        self.__PL_select_flag="Name"
        self.__PL_listview=ft.ListView(controls=[ft.ListTile(title= ft.Text(_access_notion_prop_value(name,self.__PL_select_flag)),data=name,on_click=self.__close_anchor) for name in input_list])
        self.view_elevation=4
        self.controls=[self.__PL_listview]
        self.bar_hint_text="bibファイルに加える論文を選択"
        self.view_hint_text=self.bar_hint_text
        self.autofocus=True
        self.on_tap=self.__handle_tap
        self.on_change=self.__PL_handle_change
        self.__PL_add_list_to_out=add_list
    def __PL_sort_strings(self, B):
        starts_with_B = []
        includes_B=[]
        does_not_start_with_B = []
        for str in self.__PL_listview.controls:
            if str.title.value.lower().startswith(B.lower()):
                starts_with_B.append(str)
            elif B.lower() in str.title.value.lower():
                includes_B.append(str)
            else :
                does_not_start_with_B.append(str)
        self.__PL_listview.controls= starts_with_B+includes_B + does_not_start_with_B
    def __PL_update_listview(self,texts_list):
        self.__PL_listview.clean()
        new_controls=[]
        for name in texts_list:
            new_controls.append(ft.ListTile(title=ft.Text(_access_notion_prop_value(name,self.__PL_select_flag)),on_click=self.__close_anchor,data=name))
        self.__PL_listview.controls=new_controls
    def __close_anchor(self,e):
        text=e.control.title.value
        self.close_view(text)
        time.sleep(0.05)
        datas=e.control.data
        # print(datas)
        self.__PL_add_list_to_out(text,datas)
        self.__PL_listview.controls.remove(e.control)
        self.__PL_init_list.remove(datas)
        self.value=None
        self.update()
    def __handle_tap(self,e):
        self.open_view()
    def __PL_handle_change(self,e):
        self.__PL_sort_strings(e.data)
        if e.data=="":
            self.__PL_update_listview(self.__PL_init_list)
        self.update()
    def PL_change_prop_name(self,propname):
        self.__PL_select_flag=propname
        for name in self.__PL_listview.controls:
            name.title.value=_access_notion_prop_value(name.data,propname)
        self.update()
    def add_new_props(self,new_prop):
        self.__PL_init_list.insert(0,new_prop)
        self.__PL_listview.controls.insert(0,ft.ListTile(title=ft.Text(_access_notion_prop_value(new_prop,self.__PL_select_flag)),on_click=self.__close_anchor,data=new_prop))
    def PL_get_init_list(self)->typing.List[dict]:
        return self.__PL_init_list
class _Bib_File_Name(ft.Row):
    def __init__(self,text_list:list,add_Paper_List_New_Cite_in_prop):
        super().__init__()
        # anchor=ft.SearchBar()
        self.value=None
        self.__funk_add_Paper_List_update_prop=add_Paper_List_New_Cite_in_prop
        self.__BFN_listview=ft.ListView()
        self.__text_list=text_list
        self.__BFN_listview=ft.ListView(controls=[ft.ListTile(title= ft.Text(name),on_click=self.__close_anchor) for name in text_list])
        self.__BFN_serBar=ft.SearchBar(
        view_elevation=4,
        divider_color=ft.colors.AMBER,
        bar_hint_text="bibファイル名を入力",
        view_hint_text="bibファイル名を入力",
        on_change=self.__handle_change,
        on_submit=self.__handle_submit,
        on_tap=self.__handle_tap,
        controls=[self.__BFN_listview],
        )
        text=ft.Text(visible=False,value="bibファイル名を入力")
        button=ft.FloatingActionButton(icon=ft.icons.EDIT,mini=True,on_click=self.__reset_anchor,visible=False)
        self.controls=[self.__BFN_serBar,text,button]
        self.__BFN_visible_input()
        # self.update()
    def __BFN_visible_input(self):
        self.controls[0].visible=True
        self.controls[1].visible=False
        self.controls[2].visible=False
    def __BFN_invisible_input(self):
        self.controls[0].visible=False
        self.controls[1].visible=True
        self.controls[2].visible=True

    def __BFN_update_listview(self,texts_list):
        # self.__BFN_listview.clean()
        new_controls=[]
        for name in texts_list:
            new_controls.append(ft.ListTile(title=ft.Text(name),on_click=self.__close_anchor))
        self.__BFN_listview.controls=new_controls
    def __close_anchor(self,e):
        text=e.control.title.value
        self.__BFN_serBar.close_view(text)
        self.__BFN_serBar.data=False
        import time
        time.sleep(0.05)
        self.__handle_submit(e)
    def __handle_tap(self,e):
        self.__BFN_serBar.open_view()
        self.__BFN_serBar.data=True
    def __handle_change(self,e):
        def divide_lists(list,head_text:str):
            match_head=[]
            not_match_head=[]
            for name in list:
                if name.lower().startswith(head_text.lower()):
                    match_head.append(name)
                else:
                    not_match_head.append(name)
            return match_head+not_match_head
        if e.data=="":
            strings2=self.__text_list
        else:
            strings2=divide_lists(self.__text_list,e.data)
        self.__BFN_update_listview(strings2)
        self.update()
    def __handle_submit(self,e):
        new_text=self.controls[0].value
        if new_text not in self.__text_list:
            self.__text_list.insert(0,new_text)
            self.__BFN_listview.controls.insert(0,ft.ListTile(title=ft.Text(new_text),on_click=self.__close_anchor))
            # self.controls[0].controls=[self.__BFN_listview]
        if self.__BFN_serBar.data:
            # self.__BFN_serBar.close_view(new_text)
            self.controls[0].close_view(new_text)
            self.__BFN_serBar.data=False
            self.update()
            import time
            time.sleep(0.05)
            self.__handle_submit(e)
            return
        self.__BFN_invisible_input()
        self.controls[1].value=new_text
        self.update()
        self.value=new_text
        self.__funk_add_Paper_List_update_prop(self.value)
        pass
    def __reset_anchor(self,e):
        # self.__BFN_serBar.controls=[self.__BFN_listview]
        self.__BFN_visible_input()
        self.update()
        # self.__BFN_update_listview(self.__text_list)
        self.__BFN_serBar.open_view()
        self.__BFN_serBar.data=True

class _Get_Folder_Name(ft.SearchBar):
    def __init__(self,foldername_init:str|None,funk_decide):
        """bibファイルを出すフォルダー名を入力する

        Args:
            foldername_init (str | None): フォルダ名の初期値
            funk_decide (function): submitするときに呼ぶ関数。引数はなし
        """
        super().__init__()
        # anchor=ft.SearchBar()
        self.value=None if foldername_init =="''" else foldername_init
        self.GFN_folder_name=self.value
        self.__GFN_listview=ft.ListView(controls=[])
        self.view_elevation=4
        self.controls=[self.__GFN_listview]
        self.bar_hint_text="bibファイルを出力するフォルダ名を入力"
        self.view_hint_text=self.bar_hint_text+"/を入力することで次の候補が出現"
        self.on_tap=self.__handle_tap
        self.on_change=self.__GFN_handle_change
        self.on_submit=self.__handle_submit
        self.view_trailing=[ft.FloatingActionButton(icon=ft.icons.DONE,on_click=self.__clicked_submit)]
        self.__GFN_list_suggest_folder=[]
        self.__function_decide=funk_decide

    def __GFN_sort_strings(self, B):
        starts_with_B = []
        includes_B=[]
        does_not_start_with_B = []
        for str in self.__GFN_list_suggest_folder:
            if str.lower().startswith(B.lower()):
                starts_with_B.append(str)
            elif B.lower() in str.lower():
                includes_B.append(str)
            else :
                does_not_start_with_B.append(str)
        starts_with_B.sort()
        includes_B.sort()
        does_not_start_with_B.sort()
        self.__GFN_list_suggest_folder= starts_with_B+includes_B + does_not_start_with_B
    def __GFN_update_listview(self,texts_list):
        # self.__GFN_listview.clean()
        new_controls=[]
        for name in texts_list:
            new_controls.append(ft.ListTile(title=ft.Text(name),on_click=self.__tiles_clicked))
        self.__GFN_listview.controls=new_controls
    def __GFN_update_suggest_folder(self,path_dir):
        self.__GFN_list_suggest_folder=[f for f in os.listdir(path_dir) if os.path.isdir(os.path.join(path_dir,f))]
        self.__GFN_update_listview(self.__GFN_list_suggest_folder)
    def __tiles_clicked(self,e):
        text=e.control.title.value
        self.GFN_folder_name+=text+'/'
        self.value=self.GFN_folder_name
        self.__GFN_update_suggest_folder(self.value)
        self.focus()
        self.update()
    def GFN_update_value(self,new_value:str):
        # print(new_value)
        if new_value is None:
            self.__GFN_listview.clean()
        elif new_value=="":
            self.__GFN_listview.clean()
        elif new_value[-1]=='/':
            self.GFN_folder_name=new_value
            self.__GFN_update_suggest_folder(new_value)
        else:
            split_value=new_value.split("/")
            now_folder=""
            for i in range(len(split_value)-1):
                now_folder+=split_value[i]+'/'
            self.GFN_folder_name=now_folder
            self.__GFN_update_suggest_folder(now_folder)
            # print(split_value)
            next_folder=split_value[-1]
            # print(next_folder)
            self.__GFN_sort_strings(next_folder)
            self.__GFN_update_listview(self.__GFN_list_suggest_folder)
        self.update()
    def __GFN_handle_change(self,e):
        now_value:str|None=e.data
        self.GFN_update_value(now_value)
    def __handle_tap(self,e):
        self.open_view()
    def __GFN_Confirm_name(self):
        self.close_view(self.value)
        time.sleep(0.05)
        self.__function_decide()
    def __handle_submit(self,e):
        self.__GFN_Confirm_name()
    def __clicked_submit(self,e):
        self.__GFN_Confirm_name()



class _Edit_Database(ft.Row):
    def __init__(self):
        super().__init__()
        self.ED_path_config=papnt.__path__[0]+"/config.ini"
        self.config=configparser.ConfigParser(comment_prefixes='/', allow_no_value=True)
        self.config.read(self.ED_path_config)
        self.ED_text_dir_save_bibfile_decided=ft.Text(value=self.config["misc"]["dir_save_bib"],expand=True)
        self.ED_button_open_edit=ft.FloatingActionButton(icon=ft.icons.EDIT,on_click=self.__ED_clicked_open_edit_view,mini=True)
        self.ED_text_dir_save_bibfile_input=_Get_Folder_Name(self.ED_text_dir_save_bibfile_decided.value,self.__ED_clicked_done_edit)
        self.controls=[self.ED_text_dir_save_bibfile_decided, self.ED_button_open_edit,self.ED_text_dir_save_bibfile_input]
        self.ED_text_dir_save_bibfile_input.visible=False
    def __ED_clicked_open_edit_view(self,e):
        self.ED_text_dir_save_bibfile_decided.visible=False
        self.ED_button_open_edit.visible=False
        self.ED_text_dir_save_bibfile_input.visible=True
        self.ED_text_dir_save_bibfile_input.GFN_update_value(self.ED_text_dir_save_bibfile_decided.value)
        self.ED_text_dir_save_bibfile_input.open_view()
        self.update()

    def __ED_clicked_done_edit(self):
        self.ED_text_dir_save_bibfile_decided.visible=True
        self.ED_button_open_edit.visible=True
        self.ED_text_dir_save_bibfile_input.visible=False
        new_text=self.ED_text_dir_save_bibfile_input.value
        self.ED_text_dir_save_bibfile_decided.value=new_text
        self.config["misc"]["dir_save_bib"]=new_text
        with open(self.ED_path_config, "w") as configfile:
            self.config.write(configfile, True)
        self.update()

class _Text_Paper(ft.Row):
    def __init__(self,text:str,notion_result:dict,add_to_input_list):

        super().__init__()
        self.value=text
        self.data=notion_result
        self.__TP_add_to_input_list=add_to_input_list
        self.__TP_display_text=ft.Text(value=self.value)
        self.__TP_delete_button=ft.FloatingActionButton(icon=ft.icons.DELETE,on_click=self.__delete_clicked)
        self.controls=[self.__TP_display_text,self.__TP_delete_button]
    def __delete_clicked(self,e):
        self.__TP_add_to_input_list(self.data)
        self.clean()
    def change_text(self,propname):
        self.value=_access_notion_prop_value(self.data,propname)
        self.update()


class view_bib_maker(ft.View):
    def __init__(self):
        super().__init__()
        self.route="/make_bib_file"
        self.appbar=ft.AppBar(title=ft.Text("make_bib_file"))

        #コンフィグファイルとnotionデータベースの準備;
        path_config=papnt.__path__[0]+"/config.ini"
        self.__notion_configs=papnt.misc.load_config(path_config)

        self.database=papnt.database.Database(papnt.database.DatabaseInfo())
        response=self.database.notion.databases.query(self.database.database_id)
        self.results=response["results"]

        #モジュールの宣言;
        self.select_prop_flag=ft.Dropdown(value="Name",width=150)
        self.Paper_list=ft.Column(scroll=ft.ScrollMode.HIDDEN,expand=True)
        self._input_Paper_List=_Papers_List(self.results,self._add_Paper_list)
        self.run_button=ft.FilledButton("bibファイルを出力する",on_click=self.__makebib)

        #基礎設定:データベースの設定;
        #bibファイル名の候補を出す;
        filename_list=[]
        for name in self.results:
            next_list=name["properties"][self.__notion_configs["propnames"]["output_target"]]["multi_select"]
            for next_name in next_list:
                if not next_name["name"] in filename_list:
                    filename_list.append(next_name["name"])
        self._Bib_Name=_Bib_File_Name(filename_list,self.add_Paper_List_New_Cite_in_prop)
        self.controls.append(ft.Row(controls=[_Edit_Database(),self._Bib_Name],alignment=ft.MainAxisAlignment.SPACE_BETWEEN))
        # self.scroll=ft.ScrollMode.HIDDEN
        #構成要素：入力とか;
        self.select_prop_flag.on_change=self._dropdown_changed
        self.select_prop_flag.options=[ft.dropdown.Option(key=propname) for propname in self.__notion_configs["propnames"].values()]
        self.select_prop_flag.options.insert(0,ft.dropdown.Option(key="Name"))
        self._input_Paper_List.bar_leading=self.select_prop_flag
        self.controls.append(self._input_Paper_List)
        self.controls.append(self.run_button)
        self.controls.append(self.Paper_list)
    def _change_prop_name(self,propname:str)->None:
        item:type[_Text_Paper]
        for item in self.Paper_list.controls:
            item.change_text(propname)
        self.Paper_list.update()
        self._input_Paper_List.PL_change_prop_name(propname)
    def _add_prop_to_input_list(self,notion_page):
        self._input_Paper_List.add_new_props(notion_page)

    def _add_Paper_list(self,text_value,notion_result):
        new_text_cl=_Text_Paper(text_value,notion_result,self._input_Paper_List.add_new_props)
        self.Paper_list.controls.insert(0,new_text_cl)
        self.Paper_list.update()
    def _dropdown_changed(self,e):
        self._change_prop_name(e.data)
    def add_Paper_List_New_Cite_in_prop(self,new_cite_in_value):
        #全てのリストから加えていないものを見つける
        un_added_list=self._input_Paper_List.PL_get_init_list()
        for un_added_paper in un_added_list:
            if any([cite_in_item["name"]==new_cite_in_value for cite_in_item in un_added_paper["properties"][self.__notion_configs["propnames"]["output_target"]]["multi_select"]]):
                self._add_Paper_list(_access_notion_prop_value(un_added_paper,self.select_prop_flag.value),un_added_paper)

    def __makebib(self,e):
        #notionのCite in にデータを追加する;
        self.run_button.text="実行中..."
        self.run_button.style=ft.ButtonStyle(bgcolor=ft.colors.GREEN,shape=ft.RoundedRectangleBorder(radius=1))
        self.update()
        bib_name=self._Bib_Name.value
        items:type[ft.Row]
        for items in self.Paper_list.controls:#ft.Row(controls=[ft.Text,ft.FloatingActionButton])
            notion_page=items.controls[0].data
            # print(notion_page)
            cite_in_items=[{"name":cite_in_item["name"]} for cite_in_item in notion_page["properties"][self.__notion_configs["propnames"]["output_target"]]["multi_select"]]
            next_dict={"name":bib_name}
            if not next_dict in cite_in_items:
                cite_in_items.append(next_dict)
                next_prop={self.__notion_configs["propnames"]["output_target"]:{
                    "multi_select":cite_in_items
                    }
                }
                try:
                    self.database.update(notion_page["id"],next_prop)
                except:
                    import sys
                    exc= sys.exc_info()
                    print(str(exc[1]))
                    self.run_button.text=str(exc[1])
                    self.run_button.style=ft.ButtonStyle(bgcolor=ft.colors.RED)
                    self.update()
                print("reached")


        """Make BIB file including reference information from database"""
        try:
            papnt.mainfunc.make_bibfile_from_records(
                self.database,bib_name, self.__notion_configs['propnames'],
                self.__notion_configs['misc']['dir_save_bib'])
            papnt.mainfunc.make_abbrjson_from_bibpath(
                f'{self.__notion_configs["misc"]["dir_save_bib"]}/{bib_name}.bib',
                self.__notion_configs['abbr'])
        except:
            import sys
            exc=sys.exc_info()
            print(str(exc[1]))
            self.run_button.text=str(exc[1])
            self.run_button.style=ft.ButtonStyle(bgcolor=ft.colors.RED)
            self.update()
        self.run_button.style=None
        self.run_button.text="bibファイルを出力する"
        self.update()
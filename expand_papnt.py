# papntの機能に、arXiv 関連のものを付け足す。
# notionとの通信、更新まで;

import arxiv
import papnt
import configparser
import bibtexparser.bwriter
import bibtexparser.bibdatabase
import papnt.database
import papnt.cli
import papnt.misc
import papnt.mainfunc
import papnt.notionprop as pap_prop
import papnt.prop2entry as pap_pr2en


def _access_notion_prop(value_props):
    mode = value_props["type"]
    match mode:
        case "title":
            return value_props["title"][0]["text"]["content"]
        case "select":
            return value_props["select"]["name"]
        case "multi_select":
            connected_lists = ""
            for name in value_props["multi_select"]:
                connected_lists += name["name"]
                connected_lists += ","
            return connected_lists
        case "rich_text":
            out_val = value_props["rich_text"]
            return out_val[0]["plain_text"] if len(out_val) > 0 else None
        case "number":
            return value_props["number"]
        case "url":
            return value_props["url"]
        case _:
            raise ValueError("Invalid mode")


def access_notion_prop_value(prop_page: dict, prop: str) -> str:
    """notionのページから、propの値を返す

    Args:
        prop_page (dict): notionのページ."results"の値
        prop (string): notionのプロパティ名.notion側のタイトル

    Returns:
        string: 入力したページの値
    """
    page_prop = prop_page["properties"]
    return _access_notion_prop(page_prop[prop])


# ----------------------------------------------------------------------------
# arXiv更新用関数;
# doi整形;
def _make_doi_arxiv(doi: str) -> str:
    sp = doi.split("arXiv")
    if sp[1][0] == "." or sp[1][0] == ":":
        sp[1] = sp[1][1:]
    return sp[1]


# arXivのものを持ってきた時、アクセプトされているならdoiを、そうでないならnoneを返す;
def check_arXiv_paper_accepted(doi: str) -> str | None:
    doi2 = _make_doi_arxiv(doi)
    client = arxiv.Client()
    serch = arxiv.Search(id_list=[doi2])
    reslut = next(client.results(serch))
    return reslut.doi


def _return_page_prop_accepted_paper(
    doi: str, db_notion: papnt.database.Database, propnames: dict
) -> dict | None:
    if not "arXiv" in doi:
        return None
    new_doi = check_arXiv_paper_accepted(doi)
    if new_doi is not None:
        prop = pap_prop.NotionPropMaker().from_doi(new_doi, propnames)
        result_create = db_notion.notion.pages.create(
            parent={"database_id": db_notion.database_id}, properties=prop
        )
        db_notion.notion.pages.update(page_id=result_create["id"], archived=True)
        return result_create
    else:
        return None


# -----------------------------------------------------------------------------
# makebib関連
def _notionprop_to_entry_arXiv(notionprop: dict, propname_to_bibname: dict):
    props = {
        propname_to_bibname.get(key) or key: val for key, val in notionprop.items()
    }
    entry = dict(
        ENTRYTYPE=pap_pr2en._extr_propvalue(props["entrytype"], "select"),
        ID=pap_pr2en._extr_propvalue(props["id"], "rich_text"),
        author=pap_pr2en._extr_authors_asbib(
            pap_pr2en._extr_propvalue(props["author"], "multi_select")
        ),
        title=pap_pr2en._extr_propvalue(props["title"], "rich_text"),
        journal="arXiv preprint "
        + pap_pr2en._extr_propvalue(props["doi"], "rich_text"),
        year=pap_pr2en._extr_propvalue(props["year"], "number"),
        # doi=pap_pr2en._extr_propvalue(props["doi"], "rich_text"),
    )
    return {key: val for key, val in entry.items() if val is not None}


# ---------------------------------------------------------------------------
# bib ファイルを作る
def _make_bibfile_from_lists(
    target: str,
    propnames: dict,
    list_page_prop_papers: list[dict],
    dir_save_bib: str,
):
    propname_to_bibname = {val: key for key, val in propnames.items()}
    entries = [
        (
            _notionprop_to_entry_arXiv(record["properties"], propname_to_bibname)
            if "arXiv" in access_notion_prop_value(record, propnames["doi"])
            else pap_pr2en.notionprop_to_entry(
                record["properties"], propname_to_bibname
            )
        )
        for record in list_page_prop_papers
    ]

    bib_db = bibtexparser.bibdatabase.BibDatabase()
    bib_db.entries = entries
    writer = bibtexparser.bwriter.BibTexWriter()
    with open(f"{dir_save_bib}/{target}.bib", "w") as bibfile:
        bibfile.write(writer.write(bib_db))


def makebib(bib_name:str, props_paper:list[dict], notion_configs:dict, database:papnt.database.Database):
    """
    候補に挙げられている論文から、
    1. notion側にCite in プロパティを追加
    2. bibファイルを出力
    Args:
        bib_name (str): 出力するbibファイルの名前
        props_paper (list[string]): 出力する論文のリスト。要素はnotionの"result"
        notion_configs (dict): papnt のconfig
        database (papnt.database.Database) : papntのdatabase
    """
    # notionのCite in にデータを追加する;
    # bibに出力する論文のリストを作る;
    list_add_bib_papers: list[dict] = []
    for notion_page in props_paper:
        # print(notion_page)
        cite_in_items = [
            {"name": cite_in_item["name"]}
            for cite_in_item in notion_page["properties"][
                notion_configs["propnames"]["output_target"]
            ]["multi_select"]
        ]
        next_dict = {"name": bib_name}
        if not next_dict in cite_in_items:
            cite_in_items.append(next_dict)
            next_prop = {
                notion_configs["propnames"]["output_target"]: {
                    "multi_select": cite_in_items
                }
            }
            database.update(notion_page["id"], next_prop)
        # --------------------------------------------------------------------------------
        # arXivの論文を加える場合、アクセプトされているかを調べる;
        page_arXiv_update = _return_page_prop_accepted_paper(
            access_notion_prop_value(notion_page, notion_configs["propnames"]["doi"]),
            database,
            notion_configs["propnames"],
        )
        if page_arXiv_update is not None:
            notion_page = page_arXiv_update
        list_add_bib_papers.append(notion_page)
    """Make BIB file including reference information from database"""
    _make_bibfile_from_lists(
        bib_name,
        notion_configs["propnames"],
        list_add_bib_papers,
        notion_configs["misc"]["dir_save_bib"],
    )
    papnt.mainfunc.make_abbrjson_from_bibpath(
        f'{notion_configs["misc"]["dir_save_bib"]}/{bib_name}.bib',
        notion_configs["abbr"],
    )

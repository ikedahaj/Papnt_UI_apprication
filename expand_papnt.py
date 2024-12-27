# papntの機能に、arXiv 関連のものを付け足す。
# notionとの通信、更新まで;

import arxiv
import papnt

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
def _check_arXiv_paper_accepted(doi: str) -> str | None:
    doi2 = _make_doi_arxiv(doi)
    client = arxiv.Client()
    serch = arxiv.Search(id_list=[doi2])
    reslut = next(client.results(serch))
    return reslut.doi

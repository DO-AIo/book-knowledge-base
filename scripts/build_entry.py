#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 BookCards/ 入口包：一个打开就能看到全部书的索引页 + 图谱 + 卡片。

为什么要这个：D 每次开 WorkBuddy 都要在桌面/文件夹里翻找。本脚本把三样东西
装进一个固定目录 ~/BookCards/，AI 只要 present_files 打开其中的 index.html 即可。

产物（全部为生成物，不要手改）：
  ~/BookCards/index.html   ← 索引页（书目数据内嵌，file:// 直接可开）
  ~/BookCards/graph.html   ← 图谱（d3 内联，卡片跳转指向 cards/<书名>.html）
  ~/BookCards/cards/<书名>.html
  ~/BookCards/books.json   ← 中间数据，方便排查

用法：
  python scripts/build_entry.py
每次改完书单或新增卡片后，跟 rebuild_clean.py --write 一起跑。
"""
import base64
import json
import os
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "书籍知识图谱模板.html"
D3 = ROOT / "assets" / "d3.v7.min.js"
TAG = '<script src="./assets/d3.v7.min.js"></script>'

OUT = pathlib.Path(os.path.expanduser("~")) / "BookCards"
CARDS_OUT = OUT / "cards"

CAT_ORDER = ["思维认知", "底层规律", "人性洞察", "经济与商业", "财富认知", "心理成长",
             "决策避坑", "习惯养成", "能力提升", "人际关系与沟通", "名人传记",
             "成事方法", "哲学思辨", "文学经典", "历史"]

CAT_COLOR = {
    "思维认知": "#4D96FF", "底层规律": "#4ECDC4", "人性洞察": "#EC5D7A", "经济与商业": "#FF6B6B",
    "财富认知": "#FFD166", "心理成长": "#E879B9", "决策避坑": "#6BCB77", "习惯养成": "#C5E063",
    "能力提升": "#10A19D", "人际关系与沟通": "#FF8FAB", "名人传记": "#B8A6E8",
    "成事方法": "#FF9F45", "哲学思辨": "#6F86D6", "文学经典": "#F5C28B", "历史": "#C68B59",
}


def embedded(html: str) -> dict:
    i = html.index("_EMBEDDED_GRAPH = ") + len("_EMBEDDED_GRAPH = ")
    j = html.index("{", i)
    depth = 0
    for k in range(j, len(html)):
        if html[k] == "{":
            depth += 1
        elif html[k] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(html[j:k + 1])
    raise ValueError("_EMBEDDED_GRAPH 未闭合")


def build_graph_html() -> str:
    html = SRC.read_text(encoding="utf-8")
    if TAG in html:
        b64 = base64.b64encode(D3.read_bytes()).decode()
        html = html.replace(TAG,
            "<script>(function(){var s=document.createElement(\"script\");"
            "s.textContent=atob(\"" + b64 + "\");document.head.appendChild(s);})();</script>")

    # 入口包里的卡片是 cards/<书名>.html 平铺结构，必须把 CARD_MAP 的
    # `cards/<拼音>/<书名>-知识卡片.html` 一并改写，否则点节点跳到不存在的路径。
    html = re.sub(
        r'cards/[^"/]+/([^"/]+)-知识卡片\.html',
        lambda m: f"cards/{m.group(1)}.html",
        html,
    )
    return html


def collect_books(html: str):
    g = embedded(html)
    books = [n for n in g["nodes"] if n.get("type") == "book"]
    cats = {}
    for b in books:
        cats.setdefault(b["category"], []).append({
            "t": b["label"], "a": b.get("author", ""), "r": b.get("rating"),
            "card": f"cards/{b['label']}.html" if b.get("has_card") else None,
            "_src": b.get("card_path"),
        })
    return [(c, cats[c]) for c in CAT_ORDER if cats.get(c)]


def render_index(cats, total: int, ncard: int) -> str:
    data = [{"name": c, "books": [{k: v for k, v in b.items() if k != "_src"} for b in bs]}
            for c, bs in cats]
    tpl = (ROOT / "scripts" / "entry_template.html").read_text(encoding="utf-8")
    out = (tpl.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False))
              .replace("__TOTAL__", str(total))
              .replace("__NCARD__", str(ncard))
              .replace("__CATS__", str(len(cats))))
    # 自检：内嵌数据必须能被 json 解析（历史上出现过 [...] 后残留 [] 的事故）
    i = out.index("const DATA = ") + len("const DATA = ")
    j = out.index(";\n\n(function()", i)
    parsed = json.loads(out[i:j])
    if len(parsed) != len(cats):
        raise ValueError(f"内嵌数据异常：{len(parsed)} 类，预期 {len(cats)} 类")
    return out


def main() -> int:
    html = build_graph_html()
    cats = collect_books(SRC.read_text(encoding="utf-8"))
    total = sum(len(b) for _, b in cats)
    ncard = sum(1 for _, bs in cats for b in bs if b["card"])

    OUT.mkdir(parents=True, exist_ok=True)
    CARDS_OUT.mkdir(parents=True, exist_ok=True)

    (OUT / "graph.html").write_text(html, encoding="utf-8")
    (OUT / "index.html").write_text(render_index(cats, total, ncard), encoding="utf-8")
    (OUT / "books.json").write_text(
        json.dumps([{"name": c, "books": [{k: v for k, v in b.items() if k != "_src"} for b in bs]}
                    for c, bs in cats], ensure_ascii=False, indent=1), encoding="utf-8")

    for _, bs in cats:
        for b in bs:
            if not b["_src"]:
                continue
            src = ROOT / b["_src"]
            dst = CARDS_OUT / f"{b['t']}.html"
            if src.exists():
                shutil.copy2(src, dst)

    # 给卡片副本注入「返回知识图谱」按钮（不改源文件）
    import subprocess
    subprocess.run([sys.executable, str(ROOT / "scripts" / "patch_cards.py")], check=False)

    print(f"[入口包] {OUT}")
    print(f"  书 {total} 本 / 分类 {len(cats)} 个 / 卡片 {ncard} 张")
    print(f"  打开：{OUT / 'index.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

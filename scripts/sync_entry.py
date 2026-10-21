#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 书籍知识图谱模板.html 同步成「单文件版」入口副本。

背景：模板里的 d3 是外链 ./assets/d3.v7.min.js，拷到别处（比如桌面）就会白屏。
本脚本把 d3 内联进 HTML，产出可独立放在任何位置的副本。

生成/更新的副本：
  - 知识图谱.html                                  （仓库根，好记的名字；卡片跳转走仓库 cards/）
  - index.html                                     （仓库根，双击文件夹即用；同上）
  - %USERPROFILE%/Desktop/书籍知识图谱.html         （桌面入口；卡片跳转改写为 桌面/书籍卡片/<书名>.html）

卡片跳转说明：
  仓库模板里 CARD_MAP 存的是 `cards/<拼音>/<书名>-知识卡片.html`。
  桌面副本不识别这个相对路径（会 ERR_FILE_NOT_FOUND），因此桌面版会把这些
  路径整体改写成 `书籍卡片/<书名>.html`；对应实体文件由 `sync_cards.py` 负责拷。

用法：
  python scripts/sync_entry.py
每次改完书库、跑完 rebuild_clean.py 之后，再跑一次本脚本。
"""
import base64
import json
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "书籍知识图谱模板.html"
D3 = ROOT / "assets" / "d3.v7.min.js"
TAG = '<script src="./assets/d3.v7.min.js"></script>'

DESKTOP = pathlib.Path(os.path.expanduser("~")) / "Desktop"
CARD_DIR = DESKTOP / "书籍卡片"

TARGETS = [
    ROOT / "知识图谱.html",
    ROOT / "index.html",
    DESKTOP / "书籍知识图谱.html",
]


def build_standalone() -> str:
    html = SRC.read_text(encoding="utf-8")
    if TAG not in html:
        return html  # 已内联过
    b64 = base64.b64encode(D3.read_bytes()).decode()
    loader = (
        "<script>(function(){var s=document.createElement(\"script\");"
        "s.textContent=atob(\"" + b64 + "\");"
        "document.head.appendChild(s);})();</script>"
    )
    return html.replace(TAG, loader)


def embedded_graph(html: str) -> dict:
    """按花括号配对取出 _EMBEDDED_GRAPH 的 JSON（不能直接切到文件尾）。"""
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
    raise ValueError("_EMBEDDED_GRAPH JSON 未闭合")


def card_rewrite_map() -> dict:
    """从模板 CARD_MAP 取 {书名: 相对路径}，映射成 {旧路径: 桌面简名路径}。"""
    html = SRC.read_text(encoding="utf-8")
    m = re.search(r'const CARD_MAP = \{(.*?)\};', html, re.S)
    if not m:
        return {}
    pairs = re.findall(r'"(b_[0-9a-f]+)":\s*"([^"]+)"', m.group(1))
    if not pairs:
        return {}
    g = embedded_graph(html)
    label_by_id = {n["id"]: n["label"] for n in g["nodes"] if n.get("type") == "book"}
    rewrite = {}
    for bid, rel in pairs:
        label = label_by_id.get(bid)
        if label:
            rewrite[rel] = f"书籍卡片/{label}.html"
    return rewrite


def rewrite_for_desktop(html: str) -> str:
    """把 CARD_MAP/_EMBEDDED_GRAPH 里的卡片路径改写为桌面简名路径。"""
    mapping = card_rewrite_map()
    if not mapping:
        return html
    for old, new in mapping.items():
        html = html.replace(old, new)
    return html


def main() -> int:
    if not SRC.exists():
        print(f"[ERROR] 找不到 {SRC}")
        return 1
    repo_content = build_standalone()
    desktop_content = rewrite_for_desktop(repo_content)

    for p in TARGETS:
        content = desktop_content if p.parent == DESKTOP else repo_content
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        print(f"[已同步] {p}  ({len(content):,} 字符)")

    missing = []
    for rel in card_rewrite_map().values():
        if not (CARD_DIR / pathlib.Path(rel).name).exists():
            missing.append(rel)
    if missing:
        print(f"[提醒] 桌面 {CARD_DIR.name}/ 缺卡片实体：{missing}")
        print("       跑 python scripts/sync_cards.py 补齐")
    print("[提示] 这些副本是产物，不要手改；改 UI 改模板，改数据改书单数据源.md。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

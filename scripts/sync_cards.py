#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把仓库 cards/ 下已有的知识卡片，拷成桌面 书籍卡片/<书名>.html 简名副本。

配合 sync_entry.py 使用：桌面版图谱的节点跳转指向 书籍卡片/<书名>.html，
本脚本负责让这些实体文件真的存在。

用法：
  python scripts/sync_cards.py
每次新建/修改知识卡片之后跑一次。
"""
import json
import os
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "书籍知识图谱模板.html"
DESKTOP = pathlib.Path(os.path.expanduser("~")) / "Desktop"
CARD_DIR = DESKTOP / "书籍卡片"


def main() -> int:
    if not SRC.exists():
        print(f"[ERROR] 找不到 {SRC}")
        return 1

    html = SRC.read_text(encoding="utf-8")
    i = html.index("_EMBEDDED_GRAPH = ") + len("_EMBEDDED_GRAPH = ")
    j = html.index("{", i)
    depth = 0
    for k in range(j, len(html)):
        if html[k] == "{":
            depth += 1
        elif html[k] == "}":
            depth -= 1
            if depth == 0:
                g = json.loads(html[j:k + 1])
                break

    CARD_DIR.mkdir(parents=True, exist_ok=True)
    copied = skipped = 0
    for n in g["nodes"]:
        if n.get("type") != "book" or not n.get("has_card"):
            continue
        src = ROOT / n["card_path"]
        dst = CARD_DIR / f"{n['label']}.html"
        if not src.exists():
            print(f"[WARN] 卡片源不存在：{src}")
            continue
        if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
            print(f"[跳过] {dst.name}（已是最新）")
            skipped += 1
            continue
        shutil.copy2(src, dst)
        print(f"[已拷] {dst}")
        copied += 1

    print(f"[完成] 新拷 {copied}，跳过 {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

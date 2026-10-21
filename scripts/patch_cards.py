#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给 BookCards/cards/ 下的卡片副本注入「← 返回知识图谱」悬浮按钮。

背景：图谱点节点改为同窗口跳转后，卡片页没有返回入口，看完就卡住了。
本脚本只在 BookCards 的副本上注入，不改仓库里的卡片源文件。

用法：
  python scripts/patch_cards.py
build_entry.py 会自动调用，一般不用手动跑。
"""
import json
import os
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "书籍知识图谱模板.html"
OUT = pathlib.Path(os.path.expanduser("~")) / "BookCards"
CARDS_OUT = OUT / "cards"

MARK = "<!--bookcards-back-->"

BACK_BTN = MARK + """
<style>
#bookcards-back{
  position:fixed; left:18px; bottom:18px; z-index:2147483647;
  display:inline-flex; align-items:center; gap:6px;
  padding:9px 15px; border-radius:999px;
  background:rgba(43,39,36,.88); color:#FFFCF5;
  font:500 13px/1 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif;
  text-decoration:none; box-shadow:0 4px 16px rgba(0,0,0,.18);
  transition:background .18s, transform .18s;
}
#bookcards-back:hover{background:#C4623F;transform:translateY(-1px)}
</style>
<a id="bookcards-back" href="../graph.html">&#8592; 返回知识图谱</a>
"""


def main() -> int:
    if not OUT.exists():
        print(f"[ERROR] 找不到入口包 {OUT}，先跑 build_entry.py")
        return 1
    CARDS_OUT.mkdir(parents=True, exist_ok=True)
    done = 0
    for f in sorted(CARDS_OUT.glob("*.html")):
        t = f.read_text(encoding="utf-8")
        if MARK in t:
            continue
        if "</body>" not in t:
            print(f"[跳过] {f.name}（无 </body>）")
            continue
        f.write_text(t.replace("</body>", BACK_BTN + "</body>", 1), encoding="utf-8")
        done += 1
    print(f"[返回按钮] 注入 {done} 张卡片")
    return 0


if __name__ == "__main__":
    sys.exit(main())

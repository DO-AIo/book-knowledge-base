#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一键发布到 GitHub Pages：重建数据 → 同步入口 → 提交 → 推送。

用途：电脑上改完书库（书单数据源.md / 卡片 / 模板）后，跑这一条命令，
线上版本就跟着更新，iPad 刷新即见。

用法：
  python scripts/publish.py                      # 全流程，自动写提交信息
  python scripts/publish.py -m "新增《xxx》"      # 自定义提交信息
  python scripts/publish.py --no-push            # 只做到本地提交（先看 diff）

前置：
  - 仓库已配置 origin，且当前分支已设置 upstream
  - git 凭证已就绪（首次推送会要求登录）
"""
import argparse
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PY = sys.executable


def run(cmd, check=True):
    print("$ " + " ".join(cmd))
    p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, encoding="utf-8", errors="replace")
    out = (p.stdout or "").strip()
    if out:
        print(out)
    err = (p.stderr or "").strip()
    if p.returncode != 0:
        if err:
            print(err)
        if check:
            raise SystemExit(f"[失败] 退出码 {p.returncode}")
        return None, p
    if err:
        print(err)
    return out, p


def book_count() -> int:
    src = ROOT / "书单数据源.md"
    if not src.exists():
        return 0
    text = src.read_text(encoding="utf-8")
    # 书单条目形如 `- 《书名》` 或 `| 《书名》 |`
    return len(set(re.findall(r"《([^》]+)》", text)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-m", "--message", default="")
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--skip-build", action="store_true")
    args = ap.parse_args()

    if not args.skip_build:
        run([PY, "scripts/rebuild_clean.py", "--write"])
        run([PY, "scripts/sync_entry.py"])

    # 卡片实体必须随页面一起上线，否则点击卡片会 404
    index = ROOT / "index.html"
    if not index.exists():
        raise SystemExit("[失败] index.html 不存在，请先跑 python scripts/sync_entry.py")

    html = index.read_text(encoding="utf-8")
    cards = sorted(set(re.findall(r"cards/[^\"']+\.html", html)))
    missing = [c for c in cards if not (ROOT / c).exists()]
    if missing:
        print(f"[警告] 图谱引用了 {len(missing)} 张卡片但实体不存在，线上点击会 404：")
        for m in missing[:10]:
            print("   - " + m)

    run(["git", "add", "-A"])

    out, _ = run(["git", "status", "--porcelain"], check=False)
    if not (out or "").strip():
        print("[完成] 没有需要提交的改动。")
        return 0

    msg = args.message.strip() or f"content: 更新书库（{book_count()} 本书）"
    run(["git", "commit", "-m", msg], check=False)

    if args.no_push:
        print("[完成] 已本地提交，未推送。确认无误后加 --no-push 以外的参数重跑，或直接 git push。")
        return 0

    run(["git", "push"])
    remote, _ = run(["git", "remote", "get-url", "origin"], check=False)
    print("\n[完成] 已推送。Pages 约 1 分钟后生效：")
    url = pages_url((remote or "").strip())
    if url:
        print("   " + url)
    return 0


def pages_url(remote: str) -> str:
    m = re.search(r"github\.com[:/]([^/]+)/([^/.]+)", remote)
    if not m:
        return ""
    owner, repo = m.group(1), m.group(2)
    return f"https://{owner}.github.io/{repo}/"


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diff_watch.py — 增量变更检测，识别自上次（或相对 HEAD）以来变动的源文件。

优先用 git diff；若目标不是 git 仓库，退化为基于 MD5 的 hash 快照比对。
输出变动文件相对路径列表到 JSON，供「更新维护」场景只重扫变更文件。

用法：
    python diff_watch.py <target_root> [-o changed.json] [--mode auto|git|hash]
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys

SRC_EXT = {'.py', '.java'}
SKIP_DIRS = {'.git', 'node_modules', 'target', 'dist', 'build', 'out',
             '__pycache__', '.idea', '.vscode', 'venv', '.venv'}


def git_changed(root):
    """返回相对路径集合（未提交 + 已暂存）。非 git 仓库返回 None。"""
    try:
        r1 = subprocess.run(['git', '-C', root, 'diff', '--name-only'],
                            capture_output=True, text=True)
        if r1.returncode != 0:
            return None
        r2 = subprocess.run(['git', '-C', root, 'diff', '--cached', '--name-only'],
                            capture_output=True, text=True)
        files = set(r1.stdout.split()) | set(r2.stdout.split())
        return {f for f in files if os.path.splitext(f)[1].lower() in SRC_EXT}
    except FileNotFoundError:
        return None


def hash_changed(root, cache='.cc_hash.json'):
    """基于文件 MD5 的快照比对；首次运行返回全部源码文件。"""
    manifest = {}
    for dp, dn, fns in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for fn in fns:
            if os.path.splitext(fn)[1].lower() in SRC_EXT:
                full = os.path.join(dp, fn)
                try:
                    h = hashlib.md5(open(full, 'rb').read()).hexdigest()
                except Exception:
                    continue
                manifest[os.path.relpath(full, root).replace('\\', '/')] = h
    cache_path = os.path.join(root, cache)
    prev = {}
    if os.path.exists(cache_path):
        try:
            prev = json.load(open(cache_path, encoding='utf-8'))
        except Exception:
            prev = {}
    changed = set(manifest) ^ set(prev)        # 新增或修改
    deleted = set(prev) - set(manifest)        # 删除
    json.dump(manifest, open(cache_path, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=2)
    return changed | deleted


def main():
    ap = argparse.ArgumentParser(description='检测变动的源文件')
    ap.add_argument('root', help='目标项目根目录')
    ap.add_argument('-o', '--output', default='changed.json')
    ap.add_argument('--mode', choices=['auto', 'git', 'hash'], default='auto')
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print(f"[ERR] 目录不存在: {root}", file=sys.stderr)
        sys.exit(1)

    changed = None
    if args.mode in ('auto', 'git'):
        changed = git_changed(root)
        if changed is not None:
            src = 'git'
    if changed is None and args.mode in ('auto', 'hash'):
        changed = hash_changed(root)
        src = 'hash'

    changed = sorted(changed or [])
    json.dump(changed, open(args.output, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=2)
    print(f"[{src}] 变动源文件 {len(changed)} 个 -> {args.output}")
    for f in changed[:50]:
        print(f"    {f}")


if __name__ == '__main__':
    main()

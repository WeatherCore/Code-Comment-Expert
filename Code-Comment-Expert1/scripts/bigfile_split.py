#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bigfile_split.py — 对超大源文件做行级切块，避免单文件超出 LLM 上下文。

把文件按 max_lines 切片，相邻块保留 overlap 行重叠，便于跨块连续性。
输出每块的文件路径与行区间到 JSON，供注释阶段逐批投喂。

用法：
    python bigfile_split.py <file> [--max-lines 800] [--overlap 40] [-o chunks.json]
"""
import argparse
import json
import os
import sys

DEFAULT_MAX = 800
DEFAULT_OVERLAP = 40


def split_file(path, max_lines=DEFAULT_MAX, overlap=DEFAULT_OVERLAP):
    with open(path, encoding='utf-8', errors='ignore') as f:
        lines = f.read().splitlines()
    total = len(lines)
    if total <= max_lines:
        return [{'index': 0, 'start_line': 1, 'end_line': total,
                 'path': path, 'note': '未切块（未超阈值）'}]
    out_dir = os.path.join(os.path.dirname(os.path.abspath(path)), '.cc_split')
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(path))[0]
    chunks = []
    i, idx = 0, 0
    while i < total:
        end = min(i + max_lines, total)
        chunk = lines[i:end]
        out_path = os.path.join(out_dir, f"{base}.{idx:03d}.txt")
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(chunk))
        chunks.append({'index': idx, 'start_line': i + 1, 'end_line': end,
                       'path': out_path})
        if end >= total:
            break
        i = end - overlap
        idx += 1
    return chunks


def main():
    ap = argparse.ArgumentParser(description='超大文件行级切块')
    ap.add_argument('file', help='待切分的源文件')
    ap.add_argument('--max-lines', type=int, default=DEFAULT_MAX)
    ap.add_argument('--overlap', type=int, default=DEFAULT_OVERLAP)
    ap.add_argument('-o', '--output', default='chunks.json')
    args = ap.parse_args()

    if not os.path.isfile(args.file):
        print(f"[ERR] 文件不存在: {args.file}", file=sys.stderr)
        sys.exit(1)
    chunks = split_file(args.file, args.max_lines, args.overlap)
    json.dump(chunks, open(args.output, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=2)
    print(f"[OK] 切块 {len(chunks)} 个 -> {args.output}")


if __name__ == '__main__':
    main()

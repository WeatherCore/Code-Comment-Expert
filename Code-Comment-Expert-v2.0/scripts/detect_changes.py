#!/usr/bin/env python3
"""detect_changes.py — 变更检测：用 Git Diff 找出变动文件，只对这些文件重新生成注释。

用于"更新维护"模式（场景 C）：合并分支 / 提交后，定位本次变更涉及的源码文件，
避免全量重扫。

用法:
    python detect_changes.py --root <项目根> [--base <git-ref>] [--out changes.json]
    # 默认 base 为上一次提交（HEAD^）；可指定 origin/main 等

输出 JSON:
    {"base": "...", "added": [...], "modified": [...], "deleted": [...], "all_source": [...]}
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SOURCE_EXT = {
    ".java", ".kt", ".py", ".pyw", ".js", ".jsx", ".ts", ".tsx",
    ".go", ".rs", ".c", ".h", ".cpp", ".hpp", ".cc", ".cxx",
    ".cs", ".php", ".rb", ".swift",
}

SKIP_DIRS = {
    ".git", "node_modules", "venv", ".venv", "dist", "build", "target",
    "out", "__pycache__", ".idea", ".vscode", "coverage", ".next", "vendor",
}


def is_source(rel: str) -> bool:
    if any(part in SKIP_DIRS for part in Path(rel).parts):
        return False
    p = Path(rel)
    if p.name.startswith("."):
        return False
    if p.name.startswith(("min.", ".min.")):
        return False
    return p.suffix.lower() in SOURCE_EXT


def git(args: list[str], cwd: Path) -> str:
    try:
        r = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, check=False)
    except FileNotFoundError:
        print("[ERROR] 未找到 git 命令", file=sys.stderr)
        sys.exit(1)
    if r.returncode != 0:
        print(f"[ERROR] git {' '.join(args)} 失败: {r.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    return r.stdout


def main() -> int:
    parser = argparse.ArgumentParser(description="Git Diff 变更检测，输出需重新注释的源码文件清单")
    parser.add_argument("--root", required=True, help="Git 仓库根目录")
    parser.add_argument("--base", default="HEAD", help="对比基准（默认 HEAD，即工作区未提交变更）")
    parser.add_argument("--out", default="changes.json", help="输出 JSON 路径")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not (root / ".git").exists():
        print(f"[ERROR] {root} 不是 Git 仓库", file=sys.stderr)
        return 1

    base = args.base
    if base == "HEAD":
        # 默认看工作区未提交变更；若无变更则回退到 HEAD^ 比较最近一次提交
        status = git(["status", "--porcelain"], root).strip()
        if not status:
            base = "HEAD~1"
            print(f"[INFO] 工作区无未提交变更，对比基准改为 {base}")

    output = git(["diff", "--name-status", f"{base}..."], root) if base != "HEAD" else git(["diff", "--name-status"], root)
    lines = [ln for ln in output.splitlines() if ln.strip()]

    added: list[str] = []
    modified: list[str] = []
    deleted: list[str] = []
    for ln in lines:
        parts = ln.split("\t")
        if len(parts) < 2:
            continue
        status_code, rel = parts[0], parts[1]
        if not is_source(rel):
            continue
        if status_code.startswith("A"):
            added.append(rel)
        elif status_code.startswith("D"):
            deleted.append(rel)
        else:
            modified.append(rel)

    result = {
        "base": base,
        "added": added,
        "modified": modified,
        "deleted": deleted,
        "all_source": added + modified,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True) if out.parent != Path(".") else None
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] 变更清单已写入 {out}")
    print(f"     新增: {len(added)} | 修改: {len(modified)} | 删除: {len(deleted)} | 需注释: {len(result['all_source'])}")
    for rel in result["all_source"]:
        print(f"     - {rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

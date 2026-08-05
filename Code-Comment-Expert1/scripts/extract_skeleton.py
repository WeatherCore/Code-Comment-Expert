#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_skeleton.py — 遍历项目源码，提取结构骨架到 skeleton.json。

支持：Java（正则）、Python（ast）。零外部依赖，仅用标准库。
用途：解决 LLM 上下文装不下大项目的问题——先抽取「不含实现代码」的骨架
      （类/方法签名、import、入口点、技术栈、目录树），作为全局上下文。

用法：
    python extract_skeleton.py <target_root> [-o skeleton.json]

v1 已知限制（Java）：泛型参数、内部类、Lombok、跨行注解可能提取不全；
    属预期，注释阶段靠阅读真实源码补足。
"""
import argparse
import ast
import json
import os
import re
import sys
from datetime import datetime

SKIP_DIRS = {
    '.git', 'node_modules', 'target', 'dist', 'build', 'out', 'bin', 'obj',
    '.idea', '.vscode', '__pycache__', 'venv', '.venv', 'env', '.mypy_cache',
    '.tox', 'vendor', 'assets', 'static', 'public', 'docs', 'doc',
}
TEST_DIR_HINTS = ('test', 'tests', 'spec', '__tests__', 'unittest', 'it', 'e2e', 'fixtures')
SKIP_FILE_SUFFIX = ('.min.js', '.min.css', '.map', '.lock')
SRC_EXT = {'.py': 'python', '.java': 'java'}

TECH_FILES = {
    'pom.xml': 'Java / Maven',
    'build.gradle': 'Java / Gradle',
    'build.gradle.kts': 'Java / Gradle (Kotlin DSL)',
    'requirements.txt': 'Python / pip',
    'setup.py': 'Python / setuptools',
    'pyproject.toml': 'Python / pyproject',
    'go.mod': 'Go / modules',
    'package.json': 'Node / npm',
    'Cargo.toml': 'Rust / cargo',
    'pom.xml': 'Java / Maven',
}

# ---------------- Python ----------------
def _sig(fn):
    args = [a.arg for a in fn.args.args]
    return f"{fn.name}({', '.join(args)})"

def _method_info(fn):
    return {
        'name': fn.name,
        'signature': _sig(fn),
        'doc': ast.get_docstring(fn),
        'decorators': [ast.unparse(d) for d in fn.decorator_list],
    }

def extract_python(path):
    try:
        src = open(path, encoding='utf-8').read()
        tree = ast.parse(src)
    except Exception as e:
        return {'file': path, 'language': 'python', 'error': str(e),
                'imports': [], 'classes': [], 'functions': [], 'doc': None}
    mod = {'file': path, 'language': 'python', 'doc': ast.get_docstring(tree),
           'imports': [], 'classes': [], 'functions': []}
    for node in tree.body:
        if isinstance(node, ast.Import):
            for n in node.names:
                mod['imports'].append(n.name)
        elif isinstance(node, ast.ImportFrom):
            mod['imports'].append((node.module or '') + '.*')
        elif isinstance(node, ast.ClassDef):
            cls = {'name': node.name, 'kind': 'class',
                   'bases': [ast.unparse(b) for b in node.bases],
                   'doc': ast.get_docstring(node), 'methods': [],
                   'decorators': [ast.unparse(d) for d in node.decorator_list]}
            for b in node.body:
                if isinstance(b, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    cls['methods'].append(_method_info(b))
            mod['classes'].append(cls)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            mod['functions'].append(_method_info(node))
    return mod

# ---------------- Java (regex) ----------------
JAVA_CLASS_RE = re.compile(
    r'(?:public\s+|abstract\s+|final\s+)*'
    r'(class|interface|enum)\s+(\w+)(?:<[^>]*>)?\s*'
    r'(?:extends\s+(\w+))?\s*(?:implements\s+([\w,\s]+))?'
)
JAVA_IMPORT_RE = re.compile(r'import\s+(?:static\s+)?([\w.]+)\s*;')
JAVA_JAVADOC_RE = re.compile(r'/\*\*(.*?)\*/', re.DOTALL)
# 方法：可选注解 + 修饰符 + 返回类型 + 名称 + 参数；用负向断言排除控制关键字
JAVA_METHOD_RE = re.compile(
    r'(?:@\w+(?:\([^)]*\))?\s+)*'
    r'(?:public|protected|private|static|final|abstract|synchronized|native|transient|volatile|default\s+)*\s*'
    r'(?!if|for|while|switch|catch|try|do|else|return|new|throw|synchronized|class|interface|enum|import|package\b)'
    r'([A-Za-z_][\w<>\[\],\s.]*?)\s+'
    r'(\w+)\s*\(([^)]*)\)'
)

def extract_java(path):
    try:
        src = open(path, encoding='utf-8').read()
    except Exception as e:
        return {'file': path, 'language': 'java', 'error': str(e),
                'imports': [], 'classes': [], 'functions': [], 'doc': None}
    mod = {'file': path, 'language': 'java', 'doc': None,
           'imports': [], 'classes': [], 'functions': []}
    for m in JAVA_IMPORT_RE.finditer(src):
        mod['imports'].append(m.group(1))
    javadocs = {j.end(): j.group(1).strip() for j in JAVA_JAVADOC_RE.finditer(src)}

    classes = list(JAVA_CLASS_RE.finditer(src))
    class_list = []
    for i, c in enumerate(classes):
        nxt = classes[i + 1].start() if i + 1 < len(classes) else len(src)
        cls = {'name': c.group(2), 'kind': c.group(1),
               'bases': [x for x in [c.group(3), c.group(4)] if x],
               'doc': None, 'methods': [], 'decorators': []}
        for m in JAVA_METHOD_RE.finditer(src, c.start(), nxt):
            ret = m.group(1).strip()
            if not ret:
                continue
            doc = None
            for endpos, text in javadocs.items():
                if endpos <= m.start() and (m.start() - endpos) < 300:
                    doc = text
                    break
            cls['methods'].append({
                'name': m.group(2),
                'signature': f"{m.group(2)}({m.group(3)})",
                'doc': doc,
            })
        class_list.append(cls)
    mod['classes'] = class_list
    return mod

# ---------------- 入口点 / 技术栈 ----------------
SPRING_ANNOT = ('@RestController', '@Controller', '@SpringBootApplication',
                '@Service', '@Repository', '@Component', '@RequestMapping')

def detect_entry_points(modules):
    eps = []
    for mod in modules:
        if mod.get('error'):
            continue
        f = mod['file'].replace('\\', '/')
        if mod['language'] == 'python':
            low = open(mod['file'], encoding='utf-8', errors='ignore').read().lower()
            if "__main__" in low or "def main(" in low:
                eps.append({'file': f, 'reason': 'Python 入口 (main)'})
            if 'flask' in low or 'fastapi' in low or 'django' in low:
                eps.append({'file': f, 'reason': 'Web 框架入口 (Flask/FastAPI/Django)'})
        else:
            txt = open(mod['file'], encoding='utf-8', errors='ignore').read()
            if re.search(r'public\s+static\s+void\s+main\s*\(', txt):
                eps.append({'file': f, 'reason': 'Java 入口 (main)'})
            for a in SPRING_ANNOT:
                if a in txt:
                    eps.append({'file': f, 'reason': f'Spring 组件 ({a})'})
                    break
    # 去重
    seen = set()
    uniq = []
    for e in eps:
        k = (e['file'], e['reason'])
        if k not in seen:
            seen.add(k)
            uniq.append(e)
    return uniq

def detect_tech_stack(root):
    stack = []
    for name, label in TECH_FILES.items():
        if os.path.exists(os.path.join(root, name)):
            stack.append(label)
    return sorted(set(stack))

def build_tree(root, walked_dirs):
    lines = []
    prefix = []  # 可变缩进栈，避免局部/全局作用域冲突
    def recurse(parent):
        sub = sorted([d for d in walked_dirs if os.path.dirname(d) == parent],
                     key=lambda x: x.lower())
        for i, d in enumerate(sub):
            base = os.path.basename(d)
            last = (i == len(sub) - 1)
            lines.append(f"{''.join(prefix)}{'└─ ' if last else '├─ '}{base}/")
            prefix.append('   ' if last else '│  ')
            recurse(d)
            prefix.pop()
    recurse(root)
    return '\n'.join(lines)

# ---------------- 主流程 ----------------
def main():
    ap = argparse.ArgumentParser(description='提取项目结构骨架到 JSON')
    ap.add_argument('root', help='目标项目根目录')
    ap.add_argument('-o', '--output', default='skeleton.json', help='输出 JSON 路径')
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print(f"[ERR] 目录不存在: {root}", file=sys.stderr)
        sys.exit(1)

    modules = []
    walked_dirs = set()
    stats = {'python_files': 0, 'java_files': 0, 'classes': 0, 'methods': 0}
    for dp, dn, fns in os.walk(root):
        # 过滤跳过的目录
        dn[:] = [d for d in dn if d not in SKIP_DIRS
                 and not any(h == d.lower() or h in d.lower() for h in TEST_DIR_HINTS)]
        rel_dp = os.path.relpath(dp, root)
        if rel_dp != '.':
            walked_dirs.add(os.path.normpath(os.path.join(root, rel_dp)))
        for fn in fns:
            ext = os.path.splitext(fn)[1].lower()
            if ext not in SRC_EXT:
                continue
            if fn.lower().endswith(SKIP_FILE_SUFFIX):
                continue
            full = os.path.join(dp, fn)
            if ext == '.py':
                m = extract_python(full)
                stats['python_files'] += 1
            else:
                m = extract_java(full)
                stats['java_files'] += 1
            stats['classes'] += len(m['classes'])
            stats['methods'] += sum(len(c['methods']) for c in m['classes']) \
                                + len(m['functions'])
            modules.append(m)

    skeleton = {
        'generated_at': datetime.now().isoformat(timespec='seconds'),
        'root': root,
        'tech_stack': detect_tech_stack(root),
        'entry_points': detect_entry_points(modules),
        'tree': build_tree(root, walked_dirs),
        'modules': modules,
        'stats': stats,
    }
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(skeleton, f, ensure_ascii=False, indent=2)
    print(f"[OK] 骨架已写入 {args.output}")
    print(f"     Python 文件 {stats['python_files']} | Java 文件 {stats['java_files']} "
          f"| 类 {stats['classes']} | 方法 {stats['methods']}")
    print(f"     入口点 {len(skeleton['entry_points'])} | 技术栈 {skeleton['tech_stack']}")

if __name__ == '__main__':
    main()

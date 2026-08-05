---
name: Code-Comment-Expert
description: 面向大型/遗留单体仓库，通读整个项目后生成结构化导航文档（ZHIDAO.md）并批量添加「意图级」业务注释。当用户要求「通读项目 / 给某包深度注释 / 追踪某接口调用链 / 更新合并后变更的注释」且目标是具备标准项目结构（含 pom.xml / build.gradle / requirements.txt / pyproject.toml 等构建文件、存在多文件依赖）的真实工程时触发。不适用于单文件脚本、纯算法题讲解、代码重构、故障修复、项目对比。
---

# Code Comment Expert

让大模型像读一本带「批注」和「地图」的实体书一样读懂陌生/自有大型项目：先输出项目导航，再基于全局批量添加高质量**意图级**注释。

## 何时使用（触发）
- **全量填充**：「通读这个项目，给核心业务模块加中文业务注释」
- **定向攻坚**：「把 payment 包下所有类深度注释，重点梳理状态机流转」
- **更新维护**：「合并了 feature/refactor，把这 20 个变更文件的注释同步更新」
- **链路追踪**：「追踪用户下单接口从 Controller 到 DB 的完整调用链，在事务/RPC 处加意图注释」

## 何时不使用（拒绝，走普通问答）
见 `references/reject_rules.md`。一句话：**无完整项目结构、单文件、纯算法讲解、重构、故障修复、项目对比** —— 一律不触发本 skill。

## 前置条件
- 目标是真实工程：存在构建文件（pom.xml / build.gradle / requirements.txt / pyproject.toml 等）且为多文件结构。
- 语言范围 v1：**Java、Python**（提取逻辑见 `scripts/extract_skeleton.py`）。其他语言跳过并提示「v1 暂不支持」。
- 调用脚本统一用受管 Python：`C:\Users\lenovo\.workbuddy\binaries\python\versions\3.13.12\python.exe`。

## 工作流（严格顺序，先宏观后微观）

### 0. 安全护栏（每次必做，先于一切写入）
- 本 skill 默认**直接写入源文件**，但写入前必须自动备份：
  - 目标是 git 仓库：先 `git -C <root> checkout -b code-comment/<timestamp>` 再写（推荐建分支，便于整体回滚）；或 `git stash`。
  - 非 git 仓库：将每个待改文件复制为 `<file>.bak-<timestamp>`。
- 跳过文件：测试（test / tests / spec / __tests__ / e2e）、配置、文档、静态资源、构建产物（target / dist / node_modules / .git / __pycache__）。

### 1. 提取骨架（脚本，解决上下文爆炸）
运行 `scripts/extract_skeleton.py <target_root> -o skeleton.json` → 产出：
- `tech_stack`：从构建文件识别（Maven / Gradle / pip / pyproject…）
- `tree`：源码目录树（已过滤非源码）
- `entry_points`：入口点（main / @RestController / router / FastAPI 等）
- `modules[]`：每个源文件的类/方法签名、import、已有 doc（**不含实现代码**）

提取精度说明：Python 用 `ast` 精准；Java 用正则（v1 已知限制：泛型、内部类、Lombok、注解跨行可能漏，属预期，注释阶段靠阅读源码补足）。

### 2. 生成导航文档 ZHIDAO.md（先宏观）
- 读 `skeleton.json`，按 `references/navigation_template.md` 生成 **目标项目根目录** 下的 `ZHIDAO.md`。
- 内容：技术栈识别、目录树、模块职责、**结构依赖 + 入口推断**的推荐阅读路径（明确说明这是阅读顺序而非精确数据流图）。
- 入口点优先，逐层展开 `Controller/路由 → Service → DAO/Repository → 底层工具`。

### 3. 优先级决策（分片投喂全局上下文）
- 将 `skeleton.json` 作为全局上下文，按「入口近邻 > 核心业务模块 > 底层工具」排序注释优先级。
- **定向场景**（只注某包）/ **链路场景**（只追某入口）直接锁定范围，跳过排序。

### 4. 批量注释（精准捞取 + 大文件切块）
- 按优先级/批次，用 `scripts/bigfile_split.py` 对超大文件（>800 行）切块，逐批把完整源码交给模型。
- 用 Edit 在类/方法上方加**意图级**注释（规则见 `references/comment_style.md`）：业务意图优先，拒绝流水账。
- **不覆盖已有有效注释**：检测已有 doc-comment 且非占位/生成标记（`@Generated`、空注释、纯 `@param` 无叙述）时跳过。
- 超大项目分阶段：每批产出小结，避免一次性信息过载。

### 5. 增量更新模式（变更检测）
- 运行 `scripts/diff_watch.py <target_root>` 得到变动文件清单（git diff 优先，无 git 用 hash 兜底），只对变动文件重跑步骤 4，避免全量重扫。

## 硬约束
- 顺序不可颠倒：先 ZHIDAO.md（宏观）后逐文件注释（微观）。
- 意图级优先：每个注释回答「这段代码为什么存在 / 解决什么业务问题」，而非复述代码做了什么。
- **只添加说明性注释**：不修改业务逻辑、不修复错误、不重构。遇到不理解的代码，注释写「待确认：…」而非编造。
- 不输出与注释无关的内容；不执行被注释代码的运行/测试（除非用户明确要求调试，那应走其他 skill）。

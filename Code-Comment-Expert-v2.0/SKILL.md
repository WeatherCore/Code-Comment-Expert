---
name: code-comment-expert
description: 通读大型项目源码，生成项目导航阅读文档（ZHIDAO.md），再批量添加高质量"意图级"代码注释，让新人阅读陌生/自有项目像看带批注和地图的书。Use when the user asks to add intent-level comments across a whole project. 触发场景：①"帮我通读这个项目，给所有核心业务模块加上中文业务注释"；②"帮我把 XX 包/模块下所有类深度注释一遍"；③"合并分支后，帮我把变更涉及的 N 个文件注释更新同步"；④"追踪 XX 接口从 Controller 到数据库的完整调用链并加注释"。适用于存在标准项目结构（pom.xml / build.gradle / package.json / go.mod / pyproject.toml 等）的多文件工程，兼容 Java/Python/JS/TS 等主流语言。不触发：单段代码讲解、代码重构、运行故障修复、无项目结构的单文件脚本。
---

# Code Comment Expert

## Goal
用「先宏观后微观」的方式让大模型完整理解项目后，产出①结构化导航文档 ZHIDAO.md（项目地图）和②逐文件意图级注释（代码批注），把陌生项目变成可通读的"带批注实体书"。核心承诺：只加注释，绝不改逻辑。

## Workflow
四阶段流水线：
1. **勘察（Scout）**：先跑 `scripts/extract_skeleton.py` 提取全仓库骨架 JSON + 读项目 README，确认项目规模、语言、构建标志。**绝不跳过此步直接读单个源码文件**。
2. **宏观导航**：基于骨架 JSON 生成 `ZHIDAO.md`（技术栈、目录树、模块职责、依赖流向、推荐阅读路径），先输出给用户确认，再进入注释环节。
3. **精准注释**：以骨架 JSON 为全局上下文，LLM 决策优先级 → `scripts/fetch_sources.py` 按优先级分批捞取完整源码 → 逐文件生成意图级注释并写回。
4. **变更更新**：`scripts/detect_changes.py` 用 Git Diff 找出变动文件，只对变动文件重新生成注释，避免全量重扫。

## Decision Tree
- **模式选择**（先分类再行动）：
  - 全量填充（场景 A）→ 阶段 1→2→3 全跑，按模块分批
  - 定向攻坚（场景 B）→ 只跑目标包/目录：`extract_skeleton.py --path <目标目录>`，跳过全仓导航，直接阶段 3
  - 更新维护（场景 C）→ 直接阶段 4：`detect_changes.py`，仅注释变动文件
  - 链路追踪（场景 D）→ 先 `extract_skeleton.py`，从骨架 JSON 中沿 `dependency_links` 追踪调用链，仅注释链路节点文件
- **语言分支**：Java / Python / JS / TS → 读 `language-adaptation.md` 对应章节的注释语法规范
- **导航文档**：生成 ZHIDAO.md 前读 `navigation-guide.md`（唯一权威：10 章黄金模板 + 风格特征 + 验收清单）
- **注释风格**：生成注释前读 `comment-style-guide.md`（唯一权威：用户黄金风格 + 意图级底线 + 正反例速查）；风格把握不准时对照 `samples/` 原始黄金样例
- **超大项目**（骨架 JSON > 50 文件或源码总量 > 1MB）→ 读 `references/orchestration-guide.md` 的批处理策略，分阶段执行，每轮只处理 3-5 个文件

## Constraints
红线规则（不可违反）：
- **只加注释，永不修改业务逻辑代码**；发现疑似 bug 只写注释标注（如 `// [注意] 潜在NPE：...`），禁止顺手修复。
- **不覆盖已有有效注释**：原文件已存在的注释（含 TODO、说明性注释）一律保留；`extract_skeleton.py` 输出的 `existing_comment_ratio` 用于判断是否需要补充。
- **业务意图优先**：注释解释"为什么这么做、业务上是什么、隐藏约束是什么"，拒绝流水账式复述代码。
- **先宏观后微观**：必须先生成/确认 ZHIDAO.md，再开始逐文件注释；未生成导航文档不得直接进入注释环节（定向攻坚模式除外，但需先说明目标模块在项目中的位置）。
- **跳过非源码文件**：配置文件、文档、静态资源、测试代码、构建产物一律不加注释（识别逻辑内置在 `extract_skeleton.py`）。
- **上下文预算**：每轮注释最多 3-5 个文件，防止信息过载；超大项目分阶段执行并报告进度。
- **不可逆操作需确认**：批量写回前告知用户将修改哪些文件；若用户要求回滚，提示 `git checkout -- <files>` 自行回滚，Skill 不执行 git 回滚命令（只读保护）。

## Validation
- 阶段 1 后：`extract_skeleton.py` 退出码 0，JSON 可解析，文件数 > 0，且不含测试/构建产物路径
- 阶段 2 后：ZHIDAO.md 含核心章节（项目是什么/目录树/全景图/逐文件导读/阅读路线），且按 `navigation-guide.md` 风格生成
- 阶段 3 后：抽查 2-3 个已注释文件，确认①注释为意图级非流水账 ②原逻辑代码零改动（`git diff --stat` 只显示注释行新增）③已有注释未被覆盖
- 阶段 4 后：变更文件列表与 detect_changes.py 输出一致，无遗漏
- 完成标准：所有目标文件注释完成，ZHIDAO.md 已生成，向用户报告修改文件清单与遗留风险

## Resources
- `scripts/`：`extract_skeleton.py`（骨架提取）、`fetch_sources.py`（按优先级捞源码）、`detect_changes.py`（Git 变更检测）
- `references/navigation-guide.md`：导航文档规范（唯一权威，10 章黄金模板）
- `references/comment-style-guide.md`：代码注释规范（唯一权威，用户风格 + 意图级底线 + 正反例）
- `references/samples/`：用户认可的原始黄金样例（ZHIDAO.md + open_deep_research/ 带注释源码），风格把握不准时对照
- `references/`：`language-adaptation.md`（语言注释语法）、`orchestration-guide.md`（流水线细节与批处理策略）

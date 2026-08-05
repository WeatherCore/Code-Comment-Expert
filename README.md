# code-comment-expert
Skill 作用不是给单行函数写注释，而是面向新人快速熟悉巨型遗留 / 大型单体仓库，生成项目层级、模块层级、文件层级的全景注释、结构说明，降低陌生代码库上手门槛


评分维度（每项 10 分，总分 70）
维度	v1.0	v2.0	说明
1. 触发质量（frontmatter 路由）	6	9	v1 name 是 Code-Comment-Expert（违反 hyphen-case）；v2 有 "Use when" 触发词、4 个明确场景、排除清单
2. SKILL.md 控制层结构	6	9	v1 缺 Decision Tree / Validation / Resources 标准段；v2 是教科书式六段结构
3. references 质量	5	9	v1 三份薄文档、无黄金样例、模板只有 5 节；v2 有用户实际认可的 open_deep_research 黄金样例、拟人化比喻库、10 章黄金模板
4. scripts 质量	6	7	v1 Python 用 ast（精准）、有 bigfile_split.py、有 hash 兜底；v2 14 语言、有 dependency_links，但 Python 退化成正则、丢了 bigfile_split、丢了 hash 兜底
5. 安全与诚信	9	6	v1 显式 Step 0 备份护栏（建 git 分支或 .bak 文件）+ "待确认"不编造规则；v2 这两条都退化了，只有被动 "提示 git checkout"
6. 可验证性	4	7	v1 完全无 tests；v2 有 fixtures 和 out/ 样例，但无自动化断言、ZHIDAO.example.md 不符合自己的 10 章模板
7. 黄金风格忠实度	4	10	v1 通用风格、无样例锚定；v2 直接复刻用户认可的 open_deep_research 风格
总分（/70，再换算 /10）：

v1.0 = 40/70 ≈ 5.7/10
v2.0 = 57/70 ≈ 8.1/10

v1.0 的硬伤
name 不合规（大写驼峰），路由层会被破坏
没有 agents/openai.yaml（无 UI 元数据）
缺标准控制层段（Decision Tree / Validation / Resources）
references 太薄，无黄金样例锚定
extract_skeleton.py 有 bug：TECH_FILES 字典里 pom.xml 重复定义（被覆盖）
语言只支持 Java/Python（Java 还是纯正则，泛型/Lombok 漏抓）
v2.0 的硬伤（这是关键，因为 v2 是更强基础）
安全护栏退化：v1 的 Step 0 自动备份没了，只剩被动 "提示回滚"
bigfile_split.py 丢失：超大文件切块能力没了
detect_changes.py 失去 hash 兜底：非 git 仓库直接 exit 1，v1 有 MD5 快照兜底
Python 解析从 ast 退化成正则：精度倒退
"待确认"防编造规则丢失
fetch_sources.py 有死代码（fetched = chunks.count("")）+ print 语句输出 === 而非文件名
_strip_comments 转义符 bug：\\ 后字符丢失
orchestration-guide.md 引用了不存在的 assets/navigation-guide-template.md
tests/out/ZHIDAO.example.md 不符合自己规定的 10 章黄金模板

v3.0 计划
v2 是更强的基底，v3 = v2 基础 + 找回 v1 的 5 处退化 + 修 v2 的 9 个 bug + 补强
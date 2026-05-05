# algernon-karpathy-wiki

> 基于 Karpathy LLM Wiki 模式的 **Claude Code 个人知识库技能** —— 让 AI 帮你编译、维护和查询你的知识库。

[English](README.md)

## 这是什么？

大多数人用 LLM 处理文档的方式类似 RAG：上传文件、检索片段、生成答案——然后就忘了。**没有积累。**

这个技能实现了 Karpathy 提出的替代方案：LLM 不是每次查询时重新检索原始文档，而是**增量编译并维护一个持久的、互链的 wiki**——一个位于你和原始资料之间的结构化 markdown 文件集合。当你添加新资料时，LLM 读取它、提取概念和实体、更新相关页面、保持交叉引用和最新状态。

**wiki 是一个持久、复利的产物。** 每添加一个来源，知识就变得更丰富。

## 架构

```
├── raw/              # 原始资料层（人类所有，LLM 只读）
│   ├── registry.md   # 外部目录注册表
│   ├── articles/     # Markdown 文章
│   ├── clippings/    # Obsidian Web Clipper 剪藏
│   ├── images/       # 截图和图片
│   ├── pdfs/         # PDF 及配套元数据
│   ├── notes/        # 随手记录
│   └── personal/     # 自己写的内容
├── wiki/             # 编译层（LLM 全权拥有，人类只读）
│   ├── index.md      # 全局索引（查询第一入口）
│   ├── log.md        # 追加式操作日志
│   ├── overview.md   # 高层综述 + 健康面板
│   ├── QUESTIONS.md  # 开放问题队列
│   ├── sources/      # 来源摘要页
│   ├── concepts/     # 思想、模式、技术
│   ├── entities/     # 人物、工具、机构、项目
│   ├── synthesis/    # 跨来源综合分析
│   └── templates/    # 页面模板
├── outputs/          # 查询结果和 lint 报告
├── scripts/
│   ├── lint.py       # Wiki 健康检查脚本
│   ├── compile-state.json  # 增量编译状态（基于 hash）
│   └── qmd-reindex.sh      # qmd 搜索索引重建
├── CLAUDE.md         # LLM 行为契约
└── README.md         # 本文件
```

### 核心原则

1. **`raw/` 不可变** — LLM 只读，绝不修改
2. **`wiki/` LLM 全权负责** — 创建、更新、维护所有页面
3. **编译优于检索** — 知识编译一次并保持最新，不是每次查询重新推导
4. **双向链接** — 所有页面使用 `[[wikilinks]]` 建立互连
5. **输出归档** — 有价值的答案归档回知识库，形成知识复利

## 七大能力

| # | 能力 | 说明 |
|---|------|------|
| 1 | **Init（初始化）** | 从骨架目录一键初始化：`cp -r` + 日期占位符替换 + `git init` |
| 2 | **Ingest（导入）** | 单文件导入：读源文件、创建摘要页、概念页、实体页、写入关系标注 |
| 3 | **Compile（编译）** | 批量增量编译：MD5 hash 差异检测，只处理变更文件 |
| 4 | **Lint（健康检查）** | 脚本检查（断链、孤儿、空页、关系一致性）+ LLM 语义检查（过时断言、矛盾、低置信度、知识缺口） |
| 5 | **Query（查询）** | 通过 `wiki/index.md` → 相关页面 → 综合回答，有价值答案归档到 `outputs/` |
| 6 | **Relationships（关系标注）** | 自动写入类型化关系：YAML frontmatter + 正文 `@type` 双写格式，支持 Obsidian Graph View |
| 7 | **Git（版本控制）** | 每次 wiki 操作后自动提交，纯本地 git 管理 |

## 安装

### 前置要求

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) — 运行一切的 LLM Agent
- [Obsidian](https://obsidian.md/) — 知识库前端（强烈推荐）
- [qmd](https://github.com/tobi/qmd) — 本地搜索引擎（200+ 页面时启用）

### 安装步骤

1. **克隆仓库**

```bash
git clone https://github.com/<你的用户名>/algernon-karpathy-wiki.git
```

2. **安装 skill 到 Claude Code**

```bash
# macOS / Linux
mkdir -p ~/.claude/skills/llm-wiki
cp -r algernon-karpathy-wiki/* ~/.claude/skills/llm-wiki/

# Windows (PowerShell)
Copy-Item -Path algernon-karpathy-wiki\* -Destination $env:USERPROFILE\.claude\skills\llm-wiki\ -Recurse -Force
```

3. **验证安装**

启动 Claude Code，让 AI 初始化一个知识库：

```
claude
> 用 llm-wiki skill 初始化一个知识库
```

## 使用方法

### 初始化知识库

```
在 /path/to/my-wiki 初始化一个知识库
```

Skill 会：
1. 复制骨架目录到目标目录
2. 替换所有 `{{date}}` 占位符为当天日期
3. 初始化本地 git 仓库

### 导入资料

```
导入 raw/articles/ 下的文件
```

一个来源通常会创建 5-15 个 wiki 页面：来源摘要、概念页、实体页、关系标注。

### 批量编译

```
编译知识库
```

LLM 扫描所有注册的源目录，计算 MD5 hash，增量处理变更文件。

### 查询知识库

```
DGS 和 NMS 之间是什么关系？
```

LLM 读取 `wiki/index.md`，找到相关页面，综合回答并标注引用来源。

### 健康检查

```
检查知识库健康
```

运行 `scripts/lint.py`（断链、孤儿、空页、关系一致性）+ LLM 语义检查（过时断言、矛盾、低置信度、知识缺口）。

## 关系词汇表

Skill 自动在 wiki 页面间写入类型化关系：

| 类型 | 含义 | 示例 |
|------|------|------|
| `calls` | A 调用 B 的接口/API | DGS 数据同步 calls NMS 接口 |
| `depends_on` | A 依赖 B | DGS 告警聚合 depends_on 节点状态 |
| `defines` | A 定义了 B（类、函数、配置） | 拨测策略模块 defines 策略接口 |
| `implements` | A 实现了 B 模式/协议 | 策略模式 implements 策略设计模式 |
| `queries` | A 查询 B 的数据库/表 | 巡检服务 queries 设备状态表 |
| `triggers` | A 触发 B（事件/告警/任务） | 节点离线 triggers DGS 告警 |
| `configures` | A 配置 B | Nacos 配置 configures 刷新频率 |
| `transforms` | A 转换成 B 格式 | 解析器 transforms EIAP 数据为统一格式 |
| `part_of` | A 是 B 的子模块 | 告警聚合 part_of DGS 监控 |
| `related_to` | 其他关联 | 知识管理 related_to Karpathy LLM Wiki |

## Obsidian 集成

- 将知识库目录作为 Obsidian vault 打开
- 使用 **Graph View** 可视化知识图谱（带类型连线）
- 安装 **Wikilink Types** 插件自动同步 frontmatter ↔ 正文关系
- 安装 **Dataview** 插件实现 YAML frontmatter 动态查询
- 使用 **Obsidian Web Clipper** 快速剪藏文章到 `raw/articles/`

## 致谢

- **Andrej Karpathy** — [LLM Wiki 模式](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)，核心理念的提出者
- **Vannevar Bush** — Memex（1945），此概念的精神源头
- **Obsidian** — 知识库 Markdown 前端
- **qmd** — 大型 wiki 的本地搜索引擎

## License

MIT

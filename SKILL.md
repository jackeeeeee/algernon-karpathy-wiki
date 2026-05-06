---
name: algernon-karpathy-wiki
description: >
  LLM-maintained personal knowledge base. Covers five capabilities:
  (1) Init — bootstrap a fresh knowledge-base directory structure with registry.md.
  (2) Ingest — single-file import: create source summary + concepts/entities pages + typed relationships.
  (3) Compile — batch incremental compile via registry.md + compile-state.json (hash-based).
  (4) Lint — health checks: script (broken links/orphans/empty/relationship-consistency) + LLM (stale/contradiction/low-confidence/gaps).
  (5) Query — answer questions via wiki/index.md, archive to outputs/query-YYYYMMDD.md.
  Relationships and Git commits are built into every operation automatically.
  Trigger when: 编译知识库、compile wiki、编译、compile、ingest、总结文档、总结资料、
  lint、检查健康、知识库查询、wiki 维护、knowledge base、llm wiki、初始化知识库、init。
---

# LLM Wiki — 个人知识库维护

本 skill 管理基于 Karpathy LLM Wiki 模式的知识库生命周期。
核心原则：raw/ 不可变，wiki/ LLM 全权负责，编译优于检索。

知识库结构（扁平化，无 knowledge-base/ 前缀）：

```
<target_dir>/
├── raw/              # 原始资料（人类所有，LLM 只读，绝不修改）
│   ├── registry.md   # 源文件目录注册表（LLM 编译时先读此文件定位源文件）
│   ├── articles/     # Markdown 文章
│   ├── clippings/    # Obsidian Web Clipper 剪藏
│   ├── images/       # 截图和图片
│   ├── pdfs/         # PDF 及配套元数据
│   ├── notes/        # 随手记录（可选，现多用外部 reference）
│   └── personal/     # 自己写的文章、分析报告、投资笔记
├── wiki/             # 编译层（LLM 全权拥有，人类只读不编辑）
│   ├── index.md      # 全局索引（查询第一入口）
│   ├── log.md        # 追加式操作日志（graph-excluded: true）
│   ├── overview.md   # 高层综述 + Health Dashboard
│   ├── QUESTIONS.md  # 开放问题队列
│   ├── sources/      # 每个来源的摘要页
│   ├── concepts/     # 思想、模式、技术（含 aliases）
│   ├── entities/     # 人物、工具、机构、论文
│   ├── synthesis/    # 跨来源合成分析
│   └── templates/    # 页面模板
├── outputs/          # 查询答案、lint 报告
│   ├── lint.md       # lint 报告
│   └── query-YYYYMMDD.md # 查询答案（按日期分文件）
├── scripts/          # 自动化脚本
│   ├── lint.py              # Wiki 健康检查脚本
│   ├── compile-state.json   # 编译状态（源文件 hash 和 wikiPages 映射）
│   └── qmd-reindex.sh       # qmd 索引重建脚本
├── CLAUDE.md         # LLM 行为契约
└── README.md         # 项目说明
```

## 配置文件管理

知识库根路径记录在 `config.json`（与此 SKILL.md 同级目录）：

```json
{
  "wikiPath": "D:/F/LLMwiki/my_world05"
}
```

- 路径使用正斜杠 `/`，绝对路径
- 空字符串表示未配置
- 用户可能移动知识库，旧路径会失效，需要重新定位

---

## 执行前置：定位知识库

**每次执行任何能力前，先执行此步骤获取知识库路径：**

1. 读取同目录 `config.json` 的 `wikiPath` 字段
2. 如果路径为空，或目录不存在，或缺少 `wiki/index.md`（标志文件缺失）：
   - 问用户："知识库路径是什么？"
   - 用户提供路径后，**我复述**："知识库在 `<用户提供的路径>`"
   - **我验证**：检查目录是否存在、是否有 `wiki/index.md`
   - 验证通过 → 写入 `config.json`，继续执行
   - 验证失败 → 告知用户路径无效，请重新提供
3. 路径有效 → 设为当前操作的 `<target_dir>`，继续执行能力

---

## 能力一：Init（初始化）

当用户要求"初始化知识库"或"init"时，执行此能力。

**流程**：

1. **询问目标目录**：问用户"知识库初始化在哪个目录？"
2. **确认路径**：用户给出路径后，复述确认
3. **复制骨架**：
   - 先找到 `references/skeleton` 目录（它在此 SKILL.md 所在目录下的 references/skeleton/ 中）
   - 然后执行 `cp -r <skeleton路径>/* <target_dir>/ && cp <skeleton路径>/.gitignore <target_dir>/`
   - 注意：需要两条 `cp`，因为 `*` 不匹配隐藏文件 `.gitignore`
4. **替换日期占位符**：在目标目录中递归替换所有 `{{date}}` 为当天日期（YYYY-MM-DD 格式）：
   ```bash
   find <target_dir> -type f \( -name '*.md' -o -name '*.json' \) -exec sed -i 's/{{date}}/2026-05-05/g' {} +
   ```
   （将日期替换为实际日期）
5. **初始化 Git 仓库**：
   - 在目标目录执行 `git init`
   - 执行 `git add . && git commit -m "[wiki] init: 初始化知识库结构"`
6. **报告完成**：告知用户初始化完成
7. **写入配置文件**：将知识库路径写入同目录 `config.json`：
   ```json
   {
     "wikiPath": "<target_dir的绝对路径>"
   }
   ```
   （路径使用正斜杠 `/`）
8. **引导下一步**：向用户确认如何注册源目录：
   - **选项 A**：用户将源目录路径发给你，你写入 `raw/registry.md`
   - **选项 B**：用户手动编辑 `raw/registry.md`
   完成后说 **"编译"** 或 **"compile"** 即开始批量编译。首次编译可能需要较长时间，请耐心等待。如果只需要目录结构，暂时不编译即可。

**注意事项**：
- 初始化是"一次性空壳搭建"，不做全量编译
- 如果目标目录已有同名文件，跳过而非覆盖，并提醒用户
- 骨架目录在 `references/skeleton/`，直接 `cp -r` 复制即可，不要手动创建文件
- `{{date}}` 占位符替换为当天日期（YYYY-MM-DD 格式）

---

## 能力二：Ingest（导入来源）

适用于单个文件的导入。Ingest 只处理页面本身（摘要页、概念页、实体页），**不碰 index.md 和 log.md**——这两个由 Compile 统一收尾。

**流程**：

1. **读取源文件**，通读全文，提取关键概念、实体、技术要点
2. **创建来源摘要页**：在 `wiki/sources/` 中创建文件，格式：
   ```markdown
   ---
   title: 来源标题
   sources:
     - personal-dev-clone/文件名.md
   ingested: YYYY-MM-DD
   tags: [标签1, 标签2]
   ---
   # 标题

   **Summary**: 一句话总结该来源的核心内容。

   ## 关键概念
   - [[概念A]]

   ## 关键实体
   - [[实体X]]
   ```
3. **创建/更新概念页**（`wiki/concepts/`）：
   - 提取技术、模式、思想、方法论等抽象概念
   - 已存在 → 补充新信息，注明来源
   - 不存在 → 创建新页面（模板见下方"页面模板"）
4. **创建/更新实体页**（`wiki/entities/`）：
   - 提取人物、工具、机构、项目、论文等具体实体
   - 已存在 → 补充，不存在 → 创建
5. **跨来源合成**：如果新来源涉及多个已有概念的综合对比，考虑在 `wiki/synthesis/` 创建综合分析页
6. **写入关系字段**：在 frontmatter 中添加关系类型字段（如 `part_of:`、`depends_on:`），同步在正文 `## 关系` 区块写 `@type` 链接。关系标注是编译过程中的必选步骤，即使暂无关系也应保留空 `## 关系` 区块。关系词汇表和写法见底部"参考"部分。

**页面命名规范**：
- 根据文档内容选择合适的文件名语言（中文或英文 kebab-case），frontmatter 中的 title 字段保持与页面标题一致

**来源标注**：正文中每个关键断言后加 `^[来源路径]`，例如：
> LLM 消除了知识维护的簿记难题。^[raw/articles/karpathy-llm-wiki-research.md]
> GoFrame TOML 键名大小写敏感。^[personal-dev-clone/dw-module.md]

一篇新来源通常联动更新 **5-15 个 wiki 页面**。

**用户聊天框临时发文件**：如果用户直接在聊天框拖入文件要求编译：
1. 将文件保存到 `raw/articles/` 下（按日期命名，如 `user-upload-20260505.md`）
2. 按正常 Ingest 流程处理，source 字段写 `raw/articles/文件名.md`
3. 无需经过 registry.md

---

## 能力三：Compile（批量编译）

当用户说"编译"、"compile"、"总结文档"、"总结资料"时执行。

**流程**：

1. **读源目录注册表**：读取 `raw/registry.md` 获取所有源目录路径
2. **读编译状态**：读取 `scripts/compile-state.json` 获取上次编译的文件快照。如果 state 文件不存在或 files 为空，视为首次编译，所有文件标记为 ingest。
3. **增量扫描**：遍历所有源目录，对每个文件：
   - 计算当前文件内容的 MD5 hash（`hashlib.md5(content).hexdigest()[:8]`）
   - 对比 compile-state.json 中的历史 hash（空 hash 视为变化，触发 update）：
     - 新文件（不在 state 中）→ 标记为 ingest
     - hash 变化 → 标记为 update
     - hash 未变 → 跳过
     - 文件已删除（在 state 中但磁盘不存在）→ 标记为 deleted
4. **处理文件**：对标记为 ingest/update 的文件执行 Ingest 流程
5. **更新编译状态**：将所有处理过的文件写入 compile-state.json，记录当前 hash 和对应的 wiki 页面
6. **收尾**：统一更新 index.md（加入新页面）、overview.md（刷新 Health Dashboard 统计）和 log.md（追加本次编译记录）
7. **报告编译结果**：处理了多少文件，创建/更新了多少页面，跳过了多少

**编译状态文件格式**：
```json
{
  "lastCompile": "YYYY-MM-DD",
  "files": {
    "personal-dev-clone/dgs-module.md": {
      "hash": "a1b2c3d4",
      "lastProcessed": "YYYY-MM-DD",
      "wikiPages": ["wiki/sources/dgs-module.md"]
    }
  }
}
```

路径约定：
- `raw/` 内的文件 → 用相对于知识库根的相对路径（如 `raw/articles/xxx.md`）
- 外部目录（registry.md 中注册） → 用 `逻辑名/文件名`（如 `personal-dev-clone/dgs-module.md`），LLM 根据逻辑名查 registry.md 找到实际路径

hash 基于内容计算，不随文件移动而变。文件移动但内容不变时 hash 相同，无需重新编译，只需 registry.md 中的路径映射更新即可。

---

## 能力四：Lint（健康检查）

当用户说"lint"或"检查健康"时执行。

**脚本检查**：运行 `scripts/lint.py wiki/`
1. 断链检测：`[[wikilinks]]` 指向不存在的页面
2. 孤儿页检测：无入链的页面（排除 overview.md、index.md、log.md、QUESTIONS.md 及 templates/ 目录）
3. 空页面检测：内容仅模板占位符
4. 关系一致性：自动比对 frontmatter 与正文的关系字段是否一致

**LLM 专属检查**（脚本无法替代）：
5. **过时断言**：扫描"目前/现在/latest/currently"等时间词，**仅当同句有版本号或具体日期时才标记**
6. **矛盾检测**：对比多个页面，识别对同一事实的冲突描述
7. **低置信度**：标记缺少 `^[来源]` 标注的关键断言
8. **知识缺口**：识别被多次提及但缺少独立页面的重要概念

结果写入 `outputs/lint.md`。

---

## 能力五：Query（查询）

当用户提问知识库相关问题时执行。核心原则：**编译优于检索**——知识已在 wiki 中结构化，查询是精准定位和综合，不是重新推导。

### 意图分类

LLM 自行判断问题意图类型，选择对应检索策略：

| 意图 | 典型问法 | 检索策略 |
|------|---------|---------|
| **entity**（实体/概念） | "X 是什么"、"tell me about X"、"X 有哪几种" | 读 `index.md` → 定位概念/实体页 → 简洁回答 |
| **relationship**（关系） | "A 和 B 什么关系"、"X 依赖什么"、"X 调用谁" | 读 `index.md` → 读双方页面 + frontmatter 关系字段 → 回答关系 |
| **procedural**（流程/方法） | "部署流程是什么"、"怎么做 X"、"X 的步骤" | 读 `index.md` → 读流程相关页面 → 详细分步回答 |
| **general**（综合） | "X 整体架构"、"X 和 Y 对比"、开放性问题 | 读 `index.md` → 用关键词 grep 定位多页面 → 综合回答 |

### 检索流程

```
用户问题 → LLM 判断意图类型 → 读 index.md 定位候选页面
  → Grep 关键词进一步定位 → 读取目标页面（含 frontmatter 关系字段）
  → 综合回答（精准、克制，只回答所问） → 判断是否归档
```

- **第一入口始终是 `wiki/index.md`**：它包含所有页面的分类索引和一句话描述
- **Grep 辅助定位**：当 index.md 一句话描述不够精确时，用 Grep 搜索关键词定位具体页面
- **读取 frontmatter**：读取目标页面时必须包含 YAML frontmatter，其中的关系字段（`part_of`、`depends_on` 等）是回答关系类问题的关键数据

### 回答风格

- **精准克制**：只回答用户问的内容，不主动展开到相关话题
- **有根据**：每个关键断言后标注引用的 wiki 页面（如 `[[业务拨测]]`）
- **结构化**：流程类用编号列表，对比类用表格，概念类用定义+要点
- **承认缺失**：如果 wiki 中没有相关信息，明确告知用户知识缺口

### 归档标准

有长期价值的回答归档到 `outputs/query-YYYYMMDD.md`（追加到当日文件）：

**需要归档**：
- 故障排查经验（如何定位和解决某个问题）
- 跨来源对比分析（两个模块/系统的异同）
- 技术方案和最佳实践
- 流程文档和操作指南

**不需要归档**：
- 简单事实查询（有几种类型、端口号、依赖关系）
- 一次性概念解释
- 已经存在于 wiki 中的内容复述

### 建议编译

如果查询过程中发现 wiki 缺失某个重要概念或关系，在回答末尾建议用户：
1. 补充源文件到 `raw/` 目录
2. 执行 Compile 生成正式 wiki 页面

---

## 参考：关系标注

编译时在 wiki 页面中写入类型化关系。采用 YAML frontmatter + 正文 `@type` 链接双写格式。

### 关系词汇表

| 类型 | 含义 | 示例 |
|------|------|------|
| calls | A 调用 B 的接口/API | DGS 数据同步 calls NMS 接口 |
| depends_on | A 依赖 B（运行时/配置依赖） | DGS 告警聚合 depends_on DGS 节点在线状态 |
| defines | A 定义了 B（类、函数、配置项） | 拨测策略模块 defines 拨测策略接口 |
| implements | A 实现了 B 模式/协议/接口 | 拨测策略模式 implements 策略模式 |
| queries | A 查询 B 的数据库/表/缓存 | 巡检服务 queries 设备状态表 |
| triggers | A 触发 B（事件/告警/任务/定时器） | 节点离线 triggers DGS 节点离线告警 |
| configures | A 配置 B（配置项控制的行为） | Nacos 配置项 configures DGS 刷新频率 |
| transforms | A 把数据转换成 B 格式/状态 | 数据源解析 transforms EIAP 数据为统一格式 |
| part_of | A 属于 B 的子模块 | DGS 告警聚合 part_of DGS |
| related_to | 其他关联 | 知识管理实践 related_to Karpathy LLM Wiki |

拿不准时先用 `related_to`，后续确认有价值再拆分。已有类型不删除，标记 deprecated 即可。

### Agent 自主扩展

标准词汇表够用，不新增。Agent 在编译时发现无法涵盖的关系：
1. 判断该关系是否在同一场景多次出现，是否在后续查询中会被频繁用到
2. 确认有价值后，以新关系类型（kebab-case 命名，如 `escalates_to`、`routes_to`）在此词汇表追加一行
3. 后续 wiki 页面统一使用新名称

### 页面中的写法

**YAML frontmatter（机器读）**：关系类型作为顶层 YAML 键，值为 wikilink 数组。

```yaml
---
title: DGS 告警聚合
kind: concept
part_of:
  - "[[DGS 数据联网监控]]"
triggers:
  - "[[MQ 告警]]"
depends_on:
  - "[[DGS 数据同步]]"
---
```

**正文 `## 关系` 区块（人可读）**：使用 `@type` 语法标注。

```markdown
## 关系

- → [[DGS 数据联网监控|DGS 数据联网监控 @part_of]]
- → [[MQ 告警|MQ 告警 @triggers]]
- → [[DGS 数据同步|DGS 数据同步 @depends_on]]
```

两者必须保持一致。

---

## 通用规则

### Git 自动提交

知识库根目录使用本地 git 仓库管理，**每次 wiki 操作完成后自动提交**。不需要远程仓库，纯本地使用。

- **Init 完成后**：`git add . && git commit -m "[wiki] init: 初始化知识库结构"`
- **Compile/Ingest 完成后**：`git add` 新增/修改的 wiki 文件 + `scripts/compile-state.json` + `raw/registry.md` + `git commit -m "[wiki] compile: ..."`
- **Lint 完成后**：`git add outputs/lint.md && git commit -m "[wiki] lint: ..."`
- **Query 归档后**：`git add outputs/query-YYYYMMDD.md && git commit -m "[wiki] query: ..."`（如果有归档）

### 注意事项

1. **不要过度拆分**：一个概念一页即可，不要为了数量拆成多页
2. **保持术语一致**：同一概念全文统一名称，aliases 字段记录别名
3. **优先更新而非新建**：已存在的概念/实体页优先追加内容
4. **链接即知识**：页面间的链接和页面本身一样重要，确保链接准确
5. **人类判断优先**：遇到不确定的分类或矛盾信息，在回复中询问用户
6. **文件命名**：根据文档内容选择合适的文件名语言，frontmatter title 始终保持一致
7. **来源标注不可省**：每个关键断言后必须加 `^[来源路径]`
8. **overview 同步更新**：每次编译后刷新 overview.md 中的 Health Dashboard 统计
9. **首次编译可能产生大量页面**：一个 rich 的源文件可能联动创建 10-20 个 wiki 页面，请耐心等待完成。
10. **关系标注不可省**：关系字段是编译时的必选步骤，即使暂无关系也应保留空 `## 关系` 区块。

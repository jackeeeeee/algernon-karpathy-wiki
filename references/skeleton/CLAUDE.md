---
name: knowledge-base
description: >
  LLM-maintained personal knowledge base for Algernon's NMS运维开发工作。
  基于 Karpathy LLM Wiki 模式，使用 Obsidian 作为前端，qmd 作为搜索层。
  当用户提到知识管理、文档编译、查询、lint 时使用此技能。
---

# 知识库行为契约
> 本行为契约基于 [[raw/articles/karpathy-llm-wiki-research]] 编译生成，结合 cablate/llm-atomic-wiki 实战经验优化 Lint 分工。

你是这个知识库的维护者。核心职责：读取 raw/ 中的原始资料，编译成 wiki/ 中结构化的互链页面，并持续维护知识库的健康。

## 目录结构

```
knowledge-base/
├── raw/              # 原始资料层（人类所有，LLM 只读，绝不修改）
│   ├── registry.md   # 源文件目录注册表（LLM 编译时先读此文件定位源文件）
│   ├── articles/     # 手动保存的文章（Markdown）
│   ├── clippings/    # Obsidian Web Clipper 剪藏
│   ├── images/       # 截图和图片
│   ├── pdfs/         # PDF 及配套元数据
│   ├── notes/        # 随手记录
│   └── personal/     # 自己写的文章、分析报告、投资笔记
├── wiki/             # 编译层（LLM 完全拥有，人类只读不编辑）
│   ├── index.md      # 全局索引（LLM 查询的第一入口）
│   ├── log.md        # 追加式操作日志（graph-excluded: true）
│   ├── overview.md   # 高层综述 + Health Dashboard
│   ├── QUESTIONS.md  # 开放问题队列
│   ├── sources/      # 每个来源的摘要页
│   ├── concepts/     # 思想、模式、技术（含 aliases 跨语言字段）
│   ├── entities/     # 人物、工具、机构、论文
│   ├── synthesis/    # 跨来源合成分析
│   └── templates/    # 页面模板（LLM 使用）
├── outputs/          # 查询答案、图表、幻灯片、lint 报告
│   ├── lint.md       # lint 报告
│   └── query-YYYYMMDD.md # 查询答案（按日期分文件）
├── scripts/
│   ├── lint.py              # Wiki 健康检查脚本
│   ├── compile-state.json   # 编译状态（源文件 hash 和对应 wiki 页面的映射）
│   └── qmd-reindex.sh       # qmd 索引重建脚本
├── CLAUDE.md         # 本文件：LLM 行为契约
└── README.md         # 项目说明
```

## 核心原则

1. **raw/ 不可变**：LLM 只读取 raw/ 中的文件，绝不修改、移动或删除
2. **wiki/ 由 LLM 全权负责**：创建、更新、删除 wiki/ 中的页面，人类不手动编辑
3. **编译优于检索**：新资料进来后，主动编译成结构化页面，不是简单索引
4. **双向链接**：所有 wiki 页面使用 `[[wikilinks]]` 建立互连
5. **输出归档**：查询结果有价值时，归档到 outputs/，形成知识复利

## 操作一：Ingest（导入）

当发现新源文件时（通过 raw/registry.md 中的目录），执行以下流程：

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
   - 不存在 → 创建新页面
4. **创建/更新实体页**（`wiki/entities/`）：
   - 提取人物、工具、机构、项目、论文等具体实体
   - 已存在 → 补充，不存在 → 创建
5. **跨来源合成**：如果新来源涉及多个已有概念的综合对比，考虑在 `wiki/synthesis/` 创建综合分析页
6. **写入关系字段**：在 frontmatter 中添加关系类型字段（如 `part_of:`、`depends_on:`），同步在正文 `## 关系` 区块写 `@type` 链接。关系字段是编译过程中的必选步骤，确保知识图谱数据的完整性（详见"知识图谱关系标注"）

一篇新来源通常联动更新 **5-15 个 wiki 页面**。

## 操作二：Query（查询）

当用户提问时：

1. **先读 index.md** 快速定位相关页面
2. **读取相关 wiki 页面**，综合给出答案
3. **引用来源**：回答中标注引用了哪些 wiki 页面
4. **判断是否归档**：如果答案有长期价值（排查经验、对比分析、技术方案），写入 `outputs/query-YYYYMMDD.md`（按日期分文件），并建议用户是否要将其编译为正式 wiki 页面

## 操作三：Compile（编译）

当用户说"编译"或"compile"时：

1. **读源目录注册表**：读取 `raw/registry.md` 获取所有源目录路径
2. **读编译状态**：读取 `scripts/compile-state.json` 获取上次编译的文件快照
3. **增量扫描**：遍历所有源目录，对每个文件：
   - 计算当前文件内容的 MD5 hash（`hashlib.md5(content).hexdigest()[:8]`）
   - 对比 compile-state.json 中的历史 hash：
     - 新文件（不在 state 中）→ 标记为 ingest
     - hash 变化 → 标记为 update
     - hash 未变 → 跳过
     - 文件已删除（在 state 中但磁盘不存在）→ 标记为 deleted
4. **处理文件**：对标记为 ingest/update 的文件执行 Ingest 流程
5. **更新编译状态**：将所有处理过的文件写入 compile-state.json，记录当前 hash 和对应的 wiki 页面
6. **收尾**：统一更新 index.md（加入新页面）、overview.md（刷新 Health Dashboard 统计）和 log.md（追加本次编译记录）
7. **报告编译结果**：处理了多少文件，创建/更新了多少页面，跳过了多少

一篇新来源通常会联动更新 5-15 个 wiki 页面。

## 操作四：Lint（健康检查）

当用户说"lint"或"检查健康"时，执行以下检查：

### 脚本检查（运行 `scripts/lint.py`）

1. **断链检测**：查找 `[[wikilinks]]` 中指向不存在页面的链接
2. **孤儿页检测**：查找没有任何入链的 wiki 页面（overview.md、index.md、log.md、QUESTIONS.md 及 templates/ 目录除外）
3. **空页面检测**：查找内容为空或仅有模板的页面

### LLM 专属检查（脚本无法替代，必须你执行）

4. **过时断言**：扫描含"目前/现在/latest/currently"等时间词的断言，**仅当同一句中出现版本号或具体日期时才标记**（如"当前使用 v3.2"），避免正常行文的误报。发现后注明原文并建议更新或删除。
5. **矛盾检测**：对比多个 wiki 页面，识别对同一事实的冲突描述（如一个页面说 A 依赖 B，另一个说 A 替代 B）。
6. **低置信度**：标记 wiki 页面中缺少 `^[来源]` 标注的关键断言。
7. **知识缺口**：识别被多次提及但缺少独立页面的重要概念。

检查结果写入 `outputs/lint.md`，并在回复中总结关键问题。

## 页面模板规范

所有 wiki 页面必须遵循以下模板结构：

```markdown
---
title: 页面标题
kind: concept|entity|synthesis|overview
created: 2026-04-30
updated: 2026-04-30
aliases: [别名1, 别名2]
tags: [标签1, 标签2]
sources:
  - raw/articles/karpathy-llm-wiki-research.md
  - personal-dev-clone/dgs-module.md
---

# 页面标题

**Summary**: 一句话概括页面核心内容。

---

## 正文内容

内容按逻辑分节，使用清晰的标题层级。

关键断言标注来源：^[raw/articles/来源.md]

## 关系

- → [[相关概念A|相关概念A @part_of]]

## 相关链接

- [[相关概念A]]
- [[相关实体B]]
- [[对比分析C]]
```

**页面类型说明**：
- `concept`：思想、模式、技术（如 "RAG vs 编译"、"Zettelkasten"）
- `entity`：具体的人、工具、机构、项目（如 "Karpathy"、"Obsidian"、"NMS"）
- `synthesis`：跨来源的对比分析、综合论述
- `overview`：领域综述页，连接多个概念

**空段落是有意为之的结构信号**。页面中如"暂无数据"、"待补充"等标记告诉后续 LLM 该关注哪些信息缺口。编译时应主动填充这些空段落。

## 索引文件规范

`wiki/index.md` 必须保持以下格式：

```markdown
# 知识库索引

最后更新：2026-04-30

## Concepts（概念）
- [[概念A]] - 一句话摘要
- [[概念B]] - 一句话摘要

## Entities（实体）
- [[实体X]] - 一句话摘要

## Synthesis（合成分析）
- [[分析Y]] - 一句话摘要

## Sources（来源摘要）
- [[来源Z]] - 一句话摘要
```

## 日志文件规范

`wiki/log.md` 使用追加式格式：

```markdown
# 操作日志

## [2026-04-30] ingest | NMS部署文档.md
处理了 personal-dev-clone/nms-deploy.md，创建了 3 个概念页，更新了 2 个实体页。

## [2026-04-30] query | DGS节点离线排查
查询了DGS节点离线相关问题，答案归档至 outputs/query-20260430.md。

## [2026-04-30] lint
发现 2 个断链，1 个孤儿页，已自动修复。
```

## 编译状态文件规范

`scripts/compile-state.json` 记录每个源文件的处理状态，用于增量编译：

```json
{
  "lastCompile": "2026-04-30",
  "files": {
    "personal-dev-clone/dgs-module.md": {
      "hash": "a1b2c3d4",
      "lastProcessed": "2026-04-30",
      "wikiPages": ["wiki/sources/dgs-module.md"]
    },
    "raw/articles/karpathy-llm-wiki-research.md": {
      "hash": "e5f6g7h8",
      "lastProcessed": "2026-04-30",
      "wikiPages": ["wiki/sources/karpathy-llm-wiki-research.md"]
    }
  }
}
```

路径约定：
- `raw/` 内的文件 → 用相对于知识库根的相对路径（如 `raw/articles/xxx.md`）
- 外部目录（registry.md 中注册） → 用 `逻辑名/文件名`（如 `personal-dev-clone/dgs-module.md`），LLM 根据逻辑名查 registry.md 找到实际路径

- `hash`：文件内容的 MD5 前 8 位（基于内容，不随文件移动而变）
- `lastProcessed`：上次处理日期
- `wikiPages`：该源文件对应生成的 wiki 页面列表（相对知识库根路径）

编译完成后必须更新此文件。当源文件 hash 变化时，LLM 需重新编译并更新 wikiPages。文件移动位置但内容不变时 hash 相同，无需重新编译，只需 registry.md 中的路径映射更新即可。

## 知识图谱关系标注

在 wiki 页面的 YAML frontmatter 中直接在顶层添加关系字段（不嵌套），用于在 Obsidian Graph View 中展示带类型标签的连线。关系标注是编译过程中的必选步骤。

### 基准关系词汇表

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

### Agent 自主扩展

基准词汇表是起点，不是终点。Agent 在编译时遇到上述类型无法覆盖的关系：
1. 判断该关系是否在同一领域中多次出现、是否在后续查询中会被明确用到
2. 如果满足条件，创建新类型（kebab-case 命名，如 escalates_to、routes_to），在此词汇表中追加一行
3. 在新编译的页面中使用该类型

拿不准时先用 related_to，后续确认有价值再拆分。已有类型不删除，标记 deprecated 即可。

### 页面中的写法

关系标注采用 YAML frontmatter + 正文 `@type` 链接双写格式。

**YAML frontmatter（机器读）**：关系类型作为顶层 YAML 键，值为 wikilink 数组。多个目标用多行数组，单个目标也写成数组保持一致性。

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

**正文 `## 关系` 区块（人可读）**：使用 `@type` 语法标注在 wikilink alias 中，用箭头区分出向关系。

```markdown
## 关系

- → [[DGS 数据联网监控|DGS 数据联网监控 @part_of]]
- → [[MQ 告警|MQ 告警 @triggers]]
- → [[DGS 数据同步|DGS 数据同步 @depends_on]]
```

两者必须保持一致。如果安装了 Wikilink Types 插件，它会自动在两者之间同步。未安装插件时，前文和 body 互为备份，lint 时可检查一致性。

## 搜索层说明

知识库使用 [qmd](https://github.com/tobi/qmd) 作为搜索层（当 wiki 页面超过 200 页时启用）：

```bash
qmd search "关键词"     # BM25 关键词搜索
qmd vsearch "语义查询"   # 向量语义搜索
qmd query "混合查询"     # BM25 + 向量 + LLM 重排
```

qmd 索引范围：`wiki/` 目录下的所有 .md 文件。

## 注意事项

1. **不要过度拆分**：一个概念一页即可，不要为了数量拆成多页
2. **保持一致的术语**：同一概念在全文中使用统一名称，aliases 字段记录别名
3. **优先更新而非新建**：已存在的概念/实体页优先追加内容，不要重复创建
4. **链接即知识**：页面间的链接和页面本身一样重要，确保链接准确
5. **人类判断优先**：遇到不确定的分类或矛盾信息，在回复中询问用户

---
name: knowledge-base
description: >
  LLM-maintained personal knowledge base based on Karpathy LLM Wiki pattern.
  Use Obsidian as frontend, qmd as search layer.
  Trigger when: 知识管理、文档编译、查询、lint、ingest、compile、wiki 维护。
---

# 知识库行为契约

你是这个知识库的维护者。核心职责：读取 raw/ 中的原始资料，编译成 wiki/ 中结构化的互链页面，并持续维护知识库的健康。

详细操作流程见 SKILL.md 中的七大能力定义。

## 核心原则

1. **raw/ 不可变** — LLM 只读，绝不修改
2. **wiki/ LLM 全权负责** — 创建、更新、维护所有页面，人类只读不编辑
3. **编译优于检索** — 知识编译一次并保持最新，不是每次查询重新推导
4. **双向链接** — 所有 wiki 页面使用 `[[wikilinks]]` 建立互连
5. **输出归档** — 有价值的答案归档回 outputs/，形成知识复利

## 目录结构

```
<知识库根>/
├── raw/              # 原始资料（人类所有，LLM 只读）
│   ├── registry.md   # 源文件目录注册表
│   ├── articles/     # Markdown 文章
│   ├── clippings/    # Obsidian Web Clipper 剪藏
│   ├── images/       # 截图和图片
│   ├── pdfs/         # PDF 及配套元数据
│   ├── notes/        # 随手记录
│   └── personal/     # 自己写的内容
├── wiki/             # 编译层（LLM 全权拥有，人类只读）
│   ├── index.md      # 全局索引（查询第一入口）
│   ├── log.md        # 追加式操作日志（graph-excluded: true）
│   ├── overview.md   # 高层综述 + Health Dashboard
│   ├── QUESTIONS.md  # 开放问题队列
│   ├── sources/      # 来源摘要页
│   ├── concepts/     # 概念、模式、技术
│   ├── entities/     # 人物、工具、机构、论文
│   ├── synthesis/    # 跨来源综合分析
│   └── templates/    # 页面模板
├── outputs/          # 查询答案、lint 报告
├── scripts/          # lint.py、compile-state.json、qmd-reindex.sh
├── CLAUDE.md         # 本文件
└── README.md
```

## 关系词汇表

编译时在 wiki 页面写入类型化关系（YAML frontmatter + 正文 `@type` 双写）：

| 类型 | 含义 | 示例 |
|------|------|------|
| calls | A 调用 B 的接口/API | DGS 数据同步 calls NMS 接口 |
| depends_on | A 依赖 B | DGS 告警聚合 depends_on 节点状态 |
| defines | A 定义了 B（配置、接口、字段、规则） | NMSInterface.json defines 接口映射 |
| implements | A 实现了 B 模式/接口/协议 | 策略实现 implements 策略模式 |
| queries | A 查询 B 的数据库 | 巡检服务 queries 设备状态表 |
| triggers | A 触发 B | 节点离线 triggers 告警 |
| configures | A 配置 B | Nacos 配置 configures 刷新频率 |
| transforms | A 转换成 B 格式 | 解析器 transforms EIAP 数据 |
| part_of | A 是 B 的组成部分，只存子 -> 父 | 告警聚合 part_of DGS 监控 |
| related_to | 其他关联，不参与强推理 | 知识管理 related_to Karpathy LLM Wiki |

方向规则：
- `part_of` 只写子 -> 父；父页面不要把“包含子模块”写成反向 `part_of`。
- 不双写 `contains`/`has_part`，查询时从子页面 `part_of` 反查。
- `implements` 只用于具体实现 -> 抽象模式/接口/协议。
- `defines` 只用于定义者 -> 被定义物，不表示普通包含。
- `kind: source` 页面不进入领域关系图，只保留普通关键概念/关键实体链接。
- 拿不准时先用 `related_to` 或普通 wikilink，并记录待确认问题。

## 页面模板

```markdown
---
title: 页面标题
kind: concept|entity|synthesis|overview|log|questions
created: {{date}}
updated: {{date}}
aliases: []
tags: []
sources: []
# 关系字段（编译时自动填充）
---

# 页面标题

**Summary**: 一句话概括。

---

## 正文内容

关键断言标注来源：^[raw/articles/来源.md]

## 关系

- → [[相关概念|相关概念 @part_of]]

## 相关链接

- [[相关概念]]
```

关系字段（frontmatter + 正文 `## 关系`）是编译时的**必选步骤**，即使暂无关系也应保留空 `## 关系` 区块。

## 注意事项

1. **不要过度拆分** — 一个概念一页
2. **术语一致** — 同一概念全文统一，aliases 记录别名
3. **优先更新而非新建** — 已存在的页面优先追加
4. **链接即知识** — 确保链接准确
5. **来源标注不可省** — 每个关键断言后加 `^[来源路径]`
6. **人类判断优先** — 不确定的分类或矛盾，询问用户

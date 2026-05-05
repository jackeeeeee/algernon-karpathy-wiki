# 个人知识库

基于 Karpathy LLM Wiki 模式的个人知识库系统。Obsidian 作为前端，Claude Code 作为编译引擎，qmd 作为搜索层。

## 快速开始

### 1. 用 Obsidian 打开

在 Obsidian 中将本目录作为 Vault 打开。

### 2. 导入资料

把原始文档（Markdown/PDF/笔记等）放入 `raw/` 对应的子目录：

```
raw/
├── articles/   # 文章
├── clippings/  # Web Clipper 剪藏
├── pdfs/       # PDF
├── notes/      # 随手记录
└── personal/   # 自己写的内容
```

或者在 `raw/registry.md` 中注册外部目录路径（适合散落在代码库、技能目录中的源文件）。

### 3. 让 Claude Code 编译

```bash
claude
```

然后告诉 Claude：`"Compile the wiki"` 或 `"Ingest the new files in raw/"`

### 4. 日常查询

继续在 Claude Code 里提问，或者安装 qmd 后用：

```bash
npm install -g @tobilu/qmd
qmd query "你的问题"
```

### 5. 健康检查

```bash
python scripts/lint.py
```

## 目录说明

| 目录 | 用途 |
|---|---|
| `raw/` | 原始资料，人类所有，LLM 只读 |
| `wiki/` | 编译后的知识页面，LLM 全权维护 |
| `outputs/` | 查询结果和 lint 报告 |
| `scripts/` | 自动化脚本 |

## 核心文件

- `CLAUDE.md` - LLM 行为契约（告诉 Claude 如何维护知识库）
- `wiki/index.md` - 全局索引
- `wiki/log.md` - 操作日志
- `wiki/overview.md` - 综述和健康面板
- `wiki/QUESTIONS.md` - 开放问题队列
- `raw/registry.md` - 外部源目录注册表

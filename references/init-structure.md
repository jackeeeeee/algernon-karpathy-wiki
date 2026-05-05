# 知识库初始化 — 完整文件清单

> **本文件仅供参考，不再是 init 的数据源。**
> Init 流程使用 `references/skeleton/` 目录进行 `cp -r` 复制。
> 本文件保留作为人类可读的文件清单文档，方便理解骨架结构。
> 如果修改了 `skeleton/` 中的文件，请同步更新本文档以保持一致。

---

## 一、目录结构

```
<target>/
├── raw/
│   ├── registry.md       # 源文件目录注册表
│   ├── articles/
│   ├── clippings/
│   ├── images/
│   ├── pdfs/
│   ├── notes/
│   └── personal/
├── wiki/
│   ├── sources/
│   ├── concepts/
│   ├── entities/
│   ├── synthesis/
│   └── templates/
├── outputs/
├── scripts/
├── CLAUDE.md
└── README.md
```

---

## 二、wiki/templates/ 模板文件

### wiki/templates/concept.md

```markdown
---
title: "{{title}}"
kind: concept
created: "{{date}}"
updated: "{{date}}"
aliases: []
tags: []
sources: []
# 关系字段（编译时 LLM 自动填充，如 part_of, depends_on 等）
---

# {{title}}

**Summary**: 一句话概括页面核心内容。

---

## 正文内容

_在此编写内容，关键断言标注来源：^[raw/来源路径]_

## 关系

- → [[相关概念|相关概念 @part_of]]

## 相关链接

- _相关页面 wikilink_
```

### wiki/templates/entity.md

```markdown
---
title: "{{title}}"
kind: entity
created: "{{date}}"
updated: "{{date}}"
aliases: []
tags: []
sources: []
# 关系字段（编译时 LLM 自动填充）
---

# {{title}}

**类型**: 人物/工具/机构/项目/论文
**Summary**: 一句话概括。

---

## 基本信息

_关键属性、背景信息_

## 相关概念

- _相关概念 wikilink_

## 相关链接

- _相关实体 wikilink_
```

### wiki/templates/synthesis.md

```markdown
---
title: "{{title}}"
kind: synthesis
created: "{{date}}"
updated: "{{date}}"
aliases: []
tags: []
sources: []
# 关系字段（编译时 LLM 自动填充）
---

# {{title}}

**Summary**: 一句话概括综合分析的核心结论。

---

## 分析维度

### 维度一

_内容，标注来源：^[raw/来源路径]_

### 维度二

_内容_

## 对比总结

| 维度 | A | B |
|---|---|---|
| 特性1 | ... | ...

## 结论

_综合分析得出的结论_

## 相关链接

- _相关概念 A wikilink_
- _相关实体 B wikilink_
```

---

## 三、wiki/ 核心文件

### wiki/index.md

```markdown
# 知识库索引

最后更新：{{date}}

## Concepts（概念）
_暂无 — 待编译_

## Entities（实体）
_暂无 — 待编译_

## Synthesis（合成分析）
_暂无 — 待编译_

## Sources（来源摘要）
_暂无 — 待编译_
```

### wiki/log.md

```markdown
# 操作日志

> 追加式记录，永不删除或修改已有条目。

```

### wiki/overview.md

```markdown
# 知识库综述

> 高层视角：当前知识库覆盖哪些领域，健康状态如何。

## 覆盖领域

_待编译_

## Health Dashboard

| 指标 | 值 |
|---|---|
| 概念页数量 | 0 |
| 实体页数量 | 0 |
| 来源页数量 | 0 |
| 合成分析页数量 | 0 |
| **总 wiki 页面** | **0** |
| raw 文件数量 | 0 |
| 最后编译时间 | 未编译 |
| 最后 lint 时间 | 未检查 |
| 处理率 | 0%

## 待解决问题

见 [[QUESTIONS]]
```

### wiki/QUESTIONS.md

```markdown
# 开放问题队列

> 记录知识库中尚未解决的问题、待验证的假设、需要用户确认的事项。

_暂无_
```

### raw/registry.md

```markdown
# 源文件目录注册表

> 记录散落在项目各处的源文件目录。编译时 LLM 扫描这些目录中的文件进行编译。
> 文件移动后只需更新此表，无需修改 wiki 页面。

| 逻辑名 | 路径 | 说明 |
|--------|------|------|

```

---

## 四、scripts/ 脚本

### scripts/lint.py

```python
#!/usr/bin/env python3
"""
Wiki 健康检查脚本（确定性检查）

检查项目：
1. 断链检测 - 查找 [[wikilinks]] 中指向不存在页面的链接
2. 孤儿页检测 - 查找没有任何入链的 wiki 页面
3. 空页面检测 - 查找内容为空或仅有模板的页面
4. 关系一致性 - 自动比对 frontmatter 与正文的关系字段是否一致

注意：过时断言检测、矛盾检测、低置信度检测已由 LLM 负责执行，
      因为这些需要语义理解，正则扫描会产生大量误报。
      参见 CLAUDE.md 中的"LLM 专属检查"部分。

用法：python lint.py <wiki目录路径>
"""

import os
import re
import sys
from pathlib import Path


def find_md_files(directory):
    """递归查找所有 .md 文件"""
    md_files = []
    for root, _, files in os.walk(directory):
        for f in files:
            if f.endswith('.md'):
                md_files.append(os.path.join(root, f))
    return md_files


def extract_wikilinks(content):
    """提取所有 [[wikilinks]]"""
    return re.findall(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', content)


def extract_frontmatter(content):
    """提取 YAML frontmatter"""
    match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
    if match:
        return match.group(1)
    return ''


def get_title_from_frontmatter(frontmatter):
    """从 frontmatter 提取 title"""
    match = re.search(r'^title:\s*(.+)$', frontmatter, re.MULTILINE)
    return match.group(1).strip().strip('"').strip("'") if match else None


# --- 关系类型关键词 ---
RELATION_TYPES = [
    'calls', 'depends_on', 'defines', 'implements', 'queries',
    'triggers', 'configures', 'transforms', 'part_of', 'related_to'
]


def extract_fm_relationships(fm_text):
    """从 frontmatter 文本中提取关系链接列表"""
    links = []
    for rtype in RELATION_TYPES:
        pattern = rf'^{rtype}:\s*(?:- "?\[\[([^\]]+)\]\]"?|"\[\[([^\]]+)\]\]"?)'
        matches = re.findall(pattern, fm_text, re.MULTILINE)
        for m in matches:
            link = m[0] or m[1]
            links.append(link)
    return sorted(links)


def extract_body_relationships(body_text):
    """从正文 ## 关系 区块提取链接列表"""
    rel_section_match = re.search(r'^## 关系\s*\n(.*?)(?=^## |\Z)', body_text, re.MULTILINE | re.DOTALL)
    if not rel_section_match:
        return []
    rel_text = rel_section_match.group(1)
    links = re.findall(r'→ \[\[([^\]|]+)(?:\|[^\]]+)?\]\]', rel_text)
    return sorted(links)


def check_relationship_consistency(wiki_dir):
    """检查 frontmatter 与正文关系字段是否一致"""
    issues = []
    md_files = find_md_files(wiki_dir)
    exclude_basenames = {'index.md', 'overview.md', 'log.md', 'QUESTIONS.md'}

    for f in md_files:
        basename = os.path.basename(f)
        if basename in exclude_basenames:
            continue
        rel_path = os.path.relpath(f, wiki_dir)
        if rel_path.startswith('templates' + os.sep) or rel_path.startswith('templates/'):
            continue

        content = open(f, 'r', encoding='utf-8').read()
        fm = extract_frontmatter(content)
        if not fm:
            continue

        has_rel = any(re.search(rf'^{rtype}:', fm, re.MULTILINE) for rtype in RELATION_TYPES)
        if not has_rel:
            continue

        body = content[len(fm) + 7:] if fm else content
        fm_links = extract_fm_relationships(fm)
        body_links = extract_body_relationships(body)

        if fm_links != body_links:
            issues.append(f"  关系不一致: {rel_path} (Frontmatter: {len(fm_links)} 条 vs 正文: {len(body_links)} 条)")

    return issues


def check_broken_links(wiki_dir):
    """检查断链"""
    issues = []
    md_files = find_md_files(wiki_dir)

    title_to_path = {}
    for f in md_files:
        content = open(f, 'r', encoding='utf-8').read()
        fm = extract_frontmatter(content)
        title = get_title_from_frontmatter(fm)
        if title:
            basename = os.path.splitext(os.path.basename(f))[0]
            title_to_path[title] = f
            title_to_path[basename] = f

    for f in md_files:
        content = open(f, 'r', encoding='utf-8').read()
        links = extract_wikilinks(content)
        for link in links:
            if link not in title_to_path:
                rel_path = os.path.relpath(f, wiki_dir)
                issues.append(f"  断链: {rel_path} -> [[{link}]] (页面不存在)")

    return issues


def check_orphan_pages(wiki_dir):
    """检查孤儿页（无入链的页面，排除 index.md/overview.md/log.md/QUESTIONS.md 和 templates/ 目录）"""
    issues = []
    md_files = find_md_files(wiki_dir)
    exclude_basenames = {'index.md', 'overview.md', 'log.md', 'QUESTIONS.md'}

    all_targets = set()
    for f in md_files:
        content = open(f, 'r', encoding='utf-8').read()
        links = extract_wikilinks(content)
        all_targets.update(links)

    for f in md_files:
        basename = os.path.basename(f)
        if basename in exclude_basenames:
            continue
        rel_path = os.path.relpath(f, wiki_dir)
        if rel_path.startswith('templates' + os.sep) or rel_path.startswith('templates/'):
            continue
        content = open(f, 'r', encoding='utf-8').read()
        fm = extract_frontmatter(content)
        title = get_title_from_frontmatter(fm) or os.path.splitext(basename)[0]
        if title not in all_targets:
            rel_path = os.path.relpath(f, wiki_dir)
            issues.append(f"  孤儿页: {rel_path} (title='{title}', 无入链)")

    return issues


def check_empty_pages(wiki_dir):
    """检查空页面（排除 index.md/overview.md/log.md/QUESTIONS.md 和 templates/ 目录）"""
    issues = []
    md_files = find_md_files(wiki_dir)
    exclude_basenames = {'index.md', 'overview.md', 'log.md', 'QUESTIONS.md'}

    for f in md_files:
        basename = os.path.basename(f)
        if basename in exclude_basenames:
            continue
        rel_path = os.path.relpath(f, wiki_dir)
        if rel_path.startswith('templates' + os.sep) or rel_path.startswith('templates/'):
            continue
        content = open(f, 'r', encoding='utf-8').read()
        fm = extract_frontmatter(content)
        body = content[len(fm) + 7:] if fm else content
        body = body.strip()
        if not body or body in ('_在此编写内容_', '_内容_'):
            rel_path = os.path.relpath(f, wiki_dir)
            issues.append(f"  空页面: {rel_path}")

    return issues


def main():
    if len(sys.argv) < 2:
        wiki_dir = os.path.join(os.path.dirname(__file__), '..', 'wiki')
    else:
        wiki_dir = sys.argv[1]

    wiki_dir = os.path.abspath(wiki_dir)
    if not os.path.isdir(wiki_dir):
        print(f"错误: 目录不存在: {wiki_dir}")
        sys.exit(1)

    print(f"Wiki 健康检查: {wiki_dir}")
    print("=" * 50)

    all_issues = []

    print("\n[1/4] 检查断链...")
    broken = check_broken_links(wiki_dir)
    if broken:
        all_issues.extend(broken)
        print(f"  发现 {len(broken)} 个问题")
        for issue in broken:
            print(issue)
    else:
        print("  通过")

    print("\n[2/4] 检查孤儿页...")
    orphans = check_orphan_pages(wiki_dir)
    if orphans:
        all_issues.extend(orphans)
        print(f"  发现 {len(orphans)} 个问题")
        for issue in orphans:
            print(issue)
    else:
        print("  通过")

    print("\n[3/4] 检查空页面...")
    empty = check_empty_pages(wiki_dir)
    if empty:
        all_issues.extend(empty)
        print(f"  发现 {len(empty)} 个问题")
        for issue in empty:
            print(issue)
    else:
        print("  通过")

    print("\n[4/4] 检查关系一致性...")
    rel_issues = check_relationship_consistency(wiki_dir)
    if rel_issues:
        all_issues.extend(rel_issues)
        print(f"  发现 {len(rel_issues)} 个问题")
        for issue in rel_issues:
            print(issue)
    else:
        print("  通过")

    print("\n" + "=" * 50)
    total = len(all_issues)
    if total == 0:
        print("健康状态: 全部通过")
    else:
        print(f"健康状态: 发现 {total} 个问题需要处理")

    return 0 if total == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
```

### scripts/qmd-reindex.sh

```bash
#!/bin/bash
# qmd 索引重建脚本
# 用法: ./qmd-reindex.sh [wiki目录路径]

WIKI_DIR="${1:-$(dirname "$0")/../wiki}"
WIKI_DIR=$(cd "$WIKI_DIR" && pwd)

echo "重建 qmd 索引: $WIKI_DIR"

# 删除旧索引（如果存在）
rm -rf "$WIKI_DIR/../.qmd"

# 重建索引
qmd collection add "$WIKI_DIR" --name wiki

echo "索引重建完成"
```

### scripts/compile-state.json

```json
{
  "lastCompile": "{{date}}",
  "files": {}
}
```

---

## 五、根目录文件

### CLAUDE.md

> Init 时从 `references/CLAUDE.md` 完整拷贝到目标目录。
> 不做任何修改，保证 init 出的知识库拥有完整一致的行为契约。
> 后续 CLAUDE.md 的更新只需同步 `references/CLAUDE.md` 即可。

### README.md

```markdown
# Algernon 个人知识库

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
```

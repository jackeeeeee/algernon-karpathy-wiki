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
    lines = fm_text.split('\n')
    in_rel_key = False
    for line in lines:
        # Check if this line starts a relationship key
        matched_key = False
        for rtype in RELATION_TYPES:
            if re.match(rf'^{rtype}:\s*$', line):
                in_rel_key = True
                matched_key = True
                break
            elif re.match(rf'^{rtype}:\s*-', line):
                # Single-line: key: - "[[...]]"
                m = re.search(r'\[\[([^\]]+)\]\]', line)
                if m:
                    links.append(m.group(1))
                in_rel_key = False
                matched_key = True
                break
        if matched_key:
            continue
        # Check if this line is a list item under a relationship key
        if in_rel_key:
            m = re.search(r'\[\[([^\]]+)\]\]', line)
            if m:
                links.append(m.group(1))
            elif re.match(r'^[a-z]', line) and not line.startswith(' '):
                # New top-level key, stop collecting
                in_rel_key = False
    return sorted(links)


def extract_body_relationships(body_text):
    """从正文 ## 关系 区块提取链接列表"""
    rel_section_match = re.search(r'^## 关系\s*\n(.*?)(?=^## |\Z)', body_text, re.MULTILINE | re.DOTALL)
    if not rel_section_match:
        return []
    rel_text = rel_section_match.group(1)
    links = re.findall(r'→ \[\[([^\]|]+)(?:\|[^\]]+)?\]\]', rel_text)
    return sorted(links)


def is_template_file(rel_path):
    """判断是否为 templates/ 目录下的文件"""
    return rel_path.startswith('templates' + os.sep) or rel_path.startswith('templates/')


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
        if is_template_file(rel_path):
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
    """检查断链（排除 templates/ 目录下的文件）"""
    issues = []
    md_files = find_md_files(wiki_dir)

    # 构建 title/basename -> 文件路径的映射
    title_to_path = {}
    for f in md_files:
        rel_path = os.path.relpath(f, wiki_dir)
        if is_template_file(rel_path):
            continue
        content = open(f, 'r', encoding='utf-8').read()
        fm = extract_frontmatter(content)
        title = get_title_from_frontmatter(fm)
        basename = os.path.splitext(os.path.basename(f))[0]
        # 始终按 basename 索引（无 frontmatter 的文件也能被 wikilink 找到）
        title_to_path[basename] = f
        # 有 title 且与 basename 不同时，额外按 title 索引
        if title and title != basename:
            title_to_path[title] = f

    # 检查每个文件的链接（排除 templates/）
    for f in md_files:
        rel_path = os.path.relpath(f, wiki_dir)
        if is_template_file(rel_path):
            continue
        content = open(f, 'r', encoding='utf-8').read()
        links = extract_wikilinks(content)
        for link in links:
            if link not in title_to_path:
                issues.append(f"  断链: {rel_path} -> [[{link}]] (页面不存在)")

    return issues


def check_orphan_pages(wiki_dir):
    """检查孤儿页（无入链的页面，排除 index.md/overview.md/log.md/QUESTIONS.md 和 templates/ 目录）"""
    issues = []
    md_files = find_md_files(wiki_dir)
    exclude_basenames = {'index.md', 'overview.md', 'log.md', 'QUESTIONS.md'}

    # 收集所有链接目标
    all_targets = set()
    for f in md_files:
        content = open(f, 'r', encoding='utf-8').read()
        links = extract_wikilinks(content)
        all_targets.update(links)

    # 检查每个页面是否被链接
    for f in md_files:
        basename = os.path.basename(f)
        if basename in exclude_basenames:
            continue
        rel_path = os.path.relpath(f, wiki_dir)
        if is_template_file(rel_path):
            continue
        content = open(f, 'r', encoding='utf-8').read()
        fm = extract_frontmatter(content)
        title = get_title_from_frontmatter(fm) or os.path.splitext(basename)[0]
        if title not in all_targets:
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
        if is_template_file(rel_path):
            continue
        content = open(f, 'r', encoding='utf-8').read()
        fm = extract_frontmatter(content)
        body = content[len(fm) + 7:] if fm else content
        body = body.strip()
        if not body or body in ('_在此编写内容_', '_内容_'):
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

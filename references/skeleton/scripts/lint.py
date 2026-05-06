#!/usr/bin/env python3
"""
Wiki 健康检查脚本（确定性检查）

检查项目：
1. 断链检测 - 查找 [[wikilinks]] 中指向不存在页面的链接
2. 孤儿页检测 - 查找没有任何入链的 wiki 页面
3. 空页面检测 - 查找内容为空或仅有模板的页面
4. 关系一致性 - 自动比对 frontmatter 与正文的关系三元组是否一致
5. Canonical link 检测 - index.md 必须使用真实相对路径链接

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


def get_field_from_frontmatter(frontmatter, field):
    """提取 frontmatter 单行字段"""
    match = re.search(rf'^{re.escape(field)}:\s*(.+)$', frontmatter, re.MULTILINE)
    return match.group(1).strip().strip('"').strip("'") if match else None


def get_list_field_from_frontmatter(frontmatter, field):
    """提取 frontmatter 列表字段"""
    lines = frontmatter.split('\n')
    values = []
    in_list = False
    for line in lines:
        if re.match(rf'^{re.escape(field)}:\s*$', line):
            in_list = True
            continue
        if in_list:
            if re.match(r'^[A-Za-z_][A-Za-z0-9_-]*:\s*', line):
                break
            m = re.match(r'^\s*-\s*(.+)$', line)
            if m:
                value = m.group(1).strip().strip('"').strip("'")
                values.append(value)
    return values


def normalize_link_target(target):
    """规范化 wikilink 目标，移除锚点、扩展名并统一路径分隔符"""
    target = target.split('#', 1)[0].replace('\\', '/').strip()
    if target.endswith('.md'):
        target = target[:-3]
    return target


def build_link_index(wiki_dir):
    """构建 title、basename、relative path 到实际文件的映射"""
    link_index = {}
    path_stems = set()
    md_files = find_md_files(wiki_dir)

    for f in md_files:
        rel_path = os.path.relpath(f, wiki_dir)
        if is_template_file(rel_path) or is_maintenance_file(rel_path):
            continue

        rel_stem = Path(rel_path).with_suffix('').as_posix()
        basename = os.path.splitext(os.path.basename(f))[0]
        content = open(f, 'r', encoding='utf-8').read()
        fm = extract_frontmatter(content)
        title = get_title_from_frontmatter(fm)

        path_stems.add(rel_stem)
        link_index[rel_stem] = f
        link_index[basename] = f
        if title:
            link_index[title] = f

    return link_index, path_stems


def normalize_slug(slug):
    return slug.replace('\\', '/').strip().rstrip('/')


def build_identity_maps(wiki_dir):
    """构建 identity maps，用于检查 title/slug/alias 冲突"""
    pages = []
    md_files = find_md_files(wiki_dir)

    for f in md_files:
        rel_path = os.path.relpath(f, wiki_dir)
        if is_template_file(rel_path) or is_maintenance_file(rel_path):
            continue

        content = open(f, 'r', encoding='utf-8').read()
        fm = extract_frontmatter(content)
        title = get_title_from_frontmatter(fm) or os.path.splitext(os.path.basename(f))[0]
        slug = get_field_from_frontmatter(fm, 'slug')
        kind = get_field_from_frontmatter(fm, 'kind')
        aliases = get_list_field_from_frontmatter(fm, 'aliases')

        pages.append({
            'path': Path(rel_path).with_suffix('').as_posix(),
            'rel_path': rel_path,
            'title': title,
            'slug': normalize_slug(slug) if slug else None,
            'kind': kind,
            'aliases': aliases,
        })

    return pages


# --- 关系类型关键词 ---
RELATION_TYPES = [
    'calls', 'depends_on', 'defines', 'implements', 'queries',
    'triggers', 'configures', 'transforms', 'part_of', 'related_to'
]

DOMAIN_RELATION_TYPES = [
    'calls', 'depends_on', 'defines', 'implements', 'queries',
    'triggers', 'configures', 'transforms', 'part_of'
]


def extract_fm_relationships(fm_text):
    """从 frontmatter 文本中提取 (关系类型, 链接目标) 三元组片段"""
    relationships = []
    lines = fm_text.split('\n')
    in_rel_key = None
    for line in lines:
        # Check if this line starts a relationship key
        matched_key = False
        for rtype in RELATION_TYPES:
            if re.match(rf'^{rtype}:\s*$', line):
                in_rel_key = rtype
                matched_key = True
                break
            elif re.match(rf'^{rtype}:\s*-', line):
                # Single-line: key: - "[[...]]"
                m = re.search(r'\[\[([^\]]+)\]\]', line)
                if m:
                    relationships.append((rtype, normalize_link_target(m.group(1))))
                in_rel_key = None
                matched_key = True
                break
        if matched_key:
            continue
        # Check if this line is a list item under a relationship key
        if in_rel_key:
            m = re.search(r'\[\[([^\]]+)\]\]', line)
            if m:
                relationships.append((in_rel_key, normalize_link_target(m.group(1))))
            elif re.match(r'^[a-z]', line) and not line.startswith(' '):
                # New top-level key, stop collecting
                in_rel_key = None
    return sorted(relationships)


def extract_body_relationships(body_text):
    """从正文 ## 关系 区块提取 (关系类型, 链接目标) 三元组片段"""
    rel_section_match = re.search(r'^## 关系\s*\n(.*?)(?=^## |\Z)', body_text, re.MULTILINE | re.DOTALL)
    if not rel_section_match:
        return []
    rel_text = rel_section_match.group(1)
    relationships = []
    for target, label in re.findall(r'→ \[\[([^\]|]+)(?:\|([^\]]+))?\]\]', rel_text):
        label_text = label or target
        type_match = re.search(r'@([A-Za-z_][A-Za-z0-9_-]*)\b', label_text)
        if type_match:
            relationships.append((type_match.group(1), normalize_link_target(target)))
    return sorted(relationships)


def get_page_identity(wiki_dir):
    """返回 path/title/basename 到页面元数据的索引"""
    index = {}
    for f in find_md_files(wiki_dir):
        rel_path = os.path.relpath(f, wiki_dir)
        if is_template_file(rel_path) or is_maintenance_file(rel_path):
            continue
        content = open(f, 'r', encoding='utf-8').read()
        fm = extract_frontmatter(content)
        rel_stem = Path(rel_path).with_suffix('').as_posix()
        title = get_title_from_frontmatter(fm) or os.path.splitext(os.path.basename(f))[0]
        page = {
            'path': rel_stem,
            'rel_path': rel_path,
            'title': title,
            'kind': get_field_from_frontmatter(fm, 'kind'),
        }
        index[rel_stem] = page
        index[os.path.splitext(os.path.basename(f))[0]] = page
        index[title] = page
    return index


def is_template_file(rel_path):
    """判断是否为 templates/ 目录下的文件"""
    return rel_path.startswith('templates' + os.sep) or rel_path.startswith('templates/')


def is_maintenance_file(rel_path):
    """判断是否为维护说明文件，不参与知识图谱检查"""
    normalized = rel_path.replace('\\', '/')
    return normalized == 'RESOLVER.md' or normalized.endswith('/README.md')


def check_relationship_consistency(wiki_dir):
    """检查 frontmatter 与正文关系字段是否一致，并做轻量方向护栏"""
    issues = []
    md_files = find_md_files(wiki_dir)
    exclude_basenames = {'index.md', 'overview.md', 'log.md', 'QUESTIONS.md'}
    page_index = get_page_identity(wiki_dir)
    part_of_edges = []

    for f in md_files:
        basename = os.path.basename(f)
        if basename in exclude_basenames:
            continue
        rel_path = os.path.relpath(f, wiki_dir)
        if is_template_file(rel_path) or is_maintenance_file(rel_path):
            continue

        content = open(f, 'r', encoding='utf-8').read()
        fm = extract_frontmatter(content)
        if not fm:
            continue

        body = content[len(fm) + 7:] if fm else content
        kind = get_field_from_frontmatter(fm, 'kind')
        fm_relationships = extract_fm_relationships(fm)
        body_relationships = extract_body_relationships(body)
        if not fm_relationships and not body_relationships:
            continue

        if kind == 'source':
            domain_relationships = [
                rel for rel in fm_relationships + body_relationships
                if rel[0] in DOMAIN_RELATION_TYPES
            ]
            if domain_relationships:
                issues.append(f"  source 领域关系: {rel_path} 使用了领域关系字段，source 页只保留普通关键概念/实体链接")

        if fm_relationships != body_relationships:
            fm_only = sorted(set(fm_relationships) - set(body_relationships))
            body_only = sorted(set(body_relationships) - set(fm_relationships))
            issues.append(
                f"  关系不一致: {rel_path} "
                f"(frontmatter_only={fm_only}, body_only={body_only})"
            )

        subject = Path(rel_path).with_suffix('').as_posix()
        for rtype, target in fm_relationships:
            if rtype == 'part_of':
                target_page = page_index.get(target)
                if target_page:
                    part_of_edges.append((subject, target_page['path'], rel_path))

    edge_set = {(src, dst) for src, dst, _ in part_of_edges}
    for src, dst, rel_path in part_of_edges:
        if src == dst:
            issues.append(f"  part_of 自循环: {rel_path} 指向自己")
        if (dst, src) in edge_set:
            issues.append(f"  part_of 互相包含: {src} <-> {dst}，请人工确认父子方向")

    return issues


def check_broken_links(wiki_dir):
    """检查断链（排除 templates/ 目录下的文件）"""
    issues = []
    md_files = find_md_files(wiki_dir)
    link_index, _ = build_link_index(wiki_dir)

    # 检查每个文件的链接（排除 templates/）
    for f in md_files:
        rel_path = os.path.relpath(f, wiki_dir)
        if is_template_file(rel_path) or is_maintenance_file(rel_path):
            continue
        content = open(f, 'r', encoding='utf-8').read()
        links = extract_wikilinks(content)
        for link in links:
            target = normalize_link_target(link)
            if target not in link_index:
                issues.append(f"  断链: {rel_path} -> [[{link}]] (页面不存在)")

    return issues


def check_index_canonical_links(wiki_dir):
    """检查 index.md 是否全部使用 canonical path wikilink"""
    issues = []
    index_path = os.path.join(wiki_dir, 'index.md')
    if not os.path.isfile(index_path):
        return ["  Canonical link: index.md 不存在"]

    _, path_stems = build_link_index(wiki_dir)
    content = open(index_path, 'r', encoding='utf-8').read()

    for link in extract_wikilinks(content):
        target = normalize_link_target(link)
        if '/' not in target:
            issues.append(f"  非 canonical 链接: index.md -> [[{link}]] (必须写为 [[path/to/page|显示标题]])")
        elif target not in path_stems:
            issues.append(f"  canonical 目标不存在: index.md -> [[{link}]]")

    return issues


def check_identity_consistency(wiki_dir):
    """检查 slug、kind、title、alias 的 identity 一致性"""
    issues = []
    pages = build_identity_maps(wiki_dir)
    title_map = {}
    slug_map = {}
    alias_map = {}

    for page in pages:
        if not page['kind']:
            issues.append(f"  身份缺失: {page['rel_path']} 缺少 kind")
        if not page['slug']:
            issues.append(f"  身份缺失: {page['rel_path']} 缺少 slug")
        elif page['slug'] != page['path']:
            issues.append(f"  slug 不一致: {page['rel_path']} 的 slug='{page['slug']}'，但路径应为 '{page['path']}'")

        title_map.setdefault(page['title'], []).append(page['rel_path'])
        if page['slug']:
            slug_map.setdefault(page['slug'], []).append(page['rel_path'])
        for alias in page['aliases']:
            alias_map.setdefault(alias, []).append(page['rel_path'])

    for slug, paths in slug_map.items():
        if len(paths) > 1:
            issues.append(f"  slug 冲突: {slug} => {', '.join(paths)}")

    for title, paths in title_map.items():
        kinds = set()
        for rel_path in paths:
            for page in pages:
                if page['rel_path'] == rel_path and page['kind']:
                    kinds.add(page['kind'])
        if len(paths) > 1 and len(kinds) == 1:
            issues.append(f"  title 重复: {title} => {', '.join(paths)}")

    for alias, paths in alias_map.items():
        if len(paths) > 1:
            issues.append(f"  alias 冲突: {alias} => {', '.join(paths)}")

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
        all_targets.update(normalize_link_target(link) for link in links)

    # 检查每个页面是否被链接
    for f in md_files:
        basename = os.path.basename(f)
        if basename in exclude_basenames:
            continue
        rel_path = os.path.relpath(f, wiki_dir)
        if is_template_file(rel_path) or is_maintenance_file(rel_path):
            continue
        content = open(f, 'r', encoding='utf-8').read()
        fm = extract_frontmatter(content)
        title = get_title_from_frontmatter(fm) or os.path.splitext(basename)[0]
        rel_stem = Path(rel_path).with_suffix('').as_posix()
        page_keys = {title, os.path.splitext(basename)[0], rel_stem}
        if not page_keys.intersection(all_targets):
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
        if is_template_file(rel_path) or is_maintenance_file(rel_path):
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

    print("\n[1/6] 检查断链...")
    broken = check_broken_links(wiki_dir)
    if broken:
        all_issues.extend(broken)
        print(f"  发现 {len(broken)} 个问题")
        for issue in broken:
            print(issue)
    else:
        print("  通过")

    print("\n[2/6] 检查孤儿页...")
    orphans = check_orphan_pages(wiki_dir)
    if orphans:
        all_issues.extend(orphans)
        print(f"  发现 {len(orphans)} 个问题")
        for issue in orphans:
            print(issue)
    else:
        print("  通过")

    print("\n[3/6] 检查空页面...")
    empty = check_empty_pages(wiki_dir)
    if empty:
        all_issues.extend(empty)
        print(f"  发现 {len(empty)} 个问题")
        for issue in empty:
            print(issue)
    else:
        print("  通过")

    print("\n[4/6] 检查关系一致性...")
    rel_issues = check_relationship_consistency(wiki_dir)
    if rel_issues:
        all_issues.extend(rel_issues)
        print(f"  发现 {len(rel_issues)} 个问题")
        for issue in rel_issues:
            print(issue)
    else:
        print("  通过")

    print("\n[5/6] 检查 index canonical links...")
    canonical_issues = check_index_canonical_links(wiki_dir)
    if canonical_issues:
        all_issues.extend(canonical_issues)
        print(f"  发现 {len(canonical_issues)} 个问题")
        for issue in canonical_issues:
            print(issue)
    else:
        print("  通过")

    print("\n[6/6] 检查 identity 一致性...")
    identity_issues = check_identity_consistency(wiki_dir)
    if identity_issues:
        all_issues.extend(identity_issues)
        print(f"  发现 {len(identity_issues)} 个问题")
        for issue in identity_issues:
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

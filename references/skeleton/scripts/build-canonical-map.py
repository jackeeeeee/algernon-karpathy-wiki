#!/usr/bin/env python3
"""
Build canonical_map.json from wiki frontmatter.

This file is a compiled identity cache for query/lint/compile.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


def find_md_files(directory: Path):
    for root, _, files in os.walk(directory):
        for f in files:
            if f.endswith(".md"):
                yield Path(root) / f


def extract_frontmatter(content: str) -> str:
    m = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    return m.group(1) if m else ""


def get_field(frontmatter: str, field: str):
    m = re.search(rf"^{re.escape(field)}:\s*(.+)$", frontmatter, re.MULTILINE)
    return m.group(1).strip().strip('"').strip("'") if m else None


def get_list_field(frontmatter: str, field: str):
    lines = frontmatter.split("\n")
    values = []
    in_list = False
    for line in lines:
        if re.match(rf"^{re.escape(field)}:\s*$", line):
            in_list = True
            continue
        if in_list:
            if re.match(r"^[A-Za-z_][A-Za-z0-9_-]*:\s*", line):
                break
            m = re.match(r"^\s*-\s*(.+)$", line)
            if m:
                values.append(m.group(1).strip().strip('"').strip("'"))
    return values


def normalize_slug(value: str | None):
    if not value:
        return None
    return value.replace("\\", "/").strip().rstrip("/")


def main():
    wiki_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "wiki"
    wiki_dir = wiki_dir.resolve()
    if not wiki_dir.is_dir():
        print(f"error: wiki dir not found: {wiki_dir}", file=sys.stderr)
        return 1

    pages = []
    for md in find_md_files(wiki_dir):
        rel_path = md.relative_to(wiki_dir).as_posix()
        if "templates/" in rel_path:
            continue
        content = md.read_text(encoding="utf-8")
        fm = extract_frontmatter(content)
        title = get_field(fm, "title") or md.stem
        kind = get_field(fm, "kind")
        slug = normalize_slug(get_field(fm, "slug")) or md.relative_to(wiki_dir).with_suffix("").as_posix()
        aliases = get_list_field(fm, "aliases")
        sources = get_list_field(fm, "sources")
        pages.append(
            {
                "path": rel_path,
                "slug": slug,
                "title": title,
                "kind": kind,
                "aliases": aliases,
                "sources": sources,
            }
        )

    title_map = {}
    slug_map = {}
    alias_map = {}
    source_map = {}
    kind_map = {}

    for page in pages:
        title_map.setdefault(page["title"], []).append(page["path"])
        slug_map.setdefault(page["slug"], []).append(page["path"])
        kind_map.setdefault(page["kind"] or "", []).append(page["path"])
        for alias in page["aliases"]:
            alias_map.setdefault(alias, []).append(page["path"])
        for source in page["sources"]:
            source_map.setdefault(source, []).append(page["path"])

    out = {
        "generatedAt": None,
        "pages": pages,
        "maps": {
            "title": title_map,
            "slug": slug_map,
            "alias": alias_map,
            "source": source_map,
            "kind": kind_map,
        },
    }

    out_path = wiki_dir.parent / "scripts" / "canonical_map.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

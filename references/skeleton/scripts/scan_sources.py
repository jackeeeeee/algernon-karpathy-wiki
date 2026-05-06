#!/usr/bin/env python3
"""
Generate a deterministic compile plan from raw/registry.md.

This script validates the registry schema, scans enabled sources, hashes files,
and compares them with scripts/compile-state.json. It writes
scripts/compile-plan.json and does not modify compile-state.json or wiki pages.
"""

import argparse
import fnmatch
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_COLUMNS = ["logical", "path", "kind", "include", "exclude", "enabled"]
VALID_KINDS = {"directory", "file"}
VALID_ENABLED = {"true", "false"}
LOGICAL_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def posix(path):
    return path.as_posix() if isinstance(path, Path) else str(path).replace("\\", "/")


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def empty_summary():
    return {"ingest": 0, "update": 0, "delete": 0, "skip": 0, "error": 0}


def write_plan(plan_path, plan):
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_plan(root, registry_path, state_path):
    return {
        "status": "ok",
        "generatedAt": now_iso(),
        "root": posix(root),
        "registry": posix(registry_path.relative_to(root)),
        "state": posix(state_path.relative_to(root)),
        "summary": empty_summary(),
        "items": [],
        "deleted": [],
        "errors": [],
    }


def parse_markdown_table(registry_path):
    lines = registry_path.read_text(encoding="utf-8").splitlines()
    table_lines = [line.strip() for line in lines if line.strip().startswith("|") and line.strip().endswith("|")]
    if len(table_lines) < 2:
        return None, [], ["registry: missing markdown table"]

    header = [cell.strip() for cell in table_lines[0].strip("|").split("|")]
    separator = [cell.strip() for cell in table_lines[1].strip("|").split("|")]
    if len(header) != len(separator) or not all(re.fullmatch(r":?-{3,}:?", cell) for cell in separator):
        return None, [], ["registry: second table row must be a markdown separator"]

    rows = []
    errors = []
    for offset, line in enumerate(table_lines[2:], start=3):
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != len(header):
            errors.append(f"registry row {offset}: expected {len(header)} columns, got {len(cells)}")
            continue
        rows.append({header[i]: cells[i] for i in range(len(header))} | {"_row": offset})
    return header, rows, errors


def split_patterns(value):
    return [part.strip() for part in value.split(";") if part.strip()]


def resolve_source_path(root, value):
    raw = Path(value)
    if raw.is_absolute():
        return raw.resolve()
    return (root / raw).resolve()


def validate_registry(root, registry_path):
    errors = []
    if not registry_path.is_file():
        return [], [f"registry: file not found: {registry_path}"]

    header, rows, parse_errors = parse_markdown_table(registry_path)
    errors.extend(parse_errors)
    if header is None:
        return [], errors

    if header != REQUIRED_COLUMNS:
        errors.append(f"registry: header must be exactly: {' | '.join(REQUIRED_COLUMNS)}")

    seen_logical = set()
    entries = []
    for row in rows:
        row_no = row["_row"]
        logical = row.get("logical", "").strip()
        path_value = row.get("path", "").strip()
        kind = row.get("kind", "").strip().lower()
        include = row.get("include", "").strip()
        exclude = row.get("exclude", "").strip()
        enabled = row.get("enabled", "").strip().lower()

        prefix = f"registry row {row_no}"
        if not logical:
            errors.append(f"{prefix}: logical is required")
        elif not LOGICAL_RE.fullmatch(logical):
            errors.append(f"{prefix}: logical must match [A-Za-z0-9._-]+ and contain no slash")
        elif logical in seen_logical:
            errors.append(f"{prefix}: duplicate logical '{logical}'")
        seen_logical.add(logical)

        if not path_value:
            errors.append(f"{prefix}: path is required")
            source_path = None
        else:
            source_path = resolve_source_path(root, path_value)
            if not source_path.exists():
                errors.append(f"{prefix}: path does not exist: {posix(source_path)}")

        if kind not in VALID_KINDS:
            errors.append(f"{prefix}: kind must be 'directory' or 'file'")
        elif source_path and source_path.exists():
            if kind == "directory" and not source_path.is_dir():
                errors.append(f"{prefix}: kind=directory but path is not a directory: {posix(source_path)}")
            if kind == "file" and not source_path.is_file():
                errors.append(f"{prefix}: kind=file but path is not a file: {posix(source_path)}")

        if kind == "directory" and not include:
            errors.append(f"{prefix}: include is required for kind=directory")

        if enabled not in VALID_ENABLED:
            errors.append(f"{prefix}: enabled must be true or false")

        entries.append({
            "logical": logical,
            "path": source_path,
            "kind": kind,
            "include": split_patterns(include),
            "exclude": split_patterns(exclude),
            "enabled": enabled == "true",
            "row": row_no,
        })

    return entries, errors


def load_state(state_path):
    if not state_path.is_file():
        return {"lastCompile": None, "files": {}}
    return json.loads(state_path.read_text(encoding="utf-8"))


def md5_8(path):
    return hashlib.md5(path.read_bytes()).hexdigest()[:8]


def matches_any(rel_path, patterns):
    if not patterns:
        return False
    rel_path = rel_path.replace("\\", "/")
    for pattern in patterns:
        if fnmatch.fnmatch(rel_path, pattern):
            return True
        if pattern.startswith("**/") and fnmatch.fnmatch(rel_path, pattern[3:]):
            return True
    return False


def discover_files(entry):
    if not entry["enabled"]:
        return []

    source_path = entry["path"]
    if entry["kind"] == "file":
        return [(source_path, source_path.name)]

    files = []
    for path in sorted(p for p in source_path.rglob("*") if p.is_file()):
        rel = path.relative_to(source_path).as_posix()
        if entry["include"] and not matches_any(rel, entry["include"]):
            continue
        if entry["exclude"] and matches_any(rel, entry["exclude"]):
            continue
        files.append((path, rel))
    return files


def find_state_entry(files_state, logical_path):
    if logical_path in files_state:
        return logical_path, files_state[logical_path]
    parts = logical_path.split("/", 1)
    if len(parts) == 2 and parts[1] in files_state:
        return parts[1], files_state[parts[1]]
    return None, None


def build_plan(root):
    registry_path = root / "raw" / "registry.md"
    state_path = root / "scripts" / "compile-state.json"
    plan_path = root / "scripts" / "compile-plan.json"
    plan = make_plan(root, registry_path, state_path)

    entries, errors = validate_registry(root, registry_path)
    if errors:
        plan["status"] = "error"
        plan["errors"] = errors
        plan["summary"]["error"] = len(errors)
        write_plan(plan_path, plan)
        return plan, 1

    state = load_state(state_path)
    files_state = state.get("files", {})
    seen_state_keys = set()
    seen_logical_paths = set()

    for entry in entries:
        for abs_path, rel_path in discover_files(entry):
            logical_path = f"{entry['logical']}/{rel_path}".replace("\\", "/")
            file_hash = md5_8(abs_path)
            state_key, state_entry = find_state_entry(files_state, logical_path)
            if state_key:
                seen_state_keys.add(state_key)
            seen_logical_paths.add(logical_path)

            previous_hash = state_entry.get("hash") if state_entry else None
            if state_entry is None:
                action = "ingest"
            elif previous_hash == file_hash:
                action = "skip"
            else:
                action = "update"

            plan["summary"][action] += 1
            plan["items"].append({
                "action": action,
                "logical": entry["logical"],
                "logicalPath": logical_path,
                "stateKey": state_key,
                "absolutePath": posix(abs_path),
                "hash": file_hash,
                "previousHash": previous_hash,
                "wikiPages": state_entry.get("wikiPages", []) if state_entry else [],
            })

    for state_key, state_entry in sorted(files_state.items()):
        if state_key in seen_state_keys:
            continue
        # Legacy keys may be represented by a scanned logicalPath suffix.
        if any(path.endswith("/" + state_key) for path in seen_logical_paths):
            continue
        plan["summary"]["delete"] += 1
        plan["deleted"].append({
            "action": "delete",
            "stateKey": state_key,
            "previousHash": state_entry.get("hash"),
            "wikiPages": state_entry.get("wikiPages", []),
        })

    write_plan(plan_path, plan)
    return plan, 0


def print_summary(plan):
    summary = plan["summary"]
    print(f"compile plan: {plan['status']}")
    print(
        "summary: "
        f"ingest={summary['ingest']} update={summary['update']} "
        f"delete={summary['delete']} skip={summary['skip']} error={summary['error']}"
    )
    if plan["errors"]:
        print("errors:")
        for error in plan["errors"]:
            print(f"- {error}")


def main():
    parser = argparse.ArgumentParser(description="Generate scripts/compile-plan.json from raw/registry.md")
    parser.add_argument("--root", help="Knowledge base root. Defaults to scripts/..")
    args = parser.parse_args()

    if args.root:
        root = Path(args.root).resolve()
    else:
        root = Path(__file__).resolve().parents[1]

    plan, exit_code = build_plan(root)
    print_summary(plan)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())

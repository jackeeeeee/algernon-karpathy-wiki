# algernon-karpathy-wiki

> A skill for Claude Code that turns any directory into a **self-maintaining personal knowledge base** — inspired by Andrej Karpathy's [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) pattern.

[中文版](README_zh.md)

## What is this?

Most people's experience with LLMs and documents looks like RAG: you upload files, the LLM retrieves chunks, generates an answer — then forgets everything. **Nothing is built up.**

This skill implements Karpathy's alternative: instead of retrieving from raw documents at query time, the LLM **incrementally builds and maintains a persistent, interlinked wiki** — a structured collection of markdown files that sits between you and the raw sources. When you add new material, the LLM reads it, extracts concepts and entities, updates relevant pages, and keeps everything cross-referenced and current.

**The wiki is a persistent, compounding artifact.** Knowledge gets richer with every source you add.

## Architecture

```
├── raw/              # Immutable source documents (human-owned, LLM read-only)
│   ├── registry.md   # External directory registry
│   ├── articles/     # Markdown articles
│   ├── clippings/    # Obsidian Web Clipper captures
│   ├── images/       # Screenshots and images
│   ├── pdfs/         # PDFs and metadata
│   ├── notes/        # Quick notes
│   └── personal/     # Self-written content
├── wiki/             # Compiled knowledge layer (LLM-owned, human read-only)
│   ├── index.md      # Global index (query entry point)
│   ├── log.md        # Append-only operation log
│   ├── overview.md   # High-level overview + Health Dashboard
│   ├── QUESTIONS.md  # Open question queue
│   ├── sources/      # Source summary pages
│   ├── concepts/     # Ideas, patterns, technologies
│   ├── entities/     # People, tools, orgs, projects
│   ├── synthesis/    # Cross-source comparative analysis
│   └── templates/    # Page templates (concept, entity, synthesis)
├── outputs/          # Query results and lint reports
├── scripts/
│   ├── lint.py       # Wiki health check script
│   ├── compile-state.json  # Incremental compile state (hash-based)
│   └── qmd-reindex.sh      # qmd search index rebuild
├── CLAUDE.md         # LLM behavior contract
└── README.md         # This file
```

### Core Principles

1. **`raw/` is immutable** — LLM reads, never modifies
2. **`wiki/` is LLM-owned** — creates, updates, maintains all pages
3. **Compile over retrieve** — knowledge is compiled once and kept current, not re-derived per query
4. **Bidirectional links** — all wiki pages use `[[wikilinks]]` for interconnection
5. **Output archival** — valuable answers are filed back into the knowledge base

## Features

### Seven Capabilities

| # | Capability | Description |
|---|------------|-------------|
| 1 | **Init** | Bootstrap a fresh knowledge base from skeleton — `cp -r` + date placeholder replacement + `git init` |
| 2 | **Ingest** | Import a single source: read it, create summary + concept/entity pages, write typed relationships |
| 3 | **Compile** | Batch incremental compile — MD5 hash-based change detection, processes only changed files |
| 4 | **Lint** | Health checks — broken links, orphans, empty pages (Python script) + stale claims, contradictions, low-confidence, knowledge gaps (LLM) |
| 5 | **Query** | Answer questions via `wiki/index.md` → relevant pages, archive valuable answers to `outputs/` |
| 6 | **Relationships** | Auto-write typed relationships in YAML frontmatter + `@type` links in body — supports Obsidian Graph View |
| 7 | **Git** | Auto-commit after every wiki operation — local-only, full version history |

### Key Design Decisions

- **Incremental compilation**: hash-based, not full rebuild. Only changed sources are re-processed.
- **Typed knowledge graph**: frontmatter `part_of:`, `depends_on:`, `calls:`, etc. + body `@type` syntax.
- **Dual-source relationship tracking**: YAML frontmatter (machine-readable) + `## 关系` section (human-readable), lint-checked for consistency.
- **Relationship vocabulary**: `calls`, `depends_on`, `defines`, `implements`, `queries`, `triggers`, `configures`, `transforms`, `part_of`, `related_to` — extensible by the agent.
- **Lint分工**: Script handles deterministic checks (regex-based). LLM handles semantic checks (context-dependent).
- **qmd search layer**: Local BM25 + vector + LLM reranking search engine for large wikis (200+ pages).

## Installation

### Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) — the LLM agent that runs everything
- [Obsidian](https://obsidian.md/) — the frontend for browsing and visualizing the wiki (optional but recommended)
- [qmd](https://github.com/tobi/qmd) — local markdown search engine (optional, for large wikis)

### Setup

1. **Clone this repository**

```bash
git clone https://github.com/<your-username>/algernon-karpathy-wiki.git
```

2. **Install the skill**

Copy the skill to your Claude Code skills directory:

```bash
# macOS / Linux
mkdir -p ~/.claude/skills/llm-wiki
cp -r algernon-karpathy-wiki/* ~/.claude/skills/llm-wiki/

# Windows (PowerShell)
Copy-Item -Path algernon-karpathy-wiki\* -Destination $env:USERPROFILE\.claude\skills\llm-wiki\ -Recurse -Force
```

3. **Verify installation**

Start Claude Code and ask it to initialize a knowledge base:

```
claude
> 用 llm-wiki skill 初始化一个知识库
```

## Usage

### Initialize a Knowledge Base

```
Initialize a knowledge base in /path/to/my-wiki
```

The skill will:
1. Copy the skeleton structure to your target directory
2. Replace `{{date}}` placeholders with today's date
3. Initialize a local git repository

### Import Sources

```
Ingest the files in raw/articles/
```

A single source typically creates 5-15 wiki pages: source summary, concept pages, entity pages, and typed relationships.

### Batch Compile

```
Compile the wiki
```

The LLM scans all registered source directories, computes MD5 hashes, and incrementally processes only changed files.

### Query the Wiki

```
What is the relationship between DGS and NMS?
```

The LLM reads `wiki/index.md`, finds relevant pages, and synthesizes an answer with citations.

### Health Check

```
Lint the wiki
```

Runs `scripts/lint.py` (broken links, orphans, empty pages, relationship consistency) + LLM semantic checks (stale claims, contradictions, low-confidence assertions, knowledge gaps).

## Relationship Vocabulary

The skill auto-writes typed relationships between wiki pages:

| Type | Meaning | Example |
|------|---------|---------|
| `calls` | A calls B's interface/API | DGS sync calls NMS API |
| `depends_on` | A depends on B | Alarm aggregation depends_on node status |
| `defines` | A defines B (class, function, config) | Strategy module defines strategy interface |
| `implements` | A implements B pattern/protocol | Strategy pattern implements Strategy design pattern |
| `queries` | A queries B's database/table | Inspection service queries device status table |
| `triggers` | A triggers B (event/alert/task) | Node offline triggers DGS alert |
| `configures` | A configures B | Nacos config configures refresh frequency |
| `transforms` | A converts data to B format | Parser transforms EIAP data to unified format |
| `part_of` | A is a submodule of B | Alert aggregation part_of DGS monitoring |
| `related_to` | Other associations | Knowledge management related_to Karpathy LLM Wiki |

## Obsidian Integration

- Open the knowledge base directory as an Obsidian vault
- Use **Graph View** to visualize the knowledge graph with typed edges
- Install **Wikilink Types** plugin for automatic frontmatter ↔ body sync
- Install **Dataview** plugin for dynamic queries over YAML frontmatter
- Use **Obsidian Web Clipper** for quick article clipping to `raw/articles/`

## Credits

- **Andrej Karpathy** — [LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f), the foundational idea
- **Vannevar Bush** — Memex (1945), the spiritual ancestor of this concept
- **Obsidian** — the markdown wiki frontend
- **qmd** — local search engine for large wikis

## License

MIT

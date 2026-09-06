"""Discover the two non-code bundles a context-aware reviewer needs.

  task-context.md  — what the project SAID it would build (acceptance criteria,
                     specs, PRDs, tickets). Without this the requirements-gap
                     agent has nothing to measure against.
  standards.md     — how the project said it would be built (engineering
                     principles, lint/type config, public claims).

Both are discovered by filename convention, because that is what actually exists
in real repos. Anything found can be overridden with --task-file / --standards-file.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path

# Ordered by how directly each names acceptance criteria.
TASK_PATTERNS = [
    "specification.json", "specification.md", "spec.md", "SPEC.md",
    "definition_of_done.md", "DEFINITION_OF_DONE.md", "acceptance*.md",
    "requirements.md", "REQUIREMENTS.md", "requirements*.txt.md",
    "PRD.md", "prd.md", "product-requirements*.md",
    "progress_tracking.json", "tasks/todo.md", "TODO.md",
    "docs/spec*.md", "docs/requirements*.md", "docs/acceptance*.md",
    "docs/prd*.md", "docs/rfc*.md", "doc/spec*.md",
    ".github/ISSUE_TEMPLATE/*.md",
]

STANDARDS_PATTERNS = [
    "CLAUDE.md", "AGENTS.md", ".cursorrules", ".windsurfrules",
    "CONTRIBUTING.md", "CONVENTIONS.md", "STYLEGUIDE.md", "style-guide.md",
    "ARCHITECTURE.md", "docs/architecture*.md", "docs/conventions*.md",
    "docs/standards*.md", "adr/*.md", "docs/adr/*.md",
    "README.md",
    "eslint.config.js", "eslint.config.mjs", ".eslintrc.json", ".eslintrc.js",
    "tsconfig.json", "pyproject.toml", "ruff.toml", ".ruff.toml",
    "setup.cfg", ".editorconfig", "rustfmt.toml", ".golangci.yml",
    ".golangci.yaml", "Makefile", "justfile",
]

# Large files are truncated rather than dropped: a 400KB lockfile-ish doc would
# swamp the bundle, but its opening is often still the useful part.
MAX_FILE_CHARS = 60_000
MAX_BUNDLE_CHARS = 220_000

FENCE = {
    ".json": "json", ".md": "markdown", ".js": "javascript", ".mjs": "javascript",
    ".ts": "typescript", ".toml": "toml", ".yml": "yaml", ".yaml": "yaml",
    ".cfg": "ini", ".txt": "text",
}


def _resolve(root: Path, patterns: list[str], limit: int) -> list[Path]:
    found: list[Path] = []
    seen: set[Path] = set()
    for pat in patterns:
        if any(ch in pat for ch in "*?["):
            parent = root / Path(pat).parent
            if not parent.is_dir():
                continue
            cands = sorted(
                p for p in parent.iterdir()
                if p.is_file() and fnmatch.fnmatch(p.name, Path(pat).name)
            )
        else:
            p = root / pat
            cands = [p] if p.is_file() else []
        for c in cands:
            rp = c.resolve()
            if rp in seen:
                continue
            seen.add(rp)
            found.append(c)
            if len(found) >= limit:
                return found
    return found


def _render(root: Path, paths: list[Path], title: str, preamble: str) -> tuple[str, list[str]]:
    parts = [f"# {title}", "", preamble, ""]
    used: list[str] = []
    budget = MAX_BUNDLE_CHARS
    for p in paths:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if not text.strip():
            continue
        truncated = False
        if len(text) > MAX_FILE_CHARS:
            text = text[:MAX_FILE_CHARS]
            truncated = True
        if len(text) > budget:
            text = text[:max(budget, 0)]
            truncated = True
        budget -= len(text)
        rel = p.resolve().relative_to(root.resolve()).as_posix()
        used.append(rel)
        parts += [f"## {rel}" + ("  _(truncated)_" if truncated else ""),
                  f"```{FENCE.get(p.suffix, '')}", text, "```", ""]
        if budget <= 0:
            parts.append("_Bundle size limit reached; remaining files omitted._")
            break
    return "\n".join(parts), used


def build_task_context(root: Path, extra: list[Path] | None = None) -> tuple[str, list[str]]:
    paths = list(extra or []) or _resolve(root, TASK_PATTERNS, limit=6)
    if not paths:
        return (
            "# Task-level context\n\n"
            "_No specification, acceptance-criteria or requirements document was found in this "
            "repository._\n\n"
            "The requirements-gap agent has nothing to measure the implementation against and "
            "should report that plainly rather than inventing criteria. This absence is itself a "
            "finding about the project.\n",
            [],
        )
    return _render(
        root, paths, "Task-level context — requirements the code must satisfy",
        "What the project said it would build. These are the acceptance criteria a reviewer\n"
        "measures the implementation against; they are what make *requirements gap* findings\n"
        "possible at all.",
    )


def build_standards(root: Path, extra: list[Path] | None = None) -> tuple[str, list[str]]:
    paths = list(extra or []) or _resolve(root, STANDARDS_PATTERNS, limit=10)
    if not paths:
        return (
            "# Repo rules & engineering standards\n\n"
            "_No standards, conventions or configuration documents were found._\n\n"
            "Findings cannot cite a written project rule. Judge against conventions the codebase\n"
            "itself establishes instead, and say so.\n",
            [],
        )
    return _render(
        root, paths, "Repo rules & engineering standards",
        "How the project said it would be built: written principles, the lint and type\n"
        "configuration actually in force, and the public claims the code must live up to.",
    )

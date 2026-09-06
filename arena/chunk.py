"""Structure-aware chunking of a repository.

Three strategies, chosen per file extension:

  .ts .tsx .js .jsx .mjs .cjs  -> real TypeScript compiler AST (via chunk_ts.mjs)
  .py                          -> Python's own `ast`
  everything else              -> generic structural heuristic (documented below)

The point of chunking on structure rather than line windows is that a retrieved
chunk should be a thing a reviewer can reason about — a whole function, not the
back half of one.
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

TS_EXTS = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}
PY_EXTS = {".py", ".pyi"}
MIN_CHARS = 20

# Languages the generic chunker handles acceptably. Anything not listed still
# works, but the heuristic may be coarse — say so in the run report.
GENERIC_EXTS = {
    ".go", ".rs", ".java", ".kt", ".kts", ".swift", ".c", ".h", ".cc", ".cpp",
    ".hpp", ".cs", ".rb", ".php", ".scala", ".sh", ".bash", ".lua", ".dart",
    ".ex", ".exs", ".sql", ".vue", ".svelte",
}

DEFAULT_EXTS = TS_EXTS | PY_EXTS | GENERIC_EXTS

SKIP_DIRS = {
    ".git", "node_modules", "dist", "build", "out", "target", "vendor",
    "__pycache__", ".venv", "venv", ".mypy_cache", ".pytest_cache", ".next",
    "coverage", ".tox", ".idea", ".vscode", "site-packages",
}

# A top-level definition in a curly-brace or indentation language. Deliberately
# permissive: it is better to over-capture a definition than to split one.
GENERIC_DEF = re.compile(
    r"^[ \t]{0,4}"
    r"(?:(?:pub|public|private|protected|internal|static|final|abstract|export|"
    r"default|async|const|inline|virtual|override|open|suspend|unsafe|extern)\s*"
    r"(?:\([^)]*\)\s*)?\s+)*"
    r"(?P<kind>func|fn|def|function|class|struct|interface|impl|trait|enum|type|"
    r"module|object|record|protocol|extension|sub|method)\s+"
    # Go methods carry a receiver between the keyword and the name:
    #   func (s *Server) Start() error
    r"(?:\([^)]*\)\s*)?"
    r"(?P<name>[A-Za-z_][\w.<>:]*)",
)


@dataclass
class Chunk:
    type: str
    name: str
    file: str
    start_line: int
    end_line: int
    content: str


def iter_source_files(root: Path, targets: list[str], exts: set[str]) -> list[Path]:
    out: list[Path] = []
    for t in targets:
        base = (root / t).resolve()
        if base.is_file():
            if base.suffix in exts:
                out.append(base)
            continue
        if not base.is_dir():
            print(f"  warning: target not found, skipping: {t}", file=sys.stderr)
            continue
        for p in base.rglob("*"):
            if not p.is_file() or p.suffix not in exts:
                continue
            if any(part in SKIP_DIRS for part in p.parts):
                continue
            out.append(p)
    return sorted(set(out))


def chunk_typescript(files: list[Path], root: Path) -> list[Chunk]:
    """Delegate to the TypeScript compiler. Returns [] if node/typescript missing."""
    if not files:
        return []
    script = Path(__file__).parent / "chunk_ts.mjs"
    try:
        proc = subprocess.run(
            ["node", str(script)],
            input=json.dumps([str(f) for f in files]),
            capture_output=True,
            # Explicit UTF-8: the default is the locale codec, which is cp1252 on
            # Windows and blows up on the first non-ASCII byte in any source file.
            encoding="utf-8",
            errors="replace",
            timeout=180,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        print(f"  note: node unavailable ({type(exc).__name__}) — TS/JS falls back to the "
              f"generic chunker", file=sys.stderr)
        return chunk_generic(files, root)
    if proc.returncode != 0:
        why = "typescript not installed" if proc.returncode == 3 else proc.stderr.strip()[:200]
        print(f"  note: TS AST chunker unavailable ({why}) — using generic chunker",
              file=sys.stderr)
        return chunk_generic(files, root)
    try:
        raw = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError:
        print("  note: TS AST chunker produced unreadable output — using generic chunker",
              file=sys.stderr)
        return chunk_generic(files, root)
    if not raw:
        # Silence here would masquerade as "this code has no functions", and the
        # whole-file backfill downstream would hide it. Be loud and fall back.
        print(f"  note: TS AST chunker returned nothing for {len(files)} file(s) — "
              f"using generic chunker", file=sys.stderr)
        return chunk_generic(files, root)
    return [
        Chunk(c["type"], c["name"], rel(Path(c["file"]), root),
              c["start_line"], c["end_line"], c["content"])
        for c in raw
    ]


def chunk_python(files: list[Path], root: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    for f in files:
        try:
            src = f.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(src)
        except (SyntaxError, OSError):
            continue
        lines = src.split("\n")

        def emit(node: ast.AST, kind: str, name: str) -> None:
            start = getattr(node, "lineno", None)
            end = getattr(node, "end_lineno", None)
            if start is None or end is None:
                return
            # Include decorators, which carry meaning a reviewer needs.
            decs = getattr(node, "decorator_list", []) or []
            if decs:
                start = min(start, min(d.lineno for d in decs))
            content = "\n".join(lines[start - 1:end])
            if len(content.strip()) < MIN_CHARS:
                return
            chunks.append(Chunk(kind, name, rel(f, root), start, end, content))

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                emit(node, "class", node.name)
                for sub in node.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        emit(sub, "method", f"{node.name}.{sub.name}")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                emit(node, "function", node.name)
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                tgt = node.targets[0] if isinstance(node, ast.Assign) else node.target
                if isinstance(tgt, ast.Name):
                    emit(node, "const", tgt.id)
    return chunks


def chunk_generic(files: list[Path], root: Path) -> list[Chunk]:
    """Heuristic chunker for languages without a parser here.

    Finds top-level definition keywords and extends each chunk to the next
    definition at the same or shallower indentation. Coarser than an AST, but it
    keeps whole definitions together, which is what retrieval needs.
    """
    chunks: list[Chunk] = []
    for f in files:
        try:
            src = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lines = src.split("\n")
        starts: list[tuple[int, str, str, int]] = []
        for i, line in enumerate(lines):
            m = GENERIC_DEF.match(line)
            if m:
                indent = len(line) - len(line.lstrip())
                starts.append((i, m.group("kind"), m.group("name"), indent))
        for idx, (i, kind, name, indent) in enumerate(starts):
            end = len(lines)
            for j, _, _, ind2 in starts[idx + 1:]:
                if ind2 <= indent:
                    end = j
                    break
            content = "\n".join(lines[i:end]).rstrip()
            if len(content.strip()) < MIN_CHARS:
                continue
            chunks.append(Chunk(kind, name, rel(f, root), i + 1, end, content))
    return chunks


def rel(p: Path, root: Path) -> str:
    try:
        return p.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return p.as_posix()


def chunk_repository(root: Path, targets: list[str], exts: set[str]) -> list[Chunk]:
    files = iter_source_files(root, targets, exts)
    ts = [f for f in files if f.suffix in TS_EXTS]
    py = [f for f in files if f.suffix in PY_EXTS]
    other = [f for f in files if f.suffix not in TS_EXTS | PY_EXTS]
    chunks = chunk_typescript(ts, root) + chunk_python(py, root) + chunk_generic(other, root)
    # A file with no recognisable definitions still deserves representation.
    covered = {c.file for c in chunks}
    for f in files:
        r = rel(f, root)
        if r in covered:
            continue
        try:
            src = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if len(src.strip()) < MIN_CHARS:
            continue
        chunks.append(Chunk("file", Path(r).name, r, 1, len(src.split("\n")), src))
    return chunks


def summarise(chunks: list[Chunk], files_count: int) -> str:
    dist: dict[str, int] = {}
    for c in chunks:
        dist[c.type] = dist.get(c.type, 0) + 1
    total = sum(len(c.content) for c in chunks)
    body = "\n".join(f"    {k:<10} {v}" for k, v in sorted(dist.items(), key=lambda kv: -kv[1]))
    return (f"  files indexed : {files_count}\n"
            f"  chunks created: {len(chunks)}\n"
            f"  total chars   : {total:,}\n{body}")


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Chunk a repository for review retrieval.")
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--target", nargs="+", required=True)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--ext", nargs="*", default=None,
                    help="Extensions to include, e.g. .ts .py (default: a broad built-in set)")
    a = ap.parse_args()
    exts = set(a.ext) if a.ext else DEFAULT_EXTS
    exts = {e if e.startswith(".") else f".{e}" for e in exts}
    files = iter_source_files(a.repo, a.target, exts)
    chunks = chunk_repository(a.repo, a.target, exts)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps([asdict(c) for c in chunks], indent=2), encoding="utf-8")
    print(summarise(chunks, len(files)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

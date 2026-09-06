"""Mechanical evidence check: does every `file:line` citation point inside a real file?

Cheap, objective, and it separates two very different failure modes:

  out-of-range  the reviewer cited a line past the end of the file
  unknown-file  the reviewer cited a path that does not exist

Neither proves a finding is wrong — in practice the quoted *code* is often real
and only the pointer drifted — but both cost a developer time, and the rate is
one of the few things you can compare between reviewers without a ground-truth
issue set.

Run it over any directory of review outputs, from any tool.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

CITE = re.compile(r"(?<![\w/.-])([\w./-]+\.[A-Za-z][\w]{0,7}):(\d+)(?:\s*[-–]\s*(\d+))?")

SKIP_DIRS = {
    ".git", "node_modules", "dist", "build", "out", "target", "vendor",
    "__pycache__", ".venv", "venv", ".next", "coverage",
}


def index_repo(root: Path) -> dict[str, int]:
    """Map repo-relative path -> line count. See resolve_cited for lookup rules."""
    lens: dict[str, int] = {}
    for p in root.rglob("*"):
        if not p.is_file() or any(part in SKIP_DIRS for part in p.parts):
            continue
        try:
            n = len(p.read_text(encoding="utf-8", errors="replace").split("\n"))
        except (OSError, ValueError):
            continue
        lens[p.resolve().relative_to(root.resolve()).as_posix()] = n
    return lens


def resolve_cited(cited: str, lens: dict[str, int]) -> int | None:
    """Resolve a cited path to a line count, or None if it cannot be resolved.

    Exact repo-relative match first, then a unique *path suffix* match — so
    `sanitize.ts` finds `src/pipeline/sanitize.ts`, while `render.ts` (two
    candidates) and `lib/index.js` (a dependency path outside the repo) resolve
    to nothing rather than being scored against the wrong file.
    """
    cited = cited.lstrip("./")
    if cited in lens:
        return lens[cited]
    matches = [p for p in lens if p.endswith("/" + cited)]
    return lens[matches[0]] if len(matches) == 1 else None


def check_file(path: Path, lens: dict[str, int]) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    seen: set[tuple[str, int, int]] = set()
    ok, bad, unknown = 0, [], []
    for m in CITE.finditer(text):
        f, lo = m.group(1), int(m.group(2))
        hi = int(m.group(3)) if m.group(3) else lo
        key = (f, lo, hi)
        if key in seen:
            continue
        seen.add(key)
        n = resolve_cited(f, lens)
        if n is None:
            # Either no such file, or a basename that matches several files —
            # in both cases the citation cannot be scored, so do not score it.
            unknown.append(f"{f}:{lo}")
            continue
        if 1 <= lo <= n and hi <= n:
            ok += 1
        else:
            bad.append(f"{f}:{lo}-{hi} (file has {n} lines)")
    total = ok + len(bad)
    return {"ok": ok, "total": total, "bad": bad, "unknown": unknown,
            "pct": (ok / total * 100) if total else None}


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Check file:line citation accuracy in review outputs.")
    ap.add_argument("--repo", required=True, type=Path, help="Repo the review was about")
    ap.add_argument("paths", nargs="+", type=Path, help="Review output files or directories")
    a = ap.parse_args()

    lens = index_repo(a.repo)
    files: list[Path] = []
    for p in a.paths:
        files.extend(sorted(p.rglob("*.md")) if p.is_dir() else [p])

    grand_ok = grand_total = 0
    for f in files:
        if not f.is_file():
            continue
        r = check_file(f, lens)
        if r["total"] == 0 and not r["unknown"]:
            continue
        pct = f"{r['pct']:.0f}%" if r["pct"] is not None else "n/a"
        label = f.name
        print(f"{label:<38} {r['ok']:3d}/{r['total']:3d} in range ({pct})"
              + (f"  [{len(r['unknown'])} unknown file]" if r["unknown"] else ""))
        for b in r["bad"]:
            print(f"      OUT OF RANGE: {b}")
        for u in r["unknown"][:5]:
            print(f"      UNKNOWN FILE: {u}")
        grand_ok += r["ok"]
        grand_total += r["total"]

    if grand_total:
        print(f"\n{'TOTAL':<38} {grand_ok:3d}/{grand_total:3d} in range "
              f"({grand_ok / grand_total * 100:.0f}%)")
    else:
        print("No file:line citations found.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

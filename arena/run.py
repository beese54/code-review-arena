"""One command: chunk a repo, discover its context, retrieve per-agent bundles,
and write ready-to-paste prompts for the context-aware arm.

    python -m arena.run --repo /path/to/repo --target src server

What this does NOT do is call an LLM. The agent step is deliberately left to you,
because the interesting comparison is between *your* tools, and because a harness
that quietly burns tokens is a bad neighbour. It writes prompts; you run them in
whatever agent runner you use, then point --arm-a/--arm-b at the outputs to
compare.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

from .chunk import DEFAULT_EXTS, chunk_repository, iter_source_files, summarise
from .context import build_standards, build_task_context
from .retrieve import load_agents, retrieve


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(
        prog="arena.run",
        description="Prepare a context-aware code review arm for any repository.")
    ap.add_argument("--repo", required=True, type=Path, help="Repository root")
    ap.add_argument("--target", nargs="+", default=["."],
                    help="Paths within the repo to review (default: whole repo)")
    ap.add_argument("--out", type=Path, default=None,
                    help="Output directory (default: <repo>/review-arena-run)")
    ap.add_argument("--agents-dir", type=Path, default=None,
                    help="Agent definitions (default: the bundled agents/)")
    ap.add_argument("--ext", nargs="*", default=None, help="Extensions to include")
    ap.add_argument("--top-k", type=int, default=30,
                    help="Chunks per agent bundle (default 30, ~15%% of a mid-size index)")
    ap.add_argument("--per-query", type=int, default=12)
    ap.add_argument("--embedder", choices=["local", "openai"], default="local")
    ap.add_argument("--only", nargs="*", default=None, help="Run only these agents by name")
    ap.add_argument("--task-file", nargs="*", type=Path, default=None,
                    help="Override task-context discovery")
    ap.add_argument("--standards-file", nargs="*", type=Path, default=None,
                    help="Override standards discovery")
    ap.add_argument("--describe", default=None,
                    help="One-paragraph description of the system, injected into every prompt")
    a = ap.parse_args()

    repo = a.repo.resolve()
    if not repo.is_dir():
        print(f"error: --repo is not a directory: {repo}", file=sys.stderr)
        return 2
    out = (a.out or repo / "review-arena-run").resolve()
    agents_dir = (a.agents_dir or Path(__file__).parent.parent / "agents").resolve()
    bundles = out / "bundles"
    prompts = out / "prompts"
    for d in (out, bundles, prompts, out / "arm-a", out / "arm-b"):
        d.mkdir(parents=True, exist_ok=True)

    exts = {e if e.startswith(".") else f".{e}" for e in (a.ext or DEFAULT_EXTS)}

    print(f"repo   : {repo}")
    print(f"target : {' '.join(a.target)}")
    print(f"output : {out}\n")

    # 1. Chunk -------------------------------------------------------------
    print("[1/4] chunking")
    files = iter_source_files(repo, a.target, exts)
    if not files:
        print("error: no source files matched. Check --target and --ext.", file=sys.stderr)
        return 2
    chunks = chunk_repository(repo, a.target, exts)
    if not chunks:
        print("error: no chunks produced.", file=sys.stderr)
        return 2
    chunk_dicts = [asdict(c) for c in chunks]
    (out / "chunks.json").write_text(json.dumps(chunk_dicts, indent=2), encoding="utf-8")
    print(summarise(chunks, len(files)))

    total_lines = 0
    for f in files:
        try:
            total_lines += len(f.read_text(encoding="utf-8", errors="replace").split("\n"))
        except OSError:
            pass

    # 2. Context -----------------------------------------------------------
    print("\n[2/4] discovering project context")
    task_md, task_used = build_task_context(repo, a.task_file)
    std_md, std_used = build_standards(repo, a.standards_file)
    (bundles / "task-context.md").write_text(task_md, encoding="utf-8")
    (bundles / "standards.md").write_text(std_md, encoding="utf-8")
    print(f"  task context : {', '.join(task_used) if task_used else 'NONE FOUND'}")
    print(f"  standards    : {', '.join(std_used) if std_used else 'NONE FOUND'}")
    if not task_used:
        print("  note: with no acceptance criteria, the requirements-gap agent has nothing to\n"
              "        measure against. That absence is itself worth reporting.")

    # 3. Retrieve ----------------------------------------------------------
    print("\n[3/4] embedding and selective retrieval")
    agents = load_agents(agents_dir, a.only)
    if not agents:
        print(f"error: no agent definitions in {agents_dir}", file=sys.stderr)
        return 2
    report = retrieve(chunk_dicts, agents, bundles, a.top_k, a.per_query, a.embedder)
    report["repo"] = str(repo)
    report["target"] = a.target
    report["files"] = len(files)
    report["lines"] = total_lines
    report["task_context_files"] = task_used
    report["standards_files"] = std_used
    (out / "retrieval-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    # 4. Prompts -----------------------------------------------------------
    print("\n[4/4] writing prompts")
    description = a.describe or (
        f"A codebase at `{repo.name}`. {len(files)} source files, ~{total_lines:,} lines, "
        f"under {', '.join(a.target)}. No further description was supplied — judge the code by "
        f"the standards and requirements bundles, and by the conventions it establishes itself."
    )
    for ag in agents:
        body = (ag.body
                .replace("{BUNDLE_DIR}", bundles.as_posix())
                .replace("{OUT_DIR}", (out / "arm-a").as_posix())
                .replace("{PROJECT_DESCRIPTION}", description))
        (prompts / f"{ag.name}.md").write_text(body, encoding="utf-8")
        print(f"  prompts/{ag.name}.md")

    write_run_notes(out, repo, a.target, agents, report, total_lines, len(files))
    print(f"\nDone. Next steps are in {out / 'RUN.md'}")
    return 0


def write_run_notes(out: Path, repo: Path, target: list[str], agents, report: dict,
                    lines: int, files: int) -> None:
    names = [ag.name for ag in agents]
    rows = "\n".join(
        f"| {n} | {report['agents'][n]['chunks']} | {report['agents'][n]['chars']:,} | "
        f"{report['agents'][n]['reduction_pct']}% |" for n in names
    )
    md = f"""# Run — next steps

**Repo:** `{repo}`
**Target:** `{' '.join(target)}` — {files} files, ~{lines:,} lines
**Index:** {report['index']['chunks']} chunks, {report['index']['chars']:,} chars
**Embedder:** {report['index']['embedder']}

| Agent | Chunks | Chars | Reduction vs full context |
|---|---:|---:|---:|
{rows}

Task context discovered: {', '.join(report['task_context_files']) or '**none**'}
Standards discovered: {', '.join(report['standards_files']) or '**none**'}

---

## Arm A — the context-aware ensemble

Run each prompt in `prompts/` as its **own fresh agent session**, in parallel if you can. Each is
self-contained and tells the agent exactly which files it may read. Do not let them see each other's
output — independence is what makes the dedup step meaningful.

```
{chr(10).join(f'  {("prompts/" + n + ".md"):<34} ->  arm-a/specialist-{n}.md' for n in names)}
```

With Claude Code, one session per agent:

```bash
{chr(10).join(f'claude -p "$(cat {(out / "prompts" / (n + ".md")).as_posix()})"' for n in names)}
```

Then combine: findings two specialists reached independently are the highest-confidence class;
carry unique high/medium findings through; deduplicate aggressively; and triage each survivor as
**Action Required** or **Review Recommended**.

> One caveat worth keeping: agreement between two *retrieval-bound* specialists is correlated
> evidence, not independent evidence — they may both be reasoning from the same absence. Treat
> convergence as a prompt to verify, not as proof.

## Arm B — your exploring reviewer

Run whatever agentic reviewer you want to compare against, on the same target, same commit, same
day. It should read files itself rather than receive a bundle. For example:

```
/code-review high {' '.join(target)}
```

Save its output to `arm-b/findings.md`, and record what it read, how long it took, and whether it
executed anything — that last one usually explains most of the difference.

## Then compare

```bash
python -m arena.check_citations --repo {repo.as_posix()} {(out / 'arm-a').as_posix()} {(out / 'arm-b').as_posix()}
```

Build the overlap set by hand — it is the number that matters, and it is small enough to do
honestly. For each finding, ask:

1. Did both arms find it? (Overlap is usually far lower than people expect.)
2. Could the other arm have found it *at all*, or was it structurally invisible?
3. **Then fix it.** Verification is weaker than it looks: a finding can be confirmed, reproduced,
   and still carry an explanation that sends you to the wrong line. Implementing the fix is the
   only step that catches that.
"""
    (out / "RUN.md").write_text(md, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())

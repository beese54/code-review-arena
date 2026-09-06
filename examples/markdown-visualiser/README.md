# Reference run — markdown-visualiser

The run this harness came out of. A real repository, not a toy.

**Target:** `src/` + `server/` — 31 TS/TSX files, 4,265 LOC, at a clean commit
**Both arms:** Claude Opus 5, same day, clean-room sessions blind to each other

| | Arm A (context-aware ensemble) | Arm B (Claude Code `/code-review high`) |
|---|---|---|
| Findings | 20 after dedup | 13 |
| Files opened | 0 — retrieval-bound | 31 of 31 |
| Non-source context | spec, DoD, README, standards | none |
| Ran the code | no | yes — 3 findings reproduced |
| Citation accuracy | 86% | 100% |

**33 findings. 2 were the same finding.**

## Read in this order

1. [`COMPARISON.md`](COMPARISON.md) — the analysis. §6 is the part worth your time.
2. [`verification.md`](verification.md) — both arms checked against source, one method. The addendum
   records what fixing the findings revealed that verification missed.
3. [`METHODOLOGY.md`](METHODOLOGY.md) — how each arm ran, and the limits on what can be claimed.
4. [`PLAN.md`](PLAN.md) — the design, written before the runs.

Raw outputs: [`arm-a-qodo/`](arm-a-qodo/) (three specialists + the ensemble/triage step) and
[`arm-b-claude-code/`](arm-b-claude-code/) (verbatim output plus what it read and executed).

## Caveats that travel with these numbers

- The Qodo **product** was not run. Arm A implements the methodology from their course. This is an
  architecture comparison, not a product benchmark.
- **No ground truth**, so no precision/recall/F1 — the comparison is qualitative plus an overlap
  count and one mechanical metric.
- Single run, single repo, one day. LLM output is non-deterministic.
- Arm A's paths in these files reference the original run layout (`context-engine/bundles/`);
  the harness now writes to `review-arena-run/bundles/`.

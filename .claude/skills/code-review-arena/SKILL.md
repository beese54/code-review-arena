---
name: code-review-arena
description: >
  Run two architecturally different AI code reviewers over the same code and find out what each one
  structurally cannot see. Builds the context-aware arm — structure-aware chunking, selective
  embedding retrieval, a specialist ensemble grounded in the project's own spec and standards — runs
  it against whatever reviewer you want to compare (Claude Code's /code-review, a PR bot, another
  model), then measures citation accuracy and the overlap between them. Use when asked to compare
  code review tools or approaches, to evaluate whether a review setup is worth its cost, to
  reproduce or extend the code-review-arena experiment, or to run a context-aware ensemble review on
  a repo. Not a benchmark and it will not declare a winner — the overlap is the result.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, AskUserQuestion, TodoWrite
---

# code-review-arena

Two reviewers. Same code, same commit, same day, same model. The only variable is **how each
reviewer is built**. The output is not a score — it is a map of each one's blind spots.

In the reference run: **31 distinct issues, 2 shared. 6.5% overlap.**

## Before you start

This skill assumes the `code-review-arena` repo is available. If it is not:

```bash
git clone https://github.com/beese54/code-review-arena
cd code-review-arena && pip install -r requirements.txt && npm install
```

`npm install` is only for the TypeScript AST chunker. Without Node the tool falls back to the
structural chunker and says so.

## The one rule

**Never declare a winner.** There is no ground-truth bug list for a real repo, so precision, recall
and F1 are unavailable, and any "Arm A won" claim is unearned. If the user asks which is better, say
what you can support instead: what each found, what each structurally could not have found, and how
little they agreed. That framing is the deliverable.

---

## Phase 1 — Set the experiment up

Ask the user only for what you cannot determine yourself:

- **Target** — which paths (`src`, `server`, `lib`…). Default to the app source, not tests or
  generated code.
- **Arm B** — the reviewer to compare against. Claude Code's `/code-review high` is the usual
  choice; a PR bot or another model works too.

Then pin the conditions and write them down, because they are what makes the comparison mean
anything:

```bash
git rev-parse --short HEAD && git status --short   # must be clean
```

Record: repo, commit, target paths, file count, line count, date, model. Both arms must see the
**same code at the same commit**, and neither may see the other's output.

## Phase 2 — Build Arm A's context

```bash
python -m arena.run --repo /path/to/repo --target src server --describe "One paragraph about what this system does and who uses it."
```

`--describe` is worth writing by hand. It is injected into every specialist prompt, and it is the
difference between a reviewer that knows what the code is *for* and one guessing from identifiers.

Check the output before continuing:

- **Reduction should be 70–85%.** If it is near 0%, `--top-k` exceeded the index — that is a
  full-context run, not a selective one, and the tool warns about it. Lower `--top-k` to roughly
  15% of the index.
- **Task context discovered.** If it printed `NONE FOUND`, the requirements-gap agent has nothing
  to measure against. Either point `--task-file` at the spec, or keep the agent and report the
  absence — "this project has no written acceptance criteria" is a finding.

Everything lands in `<repo>/review-arena-run/`, and `RUN.md` restates the next steps with the real
paths filled in.

## Phase 3 — Run both arms, blind

**Arm A.** Each prompt in `prompts/` runs as its **own fresh agent session**, in parallel. Launch
them with the Agent tool, one per specialist, passing the prompt file's contents. They must not see
each other's findings — independence is the only thing that makes the later dedup meaningful.

Each writes to `arm-a/specialist-<name>.md`.

Then combine them yourself into `arm-a/ensemble.md`:

1. Deduplicate aggressively — same root cause at the same location is one finding.
2. Note which findings **two specialists reached independently**. The method treats these as
   highest-confidence.
3. Triage each survivor: **Action Required** or **Review Recommended**.
4. State coverage honestly. If acceptance criteria were checked, say how many could not be assessed
   from the retrieved slice — in the reference run that was 24 of 53.

**Arm B.** Run the comparison reviewer on the same target, same commit. Save to `arm-b/findings.md`
and record in `arm-b/run-notes.md`: what it read, how long it took, whether it executed anything,
and whether it used subagents. That last pair usually explains most of the difference.

## Phase 4 — Compare

```bash
python -m arena.check_citations --repo /path/to/repo review-arena-run/arm-a review-arena-run/arm-b
```

This is the one fully objective measurement available: do the `file:line` citations point at real
lines? It reports out-of-range and unresolvable separately, and refuses to score an ambiguous path
rather than guessing.

Then build the overlap set **by hand**. It is small enough to do honestly, and the number is the
point of the whole exercise. For each finding:

1. Did both arms find it?
2. Could the other arm have found it **at all**, or was it structurally invisible?
3. Is the *mechanism* right, not just the symptom?

Read `references/comparing.md` for how to run that analysis and the three traps that make it come
out wrong.

## Phase 5 — Fix one

Do not stop at "verified". Pick the highest-severity confirmed finding from each arm and **implement
the fix**.

This is the step that separates this workflow from a review that reads well. In the reference run,
both arms passed verification with zero fabrications — and fixing revealed that **both were wrong
about mechanism**, including the one that had reproduced its bug by executing the code. It proved a
real symptom and blamed the wrong cause.

Record what fixing changed about each finding. That addendum is usually the most valuable artifact
in the run.

---

## Reference files

| File | Read when |
|---|---|
| `references/comparing.md` | Phase 4 — building the overlap set, and the three traps |
| `references/adding-agents.md` | The user wants a specialist beyond the built-in three |

## Reporting

Write the run up as `COMPARISON.md` with: the shared conditions table, per-arm findings counts, the
overlap number, a section per non-overlapping finding explaining *why* the other arm could not have
found it, the citation-accuracy figures, and a section on what fixing revealed.

State the limitations in the document, not in a footnote: no ground truth, so no precision or recall;
the arms are asymmetric by design; and one run on one repo is an observation, not a result.

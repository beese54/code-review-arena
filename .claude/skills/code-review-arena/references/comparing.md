# Building the overlap set

Phase 4. This is where the run either produces something honest or produces a scoreboard nobody
should trust.

## The table

One row per finding across both arms. Do it by hand — a real run is 20–40 findings, which is small
enough to read properly, and no string similarity will tell you whether two findings are the same
bug.

| # | Arm | Severity | Location | Claim | Same as | Could the other arm have found it? |
|---|---|---|---|---|---|---|

Two findings are **the same** when they name the same root cause at the same location. Not when they
touch the same file. Not when they use the same vocabulary. Two agents can both write "unsafe
sanitizer config" about two unrelated lines.

Expect the overlap to be low. In the reference run it was 2 of 33. If you get a high overlap,
suspect the arms were not actually independent — check that Arm B could not see Arm A's output, and
that the same session did not pre-read the source for both.

## Column 7 is the whole point

For every finding only one arm reported, answer: **could the other arm have found this at all?**

Three honest answers:

- **Structurally invisible.** The other arm lacked the *kind* of evidence needed. A reviewer with no
  spec cannot find "the API documents a field the server ignores" — the evidence is a promise made
  outside the code. A reviewer that cannot execute cannot find "this output is wrong at runtime."
- **Reachable but missed.** The evidence was available and it did not look. This is the only column-7
  answer that is a quality difference rather than an architecture difference.
- **Out of scope.** The finding is about code the other arm was not pointed at.

A comparison that reports only counts is nearly worthless. A comparison that classifies every
non-overlapping finding this way tells you what each architecture is *for*.

## The three traps

**1. Ensemble agreement is correlated evidence, not independent evidence.**

The method treats "two specialists found this independently" as its highest-confidence class. In the
reference run, that class contained exactly one finding — and it was the finding that verification
deflated hardest. Both specialists were reasoning from the same *absence* in the same bundle, so they
were not two witnesses. They were one witness, asked twice.

Treat convergence as a reason to verify, never as proof.

**2. Retrieval cannot show an absence.**

Arm A's bundles contain code. They cannot contain the fact that nothing imports a given symbol,
because "no callers" is not a chunk — it is a negative result over the whole repo. In the reference
run Arm A had the dead security control in its bundle and confidently reasoned about how the control
behaved. Arm B ran one grep.

When Arm A reports on whether a control is effective, check whether anything calls it before you
believe either the finding or its refutation.

**3. Verification is weaker than fixing.**

Verification asks "is the cited code real, and does the claim match it?" Both arms can pass that
completely and still be wrong about *why* the bug happens. The reference run's most-verified
finding — reproduced by executing the pipeline and pasting real broken output — attributed the
symptom to the wrong mechanism, and the fix implied by its explanation would not have closed
anything.

Symptom correct + mechanism wrong is the most expensive failure mode in AI review, because it
survives every check short of implementation.

## Citation accuracy

`check_citations.py` gives one objective number per arm. Read it carefully:

- **Out of range** — the file exists, the line does not. The quoted code is often still real; the
  pointer drifted. Costs a developer time, does not by itself make the finding wrong.
- **Unknown / unresolvable** — the path does not exist, or a bare filename matches several files.
  These are *not scored*, deliberately. Scoring a dependency path against an unrelated file of the
  same basename produces a fake failure.

Report both numbers. Do not merge them.

## What to write

`COMPARISON.md`, containing:

1. Shared conditions — repo, commit, target, size, date, model, and the statement that neither arm
   saw the other's output.
2. The counts and the overlap number, stated plainly.
3. One section per non-overlapping finding, each answering column 7.
4. Citation accuracy per arm, out-of-range and unresolvable separately.
5. What fixing revealed (Phase 5). Usually the most valuable section.
6. Limitations, in the body and not a footnote: no ground truth so no precision/recall; the arms are
   asymmetric by design; one run on one repo is an observation, not a result.

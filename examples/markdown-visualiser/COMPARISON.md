# Two AI code reviews of the same code, on the same day

**Repo:** `markdown-visualiser` · **Target:** `src/` + `server/`, 31 TS/TSX files, 4,265 LOC
**HEAD:** `cc34345`, tree clean · **Date:** 2026-09-05 · **Model:** Claude Opus 5, both arms

- **Arm A — the qodo methodology.** Context engine (AST chunking → embeddings → selective vector
  retrieval) + task-level context + repo standards → three specialist agents in parallel →
  deduplicate → risk triage. Reconstructed from the DeepLearning.AI × Qodo course.
- **Arm B — Claude Code's built-in review.** `/code-review high src server`, unmodified.

Both ran in clean-room sessions, blind to each other. Both were then verified against the real
source using the same method (`verification.md`).

> **Read this first:** the qodo *product* is not installed here and no qodo key is present. Arm A is
> a faithful implementation of the *methodology the course teaches* — not the commercial tool. The
> product's PR integration, memory layer and cross-repo analysis are not reproduced. See
> `METHODOLOGY.md` for the full limitations list.

---

## 1. The headline number

| | Arm A (qodo methodology) | Arm B (Claude Code) |
|---|---|---|
| Raw findings | 21 → **20** after dedup | **13** |
| Severity mix | 4 high / 12 med / 5 low | 2 HIGH / 7 MED / 4 LOW |
| Triage labels | Action Required 6 · Review Recommended 14 | none (severity only) |
| Wall clock | ~5.5 min (3 specialists in parallel) + ~2 min engine build | **9 min 27 s** |
| Tokens | ~239k across 3 specialists | ~156k |
| Files opened | **0** (retrieval-bound) | **31 of 31**, plus 4 `node_modules` sources |
| Non-source context | spec, DoD, README, CLAUDE.md, eslint, tsconfig | **none** |
| Code executed to verify | none (architecturally impossible) | **3 findings reproduced** |
| Citation accuracy | **86%** (51/59) | **100%** (15/15) |
| Findings refuted on verification | 1 downgraded, 1 overstated | 0 |
| Findings whose *mechanism* was wrong (found when fixing) | 0 | **1** |
| Findings pointing at non-existent code | 0 | 0 |

**33 findings between them. Exactly 2 are the same finding.**

```
        Arm A only          shared          Arm B only
    ┌──────────────────┐  ┌────────┐  ┌──────────────────┐
    │       18         │  │   2    │  │       11         │
    └──────────────────┘  └────────┘  └──────────────────┘
                    31 distinct issues
                     overlap: 6.5%
```

That is the result. Not "one is better" — **they barely look at the same thing.**

### The two they agreed on

| Issue | Arm A | Arm B |
|---|---|---|
| `getBrowser` caches a *rejected* launch promise, so one transient Chromium failure 503s the print service for the life of the process | P1 (high) | #2 (HIGH) |
| A bare `'className'` on `'*'` voids the six per-tag class allowlists below it | S3 (medium) | #4 (MEDIUM) |

Both real, both confirmed. Worth noting *how* each got there: Arm A found the browser bug by
noticing the codebase **contradicts a rule it wrote down for itself** — `Mermaid.tsx` documents
"never cache a rejected promise" for the identical `??=` idiom and guards against it. Arm B found
the same bug by reading the code and reasoning about `??=` from first principles. Same defect, two
completely different routes.

On the `className` finding, Arm B got the line right (`98`, where Arm A said `274-281` in a 180-line
file) and **reproduced** a forged `<pre class="mermaid">` being drawn as a real diagram from
author-controlled raw HTML.

But when I actually fixed the finding, Arm B's *explanation* turned out to be wrong and **Arm A's
was right** — see §6. Arm B claimed the per-tag allowlists "are never consulted"; they are, and they
do strip. And the mermaid forgery it reproduced is not caused by the `className` bug at all: `pre`
explicitly permits `'mermaid'`, so that forgery still works after the fix. Reproduction proved the
symptom and mis-attributed the cause.

---

## 2. What only Arm A could find

**Every requirements gap.** Arm B read no specification, so it could not measure the code against
one. These four are structurally invisible to it:

| | Finding |
|---|---|
| **R1** | `specification.json` advertises an optional `margin: {top,right,bottom,left}` on `POST /api/export/pdf`. The server hardcodes `22mm/18mm/20mm/22mm` and never reads it; the client type has no field to send it. Meanwhile the server *does* read an undocumented `landscape`. **The contract and the implementation diverge in both directions.** |
| **R2** | The standalone HTML export carries the *repaired* rendering with none of the repair notes — the one artefact a user sends to someone else is the one where the alterations become invisible. The README calls this out as a moral commitment: *"silently editing someone's writing is not acceptable behaviour for a reader."* |
| **R3** | `dropRedundantTitle` is a **sixth** repair behaviour outside the five specified rules and the closed `RepairRule` union — and it *removes* a heading where the spec's `duplicate-h1` rule specifies *demotion*. It then files the note under `duplicate-h1`, so the note misdescribes what happened. |
| **R5** | The skipped-files list renders `slice(0, 20)` with no "and N more", so past 20 skips the spec's *"never silently discarded"* guarantee has no user-reachable surface. |

R1 is the clearest case. It is not a bug in any local sense — the code is internally consistent and
does exactly what it says. It is only wrong **relative to a document Arm B never opened.**

Arm A also produced a class Arm B did not: **findings that cite the codebase's own written
standards.** P3 and P6 are not "this is bad practice" — they are "this contradicts the rule this
repo states for itself", quoting the spec's *"never silently discarded"* and DoD 1.6. Verification
found both were *understated*:

- **P3** — on a failed asset the export calls `img.removeAttribute('src')`: a broken image, no
  placeholder, no notice, against a spec that mandates *"a styled placeholder figure naming the
  missing path; never a broken-image icon."* Worse, the CSS path silently leaves the **remote URL**
  in the stylesheet, so the "works offline" file still reaches for the network.
- **P6** — `walkEntry` wraps the **file** branch in try/catch with a comment saying *"A single
  unreadable file must not abort the whole import"*, then leaves the **directory** branch unguarded
  one branch away. The convention is established and broken in the same function.

---

## 3. What only Arm B could find

**Anything requiring you to run the code.** Arm B wrote throwaway ESM scripts, executed the real
unified/remark/rehype pipeline against the project's own `node_modules`, and deleted them. Three
findings carry reproduced output:

| | Finding |
|---|---|
| **#1** | `clobberPrefix` is applied twice, so **every GFM footnote link in every document is dead**. `mdast-util-to-hast` already prefixes footnote ids with `user-content-` and writes matching hrefs; the schema then prefixes the *id* again and leaves the *href* alone. Reproduced: `<a href="#user-content-fn-1" id="user-content-user-content-fnref-1">`. |
| **#5** | `repairListNesting` **welds sibling list items into one run-on item** — `flatMap((child) => child.children)` discards the item boundaries. Reproduced: `- - a\n  - b` becomes `<ul><li>ab</li></ul>`, while the repair note still claims "nested items lifted to this level". A repair tool silently mangling the user's list is about the worst failure this product has. |
| **#4** | The `className` exploit, reproduced end to end (see above). |

Arm A could not have found any of these. It never had the ability to execute anything.

**And one more, which is the most interesting result in the whole exercise:**

| | Finding |
|---|---|
| **#3** | `printSchema` — documented as *"a second, stricter schema applied server-side before the print service hands HTML to Chromium"* — is **never imported anywhere**. `grep -rn printSchema src server tests` returns exactly one line: its own definition. `server/pdf.ts` passes `request.html` straight into `page.setContent`. The stated defence-in-depth layer does not exist. |

`printSchema` **was in Arm A's retrieved bundle.** The security specialist read it, and reasoned
about its `src: ['data','blob']` restriction as a live control (its finding S6 argues a
protocol-relative URL slips past it). The restriction is not bypassed — it is never applied.

**Retrieval hands you the code. It cannot hand you the absence of callers.** You cannot grep for
"who imports this" from inside a bundle, and no amount of extra retrieved context fixes it, because
the evidence required is a *negative result over the whole repo*. Arm A's richer context actively
misled it here: having the code made it confident about a control that was dead.

---

## 4. Where the context-rich arm went wrong

Being fair to the result cuts both ways.

**The ensemble's strongest signal was its weakest finding.** The course's scoring rule treats
agreement between two independent specialists as the highest-confidence class. Exactly one such
convergence occurred — E1, where the security agent (from OWASP) and the requirements agent (from
the spec's `pipeline.invariant`) independently concluded that user-controlled data reaches stages
running after the sanitizer. Verification collapsed both halves:

- `Mermaid.tsx:50` already pins `securityLevel: 'strict'`.
- `rehype-assets` builds placeholder nodes structurally — `{type:'element', …, children:[{type:'text', value: path}]}` — never as raw HTML. A path of `"><img src=x onerror=1>` renders as visible text.

What survives is real but much smaller: `specification.json` lists 9 post-parse stages, the code
runs 13, and the README's diagram disagrees with the spec. **E1 was downgraded from a security
blocker to documentation drift.**

The lesson generalises: **agreement between two context-starved reviewers is correlated evidence,
not independent evidence.** They were both reasoning from the same absence. An ensemble that scores
agreement as confidence will systematically over-rate exactly the findings its shared blind spot
produces.

**Citation drift.** 8 of Arm A's 59 citations pointed past the end of the file — the security agent
cited `sanitize.ts:274-281`, `:288-298`, `:294-296` in a **180-line file**. The quoted *code* was
real every time; only the pointers were wrong. Notably the bundle headers carried the **correct**
line numbers, so the engine was fine and the agent drifted. Arm B, reading files directly, was
100% accurate — its line numbers came from the tool that opened the file.

**Coverage it could not admit to.** The requirements agent extracted **53 acceptance criteria** and
could only reach a verdict on 29. It marked **24 (45%) "Not visible"** — honestly, rather than
guessing. At a 15%-of-index retrieval budget, nearly half the specification went unchecked.

---

## 5. So what is actually different?

| | Arm A — qodo methodology | Arm B — Claude Code |
|---|---|---|
| **Core question it answers** | "Does this match what we said we'd build, and how we said we'd build it?" | "Does this code actually work?" |
| **Where its knowledge comes from** | Documents you wrote: spec, DoD, standards, README | The code itself, plus its own execution |
| **Evidence it produces** | A quoted requirement next to the code that fails it | A reproduced failure, pasted |
| **Structural blind spot** | Anything requiring execution; anything requiring a negative result over the repo | Anything requiring a document it wasn't given |
| **Failure mode observed** | Overstated severity; drifting line numbers | None observed in this run |
| **Precision-limiting factor** | What retrieval happened to surface | Nothing external — it can go look |
| **Improves when you** | Write better specs, standards and tickets | Nothing to feed it; it already reads everything |

The comparison people expect is "which one finds more bugs". The honest answer is that
**they are answering different questions**, and the 6.5% overlap is the proof.

A concrete way to see it: **R1 and #1 are both real, both worth fixing, and neither tool could ever
have found the other's.** R1 (a documented API field silently ignored) requires a spec. #1 (every
footnote link in the app is dead) requires running the pipeline. No amount of "trying harder" moves
either tool across that line — the limits are architectural, not effort-based.

### The practical read

They compose, and the ordering matters. The course's own best practice #2 says to run a **pre-PR
review locally** before asking anyone else to look — and Arm B, which reads everything and can
execute, is exactly the right shape for that. Then a context-fed reviewer measures the result
against the spec and standards at PR time, which is the one thing the local pass structurally
cannot do.

Running them in that order is not a compromise. It is the only sequence in which each one's blind
spot is covered by the other's strength.

### One caveat that survives all of this

The single most valuable finding across both arms — #5, the repair pass silently welding a user's
list items together — was found by reading and running the code, and it violates a rule the module
header states in plain English. The context-fed arm had that rule **and** the spec's
`repair.philosophy` in its bundle and still missed it, because its retrieval never surfaced
`repairListNesting`.

Context is not a substitute for coverage. Arm A had better *information* about the repair module
than Arm B ever did, and Arm B found the bug anyway — by opening the file.

---

## 6. The part you only learn by fixing the findings

Both confirmed findings were then fixed for real. That is where the sharpest result came from —
because implementing a fix forces you to reproduce the defect *exactly*, and both reviews turned out
to be partly wrong about mechanism.

**The `className` bug is real — and bigger than either arm said.** Sweeping all 56 permitted tags:

```
before fix   arbitrary class KEPT on 43 tags   (h1, h3-h6, em, strong, table, img, figure, details …)
after  fix   arbitrary class KEPT on  0 tags
```

But Arm B's stated mechanism — *"the code/pre/span/div allowlists are never consulted"* — is false.
They are consulted and they do strip. And the forged `<pre class="mermaid">` it reproduced isn't
caused by this bug: `pre` deliberately allows `'mermaid'`, so that forgery survives the fix
untouched. **Arm B ran the code, proved a real symptom, and attributed it to the wrong cause.**

Arm A, which could not run anything, described the mechanism correctly — *"unconditional for the
un-narrowed tags"*, with the narrowed ones explicitly flagged as unresolvable from its bundle. It
reasoned its way there from the file's own `inheritedExcept` doc comment.

**`printSchema` is worse than dead — it is unusable.** Arm B found it was never imported and framed
the fix as wiring it up. It cannot be wired up: it extends `sanitizeSchema`, which by design forbids
`style=`, `<svg>` and `<math>` — exactly what KaTeX, Shiki and Mermaid emit after the boundary.
Measured on a real export:

```
BEFORE printSchema: katex ✓  styles ✓  shiki ✓   1297 bytes
AFTER  printSchema: katex ✗  styles ✗  shiki ✗    499 bytes
```

Switching it on would have shipped a blank-looking PDF. Arm B got the defect right and the remedy
wrong; Arm A argued about the behaviour of a control that was neither live nor applicable.

**And a real issue neither arm found:** the marker classes the downstream plugins key off
(`mermaid` on `pre`, `markdown-alert*` on `div`/`p`) are reachable from raw HTML inside user
markdown, not only from real fences and callouts. Mermaid runs at `securityLevel: 'strict'`, so it
is spoofing rather than script execution — but the allowlist cannot currently tell a class the
pipeline generated from one an author typed.

### The takeaway that outranks the overlap number

Verification said both arms were clean. **Fixing said otherwise.**

A finding can be confirmed, reproduced, correctly prioritised, genuinely worth fixing — and still
carry an explanation that would send you to the wrong line. The only step that catches that is
implementing the fix. If you are evaluating AI code review tools, "did it find real bugs" is the
easy half of the question. "Was it right about why" is the half that decides whether the fix you
ship actually closes anything.

---

## Artefacts

| Path | What it is |
|---|---|
| `PLAN.md` | Experimental design, fairness controls |
| `METHODOLOGY.md` | Exactly how each arm was run + limitations |
| `verification.md` | Both arms checked against source, same method |
| `check_citations.py` | The mechanical citation checker |
| `context-engine/chunk.mjs` | AST chunker (TypeScript compiler API) |
| `context-engine/retrieve.py` | Embeddings → Chroma → selective retrieval |
| `context-engine/bundles/` | The five context bundles the specialists received |
| `context-engine/retrieval-report.md` | What was retrieved, with similarity scores |
| `arm-a-qodo/specialist-*.md` | The three specialists' raw findings |
| `arm-a-qodo/ensemble.md` | Combine → dedup → triage |
| `arm-b-claude-code/findings.md` | Verbatim `/code-review high` output |
| `arm-b-claude-code/run-notes.md` | What it read, how long, what it executed |

## Reproducing

```bash
node code-review-comparison/context-engine/chunk.mjs .      # 31 files -> 199 chunks
python code-review-comparison/context-engine/retrieve.py    # -> bundles/
python code-review-comparison/check_citations.py            # citation accuracy
```

Arm B: `/code-review high src server` in Claude Code.

## Caveats worth keeping attached to any public writeup

1. **This is not the qodo product** — no CLI, no key. It is the course's methodology, reimplemented.
2. **No ground truth**, so no precision/recall/F1. The course computes those against 15 synthetic
   PRs with planted bugs; this repo has no labelled issue set. Everything here is qualitative plus
   an overlap count and one mechanical metric (citations).
3. **Single run, single repo, one day.** LLM output is non-deterministic; re-running either arm
   would shift the finding sets.
4. **Same model both sides** (Claude Opus 5), which isolates architecture as the variable — but also
   means this measures review *architecture*, not qodo's model choices.
5. **The asymmetry is real, not imposed.** Arm A is retrieval-bound; Arm B explores freely. Neither
   handicap was added — each is how that architecture works.

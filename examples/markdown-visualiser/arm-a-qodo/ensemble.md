# Arm A — Ensemble result (combine → deduplicate → triage)

Per the course's lesson-6 strategy: run the specialists in parallel, treat findings **two
specialists independently reached** as the highest-confidence class, carry unique high/medium
findings through, deduplicate aggressively — then apply best-practice #5 risk triage
(**Action Required** vs **Review Recommended**).

## Input

| Specialist | Raw findings | high | medium | low |
|---|---:|---:|---:|---:|
| Security | 6 | 0 | 4 | 2 |
| Pattern compliance | 10 | 3 | 5 | 2 |
| Requirements gap | 5 | 1 | 3 | 1 |
| **Total raw** | **21** | **4** | **12** | **5** |

## Deduplication

One genuine cross-specialist convergence, reached from two different directions:

- **S1** (security agent, from the OWASP angle: "user-controlled data is consumed by stages that run
  after the sanitizer") and **R4** (requirements agent, from the spec angle: "four plugins run after
  the trust boundary that `pipeline.order` does not list, and `rehypeAssets` writes user-derived
  `src`/`href` there"). Neither agent could see the other. They converged on the same defect in
  `src/pipeline/render.ts` from independent evidence.
  → merged as **E1**, and promoted: the course treats agreement between specialists as the
  strongest signal the ensemble produces.

Three near-neighbours were examined and **kept separate**, because they are distinct defects that
merely share a file or a theme:

- **P3** (`toDataUri` silently drops assets from the export) vs **R2** (the export drops repair
  notes) — same file, same "the export loses information" theme, different data lost and different
  fixes. Not duplicates.
- **P6** (`readAllEntries` rejects the whole walk on one bad directory) vs **S4** (`walkEntry`
  recurses with no depth cap or cycle guard) — both in `walker.ts`, but one is error propagation and
  the other is unbounded recursion.
- **S5** (remote `img.src` defeats "zero third-party requests") overlaps the requirements agent's
  DoD 4.1 row, which that agent had marked *Not visible*. Kept as one finding, credited to security.

**21 raw → 20 after dedup.**

## Triage

### Action Required — address before this is considered done

Findings that affect security, data integrity, or system behaviour.

| ID | Finding | Source | Sev | Conf |
|---|---|---|---|---|
| **P1** | `getBrowser` caches a *rejected* launch promise forever — one transient Chromium failure 503s every PDF export for the life of the process. The codebase documents this exact rule for the same idiom in `Mermaid.tsx` and guards against it there. | pattern | high | high |
| **P3** | `toDataUri` collapses three failure modes into an unlabelled `null`, silently dropping assets from the "opens offline" export — against the spec's *"never silently discarded"* and DoD 4.1. | pattern | high | med |
| **R1** | `POST /api/export/pdf` advertises an optional `margin` object in `specification.json`; the server hardcodes margins and never reads it, and the client type cannot even send it. Meanwhile it *does* read an undocumented `landscape`. | requirements | high | high |
| **P2** | `harden` fires `route.continue()`/`route.abort()` with bare `void` and no catch, on precisely the deadline path where `renderPdf` closes the context underneath them — unhandled rejections in the service DoD 4.7 requires to stay up. | pattern | high | med |
| **E1** | **Cross-specialist convergence.** The `pipeline.invariant` ("nothing user-controlled after `rehype-sanitize`") does not hold as written: `rehypeAssets` builds nodes from author-controlled paths after the boundary, and mermaid source is carried out of band and rendered into the live DOM later. Spec lists 9 post-parse stages; code runs 13. | security + requirements | med | low–med |
| **S3** | A bare `'className'` on `'*'` sits above six narrowed `classes(...)` entries, so arbitrary classes reach every un-narrowed tag — silently making the schema's closed-set intent decorative. | security | med | med |

### Review Recommended — developer judgement, not necessarily a blocker

| ID | Finding | Source | Sev | Conf |
|---|---|---|---|---|
| **R2** | The standalone HTML export carries the *repaired* rendering with none of the repair notes — the one artefact a user sends to someone else is the one where the alterations become invisible. | requirements | med | med-high |
| **R3** | `dropRedundantTitle` is a sixth repair behaviour outside the five specified rules and the closed `RepairRule` union, and it *removes* where the spec's `duplicate-h1` rule specifies *demotion*. | requirements | med | med |
| **S2** | Dropped `.svg` may be handed a same-origin `blob:` URL — the exact content `sanitize.ts` refuses to inline, on the reasoning that SVG can carry script. Inert in `<img>`, live if the lightbox navigates to it. | security | med | low |
| **S4** | `walkEntry` recurses with no depth cap and no cycle guard; `maxFiles` counts files only, so an all-directories symlink cycle never trips it and the UI hangs silently in `reading`. | security | med | med |
| **P4** | `void job.finally(...)` — `.finally` re-throws, so a mermaid render timeout is an unhandled rejection, and the reader silently shows raw diagram source. | pattern | med | med |
| **P5** | The store's `ingest()` has no staleness guard while the render layer builds two for the same bug class; a superseded `DocumentSet` also never has its object URLs revoked — the leak `disposeCurrent`'s comment exists to prevent. | pattern | med | med |
| **P6** | `readAllEntries` passes `reject` straight to `readEntries`, so one unreadable directory discards the whole drop — against DoD 1.6 and the `skipped[]` contract. | pattern | med | med |
| **P7** | `renderDocument` returns a well-formed *successful* empty result for a doc it knows is broken, bypassing the existing `RenderState.failed` channel and discarding the message. | pattern | med | med |
| **P8** | The Shiki discovery pass is a second plugin chain that has already drifted — its tree comes from a separate bare `remarkParse`, making its `remarkFrontmatter`/`remarkGfm` dead config — joined by two `as` casts under a strict tsconfig. | pattern | med | med |
| **S5** | Untrusted markdown can make the reader fetch remote images, contradicting the README's *"zero third-party requests"* and surviving into the "offline" export as a read receipt. | security | low | high |
| **S6** | Protocol-relative `//host/path` passes both the `(?!\w+:)` lookahead and the protocol check, so `printSchema`'s `src: ['data','blob']` restriction never applies to it. | security | low | high |
| **R5** | The skipped-files list renders `slice(0, 20)` with no "and N more", so past 20 skips the "never silently discarded" guarantee has no user-reachable surface. | requirements | low | med |
| **P9** | `withTimeout` and `withDeadline` are byte-for-byte the same helper maintained in two places. | pattern | low | high |
| **P10** | `Heading.children` / `RepairResult.notes` are mutable arrays on cached, shared results, while the consuming components already declare `readonly`. | pattern | low | med |

**Action Required: 6 · Review Recommended: 14 · Total: 20**

## Coverage honesty

The requirements agent extracted **53 acceptance criteria** and could only reach a verdict on 29 of
them; **24 (45%) were marked "Not visible"** because the relevant code was not among its 30
retrieved chunks. It reported those as unknown rather than as passes or gaps.

That is the retrieval-bound architecture's structural cost, stated plainly: at a 15%-of-index
context budget, nearly half the specification could not be checked at all. Raising `n_results`, or
retrieving per-criterion instead of per-domain, would close it — at proportionally higher token cost.

Every specialist also attached an explicit `context_limitation` to each finding, naming the chunk it
would need to confirm or kill that finding. Nine of the twenty say, in effect, *"if the code I could
not see does X, this collapses."* That is unusually honest for a review — and it is also a
measurable liability, which the verification pass in `../COMPARISON.md` tests directly.

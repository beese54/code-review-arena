# Verification pass

Neither arm's findings are taken on trust. Every finding was checked against the actual source at
`cc34345`, using the same method for both arms:

1. **Citation check** (mechanical, `check_citations.py`) — does every `file:line` reference point
   inside the file that exists?
2. **Collapse-condition check** (manual) — Arm A's specialists each attached a
   `context_limitation` naming the code they could not see that would kill the finding. Each of
   those conditions was resolved against the real source.
3. **Claim check** (manual) — does the quoted code exist and does it do what the finding says?

---

## Arm A — citation accuracy

| Specialist | In-range citations | Accuracy |
|---|---|---|
| Security | 16 / 21 | 76% |
| Pattern compliance | 26 / 29 | 90% |
| Requirements gap | 9 / 9 | 100% |
| **Arm A total** | **51 / 59** | **86%** |

Out-of-range citations:

```
security     src/pipeline/sanitize.ts:274-281   (file has 180 lines)
security     src/pipeline/sanitize.ts:288-298   (file has 180 lines)
security     src/pipeline/sanitize.ts:294-296   (file has 180 lines)
security     src/pipeline/sanitize.ts:298       (file has 180 lines)
security     src/state/store.ts:396-425         (file has  95 lines)
pattern      server/pdf.ts:263                  (file has 231 lines)
pattern      src/state/render.ts:183            (file has 173 lines)
pattern      src/pipeline/render.ts:694         (file has 207 lines)
```

**Important qualifier: in every out-of-range case I checked, the quoted *code* is real and present
in the file — only the line pointer is wrong.** The `'*': [...inherited('*'), 'id', 'className']`
entry the security agent cites at `:274-281` genuinely exists, at `sanitize.ts:98`. So these are
navigation defects, not fabricated findings. They still cost a developer time, and they are the
clearest downside of reviewing from a retrieved bundle rather than from the file itself — note that
the bundle headers carried the *correct* line numbers, so the drift was introduced by the agent, not
by the context engine.

---

## Arm A — collapse conditions resolved

Nine of twenty findings said, in effect, *"if the code I could not see does X, this collapses."*
Resolving them against the source:

| ID | Collapse condition | Resolution | Verdict |
|---|---|---|---|
| **P1** | "if a healthcheck calls `closeBrowser()` on a failed export the window narrows" | `getBrowser` at `server/pdf.ts:54-63` has no `.catch` clearing the slot; the `disconnected` listener only attaches to a browser that *did* launch; nothing on the error path calls `closeBrowser`. | **CONFIRMED** |
| **P2** | "if the bootstrap installs `process.on('unhandledRejection')` this drops to a log line" | `server/index.ts` registers only `SIGTERM` and `SIGINT`. No global rejection handler exists. | **CONFIRMED** |
| **P3** | "if the caller already substitutes a placeholder, only the lost cause remains" | It does not. `inlineImages` calls `img.removeAttribute('src')` on failure — a broken image with no src, no placeholder, no notice. The spec mandates *"a styled placeholder figure naming the missing path; never a broken-image icon."* The CSS path is worse: on failure it silently leaves the **remote URL** in the stylesheet, so the "offline" export still reaches for the network. | **CONFIRMED, and understated** |
| **P6** | "if `walkDataTransfer` wraps each recursion in try/catch, the rejection never propagates" | It does not. `walkEntry` wraps the **file** branch in try/catch with a comment saying *"A single unreadable file must not abort the whole import"* — and leaves the **directory** branch (`await readAllEntries(...)`) unguarded. The codebase establishes the convention and omits it one branch away. | **CONFIRMED, and strengthened** |
| **R1** | "if the route rejects unknown fields, `margin` would 400 rather than be ignored" | `server/index.ts:63-64` declares only `format` and `landscape`; `margin` appears nowhere in the server. `server/pdf.ts:188` hardcodes it. `landscape` is read but undocumented. | **CONFIRMED both directions** |
| **R3** | "if it demotes and the comment's 'removed' is loose wording, severity drops" | It removes: `tree.children.splice(index, 1)` at `remark-repair.ts:68`, and then pushes a note under `rule: 'duplicate-h1'` — the rule whose spec text says H1s are *demoted to H2*. The note misdescribes the change, exactly as predicted. | **CONFIRMED** |
| **S2** | "if `isImagePath` excludes `.svg`, this collapses entirely — that single predicate decides it" | `IMAGE_EXTENSIONS` (`domain.ts:118`) **includes** `.svg`, so a same-origin `blob:` URL with `type: image/svg+xml` is minted. But the second half fails: `Lightbox.tsx:68` renders `<img src={src}>` only — no anchor, no `window.open`, no navigation affordance anywhere. | **PREMISE CONFIRMED, EXPLOIT PATH ABSENT** → defence-in-depth only |
| **S3** | "`inherited()`'s behaviour and `hast-util-sanitize`'s merge order decide whether the six narrowed tags are affected" | The bare `'className'` on `'*'` is real (`sanitize.ts:98`, directly above the six narrowed entries). The un-narrowed-tag gap is unconditional, as the agent said. | **CONFIRMED** (for un-narrowed tags) |
| **S4** | "a depth or entry cap could live in `walkDataTransfer` or `readAllEntries`" | Neither has one. `walkEntry`'s only guard is `out.length >= opts.maxFiles`, which counts files; the directory branch recurses with no depth cap and no visited-set. | **CONFIRMED** |

### The one that did not survive

**E1** — the ensemble's headline finding, and the only cross-specialist convergence, is the one
verification most damages:

- The **mermaid half** is closed. `Mermaid.tsx:50` pins `securityLevel: 'strict'`. The security
  agent predicted this exact outcome in its own context limitation.
- The **`rehype-assets` half** is closed for injection. It builds placeholder nodes structurally —
  `{ type: 'element', tagName: 'code', properties: {}, children: [{ type: 'text', value: path }] }`
  — never `{type:'raw'}`, never string concatenation. A path of `"><img src=x onerror=1>` renders as
  visible text.
- What **survives** is the requirements agent's half (a): `specification.json` lists 9 post-parse
  stages, the code runs 13, and the README's diagram disagrees with the spec. That is real
  documentation drift on the invariant both documents call "the load-bearing decision" — but it is
  documentation drift, not a vulnerability.

**E1 is downgraded from Action Required (security) to Review Recommended (documentation drift).**

This is worth dwelling on for the writeup: the ensemble's *strongest* signal by its own scoring
rule — the one finding two independent specialists agreed on — was the finding that verification
most deflated. Agreement between two context-starved reviewers is correlated evidence, not
independent evidence: they were both reasoning from the same absence.

### Arm A post-verification tally

| | Count |
|---|---|
| Confirmed as stated | 8 |
| Confirmed and *understated* by the reviewer | 2 (P3, P6) |
| Premise true, impact overstated | 1 (S2) |
| Downgraded from security to documentation | 1 (E1) |
| Not individually re-verified (low severity, self-evident from quoted code) | 8 |
| **Fabricated / non-existent code** | **0** |

Zero findings pointed at code that does not exist. The failure mode of this arm was **wrong line
numbers and overstated severity**, not invention.

---

## Arm B — citation accuracy

| | In-range citations | Accuracy |
|---|---|---|
| Claude Code `/code-review high` | 15 / 15 | **100%** |

No out-of-range citations. Every `file:line` pointed inside the file. This is the direct consequence
of reading files rather than a retrieved bundle: the line numbers came from the tool that opened the
file.

## Arm B — claim check

| # | Claim | Resolution | Verdict |
|---|---|---|---|
| 1 | `clobberPrefix` applied twice, breaking every GFM footnote link | `sanitize.ts:158-159` sets `clobberPrefix: 'user-content-'` + `clobber: ['name','id']`; `mdast-util-to-hast` already applies that prefix. The reviewer **executed the real pipeline against the project's own `node_modules`** and pasted the doubled output. | **CONFIRMED (reproduced)** |
| 2 | One failed Chromium launch permanently 503s the print service | Same defect as Arm A's P1; independently confirmed above. | **CONFIRMED** |
| 3 | `printSchema` is dead code; its doc comment describes a control that does not exist | `grep -rn printSchema src server tests` returns **exactly one line — its own definition**. Never imported. `server/pdf.ts` passes `request.html` straight to `page.setContent`. | **CONFIRMED** |
| 4 | Bare `'className'` in `'*'` voids the per-tag class allowlists | Real at `sanitize.ts:98`. The reviewer went further than Arm A and **reproduced** it: forged `<pre class="mermaid">` survives sanitization and is then drawn as a real diagram by `rehypeMermaid` from author-controlled raw HTML. | **CONFIRMED (reproduced)** |
| 5 | `repairListNesting` welds sibling list items into one run-on item | `remark-repair.ts:228` — `item.children = inner.children.flatMap((child) => child.children)` discards item boundaries. Reproduced: `- - a\n  - b` becomes `<ul><li>ab</li></ul>`. The note still claims "nested items lifted to this level". | **CONFIRMED (reproduced)** |
| 6 | Duplicate diagram source: only the first occurrence is drawn | Content-hashed ids collide; `currentSlot` re-queries with `querySelector`, which returns the first match. Consistent with the code and its own comments. | **PLAUSIBLE** (not independently re-run) |
| 8 | The client size guard measures HTML bytes, not the JSON body it sends | `export/pdf.ts:30` checks `new Blob([html]).size`, then posts `JSON.stringify({html,title,format})`, which is strictly larger. | **CONFIRMED** |
| 9 | `/healthz` returns `status:'ok'` when the print service cannot serve | `server/index.ts:53` hardcodes `status: 'ok'`; a poisoned `browserPromise` renders as `browser:'idle'`, indistinguishable from a cold start. Compounds finding 2 — the container passes liveness forever. | **CONFIRMED** |
| 11 | Header title escaped *then* truncated, so it can cut mid-entity | `server/pdf.ts:225` — `escapeHtml(title).slice(0, 120)`. | **CONFIRMED** |
| 13 | Shutdown failure leaves the process hung with an unhandled rejection | `server/index.ts:129` — `void close(...)`; `close` awaits twice before `process.exit(0)`, with no catch and no re-entry guard. | **CONFIRMED** |
| 7, 10, 12 | Scroll-timing, arrow-key/table focus, drop-cap past a raw node | Consistent with the quoted code; behavioural, not re-run. | **PLAUSIBLE** |

### Arm B post-verification tally

| | Count |
|---|---|
| Confirmed, with the reviewer's own reproduction | 3 |
| Confirmed by my check | 6 |
| Plausible, consistent with the code, not re-run | 4 |
| **Refuted** | **0** |
| **Fabricated / non-existent code** | **0** |

## The cross-arm result that matters most

**Arm B finding 3 is something Arm A structurally could not produce.** `printSchema` *was* in the
security specialist's retrieved bundle — the bundle header reads
`## const: printSchema — src/pipeline/sanitize.ts:172-180`. The specialist read it, and reasoned
about its `src: ['data','blob']` restriction as a live control (finding S6). It is not live. It is
never imported.

Retrieval hands you the code. It cannot hand you *the absence of callers*. You cannot grep for
"who imports this" from inside a bundle — and no amount of extra retrieved context fixes that,
because the evidence needed is a negative result over the whole repo.

This is the single cleanest illustration of the architectural difference between the two arms, and
it cuts against the arm with the richer context.

---

## Addendum — what fixing the findings revealed

Both confirmed findings were then actually fixed. Implementing the fixes required reproducing the
defects precisely, and that surfaced errors in **both** arms that the earlier verification missed.
This section is the most important part of this document, because it shows that "confirmed" is a
weaker word than it looks.

### The `className` finding: right conclusion, wrong mechanism (both arms)

Measured by sweeping every one of the 56 permitted tags through the sanitizer:

```
before fix   arbitrary class KEPT on 43 tags, STRIPPED on 13
after  fix   arbitrary class KEPT on  0 tags, STRIPPED on 56
```

The 43 leaking tags include `h1`, `h3`–`h6`, `em`, `strong`, `table`, `img`, `figure`,
`figcaption`, `details`, `summary`, `sub`, `sup`. So the **substance** of the finding is real and
the fix is worth making.

But the mechanism each arm gave was wrong:

- **Arm B (#4) claimed** *"the `code`/`pre`/`span`/`div` allowlists at lines 100-105 are never
  consulted."* **False.** Those allowlists *are* consulted and they *do* strip: `<p class="evil">`
  and `<div class="evil">` come back with an empty class list. The 13 tags that correctly strip are
  exactly the ones with a narrow `className` rule — six from this project, the rest inherited from
  the upstream GitHub schema.
- **Arm B's reproduction proved the symptom, not the cause.** It showed a forged
  `<pre class="mermaid">` surviving sanitization and being drawn as a real diagram, and attributed
  that to the bare `className`. It is not: `pre` *explicitly* allows `'mermaid'` via
  `classes(CODE_LANGUAGE_PATTERN, 'mermaid')`. That forgery still works after the fix. Running the
  code proved something true and then drew a false inference from it.
- **Arm A (S3) was more accurate.** It said the gap is *"unconditional for the un-narrowed tags"*
  and explicitly flagged the merge-order question for the narrowed ones as something it could not
  resolve from its bundle. That is exactly right — and it got there without being able to run
  anything, by reasoning from the file's own `inheritedExcept` doc comment.

**A finding can be confirmed, fixed, and still have been explained wrongly by the reviewer that
found it.** Reproduction is strong evidence of *a* defect, not proof of *which* defect.

### A separate real issue neither arm identified

The marker classes the downstream plugins key off — `mermaid` on `pre`, the `markdown-alert*` set on
`div`/`p`/`blockquote` — are reachable from **raw HTML inside user markdown**, not just from real
fences and real callouts. After the fix:

```
ATTACK forged mermaid  -> mermaid | language-mermaid     (still passes)
ATTACK spoofed alert   -> markdown-alert ...             (still passes)
```

Mermaid runs at `securityLevel: 'strict'`, so this is diagram and callout **spoofing**, not script
execution. It is a design question — the allowlist cannot currently distinguish a class the
markdown pipeline generated from one an author typed in raw HTML. Flagged, not fixed; it is beyond
the scope of the two findings.

### The `printSchema` finding: both arms understated it

Arm B correctly found `printSchema` was dead code and framed the fix as wiring it up. **It cannot be
wired up.** `printSchema` extends `sanitizeSchema`, which by design forbids `style=`, `<svg>` and
`<math>` — exactly the trusted output KaTeX, Shiki and Mermaid generate *after* the boundary.
Measured on a representative export:

```
BEFORE printSchema: {"katex":true, "styles":true, "shiki":true, "len":1297}
AFTER  printSchema: {"katex":false,"styles":false,"shiki":false,"len":499}
```

It strips the maths, the highlighting and every inline style, cutting the document by 62%. Applying
it would produce a blank-looking PDF. That is almost certainly *why* it was never imported.

- **Arm B** got the defect right and the remedy wrong.
- **Arm A** (S6) reasoned about `printSchema`'s `src: ['data','blob']` restriction as a live,
  applicable control, and argued about a protocol-relative URL slipping past it. The restriction
  was neither live nor applicable.

The resolution taken: delete the schema, and replace it with a comment recording why a post-hoc
sanitizer is the wrong control for this pipeline and which controls actually constrain the print
path. The README's security table turned out to be **already accurate** — it lists only the five
controls that genuinely exist. The false claim lived solely in the code comment.

### Fix verification

| Gate | Result |
|---|---|
| Arbitrary-class leak | 43 tags → **0** |
| Legitimate classes preserved | footnotes, `sr-only`, `data-footnote-backref`, `contains-task-list`, `task-list-item`, `language-*`, `markdown-alert*` — all intact |
| Unit tests | **133 passed** (was 121; 12 added — 8 negative, 4 positive) |
| Typecheck | clean (`strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`) |
| Lint | clean, 0 warnings |
| Build | client + server both build |

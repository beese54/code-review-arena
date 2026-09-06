# Requirements Gap Agent — findings

## Acceptance criteria checklist

Verdicts are against the 30 retrieved chunks in `requirements.md` only. "Not visible" means the
relevant implementation was not in my bundle — it is explicitly **not** an accusation.

| # | Criterion (source) | Verdict |
|---|---|---|
| 0.1–0.4 | Typecheck / lint / build / test gates (DoD L0) | Not visible |
| 0.5–0.6 | Container serves shell on :8080; `/healthz` reports browser status (DoD L0) | Not visible |
| 0.7 | Fonts served from origin, never a third party (DoD 0.7; README "zero third-party requests") | Not visible |
| 1.1 | Ordering: frontmatter `order` → index names → numeric prefix → depth → natural alpha (DoD 1.1, spec `ordering.rules`) | Not visible (only `computeSortKey({path, order})` call site retrieved) |
| — | Ordering applied as a composite sort key, not a comparator cascade (spec `ordering.note`) | Satisfied — `sortKey` is a string on `MarkdownDoc`, "sorting is a plain string compare" |
| 1.2 | 250+ file tree walked with zero dropped entries (DoD 1.2) | Not visible |
| 1.3 | Relative inter-doc links resolve to in-app doc ids (DoD 1.3) | Not visible (`ctx.resolveLink` is passed to `rehypeAssets`; body not retrieved) |
| 1.4 | Images register in AssetMap under normalised relative paths (DoD 1.4) | Not visible |
| 1.5 | Oversized / over-count drops rejected with the **actual measured size** in the message (DoD 1.5, spec `errorBehaviour.oversizedDrop`) | Not visible for ingest; **Satisfied** for the PDF-side analogue (`ExportTooLargeError` names the measured MB) |
| 1.6 | A single unparseable file does not fail the set (DoD 1.6) | Satisfied — `failedDoc()` returns a `MarkdownDoc` with `error` set; `renderDocument` early-returns an empty result |
| — | `errorBehaviour.unparseableFile`: appears in the index **marked as failed** | Satisfied — `IndexSidebar` adds `is-failed` on `doc.error` |
| — | `errorBehaviour.unsupportedFile`: recorded in `DocumentSet.skipped` with a reason, never silently discarded | **GAP (R5)** — recorded, but only the first 20 are surfaced, with no truncation indicator |
| — | `errorBehaviour.missingImage`: styled placeholder figure naming the missing path | Not visible |
| — | `errorBehaviour.noMarkdownFound`: explicit empty state | Not visible |
| 2.1 | GFM tables, footnotes, task lists, strikethrough (DoD 2.1) | Satisfied — `remarkGfm` in the chain |
| 2.2 | `> [!NOTE]` callouts render as admonitions (DoD 2.2) | Satisfied — `remarkAlert` in the chain |
| 2.3 | KaTeX inline + display math (DoD 2.3) | Satisfied — `remarkMath` + `rehypeKatex` |
| 2.4 | Shiki highlights code and the bundle excludes the Oniguruma WASM (DoD 2.4) | Satisfied — `createJavaScriptRegexEngine` is the engine; no WASM engine imported |
| 2.5 | `<script>`, `onerror=`, `javascript:`, `<iframe>` stripped (DoD 2.5) | Not visible (`sanitizeSchema` body not retrieved) |
| 2.6 | KaTeX/Shiki output survives (trust-boundary ordering) (DoD 2.6) | Satisfied — sanitizer sits immediately after `rehypeRaw`, before katex/shiki |
| — | Pipeline plugin order exactly as listed (spec `pipeline.order`) | **GAP (R4)** — four post-boundary plugins in the code are absent from the specified order |
| — | Trust-boundary invariant: "Nothing user-controlled may be introduced after rehype-sanitize" (spec `pipeline.invariant`) | **GAP (R4)** — `rehypeAssets` writes user-derived `src`/`href` values after the boundary and is not among the three trusted generators the invariant names |
| 2.7 | Malformed fixture repairs to clean hierarchy (DoD 2.7) | Not visible (individual repair function bodies not retrieved) |
| 2.8 | Repairs reported, never silent; `RepairNote` count matches applied changes (DoD 2.8, spec `repair.philosophy`) | **GAP (R2, R3)** — see findings |
| — | `repair.rules` = exactly the five named rules; `duplicate-h1` **demotes** subsequent H1s (spec `repair.rules`; README "Five rules") | **GAP (R3)** — `dropRedundantTitle` is a sixth, removal-based behaviour with no matching `RepairRule` |
| 3.1 | Multi-file set navigable via the index sidebar | Satisfied — `IndexSidebar` renders every doc with `onOpenDoc` |
| 3.2 | Active-section tracking follows scroll | Satisfied — `useActiveHeading(headings)` drives `is-active` / `aria-current` |
| 3.3 | Fully keyboard operable, visible focus | Not visible (CSS/focus styles not retrieved) |
| 3.4 | No horizontal scroll 360px → 2560px | Not visible |
| 3.5 | Zero serious/critical axe violations | Not visible |
| 3.6 | All motion suppressed under `prefers-reduced-motion` | Not visible |
| 4.1 | Standalone HTML opens correctly with the network disabled (DoD 4.1, README "opens correctly with the network disabled") | Not visible in full — `inlineImages` + `collectCss` are called, but `collectCss`'s font handling was not retrieved |
| 4.2 | PDF has running heads and folio numbers (DoD 4.2) | Satisfied — `displayHeaderFooter: true` with `headerTemplate(title)` and `FOOTER_TEMPLATE` |
| 4.3 | Mermaid diagrams appear as SVG in the PDF (settle-before-serialise) (DoD 4.3) | Satisfied — `await whenDiagramsSettled()` then `copyRenderedDiagrams` / `drawDiagramsIn` before serialising |
| — | `POST /api/export/pdf` request body contract incl. optional `margin` (spec `api`) | **GAP (R1)** — `margin` is accepted by contract but hardcoded in the renderer; undocumented `landscape` accepted instead |
| — | `format: 'A4' \| 'Letter'`, default A4 (spec `api`) | Satisfied — `request.format ?? 'A4'` server-side, `format = 'A4'` client-side |
| — | 413 on oversized body (spec `api.errors`, DoD 4.6) | Satisfied client-side (`ExportTooLargeError` pre-check + 413 message); server `bodyLimit` wiring Not visible |
| — | 429 with `Retry-After` on concurrency saturation (spec `api.errors`, DoD 4.7) | Shedding Satisfied (`BusyError` when `pendingCount > concurrency * 4`); the `Retry-After` header itself Not visible |
| — | 503 browser unavailable / 504 render deadline with "export the standalone HTML instead" message (spec `api.errors`, `errorBehaviour.pdfTimeout`) | Not visible (route handler not retrieved) |
| 4.4 | `file:///etc/passwd` reads nothing (DoD 4.4) | Satisfied in principle — `javaScriptEnabled: false` + `await harden(context)`; `harden`'s route policy Not visible |
| 4.5 | Internal-IP / `169.254.169.254` aborted (DoD 4.5) | Not visible (`harden` body not retrieved) |
| 4.8 | Container runs as non-root | Not visible |
| — | `limits.pdfBodyLimitBytes` = 20 MB enforced (spec `limits`) | Satisfied — `LIMITS.pdfBodyLimitBytes` used, not a literal |
| — | `limits.pdfRenderDeadlineMs` = 30000 (spec `limits`) | Not visible — `RENDER_DEADLINE_MS` is referenced but its value was not retrieved |
| — | `limits.maxTotalBytes` / `maxFiles` / `maxSingleFileBytes` (spec `limits`, README "200 MB / 2000 files / 10 MB per file") | Not visible |
| — | Schema `MarkdownDoc` (spec `schemas`) | Satisfied — field-for-field match in `src/types/domain.ts` |
| — | Schema `DocumentSet` (spec `schemas`) | Satisfied — field-for-field match |
| — | Schema `RenderResult` (spec `schemas`) | Satisfied — `renderDocument` returns exactly the seven specified fields |
| — | Schema `RepairNote` / `RepairRule` union (spec `schemas`) | Satisfied as a type; see R3 for the behaviour that has no rule |
| — | Schema `AssetRef` (spec `schemas`) | Not visible |
| — | Schema `Heading` — slug unique within a document, depth 1..6 post-repair (spec `schemas`) | Not visible (`headingPlugin` body not retrieved) |
| — | Architecture: server never parses markdown (spec `architecture.principle`) | Satisfied — `server/pdf.ts` only calls `page.setContent(request.html)` |
| G.1–G.4 | Global gates (tests, typecheck, per-layer audit, atomic commits) | Not visible |

## Context used

- `task-context.md` — `definition_of_done.md` in full (L0–L4 + global gates), and `specification.json`:
  `schemas`, `ordering`, `repair`, `pipeline`, `api`, `errorBehaviour`, `limits`.
- `standards.md` — the README section "Public claims the code must live up to", specifically
  "What it does" (five repair rules, two exports), "The trust boundary", "Limits and non-goals".
- `requirements.md` chunks relied on: `renderPdf` (`server/pdf.ts:134-198`), `requestPdf` and
  `PdfOptions` (`src/export/pdf.ts:22-58`), `buildStandalone` (`src/export/standalone.ts:105-174`),
  `renderDocument` (`src/pipeline/render.ts:138-207`), `remarkRepair` + `RepairOptions`
  (`src/pipeline/plugins/remark-repair.ts:27-35, 270-280`), `IndexSidebar`
  (`src/reader/IndexSidebar.tsx:21-99`), `readDoc`/`failedDoc` (`src/ingest/docset.ts:178-225`),
  the domain interfaces (`src/types/domain.ts`), and the Shiki/Mermaid plugins.

## Findings

### R1. The PDF endpoint's specified optional `margin` field is never honoured; margins are hardcoded

- **Severity:** high
- **Category:** requirements-gap
- **Requirement (verbatim):** from `specification.json` → `api` → `POST /api/export/pdf` → `request.body`:
  > `"margin": "{ top, right, bottom, left } CSS lengths - optional"`
- **Evidence:** `server/pdf.ts:134-198` — the only `margin` in the whole render path is a literal;
  `request.margin` is never read:
  ```ts
  return page.pdf({
    format: request.format ?? 'A4',
    landscape: request.landscape ?? false,
    ...
    margin: { top: '22mm', right: '18mm', bottom: '20mm', left: '22mm' },
  })
  ```
  And the client type that builds the request has no field to send it with —
  `src/export/pdf.ts:22-26`:
  ```ts
  export interface PdfOptions {
    readonly html: string
    readonly title: string
    readonly format?: 'A4' | 'Letter'
  }
  ```
- **The gap:** The published request contract advertises four caller-controllable page margins.
  The server hardcodes them and the client cannot even express them. Note also
  `preferCSSPageSize: true` on the same call, which makes any `@page` size/margin rule in the
  posted HTML take precedence — so even if `request.margin` were plumbed through it would be
  overridden for documents that set `@page`. Conversely, `landscape` is read from the request
  (`request.landscape ?? false`) but appears nowhere in the specified body, so the implemented
  surface and the documented surface diverge in both directions.
- **Why it matters:** Any consumer written against `specification.json` — including the repo's own
  future export UI, or the adversarial/e2e harness — will send `margin` and silently get 22/18/20/22mm.
  A silently ignored request field is the worst failure mode of an API contract: it looks like it worked.
- **Suggested fix:** Either (a) read it — `margin: request.margin ?? DEFAULT_MARGIN`, validate the
  four values as CSS lengths in the route schema, and drop `preferCSSPageSize` to `false` when a
  caller margin is supplied; or (b) remove `margin` from `specification.json`, document the fixed
  margins as part of the print design, and add `landscape` to the documented body.
- **Confidence:** high
- **Context limitation:** The Fastify route handler and the `PdfRequest` type were not in my bundle.
  If the route rejects unknown fields, `margin` would 400 rather than be ignored — that is still a
  contract gap, only a louder one. The retrieved `renderPdf` body is complete (lines 134-198) and
  contains no other margin reference.

### R2. The standalone HTML export drops every repair note, so the exported file shows altered content with no disclosure

- **Severity:** medium
- **Category:** requirements-gap
- **Requirement (verbatim):** from `specification.json` → `repair.philosophy`:
  > "Never silently alter the user's document. Every change is recorded as a RepairNote and surfaced in the UI as an inspectable list."

  and from `README.md` → "What it does":
  > "Every change is listed in the document with its line number and its before/after text, because silently editing someone's writing is not acceptable behaviour for a reader."

  and `README.md` under the repairs screenshot:
  > "Every repair is listed in the document, with the line, the text before and the text after."
- **Evidence:** `src/export/standalone.ts:105-174` — each exported article is composed of exactly a
  title header plus the rendered body; `result.repairs` is never touched:
  ```ts
  const body = document.createElement('div')
  body.className = 'prose'
  // Pipeline output, already past the trust boundary.
  body.innerHTML = result.html

  article.append(header, body)
  host.append(article)
  ```
  `RenderResult.repairs` is a sibling of `html`, not embedded in it — `src/pipeline/render.ts:138-207`
  returns `{ docId, html, headings, repairs, mermaidBlocks, wordCount, readingMinutes }`, with
  `repairs` filled by the `remarkRepair` sink and never written into the stringified tree.
- **The gap:** The export contains the *repaired* rendering — demoted headings, renormalised list
  nesting, unified bullet markers, closed emphasis runs — and none of the notes that say so. The
  one artefact a user actually sends to someone else is precisely the one where the alterations
  become invisible. The README states the disclosure as a moral commitment ("not acceptable
  behaviour for a reader"), not as a screen-only affordance.
- **Why it matters:** A reader who receives the exported HTML sees a document that differs from the
  author's source with no indication that anything was changed. That is the exact outcome the
  stated philosophy exists to prevent.
- **Suggested fix:** In `buildStandalone`, when `result.repairs.length > 0`, append a
  `<details class="repairs">` section to the article built from `result.repairs`
  (`rule`, `line`, `before`, `after`, `detail`) — reusing whatever markup the reader's repairs panel
  renders — so the export carries the same disclosure the screen does.
- **Confidence:** medium-high
- **Context limitation:** I could not retrieve `DocumentView.tsx`'s body, so I am inferring that the
  on-screen repairs panel lives in the React component rather than in `result.html`. `DocumentViewProps`
  taking the whole `result` supports that. If repairs were somehow injected into `result.html` by a
  plugin, this finding collapses — but no plugin in the visible `renderDocument` chain does so.

### R3. `dropRedundantTitle` is a sixth repair behaviour, and it removes rather than demotes — neither matches the five specified rules

- **Severity:** medium
- **Category:** requirements-gap
- **Requirement (verbatim):** from `specification.json` → `repair.rules`:
  > `"duplicate-h1": "The first H1 becomes the document title; subsequent H1s are demoted to H2 and everything below shifts accordingly."`

  and the closed union in the same file, `schemas.RepairNote.rule`:
  > `"'heading-skip' | 'duplicate-h1' | 'list-nesting' | 'mixed-markers' | 'unbalanced-emphasis'"`

  and `README.md`:
  > "**Repairs messy markdown, and says so.** Five rules — skipped heading levels, duplicate H1s, broken list nesting, mixed bullet markers and unbalanced emphasis"
- **Evidence:** `src/pipeline/plugins/remark-repair.ts:270-280` runs a transform that corresponds to
  none of the five:
  ```ts
  // Before repairHeadings, so the hierarchy is normalised against what will
  // actually be rendered rather than against a heading about to be removed.
  dropRedundantTitle(tree, opts)
  repairHeadings(tree, opts)
  ```
  Its purpose is stated in `RepairOptions` at `src/pipeline/plugins/remark-repair.ts:27-35`:
  ```ts
  /**
   * The document title as resolved by ingest, which the reader already shows
   * in its own title block. A leading H1 repeating it is printed twice.
   */
  readonly title?: string
  ```
- **The gap:** The specified `duplicate-h1` rule *preserves* every H1 by demoting the later ones.
  `dropRedundantTitle` **deletes** a heading outright ("a heading about to be removed"), and it does
  so for the *first* H1 on a criterion the spec never mentions — equality with the ingest-resolved
  title. Because `RepairRule` is a closed five-member union, any note this emits must be filed under
  a rule whose written definition describes different behaviour (presumably `duplicate-h1`), so DoD
  2.8's "RepairNote count matches applied changes" can be satisfied while the note misdescribes what
  happened. If it emits no note at all, the removal is a silent alteration, which contradicts
  `repair.philosophy` directly.
- **Why it matters:** Deleting content is the most consequential thing this pipeline does to a user's
  document, and it is the one transform with no written specification. Reviewers checking "five rules,
  five behaviours" against the code will not find this one.
- **Suggested fix:** Add a sixth rule to `specification.json` `repair.rules` and to the `RepairRule`
  union — e.g. `'redundant-title'`: "A leading H1 identical to the resolved document title is removed
  from the body, because the reader prints the title separately" — and confirm `dropRedundantTitle`
  pushes a `RepairNote` under it. If the intent was the spec's demotion behaviour, change the code to
  demote instead of remove.
- **Confidence:** medium
- **Context limitation:** Only the orchestrator and the options interface were retrieved, not
  `dropRedundantTitle`'s body. If it in fact demotes and the comment's "removed" is loose wording,
  the severity drops to low (still an unlisted sixth behaviour that must borrow another rule's name).

### R4. Four plugins run after the trust boundary that the specified pipeline order and invariant do not cover

- **Severity:** medium
- **Category:** requirements-gap
- **Requirement (verbatim):** from `specification.json` → `pipeline.order` (the complete list):
  > `"rehype-sanitize(schema)   <-- TRUST BOUNDARY", "rehype-katex", "rehypeShiki (local hast visitor)", "rehypeMermaidPlaceholder (local)", "rehype-stringify"`

  and `pipeline.invariant`:
  > "Nothing user-controlled may be introduced after rehype-sanitize. KaTeX, Shiki and Mermaid markup is generated by us, from already-sanitised source, and is therefore trusted."
- **Evidence:** `src/pipeline/render.ts:138-207` — four further plugins sit between the mermaid
  placeholder and `rehype-stringify`:
  ```ts
  .use(rehypeShiki, { highlighter })
  .use(rehypeMermaid, { sink: mermaidBlocks })
  .use(rehypeAssets, { doc, assets: ctx.assets, resolveLink: ctx.resolveLink })
  .use(headingPlugin(headings))
  .use(tableWrapPlugin())
  .use(openingParagraphPlugin())
  .use(rehypeStringify, { allowDangerousHtml: true })
  ```
- **The gap:** Two distinct shortfalls against one requirement. (a) The documented order is not the
  implemented order — `specification.json` names nine post-parse stages, the code runs thirteen, and
  the README's own diagram (`→ katex → shiki → mermaid → assets → stringify`) already disagrees with
  `specification.json` on this point, so the two blueprint documents are inconsistent with each other.
  (b) More substantively, `rehypeAssets` is handed `assets`, `doc` and `resolveLink` and rewrites
  `src`/`href` attributes from user-supplied paths — content derived from the drop, introduced after
  the sanitizer, and it is not one of the three generators the invariant declares trusted. The
  invariant's justification ("markup is generated by us") does not extend to attribute values taken
  from user input, however benign a `blob:` URL from the AssetMap is in practice.
- **Why it matters:** The trust-boundary invariant is described in both the spec and the README as
  "the load-bearing decision". An invariant that enumerates three trusted post-boundary producers
  while the code has four is not enforceable by review — the next plugin added after the sanitizer
  will look just as normal as `rehypeAssets` does.
- **Suggested fix:** Update `pipeline.order` in `specification.json` to the actual thirteen stages,
  and restate the invariant in terms of what is *allowed* rather than an enumeration — e.g. "after
  the sanitizer, plugins may only emit markup from a fixed vocabulary and may only set attribute
  values through the AssetMap/link-resolver, which return `blob:` and in-app hash URLs exclusively."
  Then have `rehypeAssets` assert that invariant on the values it writes.
- **Confidence:** high for (a), medium for (b)
- **Context limitation:** `rehype-assets.ts` was not in my bundle, so I judge it by its call-site
  arguments only. If it whitelists its output scheme internally, (b) is documentation drift rather
  than a real hole; (a) stands either way.

### R5. The skipped-files disclosure is truncated at 20 with no indication that anything is hidden

- **Severity:** low
- **Category:** requirements-gap
- **Requirement (verbatim):** from `specification.json` → `errorBehaviour.unsupportedFile`:
  > "Recorded in DocumentSet.skipped with a reason; never silently discarded."
- **Evidence:** `src/reader/IndexSidebar.tsx:21-99`:
  ```tsx
  <summary>{set.skipped.length} files skipped</summary>
  <ul>
    {set.skipped.slice(0, 20).map((s) => (
  ```
- **The gap:** With a drop near the specified `maxFiles: 2000` ceiling, the summary can read
  "1,400 files skipped" while the expanded list shows twenty entries and then simply stops — no
  "and 1,380 more", no way to reach the remaining reasons. The data model honours the requirement;
  the only surface that exposes it to a user does not, for any set with more than 20 skips.
- **Why it matters:** The stated guarantee is that a user can always find out why a file did not
  make it into their reading edition. Past twenty files, they cannot.
- **Suggested fix:** Append a `<li>` reading `+{set.skipped.length - 20} more` after the slice, or
  group the skips by reason and show counts per reason, which is more useful and stays short.
- **Confidence:** medium
- **Context limitation:** If another surface (an error panel, a console-visible export of the set)
  lists the full skip set, this is not user-visible loss. No such surface appeared in my bundle.

TOTAL FINDINGS: 5

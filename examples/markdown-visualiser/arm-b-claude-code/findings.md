# Arm B — Claude Code `/code-review high src server`

## Run metadata
- Command: /code-review high src server
- Effort level: high
- Date: 2026-09-05
- Repo HEAD: cc34345
- Files in scope: The review stated its own scope as "all of `src` and `server` (~4,265 lines of TS/TSX)". It examined 31 distinct project source files — every `.ts`/`.tsx` file under `src/` and `server/` (31 of 31; the remaining 6 files in those trees are CSS and were not opened). It additionally read 4 dependency files under `node_modules/` to verify library behaviour.

Note on scope resolution: the skill first ran `git diff @{upstream}...HEAD` and `git diff HEAD`, found both empty, and therefore reviewed the passed path target `src server` instead of a diff.

## Findings

The review produced **13 findings**. It assigned **severities** (HIGH / MEDIUM / LOW) but did **not** assign category slugs — the skill prompt scoped the pass to correctness bugs only, and no per-finding category taxonomy was emitted. The "Category" field below is therefore recorded as not assigned, rather than invented.

The `ReportFindings` tool was not available in this session; the review searched the deferred tool registry for it, did not find it, and reported the findings directly in its final message.

Order below is the order the review ranked them.

### 1. `clobberPrefix` is applied a second time, breaking every GFM footnote link
- **File:** `src/pipeline/sanitize.ts:158`
- **Category:** *(none assigned by the review)*
- **Severity or verdict:** HIGH
- **Summary:** `clobberPrefix` is applied a second time, breaking every GFM footnote link.
- **Failure scenario:** `mdast-util-to-hast` already prefixes footnote ids with `user-content-` (its `clobberPrefix` default), and it writes hrefs to match. The schema then sets `clobberPrefix: 'user-content-'` + `clobber: ['name','id']`, so `hast-util-sanitize` prefixes the *id* again while leaving the *href* alone. Reproduced with the project's own deps: `<a href="#user-content-fn-1" id="user-content-user-content-fnref-1">` pointing at `<li id="user-content-user-content-fn-1">`. Every footnote reference and back-reference in every document is a dead link. Setting `clobberPrefix: ''` restores matching ids (verified).

### 2. A single failed Chromium launch disables the print service permanently
- **File:** `server/pdf.ts:55`
- **Category:** *(none assigned by the review)*
- **Severity or verdict:** HIGH
- **Summary:** A single failed Chromium launch disables the print service permanently.
- **Failure scenario:** `browserPromise ??= launch().then(...)` — if `chromium.launch()` rejects (OOM, `/dev/shm` pressure, a transient sandbox failure), `browserPromise` holds a *rejected* promise, which is neither `null` nor `undefined`, so `??=` never retries. The `disconnected` handler that would clear it is only registered inside the success path. Every subsequent `POST /api/export/pdf` returns 503 until the process is restarted. Reset `browserPromise = null` in a `.catch` on the launch chain.

### 3. `printSchema` is dead code, and its doc comment describes a control that does not exist
- **File:** `src/pipeline/sanitize.ts:172`
- **Category:** *(none assigned by the review)*
- **Severity or verdict:** MEDIUM
- **Summary:** `printSchema` is dead code, and its doc comment describes a control that does not exist.
- **Failure scenario:** It is documented as "a second, stricter schema applied server-side before the print service hands HTML to Chromium", but `grep` finds no importer anywhere in `src/`, `server/` or `tests/` — and it lives in `src/`, unreachable from the server bundle. `server/pdf.ts:164` passes `request.html` straight into `page.setContent`. The stated defence-in-depth layer for a `/api/export/pdf` that "is not necessarily our own client" isn't wired up.

### 4. The bare `'className'` in the `'*'` bucket voids every per-tag class allowlist below it
- **File:** `src/pipeline/sanitize.ts:98`
- **Category:** *(none assigned by the review)*
- **Severity or verdict:** MEDIUM
- **Summary:** The bare `'className'` in the `'*'` bucket voids every per-tag class allowlist below it.
- **Failure scenario:** This is exactly the trap the file's own `inheritedExcept` comment documents for `src`, reproduced for classes: `hast-util-sanitize` falls back to `attributes['*']` whenever the tag-specific definition rejects a value (`lib/index.js:526`), and a bare string matches everything. Reproduced — raw HTML `<p class="totally-arbitrary-class">` and `<pre class="mermaid"><code class="language-mermaid">graph TD; A-->B;</code></pre>` both survive sanitization, and the latter is then picked up by `rehypeMermaid` and drawn as a real diagram from author-controlled raw HTML. The `code`/`pre`/`span`/`div` allowlists at lines 100-105 are never consulted.

### 5. `repairListNesting` merges sibling list items into one run-on item
- **File:** `src/pipeline/plugins/remark-repair.ts:228`
- **Category:** *(none assigned by the review)*
- **Severity or verdict:** MEDIUM
- **Summary:** `repairListNesting` merges sibling list items into one run-on item.
- **Failure scenario:** `item.children = inner.children.flatMap((child) => child.children)` lifts each inner `listItem`'s *contents*, discarding the item boundaries. Reproduced: `- - a\n  - b` renders `<ul><li><ul><li>a</li><li>b</li></ul></li></ul>` before the pass and `<ul><li>ab</li></ul>` after it. The RepairNote claims "nested items lifted to this level", but the user's two bullets are silently welded into one — which is precisely the "editing someone's writing behind their back" the module header forbids. The fix is to splice `inner.children` into the *parent list* in place of the outer item.

### 6. Two occurrences of the same diagram: only the first is ever drawn
- **File:** `src/reader/Mermaid.tsx:165`
- **Category:** *(none assigned by the review)*
- **Severity or verdict:** MEDIUM
- **Summary:** Two occurrences of the same diagram: only the first is ever drawn.
- **Failure scenario:** `rehype-mermaid.ts:61` content-hashes the id and puts it on both `id` and `data-mermaid`, so identical source yields identical ids. `currentSlot()` uses `querySelector`, which always returns the *first* match, so on the second loop iteration the freshly rendered SVG overwrites the already-drawn first slot and the second figure keeps showing raw source. Most likely in the export path, where `buildStandalone` flattens `allMermaidBlocks` across every document into one host — a shared architecture diagram repeated in two files renders once and appears as source text in the exported HTML and PDF. (It also emits duplicate DOM `id` attributes.)

### 7. Cross-document heading links land at the top of the page, not the heading
- **File:** `src/reader/Shell.tsx:42`
- **Category:** *(none assigned by the review)*
- **Severity or verdict:** MEDIUM
- **Summary:** Cross-document heading links land at the top of the page, not the heading.
- **Failure scenario:** `navigate()` calls `openDoc(docId)` then a single `requestAnimationFrame` to `document.getElementById(hash)`. For a document not already in the render cache, `useRenderedDoc` returns `pending` and the real render (`getHighlighter` → `ensureLanguages` → `unified().process`) resolves several ticks later, so at rAF time the heading does not exist and `?.scrollIntoView` is a silent no-op — while the `[activeDocId]` effect at line 107 scrolls to top. It works only for a prefetched neighbour (which resolves synchronously via the render-phase cache fallback), which makes the failure look intermittent. Scroll from an effect keyed on the rendered result instead.

### 8. The size guard measures the wrong thing, so the 413 it exists to prevent still happens
- **File:** `src/export/pdf.ts:30`
- **Category:** *(none assigned by the review)*
- **Severity or verdict:** MEDIUM
- **Summary:** The size guard measures the wrong thing, so the 413 it exists to prevent still happens.
- **Failure scenario:** `new Blob([html]).size` is the HTML byte count, but the request body is `JSON.stringify({html, title, format})`, which is strictly larger — every `"` in the export (one per HTML attribute) becomes `\"`. A ~19.8 MB export passes the client check and is rejected by Fastify's 20 MB `bodyLimit`; `requestPdf` then surfaces Fastify's own `error` field, so the user gets "Payload Too Large" instead of the friendly `ExportTooLargeError` message. Measure the serialized body, or budget headroom.

### 9. `/healthz` reports `status: 'ok'` even when the print service cannot serve anything
- **File:** `server/index.ts:53`
- **Category:** *(none assigned by the review)*
- **Severity or verdict:** MEDIUM
- **Summary:** `/healthz` reports `status: 'ok'` even when the print service cannot serve anything.
- **Failure scenario:** `browserHealthy()` swallows a rejected `browserPromise` and returns `false`, which is rendered as `browser: 'idle'` — indistinguishable from a healthy cold start. Combined with the poisoned-promise bug above, a container stuck returning 503 on every export passes its liveness probe indefinitely and is never restarted.

### 10. The global arrow-key handler makes wide tables unscrollable by keyboard
- **File:** `src/reader/Shell.tsx:71`
- **Category:** *(none assigned by the review)*
- **Severity or verdict:** LOW
- **Summary:** The global arrow-key handler makes wide tables unscrollable by keyboard.
- **Failure scenario:** `ArrowRight`/`ArrowLeft` call `event.preventDefault()` unconditionally (the `INPUT|TEXTAREA|SELECT` guard doesn't cover them). `tableWrapPlugin` (`src/pipeline/render.ts:105`) deliberately gives each table wrapper `tabIndex: 0` and `role: 'region'` so it can be scrolled horizontally with the keyboard; focusing one and pressing → navigates to the next document instead of scrolling the table. Skip the handler when `event.target` is inside `.table-wrap`.

### 11. The header title is escaped and *then* truncated, so it can be cut mid-entity
- **File:** `server/pdf.ts:225`
- **Category:** *(none assigned by the review)*
- **Severity or verdict:** LOW
- **Summary:** The header title is escaped and *then* truncated, so it can be cut mid-entity.
- **Failure scenario:** `escapeHtml(title).slice(0, 120)` operates on the escaped string, where one source character can expand to six (`&#39;`). A title whose 120th escaped character falls inside an entity leaves `&#3` in the PDF header, rendered as literal text. Slice before escaping.

### 12. `openingParagraphPlugin` gives a drop cap to a document that doesn't open on prose
- **File:** `src/pipeline/render.ts:116`
- **Category:** *(none assigned by the review)*
- **Severity or verdict:** LOW
- **Summary:** `openingParagraphPlugin` gives a drop cap to a document that doesn't open on prose.
- **Failure scenario:** The loop `continue`s on any non-element node, which is needed for the whitespace text nodes — but `rehypeShiki` runs earlier and replaces highlighted `<pre>` blocks with `{type: 'raw'}` nodes (`rehype-shiki.ts:142`). A document that opens with a fenced code block therefore skips past it and applies `.opening` to the first paragraph *after* the code, contradicting the stated rule at line 129-131. Treat `raw` nodes as a stop condition.

### 13. A failure during shutdown leaves the process hung with an unhandled rejection
- **File:** `server/index.ts:129`
- **Category:** *(none assigned by the review)*
- **Severity or verdict:** LOW
- **Summary:** A failure during shutdown leaves the process hung with an unhandled rejection.
- **Failure scenario:** `process.on('SIGTERM', () => void close('SIGTERM'))` discards the promise; if `app.close()` or `closeBrowser()` rejects, `process.exit(0)` is never reached and there is no handler. Repeated signals also re-enter `close` concurrently. Wrap the body in try/finally around `process.exit`, and guard against re-entry.
## Raw output

```
No `ReportFindings` tool is available in this session (I searched the deferred tool registry; it isn't registered), so the findings are reported directly below.

## Scope

`git diff @{upstream}...HEAD` and `git diff HEAD` are both empty — the branch is fully pushed and the tree is clean (only the untracked `code-review-comparison/` scratch dir). I therefore reviewed the named target: all of `C:\Users\allti\OneDrive\Documents\markdown_visualiser\src` and `C:\Users\allti\OneDrive\Documents\markdown_visualiser\server` (~4,265 lines of TS/TSX). Findings 1, 4 and 5 were reproduced by running the real pipeline against the project's own `node_modules`.

## Findings

**`src/pipeline/sanitize.ts:158` — HIGH. `clobberPrefix` is applied a second time, breaking every GFM footnote link.** `mdast-util-to-hast` already prefixes footnote ids with `user-content-` (its `clobberPrefix` default), and it writes hrefs to match. The schema then sets `clobberPrefix: 'user-content-'` + `clobber: ['name','id']`, so `hast-util-sanitize` prefixes the *id* again while leaving the *href* alone. Reproduced with the project's own deps: `<a href="#user-content-fn-1" id="user-content-user-content-fnref-1">` pointing at `<li id="user-content-user-content-fn-1">`. Every footnote reference and back-reference in every document is a dead link. Setting `clobberPrefix: ''` restores matching ids (verified).

**`server/pdf.ts:55` — HIGH. A single failed Chromium launch disables the print service permanently.** `browserPromise ??= launch().then(...)` — if `chromium.launch()` rejects (OOM, `/dev/shm` pressure, a transient sandbox failure), `browserPromise` holds a *rejected* promise, which is neither `null` nor `undefined`, so `??=` never retries. The `disconnected` handler that would clear it is only registered inside the success path. Every subsequent `POST /api/export/pdf` returns 503 until the process is restarted. Reset `browserPromise = null` in a `.catch` on the launch chain.

**`src/pipeline/sanitize.ts:172` — MEDIUM. `printSchema` is dead code, and its doc comment describes a control that does not exist.** It is documented as "a second, stricter schema applied server-side before the print service hands HTML to Chromium", but `grep` finds no importer anywhere in `src/`, `server/` or `tests/` — and it lives in `src/`, unreachable from the server bundle. `server/pdf.ts:164` passes `request.html` straight into `page.setContent`. The stated defence-in-depth layer for a `/api/export/pdf` that "is not necessarily our own client" isn't wired up.

**`src/pipeline/sanitize.ts:98` — MEDIUM. The bare `'className'` in the `'*'` bucket voids every per-tag class allowlist below it.** This is exactly the trap the file's own `inheritedExcept` comment documents for `src`, reproduced for classes: `hast-util-sanitize` falls back to `attributes['*']` whenever the tag-specific definition rejects a value (`lib/index.js:526`), and a bare string matches everything. Reproduced — raw HTML `<p class="totally-arbitrary-class">` and `<pre class="mermaid"><code class="language-mermaid">graph TD; A-->B;</code></pre>` both survive sanitization, and the latter is then picked up by `rehypeMermaid` and drawn as a real diagram from author-controlled raw HTML. The `code`/`pre`/`span`/`div` allowlists at lines 100-105 are never consulted.

**`src/pipeline/plugins/remark-repair.ts:228` — MEDIUM. `repairListNesting` merges sibling list items into one run-on item.** `item.children = inner.children.flatMap((child) => child.children)` lifts each inner `listItem`'s *contents*, discarding the item boundaries. Reproduced: `- - a\n  - b` renders `<ul><li><ul><li>a</li><li>b</li></ul></li></ul>` before the pass and `<ul><li>ab</li></ul>` after it. The RepairNote claims "nested items lifted to this level", but the user's two bullets are silently welded into one — which is precisely the "editing someone's writing behind their back" the module header forbids. The fix is to splice `inner.children` into the *parent list* in place of the outer item.

**`src/reader/Mermaid.tsx:165` — MEDIUM. Two occurrences of the same diagram: only the first is ever drawn.** `rehype-mermaid.ts:61` content-hashes the id and puts it on both `id` and `data-mermaid`, so identical source yields identical ids. `currentSlot()` uses `querySelector`, which always returns the *first* match, so on the second loop iteration the freshly rendered SVG overwrites the already-drawn first slot and the second figure keeps showing raw source. Most likely in the export path, where `buildStandalone` flattens `allMermaidBlocks` across every document into one host — a shared architecture diagram repeated in two files renders once and appears as source text in the exported HTML and PDF. (It also emits duplicate DOM `id` attributes.)

**`src/reader/Shell.tsx:42` — MEDIUM. Cross-document heading links land at the top of the page, not the heading.** `navigate()` calls `openDoc(docId)` then a single `requestAnimationFrame` to `document.getElementById(hash)`. For a document not already in the render cache, `useRenderedDoc` returns `pending` and the real render (`getHighlighter` → `ensureLanguages` → `unified().process`) resolves several ticks later, so at rAF time the heading does not exist and `?.scrollIntoView` is a silent no-op — while the `[activeDocId]` effect at line 107 scrolls to top. It works only for a prefetched neighbour (which resolves synchronously via the render-phase cache fallback), which makes the failure look intermittent. Scroll from an effect keyed on the rendered result instead.

**`src/export/pdf.ts:30` — MEDIUM. The size guard measures the wrong thing, so the 413 it exists to prevent still happens.** `new Blob([html]).size` is the HTML byte count, but the request body is `JSON.stringify({html, title, format})`, which is strictly larger — every `"` in the export (one per HTML attribute) becomes `\"`. A ~19.8 MB export passes the client check and is rejected by Fastify's 20 MB `bodyLimit`; `requestPdf` then surfaces Fastify's own `error` field, so the user gets "Payload Too Large" instead of the friendly `ExportTooLargeError` message. Measure the serialized body, or budget headroom.

**`server/index.ts:53` — MEDIUM. `/healthz` reports `status: 'ok'` even when the print service cannot serve anything.** `browserHealthy()` swallows a rejected `browserPromise` and returns `false`, which is rendered as `browser: 'idle'` — indistinguishable from a healthy cold start. Combined with the poisoned-promise bug above, a container stuck returning 503 on every export passes its liveness probe indefinitely and is never restarted.

**`src/reader/Shell.tsx:71` — LOW. The global arrow-key handler makes wide tables unscrollable by keyboard.** `ArrowRight`/`ArrowLeft` call `event.preventDefault()` unconditionally (the `INPUT|TEXTAREA|SELECT` guard doesn't cover them). `tableWrapPlugin` (`src/pipeline/render.ts:105`) deliberately gives each table wrapper `tabIndex: 0` and `role: 'region'` so it can be scrolled horizontally with the keyboard; focusing one and pressing → navigates to the next document instead of scrolling the table. Skip the handler when `event.target` is inside `.table-wrap`.

**`server/pdf.ts:225` — LOW. The header title is escaped and *then* truncated, so it can be cut mid-entity.** `escapeHtml(title).slice(0, 120)` operates on the escaped string, where one source character can expand to six (`&#39;`). A title whose 120th escaped character falls inside an entity leaves `&#3` in the PDF header, rendered as literal text. Slice before escaping.

**`src/pipeline/render.ts:116` — LOW. `openingParagraphPlugin` gives a drop cap to a document that doesn't open on prose.** The loop `continue`s on any non-element node, which is needed for the whitespace text nodes — but `rehypeShiki` runs earlier and replaces highlighted `<pre>` blocks with `{type: 'raw'}` nodes (`rehype-shiki.ts:142`). A document that opens with a fenced code block therefore skips past it and applies `.opening` to the first paragraph *after* the code, contradicting the stated rule at line 129-131. Treat `raw` nodes as a stop condition.

**`server/index.ts:129` — LOW. A failure during shutdown leaves the process hung with an unhandled rejection.** `process.on('SIGTERM', () => void close('SIGTERM'))` discards the promise; if `app.close()` or `closeBrowser()` rejects, `process.exit(0)` is never reached and there is no handler. Repeated signals also re-enter `close` concurrently. Wrap the body in try/finally around `process.exit`, and guard against re-entry.
```

# Pattern Compliance Agent — findings

## Context used
- `server/pdf.ts:54-63` — `getBrowser` (cached launch promise)
- `server/pdf.ts:65-72` — `closeBrowser` (establishes `.catch(() => undefined)` for fire-and-forget teardown)
- `server/pdf.ts:120-132` — `harden` (route interception)
- `server/pdf.ts:134-198` — `renderPdf` (establishes `try/finally` resource discipline and typed errors `BusyError` / `RenderTimeoutError`)
- `server/pdf.ts:200-214` — `withDeadline`
- `src/reader/Mermaid.tsx:32-76` — `loadMermaid` (establishes, in a comment, the "never cache a rejected promise" rule)
- `src/reader/Mermaid.tsx:103-117` — `withTimeout`
- `src/reader/Mermaid.tsx:184-209` — `useMermaid`
- `src/state/render.ts:39-62` — `render` (establishes in-flight dedupe + failures evicted from cache)
- `src/state/render.ts:75-146` — `useRenderedDoc` (establishes the staleness-guard pattern: `live` flag *and* an id carried in state; and `void render(...).catch(() => undefined)` for fire-and-forget)
- `src/state/store.ts:28-95` — `useReader` (establishes: ingest failures become an inspectable `phase: { kind: 'error', message, code }`; object URLs owned and revoked by the set)
- `src/export/standalone.ts:14-28` — `toDataUri`
- `src/ingest/walker.ts:40-57` — `readAllEntries`
- `src/pipeline/render.ts:138-207` — `renderDocument`
- `src/types/domain.ts:21-28`, `:44-50`, `:121-133` — `Heading`, `RepairNote`, `IngestError`
- `src/pipeline/plugins/remark-repair.ts:23-25` — `RepairResult`
- `src/reader/RepairNotice.tsx:22-86` — `RepairNotice` (establishes: every automatic change is surfaced to the reader)

Written standards relied on:
- CLAUDE.md **Core Principles — "No Laziness: Find root causes. No temporary fixes."**, **"Simplicity First"**
- `specification.json` → `errorBehaviour.unsupportedFile`: *"Recorded in DocumentSet.skipped with a reason; never silently discarded"*; `repair.philosophy`: *"Never silently alter the user's document."*
- `definition_of_done.md` 1.6 (*a single unparseable file does not fail the set*), 4.1 (*standalone HTML opens correctly with the network fully disabled*), 4.7 (*saturating concurrency returns 429, not an unbounded browser spawn*)
- README architecture note: *"A server-side markdown pipeline would be a second implementation that silently drifts from the client one"*
- `tsconfig.json` `strict` + `noUncheckedIndexedAccess` + `exactOptionalPropertyTypes`; `eslint --max-warnings 0`

## Findings

### P1. `getBrowser` caches a rejected launch promise forever — the exact failure `loadMermaid` documents and guards against
- **Severity:** high
- **Category:** pattern-compliance
- **Subcategory:** error-handling
- **Evidence:** `server/pdf.ts:54-63`
```ts
export function getBrowser(): Promise<Browser> {
  browserPromise ??= launch().then((browser) => {
    // A crashed browser must not be handed out again.
    browser.on('disconnected', () => { browserPromise = null })
    return browser
  })
  return browserPromise
}
```
- **Established pattern being violated:** `src/reader/Mermaid.tsx:32-40` states the rule explicitly for the same memoised-promise idiom: *"Caching a **rejected** one would be permanent, though … On failure the slot is cleared so the next attempt genuinely retries."* — and implements it (`.catch((err) => { mermaidReady = null; throw … })`). `getBrowser` uses the identical `??=` idiom with no failure branch. The `disconnected` listener only ever attaches to a browser that *did* launch, so it cannot clear a poisoned slot.
- **Why it matters:** one transient `chromium.launch()` failure (container still warming, `/dev/shm` pressure, an OOM-killed first launch) permanently pins `browserPromise` to a rejected promise. Every subsequent `POST /api/export/pdf` re-awaits that same rejection and returns 503 for the life of the process, with no recovery short of a restart — a stateless print service that has become permanently broken by one bad moment. `closeBrowser()` is the only thing that clears the slot and nothing on the error path calls it.
- **Suggested fix:** mirror `loadMermaid`: `browserPromise ??= launch().then(…).catch((err) => { browserPromise = null; throw err })`.
- **Confidence:** high
- **Context limitation:** I cannot see the Fastify route or a healthcheck that might call `closeBrowser()` on a failed export; if such a reset exists the window narrows, but the idiom is still inconsistent with the rule the codebase wrote down for itself.

---

### P2. `harden` fires `route.continue()` / `route.abort()` with `void` and no catch — unhandled rejections on exactly the path `renderPdf` is designed to take
- **Severity:** high
- **Category:** pattern-compliance
- **Subcategory:** error-handling
- **Evidence:** `server/pdf.ts:120-132`
```ts
await context.route('**/*', (route) => {
  const url = route.request().url()
  if (ALLOWED_SCHEMES.test(url)) { void route.continue(); return }
  void route.abort('blockedbyclient')
})
```
- **Established pattern being violated:** the same file, two functions above, establishes that a teardown-racing promise must be neutralised, not merely voided — `closeBrowser` (`server/pdf.ts:99-100`) writes `await pending.catch(() => null)` and `await browser?.close().catch(() => undefined)`, and `renderPdf` (`server/pdf.ts:263`) writes `await context.close().catch(() => undefined)`. The client side agrees: `src/state/render.ts:183` uses `void render(set, next).catch(() => undefined)` — `void` is never used *without* a catch anywhere else in my bundle.
- **Why it matters:** `renderPdf`'s deadline path closes the context while requests are still in flight (`withDeadline` rejects, `finally` runs `context.close()`). Playwright then rejects the pending `route.continue()` / `route.abort()` promises with a "target closed" error that has no handler attached. Under Node's default `--unhandled-rejections=throw` that terminates the print service — i.e. one slow document can kill the process that DoD 4.7 requires to stay up and shed to 429. It is also the one place in the file where a swallowed failure is *not* deliberate.
- **Suggested fix:** `route.continue().catch(() => undefined)` and `route.abort('blockedbyclient').catch(() => undefined)`, matching the file's own idiom.
- **Confidence:** medium
- **Context limitation:** I cannot see the server bootstrap; if it installs a global `process.on('unhandledRejection')` handler the crash becomes a log line instead, and the finding drops to medium. The convention deviation stands either way.

---

### P3. `toDataUri` swallows every failure into `null`, silently dropping assets from the "works offline" export
- **Severity:** high
- **Category:** pattern-compliance
- **Subcategory:** error-handling
- **Evidence:** `src/export/standalone.ts:14-28`
```ts
async function toDataUri(url: string): Promise<string | null> {
  try {
    const response = await fetch(url)
    if (!response.ok) return null
    …
    reader.onerror = () => resolve(null)
  } catch {
    return null
  }
}
```
Three distinct failure modes — non-2xx, `FileReader` error, and any thrown exception — all collapse to the same unlabelled `null`, with the original cause discarded.
- **Established pattern being violated:** this codebase's defining convention is that nothing is degraded silently. `specification.json` → `errorBehaviour.unsupportedFile`: *"Recorded in `DocumentSet.skipped` with a reason; **never silently discarded**"*; `repair.philosophy`: *"Never silently alter the user's document. Every change is recorded as a `RepairNote` and surfaced in the UI as an inspectable list"* — implemented by the `sink: repairs` collector in `src/pipeline/render.ts:694` and rendered by `RepairNotice` (`src/reader/RepairNotice.tsx:22-86`). `errorBehaviour.missingImage` even mandates *"a styled placeholder figure naming the missing path; never a broken-image icon."* The export path has no equivalent collector.
- **Why it matters:** DoD 4.1 and the README promise *"one portable HTML file that opens correctly with the network disabled."* An asset that fails to inline produces a file that quietly fails that promise, and the user discovers it only later, offline, with no way to know which image was lost or why. That is a silent data loss in the headline feature, and it directly contradicts CLAUDE.md **"No Laziness — find root causes, no temporary fixes."**
- **Suggested fix:** thread a notice sink through the serialiser the way `remarkRepair` takes `{ sink: repairs }`, record `{ url, reason }` per failure, and surface the count in the export UI (or at minimum emit the placeholder figure the spec already mandates for missing images) instead of returning a bare `null`.
- **Confidence:** medium
- **Context limitation:** the caller of `toDataUri` is not in my bundle. If it already substitutes a placeholder and reports the failure to the user, only the loss of the original cause remains and this drops to low.

---

### P4. `useMermaid` fire-and-forgets `job.finally(...)` with no `.catch` — unhandled rejection, and a diagram that fails silently
- **Severity:** medium
- **Category:** pattern-compliance
- **Subcategory:** concurrency
- **Evidence:** `src/reader/Mermaid.tsx:203-208`
```ts
const job = drawDiagramsIn(host, blocks)
inflight.add(job)
void job.finally(() => inflight.delete(job))
```
- **Established pattern being violated:** `src/state/render.ts:183` — `for (const next of neighbours) void render(set, next).catch(() => undefined)`. The codebase's fire-and-forget form is `void <promise>.catch(...)`; `.finally()` re-throws, so `void job.finally(...)` leaves a rejected promise with no handler. `withTimeout` (`src/reader/Mermaid.tsx:103-117`) exists precisely to *reject* on a slow render, so this is a rejection the module manufactures itself.
- **Why it matters:** a mermaid render that times out produces a browser `unhandledrejection`, and — separately — the reader is left looking at raw diagram source with no explanation. `loadMermaid`'s own comment names that outcome as unacceptable (*"every later document would then reuse that failure and **silently show diagram source forever**"*), yet a per-render failure lands in the same place. Under the repairs-are-always-reported philosophy, a diagram that could not be drawn should say so.
- **Suggested fix:** `void job.catch(() => undefined).finally(() => inflight.delete(job))`, and mark the failed placeholder with a short visible note rather than leaving the source exposed.
- **Confidence:** medium
- **Context limitation:** `drawDiagramsIn` is not in my bundle. If it catches per-block internally and never rejects, the unhandled-rejection half is void; the silent-degradation half still stands.

---

### P5. The store's `ingest()` has no staleness guard, while the render layer builds an elaborate one for the same class of bug
- **Severity:** medium
- **Category:** pattern-compliance
- **Subcategory:** state-management
- **Evidence:** `src/state/store.ts:33-60`
```ts
const ingest = async (collect) => {
  try {
    set({ phase: { kind: 'reading', count: 0 } })
    const walked = await collect()
    set({ phase: { kind: 'building' } })
    …
    disposeCurrent()
    set({ set: built, activeDocId: built.docs[0]?.id ?? null, phase: { kind: 'ready' } })
```
with `onProgress: (count) => set({ phase: { kind: 'reading', count } })` wired into both entry points.
- **Established pattern being violated:** `useRenderedDoc` (`src/state/render.ts:75-146`) treats exactly this hazard as a first-class concern, using *two* mechanisms — a `live` flag in the effect cleanup and a `docId` carried inside the state object, with a documented render-time mismatch check (*"A result belonging to a different document is not this document's result"*). The store, which owns the more expensive and more interruptible async work, has neither.
- **Why it matters:** a second drop while the first is still walking produces interleaved writes: the older walk's `onProgress` callbacks keep overwriting `phase` after the newer ingest has moved to `building`, and the slower of the two `buildDocumentSet` calls wins the final `set({ set: built })`. Worse for lifecycle: `disposeCurrent()` revokes only whatever is *currently in the store*, so a `DocumentSet` that was built but overtaken never has its object URLs revoked — the leak the `disposeCurrent` doc-comment exists to prevent (*"discarding one without revoking them leaks every image for the lifetime of the page"*).
- **Suggested fix:** carry a monotonically increasing `runId` in the closure; ignore any `set(...)` — progress, success, or error — whose `runId` is not the latest, and revoke the assets of a superseded `built` set on that path.
- **Confidence:** medium
- **Context limitation:** if the dropzone component disables further drops while `phase.kind !== 'idle' | 'ready'`, concurrency is prevented at the UI layer and this becomes defence-in-depth. That component is not in my bundle.

---

### P6. `readAllEntries` rejects the whole walk when one directory read fails, against the "one bad file never fails the set" convention
- **Severity:** medium
- **Category:** pattern-compliance
- **Subcategory:** error-handling
- **Evidence:** `src/ingest/walker.ts:40-57`
```ts
const readBatch = () => {
  reader.readEntries((batch) => {
    …
  }, reject)   // ← any single directory read aborts the entire drop
}
```
- **Established pattern being violated:** DoD 1.6 — *"A single unparseable file does not fail the set"* — and `specification.json` → `errorBehaviour.unsupportedFile` (*recorded in `DocumentSet.skipped` with a reason; never silently discarded*), plus `MarkdownDoc.error: "per-file failure, does not fail the set"`. Resilience is per-entry everywhere else in the ingest contract; here it is all-or-nothing.
- **Why it matters:** one unreadable subdirectory in a 250-file tree (a permissions quirk, a symlink, a browser hiccup part-way through a large drop) discards every document the walk already collected. The user sees the generic `phase: error` with code `read-failed` and no indication of *which* directory was at fault — the opposite of the `skipped[]` reporting the spec promises.
- **Suggested fix:** capture the error for that directory, resolve with the entries gathered so far, and pass the failure up to the caller's skip list as `{ path, reason }`.
- **Confidence:** medium
- **Context limitation:** the caller (`walkDataTransfer`) is not in my bundle; if it wraps each directory recursion in its own try/catch and records a skip, the rejection never propagates and this is a non-issue.

---

### P7. `renderDocument` returns a *successful* empty result for a document it knows is broken, bypassing the `failed` render state
- **Severity:** medium
- **Category:** pattern-compliance
- **Subcategory:** error-handling
- **Evidence:** `src/pipeline/render.ts:142-150`
```ts
if (doc.error !== null) {
  return {
    docId: doc.id, html: '', headings: [], repairs: [],
    mermaidBlocks: [], wordCount: 0, readingMinutes: 0,
  }
}
```
- **Established pattern being violated:** `RenderState` already has a dedicated failure channel — `useRenderedDoc` (`src/state/render.ts:156-166`) sets `{ kind: 'failed', message }` and the reader is built to display it. Returning a well-formed `RenderResult` forces the state machine into `{ kind: 'ready' }` for a document that is not ready, and drops `doc.error`'s message on the floor entirely. It also contradicts the project-wide "never silent" stance (`repair.philosophy`, `RepairNotice`).
- **Why it matters:** the reader renders a blank sheet with a title and "1 min read" for a file that failed to parse, and the recorded reason is never shown anywhere in the document view. Under `noUncheckedIndexedAccess`-grade strictness the codebase is otherwise scrupulous about representing states honestly; this one hard-codes a lie.
- **Suggested fix:** either throw so the existing `failed` branch in `useRenderedDoc` picks it up with `doc.error` as the message, or add an explicit `error: string | null` to `RenderResult` and render a failed-document notice.
- **Confidence:** medium
- **Context limitation:** the document view component is not in my bundle. If it checks `doc.error` itself before consulting the render result, the user does see a message and this drops to low (the dead `RenderState.failed` path and the discarded message would remain).

---

### P8. The Shiki language-discovery pass is a second, drifting copy of the pipeline, joined by two `as` casts
- **Severity:** medium
- **Category:** pattern-compliance
- **Subcategory:** type-safety
- **Evidence:** `src/pipeline/render.ts:160-166`
```ts
const discovery = unified()
  .use(remarkParse).use(remarkFrontmatter, ['yaml']).use(remarkGfm)
  .use(remarkRehype, { allowDangerousHtml: true })
  .runSync(unified().use(remarkParse).parse(doc.raw) as MdastRoot) as HastRoot
await ensureLanguages(highlighter, collectLanguages(discovery))
```
- **Established pattern being violated:** the README's central architectural argument, stated for the server but general in force: *"A server-side markdown pipeline would be a second implementation that silently drifts from the client one."* Here the same file maintains two plugin chains over the same input, and they are already out of step — the tree handed to `runSync` comes from a *separate bare* `unified().use(remarkParse)` processor, so the `remarkFrontmatter` and `remarkGfm` extensions configured on `discovery` never influence the parse they are nominally there for. The two `as` casts then paper over the seam, in a project whose tsconfig turns on `strict`, `noUncheckedIndexedAccess` and `exactOptionalPropertyTypes` precisely to prevent that. CLAUDE.md: **"Simplicity First: make every change as simple as possible"**; **"No Laziness: find root causes. No temporary fixes."**
- **Why it matters:** every document is parsed twice, and the dead plugin configuration is a trap for the next developer, who will reasonably assume the discovery tree matches the real one and will add a plugin here expecting it to take effect. Any future fence-bearing construct that depends on a remark extension will be missed by discovery, and its grammar will not be loaded — code that silently renders unhighlighted (DoD 2.4).
- **Suggested fix:** derive the discovery tree from a single shared processor factory used by both passes — or drop the second pass entirely and collect fence labels with one cheap `remarkParse` + `visit` over mdast, which needs no `remarkRehype` and no casts.
- **Confidence:** medium
- **Context limitation:** `collectLanguages` only inspects `pre > code` fences (`src/pipeline/plugins/rehype-shiki.ts:65-76`), which are core CommonMark, so today's practical impact is limited to the double parse and the drift risk rather than a present bug.

---

### P9. `withTimeout` and `withDeadline` are the same function, maintained twice
- **Severity:** low
- **Category:** pattern-compliance
- **Subcategory:** layering
- **Evidence:** `src/reader/Mermaid.tsx:103-117` and `server/pdf.ts:200-214` — identical bodies, differing only in the rejection value:
```ts
const timer = setTimeout(() => reject(new Error('mermaid render timed out')), ms)
// vs
const timer = setTimeout(() => reject(new RenderTimeoutError()), ms)
```
right down to the shared `err instanceof Error ? err : new Error(String(err))` normalisation.
- **Established pattern being violated:** CLAUDE.md **"Simplicity First"** / duplicated-helper avoidance. Both also share the same subtle contract (the wrapped promise keeps running after the deadline) which is documented in neither.
- **Why it matters:** a fix to one — say, propagating an `AbortSignal` so the abandoned work actually stops — will predictably be applied to only one of them.
- **Suggested fix:** one `withDeadline<T>(promise, ms, makeError: () => Error)` in a shared module. Note the constraint: `server/` must stay free of client dependencies per the README's architecture section, so the shared home has to be a neutral utility module both may import — if that is not acceptable in this layout, leave the duplication and add a comment in each pointing at the other.
- **Confidence:** high
- **Context limitation:** if the build enforces zero shared modules between `src/` and `server/`, deliberate duplication is the right call and only the missing cross-reference is a finding.

---

### P10. `readonly` discipline on domain types is applied to fields but not to the arrays they hold
- **Severity:** low
- **Category:** pattern-compliance
- **Subcategory:** type-safety
- **Evidence:** `src/types/domain.ts:21-28` and `src/pipeline/plugins/remark-repair.ts:23-25`
```ts
export interface Heading {
  readonly id: string
  readonly depth: number
  readonly text: string
  children: Heading[]        // ← neither readonly nor ReadonlyArray
}
export interface RepairResult { readonly notes: RepairNote[] }
```
- **Established pattern being violated:** the consumer side already declares the stricter shape — `RepairNotice` takes `{ readonly repairs: readonly RepairNote[] }` (`src/reader/RepairNotice.tsx:22`), and `useMermaid` takes `readonly blocks: readonly MermaidBlock[]`. The producing types are looser than the consuming ones, in a project that opts into `exactOptionalPropertyTypes` and `noUncheckedIndexedAccess`.
- **Why it matters:** `RenderResult` values are cached and shared across components (`src/state/render.ts:39-62` hands the *same* object to every caller). A mutable `Heading.children` on a cached, shared result is a mutation waiting to happen that the compiler will not catch — and a mutated cached result would desynchronise the sidebar from the prose without any store action recording it.
- **Suggested fix:** `readonly children: readonly Heading[]` and `readonly notes: readonly RepairNote[]`; build the arrays locally as mutable and widen at the return boundary, as the render pipeline already does with its `repairs`/`headings` sinks.
- **Confidence:** medium
- **Context limitation:** the repair and heading plugins push into these arrays while building; if they type their local accumulators as the interface itself rather than as plain arrays, this change requires a small refactor at each sink. I cannot see those assignment sites.

TOTAL FINDINGS: 10

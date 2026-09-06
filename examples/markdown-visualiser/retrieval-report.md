# Context Engine — retrieval report

- Index: **199 chunks** from 31 TS/TSX files, 118,192 chars
- Embedding: `all-MiniLM-L6-v2` (384-dim), local ONNX
- Vector store: Chroma (ephemeral), cosine similarity
- Selective retrieval: top 30 chunks per specialist (union over its queries)

## security agent
- 30 chunks, 20,842 chars (82.4% reduction vs full context)
- top 8 retrieved:
  - `src/ingest/links.ts:64` — function `resolveLink` (sim -0.052)
  - `src/pipeline/sanitize.ts:172` — const `printSchema` (sim -0.063)
  - `src/ingest/assets.ts:28` — function `resolveRelative` (sim -0.136)
  - `server/pdf.ts:217` — function `escapeHtml` (sim -0.152)
  - `src/ingest/walker.ts:155` — function `stripCommonRoot` (sim -0.218)
  - `src/export/standalone.ts:89` — function `escapeHtml` (sim -0.230)
  - `src/ingest/links.ts:22` — function `buildDocIndex` (sim -0.238)
  - `src/ingest/walker.ts:62` — function `walkEntry` (sim -0.247)

## pattern agent
- 30 chunks, 29,039 chars (75.4% reduction vs full context)
- top 8 retrieved:
  - `src/reader/RepairNotice.tsx:22` — function `RepairNotice` (sim -0.231)
  - `src/reader/Mermaid.tsx:103` — function `withTimeout` (sim -0.239)
  - `server/pdf.ts:65` — function `closeBrowser` (sim -0.245)
  - `server/pdf.ts:200` — function `withDeadline` (sim -0.261)
  - `src/state/render.ts:75` — function `useRenderedDoc` (sim -0.261)
  - `server/pdf.ts:134` — function `renderPdf` (sim -0.264)
  - `src/reader/ProgressRail.tsx:13` — function `ProgressRail` (sim -0.293)
  - `src/reader/Mermaid.tsx:184` — function `useMermaid` (sim -0.294)

## requirements agent
- 30 chunks, 25,430 chars (78.5% reduction vs full context)
- top 8 retrieved:
  - `src/types/domain.ts:52` — interface `MarkdownDoc` (sim +0.202)
  - `src/reader/IndexSidebar.tsx:14` — interface `IndexSidebarProps` (sim +0.115)
  - `src/pipeline/plugins/rehype-shiki.ts:104` — interface `ShikiOptions` (sim +0.071)
  - `src/pipeline/plugins/rehype-shiki.ts:33` — function `getHighlighter` (sim -0.002)
  - `src/pipeline/plugins/rehype-shiki.ts:113` — function `rehypeShiki` (sim -0.008)
  - `src/pipeline/render.ts:138` — function `renderDocument` (sim -0.015)
  - `src/pipeline/plugins/rehype-shiki.ts:24` — const `highlighterPromise` (sim -0.031)
  - `src/pipeline/plugins/rehype-shiki.ts:22` — const `THEMES` (sim -0.077)

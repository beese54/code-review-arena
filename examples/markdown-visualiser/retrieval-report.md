# Context Engine — retrieval report

- Index: **199 chunks** from 31 TS/TSX files, 118,192 chars
- Embedding: `all-MiniLM-L6-v2` (384-dim), local ONNX
- Vector store: Chroma (ephemeral), squared-L2 over unit vectors (rank-identical to cosine)
- Selective retrieval: top 30 chunks per specialist (union over its queries)

## security agent
- 30 chunks, 20,842 chars (82.4% reduction vs full context)
- top 8 retrieved:
  - `src/ingest/links.ts:64` — function `resolveLink` (cos 0.474)
  - `src/pipeline/sanitize.ts:172` — const `printSchema` (cos 0.469)
  - `src/ingest/assets.ts:28` — function `resolveRelative` (cos 0.432)
  - `server/pdf.ts:217` — function `escapeHtml` (cos 0.424)
  - `src/ingest/walker.ts:155` — function `stripCommonRoot` (cos 0.391)
  - `src/export/standalone.ts:89` — function `escapeHtml` (cos 0.385)
  - `src/ingest/links.ts:22` — function `buildDocIndex` (cos 0.381)
  - `src/ingest/walker.ts:62` — function `walkEntry` (cos 0.377)

## pattern agent
- 30 chunks, 29,039 chars (75.4% reduction vs full context)
- top 8 retrieved:
  - `src/reader/RepairNotice.tsx:22` — function `RepairNotice` (cos 0.385)
  - `src/reader/Mermaid.tsx:103` — function `withTimeout` (cos 0.381)
  - `server/pdf.ts:65` — function `closeBrowser` (cos 0.378)
  - `server/pdf.ts:200` — function `withDeadline` (cos 0.369)
  - `src/state/render.ts:75` — function `useRenderedDoc` (cos 0.369)
  - `server/pdf.ts:134` — function `renderPdf` (cos 0.368)
  - `src/reader/ProgressRail.tsx:13` — function `ProgressRail` (cos 0.354)
  - `src/reader/Mermaid.tsx:184` — function `useMermaid` (cos 0.353)

## requirements agent
- 30 chunks, 25,430 chars (78.5% reduction vs full context)
- top 8 retrieved:
  - `src/types/domain.ts:52` — interface `MarkdownDoc` (cos 0.601)
  - `src/reader/IndexSidebar.tsx:14` — interface `IndexSidebarProps` (cos 0.557)
  - `src/pipeline/plugins/rehype-shiki.ts:104` — interface `ShikiOptions` (cos 0.535)
  - `src/pipeline/plugins/rehype-shiki.ts:33` — function `getHighlighter` (cos 0.499)
  - `src/pipeline/plugins/rehype-shiki.ts:113` — function `rehypeShiki` (cos 0.496)
  - `src/pipeline/render.ts:138` — function `renderDocument` (cos 0.492)
  - `src/pipeline/plugins/rehype-shiki.ts:24` — const `highlighterPromise` (cos 0.484)
  - `src/pipeline/plugins/rehype-shiki.ts:22` — const `THEMES` (cos 0.462)

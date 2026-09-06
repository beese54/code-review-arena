"""Embed the chunks, index them, and retrieve a SELECTIVE context bundle per agent.

Selective, not full: the whole point is that handing a reviewer the entire
codebase dilutes it. Each agent declares its own retrieval queries in its
`agents/*.md` frontmatter; results are unioned and cut to --top-k.

Embeddings come from Chroma's bundled local model (all-MiniLM-L6-v2, ONNX, no
API key). Pass --embedder openai to use text-embedding-3-large instead, which
needs OPENAI_API_KEY.
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")


@dataclass
class Agent:
    name: str
    path: Path
    queries: list[str]
    body: str
    requires_task_context: bool


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    raw, body = text[3:end], text[end + 4:].lstrip("\n")
    try:
        import yaml  # optional
        return yaml.safe_load(raw) or {}, body
    except Exception:
        pass
    # Minimal fallback: scalars and "- item" lists, which is all we declare.
    meta: dict = {}
    key = None
    for line in raw.split("\n"):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^(\w[\w-]*):\s*(.*)$", line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            if val in ("", "|", ">"):
                meta[key] = []
            elif val.startswith("[") and val.endswith("]"):
                meta[key] = [v.strip().strip("'\"") for v in val[1:-1].split(",") if v.strip()]
            else:
                meta[key] = val.strip("'\"")
        elif line.lstrip().startswith("- ") and key:
            meta.setdefault(key, [])
            if isinstance(meta[key], list):
                meta[key].append(line.lstrip()[2:].strip().strip("'\""))
    return meta, body


def load_agents(agents_dir: Path, only: list[str] | None = None) -> list[Agent]:
    out: list[Agent] = []
    for p in sorted(agents_dir.glob("*.md")):
        if p.name.upper() == "README.MD":
            continue
        meta, body = _parse_frontmatter(p.read_text(encoding="utf-8"))
        name = str(meta.get("name") or p.stem)
        if only and name not in only:
            continue
        queries = meta.get("queries") or []
        if not isinstance(queries, list) or not queries:
            print(f"  warning: {p.name} declares no queries; skipping", file=sys.stderr)
            continue
        out.append(Agent(
            name=name, path=p, queries=[str(q) for q in queries], body=body,
            requires_task_context=bool(meta.get("requires_task_context", False)),
        ))
    return out


def _embedding_fn(kind: str):
    from chromadb.utils import embedding_functions
    if kind == "openai":
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            print("  error: --embedder openai needs OPENAI_API_KEY", file=sys.stderr)
            raise SystemExit(2)
        return embedding_functions.OpenAIEmbeddingFunction(
            api_key=key, model_name="text-embedding-3-large")
    return embedding_functions.DefaultEmbeddingFunction()



def _cosine(distance: float) -> float:
    """Convert Chroma's default distance to a real cosine similarity.

    Chroma's default space is squared L2, and both embedders here return unit
    vectors, so d = |a-b|^2 = 2 - 2cos, giving cos = 1 - d/2. Reporting the raw
    `1 - d` instead — as an earlier version of this file did — is monotonic, so
    it ranks identically, but it is not a cosine: it prints -0.05 for a chunk
    whose true cosine is 0.47, which reads like "unrelated" when it is not.
    """
    return max(-1.0, min(1.0, 1.0 - distance / 2.0))


def retrieve(chunks: list[dict], agents: list[Agent], out_dir: Path,
             top_k: int, per_query: int, embedder: str) -> dict:
    import chromadb

    docs = [
        f"# {c['type']}: {c['name']} ({c['file']}:{c['start_line']}-{c['end_line']})\n{c['content']}"
        for c in chunks
    ]
    full_chars = sum(len(d) for d in docs)

    client = chromadb.EphemeralClient()
    col = client.create_collection("repo", embedding_function=_embedding_fn(embedder))

    # Chroma has a per-batch ceiling; large repos need slicing.
    BATCH = 4000
    for i in range(0, len(docs), BATCH):
        sl = slice(i, i + BATCH)
        col.add(
            ids=[str(j) for j in range(i, min(i + BATCH, len(docs)))],
            documents=docs[sl],
            metadatas=[{k: c[k] for k in ("type", "name", "file", "start_line", "end_line")}
                       for c in chunks[sl]],
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    report: dict = {"index": {"chunks": len(chunks), "chars": full_chars,
                              "embedder": embedder}, "agents": {}}

    if top_k >= len(chunks):
        print(f"  warning: --top-k {top_k} >= index size {len(chunks)}. Every agent receives the\n"
              f"           whole codebase, so this is a FULL-context run, not a selective one.\n"
              f"           Lower --top-k (~15% of the index) to exercise retrieval.",
              file=sys.stderr)
        report["index"]["selective"] = False
    else:
        report["index"]["selective"] = True

    for ag in agents:
        best: dict[str, float] = {}
        for q in ag.queries:
            res = col.query(query_texts=[q], n_results=min(per_query, len(docs)))
            for cid, dist in zip(res["ids"][0], res["distances"][0]):
                cos = _cosine(dist)
                if cos > best.get(cid, -9):
                    best[cid] = cos
        top = sorted(best.items(), key=lambda kv: -kv[1])[:top_k]
        sel_chars = sum(len(docs[int(cid)]) for cid, _ in top)
        reduction = (1 - sel_chars / full_chars) * 100 if full_chars else 0.0

        lines = [
            f"# Selective context bundle — {ag.name}", "",
            f"Retrieved {len(top)} of {len(chunks)} chunks "
            f"({sel_chars:,} of {full_chars:,} chars — {reduction:.1f}% reduction vs full context).",
            "",
            "Line numbers in the headings below are real. Cite them exactly; do not estimate.", "",
        ]
        for cid, cos in top:
            c = chunks[int(cid)]
            lines += [
                f"## {c['type']}: `{c['name']}` — "
                f"`{c['file']}:{c['start_line']}-{c['end_line']}` (cos {cos:.3f})",
                "```", c["content"], "```", "",
            ]
        (out_dir / f"{ag.name}.md").write_text("\n".join(lines), encoding="utf-8")

        report["agents"][ag.name] = {
            "chunks": len(top), "chars": sel_chars, "reduction_pct": round(reduction, 1),
            "top": [
                {"file": chunks[int(cid)]["file"], "line": chunks[int(cid)]["start_line"],
                 "type": chunks[int(cid)]["type"], "name": chunks[int(cid)]["name"],
                 "cos": round(cos, 3)}
                for cid, cos in top[:8]
            ],
        }
        print(f"  {ag.name:<20} {len(top):3d} chunks  {sel_chars:7,d} chars  "
              f"({reduction:.1f}% reduction)")
    return report


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Selective context retrieval per review agent.")
    ap.add_argument("--chunks", required=True, type=Path)
    ap.add_argument("--agents-dir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--top-k", type=int, default=30)
    ap.add_argument("--per-query", type=int, default=12)
    ap.add_argument("--embedder", choices=["local", "openai"], default="local")
    ap.add_argument("--only", nargs="*", default=None)
    a = ap.parse_args()

    chunks = json.loads(a.chunks.read_text(encoding="utf-8"))
    agents = load_agents(a.agents_dir, a.only)
    if not agents:
        print("error: no agents loaded", file=sys.stderr)
        return 2
    report = retrieve(chunks, agents, a.out, a.top_k, a.per_query, a.embedder)
    (a.out / "retrieval-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

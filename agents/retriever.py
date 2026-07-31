"""F3 — Retriever agent: semantic search over the internal document base."""

import sys

import config


def run(question: str, k: int = 3) -> str:
    client = config.qdrant()
    if not client.collection_exists(config.COLLECTION):
        return "No document index found. Run `python ingestion.py` first."
    hits = client.query_points(config.COLLECTION,
                               query=config.embed([question])[0], limit=k).points
    if not hits:
        return "No relevant documents found."
    return "\n---\n".join(f"[{h.payload['source']} | score={h.score:.2f}]\n{h.payload['text']}"
                          for h in hits)


if __name__ == "__main__":
    print(run(" ".join(sys.argv[1:]) or "why are customers churning?"))

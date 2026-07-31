"""F2 — Ingestion: load documents, chunk, embed, index into embedded Qdrant.

Chunking: paragraph-based with ~500 char cap — small docs stay coherent,
larger ones split on blank lines. Each point stores the source filename so
answers can cite it.
"""

import glob
import os
import uuid

from qdrant_client.models import Distance, PointStruct, VectorParams

import config

DOCS_DIR = os.path.join(os.path.dirname(__file__), "data", "docs")


def chunk(text: str, max_len: int = 500) -> list[str]:
    parts, buf = [], ""
    for para in text.split("\n\n"):
        if len(buf) + len(para) < max_len:
            buf += ("\n\n" if buf else "") + para
        else:
            if buf:
                parts.append(buf)
            buf = para
    if buf:
        parts.append(buf)
    return [p.strip() for p in parts if p.strip()]


def main() -> None:
    client = config.qdrant()
    if client.collection_exists(config.COLLECTION):
        client.delete_collection(config.COLLECTION)
    client.create_collection(
        config.COLLECTION,
        vectors_config=VectorParams(size=config.EMBED_DIM, distance=Distance.COSINE),
    )
    points = []
    for path in sorted(glob.glob(os.path.join(DOCS_DIR, "*.md"))):
        text = open(path, encoding="utf-8").read()
        for ch in chunk(text):
            points.append((os.path.basename(path), ch))
    vectors = config.embed([c for _, c in points])
    client.upsert(config.COLLECTION, points=[
        PointStruct(id=str(uuid.uuid4()), vector=v,
                    payload={"source": src, "text": txt})
        for (src, txt), v in zip(points, vectors)
    ])
    print(f"Indexed {len(points)} chunks from {DOCS_DIR}")
    # sanity check
    hits = client.query_points(config.COLLECTION,
                               query=config.embed(["churn ta'rifi nima"])[0],
                               limit=2).points
    for h in hits:
        print(f"  score={h.score:.3f}  {h.payload['source']}")


if __name__ == "__main__":
    main()

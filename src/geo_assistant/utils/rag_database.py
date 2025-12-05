from __future__ import annotations

import os
from typing import Any, Dict, List, Tuple

import lancedb
import requests


PC_STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
DEFAULT_DB_PATH = os.path.join("data", "lancedb")
DEFAULT_TABLE = "pc_collections"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")


def create_rag_database(db_path: str = DEFAULT_DB_PATH) -> lancedb.Database:
    """Create and connect to the LanceDB database used for RAG.

    Args:
        db_path: Filesystem path for the LanceDB database directory.

    Returns:
        A connected LanceDB Database instance.
    """
    os.makedirs(db_path, exist_ok=True)
    return lancedb.connect(db_path)


def _build_collection_text(coll: Dict[str, Any]) -> Tuple[str, str, str]:
    """Build minimal textual fields from a STAC collection for later use.

    This returns identifiers used by the embedding text builder, not the
    full embedded text itself.

    Args:
        coll: A Planetary Computer STAC collection JSON object.

    Returns:
        Tuple of (collection id, title, snippet text).
    """
    cid = coll.get("id", "")
    title = coll.get("title", cid)
    desc = (coll.get("description") or "")
    snippet = (desc or title)
    return cid, title, snippet


def fetch_pc_collections(stac_url: str = PC_STAC_URL) -> List[Dict[str, Any]]:
    """Fetch all collections from a STAC endpoint (Planetary Computer).

    Args:
        stac_url: Base URL of the STAC API.

    Returns:
        A list of collection JSON objects.
    """
    url = f"{stac_url.rstrip('/')}/collections"
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return list(data.get("collections", []))


def embed_texts_ollama(texts: List[str], model: str = EMBED_MODEL, ollama_url: str = OLLAMA_URL) -> List[List[float]]:
    """Embed a list of texts using a local Ollama embeddings endpoint.

    Sends one prompt per request to ensure 1:1 mapping between inputs and
    returned vectors. Expects a top-level "embedding" field in the response.

    Args:
        texts: List of input strings to embed.
        model: Ollama model name (e.g., "nomic-embed-text").
        ollama_url: Base URL for the Ollama server.

    Returns:
        A list of embedding vectors (list of floats) aligned with inputs.

    Raises:
        RuntimeError: If the Ollama response does not contain "embedding".
    """
    if not texts:
        return []
    url = f"{ollama_url.rstrip('/')}/api/embeddings"
    vecs: List[List[float]] = []
    for t in texts:
        payload = {"model": model, "prompt": t}
        r = requests.post(url, json=payload, timeout=120)
        r.raise_for_status()
        out = r.json()
        # Accept only the single-input response shape: {"embedding": [...]}
        if isinstance(out, dict) and isinstance(out.get("embedding"), list):
            vecs.append(out["embedding"])
            continue
        raise RuntimeError(f"Unexpected embeddings response (expected top-level 'embedding'): {out}")
    return vecs


def insert_pc_collections(
    db: lancedb.Database,
    collections: List[Dict[str, Any]],
    table_name: str = DEFAULT_TABLE,
    drop_existing: bool = False,
) -> Dict[str, Any]:
    """Insert Planetary Computer collections into LanceDB.

    Builds an embedding text per collection, embeds with Ollama, and writes
    rows with fields: id, title, snippet, text, vector.

    Args:
        db: An open LanceDB database connection.
        collections: List of STAC collection JSON objects.
        table_name: Name of the table to create or open.
        drop_existing: If True, drop the table before inserting.

    Returns:
        A summary dict with the table name and row count.
    """
    rows = []
    texts = []
    metas: List[Tuple[str, str, str]] = []
    for coll in collections:
        cid, title, snippet = _build_collection_text(coll)
        text = _build_collection_text_blob(coll)
        texts.append(text)
        metas.append((cid, title, snippet))
    vectors = embed_texts_ollama(texts)
    for (cid, title, snippet), vec, text in zip(metas, vectors, texts):
        rows.append(
            {
                "id": cid,
                "title": title,
                "snippet": snippet,
                "text": text,
                "vector": vec,
            }
        )

    if drop_existing and table_name in db.table_names():
        db.drop_table(table_name)
    if table_name not in db.table_names():
        tbl = db.create_table(table_name, data=rows[:1])
        rows = rows[1:]
    else:
        tbl = db.open_table(table_name)
    if rows:
        tbl.add(rows)
    return {"table": table_name, "count": tbl.count_rows()}


def _build_collection_text_blob(coll: Dict[str, Any]) -> str:
    """Build the full text blob used for vector embeddings.

    Includes id, title, snippet, description, keywords, providers, and raw
    spatial/temporal extents so searches can leverage coverage.

    Args:
        coll: A Planetary Computer STAC collection JSON object.

    Returns:
        A single string containing the concatenated fields.
    """
    cid, title, snippet = _build_collection_text(coll)
    extent = coll.get("extent", {})
    parts = [
        f"id: {cid}",
        f"title: {title}",
        f"snippet: {snippet}",
        f"description: {(coll.get('description') or '')[:8000]}",
        f"keywords: {', '.join(coll.get('keywords', [])[:64])}",
        f"providers: {', '.join([p.get('name','') for p in coll.get('providers', [])])}",
        f"extent.spatial.bbox: {extent.get('spatial', {}).get('bbox')}",
        f"extent.temporal.interval: {extent.get('temporal', {}).get('interval')}",
    ]
    return "\n".join(parts)


def _cli_main() -> None:
    """CLI entrypoint to fetch, preview, and (re)index collections.

    - Prints a brief preview (id, title, keywords, raw extents) for the first
      few collections.
    - Drops the LanceDB table and reinserts all collections with fresh
      embeddings.
    """
    db = create_rag_database()
    collections = fetch_pc_collections()
    print(f"Fetched collections: {len(collections)}")
    # Concise preview before embedding
    try:
        preview_n = int(os.getenv("RAG_PREVIEW_N", "5"))
    except ValueError:
        preview_n = 5
    for coll in collections[:preview_n]:
        cid = coll.get("id")
        title = coll.get("title", cid)
        kws = coll.get("keywords", [])
        extent = coll.get("extent", {})
        print({
            "id": cid,
            "title": title,
            "keywords": kws[:8],
            "extent_spatial_bbox": extent.get("spatial", {}).get("bbox"),
            "extent_temporal_interval": extent.get("temporal", {}).get("interval"),
        })
    print("Dropping existing table before reindex...")
    res = insert_pc_collections(db, collections, drop_existing=True)
    print(f"Inserted table '{res['table']}' with count={res['count']}")


if __name__ == "__main__":
    _cli_main()

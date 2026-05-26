# backend/rag/retrieval/retriever.py

from rag.schemas.models import (
    RetrievalRequest,
    RetrievalResponse,
    RetrievedArtwork,
)
from rag.embeddings.clip_encoder import encode_text
from rag.vectorstore.qdrant_client import search_artworks
from rag.config import get_settings
from rag.utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


def retrieve_artworks(request: RetrievalRequest) -> RetrievalResponse:
    """
    Core RAG retrieval step:
      1. Encode query text with CLIP
      2. Search Qdrant for nearest artwork vectors
      3. Parse and return ranked results

    Args:
        request: RetrievalRequest with query string and optional top_k override.

    Returns:
        RetrievalResponse with ranked list of RetrievedArtwork objects.
    """
    top_k = request.top_k or settings.TOP_K
    logger.info(f"Retrieving top {top_k} artworks for query: '{request.query}'")

    # Step 1 — Embed the text query
    query_vector = encode_text(request.query)

    # Step 2 — Search Qdrant
    scored_points = search_artworks(query_vector=query_vector, top_k=top_k)

    # Step 3 — Parse results
    results: list[RetrievedArtwork] = []
    for point in scored_points:
        p = point.payload
        results.append(
            RetrievedArtwork(
                artwork_id=str(point.id),
                score=round(point.score, 4),
                title=p.get("title", "Unknown"),
                artist=p.get("artist", "Unknown"),
                style=p.get("style", ""),
                year=p.get("year"),
                caption=p.get("caption", ""),
                image_url=p.get("image_url", ""),
                tags=p.get("tags", []),
            )
        )

    logger.info(f"Retrieved {len(results)} artworks above score threshold")
    return RetrievalResponse(
        query=request.query,
        results=results,
        total_found=len(results),
    )
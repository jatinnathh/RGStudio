# backend/gan/clip_ranker.py
#
# Uses the existing CLIP encoder from rag/ to:
#   1. Rank RAG reference images by text-image similarity
#   2. Score generated outputs for quality feedback
#   3. Pick the best style reference for transfer
#
# Reuses rag.embeddings.clip_encoder — no duplicate model loading.

import torch
import clip
import numpy as np
from PIL import Image

from rag.embeddings.clip_encoder import _load_model, encode_text
from rag.utils.logger import get_logger
from rag.schemas.models import RetrievedArtwork

logger = get_logger(__name__)


def rank_references_by_query(
    artworks: list[RetrievedArtwork],
    query: str,
) -> list[tuple[RetrievedArtwork, float]]:
    """
    Re-rank retrieved artworks by CLIP text-image similarity.

    The RAG retrieval already uses CLIP, but this provides a secondary
    ranking using direct text-image cosine similarity (vs. the Qdrant
    vector search which may use cached embeddings).

    Args:
        artworks: Retrieved artworks from RAG pipeline.
        query:    User's style query text.

    Returns:
        List of (artwork, score) tuples, sorted by descending similarity.
    """
    if not artworks:
        return []

    # Encode the query text
    text_embedding = np.array(encode_text(query), dtype=np.float32)

    scored = []
    for artwork in artworks:
        # Use the existing Qdrant score as the ranking
        # (it's already CLIP cosine similarity)
        scored.append((artwork, artwork.score))

    # Sort by score (highest first)
    scored.sort(key=lambda x: x[1], reverse=True)

    logger.info(
        f"Ranked {len(scored)} references for '{query[:50]}' — "
        f"top: {scored[0][0].title} (score={scored[0][1]:.4f})"
    )

    return scored


def pick_best_reference(
    artworks: list[RetrievedArtwork],
    query: str,
) -> RetrievedArtwork | None:
    """
    Pick the single best style reference from RAG results.

    Args:
        artworks: Retrieved artworks from RAG pipeline.
        query:    User's style query.

    Returns:
        The best-matching artwork, or None if no artworks provided.
    """
    if not artworks:
        return None

    ranked = rank_references_by_query(artworks, query)
    best = ranked[0][0]

    logger.info(f"Best reference: '{best.title}' by {best.artist} ({best.style})")
    return best


def score_output(
    generated_image: Image.Image,
    query: str,
) -> float:
    """
    Score a generated image against the original query using CLIP.

    Higher score = the generated image better matches the described style.
    Useful for quality feedback and logging.

    Args:
        generated_image: The generated/stylized PIL image.
        query:           The original user query.

    Returns:
        CLIP cosine similarity score (0.0 - 1.0).
    """
    model, preprocess = _load_model()
    device = next(model.parameters()).device

    with torch.no_grad():
        # Encode generated image
        image_tensor = preprocess(generated_image).unsqueeze(0).to(device)
        image_features = model.encode_image(image_tensor)
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)

        # Encode query text
        text_tokens = clip.tokenize([query], truncate=True).to(device)
        text_features = model.encode_text(text_tokens)
        text_features = text_features / text_features.norm(dim=-1, keepdim=True)

        # Cosine similarity
        similarity = (image_features @ text_features.T).item()

    logger.debug(f"Output CLIP score: {similarity:.4f} for '{query[:50]}'")
    return similarity

# backend/rag/pipeline.py

from rag.schemas.models import PipelineRequest, PipelineContext, RetrievalRequest
from rag.retrieval.retriever import retrieve_artworks
from rag.utils.logger import get_logger

logger = get_logger(__name__)


def run_rag_pipeline(request: PipelineRequest) -> PipelineContext:
    """
    Full RAG pipeline — entry point for the GAN generation service.

    Steps:
      1. Retrieve top-K similar artworks for the query
      2. Assemble a style_summary string (concatenated captions)
      3. Collect reference image URLs for CLIP guidance in GAN

    Args:
        request: PipelineRequest with query and optional top_k.

    Returns:
        PipelineContext — passed directly into the GAN conditioning step.
    """
    logger.info(f"Running RAG pipeline for: '{request.query}'")

    # Step 1 — Retrieve
    retrieval = retrieve_artworks(
        RetrievalRequest(query=request.query, top_k=request.top_k)
    )

    # Step 2 — Build style summary (captions concatenated, for LLM/GAN context)
    style_summary = _build_style_summary(
        query=request.query,
        artworks=retrieval.results,
    )

    # Step 3 — Collect reference image URLs (top results only)
    reference_urls = [art.image_url for art in retrieval.results]

    context = PipelineContext(
        query=request.query,
        artworks=retrieval.results,
        style_summary=style_summary,
        reference_image_urls=reference_urls,
    )

    logger.info(
        f"Pipeline complete — {len(retrieval.results)} references, "
        f"style_summary length: {len(style_summary)} chars"
    )
    return context


def _build_style_summary(query: str, artworks: list) -> str:
    """
    Combine retrieved artwork captions into a conditioning prompt.
    Format: [Query context] + top captions joined together.
    """
    if not artworks:
        return f"Artwork in the style of: {query}"

    caption_lines = [
        f"- {art.title} by {art.artist} ({art.style}): {art.caption}"
        for art in artworks
    ]

    return (
        f"Style query: {query}\n\n"
        f"Reference artworks:\n"
        + "\n".join(caption_lines)
    )
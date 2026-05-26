# backend/rag/ingestion/ingestor.py

from rag.schemas.models import IngestRequest, IngestResponse, ArtworkMetadata
from rag.embeddings.clip_encoder import encode_image_from_url
from rag.ingestion.captioner import caption_from_url
from rag.vectorstore.qdrant_client import upsert_artwork
from rag.utils.logger import get_logger

logger = get_logger(__name__)


def ingest_artwork(request: IngestRequest) -> IngestResponse:
    """
    Full ingestion pipeline for a single artwork:
      1. Caption the image with BLIP-2
      2. Embed the image with CLIP
      3. Build metadata payload
      4. Upsert into Qdrant

    Args:
        request: IngestRequest with image_url, title, artist, style, etc.

    Returns:
        IngestResponse with success status and assigned artwork_id.
    """
    logger.info(f"Ingesting artwork: '{request.title}' by {request.artist}")

    # Step 1 — Generate caption
    # caption = caption_from_url(request.image_url)
    caption = f"A painting in {request.style} style by {request.artist}"  # mock

    logger.info(f"Caption generated: {caption[:80]}...")

    # Step 2 — CLIP image embedding
    vector = encode_image_from_url(request.image_url)

    # Step 3 — Build metadata
    metadata = ArtworkMetadata(
        title=request.title,
        artist=request.artist,
        style=request.style,
        year=request.year,
        caption=caption,
        image_url=request.image_url,
        tags=request.tags,
    )

    # Step 4 — Upsert to Qdrant
    upsert_artwork(
        artwork_id=metadata.id,
        vector=vector,
        payload=metadata.model_dump(mode="json"),
    )

    logger.info(f"Ingestion complete. ID: {metadata.id}")
    return IngestResponse(
        success=True,
        artwork_id=str(metadata.id),
        message=f"'{request.title}' by {request.artist} ingested successfully.",
    )
# backend/rag/vectorstore/qdrant_client.py

from transformers.models.vitpose_backbone import configuration_vitpose_backbone
from uuid import UUID
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    
)
from functools import lru_cache

from rag.config import get_settings
from rag.utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


@lru_cache(maxsize=1)
def _get_client() -> QdrantClient:
    logger.info(f"Connecting to Qdrant at {settings.QDRANT_URL}")
    return QdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY,
    )


def ensure_collection_exists() -> None:
    """
    Create the artwork collection if it doesn't already exist.
    Safe to call on every startup.
    """
    client = _get_client()
    existing = [c.name for c in client.get_collections().collections]

    if settings.QDRANT_COLLECTION not in existing:
        client.create_collection(
            collection_name=settings.QDRANT_COLLECTION,
            vectors_config=VectorParams(
                size=settings.QDRANT_VECTOR_SIZE,
                distance=Distance.COSINE,
            ),
        )
        logger.info(f"Created Qdrant collection: {settings.QDRANT_COLLECTION}")
    else:
        logger.info(f"Collection already exists: {settings.QDRANT_COLLECTION}")


def upsert_artwork(
    artwork_id: UUID,
    vector: list[float],
    payload: dict,
) -> None:
    """
    Insert or update a single artwork vector + metadata payload.
    """
    client = _get_client()
    point = PointStruct(
        id=str(artwork_id),
        vector=vector,
        payload=payload,
    )
    client.upsert(
        collection_name=settings.QDRANT_COLLECTION,
        points=[point],
    )
    logger.info(f"Upserted artwork {artwork_id} into Qdrant")


def search_artworks(
    query_vector: list[float],
    top_k: int,
    style_filter: str | None = None,
) -> list:
    """
    Search for similar artworks by vector similarity.
    Optionally filter by exact style tag.
    Returns a list of ScoredPoints (id, score, payload).
    """
    client = _get_client()

    search_filter = None
    if style_filter:
        search_filter = Filter(
            must=[FieldCondition(key="style", match=MatchValue(value=style_filter))]
        )

    results = client.query_points(
        collection_name=settings.QDRANT_COLLECTION,
        query=query_vector,
        limit=top_k,
        query_filter=search_filter,
        score_threshold=settings.SCORE_THRESHOLD,
        with_payload=True,
    ).points

    logger.info(f"Qdrant search returned {len(results)} results (top_k={top_k})")
    return results


def delete_artwork(artwork_id: str) -> None:
    client = _get_client()
    client.delete(
        collection_name=settings.QDRANT_COLLECTION,
        points_selector=[artwork_id],
    )
    logger.info(f"Deleted artwork {artwork_id} from Qdrant")


def get_collection_info() -> dict:
    client = _get_client()
    info = client.get_collection(settings.QDRANT_COLLECTION)
    return {
        "name": settings.QDRANT_COLLECTION,
        "vectors_count": info.vectors_count,
        "points_count": info.points_count,
        "status": str(info.status),
    }
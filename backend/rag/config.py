# backend/rag/config.py

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Qdrant
    QDRANT_URL: str
    QDRANT_API_KEY: str
    QDRANT_COLLECTION: str = "art_references"
    QDRANT_VECTOR_SIZE: int = 512  # CLIP ViT-B/32 output dim

    # CLIP
    CLIP_MODEL: str = "ViT-B/32"
    CLIP_DEVICE: str = "cpu"  # switch to "cuda" on Railway GPU

    # BLIP-2
    BLIP_MODEL: str = "Salesforce/blip2-opt-2.7b"
    BLIP_DEVICE: str = "cpu"

    # Retrieval
    TOP_K: int = 5
    SCORE_THRESHOLD: float = 0.20

    # App
    ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
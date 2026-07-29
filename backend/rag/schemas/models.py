# backend/rag/schemas/models.py

from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID, uuid4


# ── Ingestion ──────────────────────────────────────────────────────────────

class ArtworkMetadata(BaseModel):
    """Metadata stored alongside each vector in Qdrant."""
    id: UUID = Field(default_factory=uuid4)
    title: str
    artist: str
    style: str                          # e.g. "Impressionism", "Surrealism"
    year: Optional[int] = None
    caption: str                        # BLIP-2 generated
    image_url: str                      # Cloudflare R2 URL
    tags: list[str] = []


class IngestRequest(BaseModel):
    image_url: str
    title: str
    artist: str
    style: str
    year: Optional[int] = None
    tags: list[str] = []


class IngestResponse(BaseModel):
    success: bool
    artwork_id: str
    message: str


# ── Retrieval ──────────────────────────────────────────────────────────────

class RetrievalRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=500,
                       description="Natural language art style description")
    top_k: Optional[int] = Field(default=None, ge=1, le=20)


class RetrievedArtwork(BaseModel):
    artwork_id: str
    score: float
    title: str
    artist: str
    style: str
    year: Optional[int]
    caption: str
    image_url: str
    tags: list[str]


class RetrievalResponse(BaseModel):
    query: str
    results: list[RetrievedArtwork]
    total_found: int


# ── Pipeline ───────────────────────────────────────────────────────────────

class PipelineRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=500)
    top_k: Optional[int] = 5


class PipelineContext(BaseModel):
    """Assembled context passed to the GAN generation step."""
    query: str
    artworks: list[RetrievedArtwork]
    style_summary: str                  # combined caption text for conditioning
    reference_image_urls: list[str]     # top image URLs for CLIP guidance


# ── Generation ─────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    """Request body for text-to-art generation."""
    query: str = Field(..., min_length=3, max_length=500,
                       description="Natural language art style description")
    top_k: int = Field(default=5, ge=1, le=20,
                       description="Number of style references to retrieve")
    style_weight: float = Field(default=0.8, ge=0.0, le=1.0,
                                description="Style strength: 0.0=content, 1.0=full style")
    output_size: int = Field(default=512, ge=128, le=1024,
                             description="Output image resolution (square)")
    use_multi_style: bool = Field(default=False,
                                  description="Blend multiple style references")


class GenerateResponse(BaseModel):
    """Response body for art generation."""
    success: bool
    image_base64: str                    # base64-encoded JPEG
    style_reference: Optional[RetrievedArtwork] = None  # which artwork was used
    clip_score: float = 0.0              # CLIP similarity score
    generation_time_ms: int
    query: str
    message: str


class StyleTransferResponse(BaseModel):
    """Response body for style transfer (image upload)."""
    success: bool
    image_base64: str                    # base64-encoded JPEG
    style_reference: Optional[RetrievedArtwork] = None
    clip_score: float = 0.0
    generation_time_ms: int
    style_query: str
    message: str
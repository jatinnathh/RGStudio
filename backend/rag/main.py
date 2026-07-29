# backend/rag/main.py

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware

from rag.config import get_settings
from rag.utils.logger import get_logger
from rag.vectorstore.qdrant_client import ensure_collection_exists, get_collection_info
from rag.schemas.models import (
    IngestRequest, IngestResponse,
    RetrievalRequest, RetrievalResponse,
    PipelineRequest, PipelineContext,
    GenerateRequest, GenerateResponse,
    StyleTransferResponse,
)
from rag.ingestion.ingestor import ingest_artwork
from rag.retrieval.retriever import retrieve_artworks
from rag.pipeline import run_rag_pipeline

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: ensure Qdrant collection exists."""
    logger.info("RDStudio RAG service starting up...")
    ensure_collection_exists()

    # Pre-load CLIP so first request is instant
    from rag.embeddings.clip_encoder import _load_model
    _load_model()
    logger.info("CLIP model pre-loaded.")

    logger.info("Qdrant collection ready.")
    yield
    logger.info("RDStudio RAG service shutting down.")


app = FastAPI(
    title="RDStudio — RAG + GAN Pipeline",
    description="CLIP-powered retrieval pipeline + AdaIN style transfer for art generation",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ────────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "rag-gan-pipeline", "env": settings.ENV}


@app.get("/health/qdrant", tags=["Health"])
def qdrant_health():
    try:
        info = get_collection_info()
        return {"status": "ok", "collection": info}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Qdrant unreachable: {str(e)}")


# ── Ingestion ─────────────────────────────────────────────────────────────

@app.post("/ingest", response_model=IngestResponse, tags=["Ingestion"])
def ingest(request: IngestRequest):
    """
    Ingest a single artwork into the vector store.
    Downloads the image, generates BLIP-2 caption, CLIP embeds, upserts to Qdrant.
    """
    try:
        return ingest_artwork(request)
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Retrieval ─────────────────────────────────────────────────────────────

@app.post("/retrieve", response_model=RetrievalResponse, tags=["Retrieval"])
def retrieve(request: RetrievalRequest):
    """
    Retrieve top-K similar artworks for a text query using CLIP embeddings.
    """
    try:
        return retrieve_artworks(request)
    except Exception as e:
        logger.error(f"Retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Pipeline ──────────────────────────────────────────────────────────────

@app.post("/pipeline", response_model=PipelineContext, tags=["Pipeline"])
def pipeline(request: PipelineRequest):
    """
    Full RAG pipeline. Returns assembled PipelineContext for GAN conditioning.
    Call this from the generation service — not the frontend directly.
    """
    try:
        return run_rag_pipeline(request)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Generation ────────────────────────────────────────────────────────────

@app.post("/generate", response_model=GenerateResponse, tags=["Generation"])
def generate(request: GenerateRequest):
    """
    Text → Art generation.

    1. RAG pipeline retrieves style references for your query
    2. CLIP ranker picks the best reference artwork
    3. AdaIN style transfer generates a new image in that style
    4. Returns base64-encoded JPEG + metadata

    Example:
        POST /generate
        {"query": "impressionist sunset over water", "style_weight": 0.8}
    """
    try:
        from gan.generate import text_to_art

        result = text_to_art(
            query=request.query,
            top_k=request.top_k,
            style_weight=request.style_weight,
            output_size=request.output_size,
            use_multi_style=request.use_multi_style,
        )

        return GenerateResponse(
            success=result.style_reference is not None,
            image_base64=result.image_base64,
            style_reference=result.style_reference,
            clip_score=result.clip_score,
            generation_time_ms=result.generation_time_ms,
            query=result.query,
            message=result.message,
        )

    except Exception as e:
        logger.error(f"Generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/style-transfer", response_model=StyleTransferResponse, tags=["Generation"])
async def style_transfer_endpoint(
    image: UploadFile = File(..., description="Image file to apply style to"),
    style_query: str = Form(..., description="Target art style description"),
    top_k: int = Form(default=5, ge=1, le=20),
    style_weight: float = Form(default=0.8, ge=0.0, le=1.0),
    output_size: int = Form(default=512, ge=128, le=1024),
):
    """
    Style transfer: upload an image and apply an art style to it.

    1. Receives your uploaded image + style description
    2. RAG pipeline retrieves reference artworks matching the style
    3. CLIP ranker picks the best reference
    4. AdaIN transfers the reference style onto your image
    5. Returns base64-encoded JPEG + metadata

    Example (curl):
        curl -X POST http://localhost:8000/style-transfer \\
          -F "image=@my_photo.jpg" \\
          -F "style_query=cubist Picasso style" \\
          -F "style_weight=0.7"
    """
    try:
        from gan.generate import style_transfer_from_upload
        from gan.utils import load_image_from_bytes

        # Read uploaded file
        file_bytes = await image.read()
        if len(file_bytes) > 10 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Image too large (max 10MB)")

        content_image = load_image_from_bytes(file_bytes)

        result = style_transfer_from_upload(
            content_image=content_image,
            style_query=style_query,
            top_k=top_k,
            style_weight=style_weight,
            output_size=output_size,
        )

        return StyleTransferResponse(
            success=result.style_reference is not None,
            image_base64=result.image_base64,
            style_reference=result.style_reference,
            clip_score=result.clip_score,
            generation_time_ms=result.generation_time_ms,
            style_query=style_query,
            message=result.message,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Style transfer failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
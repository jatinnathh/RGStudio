# backend/rag/main.py

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from rag.config import get_settings
from rag.utils.logger import get_logger
from rag.vectorstore.qdrant_client import ensure_collection_exists, get_collection_info
from rag.schemas.models import (
    IngestRequest, IngestResponse,
    RetrievalRequest, RetrievalResponse,
    PipelineRequest, PipelineContext,
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
    title="RDStudio — RAG Pipeline",
    description="CLIP-powered retrieval pipeline for GAN art generation",
    version="1.0.0",
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
    return {"status": "ok", "service": "rag-pipeline", "env": settings.ENV}


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
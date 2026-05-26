RAG-Powered GAN Art Studio
Tagline: Describe an art style → RAG retrieves reference images + artist context → CLIP-guided GAN generates a new artwork in that style. Two systems, one seamless pipeline.
Core Tech Stack

Frontend: Next.js 14 (App Router), Tailwind CSS, shadcn/ui
Backend: FastAPI
ML: StyleGAN2-ADA (PyTorch), CLIP (ViT-B/32), BLIP-2 (captioning)
Vector DB: Qdrant Cloud (free tier)
Storage: Cloudflare R2 (generated images)
Auth + DB: Clerk, NeonDB (Drizzle ORM)
Deploy: Vercel (frontend), Railway (FastAPI), HuggingFace Spaces (model demo + weights)


---

## RAG Pipeline — Architecture & Status

> **Status: Complete & Tested**

### How It Works

```
User Query: "impressionist sunset, Monet style"
        │
        ▼
┌──────────────────────┐
│  CLIP Text Encoder   │  ← encodes query into 512-dim vector (ViT-B/32)
└──────────────────────┘
        │
        ▼
┌──────────────────────┐
│   Qdrant Vector DB   │  ← cosine similarity search over ingested artwork vectors
└──────────────────────┘
        │
        ▼
┌──────────────────────┐
│   PipelineContext    │  ← ranked artworks + style_summary + reference image URLs
└──────────────────────┘
        │
        ▼
  GAN Generation        ← (next module — consumes PipelineContext for conditioning)
```

### Module Structure

```
backend/rag/
├── config.py                   # All env vars via pydantic-settings, loaded from backend/.env
├── pipeline.py                 # End-to-end orchestrator → returns PipelineContext for GAN
├── main.py                     # FastAPI app — /health, /ingest, /retrieve, /pipeline routes
│
├── schemas/
│   └── models.py               # All Pydantic models: IngestRequest, RetrievalResponse, PipelineContext, etc.
│
├── embeddings/
│   └── clip_encoder.py         # CLIP ViT-B/32 — text + image → normalized 512-dim float vectors
│
├── vectorstore/
│   └── qdrant_client.py        # Qdrant connection, collection init, upsert, cosine search, delete
│
├── ingestion/
│   ├── captioner.py            # BLIP-2 — image URL → natural language caption (mocked during dev)
│   └── ingestor.py             # Full ingestion: download → caption → CLIP embed → upsert to Qdrant
│
├── retrieval/
│   └── retriever.py            # Query → CLIP text embed → Qdrant search → ranked RetrievedArtwork list
│
└── utils/
    └── logger.py               # Structured logger (timestamp | level | module | message)
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Service health check |
| `GET` | `/health/qdrant` | Qdrant Cloud connection + collection stats |
| `POST` | `/ingest` | Ingest one artwork: download → BLIP-2 caption → CLIP embed → Qdrant upsert |
| `POST` | `/retrieve` | Query → CLIP text embed → top-K similar artworks from Qdrant |
| `POST` | `/pipeline` | Full RAG flow → returns `PipelineContext` for GAN conditioning |

### Data Storage Model

Qdrant stores **vectors + metadata only** — not actual image files.

```
Vector:   [0.023, -0.412, 0.891, ...]   ← 512-dim CLIP embedding (float32)
Payload:  {
    "title":     "Bridge over a Pond of Water Lilies",
    "artist":    "Claude Monet",
    "style":     "Impressionism",
    "year":      1899,
    "caption":   "A painting in Impressionism style by Claude Monet",
    "image_url": "https://images.metmuseum.org/...",   ← points to R2 in production
    "tags":      ["water", "bridge", "lilies"]
}
```

Actual image files are stored in **Cloudflare R2** in production. During development, public museum URLs (Met Museum API) are used as `image_url`.

### Environment Variables

Create `backend/.env` with the following:

```env
# Qdrant Cloud — get from cloud.qdrant.io
QDRANT_URL=https://your-cluster-id.region.cloud.qdrant.io
QDRANT_API_KEY=your_api_key_here
QDRANT_COLLECTION=art_references

# CLIP — switch to "cuda" on Railway GPU deployment
CLIP_DEVICE=cpu

# BLIP-2 — heavy model (~6GB), mocked during local dev
BLIP_DEVICE=cpu

# Retrieval
TOP_K=5
SCORE_THRESHOLD=0.20

# App
ENV=development
LOG_LEVEL=DEBUG
```

### Running Locally

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
pip install git+https://github.com/openai/CLIP.git

uvicorn rag.main:app --reload --port 8000
```

Swagger UI available at `http://localhost:8000/docs`

### Notes

- CLIP model weights (~338MB) are downloaded on first run and cached automatically.
- BLIP-2 (~6GB) is mocked locally with a template caption. Enable in `ingestor.py` for production.
- Qdrant collection is created automatically on startup if it doesn't exist.
- All image downloads use `User-Agent: Mozilla/5.0` to avoid 403 blocks from public image hosts.
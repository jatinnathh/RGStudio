RAG-Powered GAN Art Studio
Tagline: Describe an art style → RAG retrieves reference images + artist context → CLIP-guided GAN generates a new artwork in that style. Two systems, one seamless pipeline.
Core Tech Stack
Core Tech Stack

Frontend: Next.js 14 (App Router), Tailwind CSS, shadcn/ui
Backend: FastAPI
ML: AdaIN Style Transfer (VGG19 encoder/decoder), CLIP (ViT-B/32), BLIP-2 (captioning)
Vector DB: Qdrant Cloud (free tier)
Storage: Cloudflare R2 (generated images)
Auth + DB: Clerk, NeonDB (Drizzle ORM)
Deploy: Vercel (frontend), Railway (FastAPI), HuggingFace Spaces (model demo + weights)


---

## Full Pipeline — Architecture

> **Status: RAG ✅ Complete & Tested | GAN ✅ Implemented**

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
┌──────────────────────┐
│   CLIP Ranker        │  ← picks best style reference from RAG results
└──────────────────────┘
        │
        ▼
┌──────────────────────┐
│  AdaIN Style Transfer│  ← VGG19 encode → AdaIN normalize → decode → output image
└──────────────────────┘
        │
        ▼
  Generated Artwork      ← base64 JPEG + metadata + CLIP quality score
```

---

## Module Structure

### RAG Pipeline (`backend/rag/`)

```
backend/rag/
├── config.py                   # All env vars via pydantic-settings, loaded from backend/.env
├── pipeline.py                 # End-to-end orchestrator → returns PipelineContext for GAN
├── main.py                     # FastAPI app — /health, /ingest, /retrieve, /pipeline, /generate, /style-transfer
│
├── schemas/
│   └── models.py               # All Pydantic models: IngestRequest, GenerateRequest, GenerateResponse, etc.
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

### GAN Module (`backend/gan/`)

```
backend/gan/
├── __init__.py
├── config.py                   # GAN-specific settings (output_size, style_weight, device, etc.)
├── models/
│   ├── __init__.py
│   ├── vgg_encoder.py          # VGG19 feature extractor (pretrained, frozen, up to relu4_1)
│   └── decoder.py              # AdaIN decoder (mirrors VGG19 in reverse, pretrained from HuggingFace)
├── style_transfer.py           # Core AdaIN engine: content + style → stylized image
├── clip_ranker.py              # CLIP scoring to rank/pick best reference from RAG results
├── generate.py                 # Main orchestrator: text_to_art + style_transfer_from_upload
└── utils.py                    # Image I/O: URL download, PIL↔tensor, base64 encoding
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Service health check |
| `GET` | `/health/qdrant` | Qdrant Cloud connection + collection stats |
| `POST` | `/ingest` | Ingest one artwork: download → BLIP-2 caption → CLIP embed → Qdrant upsert |
| `POST` | `/retrieve` | Query → CLIP text embed → top-K similar artworks from Qdrant |
| `POST` | `/pipeline` | Full RAG flow → returns `PipelineContext` for GAN conditioning |
| `POST` | `/generate` | **Text → Art**: query → RAG → CLIP rank → AdaIN style transfer → image |
| `POST` | `/style-transfer` | **Style Transfer**: upload image + style query → RAG → AdaIN → stylized image |

### Generation Endpoints

#### `POST /generate` — Text to Art

```json
{
  "query": "impressionist sunset over water",
  "top_k": 5,
  "style_weight": 0.8,
  "output_size": 512,
  "use_multi_style": false
}
```

Response:
```json
{
  "success": true,
  "image_base64": "/9j/4AAQ...",
  "style_reference": { "title": "Bridge over...", "artist": "Claude Monet", ... },
  "clip_score": 0.287,
  "generation_time_ms": 4200,
  "query": "impressionist sunset over water",
  "message": "Generated artwork in the style of 'Bridge over a Pond of Water Lilies'..."
}
```

#### `POST /style-transfer` — Image Upload + Style

Multipart form data:
- `image`: Image file (JPEG/PNG, max 10MB)
- `style_query`: Target style description
- `style_weight`: 0.0-1.0 (default 0.8)
- `output_size`: 128-1024 (default 512)
- `top_k`: 1-20 (default 5)

```bash
curl -X POST http://localhost:8000/style-transfer \
  -F "image=@my_photo.jpg" \
  -F "style_query=cubist Picasso style" \
  -F "style_weight=0.7"
```

---

## How the GAN Works (AdaIN Style Transfer)

Based on ["Arbitrary Style Transfer in Real-time with Adaptive Instance Normalization"](https://arxiv.org/abs/1703.06868) (Huang & Belongie, 2017):

1. **VGG19 Encoder**: Extracts features at `relu4_1` from both content and style images
2. **AdaIN**: Aligns content feature statistics (mean, std) to match the style's
3. **Decoder**: Reconstructs the image from normalized features via transposed convolutions
4. **Alpha blending**: Controls style strength — `alpha * stylized + (1 - alpha) * content`

For **text-to-art** mode, a "content seed" is created by blurring and desaturating the best style reference. This gives organic structure while letting the style's colors and textures dominate.

Pretrained decoder weights are automatically downloaded from HuggingFace (~2MB).

---

## Data Storage Model

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

---

## Environment Variables

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

# GAN — switch to "cuda" on GPU
GAN_DEVICE=cpu

# Retrieval
TOP_K=5
SCORE_THRESHOLD=0.20

# App
ENV=development
LOG_LEVEL=DEBUG
```

---

## Running Locally

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
pip install git+https://github.com/openai/CLIP.git

uvicorn rag.main:app --reload --port 8000
```

Swagger UI available at `http://localhost:8000/docs`

---

## Notes

- CLIP model weights (~338MB) are downloaded on first run and cached automatically.
- VGG19 weights (~80MB) are downloaded on first run and cached by PyTorch.
- AdaIN decoder weights (~2MB) are downloaded from HuggingFace on first use.
- BLIP-2 (~6GB) is mocked locally with a template caption. Enable in `ingestor.py` for production.
- Qdrant collection is created automatically on startup if it doesn't exist.
- All image downloads use `User-Agent: Mozilla/5.0` to avoid 403 blocks from public image hosts.
- Generation takes ~2-5 seconds on CPU, <1 second on CUDA GPU.
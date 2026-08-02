# RGStudio — RAG-Powered GAN Art Studio: Flagship Implementation Plan

> **Mission**: _Describe an art style → RAG retrieves reference images + artist context → CLIP-guided GAN generates a new artwork in that style. Two systems, one seamless pipeline._

---

## Current Status Audit

### ✅ Already Built (Keep & Extend)
| Component | Status | Notes |
|---|---|---|
| `backend/rag/` — FastAPI app | ✅ Working | All endpoints live: `/ingest`, `/retrieve`, `/pipeline`, `/generate`, `/style-transfer` |
| `backend/gan/style_transfer.py` | ✅ Working | AdaIN (VGG19 encoder + decoder) fully implemented |
| `backend/gan/generate.py` | ✅ Working | `text_to_art` + `style_transfer_from_upload`, multi-style blending |
| `backend/gan/clip_ranker.py` | ✅ Working | CLIP re-ranking of RAG results |
| `backend/rag/vectorstore/` | ✅ Working | Qdrant Cloud connected, collection exists |
| `backend/rag/pipeline.py` | ✅ Working | Full RAG→GAN context assembly |
| `app/` — Next.js Landing | ✅ Working | Stunning 3D hero with scroll-driven camera (Three.js + Lenis) |
| `app/home/page.tsx` | ✅ Working | RAG retrieval workbench (basic) |
| `backend/seed_artworks.py` | ✅ Working | 28 artworks seeded |

### 🔴 Missing / Needs Building
- **Qdrant DB**: Only ~28 artworks. Need **~100 diverse styles** seeded.
- **Frontend `/home`**: RAG retrieval only. No generate button wired up. No style-transfer upload. No image output panel.
- **Auth**: Clerk not integrated.
- **Storage**: Cloudflare R2 not integrated — generated images not persisted.
- **DB**: NeonDB (Drizzle ORM) for generation history not set up.
- **GAN model weights**: Decoder weights not verified/bundled — need Railway deployment config.
- **CI/CD**: No Railway config, no Vercel config, no HuggingFace Spaces demo.
- **HuggingFace Spaces**: No model demo page.

---

## Architecture Overview

```
┌─────────────────────────────────────────┐
│              FRONTEND (Vercel)           │
│  Next.js 16 App Router + Tailwind v4    │
│                                          │
│  /           → 3D Landing (Three.js)    │
│  /home       → Studio Workbench         │
│  /generate   → Text-to-Art Page         │
│  /transfer   → Image Style Transfer     │
│  /gallery    → Generated Works Feed     │
│  /sign-in    → Clerk Auth               │
└─────────────┬───────────────────────────┘
              │ HTTPS REST
┌─────────────▼───────────────────────────┐
│         BACKEND (Railway)                │
│  FastAPI + Uvicorn                       │
│                                          │
│  /health      → Health check            │
│  /retrieve    → CLIP RAG search         │
│  /pipeline    → RAG context assembly    │
│  /generate    → Text → Art (full pipe)  │
│  /style-transfer → Upload → Stylize     │
│  /history     → User generation history │
│  /upload-r2   → Presigned upload URLs   │
└──────┬───────────────┬──────────────────┘
       │               │
┌──────▼──────┐  ┌─────▼──────────────────┐
│ Qdrant Cloud│  │ NeonDB (Drizzle ORM)   │
│ 100+ artworks│  │ users, generations,    │
│ CLIP vectors │  │ gallery metadata       │
└─────────────┘  └────────────────────────┘
                        │
               ┌────────▼────────────────┐
               │  Cloudflare R2 (Storage) │
               │  generated-images bucket │
               └─────────────────────────┘
```

---

## Phase 1 — Qdrant DB Seeding (Immediate)

**Goal**: Expand from 28 → 100+ artworks covering all major styles.

### [NEW] `backend/seed_100_styles.py`
A completely new seed script covering **100 artworks** across:
- Impressionism, Post-Impressionism, Expressionism (×10)
- Renaissance, Baroque, Rococo, Neoclassicism (×12)
- Romanticism, Realism, Naturalism (×8)
- Cubism, Futurism, Constructivism (×8)
- Surrealism, Dada, Symbolism (×8)
- Abstract, Abstract Expressionism, De Stijl (×8)
- Pop Art, Op Art, Minimalism (×6)
- Ukiyo-e, Sumi-e, Persian Miniature, Mughal, Indian Classical (×8)
- Art Nouveau, Art Deco (×6)
- Street Art / Graffiti, Digital Art, Glitch Art (×6)
- Contemporary / Hyperrealism, Photorealism (×6)
- Biomechanical, Steampunk, Dark Fantasy (×4)

All with accurate Wikimedia URLs, descriptive tags, and artist context.

---

## Phase 2 — Backend Hardening

### [MODIFY] `backend/rag/main.py`
- Add `/history` endpoint (GET + POST) backed by NeonDB
- Add `/upload-r2` presigned URL endpoint
- Add `/styles` endpoint — returns list of all indexed styles (from Qdrant facets)
- Add Clerk JWT middleware for protected routes
- Add proper CORS: restrict to Vercel domain in production

### [NEW] `backend/rag/storage/r2_client.py`
- Cloudflare R2 integration via `boto3` (S3-compatible)
- `upload_image(image_bytes, key) → public_url`
- `generate_presigned_url(key) → url`
- Store every generated artwork in R2, return CDN URL

### [NEW] `backend/rag/db/neon.py`
- NeonDB connection via `asyncpg` + Drizzle-compatible schema
- `generations` table: `id, user_id, query, style, image_url, clip_score, created_at`
- `saved_artworks` table: user favorites

### [MODIFY] `backend/rag/config.py`
- Add: `CLOUDFLARE_R2_*`, `NEON_DATABASE_URL`, `CLERK_SECRET_KEY`

### [MODIFY] `backend/requirements.txt`
- Add: `boto3`, `asyncpg`, `python-jose[cryptography]`, `httpx`

---

## Phase 3 — Frontend Overhaul (Flagship UI)

The frontend is the **showstopper**. Every page must be visually stunning.

### [MODIFY] `app/home/page.tsx` → Full Studio Workbench
Transform the current minimal retrieval page into a **full creative workbench**:

**Layout**: 3-column dark studio
- **Left sidebar**: Mode selector (Text-to-Art / Style Transfer), style filters, settings panel (style weight slider, top-K, output size)
- **Center canvas**: Large generation output area with animated loading state, result image with zoom, CLIP score badge
- **Right panel**: RAG references grid (retrieved artworks with similarity scores), artist context card, style summary prompt box

**Features to wire up**:
- ✅ `/retrieve` → RAG Reference grid
- 🔴 `/generate` → Text-to-Art output with base64 image rendering
- 🔴 `/style-transfer` → Drag-and-drop upload + style generation
- 🔴 History sidebar (last N generations from NeonDB)
- 🔴 Save to Gallery button (→ R2 upload)

### [NEW] `app/generate/page.tsx`
Dedicated **Text-to-Art** generation page:
- Full-width prompt textarea with style suggestions
- Real-time streaming progress (SSE or polling)
- Split-view: RAG references on left, generated output on right
- CLIP score meter, reference artwork attribution
- Share / Save buttons

### [NEW] `app/transfer/page.tsx`
Dedicated **Style Transfer** page:
- Drag-and-drop upload zone (your image)
- Style description input
- Before/After slider comparison
- Multi-style blending weight controls

### [NEW] `app/gallery/page.tsx`
**Public Gallery** — community generated artworks feed:
- Masonry grid layout
- Filter by style
- Each card: generated image, original query, CLIP score, timestamp
- "Recreate" button to re-use the same prompt

### [NEW] `app/components/GenerationPanel.tsx`
Reusable generation output panel:
- Animated shimmer loading state
- Image with zoom/pan (react-medium-image-zoom)
- Metadata overlay (style, CLIP score, reference)
- Download + Share buttons

### [NEW] `app/components/RagReferences.tsx`
CLIP-retrieved references grid component:
- Artwork thumbnail + score
- Artist info tooltip
- "Use as style" quick-action

### [NEW] `app/lib/api.ts`
Typed API client for all backend endpoints:
```typescript
generateArt(params) → Promise<GenerateResponse>
styleTransfer(params) → Promise<StyleTransferResponse>
retrieveArtworks(params) → Promise<RetrievalResponse>
getHistory(userId) → Promise<Generation[]>
```

### [MODIFY] `app/layout.tsx`
- Add ClerkProvider wrapper
- Add Inter + Playfair Display Google Fonts
- Add global design tokens

---

## Phase 4 — Auth Integration (Clerk)

### [NEW] `app/sign-in/[[...sign-in]]/page.tsx`
### [NEW] `app/sign-up/[[...sign-up]]/page.tsx`
### [MODIFY] `middleware.ts` (new at root)
- Protect `/generate`, `/transfer`, `/gallery` routes
- Public: `/`, `/home` (demo mode)

---

## Phase 5 — Infrastructure & Deployment

### [NEW] `railway.toml`
```toml
[build]
builder = "NIXPACKS"
buildCommand = "pip install -r requirements.txt"

[deploy]
startCommand = "uvicorn rag.main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
```

### [NEW] `vercel.json`
```json
{
  "framework": "nextjs",
  "regions": ["bom1"],
  "env": { "NEXT_PUBLIC_API_URL": "@api_url" }
}
```

### [NEW] `spaces/app.py` (HuggingFace Spaces)
- Gradio demo of the full pipeline
- Public-facing demo without auth
- Links back to the main app

### [NEW] `.github/workflows/deploy.yml`
- On push to `main`: test → deploy backend to Railway → deploy frontend to Vercel

---

## Phase 6 — Polish & Performance

### Backend
- Add Redis caching for frequently retrieved styles (Railway Redis add-on)
- Background job queue (FastAPI BackgroundTasks) for long generations
- WebSocket or SSE endpoint for real-time generation progress
- Rate limiting per Clerk user ID

### Frontend
- `next/image` for all artwork thumbnails
- `react-query` for data fetching + caching
- Skeleton loading states everywhere
- Error boundaries + toast notifications
- PWA manifest for installability

---

## Verification Plan

### Automated
```bash
# Backend unit tests
pytest backend/tests/ -v

# Frontend type check
npx tsc --noEmit

# API integration test (curl)
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"query": "impressionist sunset", "style_weight": 0.8}'
```

### Manual
1. Run seed script → verify 100 artworks in Qdrant dashboard
2. POST `/retrieve` with "van gogh starry night" → confirm top result is Van Gogh
3. POST `/generate` → confirm base64 image returned, CLIP score > 0.2
4. Upload photo + style query → confirm style-transferred image
5. Open `/home` → confirm generate button works end-to-end
6. Sign in with Clerk → confirm protected routes redirect to sign-in

---

## Open Questions

> [!IMPORTANT]
> **Q1**: Do you want Cloudflare R2 storage now or defer to Phase 4? (R2 requires a Cloudflare account with billing enabled)

> [!IMPORTANT]
> **Q2**: Do you have a NeonDB account and Clerk account set up? Or should the plan defer auth/DB to a later phase and ship the core generation pipeline first?

> [!NOTE]
> **Q3**: The GAN decoder requires pretrained weights (`decoder.pth`). Are these weights already downloaded locally, or do we need a download step in the Railway build?

> [!NOTE]
> **Q4**: Should the `/gallery` page show all users' generations publicly, or only the current user's history?

---

## Execution Order (Recommended)

```
Week 1: Phase 1 (seed 100 styles) + Phase 2 (backend hardening) + Phase 3 (frontend overhaul)
Week 2: Phase 4 (Clerk auth) + Phase 5 (Railway + Vercel deploy)
Week 3: Phase 5 (HuggingFace Spaces) + Phase 6 (polish + perf)
```

**Start immediately with**: The seed script + frontend workbench overhaul (highest visual impact, zero blockers).

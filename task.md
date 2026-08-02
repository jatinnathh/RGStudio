# RGStudio — Flagship Implementation Task List

## Phase 1 — Qdrant DB Seeding
- [/] Create `seed_100_styles.py` with 100 artworks across 20+ movements
- [ ] Run seed script and verify 100 artworks in Qdrant

## Phase 2 — Backend Hardening
- [ ] Add `/styles` endpoint (indexed style list from Qdrant)
- [ ] Add `/history` endpoint (GET/POST generations)
- [ ] Add R2 storage client (`backend/rag/storage/r2_client.py`)
- [ ] Add NeonDB integration (`backend/rag/db/neon.py`)
- [ ] Update `config.py` with R2/NeonDB/Clerk keys
- [ ] Update `requirements.txt` (boto3, asyncpg, python-jose)
- [ ] Add Clerk JWT middleware for protected routes

## Phase 3 — Frontend Overhaul
- [ ] Overhaul `app/home/page.tsx` into full 3-column studio workbench
  - [ ] Left sidebar: mode selector, settings panel (style weight, top-K, output size)
  - [ ] Center canvas: generation output, animated loading, CLIP score badge
  - [ ] Right panel: RAG references grid, artist context card
  - [ ] Wire `/generate` endpoint to generate button
  - [ ] Wire `/style-transfer` for drag-and-drop upload mode
- [ ] Create `app/generate/page.tsx` (Text-to-Art dedicated page)
- [ ] Create `app/transfer/page.tsx` (Style Transfer dedicated page)
- [ ] Create `app/gallery/page.tsx` (Public gallery feed)
- [ ] Create `app/components/GenerationPanel.tsx`
- [ ] Create `app/components/RagReferences.tsx`
- [ ] Create `app/lib/api.ts` (typed API client)
- [ ] Update `app/layout.tsx` (ClerkProvider, fonts, design tokens)

## Phase 4 — Auth Integration
- [ ] Create `app/sign-in/[[...sign-in]]/page.tsx`
- [ ] Create `app/sign-up/[[...sign-up]]/page.tsx`
- [ ] Create `middleware.ts` (route protection)

## Phase 5 — Deployment
- [ ] Create `railway.toml`
- [ ] Create `vercel.json`
- [ ] Create `spaces/app.py` (HuggingFace Gradio demo)
- [ ] Create `.github/workflows/deploy.yml` (CI/CD)

## Phase 6 — Polish & Performance
- [ ] Redis caching for frequent style queries
- [ ] SSE/WebSocket progress for generation
- [ ] Rate limiting per Clerk user ID
- [ ] `next/image` optimisation throughout
- [ ] react-query data fetching layer
- [ ] Skeleton loading states
- [ ] Error boundaries + toast notifications

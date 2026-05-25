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
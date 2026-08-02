// app/lib/api.ts
// Typed API client for all RGStudio backend endpoints.

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Types ──────────────────────────────────────────────────────────────────

export interface RetrievedArtwork {
  artwork_id: string;
  score: number;
  title: string;
  artist: string;
  style: string;
  year?: number | null;
  caption: string;
  image_url: string;
  tags: string[];
}

export interface RetrievalResponse {
  query: string;
  results: RetrievedArtwork[];
  total_found: number;
}

export interface GenerateRequest {
  query: string;
  top_k?: number;
  style_weight?: number;
  output_size?: number;
  use_multi_style?: boolean;
}

export interface GenerateResponse {
  success: boolean;
  image_base64: string;
  style_reference: RetrievedArtwork | null;
  clip_score: number;
  generation_time_ms: number;
  query: string;
  message: string;
}

export interface StyleTransferResponse {
  success: boolean;
  image_base64: string;
  style_reference: RetrievedArtwork | null;
  clip_score: number;
  generation_time_ms: number;
  style_query: string;
  message: string;
}

export interface HealthResponse {
  status: string;
  service: string;
  env: string;
}

export interface StyleInfo {
  style: string;
  count: number;
  sample_image_url: string;
  sample_artist: string;
  sample_title: string;
}

export interface StylesResponse {
  styles: StyleInfo[];
  total: number;
}

export interface GalleryArtwork {
  id: string;
  title: string;
  artist: string;
  style: string;
  year?: number | null;
  caption: string;
  image_url: string;
  tags: string[];
}

export interface GalleryResponse {
  artworks: GalleryArtwork[];
  total: number;
}

export function resolveImageUrl(url: string | undefined | null): string {
  if (!url) return "";
  if (url.startsWith("http://") || url.startsWith("https://") || url.startsWith("data:")) {
    return url;
  }
  // Remove leading slash if API_BASE also ends with slash, otherwise preserve
  const cleanPath = url.startsWith("/") ? url : `/${url}`;
  return `${API_BASE}${cleanPath}`;
}

// ── Helpers ────────────────────────────────────────────────────────────────

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// ── API Methods ────────────────────────────────────────────────────────────

export const api = {
  health: () => get<HealthResponse>("/health"),

  retrieve: (query: string, topK = 5) =>
    post<RetrievalResponse>("/retrieve", { query, top_k: topK }),

  generate: (params: GenerateRequest) =>
    post<GenerateResponse>("/generate", params),

  styleTransfer: async (
    image: File,
    styleQuery: string,
    options?: { topK?: number; styleWeight?: number; outputSize?: number }
  ): Promise<StyleTransferResponse> => {
    const form = new FormData();
    form.append("image", image);
    form.append("style_query", styleQuery);
    if (options?.topK) form.append("top_k", String(options.topK));
    if (options?.styleWeight) form.append("style_weight", String(options.styleWeight));
    if (options?.outputSize) form.append("output_size", String(options.outputSize));

    const res = await fetch(`${API_BASE}/style-transfer`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || `Style transfer failed: ${res.status}`);
    }
    return res.json() as Promise<StyleTransferResponse>;
  },

  styles: () => get<StylesResponse>("/styles"),

  gallery: (limit = 100) => get<GalleryResponse>(`/gallery?limit=${limit}`),
};

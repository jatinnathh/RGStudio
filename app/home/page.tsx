"use client";

import Link from "next/link";
import { FormEvent, useMemo, useState } from "react";

type RetrievedArtwork = {
  artwork_id: string;
  score: number;
  title: string;
  artist: string;
  style: string;
  year?: number | null;
  caption: string;
  image_url: string;
  tags: string[];
};

type RetrievalResponse = {
  query: string;
  results: RetrievedArtwork[];
  total_found: number;
};

const sampleResults: RetrievedArtwork[] = [
  {
    artwork_id: "demo-monet-water-lilies",
    score: 0.3127,
    title: "Water Lilies",
    artist: "Claude Monet",
    style: "Impressionism",
    year: 1906,
    caption: "Soft reflections, broken brushwork, pond light, and atmospheric color fields.",
    image_url: "/images/gallery-fluid.jpg",
    tags: ["water", "lilies", "light", "nature"],
  },
  {
    artwork_id: "demo-hokusai-wave",
    score: 0.2814,
    title: "The Great Wave off Kanagawa",
    artist: "Katsushika Hokusai",
    style: "Ukiyo-e",
    year: 1831,
    caption: "Graphic linework, compressed motion, ocean rhythm, and clean blue contrast.",
    image_url: "/images/gallery-nature.jpg",
    tags: ["wave", "ocean", "line", "japan"],
  },
  {
    artwork_id: "demo-kandinsky-composition",
    score: 0.2579,
    title: "Composition VIII",
    artist: "Wassily Kandinsky",
    style: "Abstract",
    year: 1923,
    caption: "Geometric tension, angular movement, circles, lines, and musical color structure.",
    image_url: "/images/artwork-abstract.jpg",
    tags: ["abstract", "geometry", "color", "motion"],
  },
];

export default function StudioHome() {
  const [query, setQuery] = useState("impressionist sunset over water, Monet style");
  const [topK, setTopK] = useState(5);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [response, setResponse] = useState<RetrievalResponse | null>(null);

  const results = response?.results?.length ? response.results : sampleResults;
  const topResult = results[0];
  const stylePrompt = useMemo(
    () =>
      results
        .slice(0, 3)
        .map((artwork) => `${artwork.title} by ${artwork.artist}: ${artwork.caption}`)
        .join("\n"),
    [results]
  );

  async function handleRetrieve(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      const res = await fetch("http://localhost:8000/retrieve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, top_k: topK }),
      });

      if (!res.ok) {
        const details = await res.text();
        throw new Error(details || `Request failed with ${res.status}`);
      }

      const data = (await res.json()) as RetrievalResponse;
      setResponse(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not reach the retrieval service.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="studio-shell">
      <style>{`
        .studio-shell {
          min-height: 100vh;
          background: #120f0d;
          color: #f5efe7;
          padding: 24px;
          font-family: var(--font-dm-sans), sans-serif;
        }

        .studio-nav,
        .studio-hero,
        .studio-workspace {
          max-width: 1180px;
          margin-left: auto;
          margin-right: auto;
        }

        .studio-nav {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 34px;
          gap: 16px;
        }

        .studio-brand,
        .studio-docs {
          color: #f5efe7;
          text-decoration: none;
        }

        .studio-brand {
          display: inline-flex;
          align-items: center;
          gap: 10px;
          font-weight: 700;
        }

        .studio-mark {
          display: inline-grid;
          place-items: center;
          width: 34px;
          height: 34px;
          border: 1px solid rgba(255,255,255,0.24);
          border-radius: 6px;
          background: rgba(255,255,255,0.08);
          font-family: var(--font-playfair), serif;
        }

        .studio-docs {
          border: 1px solid rgba(255,255,255,0.24);
          border-radius: 6px;
          padding: 10px 14px;
          background: rgba(255,255,255,0.06);
          white-space: nowrap;
        }

        .studio-hero {
          display: grid;
          grid-template-columns: minmax(0, 1fr) minmax(320px, 440px);
          gap: 24px;
          align-items: stretch;
        }

        .studio-hero-copy {
          min-height: 360px;
          display: flex;
          flex-direction: column;
          justify-content: center;
          background-image: linear-gradient(rgba(18,15,13,0.08), rgba(18,15,13,0.72)), url('/images/pipeline-landscape.jpg');
          background-size: cover;
          background-position: center;
          border-radius: 8px;
          padding: 42px;
        }

        .studio-kicker {
          margin: 0;
          color: #f1c45b;
          text-transform: uppercase;
          font-size: 12px;
          letter-spacing: 0.12em;
          font-weight: 700;
        }

        .studio-title {
          max-width: 760px;
          margin: 16px 0;
          font-family: var(--font-playfair), serif;
          font-size: clamp(38px, 6vw, 76px);
          line-height: 0.96;
          font-weight: 700;
        }

        .studio-subtitle {
          max-width: 650px;
          margin: 0;
          color: rgba(245,239,231,0.78);
          line-height: 1.7;
          font-size: 16px;
        }

        .studio-query-panel,
        .studio-context-panel,
        .studio-result-card {
          border: 1px solid rgba(255,255,255,0.14);
          border-radius: 8px;
          background: #1b1714;
        }

        .studio-query-panel {
          padding: 24px;
          display: flex;
          flex-direction: column;
          gap: 14px;
        }

        .studio-label {
          color: rgba(245,239,231,0.86);
          font-weight: 700;
        }

        .studio-textarea,
        .studio-number {
          border-radius: 6px;
          border: 1px solid rgba(255,255,255,0.18);
          background: #0f0d0b;
          color: #f5efe7;
          font: inherit;
        }

        .studio-textarea {
          width: 100%;
          resize: vertical;
          min-height: 150px;
          padding: 14px;
          line-height: 1.5;
        }

        .studio-controls {
          display: flex;
          justify-content: space-between;
          gap: 12px;
          align-items: end;
        }

        .studio-number-label {
          display: grid;
          gap: 6px;
          color: rgba(245,239,231,0.78);
          font-size: 13px;
        }

        .studio-number {
          width: 90px;
          padding: 10px 12px;
        }

        .studio-primary,
        .studio-secondary {
          border-radius: 6px;
          padding: 12px 16px;
          font-weight: 800;
        }

        .studio-primary {
          min-width: 140px;
          border: 0;
          background: #f1c45b;
          color: #17120c;
          cursor: pointer;
        }

        .studio-primary:disabled {
          cursor: wait;
          opacity: 0.7;
        }

        .studio-error {
          margin: 0;
          color: #ffb3a7;
          font-size: 13px;
          line-height: 1.5;
        }

        .studio-workspace {
          margin-top: 24px;
          display: grid;
          grid-template-columns: minmax(0, 1fr) 360px;
          gap: 24px;
          align-items: start;
        }

        .studio-section-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 14px;
          gap: 12px;
        }

        .studio-count,
        .studio-meta {
          margin: 0;
          color: rgba(245,239,231,0.58);
          font-size: 13px;
        }

        .studio-grid {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 16px;
        }

        .studio-result-card {
          overflow: hidden;
        }

        .studio-artwork-image {
          width: 100%;
          aspect-ratio: 4 / 3;
          object-fit: cover;
          display: block;
        }

        .studio-card-body {
          padding: 16px;
        }

        .studio-card-topline {
          display: flex;
          justify-content: space-between;
          gap: 10px;
          align-items: center;
          margin-bottom: 12px;
        }

        .studio-score {
          color: #f1c45b;
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
          font-size: 12px;
        }

        .studio-style-pill {
          color: #f5efe7;
          border: 1px solid rgba(255,255,255,0.16);
          border-radius: 999px;
          padding: 4px 8px;
          font-size: 11px;
        }

        .studio-card-title,
        .studio-panel-title {
          font-family: var(--font-playfair), serif;
          line-height: 1.08;
        }

        .studio-card-title {
          margin: 0 0 6px;
          font-size: 24px;
        }

        .studio-caption,
        .studio-panel-text {
          color: rgba(245,239,231,0.76);
          line-height: 1.55;
          font-size: 14px;
        }

        .studio-caption {
          margin: 12px 0 0;
        }

        .studio-context-panel {
          position: sticky;
          top: 24px;
          padding: 22px;
        }

        .studio-panel-title {
          margin: 12px 0;
          font-size: 30px;
        }

        .studio-panel-text {
          margin: 0 0 16px;
        }

        .studio-prompt-box {
          white-space: pre-wrap;
          overflow: auto;
          max-height: 260px;
          border-radius: 6px;
          border: 1px solid rgba(255,255,255,0.12);
          background: #0f0d0b;
          color: rgba(245,239,231,0.78);
          padding: 14px;
          line-height: 1.55;
          font-size: 12px;
        }

        .studio-secondary {
          width: 100%;
          margin-top: 14px;
          border: 1px solid rgba(241,196,91,0.55);
          background: rgba(241,196,91,0.12);
          color: #f1c45b;
        }

        @media (max-width: 960px) {
          .studio-hero,
          .studio-workspace {
            grid-template-columns: 1fr;
          }

          .studio-context-panel {
            position: static;
          }

          .studio-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }
        }

        @media (max-width: 640px) {
          .studio-shell {
            padding: 16px;
          }

          .studio-hero-copy,
          .studio-query-panel {
            padding: 20px;
          }

          .studio-grid {
            grid-template-columns: 1fr;
          }

          .studio-controls {
            align-items: stretch;
            flex-direction: column;
          }

          .studio-primary,
          .studio-number {
            width: 100%;
          }
        }
      `}</style>

      <nav className="studio-nav">
        <Link href="/" className="studio-brand">
          <span className="studio-mark">AS</span>
          <span>RAG Art Studio</span>
        </Link>
        <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer" className="studio-docs">
          API docs
        </a>
      </nav>

      <section className="studio-hero">
        <div className="studio-hero-copy">
          <p className="studio-kicker">RAG-powered generation workbench</p>
          <h1 className="studio-title">Describe an art style. Retrieve the references. Generate with intent.</h1>
          <p className="studio-subtitle">
            This is the operating surface for the pipeline: CLIP search pulls visual references and artist context, then
            the generation step uses the best match as style guidance.
          </p>
        </div>

        <form onSubmit={handleRetrieve} className="studio-query-panel">
          <label htmlFor="style-query" className="studio-label">
            Style prompt
          </label>
          <textarea
            id="style-query"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            minLength={3}
            maxLength={500}
            rows={4}
            className="studio-textarea"
          />
          <div className="studio-controls">
            <label className="studio-number-label">
              Top K
              <input
                type="number"
                min={1}
                max={20}
                value={topK}
                onChange={(event) => setTopK(Number(event.target.value))}
                className="studio-number"
              />
            </label>
            <button disabled={isLoading} type="submit" className="studio-primary">
              {isLoading ? "Retrieving..." : "Retrieve"}
            </button>
          </div>
          {error ? <p className="studio-error">Backend response: {error}</p> : null}
        </form>
      </section>

      <section className="studio-workspace">
        <div>
          <div className="studio-section-header">
            <p className="studio-kicker">Reference set</p>
            <p className="studio-count">{response ? `${response.total_found} retrieved` : "demo preview"}</p>
          </div>
          <div className="studio-grid">
            {results.map((artwork) => (
              <article key={artwork.artwork_id} className="studio-result-card">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={artwork.image_url} alt={artwork.title} className="studio-artwork-image" />
                <div className="studio-card-body">
                  <div className="studio-card-topline">
                    <span className="studio-score">{artwork.score.toFixed(4)}</span>
                    <span className="studio-style-pill">{artwork.style}</span>
                  </div>
                  <h2 className="studio-card-title">{artwork.title}</h2>
                  <p className="studio-meta">
                    {artwork.artist}
                    {artwork.year ? `, ${artwork.year}` : ""}
                  </p>
                  <p className="studio-caption">{artwork.caption}</p>
                </div>
              </article>
            ))}
          </div>
        </div>

        <aside className="studio-context-panel">
          <p className="studio-kicker">Generation context</p>
          <h2 className="studio-panel-title">Best reference: {topResult.title}</h2>
          <p className="studio-panel-text">
            The backend can pass this ranked context into `/pipeline` or `/generate` for CLIP ranking and AdaIN style
            transfer.
          </p>
          <pre className="studio-prompt-box">{stylePrompt}</pre>
          <button type="button" className="studio-secondary">
            Generate endpoint ready
          </button>
        </aside>
      </section>
    </main>
  );
}

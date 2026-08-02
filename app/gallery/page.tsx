"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api, resolveImageUrl, type GalleryArtwork, type StyleInfo } from "../lib/api";

export default function GalleryPage() {
  const [artworks, setArtworks] = useState<GalleryArtwork[]>([]);
  const [styles, setStyles] = useState<StyleInfo[]>([]);
  const [selectedStyle, setSelectedStyle] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedArt, setSelectedArt] = useState<GalleryArtwork | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [galleryRes, stylesRes] = await Promise.all([
          api.gallery(200),
          api.styles(),
        ]);
        setArtworks(galleryRes.artworks);
        setStyles(stylesRes.styles);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load gallery");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const filteredArtworks = selectedStyle
    ? artworks.filter((a) => a.style === selectedStyle)
    : artworks;

  const handleStyleClick = useCallback(
    (style: string) => {
      setSelectedStyle((prev) => (prev === style ? null : style));
    },
    []
  );

  return (
    <main className="gallery-root">
      <style>{GALLERY_CSS}</style>

      {/* Nav */}
      <nav className="g-nav">
        <Link href="/" className="g-brand">
          <span className="g-mark">RG</span>
          <span>RGStudio</span>
        </Link>
        <div className="g-nav-links">
          <Link href="/home" className="g-nav-link">
            Studio
          </Link>
          <Link href="/gallery" className="g-nav-link active">
            Gallery
          </Link>
        </div>
      </nav>

      {/* Header */}
      <header className="g-header">
        <h1 className="g-title">Art Reference Gallery</h1>
        <p className="g-subtitle">
          {artworks.length} artworks across {styles.length} styles in the RAG
          knowledge base
        </p>
      </header>

      {/* Style Filters */}
      {styles.length > 0 && (
        <div className="g-filters">
          <button
            className={`g-filter-pill ${!selectedStyle ? "active" : ""}`}
            onClick={() => setSelectedStyle(null)}
          >
            All ({artworks.length})
          </button>
          {styles.map((s) => (
            <button
              key={s.style}
              className={`g-filter-pill ${selectedStyle === s.style ? "active" : ""}`}
              onClick={() => handleStyleClick(s.style)}
            >
              {s.style} ({s.count})
            </button>
          ))}
        </div>
      )}

      {/* Error */}
      {error && <p className="g-error">{error}</p>}

      {/* Loading */}
      {loading && (
        <div className="g-loading">
          <div className="g-spinner" />
          <p>Loading gallery...</p>
        </div>
      )}

      {/* Gallery Grid */}
      {!loading && (
        <div className="g-grid">
          {filteredArtworks.map((art) => (
            <div
              key={art.id}
              className="g-card"
              onClick={() => setSelectedArt(art)}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={resolveImageUrl(art.image_url)}
                alt={art.title}
                className="g-card-img"
                loading="lazy"
              />
              <div className="g-card-overlay">
                <span className="g-card-style">{art.style}</span>
                <h3 className="g-card-title">{art.title}</h3>
                <p className="g-card-artist">
                  {art.artist}
                  {art.year ? ` · ${art.year}` : ""}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Lightbox Modal */}
      {selectedArt && (
        <div className="g-lightbox" onClick={() => setSelectedArt(null)}>
          <div className="g-lb-content" onClick={(e) => e.stopPropagation()}>
            <button
              className="g-lb-close"
              onClick={() => setSelectedArt(null)}
            >
              &times;
            </button>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={resolveImageUrl(selectedArt.image_url)}
              alt={selectedArt.title}
              className="g-lb-img"
            />
            <div className="g-lb-meta">
              <span className="g-lb-style">{selectedArt.style}</span>
              <h2 className="g-lb-title">{selectedArt.title}</h2>
              <p className="g-lb-artist">
                {selectedArt.artist}
                {selectedArt.year ? `, ${selectedArt.year}` : ""}
              </p>
              <p className="g-lb-caption">{selectedArt.caption}</p>
              <div className="g-lb-tags">
                {selectedArt.tags?.map((tag) => (
                  <span key={tag} className="g-tag">
                    {tag}
                  </span>
                ))}
              </div>
              <Link
                href={`/home?style=${encodeURIComponent(selectedArt.style)}`}
                className="g-lb-use-btn"
              >
                Use as Style Reference &rarr;
              </Link>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

const GALLERY_CSS = `
  .gallery-root {
    min-height: 100vh;
    background: #0c0a09;
    color: #f0ebe3;
    font-family: var(--font-dm-sans), system-ui, sans-serif;
  }

  /* Nav */
  .g-nav {
    max-width: 1440px;
    margin: 0 auto;
    padding: 16px 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid rgba(255,255,255,0.06);
  }
  .g-brand {
    display: flex;
    align-items: center;
    gap: 10px;
    font-weight: 700;
    font-size: 15px;
    color: #f0ebe3;
    text-decoration: none;
  }
  .g-mark {
    display: grid;
    place-items: center;
    width: 32px;
    height: 32px;
    border-radius: 8px;
    background: linear-gradient(135deg, #f59e0b, #ef4444);
    font-family: var(--font-playfair), serif;
    font-size: 13px;
    font-weight: 700;
    color: white;
  }
  .g-nav-links { display: flex; gap: 8px; }
  .g-nav-link {
    padding: 8px 14px;
    border-radius: 6px;
    border: 1px solid rgba(255,255,255,0.08);
    color: rgba(240,235,227,0.6);
    text-decoration: none;
    font-size: 13px;
    transition: all 0.2s;
  }
  .g-nav-link:hover, .g-nav-link.active {
    background: rgba(255,255,255,0.06);
    color: #f0ebe3;
    border-color: rgba(255,255,255,0.15);
  }

  /* Header */
  .g-header {
    max-width: 1440px;
    margin: 0 auto;
    padding: 40px 24px 0;
    text-align: center;
  }
  .g-title {
    font-family: var(--font-playfair), serif;
    font-size: 36px;
    font-weight: 700;
    margin: 0 0 8px;
    background: linear-gradient(135deg, #f59e0b, #ef4444);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
  .g-subtitle {
    color: rgba(240,235,227,0.4);
    font-size: 14px;
    margin: 0;
  }

  /* Style Filters */
  .g-filters {
    max-width: 1440px;
    margin: 24px auto 0;
    padding: 0 24px;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: center;
  }
  .g-filter-pill {
    padding: 6px 14px;
    border-radius: 999px;
    border: 1px solid rgba(255,255,255,0.1);
    background: transparent;
    color: rgba(240,235,227,0.5);
    font-size: 12px;
    cursor: pointer;
    transition: all 0.2s;
  }
  .g-filter-pill:hover {
    border-color: rgba(245,158,11,0.3);
    color: rgba(240,235,227,0.8);
  }
  .g-filter-pill.active {
    background: rgba(245,158,11,0.15);
    border-color: rgba(245,158,11,0.3);
    color: #f59e0b;
  }

  /* Error & Loading */
  .g-error {
    text-align: center;
    padding: 20px;
    color: #fca5a5;
    font-size: 14px;
  }
  .g-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 60px;
    gap: 16px;
  }
  .g-spinner {
    width: 32px;
    height: 32px;
    border: 3px solid rgba(245,158,11,0.2);
    border-top-color: #f59e0b;
    border-radius: 50%;
    animation: g-spin 0.7s linear infinite;
  }
  @keyframes g-spin { to { transform: rotate(360deg); } }
  .g-loading p { color: rgba(240,235,227,0.4); font-size: 14px; }

  /* Gallery Grid */
  .g-grid {
    max-width: 1440px;
    margin: 24px auto 40px;
    padding: 0 24px;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 16px;
  }
  .g-card {
    position: relative;
    border-radius: 10px;
    overflow: hidden;
    cursor: pointer;
    aspect-ratio: 4 / 3;
    transition: transform 0.3s, box-shadow 0.3s;
  }
  .g-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 40px rgba(0,0,0,0.5);
  }
  .g-card-img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
    transition: transform 0.5s;
  }
  .g-card:hover .g-card-img {
    transform: scale(1.05);
  }
  .g-card-overlay {
    position: absolute;
    inset: 0;
    background: linear-gradient(transparent 40%, rgba(0,0,0,0.9));
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    padding: 16px;
    opacity: 0;
    transition: opacity 0.3s;
  }
  .g-card:hover .g-card-overlay {
    opacity: 1;
  }
  .g-card-style {
    padding: 3px 10px;
    border-radius: 999px;
    border: 1px solid rgba(245,158,11,0.3);
    background: rgba(245,158,11,0.15);
    color: #f59e0b;
    font-size: 10px;
    font-weight: 700;
    width: fit-content;
    margin-bottom: 8px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .g-card-title {
    margin: 0;
    font-family: var(--font-playfair), serif;
    font-size: 16px;
    font-weight: 700;
    line-height: 1.2;
  }
  .g-card-artist {
    margin: 4px 0 0;
    font-size: 12px;
    color: rgba(240,235,227,0.5);
  }

  /* Lightbox */
  .g-lightbox {
    position: fixed;
    inset: 0;
    z-index: 999;
    background: rgba(0,0,0,0.85);
    backdrop-filter: blur(8px);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
    animation: g-fade-in 0.2s ease-out;
  }
  @keyframes g-fade-in { from { opacity: 0; } to { opacity: 1; } }
  .g-lb-content {
    max-width: 900px;
    max-height: 90vh;
    overflow-y: auto;
    background: #161412;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    display: flex;
    position: relative;
  }
  .g-lb-close {
    position: absolute;
    top: 12px;
    right: 12px;
    width: 36px;
    height: 36px;
    border: none;
    border-radius: 50%;
    background: rgba(0,0,0,0.6);
    color: white;
    font-size: 22px;
    cursor: pointer;
    z-index: 10;
    display: grid;
    place-items: center;
  }
  .g-lb-img {
    width: 55%;
    object-fit: cover;
    display: block;
  }
  .g-lb-meta {
    padding: 30px 24px;
    flex: 1;
    display: flex;
    flex-direction: column;
  }
  .g-lb-style {
    padding: 4px 12px;
    border-radius: 999px;
    border: 1px solid rgba(245,158,11,0.3);
    background: rgba(245,158,11,0.1);
    color: #f59e0b;
    font-size: 11px;
    font-weight: 700;
    width: fit-content;
    margin-bottom: 12px;
  }
  .g-lb-title {
    margin: 0;
    font-family: var(--font-playfair), serif;
    font-size: 24px;
    font-weight: 700;
    line-height: 1.2;
  }
  .g-lb-artist {
    margin: 8px 0 0;
    font-size: 13px;
    color: rgba(240,235,227,0.5);
  }
  .g-lb-caption {
    margin: 16px 0 0;
    font-size: 13px;
    line-height: 1.6;
    color: rgba(240,235,227,0.6);
  }
  .g-lb-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin: 16px 0 0;
  }
  .g-tag {
    padding: 3px 10px;
    border-radius: 6px;
    background: rgba(255,255,255,0.06);
    font-size: 11px;
    color: rgba(240,235,227,0.5);
  }
  .g-lb-use-btn {
    margin-top: auto;
    padding: 12px 18px;
    border-radius: 8px;
    background: linear-gradient(135deg, #f59e0b, #ef4444);
    color: white;
    text-decoration: none;
    font-size: 13px;
    font-weight: 700;
    text-align: center;
    transition: filter 0.2s;
  }
  .g-lb-use-btn:hover {
    filter: brightness(1.1);
  }

  @media (max-width: 768px) {
    .g-lb-content {
      flex-direction: column;
    }
    .g-lb-img {
      width: 100%;
      max-height: 300px;
    }
    .g-grid {
      grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    }
  }
`;
